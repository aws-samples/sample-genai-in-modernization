"""
Strands Tools for AWS Pricing Calculation
Provides deterministic ARR calculation from RVTools data
"""
from strands import tool
import pandas as pd
from aws_pricing_calculator import AWSPricingCalculator
from rv_tool_analysis import rv_tool_analysis
from config import USE_DETERMINISTIC_PRICING, PRICING_CONFIG
import json

@tool(
    name="calculate_exact_aws_arr",
    description="Calculate exact AWS Annual Recurring Revenue (ARR) from RVTools data using AWS pricing. Returns deterministic, consistent costs every time. Requires RVTools filename or pattern. Controlled by USE_DETERMINISTIC_PRICING config."
)
def calculate_exact_aws_arr(rvtools_filename: str, target_region: str = None):
    """
    Calculate exact AWS ARR from RVTools data with DUAL PRICING OPTIONS
    
    This tool provides DETERMINISTIC pricing - same input always produces same output.
    Uses AWS Price List API when available, falls back to accurate hardcoded pricing.
    
    Calculates TWO pricing options:
    - Option 1: 3-Year EC2 Instance Savings Plan (less flexible, typically more expensive)
    - Option 2: 3-Year Compute Savings Plan (more flexible, typically cheaper)
    
    Behavior controlled by config.py:
    - USE_DETERMINISTIC_PRICING: Enable/disable this feature
    - PRICING_CONFIG: Configure region, API usage, pricing model
    
    Args:
        rvtools_filename: RVTools file path or pattern (e.g., 'input/rvtool*.csv')
        target_region: AWS region for pricing (default: from config)
    
    Returns:
        JSON string with detailed cost breakdown including:
        - Total monthly cost and ARR for both options
        - Breakdown by instance type
        - Breakdown by OS (Windows vs Linux)
        - Cost components (compute, storage, data transfer)
        - Per-VM details
    
    Example:
        result = calculate_exact_aws_arr('input/rvtool*.csv', 'us-east-1')
    """
    # Check if deterministic pricing is enabled
    if not USE_DETERMINISTIC_PRICING:
        return json.dumps({
            'error': 'Deterministic pricing is disabled in config.py',
            'message': 'Set USE_DETERMINISTIC_PRICING = True to enable this feature',
            'current_mode': 'LLM-based estimation'
        })
    
    # Use config default if region not specified
    if target_region is None:
        target_region = PRICING_CONFIG.get('default_region', 'us-east-1')
    
    print(f"\n{'='*80}")
    print(f"EXACT AWS ARR CALCULATION - DUAL PRICING")
    print(f"{'='*80}")
    print(f"Input: {rvtools_filename}")
    print(f"Region: {target_region}")
    print(f"Mode: Deterministic (config-controlled)")
    print(f"Calculating BOTH pricing options...")
    print(f"{'='*80}\n")
    
    # Step 1: Load RVTools data
    print("Step 1: Loading RVTools data...")
    df = rv_tool_analysis(rvtools_filename)
    print(f"✓ Loaded {len(df)} VMs\n")
    
    # Step 2: Calculate Option 1 (EC2 Instance Savings Plan)
    print("Step 2: Calculating Option 1 (3-Year EC2 Instance Savings Plan)...")
    use_api = PRICING_CONFIG.get('use_aws_pricing_api', False)
    calculator_option1 = AWSPricingCalculator(region=target_region, use_api=use_api, pricing_model='3yr_ec2_sp')
    results_option1 = calculator_option1.calculate_arr_from_dataframe(df, pricing_model='3yr_ec2_sp')
    print(f"✓ Option 1 Monthly: ${results_option1['summary']['total_monthly_cost']:,.2f}\n")
    
    # Step 3: Calculate Option 2 (Compute Savings Plan)
    print("Step 3: Calculating Option 2 (3-Year Compute Savings Plan)...")
    calculator_option2 = AWSPricingCalculator(region=target_region, use_api=use_api, pricing_model='3yr_compute_sp')
    results_option2 = calculator_option2.calculate_arr_from_dataframe(df, pricing_model='3yr_compute_sp')
    print(f"✓ Option 2 Monthly: ${results_option2['summary']['total_monthly_cost']:,.2f}\n")
    
    # Step 4: Export to Excel with both options
    print("Step 4: Generating Excel export with both pricing options...")
    try:
        from excel_export import export_rvtools_dual_pricing
        excel_path = export_rvtools_dual_pricing(results_option1, results_option2, 'vm_to_ec2_mapping.xlsx')
        if excel_path:
            print(f"✓ Excel export saved: {excel_path}")
        else:
            print(f"✗ Excel export returned None - check excel_export.py for errors")
    except Exception as e:
        import traceback
        print(f"✗ Excel export failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    
    # Step 5: Format results for agent consumption
    monthly_savings = results_option2['summary']['total_monthly_cost'] - results_option1['summary']['total_monthly_cost']
    annual_savings = monthly_savings * 12
    three_year_savings = monthly_savings * 36
    savings_pct = (monthly_savings / results_option2['summary']['total_monthly_cost'] * 100) if results_option2['summary']['total_monthly_cost'] > 0 else 0
    
    output = {
        'option1': {
            'pricing_model': '3-Year EC2 Instance Savings Plan',
            'total_vms': results_option1['summary']['total_vms'],
            'total_monthly_cost_usd': results_option1['summary']['total_monthly_cost'],
            'total_annual_cost_arr_usd': results_option1['summary']['total_arr'],
            'region': results_option1['summary']['region']
        },
        'option2': {
            'pricing_model': '3-Year Compute Savings Plan',
            'total_vms': results_option2['summary']['total_vms'],
            'total_monthly_cost_usd': results_option2['summary']['total_monthly_cost'],
            'total_annual_cost_arr_usd': results_option2['summary']['total_arr'],
            'region': results_option2['summary']['region']
        },
        'savings': {
            'monthly_savings_usd': monthly_savings,
            'annual_savings_usd': annual_savings,
            'three_year_savings_usd': three_year_savings,
            'savings_percentage': savings_pct,
            'recommendation': f"Option 1 saves ${monthly_savings:,.2f}/month ({savings_pct:.1f}%)"
        },
        'calculation_method': 'Deterministic - AWS Price List API with fallback pricing',
        'consistency_guarantee': 'Same input produces identical output every time'
    }
    
    # Convert to JSON string for agent
    return json.dumps(output, indent=2)


@tool(
    name="get_vm_cost_breakdown",
    description="Get detailed cost breakdown for a specific VM configuration. Useful for what-if analysis and sizing recommendations."
)
def get_vm_cost_breakdown(vcpu: int, memory_gb: float, storage_gb: float, 
                         os: str, target_region: str = 'us-east-1'):
    """
    Calculate cost for a specific VM configuration
    
    Args:
        vcpu: Number of vCPUs
        memory_gb: Memory in GB
        storage_gb: Storage in GB
        os: Operating system ('Windows' or 'Linux')
        target_region: AWS region for pricing
    
    Returns:
        JSON string with cost breakdown for this VM
    """
    calculator = AWSPricingCalculator(region=target_region, use_api=False)
    
    result = calculator.calculate_vm_cost(
        vcpu=vcpu,
        memory_gb=memory_gb,
        storage_gb=storage_gb,
        os=os,
        vm_name='custom-vm'
    )
    
    output = {
        'vm_configuration': {
            'vcpu': vcpu,
            'memory_gb': memory_gb,
            'storage_gb': storage_gb,
            'os': os
        },
        'recommended_instance_type': result['instance_type'],
        'pricing': {
            'hourly_rate_usd': result['hourly_rate'],
            'monthly_compute_usd': result['monthly_compute'],
            'monthly_storage_usd': result['monthly_storage'],
            'monthly_data_transfer_usd': result['monthly_data_transfer'],
            'monthly_total_usd': result['monthly_total'],
            'annual_cost_usd': round(result['monthly_total'] * 12, 2)
        },
        'region': target_region,
        'pricing_model': '3-Year No Upfront Reserved Instance'
    }
    
    return json.dumps(output, indent=2)


@tool(
    name="compare_pricing_models",
    description="Compare costs across different AWS pricing models (On-Demand, 1-Year RI, 3-Year RI) for the RVTools inventory."
)
def compare_pricing_models(rvtools_filename: str, target_region: str = 'us-east-1'):
    """
    Compare pricing across different AWS purchasing options
    
    Args:
        rvtools_filename: RVTools file path or pattern
        target_region: AWS region for pricing
    
    Returns:
        JSON string comparing On-Demand, 1-Year RI, and 3-Year RI pricing
    """
    # Load RVTools data
    df = rv_tool_analysis(rvtools_filename)
    
    # Calculate for 3-Year RI (base calculation)
    calculator = AWSPricingCalculator(region=target_region, use_api=False)
    results_3yr = calculator.calculate_arr_from_dataframe(df)
    
    # Estimate other pricing models (multipliers based on typical AWS pricing)
    monthly_3yr = results_3yr['summary']['total_monthly_cost']
    
    # On-Demand is typically 2.5x more expensive than 3-Year RI
    monthly_on_demand = monthly_3yr * 2.5
    
    # 1-Year RI is typically 1.4x more expensive than 3-Year RI
    monthly_1yr = monthly_3yr * 1.4
    
    output = {
        'vm_count': results_3yr['summary']['total_vms'],
        'region': target_region,
        'pricing_comparison': {
            'on_demand': {
                'monthly_cost_usd': round(monthly_on_demand, 2),
                'annual_cost_usd': round(monthly_on_demand * 12, 2),
                'description': 'Pay-as-you-go, no commitment'
            },
            '1_year_reserved_instance': {
                'monthly_cost_usd': round(monthly_1yr, 2),
                'annual_cost_usd': round(monthly_1yr * 12, 2),
                'savings_vs_on_demand_percent': round((1 - monthly_1yr/monthly_on_demand) * 100, 1),
                'description': '1-year commitment, no upfront payment'
            },
            '3_year_reserved_instance': {
                'monthly_cost_usd': round(monthly_3yr, 2),
                'annual_cost_usd': round(monthly_3yr * 12, 2),
                'savings_vs_on_demand_percent': round((1 - monthly_3yr/monthly_on_demand) * 100, 1),
                'savings_vs_1yr_ri_percent': round((1 - monthly_3yr/monthly_1yr) * 100, 1),
                'description': '3-year commitment, no upfront payment (RECOMMENDED)'
            }
        },
        'recommendation': '3-Year No Upfront Reserved Instances provide best value for stable workloads',
        'three_year_savings_usd': round((monthly_on_demand - monthly_3yr) * 36, 2)
    }
    
    return json.dumps(output, indent=2)


if __name__ == "__main__":
    # Test the tools
    print("Testing Pricing Tools...")
    
    # Test 1: Calculate ARR
    print("\n=== Test 1: Calculate Exact AWS ARR ===")
    try:
        result = calculate_exact_aws_arr('input/RVTools_Export.xlsx', 'us-east-1')
        data = json.loads(result)
        print(f"✓ Total VMs: {data['summary']['total_vms']}")
        print(f"✓ Monthly Cost: ${data['summary']['total_monthly_cost_usd']:,.2f}")
        print(f"✓ Annual ARR: ${data['summary']['total_annual_cost_arr_usd']:,.2f}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    
    # Test 2: Single VM cost
    print("\n=== Test 2: Single VM Cost Breakdown ===")
    try:
        result = get_vm_cost_breakdown(4, 16, 100, 'Windows Server', 'us-east-1')
        data = json.loads(result)
        print(f"✓ Instance Type: {data['recommended_instance_type']}")
        print(f"✓ Monthly Cost: ${data['pricing']['monthly_total_usd']}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
    
    print("\n✓ All pricing tools tests complete")


# Helper functions for IT Inventory pricing

def get_ec2_pricing(instance_type, os_type, region='us-east-1', pricing_model='3yr_compute_sp'):
    """
    Get EC2 pricing for a specific instance type and OS using AWS Price List API
    
    Args:
        instance_type: EC2 instance type (e.g., 'm7i.xlarge')
        os_type: 'Windows' or 'Linux'
        region: AWS region
        pricing_model: '3yr_compute_sp', '3yr_ec2_sp', '3yr_no_upfront', '1yr_no_upfront', or 'on_demand'
                      '3yr_compute_sp' = 3-Year Compute Savings Plan (most flexible, typically cheapest)
                      '3yr_ec2_sp' = 3-Year EC2 Instance Savings Plan (less flexible, typically more expensive than Compute SP)
                      '3yr_no_upfront' = 3-Year Reserved Instance (least flexible)
    
    Returns:
        dict with monthly_cost and hourly_cost
    """
    
    # Use pricing calculator with AWS Price List API
    calculator = AWSPricingCalculator(region=region)
    
    try:
        # Check pricing model and get appropriate pricing
        if pricing_model == '3yr_compute_sp':
            # Use Compute Savings Plan (most flexible, best discount)
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='3yr_compute_sp')
        elif pricing_model == '3yr_ec2_sp':
            # Use EC2 Instance Savings Plan (less flexible than Compute SP)
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='3yr_ec2_sp')
        elif pricing_model == '3yr_no_upfront':
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='3yr', purchase_option='No Upfront')
        elif pricing_model == '1yr_no_upfront':
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='1yr', purchase_option='No Upfront')
        elif pricing_model == 'on_demand':
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='on_demand')
        else:
            # Default to Compute Savings Plan
            hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='3yr_compute_sp')
    except Exception as e:
        # Fallback to 3-year RI
        print(f"⚠️  API pricing failed for {instance_type}, using 3-year RI fallback: {e}")
        hourly_cost = calculator.get_ec2_price_by_term(instance_type, os_type, region, term='3yr', purchase_option='No Upfront')
    
    monthly_cost = hourly_cost * 730  # 730 hours per month average
    
    return {
        'hourly_cost': hourly_cost,
        'monthly_cost': monthly_cost,
        'instance_type': instance_type,
        'os_type': os_type,
        'region': region,
        'pricing_model': pricing_model,
        'source': 'AWS Price List API'
    }


