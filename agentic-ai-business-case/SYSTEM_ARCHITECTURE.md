# System Architecture

## Overview

Multi-agent AI system that generates AWS migration business cases from infrastructure data (RVTools, IT Inventory, or ATX assessments).

## Project Structure

The codebase is organized into functional modules:

```
agents/
├── core/                    # Business case generation orchestration
│   ├── aws_business_case.py
│   ├── multi_stage_business_case.py
│   └── case_output_manager.py
│
├── analysis/                # Data analysis modules
│   ├── inventory_analysis.py
│   ├── rv_tool_analysis.py
│   ├── atx_analysis.py
│   ├── mra_analysis.py
│   └── atx_ppt_extractor.py
│
├── pricing/                 # Pricing and cost calculation
│   ├── aws_pricing_calculator.py
│   ├── pricing_tools.py
│   ├── it_inventory_pricing.py
│   ├── atx_pricing_extractor.py
│   ├── eks_pricing.py
│   └── backup_pricing.py
│
├── strategy/                # Migration strategy and planning
│   ├── migration_strategy.py
│   ├── migration_plan.py
│   └── wave_planning.py
│
├── export/                  # Export and reporting
│   ├── excel_export.py
│   └── appendix_content.py
│
├── config/                  # Configuration management
│   ├── config.py
│   └── config_manager.py
│
├── utils/                   # Utility functions
│   ├── setup_logging.py
│   ├── project_context.py
│   ├── os_detection.py
│   ├── bedrock_guardrails.py
│   └── version.py
│
└── prompt_library/          # Agent prompts
    └── agent_prompts.py
```

## Recent Updates (January 2026)

### AWS Backup Cost Analysis (✅ NEW - January 2026)
- **Intelligent backup cost calculation** with storage tiering (up to 85% savings)
- Production vs pre-production differentiation with different retention policies
- Automatic environment detection from VM names, folders, clusters
- EKS persistent volume backup support
- Real-time AWS Pricing API integration with regional multipliers
- Excel export integration with backup cost column and Backup Summary sheet
- **Implementation**: `agents/pricing/backup_pricing.py`, `agents/pricing/aws_pricing_calculator.py`, `agents/pricing/it_inventory_pricing.py`, `agents/export/excel_export.py`

### Dependency-Based Wave Planning (✅ NEW - January 2026)
- **Intelligent migration waves** from IT Infrastructure Inventory dependencies
- Parses Application dependency, Server to application, Database to application sheets
- Generates Wave 1 (independent apps), Wave 2+ (dependency-based grouping)
- Transparent messaging when dependencies unavailable
- **Implementation**: `agents/strategy/wave_planning.py`, `agents/strategy/migration_plan.py`, `agents/core/multi_stage_business_case.py`

### IT Infrastructure Inventory EKS Enhancement (✅ NEW - January 2026)
- **Uses actual server specs** from IT Inventory Servers sheet (not synthetic estimates)
- Reads real vCPU, RAM, OS, storage per server
- Server-specific EKS categorization with actual names
- Accurate cluster sizing based on real workloads
- **Implementation**: `agents/core/aws_business_case.py` (new function: `get_it_inventory_servers_for_eks()`)

### EKS Container Migration
- **Python-based recommendation engine** - Deterministic 4-tier decision tree
- OS-aware VM categorization, consolidation ratios (2-3.5x Linux, 1.1-2x Windows)
- 35+ worker node types (Intel, AMD, Graviton), Spot instance strategy
- Excel export with 5 tabs, MRA-based recommendations
- **Implementation**: `agents/pricing/eks_pricing.py`, `agents/export/excel_export.py`, `agents/core/aws_business_case.py`

### Bedrock Guardrails (Optional)
- PII protection, hallucination prevention, content filtering
- Setup: `./setup_bedrock_guardrail.sh`
- Cost: ~$0.06 per business case (~51% overhead)
- **Implementation**: `agents/utils/bedrock_guardrails.py`, `agents/config/config.py`

### AWS Price List API Integration
- Real-time pricing for EC2, RDS, EKS (all pricing models)
- Default: 3-Year Compute Savings Plan (~9% cheaper than 3-Year RI)
- LRU cache for performance, automatic fallback if API fails
- **Implementation**: `agents/pricing/aws_pricing_calculator.py`

