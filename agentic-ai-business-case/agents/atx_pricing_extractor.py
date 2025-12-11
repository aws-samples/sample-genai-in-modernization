"""
ATX (AWS Transform for VMware) Pricing Extractor
Extracts pre-calculated ARR from ATX Excel, PDF, and PowerPoint files
"""

import pandas as pd
import os


def extract_atx_arr(atx_excel_file, region='us-east-1'):
    """
    Extract ARR from ATX Excel file
    
    ATX already calculates AWS costs, so we just extract the values
    
    Args:
        atx_excel_file: Path to ATX analysis Excel file
        region: AWS region (for reference)
    
    Returns:
        dict with ARR breakdown and summary
    """
    
    results = {
        'source': 'ATX (AWS Transform for VMware)',
        'region': region,
        'pricing_model': '1-Year No Upfront Reserved Instances',
        'shared_tenancy': {},
        'mixed_tenancy': {},
        'total_arr': 0,
        'total_monthly': 0,
        'vm_count': 0
    }
    
    try:
        # Read Shared Tenancy Analysis
        df_shared = pd.read_excel(atx_excel_file, sheet_name='Shared Tenancy Analysis')
        
        # Extract key metrics from Shared Tenancy
        shared_vms = len(df_shared)
        shared_ebs_cost = df_shared['Annualized 1 Yr EBS Cost'].sum() if 'Annualized 1 Yr EBS Cost' in df_shared.columns else 0
        shared_ec2_cost = df_shared['Annualized 1 Yr NURI Total EC2 Cost'].sum() if 'Annualized 1 Yr NURI Total EC2 Cost' in df_shared.columns else 0
        shared_license_cost = df_shared['Annualized License Only Cost'].sum() if 'Annualized License Only Cost' in df_shared.columns else 0
        
        results['shared_tenancy'] = {
            'vm_count': int(shared_vms),
            'ebs_annual_cost': float(round(shared_ebs_cost, 2)),
            'ec2_annual_cost': float(round(shared_ec2_cost, 2)),
            'license_annual_cost': float(round(shared_license_cost, 2)),
            'total_annual_cost': float(round(shared_ebs_cost + shared_ec2_cost, 2))
        }
        
        # Read Mixed Tenancy Analysis
        df_mixed = pd.read_excel(atx_excel_file, sheet_name='Mixed Tenancy Analysis')
        
        # Extract key metrics from Mixed Tenancy
        # Count VMs (exclude Dedicated Host rows)
        mixed_vms = len(df_mixed[df_mixed['Tenancy Type'] == 'Shared Tenancy'])
        mixed_ec2_cost = df_mixed['Annualized 1 Yr NURI Total EC2 Cost'].sum() if 'Annualized 1 Yr NURI Total EC2 Cost' in df_mixed.columns else 0
        mixed_license_cost = df_mixed['Annualized Licensing Only Cost'].sum() if 'Annualized Licensing Only Cost' in df_mixed.columns else 0
        
        results['mixed_tenancy'] = {
            'vm_count': int(mixed_vms),
            'ec2_annual_cost': float(round(mixed_ec2_cost, 2)),
            'license_annual_cost': float(round(mixed_license_cost, 2)),
            'total_annual_cost': float(round(mixed_ec2_cost, 2))
        }
        
        # Calculate totals
        # Use Mixed Tenancy as primary source (more comprehensive)
        results['total_arr'] = float(results['mixed_tenancy']['total_annual_cost'])
        results['total_monthly'] = float(round(results['total_arr'] / 12, 2))
        results['vm_count'] = int(mixed_vms)
        
        # Add breakdown
        results['cost_breakdown'] = {
            'compute_annual': float(round(mixed_ec2_cost - mixed_license_cost, 2)),
            'licensing_annual': float(round(mixed_license_cost, 2)),
            'total_annual': float(round(mixed_ec2_cost, 2))
        }
        
        # Extract OS distribution if available
        if 'Operating System Type' in df_mixed.columns:
            os_dist = df_mixed[df_mixed['Tenancy Type'] == 'Shared Tenancy']['Operating System Type'].value_counts()
            results['os_distribution'] = {
                'Windows': int(os_dist.get('Windows', 0)),
                'Linux': int(os_dist.get('Linux', 0))
            }
        
        # Extract instance recommendations if available
        if 'Server name / Dedicated Host' in df_mixed.columns:
            # Get server names (exclude Dedicated Host rows)
            servers = df_mixed[df_mixed['Tenancy Type'] == 'Shared Tenancy']['Server name / Dedicated Host'].tolist()
            results['server_count'] = len(servers)
        
        results['success'] = True
        results['message'] = f"Successfully extracted ATX data: {results['vm_count']} VMs, ${results['total_arr']:,.2f} ARR"
        
    except Exception as e:
        results['success'] = False
        results['error'] = str(e)
        import traceback
        results['traceback'] = traceback.format_exc()
    
    return results


def format_atx_summary(atx_data):
    """
    Format ATX data into a readable summary
    
    Args:
        atx_data: Dictionary from extract_atx_arr()
    
    Returns:
        Formatted string summary
    """
    
    if not atx_data.get('success'):
        return f"ATX Extraction Failed: {atx_data.get('error', 'Unknown error')}"
    
    summary = []
    summary.append("="*60)
    summary.append("ATX (AWS TRANSFORM FOR VMWARE) COST SUMMARY")
    summary.append("="*60)
    summary.append(f"Source: {atx_data['source']}")
    summary.append(f"Region: {atx_data['region']}")
    summary.append(f"Pricing Model: {atx_data['pricing_model']}")
    summary.append(f"\nTotal VMs: {atx_data['vm_count']}")
    summary.append(f"Total Monthly Cost: ${atx_data['total_monthly']:,.2f}")
    summary.append(f"Total Annual Cost (ARR): ${atx_data['total_arr']:,.2f}")
    
    if 'os_distribution' in atx_data:
        summary.append(f"\nOS Distribution:")
        summary.append(f"  Windows VMs: {atx_data['os_distribution']['Windows']}")
        summary.append(f"  Linux VMs: {atx_data['os_distribution']['Linux']}")
    
    if 'cost_breakdown' in atx_data:
        summary.append(f"\nCost Breakdown:")
        summary.append(f"  Compute (Annual): ${atx_data['cost_breakdown']['compute_annual']:,.2f}")
        summary.append(f"  Licensing (Annual): ${atx_data['cost_breakdown']['licensing_annual']:,.2f}")
        summary.append(f"  Total (Annual): ${atx_data['cost_breakdown']['total_annual']:,.2f}")
    
    summary.append("\n" + "="*60)
    
    return "\n".join(summary)


def export_atx_summary_to_file(atx_data, output_file):
    """
    Export ATX summary to text file
    
    Args:
        atx_data: Dictionary from extract_atx_arr()
        output_file: Path to output file
    """
    
    summary = format_atx_summary(atx_data)
    
    # Security: Specify encoding explicitly to prevent encoding issues
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(summary)
        f.write("\n\n")
        f.write("="*60)
        f.write("\nDETAILED DATA\n")
        f.write("="*60)
        f.write("\n\n")
        
        # Write detailed data
        import json
        f.write(json.dumps(atx_data, indent=2))
    
    return output_file
