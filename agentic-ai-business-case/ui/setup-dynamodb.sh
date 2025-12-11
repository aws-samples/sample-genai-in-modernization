#!/bin/bash

# AWS Migration Business Case Generator - DynamoDB Setup Script
# This script helps set up DynamoDB persistence feature

set -e

echo "=========================================="
echo "DynamoDB Persistence Setup"
echo "=========================================="
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

# Ask for confirmation
read -p "Do you want to create DynamoDB table in region $CURRENT_REGION? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

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

# Run setup script
echo "Creating DynamoDB table..."
python3 setup_dynamodb.py || python setup_dynamodb.py

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the backend: cd backend && python app.py"
echo "2. Start the frontend: npm start"
echo "3. Toggle 'DynamoDB Persistence' in the UI"
echo ""
