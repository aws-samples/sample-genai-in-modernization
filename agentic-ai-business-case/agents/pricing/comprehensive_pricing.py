"""
Comprehensive AWS Pricing for All Major Services
Uses AWS Price List API where available, with documented assumptions for estimated services
"""

import boto3
import json
import logging
from functools import lru_cache
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Region mapping for Price List API
REGION_NAMES = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
}

# ============================================================================
# AWS PRICING API SERVICES (Real-time pricing)
# ============================================================================

@lru_cache(maxsize=100)
def get_ec2_pricing(instance_type: str, os: str, region: str) -> Optional[float]:
    """Get EC2 instance pricing from AWS Price List API"""
    try:
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        location = REGION_NAMES.get(region, region)
        
        os_map = {"Linux": "Linux", "Windows": "Windows", "linux": "Linux", "windows": "Windows"}
        operating_system = os_map.get(os, "Linux")
        
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_item = json.loads(response['PriceList'][0])
            on_demand = price_item['terms']['OnDemand']
            price_dimensions = list(on_demand.values())[0]['priceDimensions']
            price_per_hour = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            return price_per_hour
    except Exception as e:
        logger.warning(f"Failed to get EC2 pricing for {instance_type}: {e}")
    return None


@lru_cache(maxsize=100)
def get_rds_pricing(instance_type: str, engine: str, deployment: str, region: str) -> Optional[float]:
    """Get RDS instance pricing from AWS Price List API"""
    try:
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        location = REGION_NAMES.get(region, region)
        
        engine_map = {
            "MySQL": "MySQL", "PostgreSQL": "PostgreSQL", "Oracle": "Oracle",
            "SQL Server": "SQL Server", "MariaDB": "MariaDB",
            "Aurora MySQL": "Aurora MySQL", "Aurora PostgreSQL": "Aurora PostgreSQL",
        }
        database_engine = engine_map.get(engine, "MySQL")
        deployment_option = "Multi-AZ" if "Multi-AZ" in deployment or "multi" in deployment.lower() else "Single-AZ"
        
        response = pricing_client.get_products(
            ServiceCode='AmazonRDS',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': database_engine},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': deployment_option},
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_item = json.loads(response['PriceList'][0])
            on_demand = price_item['terms']['OnDemand']
            price_dimensions = list(on_demand.values())[0]['priceDimensions']
            price_per_hour = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            return price_per_hour
    except Exception as e:
        logger.warning(f"Failed to get RDS pricing for {instance_type}: {e}")
    return None


@lru_cache(maxsize=50)
def get_s3_pricing(storage_class: str, region: str) -> Optional[float]:
    """Get S3 storage pricing from AWS Price List API"""
    try:
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        location = REGION_NAMES.get(region, region)
        
        response = pricing_client.get_products(
            ServiceCode='AmazonS3',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
            ],
            MaxResults=10
        )
        
        if response['PriceList']:
            for price_list_item in response['PriceList']:
                price_item = json.loads(price_list_item)
                product = price_item.get('product', {})
                attributes = product.get('attributes', {})
                item_storage_class = attributes.get('storageClass', '')
                
                if storage_class.upper() in item_storage_class.upper() or storage_class.replace('_', ' ').upper() in item_storage_class.upper():
                    on_demand = price_item['terms']['OnDemand']
                    price_dimensions = list(on_demand.values())[0]['priceDimensions']
                    price_per_gb = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
                    return price_per_gb
            
            # Default to first result
            price_item = json.loads(response['PriceList'][0])
            on_demand = price_item['terms']['OnDemand']
            price_dimensions = list(on_demand.values())[0]['priceDimensions']
            price_per_gb = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            return price_per_gb
    except Exception as e:
        logger.warning(f"Failed to get S3 pricing for {storage_class}: {e}")
    return None


