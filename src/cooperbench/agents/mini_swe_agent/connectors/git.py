"""Git-based code sharing between agents.

Enables agents in separate containers to share code via git push/pull.
Uses a shared git server sandbox that agents connect to as a remote.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    Git Server Sandbox                    │
    │        git daemon --enable=receive-pack (bare repo)      │
    └─────────────────────────────────────────────────────────┘
                               ▲
              ┌────────────────┼────────────────┐
              │                │                │
         git push         git fetch        git push
         git pull                          git pull
              │                │                │
    ┌─────────▼────┐                 ┌─────────▼────┐
    │   Agent A    │                 │   Agent B    │
    │   sandbox    │                 │   sandbox    │
    └──────────────┘                 └──────────────┘

Example:
    # Create shared git server (once per task)
    git_server = GitServer.create(app=modal_app, run_id="abc123")

    # Create connector for each agent
    git = GitConnector(
        agent_id="agent1",
        agents=["agent1", "agent2"],
        server_url=git_server.url
    )

    # Configure agent's sandbox
    git.setup(env)

    # Agent can now use git normally:
    #   git push team agent1
    #   git fetch team
    #   git merge team/agent2
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import modal

if TYPE_CHECKING:
    from cooperbench.agents.mini_swe_agent.environments.docker import DockerEnvironment
    from cooperbench.agents.mini_swe_agent.environments.modal import ModalEnvironment


class GitServer:
    """Shared git server sandbox for code collaboration.

    Creates a Modal sandbox running git-daemon that agents can push/pull to.
    """

    def __init__(self, sandbox: modal.Sandbox, hostname: str):
        """Initialize with an existing sandbox.

        Use GitServer.create() to create a new server.
        """
        self._sandbox = sandbox
        self._hostname = hostname
        self._logger = logging.getLogger("cooperbench.agents.mini_swe_agent.git_server")

    @classmethod
    def create(
        cls,
        app: modal.App,
        run_id: str,
        timeout: int = 3600,
    ) -> GitServer:
        """Create and start a git server sandbox.

        Args:
            app: Modal app to create sandbox in
            run_id: Unique run identifier (for logging)
            timeout: Sandbox timeout in seconds

        Returns:
            GitServer instance ready to accept connections
        """
        logger = logging.getLogger("cooperbench.agents.mini_swe_agent.git_server")
        logger.debug(f"Creating git server for run {run_id}")

        # Image with git
        image = modal.Image.debian_slim().run_commands(
            "apt-get update && apt-get install -y git",
        )

        # Create sandbox with port 9418 exposed for git daemon (unencrypted TCP)
        sandbox = modal.Sandbox.create(
            image=image,
            app=app,
            timeout=timeout,
            unencrypted_ports=[9418],  # Expose git daemon port via TCP tunnel
        )

        # Initialize bare repo in /git/repo.git
        proc = sandbox.exec(
            "bash",
            "-c",
            """
            set -e
            mkdir -p /git/repo.git
            cd /git/repo.git
            git init --bare
            git config receive.denyCurrentBranch ignore
            touch git-daemon-export-ok
        """,
        )
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to init git repo: {proc.stderr.read()}")

        # Start git daemon in background
        # --enable=receive-pack allows pushing
        # --export-all exports all repos
        # --base-path=/git means URL /repo.git maps to /git/repo.git
        # --listen=0.0.0.0 to accept connections from tunnel
        proc = sandbox.exec(
            "bash",
            "-c",
            """
            git daemon \
                --reuseaddr \
                --export-all \
                --enable=receive-pack \
                --base-path=/git \
                --listen=0.0.0.0 \
                /git &

            # Wait for daemon to start
            sleep 1
            echo "Git daemon started"
        """,
        )
        proc.stdout.read()
        proc.wait()

        # Give daemon time to fully initialize
        time.sleep(1)

        # Get the tunnel URL for port 9418
        tunnels = sandbox.tunnels()

        if tunnels and 9418 in tunnels:
            tunnel = tunnels[9418]
            # Use the unencrypted endpoint for git protocol
            # Tunnel has: host, port (encrypted), unencrypted_host, unencrypted_port
            hostname = f"{tunnel.unencrypted_host}:{tunnel.unencrypted_port}"
            logger.debug(f"Using unencrypted tunnel: {hostname}")
        else:
            raise RuntimeError(f"Failed to get tunnel for port 9418. Available tunnels: {tunnels}")

        logger.debug(f"Git server ready at git://{hostname}")

        return cls(sandbox=sandbox, hostname=hostname)

    @property
    def url(self) -> str:
        """Git URL for agents to use as remote.

        Returns:
            Git URL for the repository (git://hostname/repo.git)
        """
        return f"git://{self._hostname}/repo.git"

    def cleanup(self) -> None:
        """Terminate the git server sandbox."""
        if self._sandbox:
            try:
                self._sandbox.terminate()
            except Exception:
                pass


class DockerGitServer:
    """Shared git server container for code collaboration.

    Creates a Docker container running git-daemon that agents can push/pull to.
    """

    def __init__(self, container, hostname: str, port: int, network_name: str):
        """Initialize with an existing container.

        Use DockerGitServer.create() to create a new server.
        """
        self._container = container
        self._hostname = hostname
        self._port = port
        self._network_name = network_name
        self._logger = logging.getLogger("cooperbench.agents.mini_swe_agent.docker_git_server")

    @classmethod
    def create(
        cls,
        run_id: str,
        timeout: int = 3600,
    ) -> DockerGitServer:
        """Create and start a git server container.

        Args:
            run_id: Unique run identifier (for container naming)
            timeout: Container timeout in seconds (not enforced, for compatibility)

        Returns:
            DockerGitServer instance ready to accept connections
        """
        logger = logging.getLogger("cooperbench.agents.mini_swe_agent.docker_git_server")
        logger.debug(f"Creating docker git server for run {run_id}")

        try:
            import docker
        except ImportError:
            raise RuntimeError("docker package is required for Docker backend. Install with: pip install docker")

        client = docker.from_env()

        # Use a simple Debian-based image with git
        image = "debian:bookworm-slim"

        # Pull image if not present
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.debug(f"Pulling image {image}")
            client.images.pull(image)

        # Create or get shared network for git server and agents
        network_name = f"cooperbench-git-{run_id}"
        try:
            network = client.networks.get(network_name)
        except docker.errors.NotFound:
            network = client.networks.create(network_name, driver="bridge")

        # Container name based on run_id
        container_name = f"cooperbench-git-{run_id}"

        # Remove existing container if it exists
        try:
            old_container = client.containers.get(container_name)
            old_container.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Create and start container with initialization script
        # The script initializes the repo, then starts git daemon in foreground to keep container alive
        init_script = """#!/bin/bash
set -e
apt-get update -qq
apt-get install -y -qq git > /dev/null 2>&1
mkdir -p /git/repo.git
cd /git/repo.git
git init --bare
git config receive.denyCurrentBranch ignore
touch git-daemon-export-ok
exec git daemon --reuseaddr --export-all --enable=receive-pack --base-path=/git --listen=0.0.0.0 /git
"""

        container = client.containers.run(
            image=image,
            command=["bash", "-c", init_script],
            name=container_name,
            detach=True,
            network=network_name,
            ports={"9418/tcp": None},  # Auto-assign port for host access
            remove=False,
        )

        # Wait for container to start and git daemon to initialize
        time.sleep(3)

        # Verify container is running
        container.reload()
        if container.status != "running":
            logs = container.logs().decode("utf-8", errors="replace")
            container.remove(force=True)
            raise RuntimeError(f"Git server container failed to start. Logs: {logs}")

        # Reload container to get port mapping
        container.reload()

        # Get the host port
        port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        if "9418/tcp" not in port_bindings or not port_bindings["9418/tcp"]:
            container.stop()
            container.remove(force=True)
            raise RuntimeError("Failed to get port mapping for git daemon")

        # Get container's IP on the network for inter-container communication
        container.reload()
        network_settings = container.attrs.get("NetworkSettings", {})
        networks = network_settings.get("Networks", {})
        if network_name in networks:
            container_ip = networks[network_name].get("IPAddress")
            if container_ip:
                hostname = container_ip
            else:
                # Fallback to container name (DNS resolution on same network)
                hostname = container_name
        else:
            # Fallback to container name
            hostname = container_name

        logger.debug(f"Git server ready at git://{hostname}:9418 (network: {network_name})")

        return cls(container=container, hostname=hostname, port=9418, network_name=network_name)

    @property
    def url(self) -> str:
        """Git URL for agents to use as remote.

        Returns:
            Git URL for the repository (git://hostname:port/repo.git)
        """
        return f"git://{self._hostname}:{self._port}/repo.git"

    @property
    def network_name(self) -> str:
        """Docker network name for agent containers to join."""
        return self._network_name

    def cleanup(self) -> None:
        """Stop and remove the git server container and network."""
        if self._container:
            try:
                self._container.stop(timeout=5)
            except Exception:
                pass
            try:
                self._container.remove(force=True)
            except Exception:
                pass
            self._container = None

        # Clean up network
        if hasattr(self, "_network_name") and self._network_name:
            try:
                import docker
                client = docker.from_env()
                try:
                    network = client.networks.get(self._network_name)
                    network.remove()
                except docker.errors.NotFound:
                    pass
            except Exception:
                pass


class GitConnector:
    """Configures an agent's sandbox for git collaboration.

    After setup(), the agent can use standard git commands:
    - git push team <branch>  - share changes
    - git fetch team          - get other agents' branches
    - git merge team/<agent>  - merge another agent's work
    - git branch -r           - list remote branches
    """

    # Remote name used in agent's git config
    REMOTE_NAME = "team"

    def __init__(
        self,
        agent_id: str,
        agents: list[str],
        server_url: str,
    ):
        """Initialize git connector.

        Args:
            agent_id: This agent's unique identifier (e.g., "agent1")
            agents: List of all agent IDs in the collaboration
            server_url: Git server URL from GitServer.url
        """
        self.agent_id = agent_id
        self.agents = agents
        self.server_url = server_url
        self._logger = logging.getLogger("cooperbench.agents.mini_swe_agent.git_connector")
        self._initialized = False

    def setup(self, env: ModalEnvironment | DockerEnvironment) -> None:
        """Configure git remote in the agent's sandbox.

        This sets up the 'team' remote pointing to the shared git server,
        creates an agent-specific branch, and pushes the initial state.

        Args:
            env: The agent's environment (Modal or Docker)

        Raises:
            RuntimeError: If git configuration fails
        """
        self._logger.debug(f"Setting up git for {self.agent_id}")

        # Configure git user (needed for commits)
        env.execute('git config user.email "agent@cooperbench.local"')
        env.execute(f'git config user.name "{self.agent_id}"')

        # Add shared remote
        result = env.execute(f"git remote add {self.REMOTE_NAME} {self.server_url}")
        if result.get("returncode", 0) != 0:
            # Remote might already exist
            env.execute(f"git remote set-url {self.REMOTE_NAME} {self.server_url}")

        # Create agent's branch
        env.execute(f"git checkout -b {self.agent_id}")

        # Push initial state (first agent initializes the server)
        # Use --force in case branch exists from a previous run
        result = env.execute(f"git push -u {self.REMOTE_NAME} {self.agent_id} --force")
        if result.get("returncode", 0) != 0:
            self._logger.warning(f"Initial push failed: {result.get('output', '')}")

        # Also push main/master as base reference
        env.execute(f"git push {self.REMOTE_NAME} HEAD:refs/heads/main --force 2>/dev/null || true")

        self._initialized = True
        self._logger.debug(f"Git setup complete for {self.agent_id}")

    @property
    def is_initialized(self) -> bool:
        """Whether setup() has been called."""
        return self._initialized
