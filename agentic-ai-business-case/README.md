# AWS Migration Business Case Generator

**Version 1.0** | Production Ready

An AI-powered tool that generates comprehensive AWS migration business cases using multi-agent analysis of your infrastructure data.

## What's New in v1.0

✅ **Real-Time AWS Pricing** - AWS Price List API integration for EC2 and RDS (all pricing models)  
✅ **Three Input Types** - RVTools, IT Infrastructure Inventory, or ATX assessments  
✅ **Intelligent Pricing** - Automatic tool selection based on input type  
✅ **Excel Exports** - Detailed cost breakdowns with VM/server-level mapping  
✅ **UI Enforcement** - Only one infrastructure input type allowed at a time

## Features

- **Smart Agent Selection**: Automatically detects available input files and runs only relevant agents
- **Multi-Agent Analysis**: 9 specialized AI agents analyze different aspects of your migration
- **Comprehensive Business Case**: Executive summary, current state, costs, strategy, roadmap, benefits/risks
- **Multiple Data Sources**: RVTools, IT inventory, ATX assessments, MRA reports
- **Cost Analysis**: TCO comparison with validation, 3-year projections, pricing model comparison (Compute Savings Plan vs Reserved Instances)
- **Editable Output**: Edit generated markdown directly in the UI
- **Save & Load**: DynamoDB integration for case persistence with version tracking
- **S3 Storage**: Optional file storage for uploaded documents

## Quick Start

**Get started in 3 commands:**

```bash
# 1. Configure AWS credentials
aws configure

# 2. Run setup script (one-time)
# Optional to store input/output files in s3 bucket
# export S3_BUCKET_NAME=my-custom-bucket-name
./setup.sh

# 3. Start the application
./start-all.sh
```

Access at: `http://localhost:3000`

**For detailed setup instructions, troubleshooting, and manual installation, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

### Prerequisites

- Python 3.8+
- Node.js 16+
- AWS Account with Bedrock access
- AWS credentials configured

### Basic Usage

**Start the application:**
```bash
./start-all.sh
```

**Stop the application:**
```bash
./stop-all.sh
```

**Command-line generator:**
```bash
source venv/bin/activate
python agents/aws_business_case.py
deactivate
```

## Cost Estimation

### AWS Bedrock Costs

The tool uses Amazon Bedrock with Claude 3 Sonnet. Costs vary by input size:

### Pricing Model (Claude 3 Sonnet)

- **Input**: $0.003 per 1K tokens
- **Output**: $0.015 per 1K tokens

**Example Calculation (2,027 VMs - Large Dataset)**:
```
Input:  150,000 tokens × $0.003 = $0.45
Output:  25,000 tokens × $0.015 = $0.38
Total: $0.83 per business case
```

### Claude 3.5 Sonnet (Optional Upgrade)

- **Input**: $0.003 per 1K tokens
- **Output**: $0.015 per 1K tokens
- **Max Tokens**: 8,192 (vs 4,096 for Claude 3)
- **Cost**: ~10-20% higher due to more detailed output
- **Benefit**: Better quality, more comprehensive analysis

### Additional AWS Costs

#### DynamoDB (Optional)
- **Storage**: $0.25 per GB-month
- **Typical**: 100 saved cases = ~50 MB = $0.01/month
- **Reads/Writes**: On-demand pricing, negligible for typical usage

#### S3 (Optional)
- **Storage**: $0.023 per GB-month
- **Typical**: 100 cases × 50 MB = 5 GB = $0.12/month
- **Requests**: ~$0.01/month for typical usage

### Monthly Cost Examples

#### Light Usage (10 business cases/month)
- **Bedrock**: 10 × $1.00 = $10.00
- **DynamoDB**: $0.01
- **S3**: $0.05
- **Total**: ~$10/month

#### Medium Usage (50 business cases/month)
- **Bedrock**: 50 × $1.00 = $50.00
- **DynamoDB**: $0.02
- **S3**: $0.12
- **Total**: ~$50/month

