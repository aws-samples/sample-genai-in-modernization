import os
from strands import Agent, tool
from strands.models import BedrockModel

from config import input_folder_dir_path, model_id_claude3_7, model_temperature


# Create a BedrockModel
bedrock_model = BedrockModel(
    model_id=model_id_claude3_7,
    temperature=model_temperature
)

def read_file_from_input_dir(filename):
    """Read file from the input directory"""
    from project_context import get_input_file_path
    return get_input_file_path(filename)

@tool(name="read_migration_strategy_framework", description="Read the AWS 6Rs migration strategy framework reference document")
def read_migration_strategy_framework(filename: str = "aws-migration-strategy-6rs-framework.md"):
    """Read the migration strategy framework markdown file"""
    full_path = read_file_from_input_dir(filename)
    with open(full_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

@tool(name="read_portfolio_assessment", description="Read application portfolio assessment file if available")
def read_portfolio_assessment(filename: str):
    """Read application portfolio assessment file (CSV, Excel, or Markdown)"""
    full_path = read_file_from_input_dir(filename)
    
    # Determine file type and read accordingly
    if filename.endswith('.csv'):
        import pandas as pd
        df = pd.read_csv(full_path)
        return df.to_string()
    elif filename.endswith(('.xlsx', '.xls')):
        import pandas as pd
        df = pd.read_excel(full_path)
        return df.to_string()
    elif filename.endswith('.md'):
        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    else:
        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content

# System message for the migration strategy agent
system_message = """
You are an AWS migration strategy specialist with expertise in defining optimal migration approaches 
using the AWS 6Rs framework (Rehost, Replatform, Repurchase, Refactor, Retire, Retain).

**Your Role**: Analyze available data sources and recommend the most appropriate migration strategy 
for each application or workload category.

**Available Tools**:
- read_migration_strategy_framework: Access the comprehensive AWS 6Rs framework reference document
  (This document contains all guidance, ranges, context indicators, and examples)
- read_portfolio_assessment: Read application portfolio assessment if available

**CRITICAL**: The migration strategy framework document (aws-migration-strategy-6rs-framework.md) 
contains ALL the information you need including:
- Complete 6Rs strategy descriptions
- Default distribution ranges (30-40/10-20/10-20/5-10/5-10/5-10)
- Typical/midpoint values (35/15/15/7/7/7)
- Context indicators for adjustments
- Step-by-step application process
- Example calculations
- Mandatory disclaimers
- Output format templates
- Validation checklist

**Instructions**:
1. **ALWAYS read the framework document first** using read_migration_strategy_framework()
2. Check if portfolio assessment is available using read_portfolio_assessment()
3. Follow the guidance in the framework document exactly
4. Apply the ranges and adjustments as specified in the framework
5. Include all mandatory disclaimers from the framework
6. Use the output format template provided in the framework

**When Application Portfolio Assessment is Available**:
- Use actual application data for recommendations
- Adjust strategy based on real characteristics and dependencies

**When Application Portfolio Assessment is NOT Available**:
- Follow the "AGENT USAGE GUIDE" section in the framework document
- Use the ranges and typical values specified
- Apply context indicators to adjust within ranges
- Include all mandatory disclaimers from the framework document

**Windows Server OLA Check**:
- If >20 Windows Servers detected: Flag MANDATORY Optimization and License Assessment (OLA)
- Expected savings: 30-50% through license optimization

**Output Requirements**:
- Follow the output format template in the framework document
- Include all mandatory disclaimers
- Provide clear rationale for percentage adjustments
- Recommend portfolio assessment

Format your response in markdown with clear headings, bullet points, and tables as shown in the framework document.
"""

# Create the agent with migration strategy tools
agent = Agent(
    model=bedrock_model,
    system_prompt=system_message,
    tools=[read_migration_strategy_framework, read_portfolio_assessment]
)

# Example usage (commented out)
# question = """
# Analyze the available infrastructure data and recommend an optimal migration strategy 
# using the AWS 6Rs framework. Consider the IT inventory, VMware assessments, and any 
# available application portfolio data. Provide a comprehensive migration strategy with 
# wave planning and timeline recommendations.
# """
# 
# result = agent(question)
# print(result.message)


if __name__ == "__main__":
    # Test the migration strategy tools
    print("Testing Migration Strategy Analysis Tools...")
    
    # Test framework reading
    try:
        framework = read_migration_strategy_framework()
        print(f"\n✓ Migration strategy framework loaded successfully ({len(framework)} characters)")
    except Exception as e:
        print(f"\n✗ Error reading framework: {e}")
    
    # Test portfolio assessment reading (if available)
    try:
        portfolio = read_portfolio_assessment("application-portfolio.csv")
        print(f"✓ Application portfolio loaded successfully")
    except Exception as e:
        print(f"✗ Portfolio assessment not available (expected if file doesn't exist)")
