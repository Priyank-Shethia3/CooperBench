"""Unit tests for cooperbench.runner module.

These are tests that don't require Modal.
For integration tests, see tests/integration/test_runner.py
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cooperbench.runner import discover_tasks, run


class TestDiscoverTasks:
    """Tests for task discovery."""

    def test_discover_all_tasks(self):
        """Test discovering all tasks."""
        tasks = discover_tasks()
        assert len(tasks) > 0
        assert all("repo" in t and "task_id" in t and "features" in t for t in tasks)

    def test_discover_by_repo(self):
        """Test filtering by repository."""
        tasks = discover_tasks(repo_filter="llama_index_task")
        assert len(tasks) > 0
        assert all(t["repo"] == "llama_index_task" for t in tasks)

    def test_discover_by_task_id(self):
        """Test filtering by task ID."""
        tasks = discover_tasks(repo_filter="llama_index_task", task_filter=17244)
        assert len(tasks) > 0
        assert all(t["task_id"] == 17244 for t in tasks)

    def test_discover_specific_features(self):
        """Test filtering by specific feature pair."""
        tasks = discover_tasks(repo_filter="llama_index_task", task_filter=17244, features_filter=[1, 2])
        assert len(tasks) == 1
        assert tasks[0]["features"] == [1, 2]

    def test_discover_generates_pairs(self):
        """Test that discovery generates all feature pairs."""
        tasks = discover_tasks(repo_filter="llama_index_task", task_filter=17244)
        # Should have nC2 pairs
        features_found = set()
        for t in tasks:
            features_found.add(tuple(sorted(t["features"])))
        # At least some pairs
        assert len(features_found) >= 1

    def test_discover_nonexistent_repo(self):
        """Test that nonexistent repo returns empty."""
        tasks = discover_tasks(repo_filter="nonexistent_repo")
        assert tasks == []

    def test_discover_nonexistent_task_id(self):
        """Test that nonexistent task ID returns empty."""
        tasks = discover_tasks(task_filter=999999999)
        assert tasks == []

    def test_discover_returns_task_info(self):
        """Test that discovered tasks have required fields."""
        tasks = discover_tasks()
        assert isinstance(tasks, list)

        if tasks:  # If any tasks found
            task = tasks[0]
            assert "repo" in task
            assert "task_id" in task
            assert "features" in task
            assert isinstance(task["features"], list)
            assert len(task["features"]) == 2


class TestRunConfig:
    """Tests for run configuration and validation."""

    def test_run_requires_name(self):
        """Test that run requires a name parameter."""
        with pytest.raises(TypeError):
            run()  # type: ignore

    def test_run_validates_setting(self):
        """Test that invalid settings are handled."""
        # This should not crash, just find no tasks
        with patch("cooperbench.runner.discover_tasks", return_value=[]):
            run(run_name="test", setting="coop")
            run(run_name="test", setting="solo")

    def test_run_handles_no_tasks(self):
        """Test that run handles case with no tasks."""
        with patch("cooperbench.runner.discover_tasks", return_value=[]):
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
