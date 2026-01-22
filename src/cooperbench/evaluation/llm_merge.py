"""
LLM-based merge conflict resolution.

This module uses a model server to perform inference via litellm for resolving
git merge conflicts automatically.
"""

import logging
from pathlib import Path

import litellm
import requests
from requests.exceptions import RequestException

from cooperbench.core.git import run_git_command

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert software engineer resolving git merge conflicts.

RULES:
- Remove ALL conflict markers (<<<<<<< HEAD, =======, >>>>>>> branch_name)
- Merge BOTH features with MINIMAL changes
- Keep EXACT existing logic and structure from both branches
- Do NOT add any new code that wasn't in either branch
- Do NOT restructure, reorganize, or refactor
- Output ONLY the resolved code without conflict markers

Resolve this conflict:"""

SERVER_URL = "http://localhost:8457"
API_BASE = f"{SERVER_URL}/v1"


def check_server_running() -> bool:
    """Check if the model server is running.

    Returns:
        True if server is reachable, False otherwise
    """
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except RequestException:
        return False


def ensure_server_running() -> None:
    """Ensure the model server is running, raise error if not."""
    if not check_server_running():
        error_msg = (
            "\n" + "=" * 80 + "\n"
            "ERROR: Model server not running on port 8457!\n\n"
            "Start the server with:\n"
            "  python -m cooperbench.evaluation.run_server\n"
            "=" * 80
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg)


def strip_markdown_blocks(text: str) -> str:
    """Remove markdown code blocks without removing code indentation.

    Args:
        text: Text potentially containing markdown code blocks

    Returns:
        Text with markdown blocks removed
    """
    lines = text.split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    if lines and lines[0].strip().startswith("```"):
        lines.pop(0)

    if lines and lines[-1].strip() == "```":
        lines.pop()

    return "\n".join(lines)


def extract_conflict_regions(file_path: Path, context_lines: int = 5) -> list[dict]:
    """Extract conflict regions from a file with conflict markers.

    Args:
        file_path: Path to file with merge conflicts
        context_lines: Number of lines of context to include

    Returns:
        List of dictionaries with conflict region information
    """
    with open(file_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    conflicts = []
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    in_conflict = False
    conflict_start = -1

    for i, line in enumerate(lines):
        if line.startswith("<<<<<<<"):
            in_conflict = True
            conflict_start = i
        elif line.startswith(">>>>>>>") and in_conflict:
            in_conflict = False
            conflict_end = i
            conflicts.append(
                {
                    "conflict_start": conflict_start,
                    "conflict_end": conflict_end,
                }
            )

    for i, conflict in enumerate(conflicts):
        conflict_start = conflict["conflict_start"]
        conflict_end = conflict["conflict_end"]

        ideal_before_start = max(0, conflict_start - context_lines)
        ideal_after_end = min(total_lines, conflict_end + 1 + context_lines)

        if i > 0:
            prev_conflict = conflicts[i - 1]
            prev_territory_end = min(total_lines, prev_conflict["conflict_end"] + 1 + context_lines)
            ideal_before_start = max(ideal_before_start, prev_territory_end)

        if i < len(conflicts) - 1:
            next_conflict = conflicts[i + 1]
            next_territory_start = max(0, next_conflict["conflict_start"] - context_lines)
            ideal_after_end = min(ideal_after_end, next_territory_start)

        conflict["context_start"] = ideal_before_start
        conflict["context_end"] = ideal_after_end

        context_lines_data = lines[ideal_before_start:ideal_after_end]
        conflict["context_string"] = "".join(context_lines_data)

        conflict_lines_data = lines[conflict_start : conflict_end + 1]
        conflict["conflict_string"] = "".join(conflict_lines_data)

    return conflicts


def get_conflicted_files(workspace_path: Path) -> list[Path]:
    """Get list of files with merge conflicts.

    Args:
        workspace_path: Path to git workspace

    Returns:
        List of paths to conflicted files
    """
    output = run_git_command(
        workspace_path,
        "diff",
        "--name-only",
        "--diff-filter=U",
        capture_output=True,
    )

    conflicted_files = []
    if output and isinstance(output, str):
        for line in output.strip().split("\n"):
            if line.strip():
                conflicted_files.append(workspace_path / line.strip())

    return conflicted_files


def resolve_conflict_with_llm(conflict_with_context: str) -> str:
    """Resolve a conflict using the LLM via server.

    Args:
        conflict_with_context: The conflict code with markers and context

    Returns:
        Resolved code without conflict markers
    """
    full_prompt = f"{SYSTEM_PROMPT}\n\n{conflict_with_context}"

    try:
        response = litellm.completion(
            model="openai/gpt-3.5-turbo",
            api_base=API_BASE,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0,
            timeout=310.0,
            num_retries=3,
        )

        resolved = response.choices[0].message.content
        resolved = strip_markdown_blocks(resolved)

        return resolved

    except Exception as e:
        logger.error(f"Failed to get LLM resolution: {e}")
        raise


def apply_llm_resolutions(workspace_path: Path) -> tuple[int, int]:
    """Apply LLM resolutions to all conflicted files in workspace.

    Args:
        workspace_path: Path to git workspace with conflicts

    Returns:
        Tuple of (total_conflicts, resolved_conflicts)
    """
    ensure_server_running()

    conflicted_files = get_conflicted_files(workspace_path)

    if not conflicted_files:
        return 0, 0

    total_conflicts = 0
    resolved_conflicts = 0

    for conflicted_file in conflicted_files:
        if not conflicted_file.exists():
            logger.warning(f"Conflicted file does not exist: {conflicted_file}")
            continue

        conflicts = extract_conflict_regions(conflicted_file)

        if not conflicts:
            logger.warning(f"No conflicts found in {conflicted_file}")
            continue

        total_conflicts += len(conflicts)

        with open(conflicted_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        for idx, conflict in enumerate(reversed(conflicts), 1):
            conflict_num = len(conflicts) - idx + 1

            try:
                context_start = conflict["context_start"]
                context_end = conflict["context_end"]

                resolved_with_context = resolve_conflict_with_llm(conflict["context_string"])

                resolved_context_lines = resolved_with_context.split("\n")
                resolved_context_lines = [
                    line + "\n" if i < len(resolved_context_lines) - 1 and not line.endswith("\n") else line
                    for i, line in enumerate(resolved_context_lines)
                ]

                lines = lines[:context_start] + resolved_context_lines + lines[context_end:]

                resolved_conflicts += 1

            except Exception as e:
                logger.error(f"Failed to resolve conflict {conflict_num} in {conflicted_file.name}: {e}")

        try:
            with open(conflicted_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            logger.error(f"Failed to write resolved file {conflicted_file.name}: {e}")

    if total_conflicts > 0:
        logger.info(f"LLM resolved {resolved_conflicts}/{total_conflicts} conflicts")
    return total_conflicts, resolved_conflicts
