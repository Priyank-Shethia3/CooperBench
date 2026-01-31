"""Tests for cooperbench sandbox (patch testing, merging)."""

import pytest

from cooperbench.sandbox import run_patch_test


class TestPatchApplication:
    """Tests for patch application and testing."""

    @pytest.mark.modal
    def test_gold_patch_passes(self):
        """Test that applying a gold patch passes tests."""
        # Use a known task with a simple gold patch
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch=None,  # Uses gold patch from dataset
        )

        assert "passed" in result
        # Gold patch should pass
        assert result["passed"] is True

    @pytest.mark.modal
    def test_empty_patch_may_fail(self):
        """Test that an empty patch may fail (no changes)."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch="",  # Empty patch
        )

        assert "passed" in result
        # Empty patch likely fails unless feature is already implemented
        # (We just test the mechanism works, not the result)

    @pytest.mark.modal
    def test_invalid_patch_fails_gracefully(self):
        """Test that an invalid patch fails gracefully."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch="this is not a valid patch",
        )

        assert "passed" in result
        assert "error" in result or result["passed"] is False
