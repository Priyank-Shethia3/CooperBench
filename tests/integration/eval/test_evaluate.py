"""Integration tests for cooperbench.eval.evaluate (requires Modal).

Run with: pytest tests/integration/eval/test_evaluate.py --run-modal
"""

import json
import os
from pathlib import Path

import pytest

from cooperbench.eval import evaluate


@pytest.mark.modal
class TestEvaluateE2E:
    """End-to-end tests for evaluate function."""

    def test_evaluate_completed_run(self, tmp_path):
        """Test evaluating a completed run with real patches."""
        os.chdir(tmp_path)

        # Create mock completed run with gold patches
        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()
        patch2 = (task_dir / "feature2" / "feature.patch").read_text()

        run_dir = tmp_path / "logs" / "test-eval" / "coop" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)

        # Write patches
        (run_dir / "agent1.patch").write_text(patch1)
        (run_dir / "agent2.patch").write_text(patch2)
        (run_dir / "result.json").write_text(json.dumps({"setting": "coop", "status": "completed"}))

        # Run evaluation
        evaluate(run_name="test-eval", concurrency=1)

        # Check eval.json was created
        eval_file = run_dir / "eval.json"
        assert eval_file.exists()

        eval_data = json.loads(eval_file.read_text())
        assert "merge" in eval_data
        assert "feature1" in eval_data
        assert "feature2" in eval_data
        assert "both_passed" in eval_data

    def test_evaluate_solo_run(self, tmp_path):
        """Test evaluating a solo run."""
        os.chdir(tmp_path)

        # Create mock solo run
        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()
        patch2 = (task_dir / "feature2" / "feature.patch").read_text()

        run_dir = tmp_path / "logs" / "test-solo" / "solo" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)

        # Write combined patch
        (run_dir / "solo.patch").write_text(patch1 + "\n" + patch2)
        (run_dir / "result.json").write_text(json.dumps({"setting": "solo", "status": "completed"}))

        # Run evaluation
        evaluate(run_name="test-solo", concurrency=1)

        # Check eval.json was created
        eval_file = run_dir / "eval.json"
        assert eval_file.exists()

        eval_data = json.loads(eval_file.read_text())
        assert eval_data["setting"] == "solo"

    def test_evaluate_creates_summary(self, tmp_path):
        """Test that evaluate creates summary file."""
        os.chdir(tmp_path)

        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()
        patch2 = (task_dir / "feature2" / "feature.patch").read_text()

        run_dir = tmp_path / "logs" / "test-summary" / "coop" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)

        (run_dir / "agent1.patch").write_text(patch1)
        (run_dir / "agent2.patch").write_text(patch2)
        (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))

        evaluate(run_name="test-summary", concurrency=1)

        # Check summary was created
        summary_file = tmp_path / "logs" / "test-summary" / "eval_summary.json"
        assert summary_file.exists()

        summary = json.loads(summary_file.read_text())
        assert "total_runs" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "pass_rate" in summary

    def test_evaluate_skip_already_evaluated(self, tmp_path):
        """Test that already evaluated runs are skipped without force."""
        os.chdir(tmp_path)

        run_dir = tmp_path / "logs" / "test-skip" / "coop" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)

        (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))
        (run_dir / "agent1.patch").write_text("")
        (run_dir / "agent2.patch").write_text("")

        # Pre-create eval.json
        existing_eval = {"previously": "evaluated", "both_passed": True}
        (run_dir / "eval.json").write_text(json.dumps(existing_eval))

        evaluate(run_name="test-skip", concurrency=1)

        # Should not be overwritten
        eval_data = json.loads((run_dir / "eval.json").read_text())
        assert eval_data.get("previously") == "evaluated"

    def test_evaluate_force_reevaluate(self, tmp_path):
        """Test that force=True re-evaluates existing runs."""
        os.chdir(tmp_path)

        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()

        run_dir = tmp_path / "logs" / "test-force" / "coop" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)

        (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))
        (run_dir / "agent1.patch").write_text(patch1)
        (run_dir / "agent2.patch").write_text(patch1)

        # Pre-create eval.json
        (run_dir / "eval.json").write_text(json.dumps({"old": True}))

        evaluate(run_name="test-force", force=True, concurrency=1)

        # Should be overwritten with new evaluation
        eval_data = json.loads((run_dir / "eval.json").read_text())
        assert "old" not in eval_data
        assert "merge" in eval_data or "error" in eval_data