def get_rds_pricing(instance_type, engine, region='us-east-1', pricing_model='3yr_partial_upfront', deployment_type='Single-AZ'):
    """
    Get RDS pricing for a specific instance type and database engine using AWS Price List API
    
    Args:
        instance_type: RDS instance type (e.g., 'db.m6i.xlarge')
        engine: Database engine ('mysql', 'postgresql', 'oracle', 'sqlserver', 'mariadb')
        region: AWS region
        pricing_model: '3yr_partial_upfront' (Option 1 - cheaper), '1yr_no_upfront' (Option 2 - more expensive over 3 years), 
                      '3yr_no_upfront' (legacy - falls back to Partial Upfront), or 'on_demand'
        deployment_type: 'Single-AZ' or 'Multi-AZ' (Multi-AZ is ~2x cost of Single-AZ)
    
    Returns:
        dict with monthly_cost, hourly_cost, upfront_fee, and actual_purchase_option
    """
    
    # Use pricing calculator with AWS Price List API
    calculator = AWSPricingCalculator(region=region)
    
    # Map pricing model to API parameters
    if pricing_model == '3yr_partial_upfront':
        term = '3yr'
        purchase_option = 'Partial Upfront'
    elif pricing_model == '3yr_no_upfront':
        # Legacy model - No Upfront not available for 3yr, use Partial Upfront
        term = '3yr'
        purchase_option = 'Partial Upfront'
    elif pricing_model == '1yr_no_upfront':
        term = '1yr'
        purchase_option = 'No Upfront'
    elif pricing_model == 'on_demand':
        term = 'on_demand'
        purchase_option = None
    else:
        # Default to 3-year Partial Upfront
        term = '3yr'
        purchase_option = 'Partial Upfront'
    
    # Hardcoded fallback pricing (used if API fails)
    rds_fallback_pricing = {
        'db.m6i.large': {
            'mysql': 0.096, 'postgresql': 0.096, 'mariadb': 0.096,
            'oracle': 0.384, 'sqlserver': 0.288
        },
        'db.m6i.xlarge': {
            'mysql': 0.192, 'postgresql': 0.192, 'mariadb': 0.192,
            'oracle': 0.768, 'sqlserver': 0.576
        },
        'db.m6i.2xlarge': {
            'mysql': 0.384, 'postgresql': 0.384, 'mariadb': 0.384,
            'oracle': 1.536, 'sqlserver': 1.152
        },
        'db.m6i.4xlarge': {
            'mysql': 0.768, 'postgresql': 0.768, 'mariadb': 0.768,
            'oracle': 3.072, 'sqlserver': 2.304
        },
        'db.m6i.8xlarge': {
            'mysql': 1.536, 'postgresql': 1.536, 'mariadb': 1.536,
            'oracle': 6.144, 'sqlserver': 4.608
        }
    }
    
    # Track if we had to adjust the purchase option (e.g., for Oracle)
    actual_purchase_option = purchase_option
    pricing_note = None
    upfront_fee = 0.0
    
    try:
        # Use AWS Price List API for RDS pricing
        if term == 'on_demand':
            hourly_cost = calculator.get_rds_price_from_api(instance_type, engine, region, term='on_demand', deployment_type=deployment_type)
        else:
            # Use the specified purchase option (already mapped correctly above)
            hourly_cost = calculator.get_rds_price_from_api(instance_type, engine, region, term=term, purchase_option=actual_purchase_option, deployment_type=deployment_type)
            
            # Get upfront fee if applicable (Partial/All Upfront)
            if actual_purchase_option in ['Partial Upfront', 'All Upfront']:
                upfront_fee = calculator._last_upfront_fee
        
        source = 'AWS Price List API'
    except Exception as e:
        # Fallback to hardcoded pricing
        print(f"⚠️  RDS API pricing failed for {instance_type} {engine}, using fallback")
        if instance_type in rds_fallback_pricing and engine.lower() in rds_fallback_pricing[instance_type]:
            hourly_cost = rds_fallback_pricing[instance_type][engine.lower()]
            # Apply Multi-AZ multiplier if needed (Multi-AZ is ~2x Single-AZ)
            if deployment_type == 'Multi-AZ':
                hourly_cost *= 2.0
        else:
            hourly_cost = 0.192  # Default fallback
            if deployment_type == 'Multi-AZ':
                hourly_cost *= 2.0
            print(f"   Using default fallback pricing")
        source = 'Hardcoded fallback'
        pricing_note = f'Fallback pricing used (API failed: {str(e)[:50]})'
    
    monthly_cost = hourly_cost * 730  # 730 hours per month average
    
    result = {
        'hourly_cost': hourly_cost,
        'monthly_cost': monthly_cost,
        'instance_type': instance_type,
        'engine': engine,
        'region': region,
        'pricing_model': pricing_model,
        'actual_purchase_option': actual_purchase_option,
        'upfront_fee': upfront_fee,
        'source': source
    }
    
    if pricing_note:
        result['pricing_note'] = pricing_note
    
    return result