@lru_cache(maxsize=100)
def get_ebs_pricing(storage_type: str, region: str) -> Optional[float]:
    """Get EBS storage pricing from AWS Price List API"""
    try:
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        location = REGION_NAMES.get(region, region)
        
        volume_type_map = {
            "gp3": "General Purpose", "gp2": "General Purpose",
            "io1": "Provisioned IOPS", "io2": "Provisioned IOPS",
            "st1": "Throughput Optimized HDD", "sc1": "Cold HDD",
        }
        volume_type = volume_type_map.get(storage_type, "General Purpose")
        
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': volume_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_item = json.loads(response['PriceList'][0])
            on_demand = price_item['terms']['OnDemand']
            price_dimensions = list(on_demand.values())[0]['priceDimensions']
            price_per_gb = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            return price_per_gb
    except Exception as e:
        logger.warning(f"Failed to get EBS pricing for {storage_type}: {e}")
    return None


# ============================================================================
# ESTIMATED SERVICES (Documented assumptions)
# ============================================================================

def get_alb_pricing(region: str = 'us-east-1') -> float:
    """
    Application Load Balancer pricing
    Assumption: $0.0225/hour + $0.008/LCU-hour for minimal usage
    """
    base_hourly = 0.0225  # ~$16.50/month
    lcu_hourly = 0.008  # ~$5.84/month for minimal usage
    return round((base_hourly + lcu_hourly) * 730, 2)


def get_nlb_pricing(region: str = 'us-east-1') -> float:
    """
    Network Load Balancer pricing
    Assumption: $0.0225/hour + $0.006/NLCU-hour for minimal usage
    """
    base_hourly = 0.0225  # ~$16.50/month
    nlcu_hourly = 0.006  # ~$4.38/month for minimal usage
    return round((base_hourly + nlcu_hourly) * 730, 2)


def get_cloudfront_pricing(data_transfer_gb: float = 1000) -> float:
    """
    CloudFront CDN pricing
    Assumption: Tiered pricing - $0.085/GB for first 10TB (US/Europe)
    """
    if data_transfer_gb <= 10240:  # First 10 TB
        return round(data_transfer_gb * 0.085, 2)
    else:
        return round(10240 * 0.085 + (data_transfer_gb - 10240) * 0.080, 2)


def get_route53_pricing(queries_per_month: int = 1000000) -> float:
    """
    Route 53 DNS pricing
    Assumption: $0.50/hosted zone + $0.40 per million queries
    """
    hosted_zone_cost = 0.50
    query_cost = (queries_per_month / 1_000_000) * 0.40
    return round(hosted_zone_cost + query_cost, 2)


def get_waf_pricing(rules: int = 5) -> float:
    """
    AWS WAF pricing
    Assumption: $5/web ACL + $1/rule
    """
    return round(5.00 + (rules * 1.00), 2)


def get_nat_gateway_pricing(data_processed_gb: float = 1000) -> float:
    """
    NAT Gateway pricing
    Assumption: $0.045/hour + $0.045/GB data processed
    """
    hourly_cost = 0.045 * 730  # ~$32.85/month
    data_processing = 0.045 * data_processed_gb
    return round(hourly_cost + data_processing, 2)


def get_vpc_endpoint_pricing(endpoint_type: str = 'interface') -> float:
    """
    VPC Endpoint pricing
    Assumption: Interface endpoints $0.01/hour, Gateway endpoints free
    """
    if endpoint_type.lower() == 'gateway':
        return 0.00
    else:  # Interface endpoint
        return round(0.01 * 730, 2)  # ~$7.30/month


def get_transit_gateway_pricing(attachments: int = 2, data_processed_gb: float = 1000) -> float:
    """
    Transit Gateway pricing
    Assumption: $0.05/hour per attachment + $0.02/GB data processed
    """
    attachment_cost = 0.05 * 730 * attachments
    data_cost = 0.02 * data_processed_gb
    return round(attachment_cost + data_cost, 2)


