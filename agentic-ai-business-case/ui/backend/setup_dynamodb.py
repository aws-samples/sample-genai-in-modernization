#!/usr/bin/env python3
"""
Setup script to create DynamoDB table for AWS Migration Business Case Generator
"""

import boto3
import sys
import os
from botocore.exceptions import ClientError

# Configuration
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-migration-business-cases')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

def create_table():
    """Create DynamoDB table if it doesn't exist"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        
        # Check if table already exists
        try:
            table = dynamodb.Table(TABLE_NAME)
            table.load()
            print(f"✓ Table '{TABLE_NAME}' already exists in region '{AWS_REGION}'")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table
        print(f"Creating table '{TABLE_NAME}' in region '{AWS_REGION}'...")
        
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'caseId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'caseId',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand billing
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'AWS-Migration-Business-Case-Generator'
                },
                {
                    'Key': 'ManagedBy',
                    'Value': 'Setup-Script'
                }
            ]
        )
        
        # Wait for table to be created
        print("Waiting for table to be created...")
        table.wait_until_exists()
        
        print(f"✓ Table '{TABLE_NAME}' created successfully!")
        print(f"\nTable Details:")
        print(f"  - Table Name: {TABLE_NAME}")
        print(f"  - Region: {AWS_REGION}")
        print(f"  - Billing Mode: PAY_PER_REQUEST")
        print(f"  - Status: {table.table_status}")
        
        return True
        
    except ClientError as e:
        print(f"✗ Error creating table: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def delete_table():
    """Delete DynamoDB table (use with caution!)"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        table = dynamodb.Table(TABLE_NAME)
        
        print(f"Deleting table '{TABLE_NAME}'...")
        table.delete()
        
        print("Waiting for table to be deleted...")
        table.wait_until_not_exists()
        
        print(f"✓ Table '{TABLE_NAME}' deleted successfully!")
        return True
        
    except ClientError as e:
        print(f"✗ Error deleting table: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("AWS Migration Business Case Generator - DynamoDB Setup")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        confirm = input(f"Are you sure you want to DELETE table '{TABLE_NAME}'? (yes/no): ")
        if confirm.lower() == 'yes':
            success = delete_table()
        else:
            print("Delete operation cancelled.")
            success = False
    else:
        success = create_table()
    
    print()
    if success:
        print("Setup completed successfully!")
        print()
        print("To use DynamoDB persistence:")
        print("1. Ensure AWS credentials are configured (AWS CLI or environment variables)")
        print("2. Set environment variables (optional):")
        print(f"   export DYNAMODB_TABLE_NAME={TABLE_NAME}")
        print(f"   export AWS_REGION={AWS_REGION}")
        print("3. Start the backend server: python app.py")
        print("4. Enable DynamoDB toggle in the UI")
        sys.exit(0)
    else:
        print("Setup failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
