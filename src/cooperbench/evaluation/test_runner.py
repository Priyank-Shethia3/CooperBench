"""
Test runner for CooperBench evaluation.

Executes feature tests in Docker containers for isolated, reproducible test execution.
"""

import logging
import re
import shutil
import tempfile
from pathlib import Path

import docker
import docker.errors
from docker.models.images import Image

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Get or create Docker client."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _get_image_name(repo_name: str, task_id: int) -> str:
    """Generate Docker image name for a task."""
    return f"{repo_name}_{task_id}"


def _build_image(repo_name: str, task_id: int, dockerfile_dir: Path) -> Image:
    """Build Docker image for a task if it doesn't exist.

    Args:
        repo_name: Repository name
        task_id: Task identifier
        dockerfile_dir: Directory containing Dockerfile

    Returns:
        Docker image object
    """
    client = _get_client()
    image_name = _get_image_name(repo_name, task_id)

    try:
        image = client.images.get(image_name)
        logger.debug(f"Using existing image: {image_name}")
    except docker.errors.ImageNotFound:
        logger.info(f"Building image: {image_name}")
        image, _ = client.images.build(path=str(dockerfile_dir), tag=image_name)

    return image


def _parse_test_output(output: str) -> bool:
    """Parse container output to determine if tests passed.

    Args:
        output: Container stdout/stderr output

    Returns:
        True if tests passed, False otherwise
    """
    tests_ran_re = re.compile(r"(passed|PASSED|Test execution completed|\bok\b)")
    tests_ran = bool(tests_ran_re.search(output))

    if not tests_ran:
        return False

    failure_re = re.compile(r"(FAIL:|FAILED|failed.*tests?.*failed)", re.IGNORECASE)
    found_failure = bool(failure_re.search(output))

    success_re = re.compile(r"(\bok\b|passed|PASSED)")
    found_success = bool(success_re.search(output))

    return found_success and not found_failure


def run_tests(
    agent_workspace_path: Path,
    feature_id: int,
    test_script_path: Path,
    tests_patch_path: Path,
    return_errors: bool = False,
    feature_patch_path: Path | None = None,
    task_dir: Path | None = None,
    repo_name: str | None = None,
    task_id: int | None = None,
) -> tuple[bool, str | None]:
    """Run tests for a feature in a Docker container.

    Args:
        agent_workspace_path: Path to agent workspace (used to find feature patch if not provided)
        feature_id: Feature id for logging
        test_script_path: Path to test script (used to derive task_dir if not provided)
        tests_patch_path: Path to the tests.patch file
        return_errors: Whether to return error details
        feature_patch_path: Optional explicit path to feature patch
        task_dir: Optional task directory (derived from test_script_path if not provided)
        repo_name: Optional repo name (derived from task_dir if not provided)
        task_id: Optional task id (derived from task_dir if not provided)

    Returns:
        Tuple of (success, error_info)
    """
    # Derive missing parameters
    if task_dir is None:
        task_dir = test_script_path.parent

    if repo_name is None or task_id is None:
        # Parse from task_dir path like "dataset/pallets_click_task/task2068"
        task_dir_name = task_dir.name  # e.g., "task2068"
        parent_name = task_dir.parent.name  # e.g., "pallets_click_task"
        repo_name = repo_name or parent_name
        task_id = task_id or int(task_dir_name.replace("task", ""))

    # Check for Dockerfile
    dockerfile = task_dir / "Dockerfile"
    if not dockerfile.exists():
        error_msg = f"Dockerfile not found in {task_dir}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None

    # Find feature patch if not explicitly provided
    if feature_patch_path is None:
        # Look for patch in agent workspace or derive from workspace path
        possible_patch = agent_workspace_path / "feature.patch"
        if possible_patch.exists():
            feature_patch_path = possible_patch
        else:
            # Try to find it relative to test_script_path
            feature_dir = task_dir / f"feature{feature_id}"
            feature_patch_path = feature_dir / "feature.patch"

    if feature_patch_path is None or not feature_patch_path.exists():
        error_msg = f"Feature patch not found for feature {feature_id}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None

    try:
        client = _get_client()
        image = _build_image(repo_name, task_id, task_dir)

        # Create temp directory for patches
        patch_dir = Path(tempfile.mkdtemp(prefix="eval_patches_"))
        shutil.copy2(feature_patch_path, patch_dir / feature_patch_path.name)
        shutil.copy2(tests_patch_path, patch_dir / tests_patch_path.name)

        container_name = f"{repo_name}_{task_id}_f{feature_id}"

        # Remove existing container with same name if exists
        try:
            existing = client.containers.get(container_name)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        logger.debug(f"Running tests for feature {feature_id} in container {container_name}")

        container = client.containers.run(
            image=image,
            command=[tests_patch_path.name, feature_patch_path.name],
            volumes={str(patch_dir): {"bind": "/patches", "mode": "rw"}},
            name=container_name,
            auto_remove=False,
            detach=True,
        )

        try:
            wait_result = container.wait(timeout=600)
            exit_code = wait_result.get("StatusCode", -1)

            try:
                output = container.logs().decode("utf-8")
            except docker.errors.APIError as e:
                if container.id:
                    try:
                        container_refresh = client.containers.get(container.id)
                        output = container_refresh.logs().decode("utf-8")
                    except Exception:
                        output = f"Failed to retrieve logs: {e}\nExit code: {exit_code}"
                else:
                    output = f"Failed to retrieve logs: {e}\nExit code: {exit_code}"

            success = _parse_test_output(output)
            return success, output if return_errors else None

        finally:
            try:
                container.remove()
            except docker.errors.NotFound:
                pass
            except Exception:
                pass

            try:
                shutil.rmtree(patch_dir)
            except Exception:
                pass

    except docker.errors.DockerException as e:
        error_msg = f"Docker error running tests for feature {feature_id}: {e}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None

    except Exception as e:
        error_msg = f"Error running tests for feature {feature_id}: {e}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None


