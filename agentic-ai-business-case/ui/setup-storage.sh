#!/bin/bash

# AWS Migration Business Case Generator - Complete Storage Setup Script
# Sets up both DynamoDB and S3 (optional)

set -e

echo "=========================================="
echo "Complete Storage Setup"
echo "=========================================="
echo ""
echo "This script will help you set up:"
echo "  1. DynamoDB - For business case metadata"
echo "  2. S3 (optional) - For file storage"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed."
    echo "Please install AWS CLI first: https://aws.amazon.com/cli/"
    exit 1
fi

echo "✓ AWS CLI is installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured."
    echo ""
    echo "Please configure AWS credentials using one of these methods:"
    echo "  1. Run: aws configure"
    echo "  2. Set environment variables:"
    echo "     export AWS_ACCESS_KEY_ID=your_key"
    echo "     export AWS_SECRET_ACCESS_KEY=your_secret"
    echo "     export AWS_REGION=us-east-1"
    exit 1
fi

echo "✓ AWS credentials are configured"
echo ""

# Get AWS account info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CURRENT_REGION=$(aws configure get region || echo "us-east-1")

echo "AWS Account: $ACCOUNT_ID"
echo "Current Region: $CURRENT_REGION"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    exit 1
fi

echo "✓ Python 3 is installed"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt > /dev/null 2>&1 || pip install -r requirements.txt > /dev/null 2>&1

echo "✓ Dependencies installed"
echo ""

# Setup DynamoDB
echo "=========================================="
echo "Step 1: DynamoDB Setup"
echo "=========================================="
echo ""
read -p "Do you want to set up DynamoDB for business case storage? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Creating DynamoDB table..."
    python3 setup_dynamodb.py || python setup_dynamodb.py
    DYNAMODB_SETUP=true
else
    echo "Skipping DynamoDB setup."
    DYNAMODB_SETUP=false
fi

# Setup S3
echo ""
echo "=========================================="
echo "Step 2: S3 File Storage Setup (Optional)"
echo "=========================================="
echo ""
echo "S3 storage allows you to:"
echo "  • Persist uploaded files permanently"
echo "  • Automatically restore files when loading cases"
echo "  • Enable file versioning and backup"
echo ""
read -p "Do you want to set up S3 for file storage? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    
    # Ask for bucket name
    read -p "Enter S3 bucket name (or press Enter for default): " BUCKET_NAME
    if [ -z "$BUCKET_NAME" ]; then
        BUCKET_NAME="aws-migration-business-cases-files-${ACCOUNT_ID}"
        echo "Using bucket name: $BUCKET_NAME"
    fi
    
    export S3_BUCKET_NAME=$BUCKET_NAME
    
    echo ""
    echo "Creating S3 bucket..."
    python3 setup_s3.py || python setup_s3.py
    S3_SETUP=true
else
    echo "Skipping S3 setup."
    S3_SETUP=false
fi

# Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""

if [ "$DYNAMODB_SETUP" = true ]; then
    echo "✓ DynamoDB table created"
    echo "  Table: aws-migration-business-cases"
    echo "  Region: $CURRENT_REGION"
fi

if [ "$S3_SETUP" = true ]; then
    echo "✓ S3 bucket created"
    echo "  Bucket: $BUCKET_NAME"
    echo "  Region: $CURRENT_REGION"
fi

echo ""
echo "Next steps:"
echo ""

if [ "$DYNAMODB_SETUP" = true ] || [ "$S3_SETUP" = true ]; then
    echo "1. Set environment variables (add to ~/.bashrc or ~/.zshrc):"
    
    if [ "$DYNAMODB_SETUP" = true ]; then
        echo "   export DYNAMODB_TABLE_NAME=aws-migration-business-cases"
    fi
    
    if [ "$S3_SETUP" = true ]; then
        echo "   export S3_BUCKET_NAME=$BUCKET_NAME"
    fi
    
    echo "   export AWS_REGION=$CURRENT_REGION"
    echo ""
    echo "2. Start the backend:"
    echo "   cd backend && python app.py"
    echo ""
    echo "3. Start the frontend (in another terminal):"
    echo "   cd .. && npm start"
    echo ""
    
    if [ "$DYNAMODB_SETUP" = true ]; then
        echo "4. Toggle 'DynamoDB Persistence' in the UI"
    fi
    
    if [ "$S3_SETUP" = true ]; then
        echo "5. Files will automatically be backed up to S3"
    fi
else
    echo "No storage configured. The app will work with local files only."
    echo ""
    echo "To start the app:"
    echo "1. cd backend && python app.py"
    echo "2. cd .. && npm start (in another terminal)"
fi

echo ""
echo "For more information:"
if [ "$DYNAMODB_SETUP" = true ]; then
    echo "  • DynamoDB: See DYNAMODB_SETUP.md"
fi
if [ "$S3_SETUP" = true ]; then
    echo "  • S3: See S3_STORAGE_SETUP.md"
fi
echo "  • General: See README.md"
echo ""
