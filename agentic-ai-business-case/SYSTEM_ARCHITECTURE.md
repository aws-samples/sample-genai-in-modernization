# Business Case Generator - System Architecture

## Overview

This document describes the complete flow of how the AWS Migration Business Case Generator works, from UI request to final document generation.

---

## 🔄 Recent Updates (December 2025)

### AWS Price List API Integration

All pricing calculations now use **real-time AWS Price List API** for 100% accuracy:

**EC2 Pricing** (`agents/aws_pricing_calculator.py`):
- `get_ec2_price_by_term()`: Supports On-Demand, 1-Year RI, 3-Year RI, Compute Savings Plans
- **Default**: 3-Year Compute Savings Plan (~9% cheaper than 3-Year RI)
- Queries AWS Price List API with proper term filters
- LRU cache for performance optimization
- Automatic fallback to hardcoded pricing if API fails
- **Configurable**: Set `pricing_model` in `agents/config.py`

**RDS Pricing** (`agents/aws_pricing_calculator.py`):
- `get_rds_price_from_api()`: All database engines (MySQL, PostgreSQL, Oracle, SQL Server, MariaDB)
- Supports On-Demand, 1-Year RI, 3-Year RI
- LRU cache for performance optimization
- Automatic fallback to hardcoded pricing if API fails

### Three Infrastructure Input Types

**UI enforces ONE input type at a time**:

1. **RVTools** (Highest Priority)
   - Tool: `calculate_exact_aws_arr` in `agents/pricing_tools.py`
   - Uses AWS Price List API for EC2 pricing (all models)
   - Most comprehensive VM-level data
   - Generates Excel output with VM-level costs

2. **IT Infrastructure Inventory** (Medium Priority)
   - Tool: `calculate_it_inventory_arr` in `agents/inventory_analysis.py`
   - Servers tab → EC2 (AWS Price List API)
   - Databases tab → RDS (AWS Price List API)
   - **Dual pricing comparison**: 3-Year EC2 Savings Plan vs 3-Year RI
   - Returns simplified text format (easier for LLM to parse)
   - Generates Excel with comparison sheet showing both pricing options

3. **ATX** (Lowest Priority)
   - Tool: `extract_atx_arr_tool` in `agents/atx_pricing_extractor.py`
   - Extracts pre-calculated costs from ATX Excel
   - ATX uses 1-Year NURI pricing model
   - No Excel generation (ATX already provides output)

### Cost Agent Enhancement

`agent_aws_cost_arr` now has access to all pricing tools:
```python
agent_aws_cost_arr = Agent(
    tools=[
        calculate_exact_aws_arr,        # RVTools → EC2
        calculate_it_inventory_arr,     # IT Inventory → EC2 + RDS
        extract_atx_arr_tool            # ATX → Pre-calculated
    ]
)
```

The agent automatically:
1. Identifies which input type is available
2. Calls the appropriate pricing tool
3. Uses exact numbers from AWS Price List API
4. Generates business case with accurate costs

### Tool Output Format Optimization

**IT Inventory pricing tool now returns simplified text format** instead of nested JSON:
- **Why**: LLMs parse simple text more reliably than complex nested JSON structures
- **Format**: Clear sections with labeled costs (Option 1, Option 2, Savings)
- **Benefit**: Prevents LLM from ignoring specific fields or generating identical costs
- **Implementation**: `calculate_it_inventory_arr()` in `agents/inventory_analysis.py`

Example output:
```
OPTION 1: 3-Year EC2 Instance Savings Plan
Total Monthly Cost: $34,567.89

OPTION 2: 3-Year Reserved Instances
Total Monthly Cost: $38,029.35

SAVINGS: Option 1 saves $3,461.46/month (9.1%)
```

---

## 📊 Complete Business Case Generation Flow

### 1. UI REQUEST (Frontend → Backend)

**File**: `ui/backend/app.py`

```
User clicks "Generate Business Case" in UI
    ↓
POST /api/generate-business-case
    ↓
Receives: {
    projectName, customerName, region,
    projectDescription, files (RVTools, MRA, etc.)
}
    ↓
Saves files to: input/case-{caseId}/
    ↓
Calls: run_business_case_generation()
```