def run_tests_with_patch(
    repo_name: str,
    task_id: int,
    task_dir: Path,
    feature_patch: Path,
    test_patch: Path,
    container_name: str | None = None,
) -> tuple[bool, str]:
    """Run tests with explicit patch paths (for merge evaluation).

    Args:
        repo_name: Repository name
        task_id: Task identifier
        task_dir: Task directory containing Dockerfile
        feature_patch: Path to feature/merged patch to apply
        test_patch: Path to test patch
        container_name: Optional container name

    Returns:
        Tuple of (success, output)
    """
    dockerfile = task_dir / "Dockerfile"
    if not dockerfile.exists():
        raise ValueError(f"Dockerfile not found in {task_dir}")

    client = _get_client()
    image = _build_image(repo_name, task_id, task_dir)

    patch_dir = Path(tempfile.mkdtemp(prefix="eval_patches_"))
    shutil.copy2(feature_patch, patch_dir / feature_patch.name)
    shutil.copy2(test_patch, patch_dir / test_patch.name)

    if container_name:
        try:
            existing = client.containers.get(container_name)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

    container = client.containers.run(
        image=image,
        command=[test_patch.name, feature_patch.name],
        volumes={str(patch_dir): {"bind": "/patches", "mode": "rw"}},
        name=container_name,
        auto_remove=False,
        detach=True,
    )

    try:
        wait_result = container.wait(timeout=600)
        exit_code = wait_result.get("StatusCode", -1)

        try:
            output = container.logs().decode("utf-8")
        except docker.errors.APIError as e:
            if container.id:
                try:
                    container_refresh = client.containers.get(container.id)
                    output = container_refresh.logs().decode("utf-8")
                except Exception:
                    output = f"Failed to retrieve logs: {e}\nExit code: {exit_code}"
            else:
                output = f"Failed to retrieve logs: {e}\nExit code: {exit_code}"

        success = _parse_test_output(output)
        return success, output

    finally:
        try:
            container.remove()
        except docker.errors.NotFound:
            pass
        except Exception:
            pass

        try:
            shutil.rmtree(patch_dir)
        except Exception:
            pass