### Smart Agent Selection
- System detects available input files
- Only runs agents for uploaded files (e.g., skips IT Inventory agent if no file)
- Logs show: "✓ FOUND" or "✗ Not found" for each input type
- **Implementation**: `agents/core/aws_business_case.py` (lines ~140-180)

### Pre-Computed Infrastructure Summaries
- Python pre-computes VM/server counts before agent execution
- Ensures consistent counts across all sections (no LLM caching issues)
- Priority: RVTools > IT Inventory > ATX
- **Implementation**: `agents/core/aws_business_case.py` (lines ~450-650)

## Complete Business Case Generation Flow

### 1. UI Request (Frontend → Backend)

**File**: `ui/backend/app.py`

```
User clicks "Generate Business Case"
    ↓
POST /api/generate-business-case
    ↓
Receives: {projectName, customerName, region, files}
    ↓
Saves files to: input/case-{caseId}/
    ↓
Calls: run_business_case_generation()
```

### 2. Main Orchestrator

**File**: `agents/core/aws_business_case.py`

```python
run_business_case_generation()
    ↓
1. Detect available input files (RVTools, IT Inventory, ATX)
2. Pre-compute infrastructure summary:
   - RVTools: Filters to powered-on VMs, calculates totals
   - IT Inventory: Reads Servers tab, calculates totals
   - Priority: RVTools > IT Inventory > ATX
3. Read MRA PDF content (if available)
4. Build agent graph with smart selection (only active agents)
5. Execute agent graph (parallel where possible)
6. Generate multi-stage business case
7. Save to output/aws_business_case.md
```

### 3. Agent Graph Execution

**Smart Agent Selection**:
- System detects which input files exist
- Only adds agents to graph if their input files exist
- Active agents tracked in `active_analysis_agents` list

**Execution Order**:

```
PHASE 1 - Analysis (Parallel, Auto-Selected):
├── agent_it_analysis        → IT inventory (if file exists)
├── agent_rv_tool_analysis   → RVTools (if file exists)
├── agent_atx_analysis        → ATX (if file exists)
└── agent_mra_analysis        → MRA (if file exists)

PHASE 2 - Synthesis (Wait for ALL active Phase 1 agents):
├── current_state_analysis    → Synthesizes Phase 1 results
├── agent_migration_strategy  → 7Rs recommendations
└── agent_aws_cost_arr        → Cost calculations (calls pricing tools)

PHASE 3 - Planning (Wait for Phase 2):
└── agent_migration_plan      → Roadmap and timeline
    └── generate_wave_plan_from_dependencies (tool) → Dependency-based waves

PHASE 4 - Final Document (Wait for Phase 3):
└── Multi-stage business case generation (7 sections + appendix)
```

### 4. Pre-Computed Infrastructure Summaries

**File**: `agents/core/aws_business_case.py`

To ensure consistent VM/server counts and avoid LLM caching issues:

**RVTools Pre-Computation** (`get_rvtools_summary_precomputed()`):
```python
1. Read RVTools Excel with pandas
2. Filter to powered-on VMs only
3. Calculate totals: VMs, vCPUs, RAM, Storage
4. Count OS distribution (Windows/Linux/Other)
5. Treat "Other" VMs as Linux
6. Pass exact numbers to all agents
```

**IT Inventory Pre-Computation** (`get_it_inventory_summary_precomputed()`):
```python
1. Read IT Inventory Servers tab with pandas
2. Calculate totals: Servers, vCPUs, RAM, Storage
3. Count OS distribution (Windows/Linux)
4. Pass exact numbers to all agents
```

**IT Inventory Servers for EKS** (`get_it_inventory_servers_for_eks()`) - **NEW**:
```python
1. Read IT Inventory Servers sheet with pandas
2. Extract ACTUAL specs per server: vCPU, RAM, OS, storage
3. Return list of servers with real specifications
4. Used for accurate EKS categorization (not synthetic estimates)
```

**Priority Logic**:
- If RVTools available → Use RVTools summary
- Else if IT Inventory available → Use IT Inventory summary
- Else if ATX available → Extract from ATX

**Benefits**:
- ✅ Consistent counts across all sections
- ✅ Avoids LLM caching issues
- ✅ Faster execution (no repeated file parsing)
- ✅ Deterministic results

### 5. Individual Agent Files & Roles

