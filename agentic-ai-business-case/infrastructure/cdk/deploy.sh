#!/bin/bash
#
# Deploy Business Case Generator to AWS - Option 4 (Simple ALB)
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

echo_prompt() {
    echo -e "${BLUE}[INPUT]${NC} $1"
}

echo ""
echo "=========================================="
echo "Business Case Generator - AWS Deployment"
echo "Option 4: Simple ALB Architecture"
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
    echo "AWS CLI is required to deploy infrastructure to AWS"
    echo ""
    echo "Install with:"
    echo "  macOS:   brew install awscli"
    echo "  Linux:   pip install awscli"
    echo "  Windows: https://aws.amazon.com/cli/"
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

# Check Node.js and npm
if ! command -v node &>/dev/null; then
    echo_error "Node.js is not installed"
    echo "Node.js is required to build the React frontend"
    echo ""
    echo "Install with:"
    echo "  macOS:   brew install node"
    echo "  Linux:   https://nodejs.org/"
    echo "  Windows: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &>/dev/null; then
    echo_error "npm is not installed"
    echo "npm is required to build the React frontend"
    exit 1
fi

NODE_VERSION=$(node --version)
echo_info "✓ Node.js installed: $NODE_VERSION"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo_error "Python 3 is not installed"
    echo "Python 3 is required for AWS CDK"
    echo ""
    echo "Install with:"
    echo "  macOS:   brew install python3"
    echo "  Linux:   apt-get install python3 python3-pip"
    echo "  Windows: https://www.python.org/downloads/"
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
    
    # Create temporary docker wrapper for CDK
    TEMP_BIN=$(mktemp -d)
    cat > "$TEMP_BIN/docker" << 'DOCKERWRAPPER'
#!/bin/bash
exec finch "$@"
DOCKERWRAPPER
    chmod +x "$TEMP_BIN/docker"
    export PATH="$TEMP_BIN:$PATH"
    DOCKER_CMD="finch"
    DOCKER_WRAPPER_CLEANUP="$TEMP_BIN"
    
    # Verify wrapper works
    if ! docker info &>/dev/null 2>&1; then
        echo_error "Failed to create Docker wrapper for Finch"
        rm -rf "$TEMP_BIN"
        exit 1
    fi
    echo_info "  ✓ Docker wrapper created"
else
    echo_error "Neither Docker nor Finch is installed or running"
    echo ""
    echo "A container runtime is required to build and deploy the application."
    echo ""
    echo "Options:"
    echo "  1. Docker Desktop (recommended for most users)"
    echo "     macOS/Windows: https://www.docker.com/products/docker-desktop"
    echo "     Linux: https://docs.docker.com/engine/install/"
    echo ""
    echo "  2. Finch (lightweight alternative, AWS-supported)"
    echo "     macOS: brew install finch"
    echo "     Linux: https://github.com/runfinch/finch"
    echo ""
    echo "After installation:"
    echo "  Docker: Start Docker Desktop"
    echo "  Finch:  Run 'finch vm start'"
    exit 1
fi
echo ""

# Check CDK CLI
if ! command -v cdk &>/dev/null; then
    echo_warn "AWS CDK CLI is not installed"
    echo_info "CDK CLI is required to deploy infrastructure"
    echo ""
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

# Check if config file exists
CONFIG_FILE=".deployment-config"

if [ -f "$CONFIG_FILE" ]; then
    echo_info "Found existing configuration file: $CONFIG_FILE"
    read -p "Use existing configuration? (Y/n): " USE_EXISTING
    if [[ ! $USE_EXISTING =~ ^[Nn]$ ]]; then
        echo_info "Loading configuration from $CONFIG_FILE..."
        source "$CONFIG_FILE"
        SKIP_PROMPTS=true
    fi
fi

