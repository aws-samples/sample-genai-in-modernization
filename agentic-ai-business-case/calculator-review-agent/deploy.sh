#!/bin/bash
# Full deployment pipeline for Calculator Review Agent
# Build → Push to ECR → Update AgentCore Runtime

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
AWS_ACCOUNT="${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_NAME="${IMAGE_NAME:-calculator-review-agent}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
ECR_REPO="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"

echo "=== Calculator Review Agent Deployment ==="
echo "Account:  ${AWS_ACCOUNT}"
echo "Region:   ${AWS_REGION}"
echo "Image:    ${ECR_REPO}:${IMAGE_TAG}"
echo ""

# Step 1: Build the image
echo "[1/4] Building container image..."
"${SCRIPT_DIR}/build.sh" "${IMAGE_NAME}" "${IMAGE_TAG}"
echo ""

# Step 2: Ensure ECR repository exists
echo "[2/4] Ensuring ECR repository exists..."
if command -v finch &>/dev/null; then
    RUNTIME="finch"
else
    RUNTIME="docker"
fi

aws ecr describe-repositories --repository-names "${IMAGE_NAME}" --region "${AWS_REGION}" 2>/dev/null || \
    aws ecr create-repository --repository-name "${IMAGE_NAME}" --region "${AWS_REGION}" --image-scanning-configuration scanOnPush=true

# Step 3: Push to ECR
echo "[3/4] Pushing to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | ${RUNTIME} login --username AWS --password-stdin "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
${RUNTIME} tag "${IMAGE_NAME}:${IMAGE_TAG}" "${ECR_REPO}:${IMAGE_TAG}"
${RUNTIME} tag "${IMAGE_NAME}:${IMAGE_TAG}" "${ECR_REPO}:latest"
${RUNTIME} push "${ECR_REPO}:${IMAGE_TAG}"
${RUNTIME} push "${ECR_REPO}:latest"
echo "  Pushed: ${ECR_REPO}:${IMAGE_TAG}"

# Step 4: Update AgentCore runtime
echo "[4/4] Updating AgentCore runtime..."
RUNTIME_NAME="calculator_review_agent_v$(date +%Y%m%d%H%M)"
echo "  Creating new runtime: ${RUNTIME_NAME}"

aws bedrock-agentcore-control create-agent-runtime \
    --agent-runtime-name "${RUNTIME_NAME}" \
    --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${ECR_REPO}:${IMAGE_TAG}\"}}" \
    --network-configuration '{"networkMode":"PUBLIC"}' \
    --role-arn "arn:aws:iam::${AWS_ACCOUNT}:role/AgentCoreExecutionRole" \
    --region "${AWS_REGION}"

echo ""
echo "=== Deployment initiated ==="
echo "Runtime: ${RUNTIME_NAME}"
echo "Image:   ${ECR_REPO}:${IMAGE_TAG}"
echo ""
echo "Monitor runtime status:"
echo "  aws bedrock-agentcore-control get-agent-runtime --agent-runtime-name ${RUNTIME_NAME} --region ${AWS_REGION}"
echo ""
echo "Once READY, update your agent registration with the new runtime ARN."
