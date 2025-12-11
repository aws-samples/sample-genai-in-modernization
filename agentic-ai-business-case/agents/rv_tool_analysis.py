import os
import pandas as pd
import glob
from strands import Agent, tool
from strands.models import BedrockModel

from config import input_folder_dir_path, model_id_claude3_7, model_temperature, MAX_ROWS_RVTOOLS


# Create a BedrockModel
bedrock_model = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=model_temperature
)

def read_csv_from_current_dir(filename, max_rows=MAX_ROWS_RVTOOLS):
    """
    Read CSV/Excel file with row limit to prevent context overflow.
    For large datasets, only reads first max_rows to stay within context limits.
    """
    from project_context import get_input_file_path
    
    # Extract just the filename if path is included
    filename_only = os.path.basename(filename)
    full_path = get_input_file_path(filename_only)
    
    if filename.endswith('.csv'):
        df = pd.read_csv(full_path, nrows=max_rows)
    elif filename.endswith(('.xlsx', '.xls')):
        # For Excel files, try to read 'vInfo' sheet first, fallback to first sheet
        try:
            df = pd.read_excel(full_path, sheet_name='vInfo', nrows=max_rows)
        except:
            df = pd.read_excel(full_path, nrows=max_rows)
    else:
        raise ValueError(f"Unsupported file format: {filename}")
    
    # Log if data was truncated
    try:
        if filename.endswith('.csv'):
            # Security: Specify encoding explicitly to prevent encoding issues
            total_rows = sum(1 for _ in open(full_path, encoding='utf-8')) - 1  # -1 for header
        else:
            total_rows = len(pd.read_excel(full_path, usecols=[0]))
        
        if total_rows > max_rows:
            print(f"WARNING: File has {total_rows} rows. Limited to {max_rows} rows to prevent context overflow.")
            print(f"Consider filtering your data to include only active/relevant VMs.")
    except:
        pass  # If we can't determine total rows, just continue
    
    return df

def generate_vm_summary(df):
    """Generate aggregated summary statistics from VM data for cost analysis"""
    # Find storage column (can be 'Provisioned MB', 'Provisioned MiB', 'Total disk capacity MiB', etc.)
    storage_col = None
    for col in ['Provisioned MiB', 'Provisioned MB', 'Total disk capacity MiB']:
        if col in df.columns:
            storage_col = col
            break
    
    summary = {
        'total_vms': len(df),
        'total_vcpus': int(df['CPUs'].sum()) if 'CPUs' in df.columns else 0,
        'total_memory_gb': float(df['Memory'].sum() / 1024) if 'Memory' in df.columns else 0,
        'total_storage_tb': float(df[storage_col].sum() / 1024 / 1024) if storage_col else 0,
    }
    
    # Average specs per VM
    if 'CPUs' in df.columns:
        summary['avg_vcpus_per_vm'] = float(df['CPUs'].mean())
    if 'Memory' in df.columns:
        summary['avg_memory_gb_per_vm'] = float(df['Memory'].mean() / 1024)
    if storage_col:
        summary['avg_storage_gb_per_vm'] = float(df[storage_col].mean() / 1024)
    
    # VM size distribution (for EC2 instance sizing)
    if 'CPUs' in df.columns:
        summary['vm_size_distribution'] = {
            'small_1-2_vcpu': len(df[df['CPUs'] <= 2]),
            'medium_3-4_vcpu': len(df[(df['CPUs'] >= 3) & (df['CPUs'] <= 4)]),
            'large_5-8_vcpu': len(df[(df['CPUs'] >= 5) & (df['CPUs'] <= 8)]),
            'xlarge_9plus_vcpu': len(df[df['CPUs'] >= 9])
        }
    
    # OS distribution (critical for licensing)
    # RVTools has multiple possible OS column names depending on version
    os_col = None
    for col_name in ['OS according to the VMware Tools', 'OS according to the configuration file', 'OS', 'Guest OS']:
        if col_name in df.columns:
            os_col = col_name
            break
    
    if os_col:
        # Use shared OS detection logic for consistency
        from os_detection import count_os_distribution
        os_counts = count_os_distribution(df[os_col])
        summary['windows_vms'] = os_counts['windows']
        summary['linux_vms'] = os_counts['linux']
        summary['other_vms'] = os_counts['other']
    else:
        # No OS column found - cannot determine OS distribution
        summary['windows_vms'] = 0
        summary['linux_vms'] = 0
        summary['other_vms'] = len(df)
    
    return summary

