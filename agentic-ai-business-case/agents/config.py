import os

# Get the directory where this config file is located
_config_dir = os.path.dirname(os.path.abspath(__file__))

# Set paths relative to the project root (parent of agents directory)
_project_root = os.path.dirname(_config_dir)

# Input and output directories (relative paths)
input_folder_dir_path = _project_root + "/"
output_folder_dir_path = os.path.join(_project_root, "output") + "/"

#Bedrock Model Configuration

# Option 1: Claude 3 Sonnet (4096 max tokens) - Works with on-demand, STABLE
# model_id_claude3_7="anthropic.claude-3-sonnet-20240229-v1:0"
# max_tokens_default = 4096

# Option 2: Claude 3.5 Sonnet with Cross-Region Inference (8192 max tokens)
# Requires model access enabled in Bedrock Console - see CLAUDE_35_SETUP.md
# TEMPORARILY DISABLED: Service unavailable errors
# model_id_claude3_7="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
# max_tokens_default = 8192

# Option 1: Claude 3 Sonnet (4096 max tokens) - STABLE, RELIABLE
model_id_claude3_7="anthropic.claude-3-sonnet-20240229-v1:0"
max_tokens_default = 4096

# Alternative models:
# model_id_claude3_7="anthropic.claude-3-haiku-20240307-v1:0"  # Faster, cheaper (4096 tokens)

model_id_nova_ite="us.amazon.nova-lite-v1:0"
model_temperature=0.3

# Multi-stage generation settings
ENABLE_MULTI_STAGE = True  # Generate business case in multiple stages
MAX_TOKENS_BUSINESS_CASE = max_tokens_default  # Will use 8192 if Claude 3.5

# Data limits to prevent context window overflow and max_tokens errors
# Reduced significantly to prevent agent output from exceeding token limits
MAX_ROWS_RVTOOLS = 2500  # Max VMs to analyze from RVTools (increased to 2500 to capture all VMs in typical datasets)
MAX_ROWS_IT_INVENTORY = 1500  # Max rows per sheet in IT inventory (reduced from 3000)
MAX_ROWS_PORTFOLIO = 1000  # Max applications in portfolio (reduced from 2000)

# ============================================================================
# DETERMINISTIC PRICING CONFIGURATION
# ============================================================================
# Control whether to use deterministic pricing calculator or LLM-based estimation

# Enable/disable deterministic pricing
USE_DETERMINISTIC_PRICING = True  # Default: ON for consistent, accurate pricing

# AWS Pricing Calculator Settings (only used if USE_DETERMINISTIC_PRICING = True)
PRICING_CONFIG = {
    # Try to use AWS Price List API for real-time pricing
    # If False or API unavailable, uses fallback pricing
    'use_aws_pricing_api': True,  # Default: ON for real-time AWS pricing
    
    # Default AWS region for pricing calculations
    # Can be overridden per calculation
    'default_region': 'us-east-1',
    
    # Pricing model to use
    # Options: '3yr_compute_sp', '3yr_ec2_sp', '3yr_no_upfront', '1yr_no_upfront', 'on_demand'
    # '3yr_compute_sp' = 3-Year Compute Savings Plan (recommended, most flexible, typically cheapest)
    # '3yr_ec2_sp' = 3-Year EC2 Instance Savings Plan (less flexible, typically more expensive than Compute SP)
    # '3yr_no_upfront' = 3-Year Reserved Instance No Upfront
    'pricing_model': '3yr_compute_sp',
    
    # Storage pricing (EBS gp3 per GB-month)
    'storage_rate_per_gb': 0.08,  # us-east-1 base rate
    
    # Data transfer estimate (as percentage of compute cost)
    'data_transfer_percentage': 0.05,  # 5% of compute cost
    
    # Enable caching for pricing lookups (improves performance)
    'enable_caching': True,
    
    # Show detailed pricing breakdown in logs
    'verbose_logging': True,
    
    # Prefer AWS Graviton (ARM) instances for Linux workloads (20% cheaper)
    # Only applies to Linux VMs, Windows will use x86
    'prefer_graviton': False,  # Set to True to prefer Graviton instances
    
    # Instance generation preference
    # Options: 'latest' (7th gen), 'newer' (6th gen), 'current' (5th gen), 'cost_optimized' (mix)
    'generation_preference': 'newer',  # Recommended: 'newer' for best price/performance
}

