"""
Unified evaluation entrypoint for CooperBench.

Supports evaluation modes:
- merge: Test AND merge conflict analysis between features (coop/coop_ablation)
- test: Test execution only (single/solo)
"""

import argparse
import asyncio
import json
import time
from typing import Literal

from dotenv import load_dotenv

from cooperbench import BenchSetting, FileInterface
from cooperbench.core.git import run_git_command
from cooperbench.core.merge import analyze_merge, merge
from cooperbench.core.paths import get_branch_name
from cooperbench.evaluation.test_runner import run_tests

load_dotenv()


async def evaluate(
    file_interface: FileInterface,
    eval_type: Literal["merge", "test"],
    file_location: Literal["logs", "cache", "hf"],
    filter_patch: bool = True,
) -> dict:
    """Unified evaluation function.

    Args:
        file_interface: FileInterface object for file operations
        eval_type: Type of evaluation ("merge" or "test")
        file_location: Location of files ("logs", "cache", "hf")
        filter_patch: Whether to filter non-code changes from patch

    Returns:
        dict: Evaluation results
    """
    file_interface.setup_filesystem(check_for_conflicts=(eval_type == "merge"))

    if eval_type == "merge":
        results = await run_merge_evaluation(file_interface, file_location, filter_patch)
        print(f"\nMerge evaluation completed. Conflict score: {results['conflict_score']}")
    elif eval_type == "test":
        if file_interface.setting == BenchSetting.SOLO:
            results = await run_solo_evaluation(file_interface, file_location, filter_patch)
            print(f"\nSolo evaluation completed. Both tests {'passed' if results['both_tests_passed'] else 'failed'}")
        else:
            results = await run_test_evaluation(file_interface, file_location, filter_patch)
            print(f"\nTest evaluation completed. Tests {'passed' if results['test_passed'] else 'failed'}")

    return results


async def run_test_evaluation(
    file_interface: FileInterface,
    file_location: Literal["logs", "cache", "hf"],
    filter_patch: bool,
) -> dict:
    """Run test evaluation for a single feature.

    Args:
        file_interface: FileInterface object
        file_location: Location of the patch file
        filter_patch: Whether to filter non-code changes

    Returns:
        dict: Test evaluation results
    """
    start_time = time.time()

    repo_name = file_interface.repo_name
    task_id = file_interface.task_id
    feature1_id = file_interface.feature1_id

    print(f"[EVAL] Running test evaluation for {repo_name}/task{task_id}/feature{feature1_id}")

    agent_workspace_path = file_interface.agent_workspace1_path
    test_script_path = file_interface.get_test_script_path()

    # Reset workspace to base commit
    if file_location in ["logs", "cache", "hf"]:
        run_git_command(
            agent_workspace_path,
            "reset",
            "--hard",
            file_interface.base_commit,
            check=False,
            capture_output=True,
        )

    # Apply patch and run tests
    file_interface.apply_patch(file_location, first=True, filter_patch=filter_patch)
    test_passed, error_info = run_tests(
        agent_workspace_path,
        feature1_id,
        test_script_path,
        file_interface.get_tests_patch_path(first=True),
        return_errors=True,
    )

    results = {
        "task_name": repo_name,
        "task_id": task_id,
        "feature_num": feature1_id,
        "k": file_interface.k,
        "test_passed": test_passed,
        "error_info": error_info,
        "duration": time.time() - start_time,
    }

    file_interface.save_test_report(results)
    return results


async def run_solo_evaluation(
    file_interface: FileInterface,
    file_location: Literal["logs", "cache", "hf"],
    filter_patch: bool,
) -> dict:
    """Run evaluation for solo mode (one patch, two feature tests).

    Args:
        file_interface: FileInterface object
        file_location: Location of the patch file
        filter_patch: Whether to filter non-code changes

    Returns:
        dict: Evaluation results
    """
    start_time = time.time()

    repo_name = file_interface.repo_name
    task_id = file_interface.task_id
    feature1_id = file_interface.feature1_id
    feature2_id = file_interface.feature2_id

    print(f"[EVAL] Running solo evaluation for {repo_name}/task{task_id}")

    agent_workspace_path = file_interface.agent_workspace1_path
    test_script_path = file_interface.get_test_script_path()

    # Reset and apply patch
    if file_location in ["logs", "cache", "hf"]:
        run_git_command(
            agent_workspace_path,
            "reset",
            "--hard",
            file_interface.base_commit,
            check=False,
            capture_output=True,
        )

    file_interface.apply_patch(file_location, first=True, filter_patch=filter_patch)

    # Run tests for both features
    feature1_tests_passed, output1 = run_tests(
        agent_workspace_path,
        feature1_id,
        test_script_path,
        file_interface.get_tests_patch_path(first=True),
        return_errors=True,
    )

    feature2_tests_passed, output2 = run_tests(
        agent_workspace_path,
        feature2_id,
        test_script_path,
        file_interface.get_tests_patch_path(first=False),
        return_errors=True,
    )

    both_tests_passed = feature1_tests_passed and feature2_tests_passed

    results = {
        "task_name": repo_name,
        "task_id": task_id,
        "feature1_id": feature1_id,
        "feature2_id": feature2_id,
        "k": file_interface.k,
        "feature1_test_passed": feature1_tests_passed,
        "feature1_test_output": output1,
        "feature2_test_passed": feature2_tests_passed,
        "feature2_test_output": output2,
        "both_tests_passed": both_tests_passed,
        "duration": time.time() - start_time,
    }

    file_interface.save_solo_test_report(results)
    return results


