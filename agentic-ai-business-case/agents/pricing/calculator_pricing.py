"""
Real-time AWS Pricing for Calculator Generator
Uses AWS Price List API to get accurate pricing for extracted services
"""

import boto3
import json
import logging
from functools import lru_cache
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Import comprehensive pricing functions
from agents.pricing.comprehensive_pricing import (
    # AWS API Services
    get_ec2_pricing, get_rds_pricing, get_s3_pricing, get_ebs_pricing,
    # Estimated Services
    get_alb_pricing, get_nlb_pricing, get_cloudfront_pricing, get_route53_pricing,
    get_waf_pricing, get_nat_gateway_pricing, get_vpc_endpoint_pricing,
    get_transit_gateway_pricing, get_direct_connect_pricing, get_vpn_pricing,
    get_lambda_pricing, get_dynamodb_pricing, get_elasticache_pricing,
    get_efs_pricing, get_fsx_pricing, get_eks_pricing, get_ecs_fargate_pricing,
    get_kms_pricing, get_secrets_manager_pricing, get_guardduty_pricing,
    get_cloudwatch_pricing, get_cloudtrail_pricing, get_backup_pricing,
    get_sns_pricing, get_sqs_pricing, get_kinesis_pricing, get_glue_pricing,
    get_athena_pricing, get_redshift_pricing, get_emr_pricing,
    SERVICE_ASSUMPTIONS, get_service_assumption,
    REGION_NAMES
)


