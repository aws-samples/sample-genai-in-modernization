"""
IT Infrastructure Inventory Pricing Calculator
Calculates AWS ARR for Servers (EC2) and Databases (RDS) from IT inventory file
"""

import pandas as pd
import os
from pricing_tools import get_ec2_pricing, get_rds_pricing
from os_detection import detect_os_type


def calculate_it_inventory_arr(inventory_file, region='us-east-1', pricing_model='3yr_compute_sp'):
    """
    Calculate AWS ARR from IT Infrastructure Inventory file
    
    Args:
        inventory_file: Path to IT inventory Excel file
        region: AWS region for pricing
        pricing_model: Pricing model ('3yr_compute_sp', '3yr_ec2_sp', '3yr_no_upfront', '1yr_no_upfront', 'on_demand')
    
    Returns:
        dict with EC2 costs, RDS costs, total ARR, and detailed breakdowns
    """
    
    # Read Servers and Databases tabs
    df_servers = pd.read_excel(inventory_file, sheet_name='Servers')
    df_databases = pd.read_excel(inventory_file, sheet_name='Databases')
    
    # Calculate EC2 costs for servers
    ec2_results = calculate_ec2_costs(df_servers, region, pricing_model)
    
    # Calculate RDS costs for databases
    rds_results = calculate_rds_costs(df_databases, region, pricing_model)
    
    # Combine results
    total_monthly = ec2_results['total_monthly'] + rds_results['total_monthly']
    total_annual = total_monthly * 12
    
    return {
        'ec2': ec2_results,
        'rds': rds_results,
        'total_monthly': total_monthly,
        'total_annual': total_annual,
        'region': region,
        'pricing_model': pricing_model,
        'summary': {
            'total_servers': len(df_servers),
            'total_databases': len(df_databases),
            'ec2_monthly': ec2_results['total_monthly'],
            'rds_monthly': rds_results['total_monthly'],
            'total_monthly': total_monthly,
            'total_annual': total_annual
        }
    }


