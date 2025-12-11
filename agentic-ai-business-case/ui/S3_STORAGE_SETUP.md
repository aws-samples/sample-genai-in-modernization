# S3 File Storage Setup Guide

This guide explains how to set up optional S3 file storage for the AWS Migration Business Case Generator.

## Overview

By default, uploaded files are stored locally in the `input/` directory. With S3 integration:
- ✅ Files are automatically uploaded to S3 when generating business cases
- ✅ Files are automatically restored from S3 when loading saved cases
- ✅ Files persist even if local storage is cleared
- ✅ Files are versioned for history tracking
- ✅ Files are encrypted at rest
- ✅ Old file versions are automatically cleaned up

## When to Use S3 Storage

**Use S3 if:**
- You want to persist uploaded files long-term
- You're running the app on multiple machines
- You want automatic file backup
- You need file versioning
- You're deploying to production

**Skip S3 if:**
- You're just testing locally
- You don't need to save/load cases
- You're okay with re-uploading files each time

## Prerequisites

1. **AWS Account** with S3 access
2. **AWS Credentials** configured
3. **IAM Permissions** for S3 operations

## Setup Instructions

### Step 1: Configure AWS Credentials

Same as DynamoDB setup - use one of these methods:

```bash
# Option A: AWS CLI
aws configure

# Option B: Environment Variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### Step 2: Create S3 Bucket

Run the setup script:

```bash
cd agentic-ai-business-case/ui/backend
python setup_s3.py
```

This will:
- Create bucket named `aws-migration-business-cases-files` (default)
- Enable versioning
- Enable encryption at rest (AES256)
- Block all public access
- Set up lifecycle policy (delete old versions after 90 days)
- Add appropriate tags

**Custom bucket name:**
```bash
export S3_BUCKET_NAME=my-custom-bucket-name
python setup_s3.py
```

### Step 3: Configure Backend

Set the S3 bucket name environment variable:

```bash
export S3_BUCKET_NAME=aws-migration-business-cases-files
```

Or add to your shell profile (~/.bashrc, ~/.zshrc):
```bash
echo 'export S3_BUCKET_NAME=aws-migration-business-cases-files' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Restart Backend

```bash
cd agentic-ai-business-case/ui/backend
python app.py
```

You should see:
```
✓ S3 bucket 'aws-migration-business-cases-files' is accessible
```

### Step 5: Verify in UI

1. Start the UI
2. Look for the success alert: "Enhanced Storage: DynamoDB + S3 enabled"
3. Generate a business case
4. Save it - files are automatically uploaded to S3
5. Load it later - files are automatically restored

## Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::aws-migration-business-cases-files",
        "arn:aws:s3:::aws-migration-business-cases-files/*"
      ]
    }
  ]
}
```

For bucket creation, also add:
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:CreateBucket",
    "s3:PutBucketVersioning",
    "s3:PutBucketPublicAccessBlock",
    "s3:PutBucketEncryption",
    "s3:PutBucketLifecycleConfiguration",
    "s3:PutBucketTagging"
  ],
  "Resource": "arn:aws:s3:::aws-migration-business-cases-files"
}
```

## How It Works

### File Upload Flow

1. User uploads files in Step 2
2. Files saved locally to `input/` directory
3. Business case generated using local files
4. **If S3 enabled:** Files automatically uploaded to S3
5. S3 keys stored in DynamoDB with case metadata

### File Structure in S3

```
s3://aws-migration-business-cases-files/
├── case-20241124-143022/
│   ├── Test-Data-Set-Demo-Excel-V2.xlsx
│   ├── rvtool.csv
│   ├── analysis.xlsx
│   ├── report.pdf
│   ├── business_case.pptx
│   └── aws-customer-migration-readiness-assessment.md
├── case-20241124-150530/
│   ├── Test-Data-Set-Demo-Excel-V2.xlsx
│   └── ...
└── case-20241125-091245/
    └── ...
```

Each case has its own folder with all uploaded files.

### File Restore Flow

1. User clicks "Load Saved Cases"
2. Selects a case from the list
3. **If S3 enabled:** Files automatically downloaded from S3
4. Files restored to `input/` directory
5. Case can be regenerated with original files

## DynamoDB Integration

When S3 is enabled, DynamoDB records include:

```json
{
  "caseId": "case-20241124-143022",
  "projectInfo": {...},
  "businessCaseContent": "...",
  "s3Enabled": true,
  "s3FileKeys": {
    "itInventory": "case-20241124-143022/Test-Data-Set-Demo-Excel-V2.xlsx",
    "rvTool": "case-20241124-143022/rvtool.csv",
    "atxExcel": "case-20241124-143022/analysis.xlsx",
    "atxPdf": "case-20241124-143022/report.pdf",
    "atxPptx": "case-20241124-143022/business_case.pptx",
    "mra": "case-20241124-143022/aws-customer-migration-readiness-assessment.md"
  },
  "lastUpdated": "2024-11-24T14:30:22.000Z"
}
```

## Cost Considerations

### S3 Storage Costs

**Storage:**
- Standard: $0.023 per GB-month
- Typical file set: ~50 MB
- 100 cases: ~5 GB = $0.12/month

**Requests:**
- PUT: $0.005 per 1,000 requests
- GET: $0.0004 per 1,000 requests
- Typical: ~10 operations per case

**Data Transfer:**
- IN: Free
- OUT: First 100 GB/month free

