#!/usr/bin/env python3
"""
Setup script to create S3 bucket for AWS Migration Business Case Generator file storage
"""

import boto3
import sys
import os
from botocore.exceptions import ClientError

# Configuration
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'aws-migration-business-cases-files')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

def create_bucket():
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        
        # Check if bucket already exists
        try:
            s3_client.head_bucket(Bucket=BUCKET_NAME)
            print(f"✓ Bucket '{BUCKET_NAME}' already exists in region '{AWS_REGION}'")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code != '404':
                raise
        
        # Create bucket
        print(f"Creating S3 bucket '{BUCKET_NAME}' in region '{AWS_REGION}'...")
        
        if AWS_REGION == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3_client.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        
        # Enable versioning (optional but recommended)
        print("Enabling versioning...")
        s3_client.put_bucket_versioning(
            Bucket=BUCKET_NAME,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Block public access (security best practice)
        print("Configuring security settings...")
        s3_client.put_public_access_block(
            Bucket=BUCKET_NAME,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        
        # Enable encryption at rest
        print("Enabling encryption...")
        s3_client.put_bucket_encryption(
            Bucket=BUCKET_NAME,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        )
        
        # Add lifecycle policy to manage old files (optional)
        print("Setting up lifecycle policy...")
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=BUCKET_NAME,
            LifecycleConfiguration={
                'Rules': [
                    {
                        'ID': 'DeleteOldVersions',
                        'Status': 'Enabled',
                        'NoncurrentVersionExpiration': {
                            'NoncurrentDays': 90
                        }
                    }
                ]
            }
        )
        
        # Add tags
        s3_client.put_bucket_tagging(
            Bucket=BUCKET_NAME,
            Tagging={
                'TagSet': [
                    {'Key': 'Application', 'Value': 'AWS-Migration-Business-Case-Generator'},
                    {'Key': 'ManagedBy', 'Value': 'Setup-Script'},
                    {'Key': 'Purpose', 'Value': 'File-Storage'}
                ]
            }
        )
        
        print(f"✓ Bucket '{BUCKET_NAME}' created successfully!")
        print(f"\nBucket Details:")
        print(f"  - Bucket Name: {BUCKET_NAME}")
        print(f"  - Region: {AWS_REGION}")
        print(f"  - Versioning: Enabled")
        print(f"  - Encryption: AES256")
        print(f"  - Public Access: Blocked")
        print(f"  - Lifecycle: Delete old versions after 90 days")
        
        return True
        
    except ClientError as e:
        print(f"✗ Error creating bucket: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def delete_bucket():
    """Delete S3 bucket (use with caution!)"""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        
        print(f"Deleting all objects in bucket '{BUCKET_NAME}'...")
        
        # Delete all objects and versions
        paginator = s3_client.get_paginator('list_object_versions')
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            objects_to_delete = []
            
            # Delete object versions
            if 'Versions' in page:
                for version in page['Versions']:
                    objects_to_delete.append({
                        'Key': version['Key'],
                        'VersionId': version['VersionId']
                    })
            
            # Delete delete markers
            if 'DeleteMarkers' in page:
                for marker in page['DeleteMarkers']:
                    objects_to_delete.append({
                        'Key': marker['Key'],
                        'VersionId': marker['VersionId']
                    })
            
            if objects_to_delete:
                s3_client.delete_objects(
                    Bucket=BUCKET_NAME,
                    Delete={'Objects': objects_to_delete}
                )
        
        print(f"Deleting bucket '{BUCKET_NAME}'...")
        s3_client.delete_bucket(Bucket=BUCKET_NAME)
        
        print(f"✓ Bucket '{BUCKET_NAME}' deleted successfully!")
        return True
        
    except ClientError as e:
        print(f"✗ Error deleting bucket: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("AWS Migration Business Case Generator - S3 Setup")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        confirm = input(f"Are you sure you want to DELETE bucket '{BUCKET_NAME}' and ALL its contents? (yes/no): ")
        if confirm.lower() == 'yes':
            success = delete_bucket()
        else:
            print("Delete operation cancelled.")
            success = False
    else:
        success = create_bucket()
    
    print()
    if success:
        print("Setup completed successfully!")
        print()
        print("To use S3 file storage:")
        print("1. Ensure AWS credentials are configured")
        print("2. Set environment variable:")
        print(f"   export S3_BUCKET_NAME={BUCKET_NAME}")
        print(f"   export AWS_REGION={AWS_REGION}")
        print("3. Restart the backend server: python app.py")
        print("4. Files will automatically be uploaded to S3 when saving cases")
        print()
        print("Benefits:")
        print("  • Uploaded files are persisted in S3")
        print("  • Files automatically restored when loading saved cases")
        print("  • Versioning enabled for file history")
        print("  • Encrypted at rest for security")
        print("  • Old versions cleaned up after 90 days")
        sys.exit(0)
    else:
        print("Setup failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
