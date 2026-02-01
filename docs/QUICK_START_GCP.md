# Quick Start: GCP Backend

Get started with GCP backend in 3 simple steps.

## Step 1: Install Dependencies

```bash
uv pip install 'cooperbench[gcp]'
```

Or using pip:
```bash
pip install 'cooperbench[gcp]'
```

## Step 2: Configure GCP

Run the interactive setup wizard:

```bash
uv run cooperbench config gcp
```

The wizard will:
- ✓ Check if gcloud CLI is installed
- ✓ Verify Python dependencies
- 🔐 Guide you through authentication
- 📝 Help you select project, region, and zone
- ✅ Validate your setup

**That's it!** Configuration is saved automatically.

## Step 3: Run with GCP

Use GCP backend with the `--backend gcp` flag:

```bash
# Run agents on benchmark tasks
uv run cooperbench run --backend gcp -s lite

# Evaluate results
uv run cooperbench eval --backend gcp -n experiment-name
```

## Full Example

```bash
# One-time setup
uv pip install 'cooperbench[gcp]'
uv run cooperbench config gcp

# Run cooperative agents with GCP
uv run cooperbench run \
  --backend gcp \
  --setting coop \
  -s lite \
  -m gemini/gemini-3-flash-preview

# Evaluate with GCP Batch (fast parallel evaluation)
uv run cooperbench eval \
  --backend gcp \
  -n coop-lite-gemini-3-flash \
  --concurrency 50
```

## What You Need

### Prerequisites
- **GCP Account**: Free tier available at [cloud.google.com](https://cloud.google.com)
- **gcloud CLI**: Install from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install)
  - macOS: `brew install google-cloud-sdk`
  - Linux: `curl https://sdk.cloud.google.com | bash`
- **Billing Enabled**: Required for Compute Engine

### Required APIs
The wizard will guide you to enable these:
- Compute Engine API
- Cloud Batch API
- Cloud Storage API

## Configuration Details

### Where is config stored?
- macOS: `~/Library/Application Support/cooperbench/config.json`
- Linux: `~/.config/cooperbench/config.json`
- Windows: `%APPDATA%\cooperbench\config.json`

### What is saved?
```json
{
  "gcp_project_id": "your-project-id",
  "gcp_region": "us-central1",
  "gcp_zone": "us-central1-a",
  "gcp_bucket": "cooperbench-eval-your-project-id"
}
```

### How to reconfigure?
Just run the wizard again:
```bash
uv run cooperbench config gcp
```

## Cost Estimate

Using default settings:

- **Small run** (10 tasks): $0.05 - $0.15
- **Medium run** (100 tasks): $0.50 - $1.50
- **Large run** (1000 tasks): $5.00 - $10.00

Costs include VM compute + storage. GCP free tier includes $300 credit for new users.

## Troubleshooting

### gcloud not found
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Verify
gcloud version
```

### Not authenticated

```
Error: Your default credentials were not found
```

You need **both** types of authentication:

```bash
# 1. Authenticate gcloud CLI
gcloud auth login

# 2. Set up Application Default Credentials (REQUIRED)
gcloud auth application-default login
```

The second command is **required** for the GCP Python SDK to work.

### API not enabled
The wizard provides clickable links, or manually enable:
```bash
gcloud services enable \
  compute.googleapis.com \
  batch.googleapis.com \
  storage.googleapis.com
```

### Permission denied
Ensure your GCP account has these roles:
- Compute Instance Admin
- Batch Job Editor
- Storage Admin

## Comparison: Modal vs GCP

| | Modal (Default) | GCP |
|---|---|---|
| **Setup** | `modal setup` | `cooperbench config gcp` |
| **Account** | Modal account | GCP account |
| **Cost** | Modal credits | Pay-as-you-go |
| **Scale** | Auto-scaling | Up to quotas |
| **Free tier** | Limited | $300 credit |

## Next Steps

- 📖 Read full guide: [GCP Setup Guide](GCP_SETUP.md)
- 🚀 Run your first experiment
- 📊 Check results in `logs/` directory
- 🔧 Customize with advanced options

## Need Help?

- GitHub Issues: [cooperbench/CooperBench](https://github.com/cooperbench/CooperBench/issues)
- GCP Docs: [cloud.google.com/docs](https://cloud.google.com/docs)
- CooperBench Docs: [cooperbench.com](https://cooperbench.com)