if [ "$SKIP_PROMPTS" != "true" ]; then
    echo ""
    echo "=========================================="
    echo "Configuration Setup"
    echo "=========================================="
    echo ""
    echo_info "Please provide the following configuration parameters."
    echo_info "These will be saved to $CONFIG_FILE for future deployments."
    echo ""
    
    # Domain Configuration
    echo_info "--- Domain Configuration ---"
    echo_prompt "Enter your custom domain name (e.g., myapp.example.com):"
    read -p "> " DOMAIN_NAME
    export DOMAIN_NAME
    
    echo_prompt "Enter your ACM certificate ARN:"
    echo_info "  (Find in AWS Console → Certificate Manager → Your certificate)"
    read -p "> " CERTIFICATE_ARN
    export CERTIFICATE_ARN
    
    echo_prompt "Enter your Route 53 Hosted Zone ID:"
    echo_info "  (Find in AWS Console → Route 53 → Hosted zones → Your domain)"
    read -p "> " HOSTED_ZONE_ID
    export HOSTED_ZONE_ID
    
    echo ""
    echo_info "--- OIDC Configuration ---"
    echo_info "Common OIDC providers and their issuer URLs:"
    echo_info "  Okta:        https://your-domain.okta.com"
    echo_info "  Auth0:       https://your-tenant.auth0.com"
    echo_info "  Keycloak:    https://your-domain.com/auth/realms/your-realm"
    echo_info "  Azure AD:    https://login.microsoftonline.com/your-tenant-id/v2.0"
    echo ""
    
    echo_prompt "Enter OIDC Issuer URL:"
    read -p "> " OIDC_ISSUER
    export OIDC_ISSUER
    
    echo_prompt "Enter OIDC Client ID:"
    read -p "> " OIDC_CLIENT_ID
    export OIDC_CLIENT_ID
    
    echo_prompt "Enter OIDC Client Secret:"
    read -s -p "> " OIDC_CLIENT_SECRET
    echo ""
    export OIDC_CLIENT_SECRET
    
    # Auto-generate endpoints from issuer
    echo ""
    echo_info "Generating OIDC endpoints from issuer URL..."
    export OIDC_AUTHORIZATION_ENDPOINT="${OIDC_ISSUER}/api/oauth2/v1/authorize"
    export OIDC_TOKEN_ENDPOINT="${OIDC_ISSUER}/api/oauth2/v2/token"
    export OIDC_USER_INFO_ENDPOINT="${OIDC_ISSUER}/api/oauth2/v1/userinfo"
    
    echo_info "  Authorization: $OIDC_AUTHORIZATION_ENDPOINT"
    echo_info "  Token: $OIDC_TOKEN_ENDPOINT"
    echo_info "  User Info: $OIDC_USER_INFO_ENDPOINT"
    echo ""
    
    read -p "Are these endpoints correct? (Y/n): " ENDPOINTS_OK
    if [[ $ENDPOINTS_OK =~ ^[Nn]$ ]]; then
        echo_prompt "Enter OIDC Authorization Endpoint:"
        read -p "> " OIDC_AUTHORIZATION_ENDPOINT
        export OIDC_AUTHORIZATION_ENDPOINT
        
        echo_prompt "Enter OIDC Token Endpoint:"
        read -p "> " OIDC_TOKEN_ENDPOINT
        export OIDC_TOKEN_ENDPOINT
        
        echo_prompt "Enter OIDC User Info Endpoint:"
        read -p "> " OIDC_USER_INFO_ENDPOINT
        export OIDC_USER_INFO_ENDPOINT
    fi
    
    # Save configuration (without secret)
    echo ""
    echo_info "Saving configuration to $CONFIG_FILE..."
    cat > "$CONFIG_FILE" << EOF
# Business Case Generator Deployment Configuration
# Generated: $(date)

# Domain Configuration
export DOMAIN_NAME="$DOMAIN_NAME"
export CERTIFICATE_ARN="$CERTIFICATE_ARN"
export HOSTED_ZONE_ID="$HOSTED_ZONE_ID"

