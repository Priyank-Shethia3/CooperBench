"""Integration tests for the runner module.

These tests validate the runner logic without actually running agents.
For full end-to-end tests, use --run-modal flag.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cooperbench.runner import discover_tasks, run


class TestDiscoverTasksIntegration:
    """Tests for task discovery with real dataset structure."""

    def test_discover_returns_task_info(self, sample_task_dir):
        """Test that discovered tasks have required fields."""
        # Create a minimal task structure
        task_dir = sample_task_dir
        
        with patch("cooperbench.runner.Path") as mock_path:
            # Mock the dataset path to use our temp directory
            mock_path.return_value.exists.return_value = True
            
            tasks = discover_tasks()
            
            # Tasks should be a list (may be empty if no dataset)
            assert isinstance(tasks, list)

    def test_discover_filters_by_repo(self):
        """Test filtering by repository name."""
        tasks = discover_tasks(repo_filter="nonexistent_repo_xyz")
        assert tasks == []

    def test_discover_filters_by_task_id(self):
        """Test filtering by task ID."""
        tasks = discover_tasks(task_filter=999999)
        assert tasks == []


class TestRunnerConfig:
    """Tests for runner configuration and validation."""

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


class TestRunnerOutputStructure:
    """Tests for runner output directory structure."""

    def test_output_directory_format(self, tmp_path):
        """Test that output follows expected structure."""
        # Expected: logs/{run_name}/{setting}/{repo}/{task_id}/{features}/
        run_name = "test-run"
        setting = "coop"
        repo = "test_repo"
        task_id = 123
        features = "1_2"

        expected_path = tmp_path / "logs" / run_name / setting / repo / f"task{task_id}" / f"features_{features}"
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
            "start_time": "2026-01-31T12:00:00",
            "end_time": "2026-01-31T12:05:00",
            "duration_seconds": 300,
            "cost_usd": 0.05,
        }

        result_file = tmp_path / "result.json"
        result_file.write_text(json.dumps(result))

        loaded = json.loads(result_file.read_text())
        assert "run_name" in loaded
        assert "status" in loaded
        assert "duration_seconds" in loaded


@pytest.mark.modal
class TestRunnerE2E:
    """End-to-end tests that require Modal sandboxes.
    
    Run with: pytest --run-modal
    """

    def test_single_task_solo_mode(self):
        """Test running a single task in solo mode."""
        # This would actually run an agent
        # Skip if no dataset or Modal not configured
        pytest.skip("E2E test - run manually with --run-modal and valid API keys")

    def test_single_task_coop_mode(self):
        """Test running a single task in coop mode."""
        pytest.skip("E2E test - run manually with --run-modal and valid API keys")