#### Analysis Agents:

**`agents/analysis/rv_tool_analysis.py`**
- Reads RVTools Excel/CSV files
- Filters to powered-on VMs only
- Generates VM summary statistics
- Tool: `rv_tool_analysis()`

**`agents/analysis/inventory_analysis.py`**
- Reads IT inventory files
- Tool: `inventory_analysis()`

**`agents/analysis/atx_analysis.py`**
- Reads ATX files (Excel, PDF, PowerPoint)
- Tools: `read_excel_file()`, `read_pdf_file()`, `read_pptx_file()`

**`agents/analysis/mra_analysis.py`**
- Reads MRA PDF documents
- Extracts migration readiness findings
- Tool: `read_file_from_input_dir()`

#### Cost Analysis:

**`agents/pricing/pricing_tools.py`**
- Tool: `calculate_exact_aws_arr()` - RVTools pricing
- Tool: `compare_pricing_models()` - Compares pricing options
- Tool: `get_vm_cost_breakdown()` - Single VM cost
- Uses `agents/pricing/aws_pricing_calculator.py` for calculations

**`agents/analysis/inventory_analysis.py`**
- Tool: `calculate_it_inventory_arr()` - IT Inventory pricing
- Calculates BOTH: 3-Year EC2 Savings Plan AND 3-Year RI
- Returns simplified text format (better LLM parsing)
- Uses `agents/pricing/it_inventory_pricing.py` for core calculations

**`agents/pricing/aws_pricing_calculator.py`**
- Class: `AWSPricingCalculator`
- Method: `calculate_arr_from_dataframe()`
- Calculates costs for each VM
- Returns aggregated results with breakdowns

**`agents/export/excel_export.py`**
- Function: `export_vm_to_ec2_mapping()`
- Creates: `output/vm_to_ec2_mapping.xlsx`
- Contains VM-to-EC2 instance mapping with costs

#### EKS Analysis:

**`agents/pricing/eks_pricing.py`**
- Function: `categorize_vms_for_eks()` - OS-aware VM categorization
- Function: `calculate_eks_cluster_size()` - Worker node sizing
- Function: `calculate_eks_costs_async()` - Parallel cost calculation
- Function: `allocate_eks_costs_to_vms()` - Cost allocation
- Function: `recommend_eks_strategy()` - MRA-based recommendations

**`agents/core/aws_business_case.py`** (EKS Recommendation)
- Function: `calculate_eks_recommendation()` - **Python-based 4-tier decision tree**
- Lines: ~815-950 (function definition)
- Lines: ~1190-1260 (function call after hybrid costs calculation)
- **Deterministic logic** (no LLM guessing):
  - Tier 1: EKS < EC2 → Recommend EKS
  - Tier 2: EKS 0-20% more → Recommend EKS (strategic value)
  - Tier 3: EKS 20-50% more → Recommend EC2 (mention EKS)
  - Tier 4: EKS 50%+ more → Recommend EC2 only
- Configurable thresholds in `agents/config/config.py`

**`agents/export/excel_export.py`** (EKS Functions)
- Function: `create_eks_sizing_tab()` - VM categorization table
- Function: `create_eks_cluster_design_tab()` - Cluster configuration
- Function: `create_ec2_vs_eks_comparison_tab()` - Cost comparison
- Function: `create_migration_strategy_summary_tab()` - Executive summary
- Function: `create_eks_roi_analysis_tab()` - ROI calculations
- Function: `export_eks_analysis_to_excel()` - Main export orchestrator

**`agents/analysis/mra_analysis.py`** (EKS Functions)
- Function: `parse_mra_for_eks()` - Main MRA parsing for EKS
- Extracts: cloud readiness, container expertise, DevOps maturity, change readiness

#### Strategy & Planning:

**`agents/strategy/migration_strategy.py`**
- 7Rs distribution (Rehost, Replatform, Refactor, etc.)
- Wave planning recommendations

**`agents/strategy/migration_plan.py`**
- Roadmap generation
- Timeline creation with milestones
- Tool: `read_migration_plan_framework()` - Reads framework document
- Tool: `generate_wave_plan_from_dependencies()` - **NEW**: Dependency-based wave planning

