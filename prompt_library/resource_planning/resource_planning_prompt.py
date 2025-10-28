def get_resource_planning_prompt(
    migration_strategy, wave_planning_data, resource_details
):
    # Step 3: Apply Structural Guidelines - Variables
    target_utilisation = "85-95%"
    team_pods = "3-5"
    contingency = "15-20%"
    effort_estimation = "Use person-days where 8 hours = 1 day and 5 days = 1 week"

    resource_prompt = f"""
        As an AWS migration expert, please develop comprehensive AWS migration resource planning using the following inputs:

        **INPUT PARAMETERS:**
        - Migration Strategy: {migration_strategy}
        - Wave Planning Data: {wave_planning_data}  
        - Resource Details: {resource_details}

        **ANALYSIS FRAMEWORK:**

        **Step 1: Input Analysis**
        Analyse the provided inputs to understand:
        • Migration strategy complexity, scale, and workload volume from {migration_strategy}
        • Technology stack composition and legacy system dependencies
        • Wave structure, timeline, and application distribution from {wave_planning_data}
        • Available skills, roles, rates, and resource constraints from {resource_details}

        **Step 2: Team Structure Development**
        Develop two distinct team structures using the analysed inputs:

        **Team Structure 1: Hub-and-Spoke Model**
        - Central Centre of Excellence (CoE) with distributed execution teams
        - Centralised governance with federated delivery capabilities
        - Resource allocation based on {resource_details} and {wave_planning_data}

        **Team Structure 2: Wave-Based Approach**
        - Teams specifically aligned to migration waves from {wave_planning_data}
        - Sequential team formation based on wave requirements and {migration_strategy}

        **Step 3: Apply Structural Guidelines**
        For both team structures, implement:
        • Target utilisation rate: {target_utilisation}
        • Team pods of {team_pods} people with role specialisations from {resource_details}
        • {contingency} contingency capacity on all calculations
        • **Effort Estimation Standard**: {effort_estimation}

        **Step 4: Resource Calculations**
        Calculate team sizes using:
        • Wave volumes and timelines from {wave_planning_data}
        • Migration complexity factors from {migration_strategy}
        • Available skills and rates from {resource_details}
        • 6 R's migration strategy complexity multipliers
        • **Calculation Standard**: All effort estimations must use {effort_estimation.lower()}

        **OUTPUT REQUIREMENTS:**

        **Executive Summary**
        - High-level summary of migration complexity and wave structure
        - Key considerations and narrative of effort estimation methodology
        - Overview of recommended team structure approach

        **1. Team structure evaluation and recommendation** 
        - High-level overview of Team Structure 1: Hub-and-Spoke Model
        - High-level overview of Team Structure 2: Wave-Based Approach
        - Based on the developed team structures, compare Hub-and-Spoke Model and Wave-Based Approach and identify gaps and the most common or consistent elements across both structures including:
            • Shared roles and responsibilities
            • Common resource requirements
            • Consistent workstream dependencies
            • Similar governance mechanisms
        - Based on this analysis, synthesise a final structure; and select and prioritise the most relevant skills from {resource_details} based on migration complexity, cost-effectiveness and accelerated migration delivery. Specify, core team assignments, specialist requirements and Support function involvement (when needed)

        **2. Resource summary**
        • Total Project Duration: [X months]
        • Total Effort Required: [X person-days]
        • Peak Team Size: [X people]
        • Recommended Team Structure: [Hub-and-Spoke/Wave-Based/Hybrid Recommended]

        **3. Planning for recommended team structure**
        | Wave | Description | Workloads/Apps | Duration (weeks) | Required Team Size | Key Roles |
        |------|-------------|----------------|------------------|---------------|-----------|
        | Wave 1 | | | | | |
        | Wave 2 | | | | | |
        | Wave 3 | | | | | |
        | Wave 4 | | | | | |
        | **Total** | | | | | |

        **4. Role-Based resource allocation**
        - Ensure the Role-Based resource allocation is inline with a point number (Team structure evaluation and recommendation) which the most relevant skills based on migration complexity, cost-effectiveness and accelerated migration delivery
        - Total Number of Days are the same as Total Effort Required. Ensure only relevant and required specialists are included
        **Note**: All calculations based on {effort_estimation.lower()}

        | Role | Required FTE | Number of Days | Utilisation % | Daily Rate (£) | Total Cost (£) |
        |------|-------------|----------------|---------------|----------------|----------------|
        | Senior Solutions Architect | | | | | |
        | Migration Engineer | | | | | |
        | DevOps Engineer | | | | | |
        | Cloud Infrastructure Engineer | | | | | |
        | Application Migration Specialist | | | | | |
        | Test Engineer | | | | | |
        | Project Manager | | | | | |
        | Change Manager | | | | | |
        | **Total** | | | | | |

        **5. Justification and Rationale**
        Provide detailed reasoning for:
        • **Team Sizing Rational**: How wave volumes and complexity drove team size decisions
        • **Effort Estimation Methodology**: Calculation approach using complexity factors (Rehost,Replatform, and Refactor) and {effort_estimation.lower()}
        • **Cost Optimisation Strategy**: How the recommended structure balances cost efficiency with delivery acceleration

        Format your response in markdown to make it readable and structured. Use British English standards. 
        **Ensure all calculated totals are consistent across tables - the sum of individual wave efforts in Table 3 must equal the total effort in Table 2, the sum of role-based person-days in Table 4 must equal the total effort in Table 2, and all cost calculations must reconcile across all tables with no discrepancies.**
        """
    return resource_prompt
