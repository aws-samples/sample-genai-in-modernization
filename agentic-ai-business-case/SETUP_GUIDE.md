# One-Click Setup Guide

## Overview

The `setup.sh` script automates the entire installation process for the AWS Migration Business Case Generator.

## What It Does

### 1. Prerequisites Check
- ✅ Verifies Python 3.8+ is installed
- ✅ Verifies Node.js 16+ is installed
- ✅ Verifies npm is installed
- ✅ Checks for AWS CLI (warns if missing)

### 2. AWS Credentials Verification
- ✅ Validates AWS credentials are configured
- ✅ Shows AWS account and user information
- ✅ Exits with helpful message if credentials are missing

### 3. Virtual Environment Setup
- ✅ Creates main virtual environment (`venv/`)
- ✅ Creates UI backend virtual environment (`ui/backend/venv/`)
- ✅ Activates environments automatically

### 4. Dependency Installation
- ✅ Installs agent dependencies from `agents/requirements.txt`
- ✅ Installs UI backend dependencies from `ui/backend/requirements.txt`
- ✅ Installs UI frontend dependencies via `npm install`
- ✅ Upgrades pip to latest version

### 5. AWS Services Setup
- ✅ Creates DynamoDB table for business case persistence
- ✅ Configures S3 bucket for file storage (if S3_BUCKET_NAME is set)
- ✅ Handles cases where resources already exist

### 6. Directory Structure
- ✅ Creates `input/` directory for assessment files
- ✅ Creates `output/logs/` directory for execution logs

### 7. Convenience Scripts
- ✅ Creates `start-all.sh` - Starts both backend and frontend
- ✅ Creates `stop-all.sh` - Stops all services

## Usage

### First Time Setup

```bash
# 1. Navigate to project directory
cd agentic-ai-business-case

# 2. Configure AWS credentials (choose one method)
aws configure
# OR
aws sso login --profile <your-profile>
# OR
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# 3. (Optional) Set S3 bucket for file storage
export S3_BUCKET_NAME=your-bucket-name

# 4. Run setup script
./setup.sh
```

### Starting the Application

After setup completes:

```bash
# Start everything (uses Gunicorn by default)
./start-all.sh

# Access at: http://localhost:3000
```

The backend automatically runs with **Gunicorn**, a production-grade WSGI server that provides:
- ✅ Multi-process workers for better performance
- ✅ Graceful restarts with zero downtime
- ✅ Production-ready security and reliability
- ✅ Better resource management

### Stopping the Application

```bash
# Stop everything
./stop-all.sh
```

### Advanced Deployment Options

For systemd service or Nginx reverse proxy setup, see `ui/backend/README-GUNICORN.md`.

## What Gets Created

```
agentic-ai-business-case/
├── venv/                    # Main Python virtual environment
├── input/                   # Directory for input files
├── output/                  # Directory for generated business cases
│   └── logs/               # Execution logs
├── ui/
│   ├── backend/
│   │   └── venv/           # UI backend virtual environment
│   └── node_modules/       # UI frontend dependencies
├── setup.sh                # This setup script
├── start-all.sh            # Start script (created by setup)
└── stop-all.sh             # Stop script (created by setup)
```

## AWS Resources Created

### DynamoDB Table
- **Table Name**: `BusinessCases`
- **Primary Key**: `caseId` (String)
- **Purpose**: Stores business case metadata and content
- **Billing**: On-demand (pay per request)

### S3 Bucket (Optional)
- **Bucket Name**: Value of `S3_BUCKET_NAME` environment variable
- **Purpose**: Stores uploaded assessment files
- **Structure**: `s3://bucket-name/{caseId}/filename`

## Troubleshooting

### "Python 3 is not installed"
- Install Python 3.8 or higher from https://www.python.org/downloads/
- On macOS: `brew install python3`
- On Ubuntu: `sudo apt-get install python3`

### "Node.js is not installed"
- Install Node.js 16+ from https://nodejs.org/
- On macOS: `brew install node`
- On Ubuntu: `curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash - && sudo apt-get install -y nodejs`

### "AWS credentials are not configured"
- Run: `aws configure`
- Or: `aws sso login --profile <profile>`
- Or set environment variables:
  ```bash
  export AWS_ACCESS_KEY_ID=your_key
  export AWS_SECRET_ACCESS_KEY=your_secret
  export AWS_DEFAULT_REGION=us-east-1
  ```