---

### 2. MAIN ORCHESTRATOR

**File**: `agents/aws_business_case.py`

This is the **main entry point** that orchestrates everything:

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

---

### 3. AGENT GRAPH EXECUTION (Smart Selection + Parallel Processing)

**File**: `agents/aws_business_case.py` (graph builder)

**Smart Agent Selection** (NEW in v1.0):
- System detects which input files are available
- Only adds agents to graph if their input files exist
- Example: If no IT Inventory uploaded, skips `agent_it_analysis`
- Logs show: "✓ FOUND" or "✗ Not found" for each input type
- Active agents tracked in `active_analysis_agents` list

**Execution Order** (with dependencies):

```
PHASE 1 - Initial Analysis (Run in Parallel - Auto-Selected):
├── agent_it_analysis        → IT inventory analysis (if file exists)
├── agent_rv_tool_analysis   → RVTools VMware analysis (if file exists)
├── agent_atx_analysis        → ATX assessment analysis (if file exists)
└── agent_mra_analysis        → MRA readiness analysis (if file exists)

PHASE 2 - Synthesis (Wait for ALL active Phase 1 agents):
├── current_state_analysis    → Synthesizes all Phase 1 results
├── agent_migration_strategy  → 7Rs strategy recommendations
└── agent_aws_cost_arr        → Cost calculations (calls pricing tools)

PHASE 3 - Planning (Wait for Phase 2):
└── agent_migration_plan      → Roadmap and timeline

PHASE 4 - Final Document (Wait for Phase 3):
└── Multi-stage business case generation
```

**Key Improvement**: Phase 2 agents now wait for only the **active** Phase 1 agents (not all 4), making execution more efficient and preventing unnecessary waiting.

---

### 4. PRE-COMPUTED INFRASTRUCTURE SUMMARIES

**File**: `agents/aws_business_case.py`

To ensure consistent VM/server counts across all sections and avoid LLM caching issues, the system pre-computes infrastructure summaries in Python before agent execution:

**RVTools Pre-Computation** (`get_rvtools_summary_precomputed()`):
```python
1. Read RVTools Excel file directly with pandas
2. Filter to powered-on VMs only
3. Calculate totals: VMs, vCPUs, RAM, Storage
4. Count OS distribution (Windows/Linux/Other)
5. Treat "Other" VMs as Linux for consistency
6. Pass exact numbers to all agents via task context
```

**IT Inventory Pre-Computation** (`get_it_inventory_summary_precomputed()`):
```python
1. Read IT Inventory Servers tab with pandas
2. Calculate totals: Servers, vCPUs, RAM, Storage
3. Count OS distribution (Windows/Linux)
4. Pass exact numbers to all agents via task context
```

**Priority Logic**:
- If RVTools available → Use RVTools summary (most comprehensive)
- Else if IT Inventory available → Use IT Inventory summary
- Else if ATX available → Extract from ATX (pre-calculated by AWS tool)

**Benefits**:
- ✅ Consistent counts across all sections (no discrepancies)
- ✅ Avoids LLM caching issues (exact numbers in prompt)
- ✅ Faster execution (no repeated file parsing)
- ✅ Deterministic results (same input → same output)

**Implementation**:
The pre-computed summary is injected into the agent task as a mandatory section:
```
**PRE-COMPUTED RVTOOLS SUMMARY** (MANDATORY - Use these exact numbers)
- Total VMs for Migration: 51
- Total vCPUs: 204
- Total Memory (GB): 408.0
- Total Storage (TB): 5.1
- Windows VMs: 20
- Linux VMs: 31
```

All agents are instructed to use ONLY these pre-computed values, not to extract numbers from tool outputs or cached responses.

---

### 5. INDIVIDUAL AGENT FILES & THEIR ROLES

#### Analysis Agents:

**1. `agents/rv_tool_analysis.py`**
- Reads RVTools Excel/CSV files
- **Filters to powered-on VMs only** (e.g., 51 out of 212 total)
- Generates VM summary statistics
- Tool: `rv_tool_analysis()`
- **Critical**: Filtering happens here to exclude powered-off VMs
- **Pre-computation**: Main orchestrator calls `get_rvtools_summary_precomputed()` to extract exact counts before agent execution