**`agents/strategy/wave_planning.py`** - **NEW MODULE (January 2026)**
- Function: `parse_it_inventory_dependencies()` - Reads dependency sheets from IT Inventory
- Function: `build_dependency_graph()` - Creates application dependency graph
- Function: `generate_migration_waves()` - Groups applications by dependency chains
- Function: `format_wave_plan_markdown()` - Formats wave plan for business case
- Tool: `generate_wave_plan_from_dependencies()` - Strands tool for agent use
- **Output**: Wave 1 (independent apps), Wave 2+ (dependency-based grouping)

### 6. Multi-Stage Business Case Generation

**File**: `agents/core/multi_stage_business_case.py`

```python
generate_multi_stage_business_case(agent_results, project_context)
    ↓
For each section:
    1. Executive Summary
    2. Current State Analysis
    3. Migration Strategy
    4. Cost Analysis
    5. Migration Roadmap
    6. Benefits and Risks
    7. Recommendations
    8. Appendix
    ↓
Each section:
    - Creates dedicated agent with section-specific prompt
    - Passes all previous agent results as context
    - Generates section content
    - Combines into final document
```

**Section Prompts** (all in `agents/core/multi_stage_business_case.py`):
- `EXECUTIVE_SUMMARY_PROMPT`
- `CURRENT_STATE_PROMPT`
- `MIGRATION_STRATEGY_PROMPT`
- `COST_ANALYSIS_PROMPT` (dynamic based on TCO config)
- `MIGRATION_ROADMAP_PROMPT`
- `BENEFITS_RISKS_PROMPT`
- `RECOMMENDATIONS_PROMPT`

### 7. Supporting Files

**Configuration:**
- `agents/config/config.py` - System configuration (regions, pricing models, TCO settings, EKS config)
- `agents/config/config_manager.py` - Configuration override management

**Utilities:**
- `agents/utils/project_context.py` - Helper functions for case-specific file paths
- `agents/utils/setup_logging.py` - Logging configuration
- `agents/utils/bedrock_guardrails.py` - Guardrails integration
- `agents/prompt_library/agent_prompts.py` - All individual agent prompts
- `agents/export/appendix_content.py` - AWS partner programs content

### 8. Output Files

```
output/
├── aws_business_case.md          ← Final business case document
├── vm_to_ec2_mapping.xlsx        ← Excel export with VM→EC2 mapping
├── eks_migration_analysis.xlsx   ← EKS analysis with 5 tabs
└── logs/
    └── agent_execution_*.log     ← Execution logs with timestamps
```

**EKS Excel Tabs**:
1. Migration Strategy Summary - Executive view with recommendation
2. EKS VM Categorization - Technical breakdown by OS and size
3. EKS Cluster Design - Worker node configuration
4. EC2 vs EKS Comparison - Cost comparison
5. EKS ROI Analysis - Financial justification

## Simplified Flow Diagram

```
UI (React)
    ↓
ui/backend/app.py (Flask)
    ↓
agents/core/aws_business_case.py (Main Orchestrator)
    ↓
┌─────────────────────────────────────────┐
│  AGENT GRAPH (Parallel Execution)      │
├─────────────────────────────────────────┤
│  Phase 1: Analysis Agents               │
│  ├─ analysis/rv_tool_analysis.py       │
│  ├─ analysis/mra_analysis.py           │
│  ├─ analysis/atx_analysis.py           │
│  └─ analysis/inventory_analysis.py     │
│                                          │
│  Phase 2: Synthesis                     │
│  ├─ current_state_analysis              │
│  ├─ strategy/migration_strategy.py     │
│  └─ aws_arr_cost.py                     │
│      └─ pricing/pricing_tools.py       │
│          ├─ pricing/aws_pricing_calculator.py│
│          │   └─ export/excel_export.py │
│          └─ pricing/eks_pricing.py     │
│              ├─ categorize_vms_for_eks()│
│              ├─ calculate_eks_costs()   │
│              └─ recommend_eks_strategy()│
│                                          │
│  Phase 3: Planning                      │
│  └─ strategy/migration_plan.py         │
│                                          │
│  Phase 4: Python-Based EKS Recommendation│
│  └─ calculate_eks_recommendation()      │
│      (Deterministic 4-tier decision tree)│
└─────────────────────────────────────────┘
    ↓
core/multi_stage_business_case.py
    ↓
Generates 7 sections + appendix
    ↓
output/aws_business_case.md
output/eks_migration_analysis.xlsx
```

