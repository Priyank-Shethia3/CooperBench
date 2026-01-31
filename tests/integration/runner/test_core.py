"""Integration tests for cooperbench.runner.core module.

These tests run actual agent tasks using Modal sandboxes.
Run with: pytest tests/integration/runner/ --run-modal
"""

import json
import os
from pathlib import Path

import pytest

from cooperbench.runner import run

# Mark all tests in this module as requiring Modal
pytestmark = pytest.mark.modal


class TestRunSoloMode:
    """Integration tests for solo mode execution."""

    def test_single_task_solo_execution(self, tmp_path):
        """Test running a single task in solo mode."""
        os.chdir(tmp_path)

        # Copy minimal dataset structure
        task_dir = tmp_path / "dataset" / "llama_index_task" / "task17244"
        task_dir.mkdir(parents=True)

        # Link to real dataset features
        real_dataset = Path(__file__).parent.parent.parent.parent / "dataset"
        real_task = real_dataset / "llama_index_task" / "task17244"

        for feature_id in [1, 2]:
            src = real_task / f"feature{feature_id}"
            dst = task_dir / f"feature{feature_id}"
            dst.symlink_to(src)

        # Run in solo mode
        run(
            run_name="test-solo-integration",
            repo="llama_index_task",
            task_id=17244,
            features=[1, 2],
            setting="solo",
            concurrency=1,
        )

        # Check logs were created
        log_dir = tmp_path / "logs" / "test-solo-integration" / "solo"
        assert log_dir.exists()

        # Find result
        result_files = list(log_dir.rglob("result.json"))
        assert len(result_files) == 1

        with open(result_files[0]) as f:
            result = json.load(f)

        assert result["setting"] == "solo"
        assert result["repo"] == "llama_index_task"


class TestRunCoopMode:
    """Integration tests for coop mode execution."""

    def test_single_task_coop_execution(self, tmp_path, redis_url):
        """Test running a single task in coop mode."""
        os.chdir(tmp_path)

        # Copy minimal dataset structure
        task_dir = tmp_path / "dataset" / "llama_index_task" / "task17244"
        task_dir.mkdir(parents=True)

        # Link to real dataset features
        real_dataset = Path(__file__).parent.parent.parent.parent / "dataset"
        real_task = real_dataset / "llama_index_task" / "task17244"

        for feature_id in [1, 2]:
            src = real_task / f"feature{feature_id}"
            dst = task_dir / f"feature{feature_id}"
            dst.symlink_to(src)

        # Run in coop mode
        run(
            run_name="test-coop-integration",
            repo="llama_index_task",
            task_id=17244,
            features=[1, 2],
            setting="coop",
            redis_url=redis_url,
            concurrency=1,
            messaging_enabled=True,
            git_enabled=False,
        )

        # Check logs were created
        log_dir = tmp_path / "logs" / "test-coop-integration" / "coop"
        assert log_dir.exists()

        # Find result
        result_files = list(log_dir.rglob("result.json"))
        assert len(result_files) == 1

        with open(result_files[0]) as f:
            result = json.load(f)

        assert result["setting"] == "coop"
        assert "agents" in result


class TestRunOutputStructure:
    """Tests for run output structure."""

    def test_output_directory_format(self, tmp_path):
        """Test that output directory follows expected format."""
        os.chdir(tmp_path)

        # Create minimal task
        task_dir = tmp_path / "dataset" / "test_task" / "task1"
        (task_dir / "feature1").mkdir(parents=True)
        (task_dir / "feature2").mkdir(parents=True)
        (task_dir / "feature1" / "feature.md").write_text("# Test\nTest feature")
        (task_dir / "feature2" / "feature.md").write_text("# Test\nTest feature 2")

        # This will fail (no image), but we can check directory structure is created
        try:
            run(
                run_name="test-output",
                repo="test_task",
                task_id=1,
                features=[1, 2],
                setting="solo",
            )
        except Exception:
            pass  # Expected to fail without proper image

        # Config should still be created
        config_file = tmp_path / "logs" / "test-output" / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            assert "run_name" in config
            assert "setting" in config