# OIDC Configuration
export OIDC_ISSUER="$OIDC_ISSUER"
export OIDC_CLIENT_ID="$OIDC_CLIENT_ID"
export OIDC_AUTHORIZATION_ENDPOINT="$OIDC_AUTHORIZATION_ENDPOINT"
export OIDC_TOKEN_ENDPOINT="$OIDC_TOKEN_ENDPOINT"
export OIDC_USER_INFO_ENDPOINT="$OIDC_USER_INFO_ENDPOINT"

# Note: OIDC_CLIENT_SECRET is not saved for security reasons
# You will be prompted for it on each deployment
EOF
    
    echo_info "✓ Configuration saved"
    echo_warn "Note: Client secret is NOT saved for security reasons"
fi

# Prompt for client secret if using existing config (not saved for security)
if [ -z "$OIDC_CLIENT_SECRET" ]; then
    echo ""
    echo_info "--- OIDC Client Secret Required ---"
    echo_warn "Client secret is not saved in config file for security reasons"
    echo_prompt "Enter OIDC Client Secret:"
    read -s -p "> " OIDC_CLIENT_SECRET
    echo ""
    export OIDC_CLIENT_SECRET
fi
echo ""
echo_info "Validating configuration..."

REQUIRED_VARS=(
    "DOMAIN_NAME"
    "CERTIFICATE_ARN"
    "HOSTED_ZONE_ID"
    "OIDC_ISSUER"
    "OIDC_CLIENT_ID"
    "OIDC_CLIENT_SECRET"
    "OIDC_AUTHORIZATION_ENDPOINT"
    "OIDC_TOKEN_ENDPOINT"
    "OIDC_USER_INFO_ENDPOINT"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo_error "Missing required configuration:"
    for var in "${MISSING_VARS[@]}"; do
        echo_error "  - $var"
    done
    exit 1
fi

echo_info "✓ All required parameters configured"

# Show configuration summary
echo ""
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo ""
echo_info "Domain: $DOMAIN_NAME"
echo_info "Certificate: ${CERTIFICATE_ARN:0:50}..."
echo_info "Hosted Zone: $HOSTED_ZONE_ID"
echo_info "OIDC Issuer: $OIDC_ISSUER"
echo_info "OIDC Client ID: $OIDC_CLIENT_ID"
echo_info "OIDC Client Secret: ✓ Set (hidden)"
echo ""

read -p "Proceed with deployment? (Y/n): " PROCEED
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

# Check if CDKToolkit stack exists
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name CDKToolkit --region $AWS_REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
    echo_info "CDKToolkit stack not found"
    BOOTSTRAP_NEEDED=true
elif [ "$STACK_STATUS" = "DELETE_FAILED" ]; then
    echo_warn "CDKToolkit stack is in DELETE_FAILED state - cleaning up..."
    # Delete the failed stack
    aws cloudformation delete-stack --stack-name CDKToolkit --region $AWS_REGION
    echo_info "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region $AWS_REGION 2>/dev/null || true
    BOOTSTRAP_NEEDED=true
else
    # Check if SSM parameter exists (more reliable check)
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

# Synthesize CDK stack
echo_info "Synthesizing CDK stack..."
cdk synth

# Deploy
echo ""
echo_info "Deploying to AWS..."
echo_warn "This will take 5-10 minutes..."
echo ""

cdk deploy --require-approval never

# Cleanup Docker wrapper if created
if [ -n "$DOCKER_WRAPPER_CLEANUP" ]; then
    rm -rf "$DOCKER_WRAPPER_CLEANUP"
fi

echo ""
echo "=========================================="
echo_info "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo_info "Application URL: https://$DOMAIN_NAME"
echo ""
echo_info "Configuration saved to: $CONFIG_FILE"
echo_info "Next deployment will use saved configuration"
echo ""
echo_info "Next steps:"
echo "  1. Wait 2-3 minutes for ECS service to start"
echo "  2. Access https://$DOMAIN_NAME"
echo "  3. Log in with your OIDC provider"
echo ""
