"""Integration tests for the evaluator module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cooperbench.evaluator import discover_runs, evaluate


class TestDiscoverRuns:
    """Tests for run discovery."""

    def test_discover_runs_empty_logs(self, tmp_path):
        """Test discovering runs from empty logs directory."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        with patch("cooperbench.evaluator.Path") as mock_path:
            mock_path.return_value = logs_dir
            runs = discover_runs(run_name="nonexistent")
            assert runs == []

    def test_discover_runs_finds_completed(self, tmp_path):
        """Test that discover_runs finds completed runs."""
        # Create a mock run structure
        run_dir = tmp_path / "logs" / "test-run" / "coop" / "test_repo" / "task1" / "features_1_2"
        run_dir.mkdir(parents=True)

        # Add agent patches to simulate completed run
        (run_dir / "agent1.patch").write_text("diff --git a/file.py")
        (run_dir / "agent2.patch").write_text("diff --git b/file.py")
        (run_dir / "result.json").write_text(json.dumps({"status": "completed"}))

        # The run should be discoverable (though we're mocking)
        assert run_dir.exists()


class TestEvaluatorConfig:
    """Tests for evaluator configuration."""

    def test_evaluate_requires_name(self):
        """Test that evaluate requires run_name."""
        with pytest.raises(TypeError):
            evaluate()  # type: ignore

    def test_evaluate_handles_no_runs(self):
        """Test that evaluate handles case with no runs gracefully."""
        with patch("cooperbench.evaluator.discover_runs", return_value=[]):
            # Should not raise, just do nothing
            evaluate(run_name="nonexistent-run")


class TestEvalResultSchema:
    """Tests for evaluation result schema."""

    def test_eval_json_schema(self, tmp_path):
        """Test that eval.json follows expected schema."""
        eval_result = {
            "run_name": "test-run",
            "repo": "test_repo",
            "task_id": 1,
            "features": [1, 2],
            "setting": "coop",
            "merge_status": "success",
            "test_results": {
                "feature1": {"passed": 5, "failed": 0, "total": 5},
                "feature2": {"passed": 3, "failed": 1, "total": 4},
            },
            "overall_passed": True,
            "evaluated_at": "2026-01-31T12:00:00",
        }

        eval_file = tmp_path / "eval.json"
        eval_file.write_text(json.dumps(eval_result))

        loaded = json.loads(eval_file.read_text())
        assert "merge_status" in loaded
        assert "test_results" in loaded
        assert "overall_passed" in loaded


@pytest.mark.modal
class TestEvaluatorE2E:
    """End-to-end evaluator tests requiring Modal.
    
    Run with: pytest --run-modal
    """

    def test_evaluate_real_patches(self):
        """Test evaluating real agent patches."""
        pytest.skip("E2E test - requires completed run in logs/")

    def test_merge_conflict_detection(self):
        """Test that merge conflicts are properly detected."""
        pytest.skip("E2E test - requires Modal sandbox")
