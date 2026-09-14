#!/bin/bash
# Build script for Calculator Review Agent
# Builds the ARM64 container image using the public PyPI SDK.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="${1:-calculator-review-agent}"
IMAGE_TAG="${2:-latest}"

echo "=== Calculator Review Agent Build ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# Detect container runtime
if command -v finch &>/dev/null; then
    RUNTIME="finch"
elif command -v docker &>/dev/null; then
    RUNTIME="docker"
else
    echo "ERROR: No container runtime found. Install finch or docker."
    exit 1
fi

echo "Using runtime: ${RUNTIME}"
echo "Building ARM64 container image..."
${RUNTIME} build --platform linux/arm64 -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"

echo ""
echo "=== Build complete ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Next steps:"
echo "  1. Tag and push to ECR:"
echo "     ${RUNTIME} tag ${IMAGE_NAME}:${IMAGE_TAG} <account>.dkr.ecr.us-east-1.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}"
echo "     ${RUNTIME} push <account>.dkr.ecr.us-east-1.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}"
echo "  2. Or run the full deploy script: ./deploy.sh"
