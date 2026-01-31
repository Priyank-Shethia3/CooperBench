"""Tests for cooperbench.agents.registry module."""

import inspect

import pytest

from cooperbench.agents import AgentResult, get_runner, list_agents, register


class TestAgentRegistry:
    """Tests for agent registry."""

    def test_list_agents_returns_list(self):
        """Test that list_agents returns a list."""
        agents = list_agents()
        assert isinstance(agents, list)

    def test_mini_swe_agent_registered(self):
        """Test that mini_swe_agent is registered."""
        agents = list_agents()
        assert "mini_swe_agent" in agents

    def test_get_runner_returns_instance(self):
        """Test that get_runner returns an instance."""
        runner = get_runner("mini_swe_agent")
        assert runner is not None
        assert hasattr(runner, "run")

    def test_get_unknown_agent_raises(self):
        """Test that getting an unknown agent raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            get_runner("nonexistent_agent")

    def test_register_decorator(self):
        """Test the register decorator."""

        @register("test_agent_temp")
        class TestAgentRunner:
            def run(self, task, image, **kwargs) -> AgentResult:
                return AgentResult(status="Test", patch="", cost=0, steps=0)

        assert "test_agent_temp" in list_agents()
        runner = get_runner("test_agent_temp")
        assert runner is not None


class TestMiniSweAgentAdapter:
    """Tests for MiniSweAgent adapter (unit tests, no Modal)."""

    def test_adapter_has_run_method(self):
        """Test that adapter has run method."""
        runner = get_runner("mini_swe_agent")
        assert hasattr(runner, "run")
        assert callable(runner.run)

    def test_adapter_run_signature(self):
        """Test that run method has correct parameters."""
        runner = get_runner("mini_swe_agent")
        sig = inspect.signature(runner.run)
        params = list(sig.parameters.keys())

        # Required params
        assert "task" in params
        assert "image" in params

        # Optional params
        assert "agent_id" in params
        assert "model_name" in params
        assert "agents" in params
        assert "comm_url" in params
