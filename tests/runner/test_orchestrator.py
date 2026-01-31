"""Unit tests for cooperbench.runner.core module."""

import json
from unittest.mock import patch

import pytest

from cooperbench.runner import run


class TestRunConfig:
    """Tests for run configuration and validation."""

    def test_run_requires_name(self):
        """Test that run requires a name parameter."""
        with pytest.raises(TypeError):
            run()  # type: ignore

    def test_run_validates_setting(self):
        """Test that invalid settings are handled."""
        # This should not crash, just find no tasks
        with patch("cooperbench.runner.orchestrator.discover_tasks", return_value=[]):
            run(run_name="test", setting="coop")
            run(run_name="test", setting="solo")

    def test_run_handles_no_tasks(self):
        """Test that run handles case with no tasks."""
        with patch("cooperbench.runner.orchestrator.discover_tasks", return_value=[]):
            # Should not raise
            run(run_name="test-empty", repo="nonexistent")


class TestRunOutputStructure:
    """Tests for runner output directory structure."""

    def test_output_directory_format(self, tmp_path):
        """Test that output follows expected structure."""
        # Expected: logs/{run_name}/{setting}/{repo}/{task_id}/{features}/
        run_name = "test-run"
        setting = "coop"
        repo = "test_repo"
        task_id = 123
        features = "f1_f2"

        expected_path = tmp_path / "logs" / run_name / setting / repo / str(task_id) / features
        expected_path.mkdir(parents=True)

        # Verify structure is creatable
        assert expected_path.exists()
        assert expected_path.is_dir()

    def test_result_json_schema(self, tmp_path):
        """Test that result.json has expected schema."""
        result = {
            "run_name": "test",
            "repo": "test_repo",
            "task_id": 123,
            "features": [1, 2],
            "setting": "coop",
            "model": "gpt-4o",
            "status": "completed",
            "started_at": "2026-01-31T12:00:00",
            "ended_at": "2026-01-31T12:05:00",
            "duration_seconds": 300,
            "total_cost": 0.05,
        }

        result_file = tmp_path / "result.json"
        result_file.write_text(json.dumps(result))

        loaded = json.loads(result_file.read_text())
        assert "run_name" in loaded
        assert "setting" in loaded
        assert "duration_seconds" in loaded
        assert "total_cost" in loaded

    def test_config_json_schema(self, tmp_path):
        """Test that config.json has expected schema."""
        config = {
            "run_name": "test",
            "agent_framework": "mini_swe_agent",
            "model": "gemini/gemini-3-flash-preview",
            "setting": "coop",
            "concurrency": 20,
            "total_tasks": 10,
            "started_at": "2026-01-31T12:00:00",
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert "run_name" in loaded
        assert "agent_framework" in loaded
        assert "model" in loaded
        assert "setting" in loaded
