# Execution Phase

The execution phase takes implementation plans and generates actual code changes using the OpenHands agent framework.

## Overview

Execution uses [OpenHands](https://github.com/All-Hands-AI/OpenHands) to:

1. Load the implementation plan from the planning phase
2. Execute changes in a sandboxed Docker environment
3. Generate a patch file with the changes

## Prerequisites

### Docker

Docker must be installed and running:

```bash
docker info  # Verify Docker is running
```

### For `coop` Mode: Build Custom OpenHands Images

The `coop` setting requires custom OpenHands Docker images with MCP (Model Context Protocol) support for inter-agent communication.

#### 1. Initialize the Submodule

```bash
cd CooperBench
git submodule update --init --recursive
```

This downloads the custom OpenHands fork from `https://github.com/akhatua2/openhands_colab`.

#### 2. Build Docker Images

```bash
cd src/cooperbench/execution/openhands_colab
./build
```

This builds two custom Docker images:
- `colab/openhands_colab:latest` - Custom OpenHands core with MCP auto-injection
- `colab/openhands_runtime_colab:latest` - Custom OpenHands runtime

**Note:** Building requires `poetry` to be installed.

## Running Execution

### Via CLI

```bash
# Single agent execution
cooperbench execute \
    --setting single \
    --repo-name pallets_click_task \
    --task-id 2068 \
    --feature1-id 1 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --plan-location logs \
    --not-save-to-hf

# Cooperative execution (two agents with MCP communication)
cooperbench execute \
    --setting coop \
    --repo-name pallets_click_task \
    --task-id 2068 \
    --feature1-id 1 \
    --feature2-id 2 \
    --model1 anthropic/claude-sonnet-4-5-20250929 \
    --model2 anthropic/claude-sonnet-4-5-20250929 \
    --plan-location logs \
    --not-save-to-hf
```

### Via Python API

```python
import asyncio
from cooperbench import BenchSetting, FileInterface
from cooperbench.execution import create_execution

async def run():
    interface = FileInterface(
        setting=BenchSetting.SINGLE,
        repo_name="pallets_click_task",
        task_id=2068,
        k=1,
        feature1_id=1,
        model1="anthropic/claude-sonnet-4-5-20250929",
        save_to_hf=False,
    )

    await create_execution(interface, plan_location="logs")

asyncio.run(run())
```

## Execution by Setting

| Setting | Docker Images | Behavior |
|---------|--------------|----------|
| `single` | Stock OpenHands | Single agent executes one feature |
| `solo` | Stock OpenHands | Single agent executes both features |
| `coop` | Custom Colab images | Two agents with MCP communication |
| `coop_ablation` | Stock OpenHands | Two agents in parallel, no communication |

## Plan Locations

| Location | Description |
|----------|-------------|
| `logs` | Local logs directory (default) |
| `cache` | Local cache (previously downloaded from HF) |
| `hf` | Download fresh from HuggingFace |

## Output Files

| File | Description |
|------|-------------|
| `patch_<model>_k<k>_feature<id>.patch` | Git diff of changes |
| `execution_traj_<model>_k<k>.json` | OpenHands trajectory |
| `conversation_<model>.json` | Inter-agent messages (coop only) |

## MCP Communication (Coop Mode)

In `coop` mode, agents communicate via Model Context Protocol:

1. **Shared Database**: SQLite database stores messages between agents
2. **Auto-Injection**: Messages are automatically injected into agent context
3. **Coordination**: Agents share file paths and line numbers to avoid conflicts

Example agent message:
```
[Inter-agent message from agent_2]:
I'm modifying src/auth.py lines 50-80. Please avoid that section.
```

## Environment Variables

```bash
# OpenHands images (stock)
OPENHANDS_IMAGE=docker.all-hands.dev/all-hands-ai/openhands:0.54
RUNTIME_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.54-nikolaik

# LLM configuration
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

## Troubleshooting

### Docker Images Not Found

For `coop` mode, ensure you've built the custom images:

```bash
cd src/cooperbench/execution/openhands_colab
./build
```

### Permission Errors

Ensure Docker has access to workspace directories:

```bash
chmod -R 755 dataset/
```

### Submodule Not Initialized

If the openhands_colab directory is empty:

```bash
git submodule update --init --recursive
```
