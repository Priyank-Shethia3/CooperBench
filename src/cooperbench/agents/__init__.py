"""Pluggable agent frameworks for CooperBench.

This module provides a common interface for different agent frameworks
(mini_swe, swe_agent, etc.) to be used interchangeably with the benchmark.

Usage:
    from cooperbench.agents import get_runner, AgentResult

    runner = get_runner("mini_swe")
    result = runner.run(task="...", image="...", model_name="gpt-4o")
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AgentResult:
    """Standardized output from any agent framework."""

    status: str
    """Exit status: 'Submitted', 'Error', 'LimitsExceeded', etc."""

    patch: str
    """Git diff of all changes made by the agent."""

    cost: float
    """Total LLM cost in USD."""

    steps: int
    """Number of LLM calls made."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    """Full conversation trajectory for analysis."""

    error: str | None = None
    """Error message if status is 'Error'."""


class AgentRunner(Protocol):
    """Interface that all agent framework adapters must implement."""

    def run(
        self,
        task: str,
        image: str,
        *,
        agent_id: str = "agent",
        model_name: str = "gpt-4o",
        # Collaboration options (adapters can ignore if not supported)
        agents: list[str] | None = None,
        comm_url: str | None = None,
        git_server_url: str | None = None,
        git_enabled: bool = False,
        messaging_enabled: bool = True,
        # Agent-specific config
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run agent on a task.

        Args:
            task: The task description (feature spec)
            image: Docker image with the codebase
            agent_id: Unique identifier for this agent
            model_name: LLM model to use (e.g., "gpt-4o", "claude-3-opus")
            agents: List of all agent IDs (for collaboration)
            comm_url: Redis URL for inter-agent messaging
            git_server_url: Git server URL for code sharing
            git_enabled: Whether git collaboration is enabled
            messaging_enabled: Whether messaging is enabled
            config: Agent-specific configuration

        Returns:
            AgentResult with status, patch, cost, steps, messages
        """
        ...


# Import registry functions for convenience
from cooperbench.agents.registry import get_runner, list_agents, register

__all__ = [
    "AgentResult",
    "AgentRunner",
    "get_runner",
    "list_agents",
    "register",
]
