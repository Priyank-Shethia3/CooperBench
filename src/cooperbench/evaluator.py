"""Evaluate completed benchmark runs.

Scans logs/ directory to find completed agent runs, then evaluates them
by applying patches and running tests in Modal sandboxes.

For coop runs: Merges patches from both agents, tests against both features.
For solo runs: Tests the single patch against both features.

Results are saved to eval.json in each run directory, with a summary
in logs/{run_name}/eval_summary.json.

Key functions:
    evaluate: Main entry point - evaluates runs with progress display
    discover_runs: Find completed runs from logs/ directory
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from cooperbench.sandbox import test_merged, test_solo
from cooperbench.utils import console


def evaluate(
    run_name: str,
    repo: str | None = None,
    task_id: int | None = None,
    features: list[int] | None = None,
    concurrency: int = 10,
    force: bool = False,
) -> None:
    """Evaluate completed runs.

    Args:
        run_name: Name of the run to evaluate
        repo: Filter by repository name
        task_id: Filter by task ID
        features: Specific feature pair to evaluate
        concurrency: Number of parallel evaluations
        force: Force re-evaluation even if eval.json exists
    """
    runs = discover_runs(
        run_name=run_name,
        repo_filter=repo,
        task_filter=task_id,
        features_filter=features,
    )

    if not runs:
        console.print("[yellow]no runs found to evaluate[/yellow]")
        return

    is_single = len(runs) == 1

    # Header
    console.print()
    console.print(f"[bold]cooperbench eval[/bold] [dim]{run_name}[/dim]")
    console.print(f"[dim]runs:[/dim] {len(runs)}")
    console.print()

    results = []
    passed = 0
    failed = 0
    errors = 0
    skipped = 0

    def eval_run(run_info: dict) -> dict | None:
        return _evaluate_single(run_info, force=force)

    if is_single:
        # Single run - show detailed output
        run_info = runs[0]
        feat_str = ",".join(str(f) for f in run_info["features"])
        console.print(f"  [dim]evaluating[/dim] {run_info['repo']}/{run_info['task_id']} [{feat_str}]")

        result = eval_run(run_info)
        if result:
            if result.get("skipped"):
                skipped = 1
                console.print("  [dim]skipped (already evaluated)[/dim]")
            elif result.get("error"):
                errors = 1
                console.print(f"  [red]error:[/red] {result['error']}")
            elif result.get("both_passed"):
                passed = 1
                console.print("  [green]passed[/green] both features")
            else:
                failed = 1
                f1 = "[green]✓[/green]" if result.get("feature1", {}).get("passed") else "[red]✗[/red]"
                f2 = "[green]✓[/green]" if result.get("feature2", {}).get("passed") else "[red]✗[/red]"
                console.print(f"  [yellow]partial[/yellow] f1:{f1} f2:{f2}")
    else:
        # Multiple runs - show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            eval_progress = progress.add_task("evaluating", total=len(runs))

            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                future_to_run = {executor.submit(eval_run, r): r for r in runs}

                for future in as_completed(future_to_run):
                    run_info = future_to_run[future]
                    feat_str = ",".join(str(f) for f in run_info["features"])
                    task_name = f"{run_info['repo']}/{run_info['task_id']}"

                    try:
                        result = future.result()
                        if result is None:
                            errors += 1
                            status = "error"
                        elif result.get("skipped"):
                            skipped += 1
                            status = "skip"
                        elif result.get("error"):
                            errors += 1
                            status = "error"
                        elif result.get("both_passed"):
                            passed += 1
                            status = "pass"
                        else:
                            failed += 1
                            status = "fail"

                        results.append({"run": f"{task_name}/{feat_str}", "status": status})

                        status_style = {
                            "pass": "green",
                            "fail": "red",
                            "skip": "dim",
                            "error": "yellow",
                        }[status]
                        progress.console.print(
                            f"  [{status_style}]{status}[/{status_style}] {task_name} [dim][{feat_str}][/dim]"
                        )

                    except Exception as e:
                        errors += 1
                        results.append({"run": f"{task_name}/{feat_str}", "status": "error", "error": str(e)})
                        progress.console.print(f"  [yellow]error[/yellow] {task_name} [dim]{e}[/dim]")

                    progress.update(eval_progress, advance=1)

    # Save summary
    log_dir = Path("logs") / run_name
    summary = {
        "run_name": run_name,
        "evaluated_at": datetime.now().isoformat(),
        "total_runs": len(runs),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "pass_rate": passed / max(passed + failed, 1),
        "results": results,
    }
    with open(log_dir / "eval_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Summary
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("passed", f"[green]{passed}[/green]")
    table.add_row("failed", f"[red]{failed}[/red]")
    if errors:
        table.add_row("errors", f"[yellow]{errors}[/yellow]")
    if skipped:
        table.add_row("skipped", f"[dim]{skipped}[/dim]")
    table.add_row("pass rate", f"{summary['pass_rate']:.1%}")
    console.print(table)
    console.print()


def discover_runs(
    run_name: str,
    repo_filter: str | None = None,
    task_filter: int | None = None,
    features_filter: list[int] | None = None,
) -> list[dict]:
    """Discover completed runs from logs/ directory.

    Supports both new structure (logs/{run_name}/{setting}/{repo}/)
    and legacy structure (logs/{run_name}/{repo}/).

    Args:
        run_name: Name of the run
        repo_filter: Filter by repository name
        task_filter: Filter by task ID
        features_filter: Specific feature pair to find

    Returns:
        List of run dicts with repo, task_id, features, log_dir, setting
    """
    runs = []
    log_dir = Path("logs") / run_name

    if not log_dir.exists():
        return runs

    # Check for new structure (solo/, coop/)
    for setting in ["solo", "coop"]:
        setting_dir = log_dir / setting
        if setting_dir.exists():
            runs.extend(
                _discover_runs_in_dir(
                    setting_dir,
                    setting=setting,
                    repo_filter=repo_filter,
                    task_filter=task_filter,
                    features_filter=features_filter,
                )
            )

    # Check legacy structure (direct repo dirs)
    if not runs:
        runs.extend(
            _discover_runs_in_dir(
                log_dir,
                setting=None,  # Will be inferred from result.json
                repo_filter=repo_filter,
                task_filter=task_filter,
                features_filter=features_filter,
            )
        )

    return runs


def _discover_runs_in_dir(
    base_dir: Path,
    setting: str | None,
    repo_filter: str | None,
    task_filter: int | None,
    features_filter: list[int] | None,
) -> list[dict]:
    """Discover runs in a specific directory."""
    runs = []

    for repo_dir in sorted(base_dir.iterdir()):
        if not repo_dir.is_dir() or not repo_dir.name.endswith("_task"):
            continue
        if repo_filter and repo_filter != repo_dir.name:
            continue

        for task_dir in sorted(repo_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            try:
                task_id = int(task_dir.name)
            except ValueError:
                continue
            if task_filter and task_filter != task_id:
                continue

            for feature_dir in sorted(task_dir.iterdir()):
                if not feature_dir.is_dir():
                    continue

                # Parse feature string: f1_f2 or f1_f5
                parts = feature_dir.name.split("_")
                try:
                    features = [int(p[1:]) for p in parts if p.startswith("f")]
                except ValueError:
                    continue

                if len(features) < 2:
                    continue

                if features_filter:
                    if set(features_filter) != set(features):
                        continue

                result_file = feature_dir / "result.json"
                if not result_file.exists():
                    continue

                # Infer setting from result.json or solo.patch presence
                run_setting = setting
                if run_setting is None:
                    with open(result_file) as f:
                        result_data = json.load(f)
                    run_setting = result_data.get("setting")
                    if run_setting is None:
                        # Legacy: check for solo.patch
                        run_setting = "solo" if (feature_dir / "solo.patch").exists() else "coop"

                runs.append(
                    {
                        "repo": repo_dir.name,
                        "task_id": task_id,
                        "features": features,
                        "log_dir": str(feature_dir),
                        "setting": run_setting,
                    }
                )

    return runs


def _evaluate_single(run_info: dict, force: bool = False) -> dict | None:
    """Evaluate a single run."""
    log_dir = Path(run_info["log_dir"])
    eval_file = log_dir / "eval.json"

    if eval_file.exists() and not force:
        with open(eval_file) as f:
            return {"skipped": True, **json.load(f)}

    setting = run_info["setting"]
    repo = run_info["repo"]
    task_id = run_info["task_id"]
    features = run_info["features"]
    f1, f2 = features[0], features[1]

    if setting == "solo":
        # Solo evaluation
        patch_file = log_dir / "solo.patch"
        patch = patch_file.read_text() if patch_file.exists() else ""

        result = test_solo(
            repo_name=repo,
            task_id=task_id,
            feature1_id=f1,
            feature2_id=f2,
            patch=patch,
        )

        eval_result = {
            "repo": repo,
            "task_id": task_id,
            "features": features,
            "setting": "solo",
            "merge": None,
            "feature1": result.get("feature1", {}),
            "feature2": result.get("feature2", {}),
            "both_passed": result.get("both_passed", False),
            "error": result.get("error"),
            "evaluated_at": datetime.now().isoformat(),
        }
    else:
        # Coop evaluation - merge two agent patches
        patch1_file = log_dir / f"agent{f1}.patch"
        patch2_file = log_dir / f"agent{f2}.patch"

        patch1 = patch1_file.read_text() if patch1_file.exists() else ""
        patch2 = patch2_file.read_text() if patch2_file.exists() else ""

        result = test_merged(
            repo_name=repo,
            task_id=task_id,
            feature1_id=f1,
            feature2_id=f2,
            patch1=patch1,
            patch2=patch2,
        )

        eval_result = {
            "repo": repo,
            "task_id": task_id,
            "features": features,
            "setting": "coop",
            "merge": result.get("merge", {}),
            "feature1": result.get("feature1", {}),
            "feature2": result.get("feature2", {}),
            "both_passed": result.get("both_passed", False),
            "error": result.get("error"),
            "evaluated_at": datetime.now().isoformat(),
        }

    # Save result
    with open(eval_file, "w") as f:
        json.dump(eval_result, f, indent=2)

    return eval_result


__all__ = ["evaluate", "discover_runs"]