def calculate_ec2_costs(df_servers, region, pricing_model):
    """
    Calculate EC2 costs for servers from IT inventory (with parallel processing)
    
    Maps servers to appropriate EC2 instance types based on vCPU and RAM
    Uses ThreadPoolExecutor for parallel AWS API calls
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def process_server(row):
        """Process a single server (for parallel execution)"""
        from config import RIGHT_SIZING_CONFIG
        
        vcpus = row['numCpus']
        ram_gb = row['totalRAM (GB)']
        os_name = row['osName']
        
        # Get storage (handle string format like "500 GB")
        storage_gb = row.get('Storage-Total Disk Size (GB)', 0)
        if pd.isna(storage_gb) or storage_gb == 0 or storage_gb == '':
            storage_gb = RIGHT_SIZING_CONFIG.get('default_provisioned_storage_gib', 500)
        else:
            # Parse storage - handle "500 GB" format
            if isinstance(storage_gb, str):
                storage_gb = storage_gb.replace('GB', '').replace('gb', '').strip()
            storage_gb = float(storage_gb)
        
        # Store original specs
        original_vcpus = vcpus
        original_ram_gb = ram_gb
        original_storage_gb = storage_gb
        
        # Apply right-sizing if enabled (no utilization data, will use ATX assumptions)
        if RIGHT_SIZING_CONFIG.get('enable_right_sizing', False):
            from aws_pricing_calculator import AWSPricingCalculator
            calculator = AWSPricingCalculator(region=region)
            vcpus, ram_gb, storage_gb = calculator.apply_right_sizing(
                vcpus, ram_gb, storage_gb,
                cpu_util=None,  # No utilization data
                memory_util=None,
                storage_used_gb=None
            )
            right_sizing_applied = True
            vcpu_reduction = round((1 - vcpus/original_vcpus) * 100, 1) if original_vcpus > 0 else 0
            memory_reduction = round((1 - ram_gb/original_ram_gb) * 100, 1) if original_ram_gb > 0 else 0
            storage_reduction = round((1 - storage_gb/original_storage_gb) * 100, 1) if original_storage_gb > 0 else 0
        else:
            right_sizing_applied = False
            vcpu_reduction = 0
            memory_reduction = 0
            storage_reduction = 0
        
        # Detect OS type
        os_type = detect_os_type(os_name)
        
        # Map to EC2 instance type (using optimized specs)
        instance_type = map_to_ec2_instance(vcpus, ram_gb)
        
        # Get pricing
        pricing = get_ec2_pricing(instance_type, os_type, region, pricing_model)
        
        monthly_cost = pricing['monthly_cost']
        
        return {
            'server_id': row['Serverid'],
            'hostname': row['HOSTNAME'],
            # Original specs
            'vcpus': original_vcpus,
            'ram_gb': original_ram_gb,
            'storage_gb': original_storage_gb,
            # Right-sizing info
            'right_sizing_applied': right_sizing_applied,
            'vcpu_reduction': vcpu_reduction,
            'memory_reduction': memory_reduction,
            'storage_reduction': storage_reduction,
            # Optimized specs
            'optimized_vcpu': vcpus,
            'optimized_memory_gb': ram_gb,
            'optimized_storage_gb': storage_gb,
            # AWS recommendation
            'os_type': os_type,
            'instance_type': instance_type,
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12
        }
    
    # Process servers in parallel (max 20 concurrent threads)
    # Use a dict to preserve input order
    results_dict = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_server, row): idx for idx, row in df_servers.iterrows()}
        
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results_dict[idx] = result
            except Exception as e:
                print(f"Error processing server at index {idx}: {e}")
    
    # Sort by index to maintain input order
    results = [results_dict[idx] for idx in sorted(results_dict.keys())]
    
    # Handle case where no results (all failed)
    if not results:
        return {
            'total_monthly': 0,
            'total_annual': 0,
            'details': [],
            'instance_summary': []
        }
    
    total_monthly = sum(r['monthly_cost'] for r in results)
    
    # Group by instance type for summary
    df_results = pd.DataFrame(results)
    instance_summary = df_results.groupby(['instance_type', 'os_type']).agg({
        'server_id': 'count',
        'monthly_cost': 'sum'
    }).reset_index()
    instance_summary.columns = ['instance_type', 'os_type', 'count', 'monthly_cost']
    
    return {
        'total_monthly': total_monthly,
        'total_annual': total_monthly * 12,
        'details': results,
        'instance_summary': instance_summary.to_dict('records')
    }


def calculate_rds_costs(df_databases, region, pricing_model):
    """
    Calculate RDS costs for databases from IT inventory (with parallel processing)
    
    Maps databases to appropriate RDS instance types based on engine and size
    Uses ThreadPoolExecutor for parallel AWS API calls
    
    Pricing models for RDS:
    - '3yr_partial_upfront': 3-Year Partial Upfront (Option 1 - cheaper over 3 years)
    - '1yr_no_upfront': 1-Year No Upfront (Option 2 - renewed 3 times, more expensive)
    - '3yr_no_upfront': Legacy - falls back to Partial Upfront (No Upfront not available for 3yr)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Map pricing model to RDS-specific model
    if pricing_model in ['3yr_ec2_sp', '3yr_compute_sp', '3yr_no_upfront']:
        # For 3-year EC2 models, use 3-year Partial Upfront for RDS (Option 1)
        rds_pricing_model = '3yr_partial_upfront'
    elif pricing_model == '1yr_no_upfront':
        # For 1-year model, use 1-year No Upfront for RDS (Option 2)
        rds_pricing_model = '1yr_no_upfront'
    else:
        # Default to 3-year Partial Upfront
        rds_pricing_model = '3yr_partial_upfront'
    
    def process_database(row):
        """Process a single database (for parallel execution)"""
        db_id = row['Database ID']
        db_name = row['DB Name']
        engine = row['Source Engine Type']
        size_gb = row['Total Size (GB)']
        cpu_cores = row.get('CPU Cores', 2)  # Default to 2 if not specified
        deployment_type = row.get('Deployment Type', 'Single-AZ')  # Default to Single-AZ if not specified
        
        # Map to RDS instance type
        instance_type = map_to_rds_instance(cpu_cores, size_gb)
        
        # Map engine to AWS RDS engine
        rds_engine = map_to_rds_engine(engine)
        
        # Get pricing with deployment type
        pricing = get_rds_pricing(instance_type, rds_engine, region, rds_pricing_model, deployment_type)
        
        # Add storage cost (Multi-AZ requires 2x storage)
        storage_multiplier = 2.0 if deployment_type == 'Multi-AZ' else 1.0
        storage_cost = size_gb * 0.115 * storage_multiplier  # gp3 storage cost per GB-month
        
        monthly_cost = pricing['monthly_cost'] + storage_cost
        
        result_item = {
            'database_id': db_id,
            'db_name': db_name,
            'source_engine': engine,
            'rds_engine': rds_engine,
            'size_gb': size_gb,
            'cpu_cores': cpu_cores,
            'deployment_type': deployment_type,
            'instance_type': instance_type,
            'compute_cost': pricing['monthly_cost'],
            'storage_cost': storage_cost,
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12,
            'actual_purchase_option': pricing.get('actual_purchase_option', 'No Upfront'),
            'upfront_fee': pricing.get('upfront_fee', 0.0),
            'pricing_model': rds_pricing_model
        }
        
        # Add pricing note if present (e.g., for Oracle)
        if 'pricing_note' in pricing:
            result_item['pricing_note'] = pricing['pricing_note']
        
        return result_item
    
    # Process databases in parallel (max 10 concurrent threads for RDS)
    # Use a dict to preserve input order
    results_dict = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_database, row): idx for idx, row in df_databases.iterrows()}
        
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results_dict[idx] = result
            except Exception as e:
                print(f"Error processing database at index {idx}: {e}")
    
    # Sort by index to maintain input order
    results = [results_dict[idx] for idx in sorted(results_dict.keys())]
    
    # Handle case where no results (all failed)
    if not results:
        return {
            'total_monthly': 0,
            'total_annual': 0,
            'total_upfront_fees': 0.0,
            'details': [],
            'instance_summary': []
        }
    
    total_monthly = sum(r['monthly_cost'] for r in results)
    
    # Group by instance type for summary
    df_results = pd.DataFrame(results)
    instance_summary = df_results.groupby(['instance_type', 'rds_engine']).agg({
        'database_id': 'count',
        'monthly_cost': 'sum'
    }).reset_index()
    instance_summary.columns = ['instance_type', 'rds_engine', 'count', 'monthly_cost']
    
    # Calculate total upfront fees
    total_upfront_fees = sum(r.get('upfront_fee', 0.0) for r in results)
    
    return {
        'total_monthly': total_monthly,
        'total_annual': total_monthly * 12,
        'total_upfront_fees': total_upfront_fees,
        'details': results,
        'instance_summary': instance_summary.to_dict('records')
    }