# ============================================================================
# RIGHT-SIZING CONFIGURATION
# ============================================================================
# Apply right-sizing based on actual utilization (if available in RVTools)
# These assumptions align with AWS Transform for VMware (ATX) methodology

RIGHT_SIZING_CONFIG = {
    # Enable right-sizing based on utilization data
    'enable_right_sizing': True,  # Default: ON for cost optimization
    
    # CPU right-sizing: Use peak utilization
    # ATX Assumption: 25% peak CPU utilization
    'cpu_sizing_method': 'peak',  # Options: 'peak', 'average', 'p95' (95th percentile)
    'cpu_peak_utilization_percent': 25,  # ATX standard: 25% peak CPU utilization
    'cpu_headroom_percentage': 0,  # No additional headroom (already in 25% assumption)
    
    # Memory right-sizing: Use peak utilization
    # ATX Assumption: 60% peak memory utilization
    'memory_sizing_method': 'peak',  # Options: 'peak', 'average', 'p95'
    'memory_peak_utilization_percent': 60,  # ATX standard: 60% peak memory utilization
    'memory_headroom_percentage': 0,  # No additional headroom (already in 60% assumption)
    
    # Storage right-sizing: Use actual used storage vs provisioned
    # ATX Assumption: 50% storage utilization if missing data
    'storage_sizing_method': 'used',  # Options: 'used', 'provisioned'
    'storage_utilization_percent': 50,  # ATX standard: 50% storage utilization
    'storage_headroom_percentage': 0,  # No additional headroom (already in 50% assumption)
    
    # Default provisioned storage if missing data
    # ATX Assumption: 500 GiB default provisioned storage
    'default_provisioned_storage_gib': 500,  # Default storage per VM if data missing
    
    # Minimum instance sizes (prevent over-optimization)
    'min_vcpu': 2,  # Minimum 2 vCPUs
    'min_memory_gb': 4,  # Minimum 4 GB RAM
    
    # Right-sizing aggressiveness
    # Options: 'conservative' (more headroom), 'moderate', 'aggressive' (less headroom)
    'aggressiveness': 'moderate',
}

# ============================================================================
# TCO COMPARISON CONFIGURATION
# ============================================================================
# Control whether to include on-premises TCO comparison in business case

TCO_COMPARISON_CONFIG = {
    # Enable on-premises TCO comparison
    # If False, business case will focus on AWS costs and business value only
    'enable_tco_comparison': False,  # Set to True to include TCO comparison
    
    # On-premises cost assumptions (used if enable_tco_comparison = True)
    'on_prem_costs': {
        'hardware_per_server_per_year': 5000,  # Hardware depreciation + refresh
        'vmware_license_per_vm_per_year': 200,  # VMware licensing
        'windows_license_per_vm_per_year': 150,  # Windows licensing
        'datacenter_per_rack_per_year': 1000,  # Power, cooling, space
        'it_staff_per_fte_per_year': 150000,  # IT staff cost
        'vms_per_fte': 100,  # Assume 1 FTE per 100 VMs
        'maintenance_percentage': 15,  # 15% of hardware cost
    },
    
    # TCO comparison display options
    'show_tco_only_if_aws_cheaper': True,  # Only show TCO if AWS < On-Prem
    'tco_analysis_years': 3,  # 3-year TCO comparison
}

# Legacy LLM-based pricing (only used if USE_DETERMINISTIC_PRICING = False)
# These are the assumption-based ranges used in prompts
LEGACY_PRICING_RANGES = {
    'small_vm': (200, 300),      # 1-2 vCPU, 4-8 GB RAM
    'medium_vm': (400, 600),     # 3-4 vCPU, 8-16 GB RAM
    'large_vm': (800, 1200),     # 5-8 vCPU, 16-32 GB RAM
    'xlarge_vm': (1500, 2500),   # 9+ vCPU, 32+ GB RAM
}