## Key Points

### Entry Point
- **UI**: `ui/backend/app.py` receives POST request
- **Main Orchestrator**: `agents/aws_business_case.py` coordinates everything

### Parallel Execution
- Phase 1 agents run simultaneously for efficiency
- Dependencies ensure proper data flow between phases

### VM Filtering
- Happens in `rv_tool_analysis.py`
- Filters to powered-on VMs only
- Critical for accurate cost calculations

### Cost Calculation Flow
```
pricing/pricing_tools.py
    ↓ calls
analysis/rv_tool_analysis.py (gets filtered VMs)
    ↓ passes to
pricing/aws_pricing_calculator.py
    ↓ calculates costs
export/excel_export.py (generates Excel)
```

### EKS Recommendation Flow (Python-Based)
```
1. Calculate EC2 costs (Option 1, Option 2)
2. Calculate EKS costs (Option 3)
3. Python: calculate_eks_recommendation()
   - Compare costs
   - Apply 4-tier decision tree
   - Generate recommendation data
4. Log recommendation decision
5. Inject recommendation into LLM context
6. LLM: Generate business case
   - Read pre-calculated recommendation
   - Copy recommendation exactly
   - Expand rationale into natural language
```

### Final Assembly
- `agents/core/multi_stage_business_case.py` generates each section
- Each section has dedicated agent with specific prompt
- All sections receive context from previous agent results

## Data Flow Example

### Example: 51 VMs Migration

```
1. User uploads RVTools file (212 total VMs)
   ↓
2. rv_tool_analysis.py filters to 51 powered-on VMs
   ↓
3. Pre-computed summary: 51 VMs, 213 vCPUs, 686 GB RAM, 11.3 TB storage
   ↓
4. pricing_tools.py calculates costs for 51 VMs
   ↓
5. aws_pricing_calculator.py: $5,941.43/month for 51 VMs
   ↓
6. Excel export: 51 rows (one per VM)
   ↓
7. current_state_analysis: Uses 51 VMs in summary
   ↓
8. Executive Summary: Shows 51 VMs, $5,941.43/month
   ↓
9. Cost Analysis: Shows 51 VMs, $5,941.43/month (consistent!)
   ↓
10. Final business case: All sections show 51 VMs consistently
```

## Configuration

### Key Configuration Files

**`agents/config/config.py`**:
- `USE_DETERMINISTIC_PRICING` - Enable/disable pricing tools
- `TCO_COMPARISON_CONFIG` - TCO comparison settings
- `model_id_claude3_7` - AI model selection
- `MAX_TOKENS_BUSINESS_CASE` - Output token limits
- `EKS_CONFIG` - EKS analysis configuration
- `EKS_RECOMMENDATION_THRESHOLDS` - Python-based recommendation thresholds
- `BACKUP_CONFIG` - AWS Backup configuration
- `BEDROCK_GUARDRAIL_CONFIG` - Guardrails configuration

### EKS Configuration

```python
EKS_CONFIG = {
    'enabled': True,
    'strategy': 'hybrid',  # 'hybrid', 'all-eks', or 'disabled'
    'enable_graviton': True,  # AWS Graviton (ARM) for 20% savings
    'consolidation_ratios': {
        'linux': {'small': 3.5, 'medium': 2.5, 'large': 1.75, 'xlarge': 1.25},
        'windows': {'small': 2.0, 'medium': 1.5, 'large': 1.25, 'xlarge': 1.1}
    },
    'spot_percentage': 0.30,  # 30% Spot instances
    'on_demand_percentage': 0.40,  # 40% On-Demand
    'reserved_percentage': 0.30,  # 30% Reserved/Savings Plan
}

EKS_RECOMMENDATION_THRESHOLDS = {
    'tier2_max_premium': 0.20,  # Recommend EKS up to 20% premium
    'tier3_max_premium': 0.50,  # Mention EKS up to 50% premium
}
```

### TCO Configuration

```python
TCO_COMPARISON_CONFIG = {
    'enable_tco_comparison': False,  # Set to True to enable
    'on_prem_costs': {
        'hardware_per_server_per_year': 5000,
        'vmware_license_per_vm_per_year': 200,
        # ... more settings
    }
}
```

