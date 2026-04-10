#!/bin/bash
#
# Simple Deploy - Business Case Generator to AWS (No OIDC/Domain/Certificate)
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "=========================================="
echo "Business Case Generator - Simple AWS Deployment"
echo "No OIDC / No Custom Domain / No Certificate"
echo "=========================================="
echo ""

# ====================================================================
# Prerequisites Check
# ====================================================================
echo_info "Checking prerequisites..."
echo ""

# Check AWS CLI
if ! command -v aws &>/dev/null; then
    echo_error "AWS CLI is not installed"
    echo "Install with:"
    echo "  macOS:   brew install awscli"
    echo "  Linux:   pip install awscli"
    exit 1
fi

# Check AWS credentials
echo_info "Checking AWS credentials..."
if ! aws sts get-caller-identity &>/dev/null; then
    echo_error "AWS credentials not configured"
    echo "Please configure AWS CLI with: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo_info "✓ AWS CLI configured"
echo_info "  Account: $AWS_ACCOUNT"
echo_info "  Region: $AWS_REGION"
echo ""

# Check Node.js
if ! command -v node &>/dev/null; then
    echo_error "Node.js is not installed"
    exit 1
fi

NODE_VERSION=$(node --version)
echo_info "✓ Node.js installed: $NODE_VERSION"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo_info "✓ Python installed: $PYTHON_VERSION"
echo ""

# Check Docker or Finch
DOCKER_CMD=""
DOCKER_WRAPPER_CLEANUP=""

if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    echo_info "✓ Docker is installed and running"
    DOCKER_CMD="docker"
elif command -v finch &>/dev/null && finch info &>/dev/null 2>&1; then
    echo_info "✓ Finch is installed and running"
    echo_info "  Creating Docker compatibility wrapper..."
    
    TEMP_BIN=$(mktemp -d)
    cat > "$TEMP_BIN/docker" << 'DOCKERWRAPPER'
#!/bin/bash
exec finch "$@"
DOCKERWRAPPER
    chmod +x "$TEMP_BIN/docker"
    export PATH="$TEMP_BIN:$PATH"
    DOCKER_CMD="finch"
    DOCKER_WRAPPER_CLEANUP="$TEMP_BIN"
    
    if ! docker info &>/dev/null 2>&1; then
        echo_error "Failed to create Docker wrapper for Finch"
        rm -rf "$TEMP_BIN"
        exit 1
    fi
    echo_info "  ✓ Docker wrapper created"
else
    echo_error "Neither Docker nor Finch is installed or running"
    exit 1
fi
echo ""

# Check CDK CLI
if ! command -v cdk &>/dev/null; then
    echo_warn "AWS CDK CLI is not installed"
    read -p "Install AWS CDK CLI now? (Y/n): " INSTALL_CDK
    if [[ ! $INSTALL_CDK =~ ^[Nn]$ ]]; then
        echo_info "Installing AWS CDK CLI..."
        npm install -g aws-cdk
        echo_info "✓ CDK CLI installed"
    else
        echo_error "CDK CLI is required. Install with: npm install -g aws-cdk"
        exit 1
    fi
else
    CDK_VERSION=$(cdk --version 2>&1 | head -1)
    echo_info "✓ AWS CDK CLI installed: $CDK_VERSION"
fi
echo ""

echo_info "✓ All prerequisites satisfied"
echo ""

echo "=========================================="
echo "Deployment Configuration"
echo "=========================================="
echo ""
echo_warn "This deployment will:"
echo "  • Create an Application Load Balancer (HTTP only)"
echo "  • Deploy ECS Fargate service"
echo "  • Create S3 buckets and DynamoDB table"
echo "  • NO authentication (open access)"
echo "  • NO custom domain"
echo "  • NO SSL certificate"
echo ""
echo_warn "Security Note: This is suitable for testing/demo only."
echo_warn "For production, use deploy.sh with OIDC authentication."
echo ""

read -p "Proceed with simple deployment? (Y/n): " PROCEED
if [[ $PROCEED =~ ^[Nn]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Create/activate Python virtual environment
echo_info "Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install CDK dependencies
echo_info "Installing CDK dependencies..."
python3 -m pip install -q -r requirements.txt

# Bootstrap CDK (if needed)
echo_info "Checking CDK bootstrap..."
BOOTSTRAP_NEEDED=false

STACK_STATUS=$(aws cloudformation describe-stacks --stack-name CDKToolkit --region $AWS_REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
    echo_info "CDKToolkit stack not found"
    BOOTSTRAP_NEEDED=true
elif [ "$STACK_STATUS" = "DELETE_FAILED" ]; then
    echo_warn "CDKToolkit stack is in DELETE_FAILED state - cleaning up..."
    aws cloudformation delete-stack --stack-name CDKToolkit --region $AWS_REGION
    echo_info "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region $AWS_REGION 2>/dev/null || true
    BOOTSTRAP_NEEDED=true
else
    if ! aws ssm get-parameter --name /cdk-bootstrap/hnb659fds/version --region $AWS_REGION &>/dev/null; then
        echo_warn "CDKToolkit stack exists but SSM parameter missing - re-bootstrapping"
        BOOTSTRAP_NEEDED=true
    fi
fi

if [ "$BOOTSTRAP_NEEDED" = true ]; then
    echo_info "Bootstrapping CDK..."
    cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
else
    echo_info "✓ CDK already bootstrapped"
fi

# Build frontend
echo_info "Building React frontend..."
cd ../../ui
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ../infrastructure/cdk

# Synthesize CDK stack using simple app
echo_info "Synthesizing CDK stack (simple deployment)..."
cdk synth --app "python3 app-simple.py"

# Deploy
echo ""
echo_info "Deploying to AWS..."
echo_warn "This will take 5-10 minutes..."
echo ""

cdk deploy --app "python3 app-simple.py" --require-approval never

# Cleanup Docker wrapper if created
if [ -n "$DOCKER_WRAPPER_CLEANUP" ]; then
    rm -rf "$DOCKER_WRAPPER_CLEANUP"
fi

echo ""
echo "=========================================="
echo_info "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo_info "Getting application URL..."
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name BusinessCaseGeneratorSimpleStack \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSOutput`].OutputValue' \
    --output text)

echo ""
echo_info "Application URL: http://$ALB_DNS"
echo ""
echo_warn "Note: This deployment has NO authentication."
echo_warn "Anyone with the URL can access the application."
echo ""
echo_info "Next steps:"
echo "  1. Wait 2-3 minutes for ECS service to start"
echo "  2. Access http://$ALB_DNS"
echo "  3. For production, redeploy with OIDC using deploy.sh"
echo ""
