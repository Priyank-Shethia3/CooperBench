"""Tests for cooperbench.utils module."""

import threading
from unittest.mock import MagicMock

from cooperbench.utils import (
    IMAGE_PREFIX,
    REGISTRY,
    ResourceTracker,
    get_image_name,
)


class TestGetImageName:
    """Tests for get_image_name utility."""

    def test_basic_image_name(self):
        """Test basic image name generation."""
        name = get_image_name("llama_index_task", 17244)
        assert "llama-index" in name
        assert "17244" in name

    def test_image_name_format(self):
        """Test image name format."""
        name = get_image_name("test_repo_task", 123)
        # Should be Docker Hub format
        assert "/" in name
        assert ":" in name

    def test_different_repos(self):
        """Test different repository names."""
        repos = [
            "llama_index_task",
            "pallets_click_task",
            "dspy_task",
        ]

        names = [get_image_name(repo, 1) for repo in repos]

        # All should be unique
        assert len(set(names)) == len(names)

    def test_different_task_ids(self):
        """Test different task IDs produce different names."""
        name1 = get_image_name("test_task", 1)
        name2 = get_image_name("test_task", 2)

        assert name1 != name2
        assert "1" in name1 or "task1" in name1
        assert "2" in name2 or "task2" in name2

    def test_removes_task_suffix(self):
        """Test that _task suffix is removed."""
        name = get_image_name("llama_index_task", 123)
        assert "task" not in name.split("/")[-1].split(":")[0]
        assert "llama-index" in name

    def test_converts_underscores_to_hyphens(self):
        """Test underscores are converted to hyphens."""
        name = get_image_name("some_repo_name_task", 1)
        # Only the repo part (not registry/prefix)
        repo_part = name.split("/")[-1].split(":")[0]
        assert "_" not in repo_part

    def test_task_id_in_tag(self):
        """Test task ID appears in the tag."""
        name = get_image_name("repo_task", 42)
        assert ":task42" in name

    def test_registry_and_prefix(self):
        """Test registry and prefix are included."""
        name = get_image_name("test_task", 1)
        assert name.startswith(f"{REGISTRY}/{IMAGE_PREFIX}")


class TestResourceTracker:
    """Tests for ResourceTracker resource management."""

    def test_register_single_resource(self):
        """Test registering a single resource."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        tracker.register("resource1")
        assert "resource1" in tracker._resources

    def test_register_multiple_resources(self):
        """Test registering multiple resources."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        tracker.register("r1")
        tracker.register("r2")
        tracker.register("r3")

        assert len(tracker._resources) == 3
        assert "r1" in tracker._resources
        assert "r2" in tracker._resources
        assert "r3" in tracker._resources

    def test_unregister_removes_resource(self):
        """Test unregistering removes resource."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        tracker.register("r1")
        tracker.register("r2")
        tracker.unregister("r1")

        assert "r1" not in tracker._resources
        assert "r2" in tracker._resources

    def test_unregister_nonexistent_is_safe(self):
        """Test unregistering nonexistent resource is safe."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        # Should not raise
        tracker.unregister("nonexistent")

    def test_cleanup_all_calls_cleanup_fn(self):
        """Test cleanup_all calls cleanup function for each resource."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        tracker.register("r1")
        tracker.register("r2")
        tracker.cleanup_all()

        assert cleanup_fn.call_count == 2
        cleanup_fn.assert_any_call("r1")
        cleanup_fn.assert_any_call("r2")

    def test_cleanup_all_handles_exceptions(self):
        """Test cleanup_all continues even if cleanup_fn raises."""
        cleanup_fn = MagicMock(side_effect=[Exception("fail"), None])
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        tracker.register("r1")
        tracker.register("r2")

        # Should not raise
        tracker.cleanup_all()

        # Both should have been attempted
        assert cleanup_fn.call_count == 2

    def test_cleanup_all_empty_tracker(self):
        """Test cleanup_all with no resources."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        # Should not raise, should not call cleanup_fn
        tracker.cleanup_all()
        cleanup_fn.assert_not_called()

    def test_thread_safety(self):
        """Test ResourceTracker is thread-safe."""
        cleanup_fn = MagicMock()
        tracker = ResourceTracker(cleanup_fn, name="sandbox")

        def register_many(prefix: str, count: int):
            for i in range(count):
                tracker.register(f"{prefix}_{i}")

        threads = [threading.Thread(target=register_many, args=(f"t{i}", 100)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 500 resources
        assert len(tracker._resources) == 500
