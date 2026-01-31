"""Unit tests for cooperbench.agents.registry."""

import pytest

from cooperbench.agents import AgentRunner, get_runner, list_agents, register


class TestListAgents:
    """Tests for list_agents function."""

    def test_returns_list(self):
        """Test that list_agents returns a list."""
        agents = list_agents()
        assert isinstance(agents, list)

    def test_contains_mini_swe_agent(self):
        """Test that mini_swe_agent is registered."""
        agents = list_agents()
        assert "mini_swe_agent" in agents

    def test_not_empty(self):
        """Test that at least one agent is registered."""
        agents = list_agents()
        assert len(agents) > 0


class TestGetRunner:
    """Tests for get_runner function."""

    def test_returns_runner_instance(self):
        """Test that get_runner returns an object with run method."""
        runner = get_runner("mini_swe_agent")
        # AgentRunner is a Protocol, so we check it has the required method
        assert hasattr(runner, "run")
        assert callable(runner.run)

    def test_raises_for_unknown_agent(self):
        """Test that unknown agent name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            get_runner("nonexistent_agent_xyz")

    def test_runner_has_run_method(self):
        """Test that returned runner has a run method."""
        runner = get_runner("mini_swe_agent")
        assert hasattr(runner, "run")
        assert callable(runner.run)


class TestRegisterDecorator:
    """Tests for @register decorator."""

    def test_register_new_agent(self):
        """Test registering a new agent class."""

        @register("test_agent_unique_name_xyz")
        class TestAgent(AgentRunner):
            def run(self, **kwargs):
                return None

        # Should be retrievable
        agents = list_agents()
        assert "test_agent_unique_name_xyz" in agents

    def test_registered_agent_is_retrievable(self):
        """Test that registered agent can be retrieved."""

        @register("test_agent_retrievable_xyz")
        class TestAgent(AgentRunner):
            def run(self, **kwargs):
                return None

        runner = get_runner("test_agent_retrievable_xyz")
        assert isinstance(runner, TestAgent)


class TestMiniSweAgentAdapter:
    """Tests for mini_swe_agent adapter."""

    def test_adapter_exists(self):
        """Test that mini_swe_agent adapter exists."""
        runner = get_runner("mini_swe_agent")
        assert runner is not None

    def test_adapter_run_signature(self):
        """Test that adapter run method has expected parameters."""
        import inspect

        runner = get_runner("mini_swe_agent")
        sig = inspect.signature(runner.run)
        params = list(sig.parameters.keys())

        # Should have key parameters
        assert "task" in params
        assert "image" in params
        assert "agent_id" in params
        assert "model_name" in params