### "'BedrockRuntime' object has no attribute 'converse_stream'"
- This means boto3/botocore is too old
- The `converse_stream` API requires boto3 >= 1.34.90
- Solution:
  ```bash
  source venv/bin/activate
  python3 -m pip install --upgrade boto3 botocore
  # Verify version
  python3 -c "import boto3; print(boto3.__version__)"
  ```
- Should show version 1.34.90 or higher

### "DynamoDB table already exists"
- This is normal if you've run setup before
- The script will continue without error
- To recreate: Delete table in AWS Console first

### "Permission denied: ./setup.sh"
- Make script executable: `chmod +x setup.sh`
- Then run: `./setup.sh`

### Script fails partway through
- Check error message for specific issue
- Fix the issue (e.g., install missing dependency)
- Re-run `./setup.sh` - it will skip completed steps

## Manual Cleanup

If you need to start fresh:

```bash
# Remove virtual environments
rm -rf venv/
rm -rf ui/backend/venv/
rm -rf ui/node_modules/

# Remove generated scripts
rm -f start-all.sh stop-all.sh

# Remove AWS resources (optional)
aws dynamodb delete-table --table-name BusinessCases
aws s3 rb s3://$S3_BUCKET_NAME --force

# Then re-run setup
./setup.sh
```

## Environment Variables

### Required
- `AWS_ACCESS_KEY_ID` - AWS access key (or use aws configure)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (or use aws configure)
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)

### Optional
- `S3_BUCKET_NAME` - S3 bucket for file storage (enables S3 features)

## Input Files

### Required Files

1. **Migration Readiness Assessment** (Markdown, Word, or PDF)
   - Organizational readiness evaluation
   - Skills assessment
   - Change management readiness
   - **Required for all business cases**
   - **Formats supported**: .md, .docx, .doc, .pdf

2. **At least ONE infrastructure file**:
   - RVTools Export, OR
   - IT Infrastructure Inventory, OR
   - ATX Assessment files

### Infrastructure Files (Choose One or More)

1. **RVTools Export** (Excel or CSV)
   - vInfo sheet with VM inventory (prioritized for large datasets)
   - Columns: VM name, CPUs, Memory, Storage, OS, Powerstate
   - Recommended: 2,000-2,500 VMs max for optimal performance
   - **Tip**: For large exports, upload vInfo file only to prevent timeouts

2. **IT Infrastructure Inventory** (Excel)
   - Server inventory
   - Application portfolio
   - Database inventory

3. **ATX Assessment** (Excel, PDF, PowerPoint)
   - VMware environment analysis from AWS Transform for VMware
   - Cost projections
   - Technical recommendations
   - Can upload all three formats for comprehensive analysis

### Optional Files

4. **Application Portfolio** (CSV or Excel)
   - Detailed application characteristics
   - Dependencies and business criticality
   - If not provided, industry-standard assumptions are used
   - Used by Migration Strategy agent for more accurate 7Rs recommendations

## Configuration

### Model Settings (agents/config.py)

```python
# Model selection
model_id_claude3_7 = "anthropic.claude-3-sonnet-20240229-v1:0"
max_tokens_default = 8192

# Temperature (lower = more deterministic)
model_temperature = 0.3  # General agents
# Cost agent uses 0.1 for consistency

# Data limits
MAX_ROWS_RVTOOLS = 2500  # Max VMs to analyze
MAX_ROWS_IT_INVENTORY = 1500
MAX_ROWS_PORTFOLIO = 1000

# Multi-stage generation (recommended)
ENABLE_MULTI_STAGE = True
```

### AWS Credentials

Choose one method:

**Method 1: AWS Configure**
```bash
aws configure
```

**Method 2: AWS SSO**
```bash
aws sso login --profile <your-profile>
```

**Method 3: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### S3 Storage (Optional)

```bash
export S3_BUCKET_NAME=your-bucket-name
cd ui/backend
source venv/bin/activate
python3 setup_s3.py
```

## Next Steps After Setup

1. **Start the application**: `./start-all.sh`
2. **Access UI**: Open http://localhost:3000
3. **Upload files**: Use the UI to upload assessment files
4. **Generate business case**: Follow the 4-step wizard
5. **Edit and export**: Customize the generated business case

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review setup script output for error messages
3. Verify AWS credentials: `aws sts get-caller-identity`
4. Check Python version: `python3 --version`
5. Check Node version: `node --version`

## Benefits of One-Click Setup

- ✅ **Saves Time**: 10+ manual commands → 1 script
- ✅ **Prevents Errors**: Automated checks and validation
- ✅ **Consistent**: Same setup for all users
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Informative**: Clear progress and error messages
- ✅ **Complete**: Sets up everything including AWS resources