### AWS Backup Configuration

```python
BACKUP_CONFIG = {
    'enabled': True,  # Enable/disable backup cost calculations
    'enable_storage_tiering': True,  # Intelligent tiering for cost savings
    
    # Production retention policy
    'production': {
        'daily_retention_days': 7,
        'weekly_retention_weeks': 2,
        'monthly_retention_months': 12
    },
    
    # Pre-production retention policy
    'pre_production': {
        'daily_retention_days': 3,
        'weekly_retention_weeks': 1,
        'monthly_retention_months': 0
    },
    
    # Storage optimization
    'compression_ratio': 0.7,  # 70% compression
    'deduplication_ratio': 0.5,  # 50% deduplication
    'incremental_ratio': 0.2,  # 20% incremental backup size
    
    # Storage tiering strategy
    'tier_strategy': {
        'daily': {'warm_days': 7, 'archive_days': 7},
        'weekly': {'warm_days': 7, 'archive_days': 7},
        'monthly': {'warm_days': 30, 'archive_days': 60, 'deep_archive_days': 180}
    },
    
    # EKS backup configuration
    'backup_eks': True,
    'eks_stateful_percentage': 0.30,  # 30% of workloads are stateful
    'eks_avg_storage_per_workload_gb': 100,
    
    # Environment detection
    'environment_detection': {
        'enabled': True,
        'prod_patterns': ['prod', 'production', 'prd'],
        'preprod_patterns': ['dev', 'test', 'uat', 'staging', 'qa', 'development']
    },
    
    # Pricing
    'use_pricing_api': True,  # Use AWS Pricing API
    'fallback_rates': {
        'backup_storage_per_gb_month': 0.05,
        's3_glacier_flexible_per_gb_month': 0.0036,
        's3_glacier_deep_per_gb_month': 0.00099
    }
}
```

## AWS Backup Cost Analysis Architecture

### Module: `agents/pricing/backup_pricing.py`

**Core Functions**:

1. **`calculate_backup_costs(vms, region)`**
   - Main entry point for backup cost calculation
   - Detects environment for each VM (production vs pre-production)
   - Calculates costs with intelligent storage tiering
   - Returns total costs, environment breakdown, and savings

2. **`calculate_eks_backup_costs(eks_vms, region)`**
   - Calculates backup costs for EKS persistent volumes
   - Assumes 30% stateful workloads (configurable)
   - 100GB average storage per workload (configurable)
   - Uses production retention policy

3. **`detect_vm_environment(vm)`**
   - Automatic environment detection from:
     - VM names: `prod`, `production`, `prd` → Production
     - VM names: `dev`, `test`, `uat`, `staging` → Pre-Production
     - Folders/clusters (RVTools)
     - Explicit environment field (IT Inventory)
   - Default: Production (safer for cost estimation)

4. **`calculate_tiered_storage_costs()`**
   - Implements intelligent storage tiering strategy
   - Daily backups: Warm (7d) → Archive
   - Weekly backups: Warm (7d) → Archive
   - Monthly backups: Warm (30d) → Archive (60d) → Deep Archive
   - Calculates savings vs all-warm storage

5. **`get_backup_pricing_from_api(region)`**
   - Real-time pricing from AWS Price List API
   - Regional pricing multipliers
   - Fallback rates if API unavailable
   - LRU cache for performance

### Integration Points

**1. AWS Pricing Calculator** (`agents/pricing/aws_pricing_calculator.py`)
```python
def calculate_arr_from_dataframe(df):
    # ... EC2/EBS/Transfer calculations ...
    
    # Calculate backup costs
    from agents.pricing.backup_pricing import calculate_backup_costs
    backup_costs = calculate_backup_costs(backup_vms, region)
    
    # Add to totals
    total_monthly_with_backup = total_monthly + backup_costs['total_monthly']
    
    return {
        'summary': {
            'backup_monthly_cost': backup_costs['total_monthly'],
            'total_monthly_with_backup': total_monthly_with_backup,
            ...
        },
        'backup_costs': backup_costs
    }
```

