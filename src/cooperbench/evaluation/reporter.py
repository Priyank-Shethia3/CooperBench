"""
Report generation utilities for CooperBench evaluation.

Provides functions to generate JSON reports and formatted tables for
merge analysis and aggregate evaluation results.
"""

import logging
from datetime import datetime
from pathlib import Path

import jinja2

logger = logging.getLogger(__name__)

_jinja_env = None


def _get_jinja_env(template_dir: Path | None = None) -> jinja2.Environment:
    """Get or create the Jinja2 environment."""
    global _jinja_env
    if _jinja_env is None:
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        template_dir = Path(template_dir)
        _jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.debug(f"Initialized Jinja2 environment with template directory: {template_dir}")

    return _jinja_env


def _get_severity_level(score: int) -> str:
    """Get severity level from conflict score.

    Args:
        score: Numeric conflict score

    Returns:
        Severity level string
    """
    if score > 100:
        return "CRITICAL"
    elif score > 50:
        return "HIGH"
    elif score > 20:
        return "MEDIUM"
    elif score > 0:
        return "LOW"
    else:
        return "NONE"


def _get_severity_color(severity: str) -> str:
    """Get color code for severity level.

    Args:
        severity: Severity level

    Returns:
        Color code string
    """
    colors = {
        "CRITICAL": "#FF0000",
        "HIGH": "#FF6600",
        "MEDIUM": "#FF9900",
        "LOW": "#FFCC00",
        "NONE": "#00CC00",
    }
    return colors.get(severity, "#CCCCCC")


def generate_json_report(merge_results: dict) -> dict:
    """Generate a JSON-formatted report from merge results.

    Args:
        merge_results: Results from merge analysis

    Returns:
        JSON-serializable report data
    """
    conflict_score = merge_results.get("conflict_score", 0)
    severity = _get_severity_level(conflict_score)

    json_report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "repo_name": merge_results.get("repo_name"),
            "task_id": merge_results.get("task_id"),
            "evaluation_type": "merge_analysis",
        },
        "features": {
            "feature1": merge_results["feature1"],
            "feature2": merge_results["feature2"],
        },
        "merge_analysis": {
            "status": merge_results.get("merge_status"),
            "conflict_score": conflict_score,
            "severity": severity,
            "severity_color": _get_severity_color(severity),
            "conflict_details": merge_results.get("conflict_details", {}),
            "files": {
                "diff_file": str(merge_results.get("diff_file")),
            },
        },
    }

    if merge_results.get("error"):
        json_report["error"] = {
            "message": str(merge_results["error"]),
            "timestamp": merge_results.get("timestamp"),
        }

    return json_report


def generate_aggregate_table(
    table_data: dict[tuple, int],
    total_tasks: int,
    template_dir: Path | None = None,
) -> str:
    """Generate formatted contingency table for aggregate evaluation.

    Args:
        table_data: Dictionary containing counts for each cell
        total_tasks: Total number of evaluated task pairs
        template_dir: Optional template directory path

    Returns:
        Formatted table as string
    """
    template_data = {
        "total_tasks": total_tasks,
        "clean_0_pct": (table_data[(False, 2)] / total_tasks) * 100,
        "clean_1_pct": (table_data[(False, 1)] / total_tasks) * 100,
        "clean_2_pct": (table_data[(False, 0)] / total_tasks) * 100,
        "conflict_0_pct": (table_data[(True, 2)] / total_tasks) * 100,
        "conflict_1_pct": (table_data[(True, 1)] / total_tasks) * 100,
        "conflict_2_pct": (table_data[(True, 0)] / total_tasks) * 100,
    }

    template_data["clean_total_pct"] = (
        template_data["clean_0_pct"] + template_data["clean_1_pct"] + template_data["clean_2_pct"]
    )
    template_data["conflict_total_pct"] = (
        template_data["conflict_0_pct"] + template_data["conflict_1_pct"] + template_data["conflict_2_pct"]
    )
    template_data["col_0_total_pct"] = template_data["clean_0_pct"] + template_data["conflict_0_pct"]
    template_data["col_1_total_pct"] = template_data["clean_1_pct"] + template_data["conflict_1_pct"]
    template_data["col_2_total_pct"] = template_data["clean_2_pct"] + template_data["conflict_2_pct"]

    jinja_env = _get_jinja_env(template_dir)
    template = jinja_env.get_template("aggregate_table.j2")
    table_text = template.render(data=template_data)

    return table_text


def generate_single_aggregate_table(
    table_data: dict[tuple[int, int], int],
    max_k: int,
    min_feature_id: int,
    max_feature_id: int,
    success_pct: float,
    template_dir: Path | None = None,
) -> str:
    """Generate formatted table for single feature evaluation results.

    Args:
        table_data: Dictionary containing test results keyed by (feature_id, k)
        max_k: Maximum k value
        min_feature_id: Minimum feature ID
        max_feature_id: Maximum feature ID
        success_pct: Overall success percentage
        template_dir: Optional template directory path

    Returns:
        Formatted table as string
    """
    feature_ids = list(range(min_feature_id, max_feature_id + 1))
    k_range = list(range(1, max_k + 1))

    row_percentages = {}
    for feature_id in feature_ids:
        passed_count = sum(table_data[(feature_id, k)] for k in k_range)
        row_percentages[feature_id] = (passed_count / max_k) * 100.0

    col_percentages = {}
    for k in k_range:
        passed_count = sum(table_data[(feature_id, k)] for feature_id in feature_ids)
        col_percentages[k] = (passed_count / len(feature_ids)) * 100.0

    template_data = {
        "max_k": max_k,
        "feature_ids": feature_ids,
        "table_data": table_data,
        "row_percentages": row_percentages,
        "col_percentages": col_percentages,
        "success_pct": success_pct,
        "total_tasks": len(feature_ids) * max_k,
    }

    jinja_env = _get_jinja_env(template_dir)
    template = jinja_env.get_template("single_aggregate_table.j2")
    table_text = template.render(data=template_data)

    return table_text