def calculate_service_cost(service: Dict) -> float:
    """
    Calculate monthly cost for a service using AWS Pricing API or estimates
    
    Args:
        service: Service dict with type, details, region
        
    Returns:
        Estimated monthly cost in USD
    """
    service_type = service.get('service', '').lower()
    details = service.get('details', {})
    region = service.get('region', 'us-east-1')
    quantity = service.get('quantity', 1)
    
    try:
        # AWS API Services (Real-time pricing)
        if service_type == 'ec2':
            instance_type = details.get('instance_type', 't3.medium')
            os = details.get('os', 'Linux')
            hourly_price = get_ec2_pricing(instance_type, os, region)
            
            if hourly_price:
                monthly_cost = hourly_price * 730 * quantity
                storage_gb = details.get('storage_gb', 0)
                if storage_gb:
                    storage_type = details.get('storage_type', 'gp3')
                    storage_price = get_ebs_pricing(storage_type, region)
                    if storage_price:
                        monthly_cost += storage_price * storage_gb * quantity
                return round(monthly_cost, 2)
        
        elif service_type == 'ebs':
            storage_gb = details.get('size_gb', 100)
            storage_type = details.get('storage_type', 'gp3')
            storage_price = get_ebs_pricing(storage_type, region)
            
            if storage_price:
                monthly_cost = storage_price * storage_gb * quantity
                if storage_type in ['io1', 'io2']:
                    iops = details.get('iops', 3000)
                    iops_price = 0.065
                    monthly_cost += iops_price * iops * quantity
                return round(monthly_cost, 2)
        
        elif service_type == 's3':
            storage_gb = details.get('size_gb', 100)
            storage_class = details.get('storage_class', 'STANDARD')
            storage_price = get_s3_pricing(storage_class, region)
            
            if storage_price:
                monthly_cost = storage_price * storage_gb
                put_requests = details.get('put_requests', 0)
                get_requests = details.get('get_requests', 0)
                monthly_cost += (put_requests / 1000) * 0.005
                monthly_cost += (get_requests / 10000) * 0.0004
                return round(monthly_cost, 2)
        
        elif service_type == 'rds':
            instance_type = details.get('instance_type', 'db.t3.medium')
            engine = details.get('engine', 'MySQL')
            deployment = details.get('deployment', 'Single-AZ')
            hourly_price = get_rds_pricing(instance_type, engine, deployment, region)
            
            if hourly_price:
                monthly_cost = hourly_price * 730 * quantity
                storage_gb = details.get('storage_gb', 100)
                if storage_gb:
                    storage_price = get_ebs_pricing('gp3', region) or 0.10
                    monthly_cost += storage_price * storage_gb * quantity
                return round(monthly_cost, 2)
        
        # Estimated Services (Documented assumptions)
        elif service_type in ['alb', 'elb']:
            return get_alb_pricing(region) * quantity
        
        elif service_type == 'nlb':
            return get_nlb_pricing(region) * quantity
        
        elif service_type == 'cloudfront':
            data_transfer_gb = details.get('data_transfer_gb', 1000)
            return get_cloudfront_pricing(data_transfer_gb) * quantity
        
        elif service_type == 'route53':
            queries = details.get('queries_per_month', 1_000_000)
            return get_route53_pricing(queries) * quantity
        
        elif service_type == 'waf':
            rules = details.get('rules', 5)
            return get_waf_pricing(rules) * quantity
        
        elif service_type in ['nat_gateway', 'nat']:
            data_processed_gb = details.get('data_processed_gb', 1000)
            return get_nat_gateway_pricing(data_processed_gb) * quantity
        
        elif service_type == 'vpc_endpoint':
            endpoint_type = details.get('endpoint_type', 'interface')
            return get_vpc_endpoint_pricing(endpoint_type) * quantity
        
        elif service_type == 'transit_gateway':
            attachments = details.get('attachments', 2)
            data_processed_gb = details.get('data_processed_gb', 1000)
            return get_transit_gateway_pricing(attachments, data_processed_gb) * quantity
        
        elif service_type == 'direct_connect':
            port_speed = details.get('port_speed', '1Gbps')
            return get_direct_connect_pricing(port_speed) * quantity
        
        elif service_type == 'vpn':
            connections = details.get('connections', 1)
            return get_vpn_pricing(connections) * quantity
        
        elif service_type == 'lambda':
            invocations = details.get('invocations', 1_000_000)
            avg_duration_ms = details.get('avg_duration_ms', 200)
            memory_mb = details.get('memory_mb', 512)
            return get_lambda_pricing(invocations, avg_duration_ms, memory_mb) * quantity
        
        elif service_type == 'dynamodb':
            read_units = details.get('read_units', 5)
            write_units = details.get('write_units', 5)
            storage_gb = details.get('storage_gb', 10)
            return get_dynamodb_pricing(read_units, write_units, storage_gb) * quantity
        
        elif service_type == 'elasticache':
            node_type = details.get('node_type', 'cache.t3.micro')
            nodes = details.get('nodes', 2)
            return get_elasticache_pricing(node_type, nodes) * quantity
        
        elif service_type == 'efs':
            storage_gb = details.get('storage_gb', 100)
            storage_class = details.get('storage_class', 'standard')
            return get_efs_pricing(storage_gb, storage_class) * quantity
        
        elif service_type == 'fsx':
            storage_gb = details.get('storage_gb', 1200)
            throughput_mbps = details.get('throughput_mbps', 64)
            filesystem_type = details.get('filesystem_type', 'windows')
            return get_fsx_pricing(storage_gb, throughput_mbps, filesystem_type) * quantity
        
        elif service_type == 'eks':
            clusters = details.get('clusters', 1)
            return get_eks_pricing(clusters) * quantity
        
        elif service_type in ['ecs_fargate', 'fargate']:
            vcpu_hours = details.get('vcpu_hours', 730)
            gb_hours = details.get('gb_hours', 1460)
            return get_ecs_fargate_pricing(vcpu_hours, gb_hours) * quantity
        
        elif service_type == 'kms':
            keys = details.get('keys', 1)
            requests = details.get('requests', 10000)
            return get_kms_pricing(keys, requests) * quantity
        
        elif service_type == 'secrets_manager':
            secrets = details.get('secrets', 1)
            api_calls = details.get('api_calls', 10000)
            return get_secrets_manager_pricing(secrets, api_calls) * quantity
        
        elif service_type == 'guardduty':
            data_analyzed_gb = details.get('data_analyzed_gb', 1000)
            return get_guardduty_pricing(data_analyzed_gb) * quantity
        
        elif service_type == 'cloudwatch':
            logs_gb = details.get('logs_gb', 10)
            metrics = details.get('metrics', 10)
            alarms = details.get('alarms', 10)
            return get_cloudwatch_pricing(logs_gb, metrics, alarms) * quantity
        
        elif service_type == 'cloudtrail':
            trails = details.get('trails', 1)
            events = details.get('events', 100000)
            return get_cloudtrail_pricing(trails, events) * quantity
        
        elif service_type == 'backup':
            storage_gb = details.get('storage_gb', 100)
            restore_gb = details.get('restore_gb', 0)
            return get_backup_pricing(storage_gb, restore_gb) * quantity
        
        elif service_type == 'sns':
            requests = details.get('requests', 1_000_000)
            data_transfer_gb = details.get('data_transfer_gb', 1)
            return get_sns_pricing(requests, data_transfer_gb) * quantity
        
        elif service_type == 'sqs':
            requests = details.get('requests', 1_000_000)
            return get_sqs_pricing(requests) * quantity
        
        elif service_type == 'kinesis':
            shards = details.get('shards', 2)
            data_ingested_gb = details.get('data_ingested_gb', 100)
            return get_kinesis_pricing(shards, data_ingested_gb) * quantity
        
        elif service_type == 'glue':
            dpu_hours = details.get('dpu_hours', 10)
            return get_glue_pricing(dpu_hours) * quantity
        
        elif service_type == 'athena':
            data_scanned_tb = details.get('data_scanned_tb', 1)
            return get_athena_pricing(data_scanned_tb) * quantity
        
        elif service_type == 'redshift':
            node_type = details.get('node_type', 'dc2.large')
            nodes = details.get('nodes', 2)
            return get_redshift_pricing(node_type, nodes) * quantity
        
        elif service_type == 'emr':
            instance_type = details.get('instance_type', 'm5.xlarge')
            instances = details.get('instances', 3)
            hours = details.get('hours', 730)
            return get_emr_pricing(instance_type, instances, hours) * quantity
        
    except Exception as e:
        logger.warning(f"Failed to calculate cost for {service_type}: {e}")
    
    # Return estimated cost from service if calculation fails
    return service.get('estimated_monthly_cost', 0) or 0


