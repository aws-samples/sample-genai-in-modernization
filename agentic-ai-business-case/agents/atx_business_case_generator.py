"""
ATX Business Case Generator
Generates business case directly from ATX PowerPoint without LLM
Uses deterministic extraction and formatting
"""

from atx_ppt_extractor import extract_atx_ppt_data
from datetime import datetime
from typing import Dict


def generate_atx_business_case(
    atx_ppt_path: str,
    project_context: Dict,
    mra_content: str = None
) -> str:
    """
    Generate business case directly from ATX PowerPoint
    No LLM involved - pure extraction and formatting
    
    Args:
        atx_ppt_path: Path to ATX PowerPoint file
        project_context: Project information (customer, region, timeline)
        mra_content: Optional MRA content to include
    
    Returns:
        Complete business case markdown
    """
    
    # Extract data from ATX PowerPoint
    atx_data = extract_atx_ppt_data(atx_ppt_path)
    
    if not atx_data.get('success'):
        raise Exception(f"Failed to extract ATX data: {atx_data.get('error')}")
    
    # Extract sections
    scope = atx_data['assessment_scope']
    financial = atx_data['financial_overview']
    exec_summary = atx_data['executive_summary']
    
    # Get project info
    customer_name = project_context.get('customer_name', 'Customer')
    project_name = project_context.get('project_name', 'ATX Business Case')
    target_region = project_context.get('target_region', 'us-east-1')
    timeline_months = project_context.get('timeline_months', 12)
    
    # Generate business case
    business_case = f"""# AWS Migration Business Case
## {customer_name} - {project_name}

**Target Region:** {target_region}  
**Generated:** {datetime.now().strftime('%a %d %b %Y %H:%M:%S GMT')}

---

## Table of Contents

1. Executive Summary
2. Current State Analysis
3. Migration Strategy
4. Cost Analysis
5. Migration Roadmap
6. Benefits and Risks
7. Recommendations and Next Steps
8. Appendix: AWS Partner Programs

---

## Executive Summary

# Executive Summary

**Project Overview**

{customer_name} is undertaking a comprehensive AWS migration to modernize its IT infrastructure and achieve greater scalability, reliability, and cost-efficiency. The migration will be completed within {timeline_months} months to the {target_region} region.

**Current State Highlights**

- Total VMs: {scope.get('vm_count', 'Not specified')}
- Windows VMs: {scope.get('windows_vms', 'Not specified')}
- Linux VMs: {scope.get('linux_vms', 'Not specified')}
- Total Storage: {scope.get('storage_tb', 0):.2f} TB
- Total Databases: {scope.get('database_count', 0)}

**Recommended Approach**

A phased migration approach over {timeline_months} months is recommended, leveraging AWS's cloud-native capabilities and executing the migration in structured waves.

**Key Financial Metrics**

- Total Monthly AWS Cost: ${financial.get('monthly_cost', 0):,.2f}
- Total Annual AWS Cost (ARR): ${financial.get('annual_cost', 0):,.2f}
- 3-Year Total Cost: ${financial.get('three_year_cost', financial.get('annual_cost', 0) * 3):,.2f}

*Note: Costs are based on ATX (AWS Transform for VMware) analysis using AWS pricing for the {target_region} region.*

**Expected Benefits**

- Scalability and agility to respond to changing business demands
- Increased reliability and availability through AWS's global infrastructure
- Reduced operational overhead with managed services
- Accelerated innovation and faster time-to-market

**Critical Success Factors**

- Comprehensive application portfolio assessment and wave planning
- Robust cloud governance and security posture implementation
- Organizational readiness through cloud skills development
- Effective cost optimization and continuous monitoring

**Timeline Overview**

A {timeline_months}-month phased approach is planned to meet the migration timeline requirement.

---

## Current State Analysis

# Current State Analysis

## IT Infrastructure Overview

Based on the ATX assessment, {customer_name}'s current infrastructure consists of:

| Metric | Value |
|--------|-------|
| Total VMs | {scope.get('vm_count', 'Not specified')} |
| Windows VMs | {scope.get('windows_vms', 'Not specified')} |
| Linux VMs | {scope.get('linux_vms', 'Not specified')} |
| Total Storage | {scope.get('storage_tb', 0):.2f} TB |
| Total Databases | {scope.get('database_count', 0)} |

## Assessment Scope Details

{scope.get('content', 'Assessment scope details not available in ATX PowerPoint.')}

## Key Observations

The infrastructure assessment reveals a {'database-inclusive' if scope.get('database_count', 0) > 0 else 'compute-focused'} environment that will benefit from AWS's scalable and managed services.

---

## Migration Strategy

# Migration Strategy

## Recommended Approach

A phased migration approach over {timeline_months} months is recommended, allowing {customer_name} to:
- Build cloud expertise gradually
- Migrate applications based on complexity and business criticality
- Achieve operational excellence while meeting the timeline

## Migration Phases

The migration will be executed in three phases:

**Phase 1: Foundation & Learning (Months 1-{timeline_months//3})**
- Establish AWS foundation and governance
- Build cloud skills and capabilities through training
- Migrate low-risk applications for learning
- Implement DevOps practices

**Phase 2: Scale & Optimize (Months {timeline_months//3 + 1}-{2*timeline_months//3})**
- Migrate majority of applications
- Implement advanced AWS services
- Optimize costs and performance
- Establish operational excellence practices

**Phase 3: Transform & Innovate (Months {2*timeline_months//3 + 1}-{timeline_months})**
- Complete migration of mission-critical workloads
- Implement advanced AWS capabilities
- Achieve full cloud benefits and innovation

## Migration Strategies

The migration will leverage the AWS 7Rs framework:
- **Rehost (Lift & Shift)**: For applications requiring minimal changes
- **Replatform**: For applications benefiting from managed services
- **Refactor**: For applications requiring modernization
- **Repurchase**: For applications better suited as SaaS
- **Retain**: For applications not ready for migration
- **Retire**: For applications no longer needed

---

## Cost Analysis

# Cost Analysis

## AWS Cost Summary

Based on the ATX (AWS Transform for VMware) analysis:

**Monthly AWS Cost:** ${financial.get('monthly_cost', 0):,.2f}  
**Annual AWS Cost (ARR):** ${financial.get('annual_cost', 0):,.2f}  
**3-Year Total Cost:** ${financial.get('three_year_cost', financial.get('annual_cost', 0) * 3):,.2f}

## Cost Breakdown

- **Total VMs:** {scope.get('vm_count', 'Not specified')}
- **Windows VMs:** {scope.get('windows_vms', 'Not specified')}
- **Linux VMs:** {scope.get('linux_vms', 'Not specified')}
{'- **Databases:** ' + str(scope.get('database_count', 0)) if scope.get('database_count', 0) > 0 else ''}

**Average Cost per VM:** ${financial.get('monthly_cost', 0) / scope.get('vm_count', 1):,.2f}/month

## Financial Overview from ATX

{financial.get('content', 'Financial overview details not available in ATX PowerPoint.')}

## Migration Cost Ramp

The AWS costs will ramp up as the migration progresses:

| Phase | Timeline | AWS Costs |
|-------|----------|-----------|
| Phase 1 | Months 1-{timeline_months//3} | ${financial.get('monthly_cost', 0) * 0.3:,.2f}/month (30%) |
| Phase 2 | Months {timeline_months//3 + 1}-{2*timeline_months//3} | ${financial.get('monthly_cost', 0) * 0.7:,.2f}/month (70%) |
| Phase 3 | Months {2*timeline_months//3 + 1}-{timeline_months} | ${financial.get('monthly_cost', 0):,.2f}/month (100%) |

## Cost Optimization Opportunities

- Right-sizing recommendations based on actual utilization
- Reserved Instances and Savings Plans for predictable workloads
- Storage optimization with lifecycle policies
- Spot instances for fault-tolerant workloads
- AWS Cost Explorer and Budgets for continuous monitoring

---

## Migration Roadmap

# Migration Roadmap

| Phase | Duration | Key Activities |
|-------|----------|----------------|
| Foundation & Learning | Months 1-{timeline_months//3} | Establish AWS foundation, build cloud skills, migrate low-risk applications |
| Scale & Optimize | Months {timeline_months//3 + 1}-{2*timeline_months//3} | Migrate majority of applications, implement advanced services, optimize costs |
| Transform & Innovate | Months {2*timeline_months//3 + 1}-{timeline_months} | Complete migration, implement advanced capabilities, achieve full cloud benefits |

## Key Milestones

- **Month 1:** AWS landing zone established
- **Month {timeline_months//3}:** First wave of applications migrated
- **Month {2*timeline_months//3}:** Majority of applications migrated
- **Month {timeline_months}:** Migration complete, operational excellence achieved

## Success Criteria

- All {scope.get('vm_count', 'N/A')} VMs successfully migrated to AWS
- Target monthly cost of ${financial.get('monthly_cost', 0):,.2f} achieved
- 99.9% availability and performance targets met
- Security and compliance frameworks validated

---

## Benefits and Risks

# Benefits and Risks

## Key Benefits

- **Scalability and Agility:** AWS provides elastic scalability to meet changing business demands
- **Cost Optimization:** Pay-as-you-go pricing and managed services reduce operational costs
- **Reliability:** AWS's global infrastructure ensures high availability and disaster recovery
- **Innovation:** Access to cutting-edge services for AI/ML, analytics, and modernization
- **Security:** Enhanced security posture with AWS's comprehensive security services

## Main Risks

- **Skills Gap:** Cloud expertise may be limited within the organization
- **Migration Complexity:** Migrating {scope.get('vm_count', 'N/A')} VMs requires careful planning
- **Timeline Pressure:** {timeline_months}-month timeline requires efficient execution
- **Cost Management:** Without proper governance, costs can exceed projections

## Mitigation Strategies

- **Comprehensive Training:** Implement cloud skills development program
- **Phased Approach:** Migrate in waves to manage complexity
- **Partner Engagement:** Leverage AWS partners for expertise and support
- **Cost Governance:** Implement AWS Cost Explorer, Budgets, and tagging strategies

---

## Recommendations and Next Steps

# Recommendations and Next Steps

## Top 3 Strategic Recommendations

1. **Establish Cloud Center of Excellence (CCoE):** Create a centralized team to drive cloud adoption, governance, and best practices

2. **Implement Comprehensive Training Program:** Target cloud certifications and hands-on training for key team members

3. **Engage AWS Partners:** Leverage AWS Partner Network for migration expertise and accelerated delivery

## Immediate Actions

- Finalize AWS landing zone design and deployment
- Initiate cloud skills development program
- Conduct detailed application portfolio assessment
- Develop comprehensive migration wave plan
- Implement foundational security and governance controls

## Recommended Deep-Dive Assessments

- **AWS Migration Evaluator:** Detailed TCO analysis and right-sizing recommendations
- **Migration Portfolio Assessment (MPA):** Application dependency mapping and wave planning
- **AWS Well-Architected Review:** Architecture assessment and optimization recommendations

## 90-Day Plan

| Timeframe | Activity | Owner |
|-----------|----------|-------|
| Week 1-2 | Finalize AWS landing zone design | Cloud Architecture Team |
| Week 3-4 | Initiate cloud skills development program | Training Team |
| Week 5-6 | Conduct application portfolio assessment | Migration Team |
| Month 2 | Develop detailed migration wave plan | Migration Team |
| Month 3 | Complete pilot wave planning | Migration Team |

---

## Appendix: AWS Partner Programs

### Core Migration Programs

#### 1. MAP (Migration Acceleration Program)
Comprehensive cloud migration program with three phases: Assess, Mobilize, and Migrate & Modernize. Provides funding to offset initial migration costs.

**Learn more:** [AWS Migration Acceleration Program](https://aws.amazon.com/migration-acceleration-program/)

#### 2. OLA (Optimization and Licensing Assessment)
Helps assess on-premises environments and provides data-driven recommendations for migration optimization.

**Learn more:** [AWS Optimization and Licensing Assessment](https://aws.amazon.com/optimization-and-licensing-assessment/)

#### 3. AWS Application Migration Service (MGN)
Simplifies and expedites migration to AWS by automatically converting source servers to run natively on AWS.

**Learn more:** [AWS Application Migration Service](https://aws.amazon.com/application-migration-service/)

#### 4. AWS Database Migration Service (DMS)
Helps migrate databases to AWS quickly and securely with minimal downtime.

**Learn more:** [AWS Database Migration Service](https://aws.amazon.com/dms/)

---

## Document Information

**Generated by:** AWS Migration Business Case Generator  
**Generation Method:** Direct ATX PowerPoint Extraction (Deterministic)  
**Source:** ATX (AWS Transform for VMware) Analysis  
**Date:** {datetime.now().strftime('%a %d %b %Y %H:%M:%S GMT')}

---

*This business case was generated using deterministic extraction from ATX PowerPoint presentation. All costs and metrics are sourced directly from the ATX analysis.*
"""
    
    return business_case


if __name__ == "__main__":
    # Test the generator
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python atx_business_case_generator.py <atx_ppt_file>")
        sys.exit(1)
    
    atx_ppt_path = sys.argv[1]
    
    project_context = {
        'customer_name': 'Acme',
        'project_name': 'ATX Migration',
        'target_region': 'us-east-1',
        'timeline_months': 12
    }
    
    try:
        business_case = generate_atx_business_case(atx_ppt_path, project_context)
        
        # Save to file
        output_path = 'output/atx_business_case_deterministic.md'
        # Security: Specify encoding explicitly to prevent encoding issues
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(business_case)
        
        print(f"✓ Business case generated: {output_path}")
        print(f"  Length: {len(business_case)} characters")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
