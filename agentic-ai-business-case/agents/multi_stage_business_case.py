"""
Multi-stage business case generator
Generates business case in sections to maximize quality and detail
"""
import os
import pandas as pd
import glob
from strands import Agent
from strands.models import BedrockModel
from config import (
    model_id_claude3_7, 
    model_temperature, 
    MAX_TOKENS_BUSINESS_CASE, 
    output_folder_dir_path,
    TCO_COMPARISON_CONFIG
)
from appendix_content import get_appendix


def extract_exact_costs_from_excel():
    """
    Extract exact cost numbers from the Excel file to prevent LLM hallucination
    Handles both IT Inventory and RVTools Excel files
    Returns formatted string with exact costs to inject into context
    """
    try:
        # Try IT Inventory first
        excel_files = glob.glob(os.path.join(output_folder_dir_path, 'it_inventory_aws_pricing_*.xlsx'))
        
        # If no IT Inventory, try RVTools
        if not excel_files:
            excel_files = glob.glob(os.path.join(output_folder_dir_path, 'vm_to_ec2_mapping.xlsx'))
        
        if not excel_files:
            return None
        
        latest_excel = max(excel_files, key=os.path.getmtime)
        
        # Determine file type
        is_it_inventory = 'it_inventory' in os.path.basename(latest_excel)
        
        # Read the Pricing_Comparison sheet
        df = pd.read_excel(latest_excel, sheet_name='Pricing_Comparison' if is_it_inventory else 'Pricing Comparison')
        
        # Extract values (they're in the 'Value' column)
        values = df['Value'].tolist()
        
        if is_it_inventory:
            # IT Inventory format (EC2 + RDS)
            # Parse ALL the values from the Pricing_Comparison sheet
            # Row 0: Total Servers
            # Row 1: Total Databases
            # Row 4: Option 1 EC2 Monthly Cost
            # Row 5: Option 1 RDS Monthly Cost
            # Row 6: Option 1 Total Monthly Cost
            # Row 7: Option 1 Total Annual Cost
            # Row 8: Option 1 3-Year Total Cost
            # Row 9: Option 1 RDS Upfront Fees
            # Row 12: Option 2 EC2 Monthly Cost
            # Row 13: Option 2 RDS Monthly Cost
            # Row 14: Option 2 Total Monthly Cost
            # Row 15: Option 2 Total Annual Cost
            # Row 16: Option 2 3-Year Total Cost
            # Row 17: Option 2 RDS Upfront Fees
            # Row 20: EC2 Monthly Savings
            # Row 21: RDS Monthly Savings
            # Row 22: Total Monthly Savings
            # Row 23: Annual Savings
            # Row 24: 3-Year Savings
            # Row 25: Savings Percentage
            
            total_servers = values[0] if len(values) > 0 else None
            total_databases = values[1] if len(values) > 1 else None
            
            opt1_ec2_monthly = values[4] if len(values) > 4 else None
            opt1_rds_monthly = values[5] if len(values) > 5 else None
            opt1_total_monthly = values[6] if len(values) > 6 else None
            opt1_annual = values[7] if len(values) > 7 else None
            opt1_3year = values[8] if len(values) > 8 else None
            opt1_rds_upfront = values[9] if len(values) > 9 else None
            opt1_3year_incl_upfront = values[10] if len(values) > 10 else None
            
            opt2_ec2_monthly = values[13] if len(values) > 13 else None
            opt2_rds_monthly = values[14] if len(values) > 14 else None
            opt2_total_monthly = values[15] if len(values) > 15 else None
            opt2_annual = values[16] if len(values) > 16 else None
            opt2_3year = values[17] if len(values) > 17 else None
            opt2_rds_upfront = values[18] if len(values) > 18 else None
            opt2_3year_incl_upfront = values[19] if len(values) > 19 else None
            
            ec2_savings = values[22] if len(values) > 22 else None
            rds_savings = values[23] if len(values) > 23 else None
            total_savings = values[24] if len(values) > 24 else None
            annual_savings = values[25] if len(values) > 25 else None
            three_year_savings = values[26] if len(values) > 26 else None
            three_year_savings_incl_upfront = values[27] if len(values) > 27 else None
            savings_pct = values[28] if len(values) > 28 else None
            
            # Calculate migration ramp costs
            from project_context import get_project_info_dict
            project_info = get_project_info_dict()
            
            # Extract timeline from project description
            timeline_months = None
            if 'projectDescription' in project_info:
                desc = project_info['projectDescription'].lower()
                import re
                # Look for patterns like "12 months", "18-month", "24 month"
                timeline_match = re.search(r'(\d+)[\s-]?months?', desc)
                if timeline_match:
                    timeline_months = int(timeline_match.group(1))
            
            # Default to 12 months if not found
            if not timeline_months:
                timeline_months = 12
            
            # Calculate migration ramp
            migration_ramp = calculate_migration_ramp(opt1_total_monthly, timeline_months)
            
            # Format the exact costs string with ALL details
            exact_costs = f"""
================================================================================
EXACT COSTS FROM EXCEL FILE (DO NOT MODIFY THESE NUMBERS)
================================================================================
Total Servers: {total_servers}
Total Databases: {total_databases}

OPTION 1: EC2 Instance SP (3yr) + RDS Partial Upfront (3yr) - RECOMMENDED
  EC2 Monthly Cost: {opt1_ec2_monthly}
  RDS Monthly Cost: {opt1_rds_monthly}
  Total Monthly Cost: {opt1_total_monthly}
  Total Annual Cost (ARR): {opt1_annual}
  3-Year Pricing (Monthly × 36): {opt1_3year}
  RDS Upfront Fees (One-time): {opt1_rds_upfront}
  3-Year Total Cost (incl. upfront): {opt1_3year_incl_upfront}

OPTION 2: Compute SP (3yr) + RDS No Upfront (1yr × 3)
  EC2 Monthly Cost: {opt2_ec2_monthly}
  RDS Monthly Cost: {opt2_rds_monthly}
  Total Monthly Cost: {opt2_total_monthly}
  Total Annual Cost (ARR): {opt2_annual}
  3-Year Pricing (Monthly × 36): {opt2_3year}
  RDS Upfront Fees (One-time): {opt2_rds_upfront}
  3-Year Total Cost (incl. upfront): {opt2_3year_incl_upfront}

SAVINGS (Option 1 vs Option 2)
  EC2 Monthly Savings: {ec2_savings}
  RDS Monthly Savings: {rds_savings}
  Total Monthly Savings: {total_savings}
  Annual Savings: {annual_savings}
  3-Year Savings (monthly only): {three_year_savings}
  3-Year Savings (incl. upfront): {three_year_savings_incl_upfront}
  Savings Percentage: {savings_pct}

MIGRATION COST RAMP (PRE-CALCULATED - USE EXACTLY AS SHOWN)
{migration_ramp}

================================================================================
USE THESE EXACT NUMBERS IN THE COST ANALYSIS SECTION
DO NOT ROUND, MODIFY, OR ESTIMATE - COPY THEM EXACTLY AS SHOWN ABOVE
DO NOT MAKE UP ANY NUMBERS - ALL VALUES ARE PROVIDED ABOVE
THE MIGRATION COST RAMP IS PRE-CALCULATED - COPY IT EXACTLY
================================================================================
"""
        else:
            # RVTools format (EC2-only, no RDS)
            # Row 0: Total VMs
            # Row 3: Option 1 Total Monthly Cost
            # Row 4: Option 1 Total Annual Cost
            # Row 5: Option 1 3-Year Pricing
            # Row 8: Option 2 Total Monthly Cost
            # Row 9: Option 2 Total Annual Cost
            # Row 10: Option 2 3-Year Pricing
            # Row 13: Monthly Savings
            # Row 14: Annual Savings
            # Row 15: 3-Year Savings
            # Row 16: Savings Percentage
            
            total_vms = values[0] if len(values) > 0 else None
            
            opt1_total_monthly = values[3] if len(values) > 3 else None
            opt1_annual = values[4] if len(values) > 4 else None
            opt1_3year = values[5] if len(values) > 5 else None
            
            opt2_total_monthly = values[8] if len(values) > 8 else None
            opt2_annual = values[9] if len(values) > 9 else None
            opt2_3year = values[10] if len(values) > 10 else None
            
            total_savings = values[13] if len(values) > 13 else None
            annual_savings = values[14] if len(values) > 14 else None
            three_year_savings = values[15] if len(values) > 15 else None
            savings_pct = values[16] if len(values) > 16 else None
            
            # Calculate migration ramp costs
            from project_context import get_project_info_dict
            project_info = get_project_info_dict()
            
            # Extract timeline from project description
            timeline_months = None
            if 'projectDescription' in project_info:
                desc = project_info['projectDescription'].lower()
                import re
                # Look for patterns like "12 months", "18-month", "24 month"
                timeline_match = re.search(r'(\d+)[\s-]?months?', desc)
                if timeline_match:
                    timeline_months = int(timeline_match.group(1))
            
            # Default to 12 months if not found
            if not timeline_months:
                timeline_months = 12
            
            # Calculate migration ramp
            migration_ramp = calculate_migration_ramp(opt1_total_monthly, timeline_months)
            
            # Format the exact costs string for RVTools (EC2-only)
            exact_costs = f"""
================================================================================
EXACT COSTS FROM EXCEL FILE (DO NOT MODIFY THESE NUMBERS)
================================================================================
Total VMs: {total_vms}

OPTION 1: 3-Year EC2 Instance Savings Plan - RECOMMENDED
  Total Monthly Cost: {opt1_total_monthly}
  Total Annual Cost (ARR): {opt1_annual}
  3-Year Pricing: {opt1_3year}

OPTION 2: 3-Year Compute Savings Plan
  Total Monthly Cost: {opt2_total_monthly}
  Total Annual Cost (ARR): {opt2_annual}
  3-Year Pricing: {opt2_3year}

SAVINGS (Option 1 vs Option 2)
  Monthly Savings: {total_savings}
  Annual Savings: {annual_savings}
  3-Year Savings: {three_year_savings}
  Savings Percentage: {savings_pct}

MIGRATION COST RAMP (PRE-CALCULATED - USE EXACTLY AS SHOWN)
{migration_ramp}

================================================================================
USE THESE EXACT NUMBERS IN THE COST ANALYSIS SECTION
DO NOT ROUND, MODIFY, OR ESTIMATE - COPY THEM EXACTLY AS SHOWN ABOVE
DO NOT MAKE UP ANY NUMBERS - ALL VALUES ARE PROVIDED ABOVE
THE MIGRATION COST RAMP IS PRE-CALCULATED - COPY IT EXACTLY
================================================================================
"""
        
        return exact_costs
        
    except Exception as e:
        print(f"Warning: Could not extract exact costs from Excel: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_migration_ramp(monthly_cost: float, timeline_months: int) -> str:
    """
    Calculate migration cost ramp based on timeline.
    Returns formatted string with exact costs for each phase.
    
    Args:
        monthly_cost: Total monthly AWS cost (from Option 1)
        timeline_months: Project timeline in months
    
    Returns:
        Formatted string with migration ramp costs
    """
    if not monthly_cost or not timeline_months:
        return ""
    
    # Ensure monthly_cost is a float
    if isinstance(monthly_cost, str):
        monthly_cost = float(monthly_cost.replace('$', '').replace(',', ''))
    
    # Define phase percentages and month ranges based on timeline
    if timeline_months <= 3:
        # 3-month timeline
        phases = [
            ("Month 1", 0.20, monthly_cost * 0.20),
            ("Month 2", 0.50, monthly_cost * 0.50),
            ("Month 3", 1.00, monthly_cost * 1.00)
        ]
        title = "3-Month Migration Cost Ramp"
    elif timeline_months <= 8:
        # 8-month timeline
        phases = [
            ("Months 1-3", 0.30, monthly_cost * 0.30),
            ("Months 4-6", 0.70, monthly_cost * 0.70),
            ("Months 7-8", 1.00, monthly_cost * 1.00)
        ]
        title = "8-Month Migration Cost Ramp"
    elif timeline_months <= 12:
        # 12-month timeline
        phases = [
            ("Months 1-4", 0.30, monthly_cost * 0.30),
            ("Months 5-8", 0.70, monthly_cost * 0.70),
            ("Months 9-12", 1.00, monthly_cost * 1.00)
        ]
        title = "12-Month Migration Cost Ramp"
    elif timeline_months <= 18:
        # 18-month timeline
        phases = [
            ("Months 1-6", 0.30, monthly_cost * 0.30),
            ("Months 7-12", 0.70, monthly_cost * 0.70),
            ("Months 13-18", 1.00, monthly_cost * 1.00)
        ]
        title = "18-Month Migration Cost Ramp"
    else:
        # 24-month timeline
        phases = [
            ("Months 1-8", 0.30, monthly_cost * 0.30),
            ("Months 9-16", 0.70, monthly_cost * 0.70),
            ("Months 17-24", 1.00, monthly_cost * 1.00)
        ]
        title = "24-Month Migration Cost Ramp"
    
    # Format the migration ramp section
    ramp_text = f"""
**{title}**:
"""
    for period, percentage, cost in phases:
        ramp_text += f"- {period}: ${cost:,.2f} ({int(percentage * 100)}% of monthly cost)\n"
    
    return ramp_text.strip()


def create_section_agent(section_prompt):
    """Create an agent for generating a specific section"""
    model = BedrockModel(
        model_id=model_id_claude3_7,
        temperature=model_temperature,
        max_tokens=MAX_TOKENS_BUSINESS_CASE
    )
    return Agent(model=model, system_prompt=section_prompt)

# Section prompts
EXECUTIVE_SUMMARY_PROMPT = """
Generate a comprehensive Executive Summary for the AWS migration business case.

**Input**: You will receive analysis from multiple agents covering current state, costs, strategy, and migration plan.

**CRITICAL - ATX INPUT HANDLING**:
- IF ATX data is present, check for "ATX PPT PRE-COMPUTED SUMMARY" in the context
- IF found, use the Executive Summary content from ATX PowerPoint DIRECTLY
- Extract key points from the ATX Executive Summary and present them
- Use the EXACT numbers from ATX (VM counts, costs, savings percentages)
- DO NOT add information not in the ATX Executive Summary

**CRITICAL - TCO PRESENTATION RULE**:
- ONLY show cost savings metrics if AWS demonstrates lower TCO than on-premises
- If AWS costs are EQUAL or HIGHER, focus on business value and strategic benefits instead
- Do NOT show negative savings or unfavorable cost comparisons

**CRITICAL - AVOID REPETITION**:
- Keep this section HIGH-LEVEL only - detailed numbers will be in later sections
- DO NOT repeat detailed wave structures, timelines, or cost breakdowns
- Focus on KEY takeaways and strategic overview only

**Generate**:
1. Project Overview (use EXACT customer name and project details from PROJECT CONTEXT)
2. Current State Highlights - Use EXACT VM counts from analysis (e.g., "51 virtual machines" not "approximately 50")
   - FOR ATX: Use Assessment Scope numbers (Total VMs, Windows VMs, Linux VMs, Storage)
3. Recommended Approach - STRATEGIC OVERVIEW (e.g., "phased approach over 18 months" without wave details)
   - FOR ATX: Extract approach from ATX Executive Summary if mentioned
4. Key Financial Metrics - SUMMARY ONLY:
   **FOR ATX INPUT**:
   - Use Financial Overview from ATX PPT (Monthly Cost, Annual Cost, 3-Year Cost)
   - Include savings percentage if mentioned in ATX Executive Summary
   - Add note: "Pricing based on [pricing model from ATX]"
   
   **FOR RVTOOLS/IT INVENTORY INPUT**:
   - You will receive EXACT COSTS FROM EXCEL FILE in the context
   - FIRST: Check if it says "Total VMs" (RVTools) or "Total Servers and Total Databases" (IT Inventory)
   
   **IF "Total VMs" (RVTools - EC2 only)**:
   - Use the EXACT values provided for Option 1:
     * Total Monthly AWS Cost
     * Total Annual AWS Cost (ARR)
     * 3-Year Pricing
   - ❌ DO NOT include "RDS Upfront Fees" line
   - ❌ DO NOT include "3-Year Total Cost (incl. upfront)" line
   - Add note: "Pricing based on 3-Year EC2 Instance Savings Plan (Option 1 - Recommended). Alternative 3-Year Compute Savings Plan pricing (Option 2) available in Cost Analysis section."
   
   **IF "Total Servers" AND "Total Databases" (IT Inventory - EC2 + RDS)**:
   - Use the EXACT values provided for Option 1:
     * Total Monthly AWS Cost
     * Total Annual AWS Cost (ARR)
     * 3-Year Pricing
     * RDS Upfront Fees (One-time)
     * 3-Year Total Cost (incl. upfront)
   - Add note: "Pricing based on 3-Year EC2 Instance Savings Plan for EC2 and 3-Year Partial Upfront RI for RDS (Option 1 - Recommended). Alternative pricing (Option 2) available in Cost Analysis section."
   
   - DO NOT use ranges or estimates - use the EXACT numbers provided
   
   **CRITICAL**: Check TCO_ENABLED flag in context:
   - IF TCO_ENABLED=True AND AWS < On-Prem: Include "Break-even: Month X"
   - IF TCO_ENABLED=False OR AWS >= On-Prem: DO NOT include break-even, show business value instead
5. Expected Benefits - TOP 3-4 ONLY (detailed list will be in Benefits section)
   - FOR ATX: Extract benefits from ATX Executive Summary if mentioned
6. Critical Success Factors - TOP 3 ONLY
   - FOR ATX: Extract from ATX Executive Summary if mentioned
7. Timeline Overview - HIGH-LEVEL:
   **CRITICAL - USE ACTUAL PROJECT TIMELINE**:
   - Extract timeline from PROJECT CONTEXT (e.g., "9 months", "18 months", "24 months")
   - Use EXACT timeline in overview (e.g., "9-month phased approach" NOT "18-month")
   - DO NOT use hardcoded timelines - ALWAYS use the actual project timeline
   - Example: If project is 9 months, say "9-month phased approach" NOT "18-month"

**Format**: Markdown, 400-500 words MAX, include key metrics table
**Tone**: Executive-level, strategic, business-focused
**CRITICAL**: 
- Use ACTUAL NUMBERS from analysis - NO placeholders or approximations
- FOR ATX: Use EXACT content from ATX Executive Summary slide
- Financial metrics MUST match source data exactly
- VM counts must be exact (e.g., "51 VMs" not "approximately 50")
- NO meta-commentary - write only the content itself
"""

CURRENT_STATE_PROMPT = """
Generate a concise Current State Analysis section.

**Input**: Analysis from current_state_analysis, IT inventory, RVTools, ATX, and MRA agents.

**CRITICAL - ATX INPUT HANDLING**:
- IF ATX data is present, check for "ATX PPT PRE-COMPUTED SUMMARY" and "Assessment Scope" content
- Use ONLY the numbers from Assessment Scope (Total VMs, Windows VMs, Linux VMs, Storage)
- DO NOT add vCPU or RAM details if not in ATX Assessment Scope
- If data is missing, simply OMIT that field from the table - do not mention it's missing
- DO NOT hallucinate workload types, application details, or technical specifics

**Generate** (very concise):
1. IT Infrastructure Overview with ACTUAL NUMBERS from the analysis:
   - FOR ATX: Use Assessment Scope numbers (Total VMs, Windows/Linux breakdown, Storage)
   - FOR ATX: If vCPUs/RAM not in Assessment Scope, OMIT those rows from the table
   - FOR RVTOOLS/IT INVENTORY: Use complete infrastructure metrics
2. Key Challenges (from ACTUAL analysis findings)
   - FOR ATX: Extract from ATX Executive Summary if mentioned, otherwise OMIT this section
   - DO NOT add challenges not mentioned in source data
3. Technical Debt (from ACTUAL assessment data)
   - FOR ATX: Only include if mentioned in ATX data, otherwise OMIT this section
   - FOR MRA: Use MRA findings
4. Organizational Readiness (from ACTUAL MRA findings)

**Format**: Markdown, 400-500 words MAX, include 1 summary table
**Tone**: Technical but accessible, data-driven
**CRITICAL**: 
- Use ACTUAL numbers from analysis - NO placeholders, examples, or cached data
- FOR ATX: DO NOT hallucinate details not in the PowerPoint
- NO meta-commentary
"""

MIGRATION_STRATEGY_PROMPT = """
🚨🚨🚨 STOP! READ THIS FIRST! 🚨🚨🚨

LOOK FOR "PRE-COMPUTED RVTOOLS SUMMARY" OR "EXACT COSTS FROM EXCEL FILE" IN YOUR CONTEXT.

DOES IT SAY "Total VMs" OR "Total Servers and Total Databases"?

IF "Total VMs" → THIS IS RVTOOLS = EC2 ONLY, NO DATABASES EXIST
  ❌ FORBIDDEN: RDS, Aurora, DynamoDB, database migration, Oracle, SQL Server, MySQL
  ❌ DO NOT write about migrating databases
  ✅ ALLOWED: Lambda, ECS, EKS, Fargate, EC2, Auto Scaling, S3, CloudFront

IF "Total Servers" AND "Total Databases" → THIS IS IT INVENTORY = EC2 + DATABASES
  ✅ ALLOWED: Include database migration strategies

🚨 IF YOU WRITE "RDS" WHEN INPUT SAYS "Total VMs", YOU FAILED 🚨

================================================================================

Generate a concise Migration Strategy section.

**Input**: Analysis from agent_migration_strategy covering 7Rs recommendations.
  
- IF you see "Total Servers" AND "Total Databases" (IT Inventory): Include both EC2 and database strategies

**CRITICAL - TIMELINE REQUIREMENT**: 
- Check PROJECT CONTEXT for migration timeline (e.g., "18 months", "24 months")
- ALL phases and waves MUST fit within this EXACT timeline
- DO NOT exceed the specified duration
- Example for 18 months: Wave 1 (Months 1-6) + Wave 2 (Months 7-12) + Wave 3 (Months 13-18) = 18 months
- Example for 24 months: Wave 1 (Months 1-8) + Wave 2 (Months 9-16) + Wave 3 (Months 17-24) = 24 months

**CRITICAL - DEPRECATED SERVICES**: Ensure all AWS service recommendations are current and NOT deprecated. Reference: https://aws.amazon.com/products/lifecycle/

**Generate** (very concise):
1. Recommended Approach (1 paragraph) - mention the EXACT timeline from PROJECT CONTEXT
2. 7Rs Distribution (well-formatted table with actual numbers or percentages - NO "TBD" values. If exact numbers unavailable, use reasonable estimates based on VM analysis)
3. Wave Planning (brief, 2-3 sentences) - waves MUST fit within project timeline
4. Quick Wins (bullet points, 3-5 items)
   - FOR RVTOOLS (Total VMs): Focus on EC2/compute quick wins ONLY (Lambda, Fargate, ECS, EKS, Auto Scaling)
   - ❌ DO NOT mention: RDS, Aurora, DynamoDB, database migration, database consolidation
   - FOR IT INVENTORY (Total Servers + Databases): Include both compute and database quick wins

**❌ DO NOT INCLUDE**:
- Cost Analysis (this will be in a separate dedicated section)
- Cost estimates or ranges
- TCO comparisons
- Financial metrics
- Migration cost estimates

**Format**: Markdown, 400-500 words MAX, proper tables and bullets
**Tone**: Strategic, practical, actionable
**CRITICAL**: NO meta-commentary - write only the content itself. RESPECT the project timeline.
"""

def get_cost_analysis_prompt():
    """Generate cost analysis prompt based on TCO config"""
    tco_enabled = TCO_COMPARISON_CONFIG.get('enable_tco_comparison', False)
    
    if tco_enabled:
        return """
🚨🚨🚨 MANDATORY FIRST STEP - READ THIS BEFORE ANYTHING ELSE 🚨🚨🚨

LOOK AT THE "EXACT COSTS FROM EXCEL FILE" SECTION IN YOUR CONTEXT.

QUESTION: Does it say "Total VMs" OR does it say "Total Servers" and "Total Databases"?

IF "Total VMs" → RVTools input = EC2 ONLY, NO RDS, NO DATABASES
  ❌ FORBIDDEN: Never write "RDS", "database" (in cost context), "upfront", "+ RDS"
  ✅ ALLOWED: Only write "EC2", "EBS", "Storage", "Compute"

IF "Total Servers" AND "Total Databases" → IT Inventory = EC2 + RDS
  ✅ ALLOWED: You can mention RDS and databases

🚨 IF YOU WRITE "RDS" WHEN INPUT SAYS "Total VMs", YOU COMPLETELY FAILED 🚨

================================================================================

Generate a concise Cost Analysis and TCO section.

**Input**: Analysis from agent_aws_cost_arr covering AWS costs and TCO.

**CRITICAL - ATX INPUT HANDLING**:
- IF ATX data is present, check for "ATX PPT PRE-COMPUTED SUMMARY" and "Financial Overview" content
- IF found, use the Financial Overview content from ATX PowerPoint AS-IS
- Present the ATX financial data exactly as provided in the PowerPoint
- Include any cost breakdowns, savings percentages, or comparisons mentioned in ATX
- DO NOT add TCO calculations unless explicitly in the ATX Financial Overview
- DO NOT modify or reformat the ATX financial content

**CRITICAL - DEPRECATED SERVICES**: Do NOT include any deprecated or end-of-life AWS services in cost analysis. Only include current, actively supported services. Reference: https://aws.amazon.com/products/lifecycle/

**CRITICAL - TCO VALIDATION RULE**:
- ONLY show on-premises TCO comparison if AWS demonstrates cost savings (AWS < On-Prem)
- If AWS costs are EQUAL or HIGHER than on-premises, SKIP the TCO comparison table
- Instead, focus on business value: agility, innovation, scalability, reduced technical debt
- Emphasize strategic advantages and operational benefits over pure cost comparison

**CRITICAL - COST NUMBERS MUST BE EXACT**:
Before generating this section, the system will extract exact costs from the Excel file and provide them to you.
You MUST use these exact numbers - DO NOT modify, round, or estimate them.

**Generate** (very concise):

**🚨 FIRST: CHECK INPUT TYPE 🚨**
Look at the "EXACT COSTS FROM EXCEL FILE" section you received:
- Does it mention "ATX PPT PRE-COMPUTED SUMMARY"? → ATX INPUT (use ATX section below)
- Does it say "Total Servers" and "Total Databases"? → IT INVENTORY INPUT (use IT Inventory section below)
- Does it say "Total VMs" ONLY? → RVTOOLS INPUT (use RVTools section below)

**FOR ATX INPUT ONLY** (if "ATX PPT PRE-COMPUTED SUMMARY" is present):
1. Financial Overview (from ATX PowerPoint) - Present AS-IS:
   - Include the complete Financial Overview content from ATX
   - Use EXACT numbers from ATX (monthly, annual, 3-year costs)
   - Include any savings percentages or comparisons mentioned
   - Add any assumptions or notes from ATX Financial Overview slide
   - DO NOT add TCO comparison unless in ATX data
   - DO NOT modify the ATX financial content

**FOR RVTOOLS/IT INVENTORY INPUT** (if no ATX data):

**🚨 CRITICAL FIRST STEP - DETECT INPUT TYPE 🚨**:
BEFORE writing anything, CHECK the exact costs section you received:
- Does it say "Total Servers" and "Total Databases"? → IT Inventory (has EC2 + RDS)
- Does it say "Total VMs" ONLY? → RVTools (EC2 ONLY, NO RDS EXISTS)

IF RVTOOLS (Total VMs only):
- ❌ DO NOT mention RDS anywhere
- ❌ DO NOT mention databases in cost context
- ❌ DO NOT mention upfront fees
- ❌ DO NOT add "+ RDS" to option titles
- ❌ DO NOT make up RDS cost breakdowns
- ✅ ONLY mention EC2, EBS, Storage, Compute

1. AWS Cost Summary - Show BOTH pricing options:
   
   **CRITICAL - YOU WILL RECEIVE EXACT COST NUMBERS**:
   The system will provide you with ALL exact cost numbers from the Excel file.
   You MUST use these EXACT numbers - DO NOT modify, round, estimate, or make up ANY numbers.
   
   **FOR IT INVENTORY (EC2 + RDS) - Use this format if "Total Databases" is in exact costs**:
   
   **Option 1: EC2 Instance SP (3yr) + RDS Partial Upfront (3yr) - RECOMMENDED**
   - EC2 Monthly Cost: [from exact costs]
   - RDS Monthly Cost: [from exact costs]
   - Total Monthly AWS Cost: [from exact costs]
   - Total Annual AWS Cost (ARR): [from exact costs]
   - 3-Year Pricing: [from exact costs]
   - RDS Upfront Fees (One-time): [from exact costs]
   - 3-Year Total Cost (incl. upfront): [from exact costs]
   - Note: "Based on 3-Year EC2 Instance Savings Plan for EC2 and 3-Year Partial Upfront RI for RDS"
   
   **Option 2: Compute SP (3yr) + RDS No Upfront (1yr × 3)**
   - EC2 Monthly Cost: [from exact costs]
   - RDS Monthly Cost: [from exact costs]
   - Total Monthly AWS Cost: [from exact costs]
   - Total Annual AWS Cost (ARR): [from exact costs]
   - 3-Year Pricing: [from exact costs]
   - RDS Upfront Fees (One-time): [from exact costs]
   - 3-Year Total Cost (incl. upfront): [from exact costs]
   - Note: "Based on 3-Year Compute Savings Plan for EC2 and 1-Year No Upfront RI (renewed 3 times) for RDS"
   
   **Cost difference vs Option 1**: 
   - Monthly Savings: [from exact costs]
   - Annual Savings: [from exact costs]
   - 3-Year Savings: [from exact costs]
   - Savings Percentage: [from exact costs]
   
   **FOR RVTOOLS (EC2 ONLY) - Use this EXACT format if "Total VMs" is in exact costs**:
   
   🚨 REMINDER: If you see "Total VMs", DO NOT write "RDS", "database", "upfront", "+ RDS" 🚨
   
   **Option 1: 3-Year EC2 Instance Savings Plan - RECOMMENDED**
   - Total Monthly AWS Cost: [copy exact value]
   - Total Annual AWS Cost (ARR): [copy exact value]
   - 3-Year Pricing: [copy exact value]
   - Note: Based on 3-Year EC2 Instance Savings Plan
   
   **Option 2: 3-Year Compute Savings Plan** 
   - Total Monthly AWS Cost: [copy exact value]
   - Total Annual AWS Cost (ARR): [copy exact value]
   - 3-Year Pricing: [copy exact value]
   - Note: Based on 3-Year Compute Savings Plan
   - Cost difference vs Option 1: 
     - Monthly Savings: [copy exact value]
     - Annual Savings: [copy exact value]
     - 3-Year Savings: [copy exact value]
     - Savings Percentage: [copy exact value]
   
   **Cost Breakdown (Option 1 Pricing)**:
   - Compute (EC2): [calculate from monthly cost if needed]
   - Storage (EBS): [calculate from monthly cost if needed]
   - Cost per VM average: [calculate from monthly cost / VM count]
   
   ❌ DO NOT include:
   - RDS or database costs
   - Upfront fees
   - Any cost components not in exact costs
   
2. **Assumptions** (brief section showing key assumptions used in cost modeling):
   - Peak CPU Utilization: 25%
   - Peak Memory Utilization: 60%
   - Storage Utilization (if missing data): 50%
   - Default Provisioned Storage (if missing data): 500 GiB
   
3. **IF AWS < On-Prem**: Include On-Premises TCO Calculation Methodology and comparison table (use Option 1/EC2 Instance Savings Plan pricing)
4. **IF AWS >= On-Prem**: Skip TCO comparison, focus on business value and strategic benefits
5. Migration Cost Ramp (table showing gradual AWS cost increase as workloads migrate - use project timeline from PROJECT CONTEXT)
6. Cost Optimization opportunities (bullet points)
7. **IF AWS < On-Prem**: Break-Even Analysis (1 paragraph)
8. **IF AWS >= On-Prem**: Business Value Justification (agility, innovation, time-to-market, reduced operational complexity)

**CRITICAL REQUIREMENTS FOR DETERMINISTIC CALCULATIONS**:
- Show BOTH pricing options: 
  * Option 1 (Recommended): "EC2 Instance SP (3yr) + RDS Partial Upfront (3yr)"
  * Option 2: "Compute SP (3yr) + RDS No Upfront (1yr × 3)"
- Use the EXACT cost calculations from the cost analysis provided - DO NOT recalculate
- Ensure ALL cost figures are CONSISTENT throughout the section (don't show $6.2M in one place and $516K in another)
- If cost analysis shows "Year 1 AWS: $X", use that EXACT figure - don't round or estimate
- On-premises costs should be HIGHER than AWS costs
- Explain RDS pricing difference: 3-year Partial Upfront (lower monthly, requires upfront payment) vs 1-year No Upfront (higher monthly, no upfront payment)
- **MIGRATION COST RAMP**: Use the ACTUAL project timeline from PROJECT CONTEXT (e.g., 3 months, 12 months, 18 months, 24 months)
  * For 3 months: Month 1 (20%), Month 2 (50%), Month 3 (100%)
  * For 12 months: Months 1-4 (30%), Months 5-8 (70%), Months 9-12 (100%)
  * For 18 months: Months 1-6 (30%), Months 7-12 (70%), Months 13-18 (100%)
  * For 24 months: Months 1-8 (30%), Months 9-16 (70%), Months 17-24 (100%)
  * Title should match timeline: "3-Month Migration Cost Ramp" or "12-Month Migration Cost Ramp" or "18-Month Migration Cost Ramp"
  * **CALCULATION**: Monthly cost × percentage (e.g., $2,676.60 × 0.30 = $803.00, NOT $2,676.60 × 4 months)
- Use actual VM counts and specs from the analysis
- Include cost breakdown by service (Compute, Storage, Database, Networking)
- Show calculation basis with actual numbers from the analysis

**CRITICAL - OS DISTRIBUTION COUNTS**:
- SEARCH for "PRE-COMPUTED RVTOOLS SUMMARY" in the context
- Use ONLY the Windows VMs and Linux VMs counts from that summary
- Example: If summary shows "Windows VMs: 781" and "Linux VMs: 1246", use EXACTLY those numbers
- These counts are consistent with pricing calculator (Other VMs are treated as Linux)

**Format**: Markdown with proper formatting:
- Use proper table syntax with alignment (| Column | Column |)
- Clear section headers (###)
- Well-formatted tables with borders
- 500-600 words MAX

**Tone**: Financial, analytical, data-driven showing AWS cost advantage
**CRITICAL**: Stay under 600 words. Ensure cost consistency and proper table formatting.
"""
    else:
        return """
🚨🚨🚨 MANDATORY FIRST STEP - READ THIS BEFORE ANYTHING ELSE 🚨🚨🚨

LOOK AT THE "EXACT COSTS FROM EXCEL FILE" SECTION IN YOUR CONTEXT.

QUESTION: Does it say "Total VMs" OR does it say "Total Servers" and "Total Databases"?

IF "Total VMs" → RVTools input = EC2 ONLY, NO RDS, NO DATABASES
  ❌ FORBIDDEN: Never write "RDS", "database" (in cost context), "upfront", "+ RDS"
  ✅ ALLOWED: Only write "EC2", "EBS", "Storage", "Compute"

IF "Total Servers" AND "Total Databases" → IT Inventory = EC2 + RDS
  ✅ ALLOWED: You can mention RDS and databases

🚨 IF YOU WRITE "RDS" WHEN INPUT SAYS "Total VMs", YOU COMPLETELY FAILED 🚨

================================================================================

Generate a concise Cost Analysis section (TCO COMPARISON DISABLED).

**Input**: Analysis from agent_aws_cost_arr covering AWS costs.

**CRITICAL - ATX INPUT HANDLING**:
- IF ATX data is present, check for "ATX PPT PRE-COMPUTED SUMMARY" and "Financial Overview" content
- IF found, use the Financial Overview content from ATX PowerPoint AS-IS
- Present the ATX financial data exactly as provided in the PowerPoint
- Include any cost breakdowns, savings percentages, or comparisons mentioned in ATX
- DO NOT add information not in the ATX Financial Overview
- DO NOT modify or reformat the ATX financial content

**CRITICAL - TCO DISABLED**: 
- DO NOT include on-premises cost calculations
- DO NOT show TCO comparison tables
- DO NOT show break-even analysis
- DO NOT mention cost savings vs on-premises
- DO NOT calculate or reference on-premises infrastructure costs
- Focus ONLY on AWS costs and business value

**CRITICAL - DEPRECATED SERVICES**: Do NOT include any deprecated or end-of-life AWS services in cost analysis. Only include current, actively supported services.

**Generate** (very concise):

**🚨 FIRST: CHECK INPUT TYPE 🚨**
Look at the "EXACT COSTS FROM EXCEL FILE" section you received:
- Does it mention "ATX PPT PRE-COMPUTED SUMMARY"? → ATX INPUT (use ATX section below)
- Does it say "Total Servers" and "Total Databases"? → IT INVENTORY INPUT (use IT Inventory section below)
- Does it say "Total VMs" ONLY? → RVTOOLS INPUT (use RVTools section below)

**FOR ATX INPUT ONLY** (if "ATX PPT PRE-COMPUTED SUMMARY" is present):
1. Financial Overview (from ATX PowerPoint) - Present AS-IS:
   - Include the complete Financial Overview content from ATX
   - Use EXACT numbers from ATX (monthly, annual, 3-year costs)
   - Include any savings percentages or comparisons mentioned
   - Add any assumptions or notes from ATX Financial Overview slide
   - DO NOT add TCO comparison
   - DO NOT modify the ATX financial content

**FOR RVTOOLS/IT INVENTORY INPUT** (if no ATX data):

**🚨 CRITICAL FIRST STEP - DETECT INPUT TYPE 🚨**:
BEFORE writing anything, CHECK the exact costs section you received:
- Does it say "Total Servers" and "Total Databases"? → IT Inventory (has EC2 + RDS)
- Does it say "Total VMs" ONLY? → RVTools (EC2 ONLY, NO RDS EXISTS)

IF RVTOOLS (Total VMs only):
- ❌ DO NOT mention RDS anywhere
- ❌ DO NOT mention databases in cost context
- ❌ DO NOT mention upfront fees
- ❌ DO NOT add "+ RDS" to option titles
- ❌ DO NOT make up RDS cost breakdowns
- ✅ ONLY mention EC2, EBS, Storage, Compute

1. AWS Cost Summary - Show BOTH pricing options:
   
   **FOR IT INVENTORY (EC2 + RDS) - Use this format if "Total Databases" is in exact costs**:
   
   **Option 1: EC2 Instance SP (3yr) + RDS Partial Upfront (3yr) - RECOMMENDED**
   - Total Monthly AWS Cost
   - Total Annual AWS Cost (ARR)
   - 3-Year Pricing: Monthly × 36 months
   - RDS Upfront Fees (One-time): Show if applicable
   - 3-Year Total Cost (incl. upfront): 3-Year Pricing + RDS Upfront Fees
   - Note: "Based on 3-Year EC2 Instance Savings Plan for EC2 and 3-Year Partial Upfront RI for RDS"
   
   **Option 2: Compute SP (3yr) + RDS No Upfront (1yr × 3)**
   - Total Monthly AWS Cost
   - Total Annual AWS Cost (ARR)
   - 3-Year Pricing: Monthly × 36 months
   - RDS Upfront Fees (One-time): Show if applicable (typically $0 for No Upfront)
   - 3-Year Total Cost (incl. upfront): 3-Year Pricing + RDS Upfront Fees
   - Note: "Based on 3-Year Compute Savings Plan for EC2 and 1-Year No Upfront RI (renewed 3 times) for RDS"
   - Cost difference vs Option 1: Show savings amount and breakdown (EC2 + RDS)
   
   **FOR RVTOOLS (EC2 ONLY) - Use this EXACT format if "Total VMs" is in exact costs**:
   
   🚨 REMINDER: If you see "Total VMs", DO NOT write "RDS", "database", "upfront", "+ RDS" 🚨
   
   **Option 1: 3-Year EC2 Instance Savings Plan - RECOMMENDED**
   - Total Monthly AWS Cost: [copy exact value]
   - Total Annual AWS Cost (ARR): [copy exact value]
   - 3-Year Pricing: [copy exact value]
   - Note: Based on 3-Year EC2 Instance Savings Plan
   
   **Option 2: 3-Year Compute Savings Plan** 
   - Total Monthly AWS Cost: [copy exact value]
   - Total Annual AWS Cost (ARR): [copy exact value]
   - 3-Year Pricing: [copy exact value]
   - Note: Based on 3-Year Compute Savings Plan
   - Cost difference vs Option 1: 
     - Monthly Savings: [copy exact value]
     - Annual Savings: [copy exact value]
     - 3-Year Savings: [copy exact value]
     - Savings Percentage: [copy exact value]
   
   **Cost Breakdown** (use Option 1/EC2 Instance Savings Plan pricing):
   - Breakdown by service (Compute, Storage) - ❌ NO "Database" or "RDS"
   - Breakdown by instance type (ONLY if provided in cost analysis - DO NOT make up instance counts)
   - Cost per VM average
   
   **CRITICAL - INSTANCE DISTRIBUTION**:
   - ONLY include instance types explicitly mentioned in the cost analysis
   - Instance counts MUST sum to the total VM count (e.g., if 51 VMs total, all instance counts must sum to 51)
   - DO NOT list made-up instance types or counts
   - If instance distribution not provided, SKIP this subsection
   
   **CRITICAL - OS DISTRIBUTION**:
   - SEARCH for "PRE-COMPUTED RVTOOLS SUMMARY" in the context
   - Use ONLY the Windows VMs and Linux VMs counts from that summary
   - Windows + Linux counts MUST equal total migrating VMs from the summary
   - Example: If summary shows "Windows VMs: 781" and "Linux VMs: 1246", use EXACTLY those numbers
   - These counts are consistent with pricing calculator (Other VMs are treated as Linux)
2. **Assumptions** (brief section showing key assumptions used in cost modeling):
   - Peak CPU Utilization: 25%
   - Peak Memory Utilization: 60%
   - Storage Utilization (if missing data): 50%
   - Default Provisioned Storage (if missing data): 500 GiB

3. Migration Cost Ramp
   - **🚨 CRITICAL: MIGRATION RAMP IS PRE-CALCULATED 🚨**
   - The "EXACT COSTS FROM EXCEL FILE" section above includes a "MIGRATION COST RAMP" subsection
   - **COPY IT EXACTLY AS PROVIDED** - Do not calculate, modify, or change any numbers
   - The migration ramp is already calculated with:
     * Correct timeline (matches project timeline)
     * Correct percentages (30%, 70%, 100%)
     * Correct costs (monthly cost × percentage)
   - **DO NOT RECALCULATE** - Just copy the pre-calculated migration ramp from the exact costs section
   - Format: Copy the title and all bullet points exactly as shown
   - DO NOT show on-premises cost reduction
4. Cost Optimization Opportunities (bullet points, 5-7 items)
   - Compute Savings Plans and EC2 Instance Savings Plans (already included in pricing)
   - Right-sizing recommendations
   - Storage optimization
   - Spot instances for suitable workloads
5. Business Value Justification (focus on strategic benefits, NOT cost savings)
   - Agility and faster time-to-market
   - Innovation enablement (AI/ML, analytics, modern services)
   - Reduced technical debt and operational complexity
   - Global scalability and reliability
   - Security and compliance improvements

**CRITICAL REQUIREMENTS**:
- Use the EXACT cost calculations from the cost analysis provided - DO NOT recalculate
- Ensure ALL cost figures are CONSISTENT throughout the section
- Use actual VM counts and specs from the analysis
- Include cost breakdown by service (Compute, Storage, Database, Networking)
- Show calculation basis: "Based on X VMs with average cost of $Y per VM"
- DO NOT mention on-premises costs anywhere

**Format**: Markdown, 400-500 words MAX, proper tables
**Tone**: Financial, analytical, business-value focused
**CRITICAL**: NO on-premises costs. Ensure cost consistency. NO meta-commentary.
"""

COST_ANALYSIS_PROMPT = get_cost_analysis_prompt()

MIGRATION_ROADMAP_PROMPT = """
Generate a BRIEF Migration Roadmap section.

**Input**: Analysis from agent_migration_plan covering MAP methodology.

**CRITICAL - TIMELINE**: Check PROJECT CONTEXT for timeline (e.g., "3 months", "18 months"). ALL phases MUST fit within this EXACT timeline.

**Generate** (ULTRA concise - 200-300 words MAX):
1. Phased Approach (simple table, 3 phases max)
2. Key Milestones (3-5 bullets with relative timing like "Month 1", "Week 2")
3. Success Criteria (3 bullets max)

**Example for 3-month project**:
| Phase | Duration | Key Activities |
|-------|----------|----------------|
| Assess | Month 1 | Discovery, planning |
| Mobilize | Month 2 | Landing zone setup |
| Migrate | Month 3 | Execute migration |

**Format**: Markdown, 200-300 words MAX (STRICT), use relative timeframes (Month 1, Week 2, etc.)
**CRITICAL**: Keep it EXTREMELY brief. NO lengthy explanations. NO meta-commentary.
"""

BENEFITS_RISKS_PROMPT = """
Generate a concise Benefits and Risks section.

**Input**: All previous agent analyses.

**IMPORTANT**: Emphasize both financial AND strategic/operational benefits. Even if cost savings are minimal, highlight:
- Agility and faster time-to-market
- Innovation enablement (AI/ML, analytics, modern services)
- Reduced technical debt and operational complexity
- Global scalability and reliability
- Security and compliance improvements

**Generate** (very concise):
1. Key Benefits (bullet points, 5-7 items - include both cost and strategic benefits)
2. Main Risks (bullet points, 5-7 items)
3. Mitigation Strategies (bullet points, 3-5 items)

**Format**: Markdown, 300-400 words MAX, clear headers and bullets
**Tone**: Balanced, realistic, comprehensive
**CRITICAL**: NO meta-commentary - write only the content itself
"""

RECOMMENDATIONS_PROMPT = """
🚨🚨🚨 STOP! READ THIS FIRST! 🚨🚨🚨

LOOK FOR "PRE-COMPUTED RVTOOLS SUMMARY" OR "EXACT COSTS FROM EXCEL FILE" IN YOUR CONTEXT.

DOES IT SAY "Total VMs" OR "Total Servers and Total Databases"?

IF "Total VMs" → THIS IS RVTOOLS = EC2 ONLY, NO DATABASES EXIST
  ❌ FORBIDDEN: RDS, Aurora, DynamoDB, DMS, database migration
  ❌ DO NOT recommend database services
  ✅ ALLOWED: Lambda, ECS, EKS, Fargate, EC2, Auto Scaling, S3

IF "Total Servers" AND "Total Databases" → THIS IS IT INVENTORY = EC2 + DATABASES
  ✅ ALLOWED: Include database recommendations

🚨 IF YOU WRITE "RDS" OR "DMS" WHEN INPUT SAYS "Total VMs", YOU FAILED 🚨

================================================================================

Generate a concise Recommendations and Next Steps section.

**Input**: All previous analyses and recommendations.
  
- IF you see "Total Servers" AND "Total Databases" (IT Inventory): Include both compute and database recommendations

**CRITICAL - AVOID REPETITION**:
- Do NOT repeat cost savings numbers (already in Executive Summary and Cost Analysis)
- Do NOT repeat wave structures (already in Migration Roadmap)
- Do NOT repeat VM counts or infrastructure details (already in Current State)
- Focus on ACTIONABLE next steps only

**Generate** (very concise):
1. Top 3 Strategic Recommendations (NEW insights, not repeating previous sections)
2. Immediate Actions (bullet points - do NOT recommend assessments that were already completed)
3. Recommended Deep-Dive Assessments (if only basic data like RVTools was provided):
   - **AWS Migration Evaluator**: Detailed TCO analysis and right-sizing recommendations
   - **Migration Portfolio Assessment (MPA)**: Application dependency mapping and wave planning
   - **ISV Migration Tools**: Evaluate third-party solutions for enhanced migration capabilities:
     * Comprehensive cloud readiness assessments
     * Application resource management and optimization
4. 90-Day Plan (table with relative timeframes - focus on ACTIONS not metrics)

**CRITICAL REQUIREMENTS**:
- Do NOT recommend conducting MRA if MRA analysis was already provided
- Do NOT recommend RVTools assessment if RVTools data was already analyzed
- Do NOT recommend ATX assessment if ATX data was already analyzed
- If only RVTools data was provided, RECOMMEND deeper assessments (Migration Evaluator, MPA, Partner tools)
- Focus on NEXT steps, not repeating assessments already done
- Use RELATIVE timeframes (NOT specific dates):
  * Week 1-2, Week 3-4, Week 5-6, etc.
  * Month 1, Month 2, Month 3, etc.
  * Quarter 1, Quarter 2, etc.
- DO NOT use specific calendar dates (e.g., "November 25" or "Dec 2025")
- Use generic timeframes that work regardless of when the document is generated

**Example Format**:
| Timeframe | Activity | Owner |
|-----------|----------|-------|
| Week 1-2  | Finalize landing zone design | Cloud Architecture Team |
| Week 3-4  | Complete pilot wave planning | Migration Team |
| Month 2   | Execute pilot migration | Migration Team |
| Month 3   | Review and optimize | Operations Team |

**Format**: Markdown, 400-500 words MAX, action items table with relative timeframes
**Tone**: Actionable, clear, prioritized, forward-looking
**CRITICAL**: Use relative timeframes only (Week 1-2, Month 1, etc.). NO meta-commentary.
"""

def generate_multi_stage_business_case(agent_results, project_context):
    """
    Generate business case in multiple stages for maximum quality
    
    Args:
        agent_results: Dictionary of results from all agents
        project_context: Project information and context
    
    Returns:
        Complete business case document
    """
    print("="*80)
    print("MULTI-STAGE BUSINESS CASE GENERATION")
    print("="*80)
    
    sections = {}
    
    # Prepare context for all sections
    # Extract actual results from NodeResult objects
    def get_result_text(node_id, max_chars=3000):
        """
        Extract result text with size limit to prevent context overflow.
        Reduced from 8000 to 3000 chars to prevent max_tokens errors.
        """
        if node_id in agent_results:
            result = agent_results[node_id].result
            if result:
                result_text = str(result)
                # Extract key metrics from the beginning (usually has summary)
                # Take first N chars to ensure we capture the important numbers
                # while keeping context size manageable
                return result_text[:max_chars]
        return 'N/A'
    
    # Determine which assessments were completed
    completed_assessments = []
    if 'agent_rv_tool_analysis' in agent_results and agent_results['agent_rv_tool_analysis'].result:
        completed_assessments.append('RVTools VMware Assessment')
    if 'agent_atx_analysis' in agent_results and agent_results['agent_atx_analysis'].result:
        completed_assessments.append('AWS Transform (ATX) Assessment')
    if 'agent_mra_analysis' in agent_results and agent_results['agent_mra_analysis'].result:
        completed_assessments.append('Migration Readiness Assessment (MRA)')
    if 'agent_it_analysis' in agent_results and agent_results['agent_it_analysis'].result:
        completed_assessments.append('IT Infrastructure Inventory Analysis')
    
    assessments_note = f"\n**ASSESSMENTS ALREADY COMPLETED**: {', '.join(completed_assessments)}\n**DO NOT recommend these assessments again.**" if completed_assessments else ""
    
    # Get TCO configuration
    tco_enabled = TCO_COMPARISON_CONFIG.get('enable_tco_comparison', False)
    tco_note = f"\n**TCO_ENABLED**: {tco_enabled}\n**CRITICAL**: {'Include on-premises TCO comparison if AWS < On-Prem' if tco_enabled else 'DO NOT include on-premises costs, TCO comparison, or break-even analysis'}"
    
    # Build comprehensive context with actual analysis results
    context = f"""
{project_context}
{tco_note}

**ANALYSIS RESULTS FROM PREVIOUS AGENTS:**

### Current State Analysis:
{get_result_text('current_state_analysis')}

### Cost Analysis:
{get_result_text('agent_aws_cost_arr')}

### Migration Strategy:
{get_result_text('agent_migration_strategy')}

### Migration Plan:
{get_result_text('agent_migration_plan')}
{assessments_note}

**CRITICAL INSTRUCTIONS:**
- Use ONLY the ACTUAL NUMBERS and data from the analysis results above
- Extract and use REAL values from the analysis - NOT placeholders like [total VM count] or [$X]
- Look for specific metrics in the analysis text and use those exact numbers
- Do NOT make up generic examples or use placeholder data
- IGNORE any example numbers you may have seen in prompts or previous responses
- Ensure all recommendations align with the project context and actual findings
- RESPECT the TCO_ENABLED flag above - if False, DO NOT include any on-premises cost calculations
"""
    
    # Generate each section
    section_configs = [
        ('executive_summary', EXECUTIVE_SUMMARY_PROMPT, 'Executive Summary'),
        ('current_state', CURRENT_STATE_PROMPT, 'Current State Analysis'),
        ('migration_strategy', MIGRATION_STRATEGY_PROMPT, 'Migration Strategy'),
        ('cost_analysis', COST_ANALYSIS_PROMPT, 'Cost Analysis and TCO'),
        ('migration_roadmap', MIGRATION_ROADMAP_PROMPT, 'Migration Roadmap'),
        ('benefits_risks', BENEFITS_RISKS_PROMPT, 'Benefits and Risks'),
        ('recommendations', RECOMMENDATIONS_PROMPT, 'Recommendations and Next Steps')
    ]
    
    for section_key, prompt, section_name in section_configs:
        print(f"\nGenerating: {section_name}...")
        try:
            agent = create_section_agent(prompt)
            
            # Build section-specific context to reduce token usage
            # Only include relevant agent results for each section
            if section_key == 'executive_summary':
                # Executive summary needs all results but condensed
                section_context = f"""
{project_context}
{tco_note}

**ANALYSIS SUMMARY (condensed for Executive Summary):**
- Current State: {get_result_text('current_state_analysis', 2000)}
- Costs: {get_result_text('agent_aws_cost_arr', 2000)}
- Strategy: {get_result_text('agent_migration_strategy', 1500)}
{assessments_note}
"""
            elif section_key == 'current_state':
                # Current state only needs current state analysis
                section_context = f"""
{project_context}

**CURRENT STATE ANALYSIS:**
{get_result_text('current_state_analysis', 4000)}
"""
            elif section_key == 'migration_strategy':
                # Migration strategy needs strategy and current state
                section_context = f"""
{project_context}

**CURRENT STATE:**
{get_result_text('current_state_analysis', 2000)}

**MIGRATION STRATEGY:**
{get_result_text('agent_migration_strategy', 4000)}
"""
            elif section_key == 'cost_analysis':
                # Cost analysis needs cost data
                section_context = f"""
{project_context}
{tco_note}

**COST ANALYSIS:**
{get_result_text('agent_aws_cost_arr', 4000)}
"""
            elif section_key == 'migration_roadmap':
                # Migration roadmap needs plan and strategy
                section_context = f"""
{project_context}

**MIGRATION STRATEGY:**
{get_result_text('agent_migration_strategy', 2000)}

**MIGRATION PLAN:**
{get_result_text('agent_migration_plan', 4000)}
{assessments_note}
"""
            elif section_key == 'benefits_risks':
                # Benefits and risks needs all context
                section_context = context
            elif section_key == 'recommendations':
                # Recommendations needs all context
                section_context = f"""
{project_context}
{assessments_note}

**KEY FINDINGS:**
- Current State: {get_result_text('current_state_analysis', 1500)}
- Costs: {get_result_text('agent_aws_cost_arr', 1500)}
- Strategy: {get_result_text('agent_migration_strategy', 1500)}
"""
            else:
                # Default: use full context
                section_context = context
            
            # For Executive Summary and Cost Analysis sections, inject exact costs from Excel
            if section_key in ['executive_summary', 'cost_analysis']:
                exact_costs = extract_exact_costs_from_excel()
                if exact_costs:
                    print(f"✓ Injecting exact costs from Excel file into {section_name}")
                    task = f"{section_context}\n\n{exact_costs}\n\nGenerate the {section_name} section based on the available analysis."
                else:
                    print(f"⚠ Could not extract exact costs from Excel for {section_name}, using tool output only")
                    task = f"{section_context}\n\nGenerate the {section_name} section based on the available analysis."
            else:
                # Create task with section-specific context
                task = f"{section_context}\n\nGenerate the {section_name} section based on the available analysis."
            
            result = agent(task)
            
            # Extract text content from the result
            # result.message is a dict with 'role' and 'content' keys
            # content is a list of dicts with 'text' key
            if hasattr(result, 'message') and isinstance(result.message, dict):
                content_list = result.message.get('content', [])
                if content_list and isinstance(content_list, list):
                    content = content_list[0].get('text', '') if content_list else ''
                else:
                    content = str(result.message)
            else:
                content = str(result.message) if result.message else ""
            
            # Check if content was truncated
            if content and ("[Continued in next part...]" in content or content.endswith("...")):
                print(f"⚠️  {section_name} may be truncated - consider reducing detail or increasing max_tokens")
            
            sections[section_key] = content
            print(f"✓ {section_name} generated ({len(content)} chars)")
            
        except Exception as e:
            print(f"✗ Error generating {section_name}: {str(e)}")
            sections[section_key] = f"# {section_name}\n\n*Section generation failed: {str(e)}*"
    
    # Combine all sections
    business_case = combine_sections(sections, project_context)
    
    return business_case

def combine_sections(sections, project_context):
    """Combine all sections into final business case document"""
    
    # Extract project info
    project_info = {}
    for line in project_context.split('\n'):
        if 'Project Name:' in line:
            project_info['name'] = line.split(':', 1)[1].strip()
        elif 'Customer Name:' in line:
            project_info['customer'] = line.split(':', 1)[1].strip()
        elif 'Target AWS Region:' in line:
            project_info['region'] = line.split(':', 1)[1].strip()
    
    # Build final document
    document = f"""# AWS Migration Business Case
## {project_info.get('customer', 'Customer')} - {project_info.get('name', 'Migration Project')}

**Target Region:** {project_info.get('region', 'N/A')}  
**Generated:** {os.popen('date').read().strip()}

---

"""
    
    # Add table of contents (plain text, no links)
    document += """## Table of Contents

1. Executive Summary
2. Current State Analysis
3. Migration Strategy
4. Cost Analysis and TCO
5. Migration Roadmap
6. Benefits and Risks
7. Recommendations and Next Steps
8. Appendix: AWS Partner Programs for Migration and Modernization

---

"""
    
    # Add each section
    section_order = [
        ('executive_summary', 'Executive Summary'),
        ('current_state', 'Current State Analysis'),
        ('migration_strategy', 'Migration Strategy'),
        ('cost_analysis', 'Cost Analysis and TCO'),
        ('migration_roadmap', 'Migration Roadmap'),
        ('benefits_risks', 'Benefits and Risks'),
        ('recommendations', 'Recommendations and Next Steps')
    ]
    
    for section_key, section_title in section_order:
        content = sections.get(section_key, f'*{section_title} not available*')
        document += f"\n## {section_title}\n\n{content}\n\n---\n"
    
    # Add appendix with AWS partner programs
    document += f"\n{get_appendix()}\n\n"
    
    # Add footer
    document += f"""
## Document Information

**Generated by:** AWS Migration Business Case Generator  
**Generation Method:** Multi-Stage AI Analysis  
**Model:** {model_id_claude3_7}  
**Date:** {os.popen('date').read().strip()}

---

*This business case was generated using AI-powered analysis of your infrastructure data, assessment reports, and migration readiness evaluation. All recommendations should be validated with AWS solutions architects and your technical teams.*
"""
    
    # Clean up markdown code fences
    document = cleanup_markdown_fences(document)
    
    return document


def cleanup_markdown_fences(text):
    """
    Remove markdown code fence markers (```markdown, ```, etc.) from the text
    These sometimes appear in LLM output and should be removed for cleaner presentation
    """
    import re
    
    # Remove ```markdown at the start of code blocks
    text = re.sub(r'```markdown\s*\n', '', text)
    
    # Remove ``` at the end of code blocks (but preserve code blocks that are intentional)
    # Only remove standalone ``` on its own line
    text = re.sub(r'\n```\s*\n', '\n\n', text)
    
    # Remove any remaining ``` that appear at start or end of lines
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    
    return text

if __name__ == "__main__":
    print("Multi-stage business case generator module loaded")
    print(f"Using model: {model_id_claude3_7}")
    print(f"Max tokens per section: {MAX_TOKENS_BUSINESS_CASE}")