def map_to_ec2_instance(vcpus, ram_gb):
    """
    Map vCPU and RAM to appropriate EC2 instance type
    
    Uses similar logic to RVTools mapping
    """
    
    # Calculate RAM per vCPU ratio
    ram_per_vcpu = ram_gb / vcpus if vcpus > 0 else 0
    
    # Determine if compute, memory, or general purpose optimized
    if ram_per_vcpu > 8:
        # Memory optimized (r7i family)
        if vcpus <= 2:
            return 'r7i.large'
        elif vcpus <= 4:
            return 'r7i.xlarge'
        elif vcpus <= 8:
            return 'r7i.2xlarge'
        elif vcpus <= 16:
            return 'r7i.4xlarge'
        elif vcpus <= 32:
            return 'r7i.8xlarge'
        else:
            return 'r7i.16xlarge'
    elif ram_per_vcpu < 2:
        # Compute optimized (c7i family)
        if vcpus <= 2:
            return 'c7i.large'
        elif vcpus <= 4:
            return 'c7i.xlarge'
        elif vcpus <= 8:
            return 'c7i.2xlarge'
        elif vcpus <= 16:
            return 'c7i.4xlarge'
        else:
            return 'c7i.8xlarge'
    else:
        # General purpose (m7i family)
        if vcpus <= 2:
            return 'm7i.large'
        elif vcpus <= 4:
            return 'm7i.xlarge'
        elif vcpus <= 8:
            return 'm7i.2xlarge'
        elif vcpus <= 16:
            return 'm7i.4xlarge'
        else:
            return 'm7i.8xlarge'


def map_to_rds_instance(cpu_cores, size_gb):
    """
    Map CPU cores and database size to appropriate RDS instance type
    """
    
    # Use db.m6i family for general purpose databases
    if cpu_cores <= 2:
        return 'db.m6i.large'
    elif cpu_cores <= 4:
        return 'db.m6i.xlarge'
    elif cpu_cores <= 8:
        return 'db.m6i.2xlarge'
    elif cpu_cores <= 16:
        return 'db.m6i.4xlarge'
    else:
        return 'db.m6i.8xlarge'


