# DynamoDB Persistence Setup Guide

This guide explains how to set up and use the optional DynamoDB persistence feature for the AWS Migration Business Case Generator.

## Overview

The DynamoDB persistence feature allows you to:
- Save generated business cases to AWS DynamoDB
- Load previously saved business cases
- Edit and regenerate saved cases
- Track when cases were last updated
- Manage multiple business cases in one place

## Prerequisites

1. **AWS Account**: You need an active AWS account
2. **AWS Credentials**: Configured AWS credentials with DynamoDB permissions
3. **Python Dependencies**: boto3 library installed

## Setup Instructions

### Step 1: Configure AWS Credentials

You can configure AWS credentials in several ways:

#### Option A: AWS CLI Configuration (Recommended)
```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Default output format (json)

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

#### Option C: IAM Role (for EC2/ECS deployments)
If running on AWS infrastructure, attach an IAM role with DynamoDB permissions.

### Step 2: Install Python Dependencies

```bash
cd agentic-ai-business-case/ui/backend
pip install -r requirements.txt
```

This will install boto3 and other required packages.

### Step 3: Create DynamoDB Table

Run the setup script to create the DynamoDB table:

```bash
python setup_dynamodb.py
```

The script will:
- Create a table named `aws-migration-business-cases` (default)
- Use on-demand billing mode (pay per request)
- Set up the required schema
- Add appropriate tags

**Custom Configuration:**
```bash
# Use custom table name and region
export DYNAMODB_TABLE_NAME=my-custom-table-name
export AWS_REGION=us-west-2
python setup_dynamodb.py
```

### Step 4: Verify Setup

Check that the table was created successfully:

```bash
aws dynamodb describe-table --table-name aws-migration-business-cases
```

## Required IAM Permissions

The AWS credentials need the following DynamoDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/aws-migration-business-cases"
    }
  ]
}
```

For table creation, you also need:
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:CreateTable",
    "dynamodb:DescribeTable"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/aws-migration-business-cases"
}
```

## Using the Feature

### 1. Enable DynamoDB Persistence

In the UI:
1. Start the application
2. Look for the "DynamoDB Persistence" toggle in the header
3. Toggle it ON (it will show a green "success" indicator)

### 2. Save a Business Case

After generating a business case:
1. Go to the Results step
2. Click "Save to Database" button
3. The case will be saved with a unique Case ID
4. You'll see "Last saved" timestamp in the UI

### 3. Load a Saved Case

1. Click "Load Saved Cases" in the top navigation
2. Browse the list of saved cases
3. Select a case and click "Load Selected"
4. The case will be loaded into the UI

### 4. Update an Existing Case

1. Load a saved case
2. Make changes to project info or regenerate
3. Click "Update in Database" to save changes
4. The "Last Updated" timestamp will be updated

### 5. Delete a Case

1. Click "Load Saved Cases"
2. Select the case to delete
3. Click "Delete" button
4. Confirm the deletion

## Data Structure

Each saved business case contains:

```json
{
  "caseId": "case-20241124-143022",
  "projectInfo": {
    "projectName": "Enterprise Migration 2024",
    "customerName": "Acme Corp",
    "awsRegion": "us-east-1",
    "projectDescription": "..."
  },
  "uploadedFiles": ["itInventory", "rvTool", "atx"],
  "selectedAgents": {
    "runAll": true,
    "agents": {...}
  },
  "businessCaseContent": "# AWS Migration Business Case...",
  "createdAt": "2024-11-24T14:30:22.000Z",
  "lastUpdated": "2024-11-24T15:45:10.000Z",
  "executionStats": {
    "agentsExecuted": 9,
    "executionTime": "45.2s",
    "tokenUsage": "12,450"
  }
}
```

## Cost Considerations

DynamoDB costs depend on:
- **Storage**: $0.25 per GB-month
- **Read/Write Requests**: $1.25 per million write requests, $0.25 per million read requests

For typical usage (100 business cases, occasional access):
- Storage: ~10 MB = $0.0025/month
- Requests: ~1000 operations/month = $0.002/month
- **Total: Less than $0.01/month**

## Troubleshooting

### DynamoDB Toggle Not Appearing

**Cause**: Backend cannot connect to DynamoDB

**Solutions**:
1. Check AWS credentials are configured
2. Verify table exists: `aws dynamodb describe-table --table-name aws-migration-business-cases`
3. Check backend logs for errors
4. Ensure boto3 is installed: `pip install boto3`

### "DynamoDB is not enabled" Error

**Cause**: Table doesn't exist or credentials are invalid

**Solutions**:
1. Run setup script: `python setup_dynamodb.py`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Check IAM permissions

### Save Operation Fails

**Cause**: Insufficient permissions or network issues

**Solutions**:
1. Verify IAM permissions (see Required IAM Permissions section)
2. Check network connectivity to AWS
3. Review backend logs for detailed error messages

### Cannot Load Saved Cases

**Cause**: Table is empty or scan permissions missing

**Solutions**:
1. Verify cases exist: `aws dynamodb scan --table-name aws-migration-business-cases`
2. Check IAM permissions include `dynamodb:Scan`
3. Ensure table name matches configuration

## Disabling the Feature

To disable DynamoDB persistence:

1. **In UI**: Toggle OFF the "DynamoDB Persistence" switch
2. **Remove Table** (optional): `python setup_dynamodb.py delete`
3. **Remove Dependencies** (optional): Remove boto3 from requirements.txt

## Security Best Practices

1. **Use IAM Roles**: When running on AWS, use IAM roles instead of access keys
2. **Least Privilege**: Grant only required DynamoDB permissions
3. **Encryption**: Enable encryption at rest for the DynamoDB table
4. **VPC Endpoints**: Use VPC endpoints for private connectivity
5. **Audit Logging**: Enable CloudTrail logging for DynamoDB operations

## Advanced Configuration

### Custom Table Name

```bash
export DYNAMODB_TABLE_NAME=my-business-cases
python setup_dynamodb.py
```

Update backend to use custom name:
```bash
export DYNAMODB_TABLE_NAME=my-business-cases
python app.py
```

### Different AWS Region

```bash
export AWS_REGION=eu-west-1
python setup_dynamodb.py
```

### Enable Point-in-Time Recovery

```bash
aws dynamodb update-continuous-backups \
  --table-name aws-migration-business-cases \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Enable Encryption at Rest

```bash
aws dynamodb update-table \
  --table-name aws-migration-business-cases \
  --sse-specification Enabled=true,SSEType=KMS
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: Check Flask console output
3. Verify AWS service health: https://status.aws.amazon.com/
4. Check DynamoDB documentation: https://docs.aws.amazon.com/dynamodb/