**2. IT Inventory Pricing** (`agents/pricing/it_inventory_pricing.py`)
```python
def calculate_it_inventory_arr(inventory_file, region):
    # ... EC2 and RDS calculations ...
    
    # Calculate backup costs for servers
    from agents.pricing.backup_pricing import calculate_backup_costs
    backup_costs = calculate_backup_costs(backup_vms, region)
    
    # Add to totals
    total_monthly = ec2_monthly + rds_monthly + backup_costs['total_monthly']
    
    return {
        'backup': backup_costs,
        'summary': {
            'backup_monthly': backup_costs['total_monthly'],
            ...
        }
    }
```

**3. EKS Analysis** (`agents/core/aws_business_case.py`)
```python
# After EKS cost calculation
from agents.pricing.backup_pricing import calculate_eks_backup_costs
eks_backup_costs = calculate_eks_backup_costs(eks_vms, region)

# Add to EKS totals
eks_costs['backup_monthly'] = eks_backup_costs['monthly_cost']
eks_costs['monthly_avg'] += eks_backup_costs['monthly_cost']
```

**4. Excel Export** (`agents/export/excel_export.py`)
```python
def create_vm_to_ec2_mapping_excel(detailed_df, backup_costs):
    # Add "Backup Monthly Cost ($)" column
    # Create Backup Summary sheet
    # Update Summary sheet with cost breakdown
```

**5. Business Case Prompts** (`agents/core/multi_stage_business_case.py`)
```python
# Exact costs format includes backup costs
BACKUP COST DETAILS
  Production VMs: X VMs, $Y/month
  Pre-Production VMs: X VMs, $Y/month
  Storage Tiering Savings: $Z (N%)
  Retention: Daily (7d), Weekly (2w), Monthly (1yr)
```

### Storage Tiering Strategy

**Warm Storage** (AWS Backup):
- Cost: $0.05/GB-month
- Duration: Days 1-7 for daily/weekly, Days 1-30 for monthly
- Use case: Recent backups, fast recovery

**Archive Storage** (S3 Glacier Flexible):
- Cost: $0.0036/GB-month (93% cheaper)
- Duration: Days 8-90
- Use case: Medium-term retention

**Deep Archive** (S3 Glacier Deep):
- Cost: $0.00099/GB-month (98% cheaper)
- Duration: Days 90+ (optional, disabled by default)
- Use case: Long-term compliance

**Savings Example** (100 VMs, 500GB average):
```
Without Tiering: 17,500 GB × $0.05 = $875/month
With Tiering:
  - Warm (7d):     2,500 GB × $0.05    = $125/month
  - Archive (83d): 12,500 GB × $0.0036 = $45/month
  - Deep (180d):   2,500 GB × $0.00099 = $2.50/month
Total: $172.50/month
Savings: $702.50/month (80%)
```

### Data Flow

```
Input: VMs/Servers with storage data
    ↓
Environment Detection
    ├─ Production VMs (prod, production, prd)
    └─ Pre-Production VMs (dev, test, uat, staging)
    ↓
Retention Policy Selection
    ├─ Production: Daily (7d), Weekly (2w), Monthly (1yr)
    └─ Pre-Production: Daily (3d), Weekly (1w), No monthly
    ↓
Storage Calculation
    ├─ Apply compression (70%)
    ├─ Apply deduplication (50%)
    └─ Calculate backup storage per retention period
    ↓
Tiering Strategy
    ├─ Warm storage (recent backups)
    ├─ Archive storage (medium-term)
    └─ Deep archive (long-term, optional)
    ↓
Cost Calculation
    ├─ Per-tier costs
    ├─ Total monthly/annual costs
    └─ Savings vs all-warm storage
    ↓
Output: Backup costs integrated into all reports
```

### Excel Export Structure

**VM to EC2 Mapping Sheet**:
- Column 26: "Backup Monthly Cost ($)" - Per-VM backup cost
- Column 27-28: Total costs including backup

**Summary Sheet**:
- Cost Breakdown section:
  - Compute & Storage Monthly
  - Backup Monthly
  - Total Monthly

**Backup Summary Sheet** (NEW):
- Overall backup costs with tiering savings
- Production environment:
  - VM count, storage, costs
  - Retention policy
  - Storage tier breakdown
- Pre-production environment:
  - VM count, storage, costs
  - Retention policy
  - Storage tier breakdown

## Performance Characteristics

### Parallel Execution Benefits
- Phase 1: 4 agents run simultaneously (~30-40 seconds)
- Phase 2: 3 agents run simultaneously (~40-50 seconds)
- Phase 3: 1 agent (~25-30 seconds)
- Phase 4: 7 sections generated sequentially (~2-3 minutes)