def get_direct_connect_pricing(port_speed: str = '1Gbps') -> float:
    """
    Direct Connect pricing
    Assumption: Port hours - 1Gbps $0.30/hour, 10Gbps $2.25/hour
    """
    port_rates = {
        '50Mbps': 0.03, '100Mbps': 0.06, '200Mbps': 0.12, '300Mbps': 0.18,
        '400Mbps': 0.24, '500Mbps': 0.30, '1Gbps': 0.30, '10Gbps': 2.25
    }
    hourly_rate = port_rates.get(port_speed, 0.30)
    return round(hourly_rate * 730, 2)


def get_vpn_pricing(connections: int = 1) -> float:
    """
    Site-to-Site VPN pricing
    Assumption: $0.05/hour per VPN connection
    """
    return round(0.05 * 730 * connections, 2)


def get_lambda_pricing(invocations: int = 1000000, avg_duration_ms: int = 200, memory_mb: int = 512) -> float:
    """
    Lambda pricing
    Assumption: $0.20 per 1M requests + $0.0000166667/GB-second
    """
    request_cost = (invocations / 1_000_000) * 0.20
    gb_seconds = (invocations * (avg_duration_ms / 1000) * (memory_mb / 1024))
    compute_cost = gb_seconds * 0.0000166667
    return round(request_cost + compute_cost, 2)


def get_dynamodb_pricing(read_units: int = 5, write_units: int = 5, storage_gb: float = 10) -> float:
    """
    DynamoDB pricing
    Assumption: $0.00013/WCU-hour, $0.00013/RCU-hour, $0.25/GB-month storage
    """
    write_cost = write_units * 0.00013 * 730
    read_cost = read_units * 0.00013 * 730
    storage_cost = storage_gb * 0.25
    return round(write_cost + read_cost + storage_cost, 2)


def get_elasticache_pricing(node_type: str = 'cache.t3.micro', nodes: int = 2) -> float:
    """
    ElastiCache pricing
    Assumption: Varies by node type - t3.micro ~$0.017/hour
    """
    node_rates = {
        'cache.t3.micro': 0.017, 'cache.t3.small': 0.034, 'cache.t3.medium': 0.068,
        'cache.m5.large': 0.136, 'cache.m5.xlarge': 0.272, 'cache.r5.large': 0.188
    }
    hourly_rate = node_rates.get(node_type, 0.017)
    return round(hourly_rate * 730 * nodes, 2)


def get_efs_pricing(storage_gb: float = 100, storage_class: str = 'standard') -> float:
    """
    EFS pricing
    Assumption: Standard $0.30/GB-month, Infrequent Access $0.025/GB-month
    """
    rates = {'standard': 0.30, 'ia': 0.025, 'infrequent_access': 0.025}
    rate = rates.get(storage_class.lower(), 0.30)
    return round(storage_gb * rate, 2)


def get_fsx_pricing(storage_gb: float = 1200, throughput_mbps: int = 64, filesystem_type: str = 'windows') -> float:
    """
    FSx pricing
    Assumption: Windows $0.013/GB-month + $2.20/MBps-month throughput
    """
    if filesystem_type.lower() == 'lustre':
        return round(storage_gb * 0.145, 2)  # Lustre pricing
    else:  # Windows
        storage_cost = storage_gb * 0.013
        throughput_cost = throughput_mbps * 2.20
        return round(storage_cost + throughput_cost, 2)


def get_eks_pricing(clusters: int = 1) -> float:
    """
    EKS pricing
    Assumption: $0.10/hour per cluster
    """
    return round(0.10 * 730 * clusters, 2)


def get_ecs_fargate_pricing(vcpu_hours: float = 730, gb_hours: float = 1460) -> float:
    """
    ECS Fargate pricing
    Assumption: $0.04048/vCPU-hour + $0.004445/GB-hour
    """
    vcpu_cost = vcpu_hours * 0.04048
    memory_cost = gb_hours * 0.004445
    return round(vcpu_cost + memory_cost, 2)


def get_kms_pricing(keys: int = 1, requests: int = 10000) -> float:
    """
    KMS pricing
    Assumption: $1/month per customer managed key + $0.03 per 10K requests
    """
    key_cost = keys * 1.00
    request_cost = (requests / 10000) * 0.03
    return round(key_cost + request_cost, 2)


