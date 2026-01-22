"""
Base agent class for execution implementations.

Provides a common interface and lifecycle management for different
execution agents (OpenHands, etc.).
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path

from cooperbench.core.logger import get_logger


class BaseAgent(ABC):
    """Base class for all agent implementations."""

    def __init__(
        self,
        agent_workspace_path: Path,
        prompt: str,
        config: dict | None = None,
    ) -> None:
        """Initialize the agent with workspace and prompt.

        Args:
            agent_workspace_path: Path to the agent workspace directory
            prompt: The task prompt text to use
            config: Optional configuration dictionary with agent-specific settings
        """
        self.agent_workspace_path = agent_workspace_path
        self.prompt = prompt
        self.config = config or {}

        log_dir = self.config.get("log_dir")
        self.logger = get_logger(
            name=f"execution.{self.__class__.__name__}",
            log_dir=Path(log_dir) if log_dir else None,
        )

    def validate(self) -> bool:
        """Validate that the agent workspace directory exists.

        Returns:
            bool: True if validation passes, False otherwise
        """
        if not self.agent_workspace_path.exists():
            self.logger.error(f"Agent workspace directory not found: {self.agent_workspace_path}")
            return False

        if not self.agent_workspace_path.is_dir():
            self.logger.error(f"Agent workspace path is not a directory: {self.agent_workspace_path}")
            return False

        return True

    def setup(self) -> bool:
        """Perform any necessary setup before running the agent.

        Returns:
            bool: True if setup succeeds, False otherwise
        """
        return self.validate()

    def cleanup(self) -> None:
        """Perform any necessary cleanup after running the agent."""
        pass

    @abstractmethod
    def run(self) -> bool:
        """Run the agent on the workspace with the given prompt.

        Returns:
            bool: True if the agent run was successful, False otherwise
        """
        pass

    def execute(self) -> bool:
        """Execute the full agent workflow: setup, run, and cleanup.

        Returns:
            bool: True if the entire execution was successful, False otherwise
        """
        start_time = time.time()
        agent_type = self.__class__.__name__
        run_success = False

        try:
            self.logger.info(f"Starting {agent_type} execution...")
            self.logger.info("Validating agent workspace...")
            if not self.setup():
                self.logger.error("Agent workspace setup failed")
                return False

            self.logger.info("Running agent...")
            run_success = self.run()

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error during agent execution: {str(e)}")
            self.logger.info(f"Execution failed after {duration:.2f}s")
            return False
        finally:
            self.logger.info("Performing cleanup...")
            self.cleanup()
            duration = time.time() - start_time
            status = "succeeded" if run_success else "failed"
            self.logger.info(f"Execution {status} after {duration:.2f}s")

        return run_success
