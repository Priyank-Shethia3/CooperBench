"""
Evaluation phase components for CooperBench.

This subpackage handles test execution, merge conflict analysis,
and result aggregation.
"""

from cooperbench.evaluation.evaluate import (
    evaluate,
    run_aggregate_evaluation,
    run_merge_evaluation,
    run_test_evaluation,
)
from cooperbench.evaluation.llm_merge import apply_llm_resolutions
from cooperbench.evaluation.reporter import generate_json_report, generate_single_aggregate_table
from cooperbench.evaluation.test_runner import run_tests, run_tests_with_patch

__all__ = [
    "evaluate",
    "run_test_evaluation",
    "run_merge_evaluation",
    "run_aggregate_evaluation",
    "run_tests",
    "run_tests_with_patch",
    "apply_llm_resolutions",
    "generate_json_report",
    "generate_single_aggregate_table",
]