**2. `agents/mra_analysis.py`**
- Reads MRA PDF documents
- Extracts migration readiness findings
- Tool: `read_file_from_input_dir()`

**3. `agents/atx_analysis.py`**
- Reads ATX assessment files (Excel, PDF, PowerPoint)
- Tools: `read_excel_file()`, `read_pdf_file()`, `read_pptx_file()`

**4. `agents/it_analysis.py`**
- Reads IT inventory files
- Tool: `inventory_analysis()`
- **Pre-computation**: Main orchestrator calls `get_it_inventory_summary_precomputed()` to extract exact server/database counts before agent execution

#### Cost Analysis:

**5. `agents/aws_arr_cost.py`**
- Main cost analysis agent
- Uses prompts from `agents/prompt_library/agent_prompts.py`
- Calls pricing tools from `agents/pricing_tools.py`

**6. `agents/pricing_tools.py`**
- Tool: `calculate_exact_aws_arr()` - RVTools pricing calculator
- Tool: `compare_pricing_models()` - Compares Compute Savings Plan vs Reserved Instances
- Tool: `get_vm_cost_breakdown()` - Single VM cost analysis
- Calls `rv_tool_analysis()` to get filtered VM data
- Uses `agents/aws_pricing_calculator.py` for calculations
- Generates Excel export via `agents/excel_export.py`

**7. `agents/inventory_analysis.py`**
- Tool: `calculate_it_inventory_arr()` - IT Inventory pricing calculator
- Calculates BOTH pricing models: 3-Year EC2 Savings Plan AND 3-Year RI
- Returns simplified text format (not JSON) for better LLM parsing
- Generates comparison Excel with both pricing options
- Uses `agents/it_inventory_pricing.py` for core calculations

**8. `agents/aws_pricing_calculator.py`**
- Class: `AWSPricingCalculator`
- Method: `calculate_arr_from_dataframe()`
- Calculates costs for each VM
- Returns aggregated results with breakdowns

**9. `agents/excel_export.py`**
- Function: `export_vm_to_ec2_mapping()`
- Creates: `output/vm_to_ec2_mapping.xlsx`
- Contains VM-to-EC2 instance mapping with costs

#### Strategy & Planning:

**10. `agents/migration_strategy.py`**
- 7Rs distribution (Rehost, Replatform, Refactor, etc.)
- Wave planning recommendations

**11. `agents/migration_plan.py`**
- Roadmap generation
- Timeline creation with milestones

---

### 6. MULTI-STAGE BUSINESS CASE GENERATION

**File**: `agents/multi_stage_business_case.py`

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
    8. Appendix (from agents/appendix_content.py)
    ↓
Each section:
    - Creates dedicated agent with section-specific prompt
    - Passes all previous agent results as context
    - Generates section content
    - Combines into final document
```

**Section Prompts** (all in `agents/multi_stage_business_case.py`):
- `EXECUTIVE_SUMMARY_PROMPT`
- `CURRENT_STATE_PROMPT`
- `MIGRATION_STRATEGY_PROMPT`
- `COST_ANALYSIS_PROMPT` (dynamic based on TCO config)
- `MIGRATION_ROADMAP_PROMPT`
- `BENEFITS_RISKS_PROMPT`
- `RECOMMENDATIONS_PROMPT`

---

### 7. SUPPORTING FILES

**Configuration:**
- **`agents/config.py`** - System configuration (regions, pricing models, TCO settings)

**Utilities:**
- **`agents/project_context.py`** - Helper functions for case-specific file paths
- **`agents/prompt_library/agent_prompts.py`** - All individual agent prompts
- **`agents/appendix_content.py`** - AWS partner programs content

---

### 8. OUTPUT FILES

```
output/
├── aws_business_case.md          ← Final business case document
├── vm_to_ec2_mapping.xlsx        ← Excel export with VM→EC2 mapping
└── logs/
    └── agent_execution_*.log     ← Execution logs with timestamps
```

---

## 🔄 Simplified Flow Diagram

```
UI (React)
    ↓
ui/backend/app.py (Flask)
    ↓
agents/aws_business_case.py (Main Orchestrator)
    ↓
