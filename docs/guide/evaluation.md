# Evaluation Phase

The evaluation phase measures the quality of agent-generated code changes through test execution and merge conflict analysis.

## Overview

Evaluation performs:

1. **Test Execution**: Run test suite against generated patches
2. **Merge Analysis**: Check if patches from multiple agents can merge cleanly
3. **Conflict Scoring**: Quantify the severity of any merge conflicts

## Running Evaluation

### Via CLI

```bash
# Test evaluation (single/solo)
cooperbench evaluate \
    --setting single \
    --repo-name pallets_click_task \
    --task-id 2068 \
    --feature1-id 1 \
    --model1 gpt-5 \
    --eval-type test \
    --patch-location logs \
    --not-save-to-hf

# Merge evaluation (coop/coop_ablation)
cooperbench evaluate \
    --setting coop \
    --repo-name pallets_click_task \
    --task-id 2068 \
    --feature1-id 1 \
    --feature2-id 2 \
    --model1 gpt-5 \
    --model2 gpt-5 \
    --eval-type merge \
    --patch-location logs \
    --not-save-to-hf
```

### Via Python API

```python
import asyncio
from cooperbench import BenchSetting, FileInterface
from cooperbench.evaluation import evaluate

async def run():
    interface = FileInterface(
        setting=BenchSetting.COOP,
        repo_name="pallets_click_task",
        task_id=2068,
        k=1,
        feature1_id=1,
        feature2_id=2,
        model1="gpt-5",
        model2="gpt-5",
        save_to_hf=False,
    )

    results = await evaluate(interface, eval_type="merge", file_location="logs")
    print(f"Conflict score: {results['conflict_score']}")

asyncio.run(run())
```

## Evaluation Types

| Type | Settings | Description |
|------|----------|-------------|
| `test` | single, solo | Run feature tests against patch |
| `merge` | coop, coop_ablation | Merge analysis + tests |

## Metrics

### Test Pass Rate

Whether all feature tests pass after applying the patch.

### Merge Status

Whether two patches can be merged:

- `clean` - No conflicts, git merge succeeds
- `conflicts` - Has merge conflicts

### Conflict Score

Quantifies merge conflict severity:

```python
conflict_score = (conflict_sections * 20) + (conflict_lines * 2)
```

## Patch Locations

Patches can be loaded from:

| Location | Description |
|----------|-------------|
| `logs` | Local logs directory (default) |
| `cache` | Local cache (previously downloaded from HF) |
| `hf` | Download fresh from HuggingFace |

## Output Files

| File | Description |
|------|-------------|
| `test_result_*.json` | Test execution results |
| `merge_report_*.json` | Merge analysis report |

## Merge Report Format

```json
{
  "repo_name": "pallets_click_task",
  "task_id": 2068,
  "timestamp": "2024-01-15 10:30:00",
  "feature1": {
    "number": 1,
    "tests_passed": true,
    "test_output": "..."
  },
  "feature2": {
    "number": 2,
    "tests_passed": true,
    "test_output": "..."
  },
  "merge_status": "conflicts",
  "conflict_score": 42,
  "conflict_details": {
    "conflict_sections": 2,
    "conflict_lines": 11,
    "avg_lines_per_conflict": 5.5
  }
}
```

## Test Script

Each task has a `run_tests.sh` script that:

1. Applies the test patch
2. Runs the test suite
3. Returns exit code 0 for pass, non-zero for fail

```bash
# Called internally by the evaluation
./run_tests.sh <workspace_path> <tests_patch_path>
```