def map_to_rds_engine(source_engine):
    """
    Map source database engine to AWS RDS engine
    """
    
    engine_lower = str(source_engine).lower()
    
    if 'oracle' in engine_lower:
        return 'oracle'
    elif 'sql server' in engine_lower or 'mssql' in engine_lower:
        return 'sqlserver'
    elif 'mysql' in engine_lower:
        return 'mysql'
    elif 'postgres' in engine_lower or 'postgresql' in engine_lower:
        return 'postgresql'
    elif 'mariadb' in engine_lower:
        return 'mariadb'
    else:
        # Default to PostgreSQL for unknown engines
        return 'postgresql'


def export_it_inventory_complete(results_option1, results_option2, output_file):
    """
    Export complete IT inventory pricing comparison to ONE Excel file with multiple tabs
    
    Compares:
    - Option 1: EC2 Instance Savings Plan (3yr) + RDS Partial Upfront (3yr) - Recommended (cheaper)
    - Option 2: Compute Savings Plan (3yr) + RDS No Upfront (1yr × 3) - More expensive
    
    Includes:
    - Pricing comparison (both options)
    - EC2 details with pricing parameters
    - RDS details with pricing parameters (both 3yr and 1yr options)
    - EC2 and RDS comparisons
    """
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Tab 1: Pricing Comparison Summary
        # Calculate EC2 savings
        ec2_monthly_savings = results_option2['summary']['ec2_monthly'] - results_option1['summary']['ec2_monthly']
        
        # Calculate RDS savings (Option 2 uses 1yr renewed 3 times)
        rds_monthly_savings = results_option2['summary']['rds_monthly'] - results_option1['summary']['rds_monthly']
        
        # Total savings
        monthly_savings = results_option2['summary']['total_monthly'] - results_option1['summary']['total_monthly']
        annual_savings = monthly_savings * 12
        three_year_savings = monthly_savings * 36
        savings_pct = (monthly_savings / results_option2['summary']['total_monthly'] * 100) if results_option2['summary']['total_monthly'] > 0 else 0
        
        # Get upfront fees for both options
        rds_upfront_option1 = results_option1['rds'].get('total_upfront_fees', 0.0)
        rds_upfront_option2 = results_option2['rds'].get('total_upfront_fees', 0.0)
        
        comparison_data = {
            'Metric': [
                'Total Servers',
                'Total Databases',
                '',
                'OPTION 1: EC2 Instance SP (3yr) + RDS Partial Upfront (3yr) - RECOMMENDED',
                'EC2 Monthly Cost',
                'RDS Monthly Cost',
                'Total Monthly Cost',
                'Total Annual Cost (ARR)',
                '3-Year Total Cost (monthly only)',
                'RDS Upfront Fees (One-time)',
                '3-Year Total Cost (incl. upfront)',
                '',
                'OPTION 2: Compute SP (3yr) + RDS No Upfront (1yr × 3)',
                'EC2 Monthly Cost',
                'RDS Monthly Cost',
                'Total Monthly Cost',
                'Total Annual Cost (ARR)',
                '3-Year Total Cost (monthly only)',
                'RDS Upfront Fees (One-time)',
                '3-Year Total Cost (incl. upfront)',
                '',
                'SAVINGS (Option 1 vs Option 2)',
                'EC2 Monthly Savings',
                'RDS Monthly Savings',
                'Total Monthly Savings',
                'Annual Savings',
                '3-Year Savings (monthly only)',
                '3-Year Savings (incl. upfront)',
                'Savings Percentage',
                '',
                'Region',
                'Recommendation'
            ],
            'Value': [
                results_option1['summary']['total_servers'],
                results_option1['summary']['total_databases'],
                '',
                '',
                f"${results_option1['summary']['ec2_monthly']:,.2f}",
                f"${results_option1['summary']['rds_monthly']:,.2f}",
                f"${results_option1['summary']['total_monthly']:,.2f}",
                f"${results_option1['summary']['total_annual']:,.2f}",
                f"${results_option1['summary']['total_monthly'] * 36:,.2f}",
                f"${rds_upfront_option1:,.2f}",
                f"${(results_option1['summary']['total_monthly'] * 36) + rds_upfront_option1:,.2f}",
                '',
                '',
                f"${results_option2['summary']['ec2_monthly']:,.2f}",
                f"${results_option2['summary']['rds_monthly']:,.2f}",
                f"${results_option2['summary']['total_monthly']:,.2f}",
                f"${results_option2['summary']['total_annual']:,.2f}",
                f"${results_option2['summary']['total_monthly'] * 36:,.2f}",
                f"${rds_upfront_option2:,.2f}",
                f"${(results_option2['summary']['total_monthly'] * 36) + rds_upfront_option2:,.2f}",
                '',
                '',
                f"${ec2_monthly_savings:,.2f}",
                f"${rds_monthly_savings:,.2f}",
                f"${monthly_savings:,.2f}",
                f"${annual_savings:,.2f}",
                f"${three_year_savings:,.2f}",
                f"${((results_option2['summary']['total_monthly'] * 36) + rds_upfront_option2) - ((results_option1['summary']['total_monthly'] * 36) + rds_upfront_option1):,.2f}",
                f"{savings_pct:.2f}%",
                '',
                results_option1['region'],
                f"Option 1 saves ${monthly_savings:,.2f}/month ({savings_pct:.1f}%) - EC2: ${ec2_monthly_savings:,.2f}, RDS: ${rds_monthly_savings:,.2f}"
            ]
        }
        df_comparison = pd.DataFrame(comparison_data)
        df_comparison.to_excel(writer, sheet_name='Pricing_Comparison', index=False)
        
        # Tab 2: EC2 Details (Option 1 - EC2 Instance Savings Plan) with pricing parameters
        ec2_details_option1 = []
        for detail in results_option1['ec2']['details']:
            # Get EC2 instance specs
            from aws_pricing_calculator import AWSPricingCalculator
            calculator = AWSPricingCalculator()
            instance_specs = calculator.INSTANCE_SPECS.get(detail['instance_type'], (0, 0))
            ec2_vcpu, ec2_memory = instance_specs
            
            ec2_details_option1.append({
                'Server ID': detail['server_id'],
                'Hostname': detail['hostname'],
                # Input specs
                'Input vCPUs': detail['vcpus'],
                'Input RAM (GB)': detail['ram_gb'],
                'Input Storage (GB)': detail.get('storage_gb', 'N/A'),
                'OS Type': detail['os_type'],
                # Right-sizing info (if available)
                'Right-Sizing Applied': 'Yes' if detail.get('right_sizing_applied', False) else 'No',
                'vCPU Reduction %': f"{detail.get('vcpu_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Memory Reduction %': f"{detail.get('memory_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Storage Reduction %': f"{detail.get('storage_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                # Optimized specs (after right-sizing)
                'Optimized vCPUs': detail.get('optimized_vcpu', detail['vcpus']),
                'Optimized RAM (GB)': detail.get('optimized_memory_gb', detail['ram_gb']),
                'Optimized Storage (GB)': detail.get('optimized_storage_gb', detail.get('storage_gb', 'N/A')),
                # AWS EC2 recommendation
                'Instance Type': detail['instance_type'],
                'EC2 vCPUs': ec2_vcpu,
                'EC2 Memory (GB)': ec2_memory,
                # Pricing
                'Pricing Model': '3-Year EC2 Instance Savings Plan',
                'Term': '3 Years',
                'Purchase Option': 'No Upfront',
                'Monthly Cost': f"${detail['monthly_cost']:,.2f}",
                'Annual Cost': f"${detail['annual_cost']:,.2f}"
            })
        df_ec2_option1 = pd.DataFrame(ec2_details_option1)
        df_ec2_option1.to_excel(writer, sheet_name='EC2_Option1_Instance_SP', index=False)
        
        # Tab 3: EC2 Details (Option 2 - Compute Savings Plan) with pricing parameters
        ec2_details_option2 = []
        for detail in results_option2['ec2']['details']:
            # Get EC2 instance specs
            from aws_pricing_calculator import AWSPricingCalculator
            calculator = AWSPricingCalculator()
            instance_specs = calculator.INSTANCE_SPECS.get(detail['instance_type'], (0, 0))
            ec2_vcpu, ec2_memory = instance_specs
            
            ec2_details_option2.append({
                'Server ID': detail['server_id'],
                'Hostname': detail['hostname'],
                # Input specs
                'Input vCPUs': detail['vcpus'],
                'Input RAM (GB)': detail['ram_gb'],
                'Input Storage (GB)': detail.get('storage_gb', 'N/A'),
                'OS Type': detail['os_type'],
                # Right-sizing info (if available)
                'Right-Sizing Applied': 'Yes' if detail.get('right_sizing_applied', False) else 'No',
                'vCPU Reduction %': f"{detail.get('vcpu_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Memory Reduction %': f"{detail.get('memory_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Storage Reduction %': f"{detail.get('storage_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                # Optimized specs (after right-sizing)
                'Optimized vCPUs': detail.get('optimized_vcpu', detail['vcpus']),
                'Optimized RAM (GB)': detail.get('optimized_memory_gb', detail['ram_gb']),
                'Optimized Storage (GB)': detail.get('optimized_storage_gb', detail.get('storage_gb', 'N/A')),
                # AWS EC2 recommendation
                'Instance Type': detail['instance_type'],
                'EC2 vCPUs': ec2_vcpu,
                'EC2 Memory (GB)': ec2_memory,
                # Pricing
                'Pricing Model': '3-Year Compute Savings Plan',
                'Term': '3 Years',
                'Purchase Option': 'No Upfront',
                'Monthly Cost': f"${detail['monthly_cost']:,.2f}",
                'Annual Cost': f"${detail['annual_cost']:,.2f}"
            })
        df_ec2_option2 = pd.DataFrame(ec2_details_option2)
        df_ec2_option2.to_excel(writer, sheet_name='EC2_Option2_Compute_SP', index=False)
        
        # Tab 4: RDS Details (Option 1 - 3-Year Partial Upfront) with ALL pricing parameters
        rds_details_option1 = []
        for detail in results_option1['rds']['details']:
            # Get RDS instance specs (RDS uses same specs as EC2, just with db. prefix)
            from aws_pricing_calculator import AWSPricingCalculator
            calculator = AWSPricingCalculator()
            # Remove 'db.' prefix to look up specs
            ec2_instance_type = detail['instance_type'].replace('db.', '')
            instance_specs = calculator.INSTANCE_SPECS.get(ec2_instance_type, (0, 0))
            rds_vcpu, rds_memory = instance_specs
            
            # Determine license model based on engine
            license_model = 'BYOL (Bring Your Own License)' if detail['rds_engine'] == 'oracle' else 'License Included' if detail['rds_engine'] == 'sqlserver' else 'N/A'
            
            upfront_fee = detail.get('upfront_fee', 0.0)
            
            row_data = {
                'Database ID': detail['database_id'],
                'DB Name': detail['db_name'],
                'Source Engine': detail['source_engine'],
                # Input specs
                'Input CPU Cores': detail['cpu_cores'],
                'Input Size (GB)': detail['size_gb'],
                # Right-sizing info (if available)
                'Right-Sizing Applied': 'Yes' if detail.get('right_sizing_applied', False) else 'No',
                'CPU Reduction %': f"{detail.get('cpu_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Memory Reduction %': f"{detail.get('memory_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Storage Reduction %': f"{detail.get('storage_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                # Optimized specs
                'Optimized CPU Cores': detail.get('optimized_cpu_cores', detail['cpu_cores']),
                'Optimized Size (GB)': detail.get('optimized_size_gb', detail['size_gb']),
                # AWS RDS recommendation
                'RDS Engine': detail['rds_engine'],
                'Instance Type': detail['instance_type'],
                'RDS vCPUs': rds_vcpu,
                'RDS Memory (GB)': rds_memory,
                'Deployment Option': detail.get('deployment_type', 'Single-AZ'),
                # Pricing details
                'Pricing Model': '3-Year Reserved Instance (RDS)',
                'Term': '3 Years',
                'Purchase Option': detail.get('actual_purchase_option', 'Partial Upfront'),
                'License Model': license_model,
                'Database Edition': 'Standard' if detail['rds_engine'] == 'sqlserver' else 'N/A',
                'Storage Type': 'gp3 (General Purpose SSD)',
                'Storage (GB)': detail['size_gb'],
                'Upfront Fee': f"${upfront_fee:,.2f}" if upfront_fee > 0 else "$0.00",
                'Compute Cost': f"${detail['compute_cost']:,.2f}",
                'Storage Cost': f"${detail['storage_cost']:,.2f}",
                'Monthly Cost': f"${detail['monthly_cost']:,.2f}",
                'Annual Cost': f"${detail['annual_cost']:,.2f}"
            }
            
            # Add pricing note if present
            if 'pricing_note' in detail:
                row_data['Pricing Note'] = detail['pricing_note']
            
            rds_details_option1.append(row_data)
        
        df_rds_option1 = pd.DataFrame(rds_details_option1)
        df_rds_option1.to_excel(writer, sheet_name='RDS_Option1_3yr_Partial', index=False)
        
        # Tab 5: RDS Details (Option 2 - 1-Year No Upfront) with ALL pricing parameters
        rds_details_option2 = []
        for detail in results_option2['rds']['details']:
            # Get RDS instance specs (RDS uses same specs as EC2, just with db. prefix)
            from aws_pricing_calculator import AWSPricingCalculator
            calculator = AWSPricingCalculator()
            # Remove 'db.' prefix to look up specs
            ec2_instance_type = detail['instance_type'].replace('db.', '')
            instance_specs = calculator.INSTANCE_SPECS.get(ec2_instance_type, (0, 0))
            rds_vcpu, rds_memory = instance_specs
            
            # Determine license model based on engine
            license_model = 'BYOL (Bring Your Own License)' if detail['rds_engine'] == 'oracle' else 'License Included' if detail['rds_engine'] == 'sqlserver' else 'N/A'
            
            upfront_fee = detail.get('upfront_fee', 0.0)
            
            row_data = {
                'Database ID': detail['database_id'],
                'DB Name': detail['db_name'],
                'Source Engine': detail['source_engine'],
                # Input specs
                'Input CPU Cores': detail['cpu_cores'],
                'Input Size (GB)': detail['size_gb'],
                # Right-sizing info (if available)
                'Right-Sizing Applied': 'Yes' if detail.get('right_sizing_applied', False) else 'No',
                'CPU Reduction %': f"{detail.get('cpu_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Memory Reduction %': f"{detail.get('memory_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                'Storage Reduction %': f"{detail.get('storage_reduction', 0):.1f}%" if detail.get('right_sizing_applied', False) else 'N/A',
                # Optimized specs
                'Optimized CPU Cores': detail.get('optimized_cpu_cores', detail['cpu_cores']),
                'Optimized Size (GB)': detail.get('optimized_size_gb', detail['size_gb']),
                # AWS RDS recommendation
                'RDS Engine': detail['rds_engine'],
                'Instance Type': detail['instance_type'],
                'RDS vCPUs': rds_vcpu,
                'RDS Memory (GB)': rds_memory,
                'Deployment Option': detail.get('deployment_type', 'Single-AZ'),
                # Pricing details
                'Pricing Model': '1-Year Reserved Instance (RDS)',
                'Term': '1 Year (renewed 3 times)',
                'Purchase Option': detail.get('actual_purchase_option', 'No Upfront'),
                'License Model': license_model,
                'Database Edition': 'Standard' if detail['rds_engine'] == 'sqlserver' else 'N/A',
                'Storage Type': 'gp3 (General Purpose SSD)',
                'Storage (GB)': detail['size_gb'],
                'Upfront Fee': f"${upfront_fee:,.2f}" if upfront_fee > 0 else "$0.00",
                'Compute Cost': f"${detail['compute_cost']:,.2f}",
                'Storage Cost': f"${detail['storage_cost']:,.2f}",
                'Monthly Cost': f"${detail['monthly_cost']:,.2f}",
                'Annual Cost': f"${detail['annual_cost']:,.2f}",
                '3-Year Total': f"${detail['annual_cost'] * 3:,.2f}"
            }
            
            # Add pricing note if present
            if 'pricing_note' in detail:
                row_data['Pricing Note'] = detail['pricing_note']
            
            rds_details_option2.append(row_data)
        
        df_rds_option2 = pd.DataFrame(rds_details_option2)
        df_rds_option2.to_excel(writer, sheet_name='RDS_Option2_1yr_NoUpfront', index=False)
        
        # Tab 6: RDS Comparison (3yr Partial Upfront vs 1yr No Upfront)
        rds_comparison = []
        for detail_option1 in results_option1['rds']['details']:
            detail_option2 = next((d for d in results_option2['rds']['details'] if d['database_id'] == detail_option1['database_id']), None)
            if detail_option2:
                # Calculate true 3-year total cost including upfront fees
                option1_3yr_total = (detail_option1['monthly_cost'] * 36) + detail_option1.get('upfront_fee', 0.0)
                option2_3yr_total = detail_option2['monthly_cost'] * 36  # No upfront for Option 2
                
                # True 3-year savings including upfront fees
                three_year_savings = option2_3yr_total - option1_3yr_total
                
                # Monthly savings (for reference)
                monthly_savings = detail_option2['monthly_cost'] - detail_option1['monthly_cost']
                
                rds_comparison.append({
                    'Database ID': detail_option1['database_id'],
                    'DB Name': detail_option1['db_name'],
                    'Instance Type': detail_option1['instance_type'],
                    'Engine': detail_option1['rds_engine'],
                    'Option 1 (3yr Partial) Monthly': f"${detail_option1['monthly_cost']:,.2f}",
                    'Option 1 Upfront Fee': f"${detail_option1.get('upfront_fee', 0.0):,.2f}",
                    'Option 1 3-Year Total': f"${option1_3yr_total:,.2f}",
                    'Option 2 (1yr No Upfront) Monthly': f"${detail_option2['monthly_cost']:,.2f}",
                    'Option 2 3-Year Total': f"${option2_3yr_total:,.2f}",
                    'Monthly Savings': f"${monthly_savings:,.2f}",
                    '3-Year Savings (incl. upfront)': f"${three_year_savings:,.2f}"
                })
        df_rds_comparison = pd.DataFrame(rds_comparison)
        df_rds_comparison.to_excel(writer, sheet_name='RDS_Comparison', index=False)
        
        # Tab 7: EC2 Comparison (EC2 Instance SP vs Compute SP)
        ec2_comparison = []
        for detail_option1 in results_option1['ec2']['details']:
            detail_option2 = next((d for d in results_option2['ec2']['details'] if d['server_id'] == detail_option1['server_id']), None)
            if detail_option2:
                savings = detail_option2['monthly_cost'] - detail_option1['monthly_cost']
                ec2_comparison.append({
                    'Server ID': detail_option1['server_id'],
                    'Hostname': detail_option1['hostname'],
                    'Instance Type': detail_option1['instance_type'],
                    'OS Type': detail_option1['os_type'],
                    'Option 1 (EC2 Instance SP) Monthly': f"${detail_option1['monthly_cost']:,.2f}",
                    'Option 2 (Compute SP) Monthly': f"${detail_option2['monthly_cost']:,.2f}",
                    'Monthly Savings': f"${savings:,.2f}",
                    'Annual Savings': f"${savings * 12:,.2f}"
                })
        df_ec2_comparison = pd.DataFrame(ec2_comparison)
        df_ec2_comparison.to_excel(writer, sheet_name='EC2_Comparison', index=False)
        
        # Tab 8: Summary by Instance Type (EC2 Instance SP)
        instance_summary = []
        for item in results_option1['ec2']['instance_summary']:
            instance_summary.append({
                'Instance Type': item['instance_type'],
                'OS Type': item['os_type'],
                'Count': item['count'],
                'EC2 Instance SP Monthly': f"${item['monthly_cost']:,.2f}"
            })
        df_instance_summary = pd.DataFrame(instance_summary)
        df_instance_summary.to_excel(writer, sheet_name='EC2_Summary', index=False)
        
        # Tab 9: RDS Summary by Instance Type
        rds_summary = []
        for item in results_option1['rds']['instance_summary']:
            rds_summary.append({
                'Instance Type': item['instance_type'],
                'Engine': item['rds_engine'],
                'Count': item['count'],
                'Monthly Cost': f"${item['monthly_cost']:,.2f}"
            })
        df_rds_summary = pd.DataFrame(rds_summary)
        df_rds_summary.to_excel(writer, sheet_name='RDS_Summary', index=False)
    
    return output_file


def export_it_inventory_to_excel(results, output_file):
    """
    Export IT inventory pricing results to Excel file
    
    Creates sheets for EC2, RDS, and Summary
    """
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Servers',
                'Total Databases',
                'EC2 Monthly Cost',
                'RDS Monthly Cost',
                'Total Monthly Cost',
                'Total Annual Cost (ARR)',
                'Region',
                'Pricing Model'
            ],
            'Value': [
                results['summary']['total_servers'],
                results['summary']['total_databases'],
                f"${results['summary']['ec2_monthly']:,.2f}",
                f"${results['summary']['rds_monthly']:,.2f}",
                f"${results['summary']['total_monthly']:,.2f}",
                f"${results['summary']['total_annual']:,.2f}",
                results['region'],
                results['pricing_model']
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # EC2 Details sheet
        df_ec2 = pd.DataFrame(results['ec2']['details'])
        df_ec2.to_excel(writer, sheet_name='EC2_Details', index=False)
        
        # EC2 Summary by Instance Type
        df_ec2_summary = pd.DataFrame(results['ec2']['instance_summary'])
        df_ec2_summary.to_excel(writer, sheet_name='EC2_Summary', index=False)
        
        # RDS Details sheet
        df_rds = pd.DataFrame(results['rds']['details'])
        df_rds.to_excel(writer, sheet_name='RDS_Details', index=False)
        
        # RDS Summary by Instance Type
        df_rds_summary = pd.DataFrame(results['rds']['instance_summary'])
        df_rds_summary.to_excel(writer, sheet_name='RDS_Summary', index=False)
    
    return output_file



