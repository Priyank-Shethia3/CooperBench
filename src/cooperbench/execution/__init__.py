"""
Execution phase components for CooperBench.

This subpackage handles the execution of implementation plans using
agent frameworks like OpenHands.
"""

from cooperbench.execution.execute import create_execution
from cooperbench.execution.prompt import render_task_prompt

__all__ = [
    "create_execution",
    "render_task_prompt",
]
