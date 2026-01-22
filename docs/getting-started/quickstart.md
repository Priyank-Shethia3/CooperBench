# Quick Start

This guide walks through running your first CooperBench experiment.

## Prerequisites

1. Install CooperBench with LLM support:
   ```bash
   pip install cooperbench[llm]
   ```

2. Set up your API keys in `.env`:
   ```bash
   ANTHROPIC_API_KEY=your_key_here
   ```

3. Have a dataset task available in `dataset/<repo_name>/task<task_id>/`

## Dataset Structure

CooperBench expects tasks organized as:

```
dataset/
  pallets_jinja_task/
    task1621/
      setup.sh          # Repository setup script
      run_tests.sh      # Test runner script
      feature1/
        feature.md      # Feature 1 description
        feature.patch   # Golden implementation
        tests.patch     # Test cases
      feature2/
        feature.md      # Feature 2 description
        feature.patch   # Golden implementation
        tests.patch     # Test cases
```

## Running Planning

### Single Agent (One Feature)

```bash
cooperbench plan \
    --setting single \
    --repo-name pallets_jinja_task \
    --task-id 1621 \
    --feature1-id 1 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --not-save-to-hf
```

### Cooperative Planning (Two Agents)

```bash
cooperbench plan \
    --setting coop \
    --repo-name pallets_jinja_task \
    --task-id 1621 \
    --feature1-id 1 \
    --feature2-id 2 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --model2 anthropic/claude-sonnet-4-5-20250929 \
    --not-save-to-hf
```

## Output

Planning outputs are saved to `logs/<setting>/<repo_name>/task<task_id>/`:

- `plan_<model>_k<k>_feature<id>.md` - Implementation plan
- `planning_traj_<model>_k<k>.json` - Full trajectory log

## Python API

```python
import asyncio
from cooperbench import BenchSetting, FileInterface
from cooperbench.planning import create_plan

async def run_experiment():
    interface = FileInterface(
        setting=BenchSetting.SINGLE,
        repo_name="pallets_jinja_task",
        task_id=1621,
        k=1,
        feature1_id=1,
        model1="anthropic/claude-sonnet-4-5-20250929",
        save_to_hf=False,
    )
    
    await create_plan(interface, max_iterations=25)

asyncio.run(run_experiment())
```

## Running Execution

After planning, execute the implementation plan:

```bash
cooperbench execute \
    --setting single \
    --repo-name pallets_jinja_task \
    --task-id 1621 \
    --feature1-id 1 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --plan-location logs \
    --not-save-to-hf
```

Execution requires Docker with OpenHands images.

## Running Evaluation

After execution, evaluate the generated patches:

```bash
cooperbench evaluate \
    --setting single \
    --repo-name pallets_jinja_task \
    --task-id 1621 \
    --feature1-id 1 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --eval-type test \
    --patch-location logs \
    --not-save-to-hf
```

## Full Experiment Workflow

```bash
# 1. Planning - generate implementation plan
cooperbench plan --setting single --repo-name my_repo --task-id 123 \
    --feature1-id 1 --model1 gpt-5 --not-save-to-hf

# 2. Execution - run the plan to generate code
cooperbench execute --setting single --repo-name my_repo --task-id 123 \
    --feature1-id 1 --model1 gpt-5 --plan-location logs --not-save-to-hf

# 3. Evaluation - test the generated code
cooperbench evaluate --setting single --repo-name my_repo --task-id 123 \
    --feature1-id 1 --model1 gpt-5 --eval-type test --patch-location logs --not-save-to-hf
```

## Next Steps

- Read about [Experiment Settings](../concepts/settings.md) to understand the different modes
- Learn about the [Planning Phase](../guide/planning.md) in detail
- Explore the [Execution Phase](../guide/execution.md) for Docker setup
- Review [Evaluation Phase](../guide/evaluation.md) for metrics
- Explore the [System Design](../concepts/design.md) to understand the architecture
