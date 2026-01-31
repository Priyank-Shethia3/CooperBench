"""Tests for cooperbench runner (task discovery, etc)."""

from cooperbench.runner import discover_tasks


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