def enrich_services_with_pricing(services: list, region: str = 'us-east-1') -> list:
    """
    Enrich extracted services with real-time pricing from AWS API
    
    Args:
        services: List of service dicts
        region: AWS region code
        
    Returns:
        Services list with updated pricing
    """
    enriched = []
    
    # Services with AWS API pricing (Real-time)
    api_services = ['ec2', 'ebs', 's3', 'rds']
    
    # Services with estimated pricing (Documented assumptions)
    estimated_services = [
        'alb', 'nlb', 'elb', 'cloudfront', 'route53', 'waf', 'nat_gateway', 'nat',
        'vpc_endpoint', 'transit_gateway', 'direct_connect', 'vpn',
        'lambda', 'dynamodb', 'elasticache', 'efs', 'fsx', 'eks', 'ecs_fargate', 'fargate',
        'kms', 'secrets_manager', 'guardduty', 'cloudwatch', 'cloudtrail', 'backup',
        'sns', 'sqs', 'kinesis', 'glue', 'athena', 'redshift', 'emr'
    ]
    
    for service in services:
        service_copy = service.copy()
        service_copy['region'] = region
        service_type = service.get('service', '').lower()
        
        # Calculate cost using AWS Pricing API or estimates
        calculated_cost = calculate_service_cost(service_copy)
        
        if calculated_cost > 0:
            service_copy['estimated_monthly_cost'] = calculated_cost
            # Mark source based on service type
            if service_type in api_services:
                service_copy['pricing_source'] = 'aws_api'
            elif service_type in estimated_services:
                service_copy['pricing_source'] = 'estimated'
                # Add assumption documentation
                service_copy['pricing_assumption'] = get_service_assumption(service_type)
            else:
                service_copy['pricing_source'] = 'estimated'
                service_copy['pricing_assumption'] = 'Pricing varies by usage'
        else:
            # Keep existing estimate or set to 0
            service_copy['estimated_monthly_cost'] = service.get('estimated_monthly_cost', 0)
            service_copy['pricing_source'] = 'estimated'
            service_copy['pricing_assumption'] = get_service_assumption(service_type)
        
        enriched.append(service_copy)
    
    return enriched