def find_vinfo_file(pattern_path):
    """
    Find vInfo file from matching files (prioritize vInfo for large datasets)
    """
    matching_files = glob.glob(pattern_path)
    
    # Priority order for file selection
    priority_keywords = ['vinfo', 'vInfo', 'tabvInfo']
    
    for keyword in priority_keywords:
        for file_path in matching_files:
            if keyword in os.path.basename(file_path):
                return file_path
    
    # If no vInfo found, return first file
    return matching_files[0] if matching_files else None

@tool(name="rv_tool_analysis", description="Read RVTools CSV or Excel files from the target folder. Prioritizes vInfo tab for comprehensive VM data. For large files, only vInfo is processed to avoid timeouts. Provide filename or pattern like 'rvtool*.csv'.")
def rv_tool_analysis(filename_or_pattern):
    """
    Read RVTools files with optimization for large datasets.
    
    IMPORTANT: For large RVTools exports, only the vInfo tab is processed as it contains
    the most comprehensive VM information (VM names, CPUs, memory, storage, OS, power state, etc.)
    
    Can handle:
    - Single file: 'rvtool.csv' or 'rvtool-vInfo.xlsx'
    - Multiple files with pattern: 'rvtool*.csv' or 'rvtool*.xlsx'
    - Prioritizes vInfo tab when multiple files are available
    
    Returns DataFrame with vInfo data (most important for migration analysis).
    """
    # Check if pattern contains wildcard
    if '*' in filename_or_pattern:
        from project_context import get_case_input_directory
        
        # Find all matching files in case-specific directory
        filename_pattern = os.path.basename(filename_or_pattern)
        case_dir = get_case_input_directory()
        pattern_path = os.path.join(case_dir, filename_pattern)
        matching_files = glob.glob(pattern_path)
        
        if not matching_files:
            raise FileNotFoundError(f"No files found matching pattern: {filename_or_pattern}")
        
        print(f"Found {len(matching_files)} RVTools file(s)")
        
        # For large datasets, prioritize vInfo only
        vinfo_file = find_vinfo_file(pattern_path)
        
        if vinfo_file:
            print(f"Using vInfo file for analysis: {os.path.basename(vinfo_file)}")
            
            # Read with row limit to prevent context overflow
            max_rows = MAX_ROWS_RVTOOLS
            if vinfo_file.endswith('.csv'):
                df = pd.read_csv(vinfo_file, nrows=max_rows)
            elif vinfo_file.endswith(('.xlsx', '.xls')):
                # For Excel files, try to read 'vInfo' sheet first, fallback to first sheet
                try:
                    df = pd.read_excel(vinfo_file, sheet_name='vInfo', nrows=max_rows)
                except:
                    df = pd.read_excel(vinfo_file, nrows=max_rows)
            
            print(f"Loaded {len(df)} VMs from vInfo (max {max_rows} rows to prevent context overflow)")
            
            # Filter to powered-on VMs only (powered-off VMs not included in migration)
            if 'Powerstate' in df.columns or 'Power state' in df.columns:
                powerstate_col = 'Powerstate' if 'Powerstate' in df.columns else 'Power state'
                total_vms = len(df)
                powered_on = len(df[df[powerstate_col] == 'poweredOn'])
                powered_off = len(df[df[powerstate_col] != 'poweredOn'])
                print(f"  - Total VMs: {total_vms}")
                print(f"  - PoweredOn VMs: {powered_on}")
                print(f"  - PoweredOff VMs: {powered_off}")
                
                # Filter to powered-on only for migration analysis
                df = df[df[powerstate_col] == 'poweredOn'].copy()
                print(f"  - Filtered to {len(df)} powered-on VMs for migration cost analysis")
            
            # Warn if file is larger
            try:
                if vinfo_file.endswith('.csv'):
                    # Security: Specify encoding explicitly to prevent encoding issues
                    total_rows = sum(1 for _ in open(vinfo_file, encoding='utf-8')) - 1
                else:
                    # For Excel, try vInfo sheet first
                    try:
                        total_rows = len(pd.read_excel(vinfo_file, sheet_name='vInfo', usecols=[0]))
                    except:
                        total_rows = len(pd.read_excel(vinfo_file, usecols=[0]))
                
                if total_rows > max_rows:
                    print(f"WARNING: vInfo has {total_rows} VMs. Analyzing first {max_rows} to stay within context limits.")
                    print(f"TIP: Filter your RVTools export to include only active/production VMs.")
            except:
                pass
            
            # Add aggregated summary to reduce token usage
            summary_stats = generate_vm_summary(df)
            print(f"\n=== VM Summary Statistics for Cost Analysis ===")
            print(f"Total VMs for Migration: {summary_stats['total_vms']}")
            print(f"Total vCPUs: {summary_stats['total_vcpus']}")
            print(f"Total Memory (GB): {summary_stats['total_memory_gb']:.1f}")
            print(f"Total Storage (TB): {summary_stats['total_storage_tb']:.1f}")
            print(f"Avg vCPUs/VM: {summary_stats.get('avg_vcpus_per_vm', 0):.1f}")
            print(f"Avg Memory/VM (GB): {summary_stats.get('avg_memory_gb_per_vm', 0):.1f}")
            if 'vm_size_distribution' in summary_stats:
                print(f"VM Size Distribution:")
                for size, count in summary_stats['vm_size_distribution'].items():
                    print(f"  - {size}: {count} VMs")
            if 'windows_vms' in summary_stats:
                print(f"OS Distribution: Windows={summary_stats['windows_vms']}, Linux={summary_stats['linux_vms']}, Other={summary_stats['other_vms']}")
            
            return df
        else:
            # Fallback: read first file if no vInfo found
            print(f"No vInfo file found, using: {os.path.basename(matching_files[0])}")
            max_rows = MAX_ROWS_RVTOOLS
            if matching_files[0].endswith('.csv'):
                return pd.read_csv(matching_files[0], nrows=max_rows)
            elif matching_files[0].endswith(('.xlsx', '.xls')):
                # For Excel files, try to read 'vInfo' sheet first, fallback to first sheet
                try:
                    return pd.read_excel(matching_files[0], sheet_name='vInfo', nrows=max_rows)
                except:
                    return pd.read_excel(matching_files[0], nrows=max_rows)
    else:
        # Single file
        print(f"Reading single RVTools file: {filename_or_pattern}")
        df = read_csv_from_current_dir(filename_or_pattern)
        print(f"Loaded {len(df)} rows")
        
        # Filter to powered-on VMs only (powered-off VMs not included in migration)
        if 'Powerstate' in df.columns or 'Power state' in df.columns:
            powerstate_col = 'Powerstate' if 'Powerstate' in df.columns else 'Power state'
            total_vms = len(df)
            powered_on = len(df[df[powerstate_col] == 'poweredOn'])
            powered_off = len(df[df[powerstate_col] != 'poweredOn'])
            print(f"  - Total VMs: {total_vms}")
            print(f"  - PoweredOn VMs: {powered_on}")
            print(f"  - PoweredOff VMs: {powered_off}")
            
            # Filter to powered-on only for migration analysis
            df = df[df[powerstate_col] == 'poweredOn'].copy()
            print(f"  - Filtered to {len(df)} powered-on VMs for migration cost analysis")
        
        return df

