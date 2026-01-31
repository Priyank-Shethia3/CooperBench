"""Unit tests for cooperbench.evaluator module.

These are tests that don't require Modal.
For integration tests, see tests/integration/test_evaluator.py
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cooperbench.evaluator import _discover_runs_in_dir, discover_runs, evaluate


class TestDiscoverRuns:
    """Tests for discover_runs."""

    def test_discover_runs_nonexistent_dir(self, chdir_tmp):
        """Test discovering runs from nonexistent directory."""
        runs = discover_runs(run_name="nonexistent")
        assert runs == []

    def test_discover_runs_empty_run_dir(self, chdir_tmp):
        """Test discovering runs from empty run directory."""
        log_dir = chdir_tmp / "logs" / "my-run"
        log_dir.mkdir(parents=True)

        runs = discover_runs(run_name="my-run")
        assert runs == []

    def test_discover_coop_structure(self, chdir_tmp):
        """Test discovering runs with coop structure."""
        # Create coop structure: logs/{run}/coop/{repo}/task{id}/f{x}_f{y}/
        run_dir = chdir_tmp / "logs" / "test-run" / "coop" / "llama_index_task" / "17244" / "f1_f2"
        run_dir.mkdir(parents=True)
        (run_dir / "result.json").write_text(json.dumps({"setting": "coop", "status": "done"}))

        runs = discover_runs(run_name="test-run")
        assert len(runs) == 1
        assert runs[0]["repo"] == "llama_index_task"
        assert runs[0]["task_id"] == 17244
        assert runs[0]["features"] == [1, 2]
        assert runs[0]["setting"] == "coop"

    def test_discover_solo_structure(self, chdir_tmp):
        """Test discovering runs with solo structure."""
        run_dir = chdir_tmp / "logs" / "test-run" / "solo" / "dspy_task" / "123" / "f3_f4"
        run_dir.mkdir(parents=True)
        (run_dir / "result.json").write_text(json.dumps({"setting": "solo", "status": "done"}))

        runs = discover_runs(run_name="test-run")
        assert len(runs) == 1
        assert runs[0]["repo"] == "dspy_task"
        assert runs[0]["task_id"] == 123
        assert runs[0]["features"] == [3, 4]
        assert runs[0]["setting"] == "solo"

    def test_discover_multiple_runs(self, chdir_tmp):
        """Test discovering multiple runs."""
        base = chdir_tmp / "logs" / "multi-run" / "coop"

        # Create 3 different runs
        for repo, task_id, features in [
            ("repo1_task", 1, "f1_f2"),
            ("repo1_task", 1, "f2_f3"),
            ("repo2_task", 2, "f1_f2"),
        ]:
            run_dir = base / repo / str(task_id) / features
            run_dir.mkdir(parents=True)
            (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = discover_runs(run_name="multi-run")
        assert len(runs) == 3

    def test_discover_filters_by_repo(self, chdir_tmp):
        """Test filtering by repository."""
        base = chdir_tmp / "logs" / "run" / "coop"

        for repo in ["repo1_task", "repo2_task"]:
            run_dir = base / repo / "1" / "f1_f2"
            run_dir.mkdir(parents=True)
            (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = discover_runs(run_name="run", repo_filter="repo1_task")
        assert len(runs) == 1
        assert runs[0]["repo"] == "repo1_task"

    def test_discover_filters_by_task_id(self, chdir_tmp):
        """Test filtering by task ID."""
        base = chdir_tmp / "logs" / "run" / "coop" / "repo_task"

        for task_id in ["100", "200"]:
            run_dir = base / task_id / "f1_f2"
            run_dir.mkdir(parents=True)
            (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = discover_runs(run_name="run", task_filter=100)
        assert len(runs) == 1
        assert runs[0]["task_id"] == 100

    def test_discover_filters_by_features(self, chdir_tmp):
        """Test filtering by feature pair."""
        base = chdir_tmp / "logs" / "run" / "coop" / "repo_task" / "1"

        for features in ["f1_f2", "f1_f3", "f2_f3"]:
            run_dir = base / features
            run_dir.mkdir(parents=True)
            (run_dir / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = discover_runs(run_name="run", features_filter=[1, 3])
        assert len(runs) == 1
        assert set(runs[0]["features"]) == {1, 3}

    def test_discover_skips_non_task_dirs(self, chdir_tmp):
        """Test that non-repo directories are skipped."""
        base = chdir_tmp / "logs" / "run" / "coop"

        # Valid repo dir
        valid = base / "valid_task" / "1" / "f1_f2"
        valid.mkdir(parents=True)
        (valid / "result.json").write_text(json.dumps({"setting": "coop"}))

        # Invalid - doesn't end with _task
        invalid = base / "invalid_repo" / "1" / "f1_f2"
        invalid.mkdir(parents=True)
        (invalid / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = discover_runs(run_name="run")
        assert len(runs) == 1
        assert runs[0]["repo"] == "valid_task"

    def test_discover_skips_incomplete_runs(self, chdir_tmp):
        """Test that runs without result.json are skipped."""
        base = chdir_tmp / "logs" / "run" / "coop" / "repo_task" / "1"

        # Complete run
        complete = base / "f1_f2"
        complete.mkdir(parents=True)
        (complete / "result.json").write_text(json.dumps({"setting": "coop"}))

        # Incomplete run - no result.json
        incomplete = base / "f3_f4"
        incomplete.mkdir(parents=True)

        runs = discover_runs(run_name="run")
        assert len(runs) == 1
        assert runs[0]["features"] == [1, 2]


class TestDiscoverRunsInDir:
    """Tests for _discover_runs_in_dir helper."""

    def test_discover_in_dir_basic(self, tmp_path):
        """Test basic discovery in a directory."""
        base = tmp_path / "repo_task" / "123" / "f5_f6"
        base.mkdir(parents=True)
        (base / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting="coop",
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        assert runs[0]["repo"] == "repo_task"
        assert runs[0]["task_id"] == 123
        assert runs[0]["features"] == [5, 6]

    def test_discover_in_dir_infers_setting_from_result(self, tmp_path):
        """Test setting inference from result.json."""
        base = tmp_path / "repo_task" / "1" / "f1_f2"
        base.mkdir(parents=True)
        (base / "result.json").write_text(json.dumps({"setting": "solo"}))

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting=None,  # Should infer from result.json
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        assert runs[0]["setting"] == "solo"

    def test_discover_in_dir_defaults_to_coop(self, tmp_path):
        """Test setting defaults to coop when not in result.json."""
        base = tmp_path / "repo_task" / "1" / "f1_f2"
        base.mkdir(parents=True)
        (base / "result.json").write_text(json.dumps({}))  # No setting field

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting=None,
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        # Defaults to coop when setting is None and no solo.patch
        assert runs[0]["setting"] == "coop"

    def test_discover_in_dir_infers_solo_from_patch(self, tmp_path):
        """Test setting inference from solo.patch presence."""
        base = tmp_path / "repo_task" / "1" / "f1_f2"
        base.mkdir(parents=True)
        # result.json with setting=None (not just missing)
        (base / "result.json").write_text(json.dumps({"setting": None}))
        (base / "solo.patch").write_text("diff...")

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting=None,
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        assert runs[0]["setting"] == "solo"

    def test_discover_in_dir_skips_invalid_task_id(self, tmp_path):
        """Test that non-numeric task IDs are skipped."""
        # Valid
        valid = tmp_path / "repo_task" / "123" / "f1_f2"
        valid.mkdir(parents=True)
        (valid / "result.json").write_text(json.dumps({"setting": "coop"}))

        # Invalid - non-numeric task ID
        invalid = tmp_path / "repo_task" / "abc" / "f1_f2"
        invalid.mkdir(parents=True)
        (invalid / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting="coop",
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        assert runs[0]["task_id"] == 123

    def test_discover_in_dir_skips_invalid_features(self, tmp_path):
        """Test that invalid feature strings are skipped."""
        # Valid
        valid = tmp_path / "repo_task" / "1" / "f1_f2"
        valid.mkdir(parents=True)
        (valid / "result.json").write_text(json.dumps({"setting": "coop"}))

        # Invalid - bad feature format
        invalid = tmp_path / "repo_task" / "1" / "invalid"
        invalid.mkdir(parents=True)
        (invalid / "result.json").write_text(json.dumps({"setting": "coop"}))

        # Invalid - only one feature
        single = tmp_path / "repo_task" / "1" / "f1"
        single.mkdir(parents=True)
        (single / "result.json").write_text(json.dumps({"setting": "coop"}))

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting="coop",
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1
        assert runs[0]["features"] == [1, 2]

    def test_discover_in_dir_skips_files(self, tmp_path):
        """Test that files (not directories) are skipped."""
        # Valid directory
        valid = tmp_path / "repo_task" / "1" / "f1_f2"
        valid.mkdir(parents=True)
        (valid / "result.json").write_text(json.dumps({"setting": "coop"}))

        # File that looks like a repo
        (tmp_path / "fake_task").write_text("not a directory")

        runs = _discover_runs_in_dir(
            base_dir=tmp_path,
            setting="coop",
            repo_filter=None,
            task_filter=None,
            features_filter=None,
        )
        assert len(runs) == 1


class TestEvaluate:
    """Tests for evaluate function."""

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
