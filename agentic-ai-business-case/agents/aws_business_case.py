import os
from strands import Agent, tool
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from strands.multiagent.graph import GraphState
from strands.multiagent.base import Status

from config import model_id_claude3_7, model_temperature, output_folder_dir_path, ENABLE_MULTI_STAGE, MAX_TOKENS_BUSINESS_CASE
from inventory_analysis import it_analysis, calculate_it_inventory_arr, extract_atx_arr_tool
from rv_tool_analysis import rv_tool_analysis
from atx_analysis import read_excel_file, read_pdf_file, read_pptx_file
from mra_analysis import read_docx_file, read_markdown_file, read_pdf_file
from migration_strategy import read_migration_strategy_framework, read_portfolio_assessment
from migration_plan import read_migration_plan_framework
from pricing_tools import calculate_exact_aws_arr, compare_pricing_models, get_vm_cost_breakdown
from project_context import get_project_context, get_project_info_dict
from setup_logging import setup_logging
from multi_stage_business_case import generate_multi_stage_business_case
from appendix_content import get_appendix
from prompt_library.agent_prompts import (
    system_message_aws_arr_cost, 
    system_message_rv_tool_analysis, 
    system_message_it_analysis,
    system_message_aws_business_case,
    system_message_current_state_analysis,
    system_message_atx_analysis,
    system_message_mra_analysis,
    system_message_migration_strategy,
    system_message_migration_plan )

# Setup logging
logger, log_file = setup_logging()
logger.info("="*80)
logger.info("AWS BUSINESS CASE GENERATOR - STARTING")
logger.info("="*80)

# Create a BedrockModel with max_tokens limit to prevent overflow
# Add slight temperature variation to break caching
import random
temp_variation = model_temperature + (random.random() * 0.02 - 0.01)  # ±0.01 variation
bedrock_model = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=temp_variation,  # Slight variation to break cache
    max_tokens=MAX_TOKENS_BUSINESS_CASE  # Use configured max tokens (8192)
)

# Create model for cost calculations with lower temperature for consistency
# Use reduced max_tokens (3000) to force concise output and prevent MaxTokensReachedException
bedrock_model_cost = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=0.1,  # Lower temperature for more deterministic cost calculations
    max_tokens=3000  # Reduced from 4096 to force concise, focused output
)

# Create separate model for business case with configured max tokens
bedrock_model_business_case = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=model_temperature,
    max_tokens=MAX_TOKENS_BUSINESS_CASE  # 4096 for Claude 3, 8192 for Claude 3.5
)

agent_it_analysis = Agent(model=bedrock_model,system_prompt= system_message_it_analysis,tools=[it_analysis])
agent_rv_tool_analysis = Agent(model=bedrock_model,system_prompt= system_message_rv_tool_analysis,tools=[rv_tool_analysis])
agent_atx_analysis = Agent(model=bedrock_model,system_prompt= system_message_atx_analysis,tools=[read_excel_file, read_pdf_file, read_pptx_file])
agent_mra_analysis = Agent(model=bedrock_model,system_prompt= system_message_mra_analysis,tools=[read_docx_file, read_markdown_file, read_pdf_file])
agent_migration_strategy = Agent(model=bedrock_model,system_prompt= system_message_migration_strategy,tools=[read_migration_strategy_framework, read_portfolio_assessment])
agent_migration_plan = Agent(model=bedrock_model,system_prompt= system_message_migration_plan,tools=[read_migration_plan_framework])
agent_aws_cost_arr = Agent(model=bedrock_model_cost,system_prompt= system_message_aws_arr_cost,tools=[it_analysis,rv_tool_analysis,calculate_exact_aws_arr,compare_pricing_models,get_vm_cost_breakdown,calculate_it_inventory_arr,extract_atx_arr_tool])  # Use lower temperature for deterministic costs with pricing tools and comparison
current_state_analysis = Agent(model=bedrock_model,system_prompt= system_message_current_state_analysis,tools=[it_analysis,rv_tool_analysis])
aws_business_case = Agent(model=bedrock_model_business_case,system_prompt= system_message_aws_business_case)  # Use higher token limit


# Define conditional edge functions using the factory pattern
def all_dependencies_complete(required_nodes: list[str]):
    """Factory function to create AND condition for multiple dependencies."""
    def check_all_complete(state: GraphState) -> bool:
        return all(
            node_id in state.results and state.results[node_id].status == Status.COMPLETED
            for node_id in required_nodes
        )
    return check_all_complete

# Get project context early to determine input files
project_context = get_project_context()
project_info = get_project_info_dict()

# Get uploaded filenames from project_info if available, otherwise use patterns
uploaded_files = project_info.get('uploadedFiles', {})
case_id = project_info.get('caseId', '')

# Use case-specific paths if case ID exists
if case_id:
    input_base = f"input/{case_id}/"
    logger.info(f"Using case-specific input directory: {input_base}")
else:
    input_base = "input/"
    logger.info("Using base input directory (no case ID)")

input_files1 = f"{input_base}{uploaded_files.get('itInventory', 'it-infrastructure-inventory.xlsx')}" if 'itInventory' in uploaded_files else f"{input_base}it-infrastructure-inventory.xlsx"
input_files2 = f"{input_base}{uploaded_files['rvTool'][0]}" if 'rvTool' in uploaded_files and uploaded_files['rvTool'] else f"{input_base}rvtool*.xlsx"
input_files3_pptx = f"{input_base}{uploaded_files.get('atxPptx', 'atx_business_case.pptx')}" if 'atxPptx' in uploaded_files else f"{input_base}atx_business_case.pptx"

# SMART AGENT SELECTION - Only add agents for files that exist
logger.info("="*80)
logger.info("SMART AGENT SELECTION - Detecting available input files")
logger.info("="*80)

import glob