┌─────────────────────────────────────────┐
│  AGENT GRAPH (Parallel Execution)      │
├─────────────────────────────────────────┤
│  Phase 1: Analysis Agents               │
│  ├─ rv_tool_analysis.py (filters 51 VMs)│
│  ├─ mra_analysis.py                     │
│  ├─ atx_analysis.py                     │
│  └─ it_analysis.py                      │
│                                          │
│  Phase 2: Synthesis                     │
│  ├─ current_state_analysis              │
│  ├─ migration_strategy.py               │
│  └─ aws_arr_cost.py                     │
│      └─ pricing_tools.py                │
│          └─ aws_pricing_calculator.py   │
│              └─ excel_export.py         │
│                                          │
│  Phase 3: Planning                      │
│  └─ migration_plan.py                   │
└─────────────────────────────────────────┘
    ↓
multi_stage_business_case.py
    ↓
Generates 7 sections sequentially
    ↓
output/aws_business_case.md
```

---

## 🎯 Key Points

### Entry Point
- **UI**: `ui/backend/app.py` receives POST request
- **Main Orchestrator**: `agents/aws_business_case.py` coordinates everything

### Parallel Execution
- Phase 1 agents run simultaneously for efficiency
- Dependencies ensure proper data flow between phases

### VM Filtering
- Happens in `rv_tool_analysis.py`
- Filters to powered-on VMs only (e.g., 51 out of 212 total)
- Critical for accurate cost calculations

### Cost Calculation Flow
```
pricing_tools.py
    ↓ calls
rv_tool_analysis() (gets filtered 51 VMs)
    ↓ passes to
aws_pricing_calculator.py
    ↓ calculates costs
excel_export.py (generates Excel)
```

### Final Assembly
- `multi_stage_business_case.py` generates each section
- Each section has dedicated agent with specific prompt
- All sections receive context from previous agent results

### Prompt Storage
- Individual agent prompts: `agents/prompt_library/agent_prompts.py`
- Section prompts: `agents/multi_stage_business_case.py`

---

## 📝 Data Flow Example

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

---

## 🔧 Configuration

### Key Configuration Files

**`agents/config.py`**:
- `USE_DETERMINISTIC_PRICING` - Enable/disable pricing tools
- `TCO_COMPARISON_CONFIG` - TCO comparison settings
- `model_id_claude3_7` - AI model selection
- `MAX_TOKENS_BUSINESS_CASE` - Output token limits

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

---

## 🧪 Testing Individual Components

### Test RVTools Analysis
```bash
python test_rvtools_only.py
```

### Test VM Count Extraction
```bash
python test_vm_count_extraction.py
```

### Test Pricing Calculator
```python
from agents.pricing_tools import calculate_exact_aws_arr
result = calculate_exact_aws_arr('RVTools_Export.xlsx', 'us-east-1')
```

---

## 📊 Performance Characteristics

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

---

## 🔒 Critical Validation Rules

### VM Count Consistency
- All sections must show same VM count (e.g., 51 VMs)
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

---

## 📚 Related Documentation

- `SETUP_GUIDE.md` - Installation and setup
- `PRICING_CONFIGURATION_GUIDE.md` - Pricing configuration
- `EXCEL_EXPORT_DOCUMENTATION.md` - Excel export details
- `README.md` - Project overview

---

---

## ✅ Production Deployment Checklist

Before deploying to production, verify:

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
- [ ] Configuration reviewed (`agents/config.py`)
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

### Monitoring
- [ ] CloudWatch billing alerts configured
- [ ] Bedrock usage monitoring enabled
- [ ] Application logs reviewed
- [ ] Error tracking configured

---

## 🚀 Version History

### v1.0 (December 2025) - Production Release
- ✅ AWS Price List API integration (EC2 + RDS)
- ✅ Three infrastructure input types (RVTools, IT Inventory, ATX)
- ✅ Intelligent pricing tool selection
- ✅ UI enforcement (one input type at a time)
- ✅ Excel exports with detailed cost breakdowns
- ✅ Multi-stage business case generation
- ✅ Deprecated services prevention
- ✅ TCO validation logic

---

**Last Updated**: December 6, 2025  
**Version**: 1.0  
**Status**: Production Ready