def get_secrets_manager_pricing(secrets: int = 1, api_calls: int = 10000) -> float:
    """
    Secrets Manager pricing
    Assumption: $0.40/month per secret + $0.05 per 10K API calls
    """
    secret_cost = secrets * 0.40
    api_cost = (api_calls / 10000) * 0.05
    return round(secret_cost + api_cost, 2)


def get_guardduty_pricing(data_analyzed_gb: float = 1000) -> float:
    """
    GuardDuty pricing
    Assumption: Tiered pricing - first 500GB $1.15/GB, next 2000GB $0.58/GB
    """
    if data_analyzed_gb <= 500:
        return round(data_analyzed_gb * 1.15, 2)
    elif data_analyzed_gb <= 2500:
        return round(500 * 1.15 + (data_analyzed_gb - 500) * 0.58, 2)
    else:
        return round(500 * 1.15 + 2000 * 0.58 + (data_analyzed_gb - 2500) * 0.29, 2)


def get_cloudwatch_pricing(logs_gb: float = 10, metrics: int = 10, alarms: int = 10) -> float:
    """
    CloudWatch pricing
    Assumption: $0.50/GB ingested, $0.03/GB stored, $0.10/alarm, $0.30 per 1K custom metrics
    """
    ingestion = logs_gb * 0.50
    storage = logs_gb * 0.03
    alarm_cost = alarms * 0.10
    metric_cost = (metrics / 1000) * 0.30
    return round(ingestion + storage + alarm_cost + metric_cost, 2)


def get_cloudtrail_pricing(trails: int = 1, events: int = 100000) -> float:
    """
    CloudTrail pricing
    Assumption: First trail free, additional trails $2/month, $0.10 per 100K events
    """
    trail_cost = max(0, (trails - 1) * 2.00)
    event_cost = (events / 100000) * 0.10
    return round(trail_cost + event_cost, 2)


def get_backup_pricing(storage_gb: float = 100, restore_gb: float = 0) -> float:
    """
    AWS Backup pricing
    Assumption: $0.05/GB-month storage, $0.02/GB restore
    """
    storage_cost = storage_gb * 0.05
    restore_cost = restore_gb * 0.02
    return round(storage_cost + restore_cost, 2)


def get_sns_pricing(requests: int = 1000000, data_transfer_gb: float = 1) -> float:
    """
    SNS pricing
    Assumption: $0.50 per 1M requests, $0.09/GB data transfer
    """
    request_cost = (requests / 1_000_000) * 0.50
    data_cost = data_transfer_gb * 0.09
    return round(request_cost + data_cost, 2)


def get_sqs_pricing(requests: int = 1000000) -> float:
    """
    SQS pricing
    Assumption: $0.40 per 1M requests (first 1M free)
    """
    billable_requests = max(0, requests - 1_000_000)
    return round((billable_requests / 1_000_000) * 0.40, 2)


def get_kinesis_pricing(shards: int = 2, data_ingested_gb: float = 100) -> float:
    """
    Kinesis Data Streams pricing
    Assumption: $0.015/shard-hour + $0.014/GB ingested
    """
    shard_cost = shards * 0.015 * 730
    data_cost = data_ingested_gb * 0.014
    return round(shard_cost + data_cost, 2)


def get_glue_pricing(dpu_hours: float = 10) -> float:
    """
    AWS Glue pricing
    Assumption: $0.44/DPU-hour
    """
    return round(dpu_hours * 0.44, 2)


def get_athena_pricing(data_scanned_tb: float = 1) -> float:
    """
    Athena pricing
    Assumption: $5 per TB of data scanned
    """
    return round(data_scanned_tb * 5.00, 2)


def get_redshift_pricing(node_type: str = 'dc2.large', nodes: int = 2) -> float:
    """
    Redshift pricing
    Assumption: Varies by node type - dc2.large $0.25/hour
    """
    node_rates = {
        'dc2.large': 0.25, 'dc2.8xlarge': 4.80,
        'ra3.xlplus': 1.086, 'ra3.4xlarge': 3.26, 'ra3.16xlarge': 13.04
    }
    hourly_rate = node_rates.get(node_type, 0.25)
    return round(hourly_rate * 730 * nodes, 2)