**Typical Monthly Cost:**
- 100 cases with 50 MB each
- Storage: $0.12
- Requests: $0.01
- **Total: ~$0.13/month**

### Cost Optimization

1. **Lifecycle Policy** (already configured)
   - Old versions deleted after 90 days
   - Reduces storage costs

2. **Intelligent-Tiering** (optional)
   ```bash
   aws s3api put-bucket-intelligent-tiering-configuration \
     --bucket aws-migration-business-cases-files \
     --id AutoArchive \
     --intelligent-tiering-configuration ...
   ```

3. **Delete Old Cases**
   - Use the UI to delete cases you no longer need
   - Files automatically deleted from S3

## Security Features

### Encryption at Rest
- AES256 encryption enabled by default
- All files encrypted automatically
- No performance impact

### Public Access Blocked
- All public access blocked
- Files only accessible with AWS credentials
- Prevents accidental exposure

### Versioning
- File versions tracked automatically
- Can recover previous versions if needed
- Protects against accidental overwrites

### Access Control
- IAM-based access control
- Bucket policies can restrict access
- CloudTrail logging available

## Troubleshooting

### S3 Not Showing as Enabled

**Check environment variable:**
```bash
echo $S3_BUCKET_NAME
```

**Verify bucket exists:**
```bash
aws s3 ls s3://aws-migration-business-cases-files
```

**Check backend logs:**
Look for "S3 bucket 'xxx' is accessible" message

### Files Not Uploading

**Check IAM permissions:**
```bash
aws s3 cp test.txt s3://aws-migration-business-cases-files/test.txt
```

**Review backend logs:**
Look for "Error uploading to S3" messages

**Verify bucket region:**
Ensure bucket is in the same region as configured

### Files Not Restoring

**Check S3 keys in DynamoDB:**
```bash
aws dynamodb get-item \
  --table-name aws-migration-business-cases \
  --key '{"caseId": {"S": "case-20241124-143022"}}'
```

**Verify files exist in S3:**
```bash
aws s3 ls s3://aws-migration-business-cases-files/case-20241124-143022/
```

**Check download permissions:**
Ensure IAM has `s3:GetObject` permission

### Bucket Creation Fails

**Region-specific issues:**
- us-east-1 doesn't need LocationConstraint
- Other regions require it (script handles this)

**Bucket name conflicts:**
- S3 bucket names are globally unique
- Try a different name if taken

**Permission errors:**
- Ensure IAM has `s3:CreateBucket` permission

## Advanced Configuration

### Custom Bucket Name

```bash
export S3_BUCKET_NAME=my-company-migration-cases
python setup_s3.py
```

### Different Region

```bash
export AWS_REGION=eu-west-1
export S3_BUCKET_NAME=my-bucket-eu
python setup_s3.py
```

### Enable Point-in-Time Recovery

Already enabled through versioning. To adjust retention:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket aws-migration-business-cases-files \
  --lifecycle-configuration file://lifecycle.json
```

### Cross-Region Replication (Optional)

For disaster recovery:

```bash
aws s3api put-bucket-replication \
  --bucket aws-migration-business-cases-files \
  --replication-configuration file://replication.json
```

### Enable CloudTrail Logging

Track all S3 operations:

```bash
aws s3api put-bucket-logging \
  --bucket aws-migration-business-cases-files \
  --bucket-logging-status file://logging.json
```

## Monitoring

### Check Bucket Size

```bash
aws s3 ls s3://aws-migration-business-cases-files --recursive --summarize
```

### List All Cases

```bash
aws s3 ls s3://aws-migration-business-cases-files/ --recursive
```

### Check Versioning Status

```bash
aws s3api get-bucket-versioning \
  --bucket aws-migration-business-cases-files
```

### View Lifecycle Rules

```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket aws-migration-business-cases-files
```

## Disabling S3 Storage

To disable S3 (files will only be stored locally):

1. **Unset environment variable:**
   ```bash
   unset S3_BUCKET_NAME
   ```

2. **Restart backend:**
   ```bash
   python app.py
   ```

3. **Optional - Delete bucket:**
   ```bash
   python setup_s3.py delete
   ```

## Comparison: Local vs S3 Storage

| Feature | Local Only | With S3 |
|---------|-----------|---------|
| File Persistence | ❌ Lost if cleared | ✅ Permanent |
| Multi-Machine | ❌ No | ✅ Yes |
| Versioning | ❌ No | ✅ Yes |
| Backup | ❌ Manual | ✅ Automatic |
| Cost | Free | ~$0.13/month |
| Setup | None | 5 minutes |
| File Restore | ❌ Manual re-upload | ✅ Automatic |

## Best Practices

1. **Use S3 for Production**
   - Ensures files are never lost
   - Enables multi-user scenarios

2. **Regular Cleanup**
   - Delete old cases you don't need
   - Lifecycle policy handles old versions

3. **Monitor Costs**
   - Check S3 usage monthly
   - Set up billing alerts

4. **Backup Strategy**
   - S3 versioning provides backup
   - Consider cross-region replication for DR

5. **Security**
   - Keep public access blocked
   - Use IAM roles in production
   - Enable CloudTrail for audit

## Support

For issues:
1. Check troubleshooting section above
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Check bucket exists: `aws s3 ls s3://your-bucket-name`
4. Review backend logs for errors
5. Verify IAM permissions

## Related Documentation

- [DynamoDB Setup](./DYNAMODB_SETUP.md) - Database persistence
- [README](./README.md) - Main documentation
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)

---

**S3 storage is optional but recommended for production use!**