#### Heavy Usage (200 business cases/month)
- **Bedrock**: 200 × $1.00 = $200.00
- **DynamoDB**: $0.05
- **S3**: $0.50
- **Total**: ~$200/month

### Cost Optimization Tips

1. **Use Claude 3 Sonnet** (not 3.5) for standard cases
2. **Filter RVTools data** to powered-on VMs only (already implemented)
3. **Limit MAX_ROWS_RVTOOLS** in config.py (default: 2,500)
4. **Reuse saved cases** instead of regenerating
5. **Use lower temperature** for cost calculations (already set to 0.1)

### Cost Monitoring

Monitor your Bedrock usage:
```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InvocationCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-sonnet-20240229-v1:0 \
  --start-time 2025-11-01T00:00:00Z \
  --end-time 2025-11-30T23:59:59Z \
  --period 86400 \
  --statistics Sum
```

Set up billing alerts:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name bedrock-cost-alert \
  --alarm-description "Alert when Bedrock costs exceed $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

## Input Data Requirements

**For detailed file requirements and formats, see [SETUP_GUIDE.md](SETUP_GUIDE.md#input-files)**

### Required Files

1. **Migration Readiness Assessment** (Markdown, Word, or PDF) - Required
2. **Exactly ONE infrastructure input type** (UI enforces this):
   - **RVTools Export** (Excel/CSV) - VMware environment data, OR
   - **IT Infrastructure Inventory** (Excel) - Servers + Databases, OR
   - **ATX Assessment** (Excel/PDF/PowerPoint) - AWS Transform for VMware

### Optional Files

- Application Portfolio (CSV/Excel) - For more accurate 7Rs recommendations

### Infrastructure Input Types

**RVTools**
- Most comprehensive VM-level data
- Exact vCPU, RAM, storage per VM
- Best for accurate instance type mapping
- Uses AWS Price List API for all pricing models (On-Demand, 1-Year RI, 3-Year RI)
- Generates detailed Excel output with VM-level costs

**IT Infrastructure Inventory**
- Server + Database coverage
- Servers tab → EC2 instances
- Databases tab → RDS instances
- Uses AWS Price List API for EC2 and RDS pricing
- **Dual pricing comparison**: 3-Year EC2 Savings Plan vs 3-Year RI with automatic savings calculation
- Generates Excel output with 5 sheets (Summary, EC2 Details/Summary, RDS Details/Summary)

**ATX**
- Pre-calculated by AWS Transform for VMware tool
- Extracts existing cost calculations
- Fixed pricing model (1-Year NURI)
- Less flexible for what-if scenarios
- No Excel generation (ATX already provides output)

## Architecture

### Multi-Agent System (9 Agents)

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Data Sources                        │
│  RVTools │ IT Inventory │ ATX │ MRA │ Frameworks             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │   Phase 1: Analysis     │
        │  (Parallel Execution)   │
        │  Auto-selected based    │
        │  on uploaded files      │
        └────────────┬────────────┘
                     │
    ┌────────────────┼────────────────┬────────────┐
    │                │                │            │
┌───▼───┐      ┌────▼────┐      ┌───▼────┐  ┌───▼───┐
│  RV   │      │   IT    │      │  ATX   │  │  MRA  │
│ Tools │      │Inventory│      │Analysis│  │       │
└───┬───┘      └────┬────┘      └───┬────┘  └───┬───┘
    │               │                │           │
    └───────────────┼────────────────┴───────────┘
                    │
        ┌───────────▼───────────┐
        │  Phase 2: Synthesis   │
        │ (Conditional Edges)   │
        │  Always runs          │
        └───────────┬───────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼────┐    ┌────▼────┐    ┌────▼────┐
│Current │    │  Cost   │    │Migration│
│ State  │    │Analysis │    │Strategy │
└───┬────┘    └────┬────┘    └────┬────┘
    │              │              │
    └──────────────┼──────────────┘
                   │
        ┌──────────▼──────────┐
        │ Phase 3: Planning   │
        │  Always runs        │
        └──────────┬──────────┘
                   │
            ┌──────▼──────┐
            │  Migration  │
            │    Plan     │
            └──────┬──────┘
                   │
        ┌──────────▼──────────────┐
        │ Phase 4: Multi-Stage    │
        │   Business Case Gen     │
        │  Always runs            │
        └──────────┬──────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┐
    │              │              │              │
┌───▼───┐    ┌────▼────┐    ┌───▼────┐    ┌───▼────┐
│Exec   │    │Current  │    │  Cost  │    │Strategy│
│Summary│    │ State   │    │Analysis│    │        │
└───────┘    └─────────┘    └────────┘    └────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┐
    │              │              │              │
┌───▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│Roadmap │   │Benefits │   │  Recs   │   │Appendix │
│        │   │ & Risks │   │         │   │         │
└────────┘   └─────────┘   └─────────┘   └─────────┘
```

### Key Features

- **Smart Agent Selection**: Only runs agents for available input files (e.g., skips IT Inventory agent if no IT Inventory file uploaded)
- **Parallel Execution**: Phase 1 agents run simultaneously for speed
- **Conditional Edges**: Phase 2 waits for all active Phase 1 agents to complete
- **Multi-Stage Generation**: 7 sections + appendix generated independently
- **Token Optimization**: Each section gets full token budget (8,192 tokens)
- **Deprecated Services Check**: All agents verify services are not deprecated
- **TCO Validation**: Only shows on-prem comparison if AWS demonstrates savings
- **Relative Timeframes**: Uses Week 1-2, Month 1-3 instead of specific dates

## Configuration

For detailed configuration options, see [SETUP_GUIDE.md](SETUP_GUIDE.md#configuration)

### Quick Configuration Reference

**Model Settings (agents/config.py)**

```python
# Model selection
model_id_claude3_7 = "anthropic.claude-3-sonnet-20240229-v1:0"
max_tokens_default = 8192  # Increased for Claude 3.5

# Temperature (lower = more deterministic)
model_temperature = 0.3  # General agents
# Cost agent uses 0.1 for consistency

# Pricing model (default: 3-Year Compute Savings Plan)
pricing_model = '3yr_compute_sp'  # ~9% cheaper than 3yr_no_upfront
# Options: '3yr_compute_sp', '3yr_no_upfront', '1yr_no_upfront', 'on_demand'

# Data limits
MAX_ROWS_RVTOOLS = 2500  # Max VMs to analyze
MAX_ROWS_IT_INVENTORY = 1500
MAX_ROWS_PORTFOLIO = 1000

# Multi-stage generation (recommended)
ENABLE_MULTI_STAGE = True
```

### Cost Calculation Methods

**AWS Pricing (Real-Time API)**:
The tool uses **AWS Price List API** for accurate, real-time pricing:
- **EC2**: All pricing models (On-Demand, 1-Year RI, 3-Year RI, Compute Savings Plans)
- **RDS**: All database engines (MySQL, PostgreSQL, Oracle, SQL Server, MariaDB)
- **Default Pricing**: 3-Year Compute Savings Plan (~9% cheaper than 3-Year RI)
- **Configurable**: Change `pricing_model` in `agents/config.py`
- **Regions**: All AWS regions supported
- **Caching**: LRU cache for performance optimization

**Pricing Tools by Input Type**:
- **RVTools**: `calculate_exact_aws_arr` - EC2 pricing via AWS API
- **IT Inventory**: `calculate_it_inventory_arr` - EC2 + RDS pricing via AWS API
- **ATX**: `extract_atx_arr_tool` - Extracts pre-calculated costs from ATX

**On-Premises TCO** (configurable in `agents/config.py`):
- Hardware: $5,000 per server/year
- VMware licensing: $200 per VM/year
- Windows licensing: $150 per Windows VM/year
- Data center: $1,000 per rack/year
- IT staff: $150,000 per FTE/year (1 FTE per 100 VMs)
- Maintenance: 15% of hardware cost


### Deprecated Services Prevention

The tool automatically avoids recommending deprecated AWS services:
- References: `agents/reference/aws_deprecated_services.md`
- Checks against AWS lifecycle page: https://aws.amazon.com/products/lifecycle/
- Examples avoided: Migration Hub, CodeGuru Reviewer, Cognito Sync, etc.
- Recommends current alternatives: MGN, Amazon Q Developer, AppSync, etc.

### Appendix Content

Every business case includes an appendix with AWS Partner Programs:
- MAP (Migration Acceleration Program)
- OLA (Optimization and Licensing Assessment)
- ISV Workload Migration Program
- VMware Migration Programs
- POC Program
- Additional migration resources

## Troubleshooting

**For comprehensive troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)**

### Quick Fixes

**Setup issues:**
- Run `./setup.sh` again - it's safe to re-run
- Check AWS credentials: `aws sts get-caller-identity`
- Verify Python 3.8+: `python3 --version`
- Verify Node.js 16+: `node --version`

**Runtime issues:**
- Activate virtual environment: `source venv/bin/activate`
- Check logs in `output/logs/` directory
- Restart services: `./stop-all.sh && ./start-all.sh`

**AWS credential errors:**
```bash
aws sso login --profile <profile>
# or
aws configure
```

**boto3/botocore version errors:**
```bash
# Quick fix
./fix-boto3.sh

# Or manually
source venv/bin/activate
python3 -m pip install --upgrade boto3 botocore
```

**6. Deprecated services in output**
- Should not happen - agents check against lifecycle page
- If found, update `agents/reference/aws_deprecated_services.md`
- Report issue for prompt strengthening

**7.
 Specific dates in timelines**
- Should use relative timeframes (Week 1-2, Month 1-3)
- If specific dates appear, check prompt updates were applied
- Relative timeframes make documents evergreen

## Documentation

### Setup & Installation
- **`SETUP_GUIDE.md`** - Comprehensive one-click setup guide
- **`setup.sh`** - Automated setup script
- `ui/DYNAMODB_SETUP.md` - Manual DynamoDB setup instructions
- `ui/S3_STORAGE_SETUP.md` - Manual S3 storage setup instructions

### Agent Configuration
- `agents/reference/aws_deprecated_services.md` - List of deprecated services to avoid
- `agents/reference/DEPRECATED_SERVICES_IMPLEMENTATION.md` - Implementation details
- `agents/appendix_content.py` - AWS Partner Programs appendix content

### UI Documentation
- `ui/UI_REFACTORING_COMPLETE.md` - UI refactoring documentation
- `ui/UI_REFACTORING_PLAN.md` - UI refactoring plan

## Quick Reference: Input Types

| Input Type | Use Case | Pricing Method | Output |
|------------|----------|----------------|--------|
| **RVTools** | VMware environments | AWS Price List API (EC2) | Excel with VM-level costs |
| **IT Inventory** | Servers + Databases | AWS Price List API (EC2 + RDS) - Dual pricing comparison | Excel with 5 sheets + savings analysis |
| **ATX** | Pre-assessed VMware | Extracts ATX calculations | Uses ATX output |

**Note**: UI enforces selecting exactly ONE input type per business case.

## Version Information

**Current Version**: 1.0 (Production Ready)  
**Release Date**: December 2025  
**Python**: 3.8+  
**Node.js**: 16+  
**AWS Services**: Bedrock (Claude 3 Sonnet), DynamoDB (optional), S3 (optional)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review `SETUP_GUIDE.md` for setup issues
3. Review `SYSTEM_ARCHITECTURE.md` for technical details
4. Review documentation files in `agents/reference/` and `ui/`
5. Check AWS Bedrock console for errors
6. Verify AWS credentials: `aws sts get-caller-identity`
7. Check logs in `output/logs/` directory

## License

MIT License - See LICENSE file for details
