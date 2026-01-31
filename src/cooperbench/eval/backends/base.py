"""Base protocol for evaluation backends."""

from typing import Protocol


class ExecResult(Protocol):
    """Result of executing a command in a sandbox."""

    @property
    def returncode(self) -> int:
        """Exit code of the command."""
        ...

    def stdout_read(self) -> str:
        """Read stdout output."""
        ...

    def stderr_read(self) -> str:
        """Read stderr output."""
        ...


class Sandbox(Protocol):
    """Abstract sandbox for running commands in isolated containers."""

    def exec(self, *args: str) -> ExecResult:
        """Execute a command and return result.

        Args:
            *args: Command and arguments (e.g., "bash", "-c", "echo hello")

        Returns:
            ExecResult with returncode and output
        """
        ...

    def terminate(self) -> None:
        """Clean up and terminate the sandbox."""
        ...


class EvalBackend(Protocol):
    """Backend for creating evaluation sandboxes."""

    def create_sandbox(
        self,
        image: str,
        timeout: int = 600,
        workdir: str = "/workspace",
    ) -> Sandbox:
        """Create a new sandbox for evaluation.

        Args:
            image: Docker image name
            timeout: Maximum runtime in seconds
            workdir: Working directory inside container

        Returns:
            Sandbox instance
        """
        ...
