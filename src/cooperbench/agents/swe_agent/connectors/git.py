"""Git-based code sharing for SWE-agent.

Enables agents in separate containers to share code via git push/pull.
Uses a shared git server (created by cooperbench runner) that agents connect to as a remote.

This is adapted from mini_swe_agent's GitConnector to work with SWE-agent's SWEEnv.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cooperbench.agents.swe_agent.environment.swe_env import SWEEnv


class GitConnector:
    """Configures an agent's SWEEnv for git collaboration.

    After setup(), the agent can use standard git commands:
    - git push team <branch>  - share changes
    - git fetch team          - get other agents' branches
    - git merge team/<agent>  - merge another agent's work
    - git branch -r           - list remote branches
    """

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
        self._logger = logging.getLogger("swe_agent.git_connector")
        self._initialized = False

    def setup(self, env: SWEEnv, working_dir: str = "/workspace/repo") -> None:
        """Configure git remote in the agent's environment.

        This sets up the 'team' remote pointing to the shared git server,
        creates an agent-specific branch, and pushes the initial state.

        Args:
            env: The agent's SWEEnv environment
            working_dir: Path to the repository in the container

        Raises:
            RuntimeError: If git configuration fails
        """
        self._logger.info(f"Setting up git for {self.agent_id}")

        # Helper to run commands (use longer timeout for git operations on large repos)
        def run(cmd: str, timeout: int = 60) -> str:
            return env.communicate(f"cd {working_dir} && {cmd}", timeout=timeout)

        # Git user config (needed for commits)
        run('git config user.email "agent@cooperbench.local"')
        run(f'git config user.name "{self.agent_id}"')

        # Add shared remote
        run(f"git remote add {self.REMOTE_NAME} {self.server_url} 2>/dev/null || git remote set-url {self.REMOTE_NAME} {self.server_url}")

        # Create agent's branch
        run(f"git checkout -b {self.agent_id}")

        # Configure upstream tracking (but don't push yet - too slow for large repos)
        # Agents will push when they have changes to share
        run(f"git config branch.{self.agent_id}.remote {self.REMOTE_NAME}")
        run(f"git config branch.{self.agent_id}.merge refs/heads/{self.agent_id}")

        self._initialized = True
        self._logger.info(f"Git setup complete for {self.agent_id}")

    @property
    def is_initialized(self) -> bool:
        """Whether setup() has been called."""
        return self._initialized