# Detect which input files are available
# For RVTools, check the actual uploaded file (not glob pattern)
# Need to build absolute path since code runs from agents/ directory
script_dir = os.path.dirname(os.path.abspath(__file__))  # agents/
project_root = os.path.dirname(script_dir)  # project root
rvtools_file_path = os.path.join(project_root, input_base, uploaded_files['rvTool'][0]) if 'rvTool' in uploaded_files and uploaded_files['rvTool'] else None



# Build absolute paths for all files
abs_input_files1 = os.path.join(project_root, input_files1)
abs_input_files3_pptx = os.path.join(project_root, input_files3_pptx)

has_it_inventory = os.path.exists(abs_input_files1)
has_rvtools = rvtools_file_path is not None and os.path.exists(rvtools_file_path)
has_atx_pptx = os.path.exists(abs_input_files3_pptx)
has_atx = has_atx_pptx



# Pre-read MRA file if it exists
mra_content = None
mra_status = "Not Available"
try:
    from mra_analysis import find_mra_file, read_pdf_file as read_mra_pdf, read_docx_file, read_markdown_file
    
    mra_file = find_mra_file()
    if mra_file:
        logger.info(f"MRA file found: {mra_file}")
        
        # Read the file based on extension
        if mra_file.endswith('.pdf'):
            mra_content = read_mra_pdf(mra_file)
        elif mra_file.endswith('.docx') or mra_file.endswith('.doc'):
            mra_content = read_docx_file(mra_file)
        elif mra_file.endswith('.md'):
            mra_content = read_markdown_file(mra_file)
        
        if mra_content and len(mra_content) > 1000:
            mra_status = "Available"
            logger.info(f"MRA content loaded: {len(mra_content)} characters")
        else:
            logger.warning(f"MRA file found but content is minimal: {len(mra_content) if mra_content else 0} characters")
    else:
        logger.info("No MRA file found in input directory")
except Exception as e:
    logger.error(f"Error reading MRA file: {e}")
    import traceback
    logger.error(traceback.format_exc())

has_mra = mra_content is not None and len(mra_content) > 1000

logger.info(f"IT Inventory: {'✓ FOUND' if has_it_inventory else '✗ Not found'} - {input_files1}")
logger.info(f"RVTools: {'✓ FOUND' if has_rvtools else '✗ Not found'} - {input_files2}")
logger.info(f"ATX PowerPoint: {'✓ FOUND' if has_atx_pptx else '✗ Not found'} - {input_files3_pptx}")
logger.info(f"MRA: {'✓ FOUND' if has_mra else '✗ Not found'}")

# Track which analysis agents will be added
active_analysis_agents = []

# Build the graph
builder = GraphBuilder()

# Add analysis agents ONLY if their input files exist
if has_it_inventory:
    builder.add_node(agent_it_analysis, "agent_it_analysis")
    active_analysis_agents.append("agent_it_analysis")
    logger.info("→ Adding agent_it_analysis to graph")

if has_rvtools:
    builder.add_node(agent_rv_tool_analysis, "agent_rv_tool_analysis")
    active_analysis_agents.append("agent_rv_tool_analysis")
    logger.info("→ Adding agent_rv_tool_analysis to graph")

if has_atx:
    builder.add_node(agent_atx_analysis, "agent_atx_analysis")
    active_analysis_agents.append("agent_atx_analysis")
    logger.info("→ Adding agent_atx_analysis to graph")

if has_mra:
    builder.add_node(agent_mra_analysis, "agent_mra_analysis")
    active_analysis_agents.append("agent_mra_analysis")
    logger.info("→ Adding agent_mra_analysis to graph")

# Always add synthesis and planning agents
builder.add_node(current_state_analysis, "current_state_analysis")
builder.add_node(agent_aws_cost_arr, "agent_aws_cost_arr")
builder.add_node(agent_migration_strategy, "agent_migration_strategy")
builder.add_node(agent_migration_plan, "agent_migration_plan")

# Only add aws_business_case node if NOT using multi-stage generation
if not ENABLE_MULTI_STAGE:
    builder.add_node(aws_business_case, "aws_business_case")

logger.info(f"Active analysis agents: {active_analysis_agents}")
logger.info("="*80)

# Build edges dynamically based on active agents
# (1) current_state_analysis executes ONLY when ALL active analysis agents complete
if active_analysis_agents:
    condition_for_current_state = all_dependencies_complete(active_analysis_agents)
    for agent_id in active_analysis_agents:
        builder.add_edge(agent_id, "current_state_analysis", condition=condition_for_current_state)

# (2) agent_aws_cost_arr executes ONLY when ALL active analysis agents complete
if active_analysis_agents:
    condition_for_cost_arr = all_dependencies_complete(active_analysis_agents)
    for agent_id in active_analysis_agents:
        builder.add_edge(agent_id, "agent_aws_cost_arr", condition=condition_for_cost_arr)

# (3) agent_migration_strategy executes ONLY when ALL active analysis agents complete
if active_analysis_agents:
    condition_for_migration_strategy = all_dependencies_complete(active_analysis_agents)
    for agent_id in active_analysis_agents:
        builder.add_edge(agent_id, "agent_migration_strategy", condition=condition_for_migration_strategy)

# (4) agent_migration_plan executes ONLY when ALL three intermediate agents complete
condition_for_migration_plan = all_dependencies_complete(["current_state_analysis", "agent_aws_cost_arr", "agent_migration_strategy"])
builder.add_edge("current_state_analysis", "agent_migration_plan", condition=condition_for_migration_plan)
builder.add_edge("agent_aws_cost_arr", "agent_migration_plan", condition=condition_for_migration_plan)
builder.add_edge("agent_migration_strategy", "agent_migration_plan", condition=condition_for_migration_plan)

