import os
import pandas as pd
from datetime import datetime
import json
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from config import input_folder_dir_path, model_id_claude3_7,model_temperature


# Create a BedrockModel
bedrock_model = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=model_temperature
)


def datetime_handler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def excel_to_json(filename, create_file=False, max_rows_per_sheet=3000):
    """
    Convert Excel to JSON with row limits to prevent context overflow.
    Limits each sheet to max_rows_per_sheet to stay within model context limits.
    """
    try:
        from project_context import get_input_file_path
        
        # Get input folder path from config.py and join with filename directory and construct full path
        # Extract just the filename if path is included
        filename_only = os.path.basename(filename)
        full_path = get_input_file_path(filename_only)
        
        # Read Excel file
        excel_file = pd.read_excel(full_path, sheet_name=None, engine='openpyxl')
        
        # Convert to JSON-compatible dictionary
        json_data = {}
        for sheet_name, dataframe in excel_file.items():
            # Limit rows to prevent context overflow
            original_rows = len(dataframe)
            if original_rows > max_rows_per_sheet:
                print(f"WARNING: Sheet '{sheet_name}' has {original_rows} rows. Limited to {max_rows_per_sheet} rows to prevent context overflow.")
                dataframe = dataframe.head(max_rows_per_sheet)
            
            # Convert datetime columns to string format
            for column in dataframe.select_dtypes(include=['datetime64']).columns:
                dataframe[column] = dataframe[column].dt.strftime('%Y-%m-%d %H:%M:%S')
            # Handle NaN values and convert to records
            json_data[sheet_name] = dataframe.fillna('').to_dict(orient='records')
        
        # Create JSON filename
        if create_file == True:
            json_filename = os.path.splitext(filename)[0] + '.json'
            json_full_path = os.path.join(input_folder_dir_path, json_filename)
        
            # Save JSON data to file with custom serialization
            with open(json_full_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, 
                        default=datetime_handler,
                        indent=4, 
                        ensure_ascii=False)
        return json_data
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None, None



@tool(name="it_analysis", description="Read CSV file from the target folder")
def it_analysis(filename):
    json_data = excel_to_json(filename)
    return json_data

# system_message = """
#     Use tool inventory_analysis to perform inventory analysis
#     As an AWS migration expert, conduct a comprehensive analysis of the provided IT inventory with emphasis on cost optimisation, performance metrics, disaster recovery capabilities, and strategic planning.

#     Asset Distribution
#     -Total asset count
#     -Asset categories breakdown

#     Technical Environment Analysis
#         1 Infrastructure Layer
#         - Server infrastructure
#         - Storage systems
#         - Network components
#         - Security infrastructure
#     2 Application Landscape
#         - Application inventory
#         - Technology stacks
#         - Version distribution
#         - Support status
#     3 Database Systems
#         - Database types and versions
#         - Data volumes
#         - Growth patterns
#         - Backup strategies
#     4 Operating Systems
#         - OS distribution
#         - Version analysis
#         - Support status
#         - Patch levels
#     Dependency Analysis
#     1 Application Dependencies
#         - Application-to-application mapping
#         - Integration points
#         - API relationships
#         - Service dependencies
#     2 Data Dependencies
#         - Data flow mapping
#         - Master data relationships
#         - Shared data repositories
#         - Data synchronisation requirements
#     3 Infrastructure Dependencies
#         - Hardware dependencies
#         - Network dependencies
#         - Storage dependencies
#         - Security dependencies
#     4 Critical Path Analysis
#         - Single points of failure
#         - Dependency chains
#         - Impact assessment
#         - Risk evaluation
        
#         **REMINDER: Base all analysis strictly on the provided inventory data. Do not introduce external cost estimates, market pricing, or assumed financial figures. For DR analysis, only report on disaster recovery information that is explicitly documented in the inventory.**
        
#         Format your response in markdown with clear headings, bullet points, and tables where appropriate. 
#     """
# agent = Agent(model=bedrock_model,system_prompt= system_message,tools=[it_analysis])

# question = "Conduct a comprehensive analysis of the provided IT inventory for the provided file input/it-infrastructure-inventory.xlsx"

# result = agent(question)
# print(result.message)



# filename = 'input/it-infrastructure-inventory.xlsx'
# json_data = excel_to_json(filename) 
# print(json_data)
   


