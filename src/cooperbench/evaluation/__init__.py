"""
Evaluation phase components for CooperBench.

This subpackage handles test execution, merge conflict analysis,
and result aggregation.
"""

from cooperbench.evaluation.evaluate import evaluate
from cooperbench.evaluation.test_runner import run_tests

__all__ = [
    "evaluate",
    "run_tests",
]