# (5) aws_business_case executes ONLY when ALL four intermediate agents complete
# Skip if multi-stage is enabled (we'll generate business case separately)
if not ENABLE_MULTI_STAGE:
    condition_for_business_case = all_dependencies_complete(["current_state_analysis", "agent_aws_cost_arr", "agent_migration_strategy", "agent_migration_plan"])
    builder.add_edge("current_state_analysis", "aws_business_case", condition=condition_for_business_case)
    builder.add_edge("agent_aws_cost_arr", "aws_business_case", condition=condition_for_business_case)
    builder.add_edge("agent_migration_strategy", "aws_business_case", condition=condition_for_business_case)
    builder.add_edge("agent_migration_plan", "aws_business_case", condition=condition_for_business_case)


# Set entry points (the nodes that start first - they run in parallel)
# Only set entry points for active analysis agents
for agent_id in active_analysis_agents:
    builder.set_entry_point(agent_id)
    logger.info(f"Set entry point: {agent_id}")

logger.info(f"Multi-stage generation: {'ENABLED' if ENABLE_MULTI_STAGE else 'DISABLED'}")
if ENABLE_MULTI_STAGE:
    logger.info("Single-stage aws_business_case agent will be skipped")

builder.set_execution_timeout(1800)  # 30 minute timeout for entire workflow
builder.set_node_timeout(600)  # 10 minute timeout per node

# Build the graph
# Note: When ENABLE_MULTI_STAGE=True, the aws_business_case agent result is not used
# Multi-stage generation happens after the graph completes
graph = builder.build()

# Get project context
project_context = get_project_context()
project_info = get_project_info_dict()

# Get uploaded filenames from project_info if available, otherwise use patterns
uploaded_files = project_info.get('uploadedFiles', {})
case_id = project_info.get('caseId', '')

# Use case-specific paths if case ID exists
if case_id:
    input_base = f"input/{case_id}/"
    logger.info(f"Using case-specific input directory: {input_base}")
else:
    input_base = "input/"
    logger.info("Using base input directory (no case ID)")

input_files1 = f"{input_base}{uploaded_files.get('itInventory', 'it-infrastructure-inventory.xlsx')}" if 'itInventory' in uploaded_files else f"{input_base}it-infrastructure-inventory.xlsx"
input_files2 = f"{input_base}{uploaded_files['rvTool'][0]}" if 'rvTool' in uploaded_files and uploaded_files['rvTool'] else f"{input_base}rvtool*.xlsx"
input_files3_excel = f"{input_base}{uploaded_files.get('atxExcel', 'atx_analysis.xlsx')}" if 'atxExcel' in uploaded_files else f"{input_base}atx_analysis.xlsx"
input_files3_pdf = f"{input_base}atx_report.pdf"
input_files3_pptx = f"{input_base}atx_business_case.pptx"
input_files4_mra = f"{input_base}aws-customer-migration-readiness-assessment.md"
input_files5_strategy = f"{input_base}aws-migration-strategy-6rs-framework.md"

logger.info(f"RVTools path: {input_files2}")

# Pre-read MRA file if it exists (Option 1: Direct Python call)
mra_content = None
mra_status = "Not Available"
try:
    from mra_analysis import find_mra_file, read_pdf_file, read_docx_file, read_markdown_file
    
    mra_file = find_mra_file()
    if mra_file:
        logger.info(f"MRA file found: {mra_file}")
        
        # Read the file based on extension
        if mra_file.endswith('.pdf'):
            mra_content = read_pdf_file(mra_file)
        elif mra_file.endswith('.docx') or mra_file.endswith('.doc'):
            mra_content = read_docx_file(mra_file)
        elif mra_file.endswith('.md'):
            mra_content = read_markdown_file(mra_file)
        
        if mra_content and len(mra_content) > 1000:
            mra_status = "Available"
            logger.info(f"MRA content loaded: {len(mra_content)} characters")
        else:
            logger.warning(f"MRA file found but content is minimal: {len(mra_content) if mra_content else 0} characters")
    else:
        logger.info("No MRA file found in input directory")
except Exception as e:
    logger.error(f"Error reading MRA file: {e}")
    import traceback
    logger.error(traceback.format_exc())

import time
import uuid
import random
import pandas as pd
import glob
generation_id = int(time.time())
cache_buster = str(uuid.uuid4())[:8]  # Short unique ID
session_id = str(uuid.uuid4())  # Full UUID for session uniqueness
random_seed = random.randint(10000, 99999)  # Random number to break cache

