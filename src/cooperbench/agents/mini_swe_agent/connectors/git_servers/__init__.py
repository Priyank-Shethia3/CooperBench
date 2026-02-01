"""Git servers for inter-agent code collaboration.

Provides pluggable backends for hosting shared git repositories:
- Modal: Cloud-based sandboxes (default)
- Docker: Local containers
- Future: GCP VMs, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cooperbench.agents.mini_swe_agent.connectors.git_servers.base import GitServer
from cooperbench.agents.mini_swe_agent.connectors.git_servers.docker import DockerGitServer
from cooperbench.agents.mini_swe_agent.connectors.git_servers.modal import ModalGitServer

if TYPE_CHECKING:
    import modal

__all__ = ["GitServer", "ModalGitServer", "DockerGitServer", "create_git_server"]


def create_git_server(
    backend: str,
    run_id: str,
    *,
    app: modal.App | None = None,
    timeout: int = 3600,
) -> ModalGitServer | DockerGitServer:
    """Create a git server for the specified backend.

    Args:
        backend: Backend name ("modal" or "docker")
        run_id: Unique run identifier
        app: Modal app (required for modal backend, ignored for docker)
        timeout: Server timeout in seconds

    Returns:
        Git server instance ready to accept connections

    Example:
        # Docker backend
        server = create_git_server("docker", run_id="my-run")

        # Modal backend
        app = modal.App.lookup("cooperbench", create_if_missing=True)
        server = create_git_server("modal", run_id="my-run", app=app)

        # Use the server
        print(server.url)
        # ... agents push/pull ...
        server.cleanup()
    """
    if backend == "docker":
        return DockerGitServer.create(run_id=run_id, timeout=timeout)
    elif backend == "modal":
        if app is None:
            raise ValueError("Modal backend requires 'app' parameter")
        return ModalGitServer.create(app=app, run_id=run_id, timeout=timeout)
    else:
        available = "docker, modal"
        raise ValueError(f"Unknown git server backend: '{backend}'. Available: {available}")