def get_emr_pricing(instance_type: str = 'm5.xlarge', instances: int = 3, hours: float = 730) -> float:
    """
    EMR pricing
    Assumption: EC2 cost + EMR cost (varies by instance type)
    """
    # Simplified: ~25% markup on EC2 pricing
    ec2_hourly = 0.192  # m5.xlarge approximate
    emr_markup = ec2_hourly * 0.25
    return round((ec2_hourly + emr_markup) * hours * instances, 2)


# ============================================================================
# SERVICE PRICING ASSUMPTIONS DOCUMENTATION
# ============================================================================

SERVICE_ASSUMPTIONS = {
    "alb": "ALB: $0.0225/hour + $0.008/LCU-hour for minimal usage (~$22/month)",
    "nlb": "NLB: $0.0225/hour + $0.006/NLCU-hour for minimal usage (~$21/month)",
    "cloudfront": "CloudFront: Tiered pricing - $0.085/GB for first 10TB (US/Europe)",
    "route53": "Route53: $0.50/hosted zone + $0.40 per million queries",
    "waf": "WAF: $5/web ACL + $1/rule (~$10/month with 5 rules)",
    "nat_gateway": "NAT Gateway: $0.045/hour + $0.045/GB data processed (~$78/month for 1TB)",
    "vpc_endpoint": "VPC Endpoint: Interface $0.01/hour (~$7.30/month), Gateway free",
    "transit_gateway": "Transit Gateway: $0.05/hour per attachment + $0.02/GB data processed",
    "direct_connect": "Direct Connect: Port hours - 1Gbps $0.30/hour, 10Gbps $2.25/hour",
    "vpn": "Site-to-Site VPN: $0.05/hour per connection (~$37/month)",
    "lambda": "Lambda: $0.20 per 1M requests + $0.0000166667/GB-second compute",
    "dynamodb": "DynamoDB: $0.00013/WCU-hour, $0.00013/RCU-hour, $0.25/GB-month storage",
    "elasticache": "ElastiCache: Varies by node type (t3.micro ~$0.017/hour)",
    "efs": "EFS: Standard $0.30/GB-month, Infrequent Access $0.025/GB-month",
    "fsx": "FSx: Windows $0.013/GB-month + $2.20/MBps-month throughput",
    "eks": "EKS: $0.10/hour per cluster (~$73/month)",
    "ecs_fargate": "ECS Fargate: $0.04048/vCPU-hour + $0.004445/GB-hour",
    "kms": "KMS: $1/month per key + $0.03 per 10K requests",
    "secrets_manager": "Secrets Manager: $0.40/month per secret + $0.05 per 10K API calls",
    "guardduty": "GuardDuty: Tiered - first 500GB $1.15/GB, next 2000GB $0.58/GB",
    "cloudwatch": "CloudWatch: $0.50/GB ingested, $0.03/GB stored, $0.10/alarm",
    "cloudtrail": "CloudTrail: First trail free, additional $2/month, $0.10 per 100K events",
    "backup": "AWS Backup: $0.05/GB-month storage, $0.02/GB restore",
    "sns": "SNS: $0.50 per 1M requests, $0.09/GB data transfer",
    "sqs": "SQS: $0.40 per 1M requests (first 1M free)",
    "kinesis": "Kinesis: $0.015/shard-hour + $0.014/GB ingested",
    "glue": "Glue: $0.44/DPU-hour",
    "athena": "Athena: $5 per TB of data scanned",
    "redshift": "Redshift: Varies by node type (dc2.large $0.25/hour)",
    "emr": "EMR: EC2 cost + ~25% EMR markup",
}


def get_service_assumption(service_type: str) -> str:
    """Get pricing assumption documentation for a service"""
    return SERVICE_ASSUMPTIONS.get(service_type.lower(), "Pricing varies by usage")
