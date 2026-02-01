#!/bin/bash
# Build a GCP VM image with all CooperBench Docker images pre-pulled.
#
# This eliminates Docker pull time during evaluation runs.
#
# Usage:
#   ./scripts/build_gcp_vm_image.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GOOGLE_CLOUD_PROJECT environment variable set
#
# The script will:
#   1. Create a temporary VM
#   2. Pull all CooperBench Docker images
#   3. Create a VM image from the disk
#   4. Delete the temporary VM

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-4"
DISK_SIZE="200GB"
VM_NAME="cooperbench-image-builder"
IMAGE_FAMILY="cooperbench-eval"
IMAGE_NAME="cooperbench-eval-$(date +%Y%m%d)"

# Registry where CooperBench images are stored
REGISTRY="akhatua"
IMAGE_PREFIX="cooperbench"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT environment variable not set"
    echo "Run: export GOOGLE_CLOUD_PROJECT=your-project-id"
    exit 1
fi

echo "=============================================="
echo "CooperBench VM Image Builder"
echo "=============================================="
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Image name: $IMAGE_NAME"
echo "Image family: $IMAGE_FAMILY"
echo ""

# Get list of all tasks from dataset
echo "Scanning dataset for tasks..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DATASET_DIR="$REPO_ROOT/dataset"

if [ ! -d "$DATASET_DIR" ]; then
    echo "Error: Dataset directory not found: $DATASET_DIR"
    exit 1
fi

# Build list of Docker images to pull
IMAGES=()
for repo_dir in "$DATASET_DIR"/*_task; do
    if [ -d "$repo_dir" ]; then
        repo_name=$(basename "$repo_dir")
        # Convert repo name: llama_index_task -> llama-index
        image_repo=$(echo "$repo_name" | sed 's/_task$//' | tr '_' '-')

        for task_dir in "$repo_dir"/task*; do
            if [ -d "$task_dir" ]; then
                task_id=$(basename "$task_dir" | sed 's/task//')
                image="$REGISTRY/$IMAGE_PREFIX-$image_repo:task$task_id"
                IMAGES+=("$image")
            fi
        done
    fi
done

# Also add typst if it exists (no _task suffix)
if [ -d "$DATASET_DIR/typst" ]; then
    for task_dir in "$DATASET_DIR/typst"/task*; do
        if [ -d "$task_dir" ]; then
            task_id=$(basename "$task_dir" | sed 's/task//')
            image="$REGISTRY/$IMAGE_PREFIX-typst:task$task_id"
            IMAGES+=("$image")
        fi
    done
fi

echo "Found ${#IMAGES[@]} Docker images to pre-pull:"
for img in "${IMAGES[@]}"; do
    echo "  - $img"
done
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Create VM
echo ""
echo "Step 1: Creating VM..."
gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --boot-disk-size="$DISK_SIZE" \
    --boot-disk-type=pd-ssd \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only

echo "Waiting for VM to be ready..."
sleep 30

# Pull all images
echo ""
echo "Step 2: Pulling Docker images..."

# Create pull script
PULL_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

IMAGES=(
EOF
)

for img in "${IMAGES[@]}"; do
    PULL_SCRIPT+="    \"$img\""$'\n'
done

PULL_SCRIPT+=$(cat <<'EOF'
)

echo "Pulling ${#IMAGES[@]} images..."
for img in "${IMAGES[@]}"; do
    echo "Pulling: $img"
    docker pull "$img" || echo "Warning: Failed to pull $img"
done

echo "All images pulled!"
docker images
EOF
)

# Run pull script on VM
echo "$PULL_SCRIPT" | gcloud compute ssh "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --command="bash -s"

# Also pull cloud-sdk for gsutil
echo "Pulling cloud-sdk image for gsutil..."
gcloud compute ssh "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --command="docker pull gcr.io/google.com/cloudsdktool/cloud-sdk:slim"

# Stop VM
echo ""
echo "Step 3: Stopping VM..."
gcloud compute instances stop "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE"

# Create image
echo ""
echo "Step 4: Creating VM image..."
gcloud compute images create "$IMAGE_NAME" \
    --project="$PROJECT_ID" \
    --source-disk="$VM_NAME" \
    --source-disk-zone="$ZONE" \
    --family="$IMAGE_FAMILY" \
    --description="CooperBench eval VM with pre-pulled Docker images ($(date +%Y-%m-%d))"

# Delete VM
echo ""
echo "Step 5: Cleaning up VM..."
gcloud compute instances delete "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --quiet

echo ""
echo "=============================================="
echo "SUCCESS!"
echo "=============================================="
echo ""
echo "VM Image created: $IMAGE_NAME"
echo "Image family: $IMAGE_FAMILY"
echo ""
echo "To use this image in CooperBench:"
echo ""
echo "  from cooperbench.eval.backends import get_batch_evaluator"
echo "  evaluator = get_batch_evaluator('gcp')"
echo "  evaluator._vm_image = '$IMAGE_FAMILY'"
echo ""
echo "Or set in code:"
echo ""
echo "  from cooperbench.eval.backends.gcp import GCPBatchEvaluator"
echo "  evaluator = GCPBatchEvaluator(vm_image='$IMAGE_FAMILY')"
echo ""
