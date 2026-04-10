"""
AWS Pricing Calculator URL Generator
Generates shareable AWS Pricing Calculator URLs from service descriptions
Based on: https://github.com/quincysting/aws-pricing-calculator
"""

import json
import uuid
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class AWSCalculatorGenerator:
    """Generate shareable AWS Pricing Calculator URLs"""
    
    # Service name mappings (AWS Calculator service keys)
    SERVICE_MAPPINGS = {
        'ec2': 'ec2Enhancement',
        'ebs': 'amazonElasticBlockStore',
        's3': 'amazonS3',
        'secrets_manager': 'awsSecretsManager',
        'flink': 'amazonKinesisDataAnalytics',
        # Tier 2 services (may show read-only warning)
        'appstream': 'amazonAppStream',
        'rds_oracle': 'amazonRdsForOracle',
        'msk': 'amazonManagedStreamingForApacheKafkaMsk',
        'opensearch': 'amazonElasticsearchService',
    }
    
    # Service versions (discovered from AWS Calculator)
    SERVICE_VERSIONS = {
        'ec2Enhancement': '0.0.68',
        'amazonElasticBlockStore': '0.0.155',
        'amazonS3': '0.0.1',
        'awsSecretsManager': '0.0.24',
        'amazonKinesisDataAnalytics': '0.0.29',
        'amazonAppStream': '0.0.68',
        'amazonRdsForOracle': '0.0.68',
        'amazonManagedStreamingForApacheKafkaMsk': '0.0.68',
        'amazonElasticsearchService': '0.0.68',
    }
    
    # Supported services with working calculationComponents
    SUPPORTED_SERVICES = {
        'ec2': 'Tier 1 - Fully editable',
        'ebs': 'Tier 1 - Fully editable',
        's3': 'Tier 1 - Fully editable',
        'secrets_manager': 'Tier 1 - Fully editable',
        'flink': 'Tier 1 - Fully editable',
        'appstream': 'Tier 2 - May show read-only warning',
        'rds_oracle': 'Tier 2 - May show read-only warning',
        'msk': 'Tier 2 - May show read-only warning',
        'opensearch': 'Tier 2 - May show read-only warning',
    }
    
    # Region name mappings
    REGION_NAMES = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "eu-west-1": "Europe (Ireland)",
        "eu-central-1": "Europe (Frankfurt)",
    }
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.region_name = self.REGION_NAMES.get(region, region)
        
    def create_estimate_from_services(
        self,
        services: List[Dict[str, Any]],
        estimate_name: str = "AWS Migration Estimate",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create estimate JSON from service list in AWS Calculator format
        
        Args:
            services: List of service dicts with 'service', 'quantity', 'details'
            estimate_name: Name for the estimate
            description: Description of the estimate
            
        Returns:
            Estimate JSON ready for AWS Save API
        """
        # Create a group with all services
        group_id = f"grp-{str(uuid.uuid4())}"
        services_dict = {}
        group_monthly = 0.0
        
        for service in services:
            service_id = f"{service.get('service', 'svc')}-{str(uuid.uuid4())}"
            service_code = self.SERVICE_MAPPINGS.get(service.get('service', '').lower())
            
            if not service_code:
                continue
            
            monthly_cost = service.get('estimated_monthly_cost', 0) or 0
            group_monthly += monthly_cost
            
            # Determine estimateFor value based on service type
            service_type = service.get('service', '').lower()
            estimate_for = self._get_estimate_for(service_type)
            
            # Build service entry in calculator format (without version to test)
            service_entry = {
                "calculationComponents": self._create_calculation_components(service),
                "serviceCode": service_code,
                "region": self.region,
                "estimateFor": estimate_for,
                "description": None,
                "serviceCost": {
                    "monthly": round(monthly_cost, 2),
                    "upfront": 0
                },
                "serviceName": service.get('description', service_code),
                "regionName": self.region_name,
                "configSummary": service.get('description', ''),
            }
            
            services_dict[service_id] = service_entry
        
        # Build the estimate in the correct format
        estimate = {
            "name": estimate_name,
            "services": {},  # Top-level services (empty for grouped estimates)
            "groups": {
                group_id: {
                    "name": estimate_name,
                    "services": services_dict,
                    "groups": {},  # Nested groups (empty)
                    "groupSubtotal": {},
                    "totalCost": {
                        "monthly": round(group_monthly, 2),
                        "upfront": 0
                    }
                }
            },
            "groupSubtotal": {},
            "totalCost": {
                "monthly": round(group_monthly, 2),
                "upfront": 0
            },
            "support": {},
            "metaData": {
                "locale": "en_US",
                "currency": "USD",
                "createdOn": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "source": "calculator-platform"
            }
        }
        
        return estimate
    
    def _get_estimate_for(self, service_type: str) -> str:
        """Get the correct estimateFor value for each service type"""
        estimate_for_map = {
            'ec2': 'template',
            'ebs': 'elasticBlockStore',
            's3': 'template_0',
            'secrets_manager': 'awssecretsmanager',
            'flink': 'template',
            'appstream': 'appStream2',
            'rds_oracle': 'rdsForOracle',
            'msk': 'amazonMSK',
            'opensearch': 'elasticSearchService',
        }
        return estimate_for_map.get(service_type, 'template')
    
    def _create_calculation_components(self, service: Dict[str, Any]) -> Dict[str, Any]:
        """Create calculationComponents based on service type using proven formats"""
        service_type = service.get('service', '').lower()
        details = service.get('details', {})
        
        # Use proven formats for supported services
        if service_type == 'ec2':
            return self._create_ec2_components_tier1(details)
        elif service_type == 'ebs':
            return self._create_ebs_components_tier1(details)
        elif service_type == 's3':
            return self._create_s3_components_tier1(details)
        elif service_type == 'secrets_manager':
            return self._create_secrets_manager_components_tier1(details)
        elif service_type == 'flink':
            return self._create_flink_components_tier1(details)
        else:
            # For unsupported services, return minimal components
            return {}
    
    def _create_ec2_components_tier1(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """EC2 Tier 1 - Fully editable format"""
        instance_count = str(details.get('quantity', 1))
        instance_type = details.get('instance_type', 't3.medium')
        os = details.get('os', 'Linux').lower()
        storage_gb = str(details.get('storage_gb', 30))
        
        return {
            "tenancy": {"value": "shared"},
            "selectedOS": {"value": os},
            "workloadSelection": {"value": "consistent"},
            "workload": {
                "value": {
                    "workloadType": "consistent",
                    "data": instance_count
                }
            },
            "instanceType": {"value": instance_type},
            "pricingStrategy": {
                "value": {
                    "selectedOption": "onDemand"
                }
            },
            "storageType": {"value": "Storage General Purpose gp3 GB Mo"},
            "storageAmount": {"value": storage_gb, "unit": "gb"},
            "snapshotFrequency": {"value": "0"},
            "detailedMonitoringCheckbox": {"value": False},
            "ec2AdvancedPricingMetrics": {"value": 1},
            "dataTransferForEC2": {
                "value": [
                    {"entryType": "INBOUND", "value": "", "unit": "tb_month", "fromRegion": ""},
                    {"entryType": "OUTBOUND", "value": "", "unit": "tb_month", "toRegion": ""},
                    {"entryType": "INTRA_REGION", "value": "", "unit": "tb_month"}
                ]
            }
        }
    
    def _create_ebs_components_tier1(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """EBS Tier 1 - Fully editable format"""
        storage_gb = str(details.get('size_gb', 100))
        iops = str(details.get('iops', 3000))
        storage_type = details.get('storage_type', 'gp3')
        
        storage_type_value = "Storage General Purpose gp3 GB Mo" if storage_type == 'gp3' else "Storage Provisioned IOPS GB Mo"
        
        return {
            "numberOfInstances": {"value": "1"},
            "durationOfInstanceRuns": {"value": "730", "unit": "hours"},
            "storageType": {"value": storage_type_value},
            "storageAmount": {"value": storage_gb, "unit": "gb|NA"},
            "iops": {"value": iops},
            "snapshotFrequency": {"value": "0"},
            "snapshotAmount": {"value": "0", "unit": "gb|NA"}
        }
    
    def _create_s3_components_tier1(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """S3 Tier 1 - Fully editable format"""
        storage_gb = str(details.get('size_gb', 100))
        put_requests = str(details.get('put_requests', 10000))
        get_requests = str(details.get('get_requests', 100000))
        
        return {
            "s3Services_generated_0": {"value": storage_gb, "unit": "gb"},
            "s3Services_generated_1": {"value": put_requests},
            "s3Services_generated_2": {"value": get_requests},
            "s3Services_generated_3": {"value": "0", "unit": "gb"}
        }
    
    def _create_secrets_manager_components_tier1(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Secrets Manager Tier 1 - Fully editable format"""
        num_secrets = str(details.get('num_secrets', 2))
        api_calls = str(details.get('api_calls', 10000))
        
        return {
            "NumberOfSecrets": {"value": num_secrets},
            "secretDuration": {"value": "730"},
            "numberOfAPIs": {"value": api_calls, "unit": "perMonth"}
        }
    
    def _create_flink_components_tier1(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Apache Flink Tier 1 - Fully editable format"""
        num_apps = str(details.get('num_apps', 1))
        kpus = str(details.get('kpus', 4))
        
        return {
            "numberOfFlinkApps": {"value": num_apps},
            "numberOfFlinkKPU": {"value": kpus, "unit": "perHour"},
            "numberOfBackups": {"value": "1"},
            "appBackupSize": {"value": "1", "unit": "gb"},
            "numberOfStudioApps": {"value": "0"},
            "numberOfStudioKPU": {"value": "0", "unit": "perHour"}
        }
    
    
    def save_estimate_to_aws(self, estimate: Dict[str, Any]) -> Optional[str]:
        """
        Save estimate to AWS and get shareable URL
        
        Args:
            estimate: Estimate JSON
            
        Returns:
            Shareable calculator URL or None if failed
        """
        try:
            # The actual AWS Calculator Save API endpoint
            save_url = "https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs"
            
            print(f"Saving estimate to AWS Calculator API: {save_url}")
            
            # Use the same headers as the reference implementation
            response = requests.post(
                save_url,
                json=estimate,
                headers={
                    'Content-Type': 'application/json',
                    'Origin': 'https://calculator.aws',
                    'Referer': 'https://calculator.aws/',
                },
                timeout=30
            )
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                
                # The API returns a Lambda response with body as a JSON string
                if 'body' in data and isinstance(data['body'], str):
                    body = json.loads(data['body'])
                    saved_key = body.get('savedKey')
                else:
                    saved_key = data.get('savedKey') or data.get('estimateId') or data.get('id')
                
                if saved_key:
                    calculator_url = f"https://calculator.aws/#/estimate?id={saved_key}"
                    print(f"✓ Successfully generated calculator URL: {calculator_url}")
                    return calculator_url
                else:
                    print(f"✗ No savedKey in response: {data}")
                    return None
            else:
                print(f"✗ API returned error status: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                    
        except requests.exceptions.RequestException as req_err:
            print(f"✗ Request failed: {req_err}")
            return None
        except json.JSONDecodeError as je:
            print(f"✗ Failed to parse JSON response: {je}")
            return None
        except Exception as e:
            print(f"✗ Error saving estimate: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_calculator_url(
        self,
        services: List[Dict[str, Any]],
        estimate_name: str = "AWS Migration Estimate",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Generate complete calculator URL from services
        
        Args:
            services: List of service dicts
            estimate_name: Name for the estimate
            description: Description
            
        Returns:
            Dict with 'url', 'estimate', 'summary'
        """
        # Create estimate JSON
        estimate = self.create_estimate_from_services(
            services,
            estimate_name,
            description
        )
        
        # Save to AWS and get URL
        calculator_url = self.save_estimate_to_aws(estimate)
        
        # Create summary
        summary = {
            'total_services': len(services),
            'services_by_type': {},
            'estimate_name': estimate_name,
            'region': self.region
        }
        
        for service in services:
            service_type = service.get('service', 'unknown')
            summary['services_by_type'][service_type] = \
                summary['services_by_type'].get(service_type, 0) + 1
        
        return {
            'url': calculator_url,
            'estimate': estimate,
            'summary': summary,
            'success': calculator_url is not None
        }