async def run_merge_evaluation(
    file_interface: FileInterface,
    file_location: Literal["logs", "cache", "hf"],
    filter_patch: bool,
) -> dict:
    """Run merge evaluation between two features (coop/coop_ablation).

    Args:
        file_interface: FileInterface object
        file_location: Location of patch files
        filter_patch: Whether to filter non-code changes

    Returns:
        dict: Merge evaluation results
    """
    start_time = time.time()

    feature1_id = file_interface.feature1_id
    feature2_id = file_interface.feature2_id
    assert feature2_id, "Feature 2 must be specified for merge evaluation"

    agent_workspace1_path = file_interface.agent_workspace1_path
    agent_workspace2_path = file_interface.agent_workspace2_path

    print(f"[EVAL] Running merge evaluation for features {feature1_id} and {feature2_id}")

    # Reset workspaces
    if file_location in ["logs", "cache", "hf"]:
        run_git_command(
            agent_workspace1_path,
            "reset",
            "--hard",
            file_interface.base_commit,
            check=False,
            capture_output=True,
        )
        run_git_command(
            agent_workspace2_path,
            "reset",
            "--hard",
            file_interface.base_commit,
            check=False,
            capture_output=True,
        )

    # Apply patches
    file_interface.apply_patch(file_location, first=True, filter_patch=filter_patch)
    file_interface.apply_patch(file_location, first=False, filter_patch=filter_patch)

    # Perform merge analysis
    report = file_interface.get_merge_report_metadata()

    diff_output, conflict = merge(
        agent_workspace2_path,
        get_branch_name(
            file_interface.setting,
            file_interface.k,
            feature1_id,
            feature2_id,
        ),
    )
    report = analyze_merge(diff_output, conflict, report)

    # Run tests on merged result if no conflicts
    test_script_path = file_interface.get_test_script_path()

    if not conflict:
        # Test feature 1
        feature1_tests_passed, output1 = run_tests(
            agent_workspace2_path,
            feature1_id,
            test_script_path,
            file_interface.get_tests_patch_path(first=True),
            return_errors=True,
        )
        report["feature1"]["tests_passed"] = feature1_tests_passed
        report["feature1"]["test_output"] = output1

        # Reset and test feature 2
        run_git_command(agent_workspace2_path, "reset", "--hard", check=False, capture_output=True)
        feature2_tests_passed, output2 = run_tests(
            agent_workspace2_path,
            feature2_id,
            test_script_path,
            file_interface.get_tests_patch_path(first=False),
            return_errors=True,
        )
        report["feature2"]["tests_passed"] = feature2_tests_passed
        report["feature2"]["test_output"] = output2

    report["duration"] = time.time() - start_time
    file_interface.save_json_merge_report(json.dumps(report, indent=2))

    return report


async def main() -> None:
    """CLI wrapper for evaluate()."""
    parser = argparse.ArgumentParser(description="CooperBench unified evaluation entrypoint")

    parser.add_argument(
        "evaluation_type",
        choices=["merge", "test"],
        help="Type of evaluation to perform",
    )
    parser.add_argument(
        "--setting",
        "-s",
        required=True,
        choices=[s.value for s in BenchSetting],
        help="Experiment setting mode",
    )
    parser.add_argument("--repo-name", required=True, type=str, help="Repository name")
    parser.add_argument("--task-id", required=True, type=int, help="Task number")
    parser.add_argument("--model1", "-m1", required=True, help="Model for first agent")
    parser.add_argument("--model2", "-m2", help="Model for second agent")
    parser.add_argument("--feature1-id", "-i", required=True, type=int, help="First feature ID")
    parser.add_argument("--feature2-id", "-j", type=int, help="Second feature ID")
    parser.add_argument("--k", type=int, default=1, help="Experiment run identifier")
    parser.add_argument("--not-save-to-hf", action="store_true", help="Do not save to HuggingFace")
    parser.add_argument("--create-pr", action="store_true", help="Create PR when saving to HF")
    parser.add_argument(
        "--file-location",
        choices=["logs", "cache", "hf"],
        default="logs",
        help="Where to load patches from",
    )
    parser.add_argument(
        "--not-filter-patch",
        action="store_true",
        help="Do not filter non-code changes from patch",
    )

    args = parser.parse_args()

    setting = BenchSetting(args.setting)

    file_interface = FileInterface(
        setting=setting,
        repo_name=args.repo_name,
        task_id=args.task_id,
        k=args.k,
        feature1_id=args.feature1_id,
        model1=args.model1,
        feature2_id=args.feature2_id,
        model2=args.model2,
        save_to_hf=not args.not_save_to_hf,
        create_pr=args.create_pr,
    )

    await evaluate(
        file_interface,
        args.evaluation_type,
        args.file_location,
        filter_patch=not args.not_filter_patch,
    )


if __name__ == "__main__":
    asyncio.run(main())