def _format_instance_summary(summary_list):
    """Helper to format instance summary as text"""
    if not summary_list:
        return "  None"
    lines = []
    for item in summary_list:
        if 'instance_type' in item:
            lines.append(f"  - {item['instance_type']}: {item['count']} instances, ${item['monthly_cost']:,.2f}/month")
    return '\n'.join(lines) if lines else "  None"


@tool(
    name="calculate_it_inventory_arr",
    description="Calculate AWS ARR from IT Infrastructure Inventory file. Analyzes Servers tab (maps to EC2) and Databases tab (maps to RDS). Returns detailed cost breakdown and generates Excel output file."
)
def calculate_it_inventory_arr(inventory_filename: str, target_region: str = 'us-east-1'):
    """
    Calculate AWS ARR from IT Infrastructure Inventory
    
    Analyzes:
    - Servers tab: Maps to EC2 instances based on vCPU, RAM, and OS
    - Databases tab: Maps to RDS instances based on engine, size, and CPU cores
    
    Args:
        inventory_filename: IT inventory Excel file (e.g., 'it-infrastructure-inventory.xlsx')
        target_region: AWS region for pricing (default: us-east-1)
    
    Returns:
        JSON string with:
        - EC2 costs (compute for servers)
        - RDS costs (databases)
        - Total monthly and annual costs
        - Detailed breakdowns by instance type
        - Excel file path with full details
    """
    from project_context import get_input_file_path
    from it_inventory_pricing import calculate_it_inventory_arr as calc_arr
    from it_inventory_pricing import export_it_inventory_to_excel
    from config import output_folder_dir_path
    
    try:
        # Get full path to inventory file
        filename_only = os.path.basename(inventory_filename)
        full_path = get_input_file_path(filename_only)
        
        if not os.path.exists(full_path):
            return json.dumps({
                'error': f'IT inventory file not found: {full_path}',
                'searched_path': full_path
            })
        
        # Calculate ARR with BOTH pricing models
        # We need to calculate 4 combinations efficiently:
        # - EC2 Instance SP (Option 1) + RDS 3yr Partial (Option 1)
        # - Compute SP (Option 2) + RDS 1yr No Upfront (Option 2)
        
        # Read the inventory once
        import pandas as pd
        df_servers = pd.read_excel(full_path, sheet_name='Servers')
        df_databases = pd.read_excel(full_path, sheet_name='Databases')
        
        from it_inventory_pricing import calculate_ec2_costs, calculate_rds_costs
        
        # Option 1: EC2 Instance SP + RDS 3yr Partial Upfront
        ec2_option1 = calculate_ec2_costs(df_servers, target_region, '3yr_ec2_sp')
        rds_option1 = calculate_rds_costs(df_databases, target_region, '3yr_ec2_sp')  # Will map to 3yr_partial_upfront
        
        results_option1 = {
            'ec2': ec2_option1,
            'rds': rds_option1,
            'total_monthly': ec2_option1['total_monthly'] + rds_option1['total_monthly'],
            'total_annual': (ec2_option1['total_monthly'] + rds_option1['total_monthly']) * 12,
            'region': target_region,
            'pricing_model': '3yr_ec2_sp',
            'summary': {
                'total_servers': len(df_servers),
                'total_databases': len(df_databases),
                'ec2_monthly': ec2_option1['total_monthly'],
                'rds_monthly': rds_option1['total_monthly'],
                'total_monthly': ec2_option1['total_monthly'] + rds_option1['total_monthly'],
                'total_annual': (ec2_option1['total_monthly'] + rds_option1['total_monthly']) * 12
            }
        }
        
        # Option 2: Compute SP + RDS 1yr No Upfront
        ec2_option2 = calculate_ec2_costs(df_servers, target_region, '3yr_compute_sp')
        rds_option2 = calculate_rds_costs(df_databases, target_region, '1yr_no_upfront')
        
        results_option2 = {
            'ec2': ec2_option2,
            'rds': rds_option2,
            'total_monthly': ec2_option2['total_monthly'] + rds_option2['total_monthly'],
            'total_annual': (ec2_option2['total_monthly'] + rds_option2['total_monthly']) * 12,
            'region': target_region,
            'pricing_model': '3yr_compute_sp + 1yr_no_upfront',
            'summary': {
                'total_servers': len(df_servers),
                'total_databases': len(df_databases),
                'ec2_monthly': ec2_option2['total_monthly'],
                'rds_monthly': rds_option2['total_monthly'],
                'total_monthly': ec2_option2['total_monthly'] + rds_option2['total_monthly'],
                'total_annual': (ec2_option2['total_monthly'] + rds_option2['total_monthly']) * 12
            }
        }
        
        # Calculate savings between the two options (Option 1 is cheaper)
        ec2_monthly_savings = results_option2['summary']['ec2_monthly'] - results_option1['summary']['ec2_monthly']
        rds_monthly_savings = results_option2['summary']['rds_monthly'] - results_option1['summary']['rds_monthly']
        monthly_savings = results_option2['summary']['total_monthly'] - results_option1['summary']['total_monthly']
        annual_savings = monthly_savings * 12
        three_year_savings = monthly_savings * 36
        savings_pct = (monthly_savings / results_option2['summary']['total_monthly'] * 100) if results_option2['summary']['total_monthly'] > 0 else 0
        
        # Export BOTH pricing options to ONE Excel file with multiple tabs
        from it_inventory_pricing import export_it_inventory_complete
        output_filename = f"it_inventory_aws_pricing_{target_region}.xlsx"
        output_path = os.path.join(output_folder_dir_path, output_filename)
        export_it_inventory_complete(results_option1, results_option2, output_path)
        
        # Log the results for debugging
        import logging
        logger = logging.getLogger('AgentWorkflow')
        logger.info("=" * 80)
        logger.info("IT INVENTORY PRICING TOOL OUTPUT")
        logger.info("=" * 80)
        logger.info(f"Option 1 (EC2 Instance SP + RDS 3yr Partial) Monthly: ${results_option1['summary']['total_monthly']:,.2f}")
        logger.info(f"Option 2 (Compute SP + RDS 1yr No Upfront) Monthly: ${results_option2['summary']['total_monthly']:,.2f}")
        logger.info(f"Monthly Savings (Option 1 vs Option 2): ${monthly_savings:,.2f} ({savings_pct:.2f}%)")
        logger.info(f"  - EC2 Savings: ${ec2_monthly_savings:,.2f}")
        logger.info(f"  - RDS Savings: ${rds_monthly_savings:,.2f}")
        logger.info("=" * 80)
        
        # Get upfront fees for both options
        rds_upfront_option1 = results_option1['rds'].get('total_upfront_fees', 0.0)
        rds_upfront_option2 = results_option2['rds'].get('total_upfront_fees', 0.0)
        
        # Return SIMPLIFIED formatted text (easier for LLM to parse)
        summary_text = f"""
IT INVENTORY AWS PRICING ANALYSIS
Region: {target_region}
Total Servers: {results_option1['summary']['total_servers']}
Total Databases: {results_option1['summary']['total_databases']}

================================================================================
OPTION 1: EC2 Instance SP (3yr) + RDS Partial Upfront (3yr) - RECOMMENDED
================================================================================
EC2 Monthly Cost: ${results_option1['summary']['ec2_monthly']:,.2f}
RDS Monthly Cost: ${results_option1['summary']['rds_monthly']:,.2f}
Total Monthly Cost: ${results_option1['summary']['total_monthly']:,.2f}
Total Annual Cost (ARR): ${results_option1['summary']['total_annual']:,.2f}
3-Year Total Cost: ${results_option1['summary']['total_monthly'] * 36:,.2f}
RDS Upfront Fees (One-time): ${rds_upfront_option1:,.2f}

================================================================================
OPTION 2: Compute SP (3yr) + RDS No Upfront (1yr × 3)
================================================================================
EC2 Monthly Cost: ${results_option2['summary']['ec2_monthly']:,.2f}
RDS Monthly Cost: ${results_option2['summary']['rds_monthly']:,.2f}
Total Monthly Cost: ${results_option2['summary']['total_monthly']:,.2f}
Total Annual Cost (ARR): ${results_option2['summary']['total_annual']:,.2f}
3-Year Total Cost: ${results_option2['summary']['total_monthly'] * 36:,.2f}
RDS Upfront Fees (One-time): ${rds_upfront_option2:,.2f}

================================================================================
SAVINGS: Option 1 vs Option 2
================================================================================
EC2 Monthly Savings: ${ec2_monthly_savings:,.2f}
RDS Monthly Savings: ${rds_monthly_savings:,.2f}
Total Monthly Savings: ${monthly_savings:,.2f}
Annual Savings: ${annual_savings:,.2f}
3-Year Savings: ${three_year_savings:,.2f}
Savings Percentage: {savings_pct:.2f}%

RECOMMENDATION: Option 1 saves ${monthly_savings:,.2f} per month ({savings_pct:.1f}%) compared to Option 2.
  - EC2 savings: ${ec2_monthly_savings:,.2f}/month (EC2 Instance SP vs Compute SP)
  - RDS savings: ${rds_monthly_savings:,.2f}/month (3yr Partial Upfront vs 1yr No Upfront)

NOTE: 
- Option 1 RDS uses 3-Year Partial Upfront (requires ${rds_upfront_option1:,.2f} upfront payment)
- Option 2 RDS uses 1-Year No Upfront (renewed 3 times, no upfront payment)

Excel Output File: {output_path}
Tabs: Pricing_Comparison, EC2_Option1_Instance_SP, EC2_Option2_Compute_SP, RDS_Option1_3yr_Partial, RDS_Option2_1yr_NoUpfront, RDS_Comparison, EC2_Comparison, EC2_Summary, RDS_Summary

EC2 Instance Summary (Option 1 - EC2 Instance SP):
{_format_instance_summary(results_option1['ec2']['instance_summary'])}

RDS Instance Summary (Option 1 - 3yr Partial Upfront):
{_format_instance_summary(results_option1['rds']['instance_summary'])}
"""
        
        return summary_text
        
    except Exception as e:
        import traceback
        return json.dumps({
            'error': str(e),
            'traceback': traceback.format_exc()
        })


