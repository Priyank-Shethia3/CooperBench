# Quick Start: GCP Backend

Get started with GCP backend in 3 simple steps.

## Prerequisites

Before you begin, make sure you have:
- **GCP Account**: Sign up at [cloud.google.com](https://cloud.google.com) (free tier includes $300 credit)
- **gcloud CLI**: Required for authentication
  - macOS: `brew install google-cloud-sdk`
  - Linux: `curl https://sdk.cloud.google.com | bash`
  - Windows: Download from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install)
- **Billing Enabled**: Required for Compute Engine (enable at [console.cloud.google.com/billing](https://console.cloud.google.com/billing))

## Step 1: Install CooperBench with GCP Support

```bash
pip install 'cooperbench[gcp]'
```

This installs CooperBench and the required Google Cloud libraries.

## Step 2: Configure GCP

Run the interactive setup wizard:

```bash
cooperbench config gcp
```

The wizard will guide you through:
1. Checking prerequisites (gcloud CLI, Python packages)
2. Authenticating with Google (opens browser automatically)
3. Selecting your GCP project, region, and zone
4. Validating API access

**That's it!** Your configuration is saved automatically and will be used for all GCP operations.

## Step 3: Run Experiments

Just add `--backend gcp` to any cooperbench command:

```bash
# Run agents on benchmark tasks
cooperbench run --backend gcp -s lite

# Evaluate results
cooperbench eval --backend gcp -n experiment-name
```

The configuration from Step 2 is automatically loaded - no need to set environment variables!

## Complete Example

```bash
# One-time setup
pip install 'cooperbench[gcp]'
cooperbench config gcp

# Run cooperative agents with GCP
cooperbench run \
  --backend gcp \
  --setting coop \
  -s lite \
  -m gemini/gemini-3-flash-preview

# Evaluate with GCP Batch (scales to 100s of parallel tasks)
cooperbench eval \
  --backend gcp \
  -n coop-lite-gemini-3-flash \
  --concurrency 50
```

## Required APIs

The configuration wizard will test access to these APIs and provide links if they need to be enabled:
- **Compute Engine API**: For running VMs
- **Cloud Batch API**: For parallel evaluation
- **Cloud Storage API**: For storing results

The wizard handles API testing automatically - you don't need to enable them manually unless the wizard prompts you.

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
