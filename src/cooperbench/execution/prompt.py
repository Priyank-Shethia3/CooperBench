"""
Prompt rendering utilities for execution phase.

Renders task prompts using Jinja2 templates with feature descriptions
and implementation plans.
"""

from pathlib import Path

import jinja2


def render_task_prompt(
    feature_description: str,
    plan: str,
    template_dir: Path | None = None,
    template_name: str = "task_prompt.j2",
    **extra_context: object,
) -> str:
    """Render the main task prompt using the Jinja2 template.

    Args:
        feature_description: The feature description text
        plan: Implementation plan from planning phase
        template_dir: Directory containing Jinja2 templates
        template_name: Name of the template file to use
        **extra_context: Additional context variables for template rendering

    Returns:
        str: The rendered prompt
    """
    if template_dir is None:
        template_dir = Path(__file__).parent / "templates"

    template_dir = Path(template_dir)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_name)

    context = {
        "feature_description": feature_description,
        "plan": plan,
        **extra_context,
    }

    return template.render(**context)
