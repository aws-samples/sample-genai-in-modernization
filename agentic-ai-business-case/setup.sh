#!/bin/bash

# AWS Migration Business Case Generator - One-Click Setup Script
# This script sets up the entire environment including virtual environments,
# dependencies, DynamoDB, and S3 storage.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running from correct directory
if [ ! -f "setup.sh" ]; then
    print_error "Please run this script from the agentic-ai-business-case directory"
    exit 1
fi

print_header "AWS Migration Business Case Generator - Setup"

# Step 1: Check prerequisites
print_header "Step 1: Checking Prerequisites"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm is not installed. Please install npm."
    exit 1
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    print_success "AWS CLI found: $AWS_VERSION"
else
    print_warning "AWS CLI is not installed. You'll need it for AWS operations."
    print_info "Install from: https://aws.amazon.com/cli/"
fi

# Step 2: Check AWS credentials
print_header "Step 2: Checking AWS Credentials"

if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    print_success "AWS credentials are configured"
    print_info "Account: $AWS_ACCOUNT"
    print_info "User: $AWS_USER"
else
    print_error "AWS credentials are not configured or expired"
    print_info "Please configure AWS credentials before continuing:"
    print_info "  - Run: aws configure"
    print_info "  - Or: aws sso login --profile <your-profile>"
    print_info "  - Or: export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

# Step 3: Create virtual environment for agents
print_header "Step 3: Setting Up Python Virtual Environment"

if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation."
else
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Step 4: Install Python dependencies for agents
print_header "Step 4: Installing Python Dependencies for Agents"

print_info "Installing dependencies from agents/requirements.txt..."
python3 -m pip install --upgrade pip
python3 -m pip install -r agents/requirements.txt
print_success "Agent dependencies installed"

# Step 5: Set up UI backend
print_header "Step 5: Setting Up UI Backend"

cd ui/backend

if [ -d "venv" ]; then
    print_warning "UI backend virtual environment already exists. Skipping creation."
else
    print_info "Creating UI backend virtual environment..."
    python3 -m venv venv
    print_success "UI backend virtual environment created"
fi

print_info "Installing UI backend dependencies..."
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
print_success "UI backend dependencies installed"

cd ../..

# Step 6: Install UI frontend dependencies
print_header "Step 6: Installing UI Frontend Dependencies"

cd ui
print_info "Installing npm packages..."
npm install
print_success "UI frontend dependencies installed"
cd ..

# Step 7: Set up DynamoDB
print_header "Step 7: Setting Up DynamoDB"

print_info "Creating DynamoDB table for business case persistence..."
cd ui/backend
source venv/bin/activate

if python3 setup_dynamodb.py; then
    print_success "DynamoDB table created successfully"
else
    print_warning "DynamoDB setup encountered an issue (table may already exist)"
fi

cd ../..

# Step 8: Set up S3 (optional)
print_header "Step 8: Setting Up S3 Storage"

# Check if S3_BUCKET_NAME is set
if [ -z "$S3_BUCKET_NAME" ]; then
    print_warning "S3_BUCKET_NAME environment variable not set"
    print_info "S3 storage will be disabled. To enable:"
    print_info "  1. Set S3_BUCKET_NAME: export S3_BUCKET_NAME=your-bucket-name"
    print_info "  2. Run: cd ui/backend && python3 setup_s3.py"
else
    print_info "Setting up S3 bucket: $S3_BUCKET_NAME"
    cd ui/backend
    source venv/bin/activate
    
    if python3 setup_s3.py; then
        print_success "S3 bucket configured successfully"
    else
        print_warning "S3 setup encountered an issue"
    fi
    
    cd ../..
fi

# Step 9: Create input directory if it doesn't exist
print_header "Step 9: Setting Up Directories"

if [ ! -d "input" ]; then
    mkdir -p input
    print_success "Created input directory"
else
    print_info "Input directory already exists"
fi

if [ ! -d "output" ]; then
    mkdir -p output/logs
    print_success "Created output directory"
else
    print_info "Output directory already exists"
fi

# Step 10: Create convenience start script
print_header "Step 10: Creating Start Script"

cat > start-all.sh << 'EOF'
#!/bin/bash

# Start both backend and frontend

echo "Starting AWS Migration Business Case Generator..."

# Start backend in background
echo "Starting backend server..."
cd ui/backend
source venv/bin/activate
python3 app.py &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend server..."
cd ui
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "Services started successfully!"
echo "=========================================="
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Access the application at: http://localhost:3000"
echo ""
echo "To stop the services, run: ./stop-all.sh"
echo "Or press Ctrl+C and run: kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Wait for both processes
wait
EOF

chmod +x start-all.sh
print_success "Created start-all.sh script"

# Create stop script
cat > stop-all.sh << 'EOF'
#!/bin/bash

echo "Stopping AWS Migration Business Case Generator..."

# Kill backend
pkill -f "python3 app.py"
echo "✓ Backend stopped"

# Kill frontend
pkill -f "npm start"
pkill -f "react-scripts start"
echo "✓ Frontend stopped"

echo "All services stopped."
EOF

chmod +x stop-all.sh
print_success "Created stop-all.sh script"

# Final summary
print_header "Setup Complete!"

echo -e "${GREEN}✓ Virtual environments created${NC}"
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo -e "${GREEN}✓ UI dependencies installed${NC}"
echo -e "${GREEN}✓ DynamoDB configured${NC}"
if [ -n "$S3_BUCKET_NAME" ]; then
    echo -e "${GREEN}✓ S3 storage configured${NC}"
else
    echo -e "${YELLOW}⚠ S3 storage not configured (optional)${NC}"
fi
echo -e "${GREEN}✓ Directories created${NC}"
echo -e "${GREEN}✓ Start/stop scripts created${NC}"

print_header "Next Steps"

echo -e "${BLUE}To start the application:${NC}"
echo -e "  ${GREEN}./start-all.sh${NC}"
echo ""
echo -e "${BLUE}Or start manually:${NC}"
echo -e "  ${GREEN}cd ui && ./start.sh${NC}"
echo ""
echo -e "${BLUE}To run command-line generator:${NC}"
echo -e "  ${GREEN}source venv/bin/activate${NC}"
echo -e "  ${GREEN}python agents/aws_business_case.py${NC}"
echo ""
echo -e "${BLUE}To stop the application:${NC}"
echo -e "  ${GREEN}./stop-all.sh${NC}"
echo ""
echo -e "${BLUE}Access the UI at:${NC}"
echo -e "  ${GREEN}http://localhost:3000${NC}"
echo ""

if [ -z "$S3_BUCKET_NAME" ]; then
    print_info "To enable S3 storage later:"
    echo "  export S3_BUCKET_NAME=your-bucket-name"
    echo "  cd ui/backend && source venv/bin/activate && python3 setup_s3.py"
    echo ""
fi

print_success "Setup completed successfully!"