# system_message = """
#     Use tool inventory_analysis to perform inventory analysis
#     As an AWS migration expert, conduct a comprehensive analysis of the provided IT inventory with emphasis on cost optimisation, performance metrics, disaster recovery capabilities, and strategic planning.

#         **IMPORTANT: Do not assume, estimate, or calculate any costs, prices, or financial figures unless explicitly provided in the inventory data. Only analyse and report on cost-related information that is directly available in the provided dataset.**

#         IT Inventory: Ensure mathematical operations like addition, subtraction, multiplication, and division are correct for Compute, Storage and Database provided in the inventory.
       
#         Perform a thorough analysis and provide your response in the following structured order:

#         ## (1) Inventory Insight & Cost Verification
#         - **Asset Categorisation**: Identify and categorise by Compute, Storage, Database, Networking, Security, Monitoring, DevOps, AI, ML
#         - **Purchase Price Verification**: 
#             - Check first if purchase prices, acquisition dates, and depreciation schedules are available. If available, then only review and validate purchase prices, acquisition dates, and depreciation schedules
#         - **Cost Categorisation**: 
#             - Check first if costs are available for assets. If available, then only break down costs by asset type with detailed cost allocation
#         - **Service Level Agreements**: 
#             - Check first if any SLAs, performance guarantees, and associated penalty clauses are available. If available, then only review existing SLAs, performance guarantees, and associated penalty clauses

