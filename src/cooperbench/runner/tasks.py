"""Task discovery from dataset/ directory."""

from itertools import combinations
from pathlib import Path


def discover_tasks(
    repo_filter: str | None = None,
    task_filter: int | None = None,
    features_filter: list[int] | None = None,
) -> list[dict]:
    """Discover benchmark tasks from dataset/.

    Args:
        repo_filter: Filter by repository name
        task_filter: Filter by task ID
        features_filter: Specific feature pair to use

    Returns:
        List of task dicts with repo, task_id, features
    """
    dataset_dir = Path("dataset")
    tasks = []

    for repo_dir in sorted(dataset_dir.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name == "README.md":
            continue
        if repo_filter and repo_filter != repo_dir.name:
            continue

        for task_dir in sorted(repo_dir.iterdir()):
            if not task_dir.is_dir() or not task_dir.name.startswith("task"):
                continue

            task_id = int(task_dir.name.replace("task", ""))
            if task_filter and task_filter != task_id:
                continue

            feature_ids = []
            for feature_dir in sorted(task_dir.iterdir()):
                if feature_dir.is_dir() and feature_dir.name.startswith("feature"):
                    fid = int(feature_dir.name.replace("feature", ""))
                    feature_ids.append(fid)

            if len(feature_ids) < 2:
                continue

            if features_filter:
                if all(f in feature_ids for f in features_filter):
                    tasks.append(
                        {
                            "repo": repo_dir.name,
                            "task_id": task_id,
                            "features": features_filter,
                        }
                    )
            else:
                # All pairwise combinations: nC2
                feature_ids.sort()
                for f1, f2 in combinations(feature_ids, 2):
                    tasks.append(
                        {
                            "repo": repo_dir.name,
                            "task_id": task_id,
                            "features": [f1, f2],
                        }
                    )

    return tasks
