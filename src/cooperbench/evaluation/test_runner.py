"""
Test runner for CooperBench evaluation.

Executes feature tests in agent workspaces and reports results.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_tests(
    agent_workspace_path: Path,
    feature_id: int,
    test_script_path: Path,
    tests_patch_path: Path,
    return_errors: bool = False,
) -> tuple[bool, str | None]:
    """Run tests for a feature and return results.

    Args:
        agent_workspace_path: Path to agent workspace
        feature_id: Feature id
        test_script_path: Path to the test script
        tests_patch_path: Path to the tests.patch file
        return_errors: Whether to return error details

    Returns:
        Tuple of (success, error_info)
    """
    try:
        logger.debug(f"Executing test script: {test_script_path}")
        result = subprocess.run(
            [
                str(test_script_path.resolve()),
                str(agent_workspace_path.resolve()),
                str(tests_patch_path.resolve()),
            ],
            cwd=str(agent_workspace_path),
            capture_output=True,
            text=True,
            timeout=600,
        )

        success = result.returncode == 0

        if success:
            return True, None
        else:
            if return_errors:
                error_info = f"Tests failed with return code {result.returncode}"
                if result.stderr:
                    error_info += f"\nSTDERR: {result.stderr}"
                if result.stdout:
                    error_info += f"\nSTDOUT: {result.stdout}"
                return False, error_info
            return False, None

    except subprocess.TimeoutExpired:
        error_msg = f"Test execution timed out for feature {feature_id}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None

    except Exception as e:
        error_msg = f"Error running tests for feature {feature_id}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg if return_errors else None