#         ## (2) Capacity & Performance Analysis
#         - **Utilisation Metrics**: CPU usage, memory usage, storage usage, and network bandwidth patterns
#         - **Critical Capacity Issues**: Identify systems operating above 80% capacity with immediate action requirements
#         - **Performance Trends**: Analyse utilisation patterns, peak usage times, and growth trajectories
#         - **Underutilised Resources**: Highlight assets with consistently low utilisation rates

#         ## (3) Disaster Recovery & Business Continuity Analysis
#         - **Storage Systems Assessment**: 
#             - Analyse storage infrastructure (SAN, NAS, local storage) with capacity, performance metrics, and backup capabilities
#             - Identify storage dependencies and single points of failure
#         - **Recovery Requirements (RTO/RPO)**:
#             - Check if RTO (Recovery Time Objective) and RPO (Recovery Point Objective) requirements are documented
#             - If available, analyse business impact classifications and acceptable downtime windows
#             - Assess data loss tolerance requirements per application/system
#         - **Backup Strategies Analysis**:
#             - Review backup frequency schedules and retention policies if documented
#             - Analyse backup testing procedures and success rates if available
#             - Identify gaps in backup coverage or untested backup systems
#         - **Replication Mechanisms**:
#             - Identify existing replication setups (real-time vs. batch processing)
#             - Document synchronous vs. asynchronous replication methods if present
#             - Analyse replication targets and geographic distribution
#         - **Current DR Capabilities**:
#             - Assess existing disaster recovery sites and their capacity
#             - Review DR testing history and procedures if documented
#             - Identify critical systems without adequate DR protection

#         ## (4) Risk Assessment & End-of-Life Planning
#         - **End-of-Life Identification**: List all hardware approaching end-of-life within 12 months
#         - **Security Vulnerabilities**: Identify unsupported or obsolete systems posing security risks
#         - **Business Continuity Impact**: Assess potential service disruption risks and DR readiness gaps
#         - **Single Points of Failure**: Highlight critical systems without redundancy or DR protection

#         ## (5) Cost Optimisation Opportunities
#         - **Licence Consolidation Savings**: Check if any licence details are available. If licence details are available, then only identify potential software licence optimisation and consolidation opportunities for Microsoft and Oracle
#         - **Immediate Cost Reduction**: Identify quick wins for cost reduction (redundant systems, over-provisioned resources)
#         - **DR Cost Efficiency**: Analyse DR infrastructure costs and identify optimisation opportunities if cost data is available

#         ## (6) Patterns, Anomalies & Dependencies
#         - **Usage Patterns**: Identify trends, seasonal variations, and anomalous behaviour
#         - **Asset Dependencies**: Map critical relationships and dependencies between systems
#         - **Technology Stack Analysis**: Highlight integration points and potential single points of failure
#         - **DR Dependencies**: Analyse cross-system dependencies that impact disaster recovery strategies

#         ## (7) Strategic Recommendations & Key Findings
#         - **Executive Summary**: Data-driven insights based solely on available data
#         - **DR Readiness Assessment**: Overall disaster recovery maturity and gaps
#         - **Migration Priorities**: Systems requiring immediate attention for DR improvement
        
#         **REMINDER: Base all analysis strictly on the provided inventory data. Do not introduce external cost estimates, market pricing, or assumed financial figures. For DR analysis, only report on disaster recovery information that is explicitly documented in the inventory.**
        
#         Format your response in markdown with clear headings, bullet points, and tables where appropriate. 
#     """
# agent = Agent(model=bedrock_model,system_prompt= system_message,tools=[rv_tool_analysis])

# question = "Conduct a comprehensive analysis of the provided IT inventory with emphasis on cost optimisation, performance metrics, disaster recovery capabilities for the provided file input/rvtool.csv"

# result = agent(question)
# print(result.message)


# if __name__ == "__main__":
   
#     filename = 'input/rvtool.csv'
#     df = rv_tool_analysis(filename) 
#     print(df)