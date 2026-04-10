"""
OLA Pricing Engine
Real AWS pricing with rightsizing for Dedicated Hosts, Shared EC2, and RDS
"""
import boto3
import json
from typing import Dict, List, Tuple, Optional
import pandas as pd


class OLAPricingEngine:
    """Calculate real AWS pricing for OLA scenarios"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # Rightsizing mapping: vCPU -> EC2 instance type
        self.instance_mapping = {
            1: 't3.small',
            2: 't3.medium',
            4: 't3.xlarge',
            8: 't3.2xlarge',
            16: 'm5.4xlarge',
            32: 'm5.8xlarge',
            64: 'm5.16xlarge',
            96: 'm5.24xlarge'
        }
        
        # Dedicated Host mapping with actual capacity
        self.dedicated_host_mapping = {
            'c5.metal': {'vcpus': 96, 'memory': 192, 'hourly_cost': None},  # Compute optimized
            'm5.metal': {'vcpus': 96, 'memory': 384, 'hourly_cost': None},  # General purpose
            'r5.metal': {'vcpus': 96, 'memory': 768, 'hourly_cost': None}   # Memory optimized
        }
    
    def calculate_dedicated_host_packing(self, vms: List[Dict]) -> Dict:
        """
        Calculate optimal Dedicated Host allocation using bin-packing
        
        Args:
            vms: List of VMs with 'vcpu' and 'memory' requirements
        
        Returns: Dict with host allocation and costs
        """
        # Sort VMs by size (largest first) for better packing
        sorted_vms = sorted(vms, key=lambda x: (x['vcpu'], x['memory']), reverse=True)
        
        # Try each host type and pick the most cost-effective
        best_allocation = None
        best_cost = float('inf')
        
        for host_type, specs in self.dedicated_host_mapping.items():
            allocation = self._pack_vms_on_hosts(sorted_vms, specs['vcpus'], specs['memory'])
            host_cost = self.get_dedicated_host_pricing(host_type)
            total_cost = allocation['hosts_needed'] * host_cost
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_allocation = {
                    'host_type': host_type,
                    'hosts_needed': allocation['hosts_needed'],
                    'total_monthly_cost': total_cost,
                    'cost_per_vm': total_cost / len(vms) if len(vms) > 0 else 0,
                    'utilization': allocation['utilization'],
                    'vms_per_host': allocation['vms_per_host']
                }
        
        return best_allocation
    
    def _pack_vms_on_hosts(self, vms: List[Dict], host_vcpus: int, host_memory: int) -> Dict:
        """
        Bin-packing algorithm for VMs on Dedicated Hosts
        
        Returns: Dict with hosts_needed, utilization, vms_per_host
        """
        hosts = []
        current_host = {'vcpus_used': 0, 'memory_used': 0, 'vms': []}
        
        for vm in vms:
            vm_vcpu = vm.get('vcpu', 4)
            vm_memory = vm.get('memory', 16)
            
            # Check if VM fits on current host
            if (current_host['vcpus_used'] + vm_vcpu <= host_vcpus and 
                current_host['memory_used'] + vm_memory <= host_memory):
                # Add to current host
                current_host['vcpus_used'] += vm_vcpu
                current_host['memory_used'] += vm_memory
                current_host['vms'].append(vm)
            else:
                # Need a new host
                if current_host['vms']:  # Save current host if it has VMs
                    hosts.append(current_host)
                
                # Start new host
                current_host = {
                    'vcpus_used': vm_vcpu,
                    'memory_used': vm_memory,
                    'vms': [vm]
                }
        
        # Add the last host
        if current_host['vms']:
            hosts.append(current_host)
        
        # Calculate utilization
        total_vcpu_utilization = sum(h['vcpus_used'] for h in hosts) / (len(hosts) * host_vcpus) if hosts else 0
        total_memory_utilization = sum(h['memory_used'] for h in hosts) / (len(hosts) * host_memory) if hosts else 0
        
        return {
            'hosts_needed': len(hosts),
            'utilization': {
                'vcpu': total_vcpu_utilization * 100,
                'memory': total_memory_utilization * 100,
                'average': (total_vcpu_utilization + total_memory_utilization) / 2 * 100
            },
            'vms_per_host': [len(h['vms']) for h in hosts]
        }
    
    def detect_license_date(self, version: str, product_type: str = 'windows') -> str:
        """
        Detect if license is pre or post October 2019
        
        Args:
            version: Version string (e.g., "Windows Server 2016", "SQL Server 2017")
            product_type: 'windows' or 'sql'
        
        Returns: 'pre_2019' or 'post_2019'
        """
        if not version or pd.isna(version):
            return 'unknown'
        
        version_str = str(version).lower()
        
        if product_type == 'windows':
            # Windows Server versions
            # Pre-2019: 2008, 2008 R2, 2012, 2012 R2, 2016, 2019 (released Oct 2018)
            # Post-2019: 2022 and later
            if any(v in version_str for v in ['2022', '2025']):
                return 'post_2019'
            elif any(v in version_str for v in ['2008', '2012', '2016', '2019']):
                return 'pre_2019'
            else:
                return 'unknown'
        
        elif product_type == 'sql':
            # SQL Server versions
            # Pre-2019: 2008, 2008 R2, 2012, 2014, 2016, 2017, 2019 (released Nov 2018)
            # Post-2019: 2022 and later
            if any(v in version_str for v in ['2022', '2025']):
                return 'post_2019'
            elif any(v in version_str for v in ['2008', '2012', '2014', '2016', '2017', '2019']):
                return 'pre_2019'
            else:
                return 'unknown'
        
        return 'unknown'
    
    def rightsize_instance(self, vcpu: int, memory_gb: int) -> str:
        """
        Rightsize to appropriate EC2 instance type
        Returns: instance type (e.g., 'm5.4xlarge')
        """
        # Find closest vCPU match
        vcpu_options = sorted(self.instance_mapping.keys())
        selected_vcpu = min([v for v in vcpu_options if v >= vcpu], default=vcpu_options[-1])
        
        instance_type = self.instance_mapping[selected_vcpu]
        
        # Adjust for memory-intensive workloads
        if memory_gb > selected_vcpu * 8:  # More than 8GB per vCPU
            # Use memory-optimized (r5 family)
            instance_type = instance_type.replace('t3', 'r5').replace('m5', 'r5')
        
        return instance_type
    
    def get_ec2_pricing(self, instance_type: str, os: str, tenancy: str = 'Shared') -> float:
        """
        Get EC2 pricing from AWS Pricing API (3-year Reserved Instance, No Upfront)
        
        Args:
            instance_type: e.g., 'm5.4xlarge'
            os: 'Windows' or 'Linux'
            tenancy: 'Shared', 'Dedicated', or 'Host'
        
        Returns: Monthly cost in USD
        """
        try:
            # Map OS to AWS pricing terms
            operating_system = 'Windows' if 'windows' in str(os).lower() else 'Linux'
            
            # Try Reserved Instance pricing first (3-year, No Upfront)
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name()},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=10
            )
            
            if not response['PriceList']:
                # Fallback to estimated pricing
                return self._estimate_ec2_cost(instance_type, os, tenancy)
            
            # Parse pricing - look for Reserved Instance terms
            for price_list_item in response['PriceList']:
                price_item = json.loads(price_list_item)
                
                # Check if Reserved terms exist
                if 'Reserved' in price_item.get('terms', {}):
                    reserved_terms = price_item['terms']['Reserved']
                    
                    # Find 3-year No Upfront option
                    for term_key, term_value in reserved_terms.items():
                        term_attrs = term_value.get('termAttributes', {})
                        
                        if (term_attrs.get('LeaseContractLength') == '3yr' and 
                            term_attrs.get('PurchaseOption') == 'No Upfront'):
                            
                            # Get the hourly rate
                            price_dimensions = term_value.get('priceDimensions', {})
                            for dim_key, dim_value in price_dimensions.items():
                                if 'Hrs' in dim_value.get('unit', ''):
                                    hourly_rate = float(dim_value['pricePerUnit']['USD'])
                                    # Monthly cost (730 hours)
                                    monthly_cost = hourly_rate * 730
                                    return monthly_cost
                
                # If no Reserved pricing found, try On-Demand and apply 60% discount
                if 'OnDemand' in price_item.get('terms', {}):
                    on_demand = price_item['terms']['OnDemand']
                    price_dimensions = list(on_demand.values())[0]['priceDimensions']
                    hourly_rate = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
                    # Apply 60% discount for 3-year RI approximation
                    monthly_cost = hourly_rate * 730 * 0.4
                    return monthly_cost
            
            # Fallback to estimated pricing
            return self._estimate_ec2_cost(instance_type, os, tenancy)
            
        except Exception as e:
            print(f"Error getting EC2 pricing: {e}")
            return self._estimate_ec2_cost(instance_type, os, tenancy)
    
    def get_dedicated_host_pricing(self, host_type: str) -> float:
        """
        Get Dedicated Host pricing (3-year Reserved Instance, No Upfront)

        Uses productFamily='Dedicated Host' and instanceType (e.g. 'm5')
        to query the AWS Pricing API correctly for DH pricing.

        Args:
            host_type: 'c5.metal', 'm5.metal', 'r5.metal'

        Returns: Monthly cost in USD
        """
        # Extract instance family from host_type (e.g. 'm5.metal' -> 'm5')
        # DH Pricing API uses instanceType='m5' (not 'm5.metal')
        dh_instance_type = host_type.split('.')[0]

        estimates = {
            'm5.metal': 2800, 'r5.metal': 3500, 'c5.metal': 2500,
            'm5n.metal': 2900, 'r5n.metal': 3600
        }

        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Dedicated Host'},
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': dh_instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name()},
            ]

            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                FormatVersion='aws_v1',
                MaxResults=10
            )

            if not response['PriceList']:
                return estimates.get(host_type, 3500)

            for price_list_item in response['PriceList']:
                price_item = json.loads(price_list_item)

                # Look for 3-year Reserved Instance, No Upfront
                if 'Reserved' in price_item.get('terms', {}):
                    reserved_terms = price_item['terms']['Reserved']
                    for term_key, term_value in reserved_terms.items():
                        term_attrs = term_value.get('termAttributes', {})
                        if (term_attrs.get('LeaseContractLength') == '3yr' and 
                            term_attrs.get('PurchaseOption') == 'No Upfront'):
                            price_dimensions = term_value.get('priceDimensions', {})
                            for dim_key, dim_value in price_dimensions.items():
                                if 'Hrs' in dim_value.get('unit', ''):
                                    hourly_rate = float(dim_value['pricePerUnit']['USD'])
                                    if hourly_rate > 0:
                                        return hourly_rate * 730

                # Fallback: On-Demand with 60% discount for 3yr RI approximation
                if 'OnDemand' in price_item.get('terms', {}):
                    on_demand = price_item['terms']['OnDemand']
                    price_dimensions = list(on_demand.values())[0]['priceDimensions']
                    hourly_rate = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
                    if hourly_rate > 0:
                        return hourly_rate * 730 * 0.4

            return estimates.get(host_type, 3500)

        except Exception as e:
            print(f"Error getting Dedicated Host pricing: {e}")
            return estimates.get(host_type, 3500)
    
    def get_rds_pricing(self, db_type: str, instance_type: str, edition: str = 'Standard') -> float:
        """
        Get RDS pricing (License Included, 3-year Reserved Instance, No Upfront)
        
        Args:
            db_type: 'SQL Server' or 'Oracle'
            instance_type: e.g., 'db.m5.4xlarge'
            edition: 'Standard', 'Enterprise', 'Web'
        
        Returns: Monthly cost in USD
        """
        try:
            # Map to RDS engine
            if 'sql' in str(db_type).lower():
                engine = 'SQL Server'
                database_engine = f'SQL Server {edition} Edition'
            elif 'oracle' in str(db_type).lower():
                engine = 'Oracle'
                database_engine = f'Oracle {edition} Edition'
            else:
                return 0
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': database_engine},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name()}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters,
                MaxResults=10
            )
            
            if not response['PriceList']:
                return self._estimate_rds_cost(db_type, instance_type, edition)
            
            # Parse pricing - look for Reserved Instance terms
            for price_list_item in response['PriceList']:
                price_item = json.loads(price_list_item)
                
                # Check if Reserved terms exist
                if 'Reserved' in price_item.get('terms', {}):
                    reserved_terms = price_item['terms']['Reserved']
                    
                    # Find 3-year No Upfront option
                    for term_key, term_value in reserved_terms.items():
                        term_attrs = term_value.get('termAttributes', {})
                        
                        if (term_attrs.get('LeaseContractLength') == '3yr' and 
                            term_attrs.get('PurchaseOption') == 'No Upfront'):
                            
                            # Get the hourly rate
                            price_dimensions = term_value.get('priceDimensions', {})
                            for dim_key, dim_value in price_dimensions.items():
                                if 'Hrs' in dim_value.get('unit', ''):
                                    hourly_rate = float(dim_value['pricePerUnit']['USD'])
                                    # Monthly cost (730 hours)
                                    monthly_cost = hourly_rate * 730
                                    return monthly_cost
                
                # If no Reserved pricing found, try On-Demand and apply 60% discount
                if 'OnDemand' in price_item.get('terms', {}):
                    on_demand = price_item['terms']['OnDemand']
                    price_dimensions = list(on_demand.values())[0]['priceDimensions']
                    hourly_rate = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
                    # Apply 60% discount for 3-year RI approximation
                    monthly_cost = hourly_rate * 730 * 0.4
                    return monthly_cost
            
            return self._estimate_rds_cost(db_type, instance_type, edition)
            
        except Exception as e:
            print(f"Error getting RDS pricing: {e}")
            return self._estimate_rds_cost(db_type, instance_type, edition)
    
    def calculate_server_costs(self, server: Dict, sa_status: str, license_date: str = 'post_2019') -> Dict:
        """
        Calculate costs for a single server across all deployment options
        
        Args:
            server: Dict with 'vcpu', 'memory', 'os'
            sa_status: Software Assurance status ('all_active', 'mixed', 'none_unknown', 'need_verify')
            license_date: 'pre_2019' or 'post_2019'
        
        Returns: Dict with costs for each option and availability
        """
        vcpu = int(server.get('vcpu', 4) or 4)
        memory = int(server.get('memory', 16) or 16)
        os = str(server.get('os', 'Linux') or 'Linux')
        
        instance_type = self.rightsize_instance(vcpu, memory)
        
        costs = {}
        recommendations = {}
        
        is_windows = 'windows' in os.lower()
        
        # Option 1: Dedicated Host with BYOL
        # Always calculate for comparison; mark eligibility separately
        if is_windows:
            host_cost = self.get_dedicated_host_pricing('m5.metal')
            costs['dedicated_host_byol'] = host_cost / 8  # Amortized per VM (assume 8 VMs per host)
            byol_eligible = (license_date == 'pre_2019' or sa_status in ['all_active', 'mixed'])
            recommendations['dedicated_host_byol'] = {
                'available': True,
                'byol_eligible': byol_eligible,
                'reason': ('BYOL eligible: ' + ('Pre-Oct 2019 license' if license_date == 'pre_2019' else 'Active SA'))
                          if byol_eligible else 'Requires SA verification for BYOL — cost shown for comparison',
                'savings': 'Bring your own licenses - no AWS license cost'
            }
        else:
            costs['dedicated_host_byol'] = None
            recommendations['dedicated_host_byol'] = {
                'available': False,
                'byol_eligible': False,
                'reason': 'Linux - no licensing restrictions',
                'action': 'Use standard EC2 instances'
            }
        
        # Option 2: Shared EC2 with License Included (always available)
        costs['shared_ec2_li'] = self.get_ec2_pricing(instance_type, os, 'Shared')
        recommendations['shared_ec2_li'] = {
            'available': True,
            'reason': 'Always available - AWS provides licenses',
            'savings': 'No license management, pay-as-you-go'
        }
        
        costs['instance_type'] = instance_type
        costs['vcpu'] = vcpu
        costs['memory'] = memory
        costs['recommendations'] = recommendations
        
        return costs
    
    def calculate_database_costs(self, database: Dict, sa_status: str, license_date: str = 'post_2019') -> Dict:
        """
        Calculate costs for a single database across all deployment options
        
        Args:
            database: Dict with 'type', 'edition', 'vcpu', 'memory'
            sa_status: Software Assurance status
            license_date: 'pre_2019' or 'post_2019'
        
        Returns: Dict with costs for each option and availability
        """
        db_type = str(database.get('type', 'SQL Server') or 'SQL Server')
        edition = str(database.get('edition', 'Standard') or 'Standard')
        vcpu = int(database.get('vcpu', 8) or 8)
        memory = int(database.get('memory', 32) or 32)
        
        # Rightsize to RDS instance
        instance_type = self.rightsize_instance(vcpu, memory)
        rds_instance = instance_type.replace('m5', 'db.m5').replace('t3', 'db.t3')
        
        costs = {}
        recommendations = {}
        
        is_sql_or_oracle = 'sql' in str(db_type).lower() or 'oracle' in str(db_type).lower()
        
        # Option 1: Dedicated Host with BYOL
        # Always calculate for comparison; mark eligibility separately
        if is_sql_or_oracle:
            host_cost = self.get_dedicated_host_pricing('m5.metal')
            costs['dedicated_host_byol'] = host_cost / 4  # Assume 4 DBs per host
            byol_eligible = (license_date == 'pre_2019' or sa_status in ['all_active', 'mixed'])
            recommendations['dedicated_host_byol'] = {
                'available': True,
                'byol_eligible': byol_eligible,
                'reason': ('BYOL eligible: ' + ('Pre-Oct 2019 license' if license_date == 'pre_2019' else 'Active SA'))
                          if byol_eligible else 'Requires SA verification for BYOL — cost shown for comparison',
                'savings': 'Bring your own licenses - significant savings for Enterprise edition'
            }
        else:
            costs['dedicated_host_byol'] = None
            recommendations['dedicated_host_byol'] = {
                'available': False,
                'byol_eligible': False,
                'reason': 'Not applicable for this database type'
            }
        
        # Option 2: RDS with License Included (always available)
        costs['rds_li'] = self.get_rds_pricing(db_type, rds_instance, edition)
        recommendations['rds_li'] = {
            'available': True,
            'reason': 'Fully managed service - AWS handles licensing, patching, backups',
            'savings': 'Reduced operational overhead, high availability built-in'
        }
        
        costs['instance_type'] = rds_instance
        costs['vcpu'] = vcpu
        costs['memory'] = memory
        costs['recommendations'] = recommendations
        
        return costs
    
    def _get_location_name(self) -> str:
        """Map region to AWS Pricing API location name"""
        location_map = {
            'us-east-1': 'US East (N. Virginia)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'ap-southeast-1': 'Asia Pacific (Singapore)'
        }
        return location_map.get(self.region, 'US East (N. Virginia)')
    
    def _estimate_ec2_cost(self, instance_type: str, os: str, tenancy: str) -> float:
        """Fallback cost estimates"""
        base_costs = {
            't3.small': 15, 't3.medium': 30, 't3.xlarge': 120, 't3.2xlarge': 240,
            'm5.4xlarge': 560, 'm5.8xlarge': 1120, 'm5.16xlarge': 2240, 'm5.24xlarge': 3360
        }
        base = base_costs.get(instance_type, 500)
        
        # Windows adds ~40% cost
        if 'windows' in str(os).lower():
            base *= 1.4
        
        return base
    
    def _estimate_rds_cost(self, db_type: str, instance_type: str, edition: str) -> float:
        """Fallback RDS cost estimates"""
        base_costs = {
            'db.t3.small': 50, 'db.t3.medium': 100, 'db.t3.xlarge': 400,
            'db.m5.4xlarge': 1200, 'db.m5.8xlarge': 2400
        }
        base = base_costs.get(instance_type, 800)
        
        # SQL Server Enterprise is ~3x Standard
        if 'enterprise' in str(edition).lower():
            base *= 3
        
        # Oracle is typically more expensive
        if 'oracle' in str(db_type).lower():
            base *= 1.5
        
        return base

    
    def analyze_migration_options(self, servers_df: pd.DataFrame, databases_df: pd.DataFrame, 
                                  sa_status: str) -> Dict:
        """
        Analyze all migration options for servers and databases with version breakdown
        Uses intelligent bin-packing for Dedicated Host cost calculation
        
        Returns: Complete cost analysis with recommendations and version breakdown
        """
        results = {
            'servers': {
                'total': len(servers_df),
                'windows': 0,
                'linux': 0,
                'windows_pre_2019': 0,
                'windows_post_2019': 0,
                'windows_unknown': 0,
                'costs': {
                    'dedicated_host_byol': 0,
                    'shared_ec2_li': 0
                },
                'version_breakdown': {
                    'pre_2019': {'count': 0, 'dedicated_host': 0, 'license_included': 0},
                    'post_2019': {'count': 0, 'dedicated_host': 0, 'license_included': 0},
                    'unknown': {'count': 0, 'dedicated_host': 0, 'license_included': 0}
                },
                'dedicated_host_allocation': None,
                'details': []
            },
            'databases': {
                'total': len(databases_df),
                'sql_server': 0,
                'oracle': 0,
                'sql_pre_2019': 0,
                'sql_post_2019': 0,
                'sql_unknown': 0,
                'costs': {
                    'dedicated_host_byol': 0,
                    'rds_li': 0
                },
                'version_breakdown': {
                    'pre_2019': {'count': 0, 'dedicated_host': 0, 'rds_li': 0},
                    'post_2019': {'count': 0, 'dedicated_host': 0, 'rds_li': 0},
                    'unknown': {'count': 0, 'dedicated_host': 0, 'rds_li': 0}
                },
                'dedicated_host_allocation': None,
                'details': []
            },
            'summary': {},
            'recommendations': []
        }
        
        # Collect Windows VMs for bin-packing (ALL Windows, not just BYOL-eligible)
        windows_vms_all = []
        
        # Process servers
        for _, server_row in servers_df.iterrows():
            os_version = str(server_row.get('os', 'Linux') or 'Linux')
            server_name = str(server_row.get('name', '') or server_row.get('vm name', '') or server_row.get('dns name', '') or '')
            server = {
                'vcpu': int(server_row.get('cpus', 4) or 4) if not pd.isna(server_row.get('cpus', 4)) else 4,
                'memory': int(server_row.get('memory', 16) or 16) if not pd.isna(server_row.get('memory', 16)) else 16,
                'os': os_version
            }
            
            is_windows = 'windows' in str(server['os']).lower()
            
            if is_windows:
                results['servers']['windows'] += 1
                windows_vms_all.append(server)
                
                # Detect version
                license_date = self.detect_license_date(os_version, 'windows')
                
                if license_date == 'pre_2019':
                    results['servers']['windows_pre_2019'] += 1
                elif license_date == 'post_2019':
                    results['servers']['windows_post_2019'] += 1
                else:
                    results['servers']['windows_unknown'] += 1
                
                can_use_byol = (license_date == 'pre_2019' or 
                               (license_date in ['post_2019', 'unknown'] and sa_status in ['all_active', 'mixed']))
                
                costs = self.calculate_server_costs(server, sa_status, license_date)
                results['servers']['costs']['shared_ec2_li'] += costs['shared_ec2_li']
                results['servers']['version_breakdown'][license_date]['license_included'] += costs['shared_ec2_li']
                results['servers']['version_breakdown'][license_date]['count'] += 1
                
                costs['license_date'] = license_date
                costs['can_use_byol'] = can_use_byol
                costs['server_name'] = server_name
                costs['os'] = os_version
                results['servers']['details'].append(costs)
            else:
                results['servers']['linux'] += 1
                costs = self.calculate_server_costs(server, sa_status, 'pre_2019')
                results['servers']['costs']['shared_ec2_li'] += costs['shared_ec2_li']
                costs['server_name'] = server_name
                costs['os'] = os_version
                costs['license_date'] = 'n/a'
                costs['can_use_byol'] = False
                results['servers']['details'].append(costs)
        
        # Calculate Dedicated Host costs using bin-packing for ALL Windows VMs (for comparison)
        if windows_vms_all:
            host_allocation = self.calculate_dedicated_host_packing(windows_vms_all)
            results['servers']['dedicated_host_allocation'] = host_allocation
            results['servers']['costs']['dedicated_host_byol'] = host_allocation['total_monthly_cost']
            
            # Distribute costs by version
            for vm_detail in results['servers']['details']:
                if 'windows' in str(vm_detail.get('os', '')).lower():
                    ld = vm_detail.get('license_date', 'unknown')
                    if ld in results['servers']['version_breakdown']:
                        results['servers']['version_breakdown'][ld]['dedicated_host'] += host_allocation['cost_per_vm']
        
        # Collect SQL/Oracle databases for bin-packing (ALL, not just BYOL-eligible)
        sql_oracle_dbs_all = []
        
        # Process databases
        for _, db_row in databases_df.iterrows():
            db_version = str(db_row.get('version', '') or '')
            db_name = str(db_row.get('name', '') or db_row.get('database name', '') or db_row.get('instance', '') or '')
            database = {
                'type': str(db_row.get('type', 'SQL Server') or 'SQL Server'),
                'edition': str(db_row.get('edition', 'Standard') or 'Standard'),
                'vcpu': int(db_row.get('vcpu', 8) or 8) if not pd.isna(db_row.get('vcpu', 8)) else 8,
                'memory': int(db_row.get('memory', 32) or 32) if not pd.isna(db_row.get('memory', 32)) else 32,
                'version': db_version
            }
            
            if 'sql' in str(database['type']).lower():
                results['databases']['sql_server'] += 1
                sql_oracle_dbs_all.append(database)
                
                # Detect SQL Server version
                license_date = self.detect_license_date(db_version, 'sql')
                
                if license_date == 'pre_2019':
                    results['databases']['sql_pre_2019'] += 1
                elif license_date == 'post_2019':
                    results['databases']['sql_post_2019'] += 1
                else:
                    results['databases']['sql_unknown'] += 1
                
                can_use_byol = (license_date == 'pre_2019' or 
                               (license_date in ['post_2019', 'unknown'] and sa_status in ['all_active', 'mixed']))
                
                costs = self.calculate_database_costs(database, sa_status, license_date)
                results['databases']['costs']['rds_li'] += costs['rds_li']
                results['databases']['version_breakdown'][license_date]['rds_li'] += costs['rds_li']
                results['databases']['version_breakdown'][license_date]['count'] += 1
                
                costs['license_date'] = license_date
                costs['can_use_byol'] = can_use_byol
                costs['db_name'] = db_name
                costs['db_type'] = database['type']
                costs['edition'] = database['edition']
                costs['version'] = db_version
                results['databases']['details'].append(costs)
                
            elif 'oracle' in str(database['type']).lower():
                results['databases']['oracle'] += 1
                sql_oracle_dbs_all.append(database)
                costs = self.calculate_database_costs(database, sa_status, 'pre_2019')
                results['databases']['costs']['rds_li'] += costs['rds_li']
                costs['db_name'] = db_name
                costs['db_type'] = database['type']
                costs['edition'] = database['edition']
                costs['version'] = db_version
                costs['license_date'] = 'n/a'
                costs['can_use_byol'] = False
                results['databases']['details'].append(costs)
        
        # Calculate Dedicated Host costs using bin-packing for ALL SQL/Oracle databases (for comparison)
        if sql_oracle_dbs_all:
            db_host_allocation = self.calculate_dedicated_host_packing(sql_oracle_dbs_all)
            results['databases']['dedicated_host_allocation'] = db_host_allocation
            results['databases']['costs']['dedicated_host_byol'] = db_host_allocation['total_monthly_cost']
            
            # Distribute costs by version
            for db_detail in results['databases']['details']:
                ld = db_detail.get('license_date', 'unknown')
                if ld in results['databases']['version_breakdown']:
                    results['databases']['version_breakdown'][ld]['dedicated_host'] += db_host_allocation['cost_per_vm']
        
        # Calculate totals
        total_dedicated_host = (results['servers']['costs']['dedicated_host_byol'] + 
                               results['databases']['costs']['dedicated_host_byol'])
        total_li = (results['servers']['costs']['shared_ec2_li'] + 
                   results['databases']['costs']['rds_li'])
        
        results['summary'] = {
            'dedicated_host_byol_monthly': total_dedicated_host,
            'dedicated_host_byol_annual': total_dedicated_host * 12,
            'license_included_monthly': total_li,
            'license_included_annual': total_li * 12,
            'potential_savings_monthly': total_li - total_dedicated_host if total_dedicated_host > 0 else 0,
            'potential_savings_annual': (total_li - total_dedicated_host) * 12 if total_dedicated_host > 0 else 0,
            'savings_percentage': ((total_li - total_dedicated_host) / total_li * 100) if total_li > 0 and total_dedicated_host > 0 else 0
        }
        
        # Generate recommendations with bin-packing insights
        if total_dedicated_host > 0 and total_dedicated_host < total_li:
            server_alloc = results['servers']['dedicated_host_allocation']
            db_alloc = results['databases']['dedicated_host_allocation']
            
            recommendation_text = f'BYOL on Dedicated Hosts can save ${results["summary"]["potential_savings_annual"]:,.0f}/year ({results["summary"]["savings_percentage"]:.1f}%)'
            
            if server_alloc:
                recommendation_text += f'\n• Servers: {results["servers"]["windows"]} Windows VMs on {server_alloc["hosts_needed"]} {server_alloc["host_type"]} hosts ({server_alloc["utilization"]["average"]:.1f}% avg utilization)'
            
            if db_alloc:
                recommendation_text += f'\n• Databases: {results["databases"]["sql_server"] + results["databases"]["oracle"]} DBs on {db_alloc["hosts_needed"]} {db_alloc["host_type"]} hosts ({db_alloc["utilization"]["average"]:.1f}% avg utilization)'
            
            results['recommendations'].append({
                'priority': 'high',
                'recommendation': recommendation_text,
                'action': 'Verify license agreements and SA status to proceed with BYOL strategy'
            })
        elif total_dedicated_host == 0:
            if results['servers']['windows_post_2019'] > 0 or results['databases']['sql_post_2019'] > 0:
                results['recommendations'].append({
                    'priority': 'high',
                    'recommendation': f'Post-Oct 2019 licenses detected ({results["servers"]["windows_post_2019"]} Windows, {results["databases"]["sql_post_2019"]} SQL) - BYOL requires active SA',
                    'action': 'Verify Software Assurance status or consider License Included options'
                })
            else:
                results['recommendations'].append({
                    'priority': 'medium',
                    'recommendation': 'BYOL not available with current licensing status',
                    'action': 'Consider License Included options or verify SA status for potential savings'
                })
        
        if results['databases']['total'] > 0:
            results['recommendations'].append({
                'priority': 'medium',
                'recommendation': 'Consider RDS for managed database services',
                'action': 'Evaluate operational savings vs. license costs for RDS License Included'
            })
        
        # Add version-specific recommendations
        if results['servers']['windows_pre_2019'] > 0:
            results['recommendations'].append({
                'priority': 'medium',
                'recommendation': f'{results["servers"]["windows_pre_2019"]} Windows servers with pre-Oct 2019 licenses can use BYOL without SA',
                'action': 'Consider Dedicated Hosts for these servers to maximize license value'
            })
        
        if results['databases']['sql_pre_2019'] > 0:
            results['recommendations'].append({
                'priority': 'medium',
                'recommendation': f'{results["databases"]["sql_pre_2019"]} SQL Server databases with pre-Oct 2019 licenses can use BYOL without SA',
                'action': 'Evaluate Dedicated Hosts vs RDS based on operational requirements'
            })
        
        return results