**Total Time**: ~3-4 minutes for complete business case

### Token Usage
- Individual agents: 2,000-8,000 tokens per agent
- Section generation: 400-600 words per section
- Total document: ~5,000-8,000 words

## Critical Validation Rules

### VM Count Consistency
- All sections must show same VM count
- Powered-on VMs only (powered-off excluded)
- Instance distribution must sum to total VM count

### Financial Consistency
- Executive Summary costs must match Cost Analysis
- All cost figures from same source (pricing tool)
- No estimation or recalculation allowed

### Data Accuracy
- Use actual numbers from analysis (no placeholders)
- No approximations (e.g., "51 VMs" not "approximately 50")
- No meta-commentary in output

## Related Documentation

**Core Documentation**
- `README.md` - Project overview
- `SETUP_GUIDE.md` - Installation and setup
- `BEDROCK_GUARDRAILS_GUIDE.md` - Guardrails setup

**EKS Implementation**
- `EKS_PRICING_DESIGN.md` - Complete design specification
- `WHY_EKS_REQUIRES_LINUX.md` - Technical explanation
- `docs/history/PYTHON_BASED_RECOMMENDATION_IMPLEMENTED.md` - Implementation details

**Wave Planning & IT Inventory Enhancements (NEW - January 2026)**
- `WAVE_PLANNING_IMPLEMENTATION.md` - Complete wave planning implementation guide
- `DEPENDENCY_WAVE_PLANNING_COMPLETE.md` - Quick reference for wave planning
- `IT_INVENTORY_DEPENDENCY_GAP.md` - Gap analysis (resolved)
- `IT_INVENTORY_EKS_ENHANCEMENT.md` - IT Inventory EKS enhancement guide
- `IT_INVENTORY_ARR_VERIFICATION.md` - IT Inventory ARR verification
- `IMPLEMENTATION_SUMMARY.md` - Summary of all recent implementations

**Additional Resources**
- `docs/history/` - Implementation history and detailed guides
- `tests/README.md` - Testing documentation

## Production Deployment Checklist

### AWS Configuration
- [ ] AWS credentials configured (`aws sts get-caller-identity`)
- [ ] Bedrock access enabled in target region
- [ ] Claude 3 Sonnet model access granted
- [ ] DynamoDB table created (if using persistence)
- [ ] S3 bucket created (if using file storage)
- [ ] IAM permissions configured correctly

### Application Setup
- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Virtual environment created (`./setup.sh`)
- [ ] Dependencies installed (Python + Node)
- [ ] Configuration reviewed (`agents/config/config.py`)
- [ ] Environment variables set (if using S3)

### Testing
- [ ] Test with RVTools input
- [ ] Test with IT Inventory input
- [ ] Test with ATX input
- [ ] Verify Excel exports generated
- [ ] Verify business case output quality
- [ ] Check logs for errors (`output/logs/`)

### Security
- [ ] AWS credentials not hardcoded
- [ ] Sensitive data not in version control
- [ ] Input files stored securely
- [ ] Output files access controlled
- [ ] API endpoints secured (if exposing publicly)
- [ ] Bedrock Guardrails enabled (recommended for production)

### Monitoring
- [ ] CloudWatch billing alerts configured
- [ ] Bedrock usage monitoring enabled
- [ ] Application logs reviewed
- [ ] Error tracking configured

## Version History

### v1.0 (January 2026) - Production Release
- ✅ AWS Price List API integration (EC2 + RDS + EKS)
- ✅ Three infrastructure input types (RVTools, IT Inventory, ATX)
- ✅ **Dependency-based wave planning** from IT Infrastructure Inventory (NEW)
- ✅ **IT Inventory EKS enhancement** - Uses actual server specs (NEW)
- ✅ Python-based EKS recommendation engine (4-tier decision tree)
- ✅ Bedrock Guardrails integration (optional)
- ✅ Smart agent selection (only runs agents for available files)
- ✅ Pre-computed infrastructure summaries (deterministic)
- ✅ Excel exports with detailed cost breakdowns
- ✅ Multi-stage business case generation

---

**Last Updated**: January 2, 2026  
**Version**: 1.0  
**Status**: Active