# PRE-COMPUTE RVTOOLS SUMMARY IN PYTHON (bypasses LLM extraction and caching issues)
def get_rvtools_summary_precomputed(rvtools_path):
    """Pre-compute RVTools summary to avoid LLM extraction issues"""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(rvtools_path)
        logger.info(f"Pre-computing RVTools summary from: {abs_path}")
        
        # Check if file exists
        if not os.path.exists(abs_path):
            logger.error(f"File does not exist: {abs_path}")
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Directory contents: {os.listdir(os.path.dirname(abs_path)) if os.path.exists(os.path.dirname(abs_path)) else 'Directory not found'}")
            return None
        
        df = pd.read_excel(abs_path, sheet_name='vInfo')
        logger.info(f"✓ Loaded {len(df)} VMs from RVTools")
        
        # Filter to powered-on VMs only (powered-off VMs not included in migration)
        if 'Powerstate' in df.columns:
            df_powered_on = df[df['Powerstate'] == 'poweredOn']
            logger.info(f"✓ Filtered to {len(df_powered_on)} powered-on VMs")
        elif 'Power state' in df.columns:
            df_powered_on = df[df['Power state'] == 'poweredOn']
            logger.info(f"✓ Filtered to {len(df_powered_on)} powered-on VMs")
        else:
            df_powered_on = df
            logger.info("✓ No Powerstate column - using all VMs")
        
        # Calculate summary using the same logic as rv_tool_analysis
        from rv_tool_analysis import generate_vm_summary
        summary = generate_vm_summary(df_powered_on)
        
        logger.info(f"✓✓✓ PRE-COMPUTED SUMMARY SUCCESS ✓✓✓")
        logger.info(f"    Total VMs: {summary['total_vms']}")
        logger.info(f"    Total vCPUs: {summary['total_vcpus']}")
        logger.info(f"    Total RAM (GB): {summary['total_memory_gb']:.1f}")
        logger.info(f"    Total Storage (TB): {summary['total_storage_tb']:.1f}")
        logger.info(f"    Windows VMs: {summary.get('windows_vms', 0)}")
        logger.info(f"    Linux VMs: {summary.get('linux_vms', 0)}")
        return summary
    except Exception as e:
        logger.error(f"✗ Error pre-computing RVTools summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# PRE-COMPUTE IT INVENTORY SUMMARY IN PYTHON
def get_it_inventory_summary_precomputed(it_inventory_path):
    """Pre-compute IT Inventory summary to avoid LLM extraction issues"""
    try:
        abs_path = os.path.abspath(it_inventory_path)
        logger.info(f"Pre-computing IT Inventory summary from: {abs_path}")
        
        if not os.path.exists(abs_path):
            logger.error(f"File does not exist: {abs_path}")
            return None
        
        # Read Servers sheet
        df_servers = pd.read_excel(abs_path, sheet_name='Servers')
        logger.info(f"✓ Loaded {len(df_servers)} servers from IT Inventory")
        
        # Read Databases sheet
        df_databases = pd.read_excel(abs_path, sheet_name='Databases')
        total_databases = len(df_databases)
        logger.info(f"✓ Loaded {total_databases} databases from IT Inventory")
        
        # Calculate server totals
        total_servers = len(df_servers)
        server_vcpus = int(df_servers['numCpus'].sum()) if 'numCpus' in df_servers.columns else 0
        server_memory_gb = float(df_servers['totalRAM (GB)'].sum()) if 'totalRAM (GB)' in df_servers.columns else 0.0
        
        # Calculate database totals
        db_vcpus = int(df_databases['CPU Cores'].sum()) if 'CPU Cores' in df_databases.columns else 0
        db_memory_gb = float(df_databases['RAM (GB)'].sum()) if 'RAM (GB)' in df_databases.columns else 0.0
        db_storage_gb = float(df_databases['Total Size (GB)'].sum()) if 'Total Size (GB)' in df_databases.columns else 0.0
        
        # Combined totals
        total_vcpus = server_vcpus + db_vcpus
        total_memory_gb = server_memory_gb + db_memory_gb
        
        # Handle server storage - convert to numeric first
        server_storage_gb = 0.0
        if 'Storage-Total Disk Size (GB)' in df_servers.columns:
            try:
                server_storage_gb = pd.to_numeric(df_servers['Storage-Total Disk Size (GB)'], errors='coerce').sum()
            except Exception as e:
                logger.warning(f"Could not calculate server storage: {e}")
        
        total_storage_tb = float((server_storage_gb + db_storage_gb) / 1024)
        
        # Count OS distribution (servers only)
        windows_vms = 0
        linux_vms = 0
        if 'osName' in df_servers.columns:
            for os_name in df_servers['osName']:
                if pd.notna(os_name):
                    os_lower = str(os_name).lower()
                    if 'windows' in os_lower:
                        windows_vms += 1
                    else:
                        linux_vms += 1
        
        summary = {
            'total_vms': total_servers,
            'total_databases': total_databases,
            'total_vcpus': int(total_vcpus),
            'total_memory_gb': float(total_memory_gb),
            'total_storage_tb': float(total_storage_tb),
            'windows_vms': windows_vms,
            'linux_vms': linux_vms
        }
        
        logger.info(f"✓✓✓ IT INVENTORY PRE-COMPUTED SUMMARY SUCCESS ✓✓✓")
        logger.info(f"    Total Servers: {summary['total_vms']}")
        logger.info(f"    Total Databases: {summary['total_databases']}")
        logger.info(f"    Total vCPUs (Servers + DBs): {summary['total_vcpus']}")
        logger.info(f"    Total RAM (GB) (Servers + DBs): {summary['total_memory_gb']:.1f}")
        logger.info(f"    Total Storage (TB) (Servers + DBs): {summary['total_storage_tb']:.1f}")
        logger.info(f"    Windows Servers: {summary['windows_vms']}")
        logger.info(f"    Linux Servers: {summary['linux_vms']}")
        return summary
    except Exception as e:
        logger.error(f"✗ Error pre-computing IT Inventory summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# PRE-COMPUTE ATX SUMMARY IN PYTHON
def get_atx_summary_precomputed(atx_excel_path):
    """Pre-compute ATX summary to avoid LLM extraction issues"""
    try:
        abs_path = os.path.abspath(atx_excel_path)
        logger.info(f"Pre-computing ATX summary from: {abs_path}")
        
        if not os.path.exists(abs_path):
            logger.error(f"File does not exist: {abs_path}")
            return None
        
        # Use the existing ATX extractor
        from atx_pricing_extractor import extract_atx_arr
        atx_data = extract_atx_arr(abs_path)
        
        if not atx_data.get('success'):
            logger.error(f"ATX extraction failed: {atx_data.get('error')}")
            return None
        
        # Convert to summary format
        summary = {
            'total_vms': atx_data['vm_count'],
            'total_vcpus': 0,  # ATX doesn't provide vCPU details
            'total_memory_gb': 0.0,  # ATX doesn't provide RAM details
            'total_storage_tb': 0.0,  # ATX doesn't provide storage details
            'windows_vms': atx_data.get('os_distribution', {}).get('Windows', 0),
            'linux_vms': atx_data.get('os_distribution', {}).get('Linux', 0),
            'total_arr': atx_data['total_arr'],
            'total_monthly': atx_data['total_monthly']
        }
        
        logger.info(f"✓✓✓ ATX PRE-COMPUTED SUMMARY SUCCESS ✓✓✓")
        logger.info(f"    Total VMs: {summary['total_vms']}")
        logger.info(f"    Windows VMs: {summary['windows_vms']}")
        logger.info(f"    Linux VMs: {summary['linux_vms']}")
        logger.info(f"    Total ARR: ${summary['total_arr']:,.2f}")
        logger.info(f"    Total Monthly: ${summary['total_monthly']:,.2f}")
        return summary
    except Exception as e:
        logger.error(f"✗ Error pre-computing ATX summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# PRE-COMPUTE ATX PPT SUMMARY IN PYTHON
def get_atx_ppt_summary_precomputed(atx_ppt_path):
    """Pre-compute ATX PowerPoint summary to extract key slides"""
    try:
        abs_path = os.path.abspath(atx_ppt_path)
        logger.info(f"Pre-computing ATX PowerPoint summary from: {abs_path}")
        
        if not os.path.exists(abs_path):
            logger.error(f"File does not exist: {abs_path}")
            return None
        
        # Use the new ATX PowerPoint extractor
        from atx_ppt_extractor import extract_atx_ppt_data
        atx_ppt_data = extract_atx_ppt_data(abs_path)
        
        if not atx_ppt_data.get('success'):
            logger.error(f"ATX PowerPoint extraction failed: {atx_ppt_data.get('error')}")
            return None
        
        # Extract data from slides
        scope = atx_ppt_data['assessment_scope']
        financial = atx_ppt_data['financial_overview']
        exec_summary = atx_ppt_data['executive_summary']
        
        # Convert to summary format
        summary = {
            'total_vms': scope.get('vm_count', 0),
            'total_vcpus': scope.get('vcpu_count', 0),
            'total_memory_gb': scope.get('ram_gb', 0),
            'total_storage_tb': scope.get('storage_tb', 0),
            'windows_vms': scope.get('windows_vms', 0),
            'linux_vms': scope.get('linux_vms', 0),
            'database_count': scope.get('database_count', 0),  # Extract database count
            'total_arr': financial.get('annual_cost', 0),
            'total_monthly': financial.get('monthly_cost', 0),
            'three_year_cost': financial.get('three_year_cost', 0),
            'executive_summary_content': exec_summary.get('content', ''),
            'financial_overview_content': financial.get('content', ''),
            'assessment_scope_content': scope.get('content', '')
        }
        
        logger.info(f"✓✓✓ ATX PPT PRE-COMPUTED SUMMARY SUCCESS ✓✓✓")
        logger.info(f"    Total VMs: {summary['total_vms']}")
        logger.info(f"    Windows VMs: {summary['windows_vms']}")
        logger.info(f"    Linux VMs: {summary['linux_vms']}")
        logger.info(f"    Database Count: {summary['database_count']}")
        logger.info(f"    Total ARR: ${summary['total_arr']:,.2f}")
        logger.info(f"    Total Monthly: ${summary['total_monthly']:,.2f}")
        return summary
    except Exception as e:
        logger.error(f"✗ Error pre-computing ATX PowerPoint summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Get pre-computed summaries based on which files exist (priority: RVTools > IT Inventory > ATX)
script_dir = os.path.dirname(os.path.abspath(__file__))  # agents/
project_root = os.path.dirname(script_dir)  # project root

# Try RVTools first (highest priority)
rvtools_summary = None
if has_rvtools:
    if 'rvTool' in uploaded_files and uploaded_files['rvTool']:
        rvtools_filename = uploaded_files['rvTool'][0]
    else:
        rvtools_filename = "RVTools_Export.xlsx"
    
    rvtools_path = os.path.join(project_root, input_base, rvtools_filename)
    logger.info(f"RVTools absolute path: {rvtools_path}")
    rvtools_summary = get_rvtools_summary_precomputed(rvtools_path)

# Try IT Inventory if RVTools not available
it_inventory_summary = None
if has_it_inventory and not rvtools_summary:
    if 'itInventory' in uploaded_files:
        it_inventory_filename = uploaded_files['itInventory']
    else:
        it_inventory_filename = "it-infrastructure-inventory.xlsx"
    
    it_inventory_path = os.path.join(project_root, input_base, it_inventory_filename)
    logger.info(f"IT Inventory absolute path: {it_inventory_path}")
    it_inventory_summary = get_it_inventory_summary_precomputed(it_inventory_path)

# Try ATX if neither RVTools nor IT Inventory available
atx_summary = None
if has_atx and not rvtools_summary and not it_inventory_summary:
    if 'atxPptx' in uploaded_files:
        atx_filename = uploaded_files['atxPptx']
    else:
        atx_filename = "atx_business_case.pptx"
    
    atx_path = os.path.join(project_root, input_base, atx_filename)
    logger.info(f"ATX absolute path: {atx_path}")
    atx_summary = get_atx_ppt_summary_precomputed(atx_path)

# Build data section based on what's available (priority: RVTools > IT Inventory > ATX)
if rvtools_summary:
    infrastructure_data_section = f"""
**═══════════════════════════════════════════════════════════════**
**PRE-COMPUTED RVTOOLS SUMMARY** (MANDATORY - Use these exact numbers)
**═══════════════════════════════════════════════════════════════**

These numbers were calculated directly from the RVTools file in Python.
DO NOT call rv_tool_analysis tool. DO NOT extract numbers from anywhere else.
USE ONLY THESE PRE-COMPUTED VALUES:

- **Total VMs for Migration**: {rvtools_summary['total_vms']}
- **Total vCPUs**: {rvtools_summary['total_vcpus']}
- **Total Memory (GB)**: {rvtools_summary['total_memory_gb']:.1f}
- **Total Storage (TB)**: {rvtools_summary['total_storage_tb']:.1f}
- **Windows VMs**: {rvtools_summary.get('windows_vms', 0)}
- **Linux VMs**: {rvtools_summary.get('linux_vms', 0)} (includes {rvtools_summary.get('other_vms', 0)} "Other" VMs treated as Linux)

**NOTE**: "Other" VMs are treated as Linux for pricing and reporting purposes.

**CRITICAL INSTRUCTIONS FOR ALL AGENTS**:
1. Use ONLY the numbers above in your analysis
2. Do NOT call rv_tool_analysis tool
3. Do NOT extract numbers from tool outputs
4. Do NOT use cached or remembered numbers
5. Copy these exact numbers into your response
6. **FOR ALL SECTIONS**: When reporting OS distribution, use EXACTLY these counts:
   - Windows VMs: {rvtools_summary.get('windows_vms', 0)}
   - Linux VMs: {rvtools_summary.get('linux_vms', 0)}
   - These counts MUST be consistent across ALL sections (Current State, Cost Analysis, etc.)

**═══════════════════════════════════════════════════════════════**
"""
    logger.info("✓ RVTools pre-computed summary added to task")
elif it_inventory_summary:
    infrastructure_data_section = f"""
**═══════════════════════════════════════════════════════════════**
**PRE-COMPUTED IT INVENTORY SUMMARY** (MANDATORY - Use these exact numbers)
**═══════════════════════════════════════════════════════════════**

These numbers were calculated directly from the IT Inventory file in Python.
DO NOT call it_analysis tool. DO NOT extract numbers from anywhere else.
USE ONLY THESE PRE-COMPUTED VALUES:

- **Total Servers for Migration**: {it_inventory_summary['total_vms']}
- **Total Databases (RDS)**: {it_inventory_summary['total_databases']}
- **Total vCPUs (Servers + Databases)**: {it_inventory_summary['total_vcpus']}
- **Total Memory GB (Servers + Databases)**: {it_inventory_summary['total_memory_gb']:.1f}
- **Total Storage TB (Servers + Databases)**: {it_inventory_summary['total_storage_tb']:.1f}
- **Windows Servers**: {it_inventory_summary['windows_vms']}
- **Linux Servers**: {it_inventory_summary['linux_vms']}

**CRITICAL INSTRUCTIONS FOR ALL AGENTS**:
1. Use ONLY the numbers above in your analysis
2. Do NOT call it_analysis tool
3. Do NOT extract numbers from tool outputs
4. Do NOT use cached or remembered numbers
5. Copy these exact numbers into your response
6. **FOR ALL SECTIONS**: When reporting infrastructure, ALWAYS include:
   - Total Servers: {it_inventory_summary['total_vms']}
   - Total Databases: {it_inventory_summary['total_databases']}
   - Total vCPUs, Memory, Storage (combined servers + databases)
7. **FOR ALL SECTIONS**: When reporting OS distribution, use EXACTLY these counts:
   - Windows Servers: {it_inventory_summary['windows_vms']}
   - Linux Servers: {it_inventory_summary['linux_vms']}
   - These counts MUST be consistent across ALL sections (Current State, Cost Analysis, etc.)

**═══════════════════════════════════════════════════════════════**
"""
    logger.info("✓ IT Inventory pre-computed summary added to task")
elif atx_summary:
    # Build ATX section with all extracted content
    assessment_scope_text = atx_summary.get('assessment_scope_content', 'Not available')
    exec_summary_text = atx_summary.get('executive_summary_content', 'Not available')
    financial_overview_text = atx_summary.get('financial_overview_content', 'Not available')
    
    infrastructure_data_section = f"""
**═══════════════════════════════════════════════════════════════**
**ATX PPT PRE-COMPUTED SUMMARY** (MANDATORY - Use these exact numbers and content)
**═══════════════════════════════════════════════════════════════**

These numbers and content were extracted directly from the ATX PowerPoint presentation.
DO NOT call read_pptx_file tool. DO NOT extract numbers from anywhere else.
USE ONLY THESE PRE-EXTRACTED VALUES AND CONTENT:

## ASSESSMENT SCOPE (from ATX PowerPoint)
- **Total VMs for Migration**: {atx_summary['total_vms']}
- **Windows VMs**: {atx_summary['windows_vms']}
- **Linux VMs**: {atx_summary['linux_vms']}
- **Total Databases**: {atx_summary.get('database_count', 0)}
- **Total Storage**: {atx_summary['total_storage_tb']:.2f} TB
- **Total vCPUs**: {atx_summary.get('total_vcpus', 'Not specified in ATX')}
- **Total RAM**: {atx_summary.get('total_memory_gb', 'Not specified in ATX')} GB

**🚨 CRITICAL - DATABASE COUNT**: {atx_summary.get('database_count', 0)} databases
- IF database count is 0: This is VM-ONLY migration, NO RDS, NO database costs
- IF database count > 0: Include both EC2 and RDS costs

**Full Assessment Scope Content**:
{assessment_scope_text}

## EXECUTIVE SUMMARY (from ATX PowerPoint)
**Use this content for Executive Summary section**:
{exec_summary_text}

## FINANCIAL OVERVIEW (from ATX PowerPoint)
- **Monthly AWS Cost**: ${atx_summary['total_monthly']:,.2f}
- **Annual AWS Cost (ARR)**: ${atx_summary['total_arr']:,.2f}
- **3-Year Total Cost**: ${atx_summary.get('three_year_cost', atx_summary['total_arr'] * 3):,.2f}

**Full Financial Overview Content (USE AS-IS in Cost Analysis section)**:
{financial_overview_text}

**CRITICAL INSTRUCTIONS FOR ALL AGENTS**:
1. Use ONLY the numbers and content above in your analysis
2. For Executive Summary: Extract key points from the ATX Executive Summary content
3. For Cost Analysis: Include the Financial Overview content AS-IS
4. For Current State: Use Assessment Scope numbers ONLY
5. DO NOT add information not present in the ATX content
6. DO NOT hallucinate workload types, applications, or technical details
7. If information is missing, state "Not provided in ATX assessment"
8. **FOR ALL SECTIONS**: When reporting OS distribution, use EXACTLY these counts:
   - Windows VMs: {atx_summary['windows_vms']}
   - Linux VMs: {atx_summary['linux_vms']}
   - These counts MUST be consistent across ALL sections

**═══════════════════════════════════════════════════════════════**
"""
    logger.info("✓ ATX PPT pre-computed summary added to task")
else:
    infrastructure_data_section = """
**Infrastructure Summary**: Not available - file could not be read
"""
    logger.warning("⚠ Infrastructure summary could not be pre-computed")

# Build agent task with MRA content if available
# Truncate MRA to 10000 chars to prevent token overflow
mra_section = f"""
    **MRA STATUS**: {mra_status}
    
    {'**MRA CONTENT PROVIDED** - MRA file available for analysis' if mra_content else '**MRA NOT AVAILABLE** - Recommend conducting MRA as next step.'}
    
    {f'--- MRA SUMMARY (first 10000 chars) ---\\n{mra_content[:10000]}\\n--- END MRA SUMMARY ---' if mra_content else ''}
    """ if mra_content else "**MRA STATUS**: Not Available"

# Extract timeline from project description
import re
def extract_timeline_months(description):
    """Extract migration timeline in months from project description"""
    if not description:
        return None
    # Look for patterns like "18 months", "24 months", "within 18 months", "next 18 months"
    patterns = [
        r'within\s+(?:the\s+)?(?:next\s+)?(\d+)\s+months',
        r'(?:next|in)\s+(\d+)\s+months',
        r'(\d+)[-\s]month',
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

timeline_months = extract_timeline_months(project_info.get('projectDescription', ''))
timeline_note = f"\n**⚠️ MIGRATION TIMELINE REQUIREMENT: {timeline_months} MONTHS ⚠️**\n**ALL migration phases, waves, and timelines MUST fit within {timeline_months} months total.**\n**DO NOT exceed {timeline_months} months under any circumstances.**\n" if timeline_months else ""

# Extract project details for ATX deterministic generation
customer_name = project_info.get('customerName', 'Customer')
project_name = project_info.get('projectName', 'AWS Migration')
target_region = project_info.get('awsRegion', 'us-east-1')

logger.info(f"Extracted timeline: {timeline_months} months" if timeline_months else "No timeline found in project description")

# Cache busting: Add unique session identifier
cache_breaking_prefix = f"[SESSION:{session_id[:8]}|GEN:{generation_id}|SEED:{random_seed}] "

agent_task = f"""{cache_breaking_prefix}Create a comprehensive business case to migrate on-premises IT workload to AWS.

{project_context}
{timeline_note}

    {infrastructure_data_section}
    
    **Input Data Sources:**
        1. IT Infrastructure Inventory: {input_files1}
        2. RVTool Assessment Data: {input_files2} (summary pre-computed above)
        3. AWS Transform for VMware (ATX) Assessment:
           - VMware Environment Data: {input_files3_excel}
           - Technical Assessment Report: {input_files3_pdf}
           - Business Case Presentation: {input_files3_pptx}
        4. Migration Readiness Assessment (MRA): {input_files4_mra}
        5. Migration Strategy Framework (6Rs): {input_files5_strategy}
        
    {mra_section}
        
    **CRITICAL**: Use the PRE-COMPUTED RVTOOLS SUMMARY numbers provided above.
   """

logger.info("="*80)
logger.info("STARTING AGENT WORKFLOW")
logger.info("="*80)
logger.info(f"Project: {project_info.get('projectName', 'N/A')}")
logger.info(f"Customer: {project_info.get('customerName', 'N/A')}")
logger.info(f"Region: {project_info.get('awsRegion', 'N/A')}")
logger.info(f"Description: {project_info.get('projectDescription', 'N/A')}")
logger.info("="*80)

logger.info("Executing agent graph...")
result = graph(agent_task)
logger.info("Agent graph execution completed")

logger.info("="*80)
logger.info("FINAL BUSINESS CASE GENERATION")
logger.info("="*80)

# Check if multi-stage generation is enabled
if ENABLE_MULTI_STAGE:
    logger.info("Using MULTI-STAGE generation for comprehensive business case")
    try:
        # Add timeline requirement to project context for multi-stage generation
        project_context_with_timeline = project_context
        if timeline_months:
            project_context_with_timeline = f"""{project_context}

**⚠️ CRITICAL - MIGRATION TIMELINE REQUIREMENT: {timeline_months} MONTHS ⚠️**
**ALL migration phases, waves, and timelines MUST fit within {timeline_months} months total.**
**DO NOT exceed {timeline_months} months under any circumstances.**
**Example for {timeline_months} months: Phase 1 (Months 1-{timeline_months//3}) + Phase 2 (Months {timeline_months//3+1}-{timeline_months*2//3}) + Phase 3 (Months {timeline_months*2//3+1}-{timeline_months}) = {timeline_months} months**
"""
        
        # Check if this is ATX PowerPoint-only (no Excel file)
        # If so, use deterministic generation instead of LLM
        if has_atx_pptx and not has_it_inventory and not has_rvtools:
            logger.info("="*60)
            logger.info("ATX PowerPoint-only detected - using deterministic generation")
            logger.info("="*60)
            
            try:
                from atx_business_case_generator import generate_atx_business_case
                
                # Get ATX PowerPoint path
                if 'atxPpt' in uploaded_files:
                    atx_ppt_filename = uploaded_files['atxPpt']
                else:
                    atx_ppt_filename = "atx_business_case.pptx"
                
                atx_ppt_path = os.path.join(project_root, input_base, atx_ppt_filename)
                
                # Extract project context dict
                project_dict = {
                    'customer_name': customer_name,
                    'project_name': project_name,
                    'target_region': target_region,
                    'timeline_months': timeline_months
                }
                
                # Generate deterministic business case
                final_result_text = generate_atx_business_case(atx_ppt_path, project_dict)
                logger.info(f"Deterministic ATX business case generated ({len(final_result_text)} characters)")
                
            except Exception as e:
                logger.warning(f"Deterministic ATX generation failed: {e}")
                logger.info("Falling back to multi-stage LLM generation")
                final_result_text = generate_multi_stage_business_case(result.results, project_context_with_timeline)
                logger.info(f"Multi-stage business case generated ({len(final_result_text)} characters)")
        else:
            # Generate business case in multiple stages using LLM
            final_result_text = generate_multi_stage_business_case(result.results, project_context_with_timeline)
            logger.info(f"Multi-stage business case generated ({len(final_result_text)} characters)")
        
        file_path = os.path.join(output_folder_dir_path, 'aws_business_case.md')
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(final_result_text)
        logger.info(f"Business case saved to: {file_path}")
        
        # Validate and fix business case
        logger.info("="*60)
        logger.info("Running business case validation...")
        logger.info("="*60)
        try:
            from business_case_validator import validate_business_case
            
            # Find Excel file if it exists
            excel_path = None
            if has_rvtools:
                excel_path = os.path.join(output_folder_dir_path, 'vm_to_ec2_mapping.xlsx')
            elif has_it_inventory:
                excel_path = os.path.join(output_folder_dir_path, f'it_inventory_aws_pricing_{target_region}.xlsx')
            
            if excel_path and not os.path.exists(excel_path):
                excel_path = None
            
            is_valid, issues, fixes = validate_business_case(file_path, excel_path)
            
            if not is_valid and fixes:
                logger.info(f"✓ Business case validated and fixed ({len(fixes)} fixes applied)")
            elif is_valid:
                logger.info("✓ Business case validation passed")
            else:
                logger.warning(f"⚠ Business case has issues but no fixes applied")
                
        except Exception as e:
            logger.warning(f"Business case validation failed: {e}")
            logger.warning("Continuing without validation")
        
    except Exception as e:
        logger.error(f"Multi-stage generation failed: {str(e)}")
        logger.info("Falling back to single-stage generation")
        
        if "aws_business_case" in result.results:
            final_result = result.results["aws_business_case"].result
            final_result_text = str(final_result)
            file_path = os.path.join(output_folder_dir_path, 'aws_business_case.md')
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("# AWS Business Case Report\n\n")
                file.write(f"Generated on: {result.execution_order[-1].execution_time}ms execution time\n\n")
                file.write("---\n\n")
                file.write(final_result_text)
            logger.info(f"Business case saved to: {file_path}")
else:
    logger.info("Using SINGLE-STAGE generation")
    if "aws_business_case" in result.results:
        final_result = result.results["aws_business_case"].result
        logger.info("Business case generated successfully")
        
        final_result_text = str(final_result)
        file_path = os.path.join(output_folder_dir_path, 'aws_business_case.md')
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("# AWS Business Case Report\n\n")
            file.write(f"Generated on: {result.execution_order[-1].execution_time}ms execution time\n\n")
            file.write("---\n\n")
            file.write(final_result_text)
            file.write("\n\n---\n\n")
            file.write(get_appendix())
        logger.info(f"Business case saved to: {file_path}")
        
        # Validate and fix business case
        logger.info("="*60)
        logger.info("Running business case validation...")
        logger.info("="*60)
        try:
            from business_case_validator import validate_business_case
            
            # Find Excel file if it exists
            excel_path = None
            if has_rvtools:
                excel_path = os.path.join(output_folder_dir_path, 'vm_to_ec2_mapping.xlsx')
            elif has_it_inventory:
                excel_path = os.path.join(output_folder_dir_path, f'it_inventory_aws_pricing_{target_region}.xlsx')
            
            if excel_path and not os.path.exists(excel_path):
                excel_path = None
            
            is_valid, issues, fixes = validate_business_case(file_path, excel_path)
            
            if not is_valid and fixes:
                logger.info(f"✓ Business case validated and fixed ({len(fixes)} fixes applied)")
            elif is_valid:
                logger.info("✓ Business case validation passed")
            else:
                logger.warning(f"⚠ Business case has issues but no fixes applied")
                
        except Exception as e:
            logger.warning(f"Business case validation failed: {e}")
            logger.warning("Continuing without validation")
    else:
        logger.error("Business case not found in results")

logger.info("="*60)
logger.info(f"Status: {result.status}")
logger.info(f"Execution order: {[node.node_id for node in result.execution_order]}")
logger.info("="*60)

# Display overall performance
logger.info("=== Graph Performance ===")
logger.info(f"Total Nodes Executed: {result.completed_nodes}/{result.total_nodes}")
logger.info(f"Total Execution Time: {result.execution_time}ms")
logger.info(f"Token Usage: {result.accumulated_usage}")

# Display individual node performance
logger.info("=== Individual Node Performance ===")
for node in result.execution_order:
    logger.info(f"- {node.node_id}: {node.execution_time}ms")
    if hasattr(node, 'status'):
        logger.info(f"  Status: {node.status}")

logger.info("="*80)
logger.info(f"Log file saved to: {log_file}")
logger.info("="*80)

