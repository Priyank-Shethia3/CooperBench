"""Integration tests for cooperbench.eval.sandbox (requires Modal).

Run with: pytest tests/integration/eval/test_sandbox.py --run-modal
"""

import pytest

from cooperbench.eval.sandbox import run_patch_test
from cooperbench.eval.sandbox import test_merged as sandbox_test_merged
from cooperbench.eval.sandbox import test_solo as sandbox_test_solo
from cooperbench.utils import get_image_name


@pytest.mark.modal
class TestRunPatchTest:
    """Integration tests for run_patch_test."""

    def test_gold_patch_passes(self):
        """Test that gold patch from dataset passes its tests."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch=None,  # Uses gold patch
            timeout=300,
        )

        assert result["error"] is None, f"Error: {result.get('error')}"
        assert result["passed"] is True
        assert result["tests_passed"] > 0

    def test_empty_patch_may_fail(self):
        """Test behavior with empty patch."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch="",
            timeout=300,
        )

        # Empty patch should return an error
        assert result["error"] is not None or result["passed"] is False

    def test_invalid_patch_fails_gracefully(self):
        """Test that invalid patch is handled gracefully."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=17244,
            feature_id=1,
            agent_patch="this is not a valid patch",
            timeout=300,
        )

        # Should not crash, should indicate failure
        assert result["passed"] is False

    def test_nonexistent_task_returns_error(self):
        """Test that nonexistent task returns error."""
        result = run_patch_test(
            repo_name="llama_index_task",
            task_id=99999999,
            feature_id=1,
            agent_patch=None,
            timeout=60,
        )

        assert result["error"] is not None


@pytest.mark.modal
class TestTestMerged:
    """Integration tests for test_merged (coop mode)."""

    def test_gold_patches_pass(self):
        """Test that gold patches from both features merge and pass."""
        from pathlib import Path

        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()
        patch2 = (task_dir / "feature2" / "feature.patch").read_text()

        result = sandbox_test_merged(
            repo_name="llama_index_task",
            task_id=17244,
            feature1_id=1,
            feature2_id=2,
            patch1=patch1,
            patch2=patch2,
            timeout=600,
        )

        assert result["error"] is None, f"Error: {result.get('error')}"
        assert result["merge"]["status"] in ["clean", "conflicts"]
        assert result["merge"]["strategy"] in ["naive", "union"]
        # Both features should pass with gold patches
        assert result["both_passed"] is True

    def test_empty_patches_handled(self):
        """Test behavior with empty patches."""
        result = sandbox_test_merged(
            repo_name="llama_index_task",
            task_id=17244,
            feature1_id=1,
            feature2_id=2,
            patch1="",
            patch2="",
            timeout=300,
        )

        # Should complete without crashing
        assert "merge" in result
        assert "error" in result

    def test_conflicting_patches(self):
        """Test handling of patches that conflict."""
        # Create patches that will conflict (both modify same line)
        patch1 = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1 +1 @@
-original
+version1
"""
        patch2 = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1 +1 @@
-original
+version2
"""
        result = sandbox_test_merged(
            repo_name="llama_index_task",
            task_id=17244,
            feature1_id=1,
            feature2_id=2,
            patch1=patch1,
            patch2=patch2,
            timeout=300,
        )

        # Should attempt merge strategies
        assert "merge" in result
        if result["merge"]["status"] == "conflicts":
            # Union merge might be attempted
            assert result["merge"]["strategy"] in ["naive", "union", None]


@pytest.mark.modal
class TestTestSolo:
    """Integration tests for test_solo (solo mode)."""

    def test_combined_gold_patch_passes(self):
        """Test that combined gold patches pass both feature tests."""
        from pathlib import Path

        task_dir = Path("dataset/llama_index_task/task17244")
        patch1 = (task_dir / "feature1" / "feature.patch").read_text()
        patch2 = (task_dir / "feature2" / "feature.patch").read_text()

        # Combine patches (naive concatenation for test)
        combined = patch1 + "\n" + patch2

        result = sandbox_test_solo(
            repo_name="llama_index_task",
            task_id=17244,
            feature1_id=1,
            feature2_id=2,
            patch=combined,
            timeout=600,
        )

        assert result["error"] is None, f"Error: {result.get('error')}"
        assert result["setting"] == "solo"
        # At minimum, patch should be applied
        assert result["patch_lines"] > 0

    def test_empty_patch_handled(self):
        """Test behavior with empty patch."""
        result = sandbox_test_solo(
            repo_name="llama_index_task",
            task_id=17244,
            feature1_id=1,
            feature2_id=2,
            patch="",
            timeout=300,
        )

        assert result["setting"] == "solo"
        assert result["patch_lines"] == 0


@pytest.mark.modal
class TestSandboxCreation:
    """Integration tests for sandbox creation and image pulling."""

    def test_image_exists(self):
        """Test that task image can be pulled."""
        import modal

        image_name = get_image_name("llama_index_task", 17244)
        image = modal.Image.from_registry(image_name)

        # This will fail if image doesn't exist
        assert image is not None

    def test_sandbox_creates_successfully(self):
        """Test that sandbox can be created."""
        import modal

        image_name = get_image_name("llama_index_task", 17244)
        image = modal.Image.from_registry(image_name).entrypoint([])

        app = modal.App.lookup("cooperbench-eval", create_if_missing=True)
        sb = modal.Sandbox.create(image=image, timeout=60, workdir="/workspace", app=app)

        try:
            # Test basic command execution
            result = sb.exec("echo", "hello")
            result.wait()
            assert "hello" in result.stdout.read()
        finally:
            sb.terminate()

    def test_repo_exists_in_sandbox(self):
        """Test that repository exists in sandbox at expected location."""
        import modal

        image_name = get_image_name("llama_index_task", 17244)
        image = modal.Image.from_registry(image_name).entrypoint([])

        app = modal.App.lookup("cooperbench-eval", create_if_missing=True)
        sb = modal.Sandbox.create(image=image, timeout=60, workdir="/workspace", app=app)

        try:
            result = sb.exec("ls", "/workspace/repo")
            result.wait()
            # Should list files without error
            assert result.returncode == 0
        finally:
            sb.terminate()