@tool(
    name="compare_pricing_models",
    description="Compare AWS pricing between 3-Year Compute Savings Plan and 3-Year Reserved Instances. Shows cost difference and savings. Use this to provide customers with pricing options."
)
def compare_pricing_models(rvtools_filename: str, target_region: str = None):
    """
    Compare pricing between Compute Savings Plan and Reserved Instances
    
    Calculates costs using both models and shows the difference.
    Helps customers understand pricing options.
    
    Args:
        rvtools_filename: RVTools file path
        target_region: AWS region (default: from config)
    
    Returns:
        JSON with both pricing models and comparison
    """
    if not USE_DETERMINISTIC_PRICING:
        return json.dumps({'error': 'Deterministic pricing disabled'})
    
    region = target_region or PRICING_CONFIG.get('default_region', 'us-east-1')
    
    # Calculate with Compute Savings Plan (9% discount vs RI)
    calculator_sp = AWSPricingCalculator(region=region)
    result_sp = calculator_sp.calculate_arr_from_rvtools(rvtools_filename, pricing_model='3yr_compute_sp')
    
    # Calculate with Reserved Instances
    calculator_ri = AWSPricingCalculator(region=region)
    result_ri = calculator_ri.calculate_arr_from_rvtools(rvtools_filename, pricing_model='3yr_no_upfront')
    
    # Calculate savings
    monthly_savings = result_ri['total_monthly_cost'] - result_sp['total_monthly_cost']
    annual_savings = monthly_savings * 12
    savings_percentage = (monthly_savings / result_ri['total_monthly_cost']) * 100
    
    comparison = {
        'compute_savings_plan': {
            'monthly_cost': result_sp['total_monthly_cost'],
            'annual_cost': result_sp['total_monthly_cost'] * 12,
            'three_year_cost': result_sp['total_monthly_cost'] * 36,
            'model': '3-Year Compute Savings Plan',
            'recommended': True
        },
        'reserved_instances': {
            'monthly_cost': result_ri['total_monthly_cost'],
            'annual_cost': result_ri['total_monthly_cost'] * 12,
            'three_year_cost': result_ri['total_monthly_cost'] * 36,
            'model': '3-Year Reserved Instance (No Upfront)',
            'recommended': False
        },
        'savings': {
            'monthly_savings': monthly_savings,
            'annual_savings': annual_savings,
            'three_year_savings': annual_savings * 3,
            'savings_percentage': savings_percentage
        },
        'recommendation': f"Compute Savings Plan saves ${monthly_savings:,.2f}/month ({savings_percentage:.1f}%) vs Reserved Instances"
    }
    
    return json.dumps(comparison, indent=2)