def _format_instance_summary(summary_list):
    """Helper to format instance summary as text"""
    if not summary_list:
        return "  None"
    lines = []
    for item in summary_list:
        if 'instance_type' in item:
            lines.append(f"  - {item['instance_type']}: {item['count']} instances, ${item['monthly_cost']:,.2f}/month")
    return '\n'.join(lines) if lines else "  None"


@tool(
    name="extract_atx_arr_tool",
    description="Extract AWS ARR from ATX (AWS Transform for VMware) Excel file. ATX pre-calculates costs, this tool extracts them. Returns ARR breakdown with VM counts and OS distribution."
)
def extract_atx_arr_tool(atx_filename: str, target_region: str = 'us-east-1'):
    """
    Extract AWS ARR from ATX Excel file
    
    ATX (AWS Transform for VMware) already calculates AWS costs.
    This tool extracts the pre-calculated values.
    
    Args:
        atx_filename: ATX analysis Excel file (e.g., 'atx_analysis.xlsx')
        target_region: AWS region for reference (default: us-east-1)
    
    Returns:
        JSON string with:
        - Total VMs and ARR
        - OS distribution (Windows/Linux)
        - Cost breakdown (compute, licensing)
        - Pricing model (1-Year NURI)
    """
    from project_context import get_input_file_path
    from atx_pricing_extractor import extract_atx_arr
    
    try:
        # Get full path to ATX file
        filename_only = os.path.basename(atx_filename)
        full_path = get_input_file_path(filename_only)
        
        if not os.path.exists(full_path):
            return json.dumps({
                'error': f'ATX file not found: {full_path}',
                'searched_path': full_path
            })
        
        # Extract ARR
        atx_data = extract_atx_arr(full_path, region=target_region)
        
        if not atx_data.get('success'):
            return json.dumps({
                'error': atx_data.get('error', 'Unknown error'),
                'traceback': atx_data.get('traceback', '')
            })
        
        # Prepare summary for return
        summary = {
            'success': True,
            'source': atx_data['source'],
            'region': target_region,
            'pricing_model': atx_data['pricing_model'],
            'total_vms': atx_data['vm_count'],
            'total_monthly_cost': atx_data['total_monthly'],
            'total_annual_cost': atx_data['total_arr'],
            'os_distribution': atx_data.get('os_distribution', {}),
            'cost_breakdown': atx_data.get('cost_breakdown', {}),
            'note': 'ATX pre-calculates costs using AWS pricing. Values extracted from ATX analysis.'
        }
        
        return json.dumps(summary, indent=2)
        
    except Exception as e:
        import traceback
        return json.dumps({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
