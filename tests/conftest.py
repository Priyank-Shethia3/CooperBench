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
    parser.addoption(
        "--run-docker",
        action="store_true",
        default=False,
        help="Run tests that require Docker (requires local Docker daemon)",
    )
    parser.addoption(
        "--run-gcp",
        action="store_true",
        default=False,
        help="Run tests that require GCP (requires GOOGLE_CLOUD_PROJECT and credentials)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "modal: tests that require Modal sandboxes (slow, requires network)")
    config.addinivalue_line("markers", "docker: tests that require Docker (requires local Docker daemon)")
    config.addinivalue_line("markers", "gcp: tests that require GCP (requires GOOGLE_CLOUD_PROJECT and credentials)")


def pytest_ignore_collect(collection_path, config):
    """Ignore src directory during test collection."""
    if "src" in collection_path.parts:
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Skip Modal/Docker/GCP tests unless respective options are specified."""
    run_modal = config.getoption("--run-modal")
    run_docker = config.getoption("--run-docker")
    run_gcp = config.getoption("--run-gcp")

    skip_modal = pytest.mark.skip(reason="need --run-modal option to run")
    skip_docker = pytest.mark.skip(reason="need --run-docker option to run")
    skip_gcp = pytest.mark.skip(reason="need --run-gcp option to run")

    for item in items:
        if "modal" in item.keywords and not run_modal:
            item.add_marker(skip_modal)
        if "docker" in item.keywords and not run_docker:
            item.add_marker(skip_docker)
        if "gcp" in item.keywords and not run_gcp:
            item.add_marker(skip_gcp)


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
