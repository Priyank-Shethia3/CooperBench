"""Tests for utility functions."""

from cooperbench.utils import get_image_name


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
