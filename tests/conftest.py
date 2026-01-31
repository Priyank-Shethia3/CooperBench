"""Pytest configuration and shared fixtures."""

import os

import pytest


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test (prevents test pollution)."""
    original = os.getcwd()
    yield
    os.chdir(original)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-modal",
        action="store_true",
        default=False,
        help="Run tests that require Modal sandboxes (slow, network)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "modal: tests that require Modal sandboxes (slow, requires network)")


def pytest_ignore_collect(collection_path, config):
    """Ignore src directory during test collection."""
    if "src" in collection_path.parts:
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Skip Modal tests unless --run-modal is specified."""
    if config.getoption("--run-modal"):
        return

    skip_modal = pytest.mark.skip(reason="need --run-modal option to run")
    for item in items:
        if "modal" in item.keywords:
            item.add_marker(skip_modal)


@pytest.fixture(scope="session")
def modal_app():
    """Get or create Modal app for tests."""
    import modal

    return modal.App.lookup("cooperbench-test", create_if_missing=True)


@pytest.fixture(scope="session")
def redis_url():
    """Redis URL for tests - auto-starts via Docker if needed."""
    import subprocess
    import time

    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379")

    # Try to connect
    try:
        import redis

        client = redis.from_url(url)
        client.ping()
        return url
    except Exception:
        pass

    # Auto-start via Docker
    try:
        subprocess.run(
            ["docker", "run", "-d", "--name", "cooperbench-redis-test", "-p", "6379:6379", "redis:alpine"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # Container may already exist, try starting it
        subprocess.run(["docker", "start", "cooperbench-redis-test"], capture_output=True)

    # Wait for Redis to be ready
    import redis

    client = redis.from_url(url)
    for _ in range(10):
        time.sleep(0.5)
        try:
            client.ping()
            return url
        except Exception:
            pass

    pytest.skip("Could not start Redis via Docker")
    return url


@pytest.fixture
def sample_task_dir(tmp_path):
    """Create a sample task directory structure for testing."""
    task_dir = tmp_path / "test_repo_task" / "task1"
    feature1_dir = task_dir / "feature1"
    feature2_dir = task_dir / "feature2"

    feature1_dir.mkdir(parents=True)
    feature2_dir.mkdir(parents=True)

    (feature1_dir / "feature.md").write_text("# Feature 1\n\nImplement feature 1.")
    (feature2_dir / "feature.md").write_text("# Feature 2\n\nImplement feature 2.")

    return task_dir


@pytest.fixture
def chdir_tmp(tmp_path):
    """Change to tmp_path and restore original cwd afterward."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)
