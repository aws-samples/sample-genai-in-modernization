# Resource Planning Prompt Library

## Description
The Resource Planning Prompt Library provides a prompt generation functionality for AWS migration resource planning. This module creates a sample structured prompts that leverage Amazon Bedrock's models to generate resource allocation plans, team structures, and cost projections for AWS migration projects.

## Primary Purpose

This module serves as the prompt engineering foundation for automated resource planning in AWS migrations. It transforms raw migration strategy data, wave planning information, and resource profiles into structured prompts that generate:

- Executive summaries of migration complexity
- Comparative team structure evaluations (Hub-and-Spoke vs Wave-Based models)
- Detailed resource allocation plans
- Cost projections and effort estimations
- Role-based resource assignments with utilisation metrics

## Key Features

### 1. **Configurable Parameters**
- Built-in structural guidelines with configurable utilisation rates, team sizes, and contingency factors
- Standardised effort estimation methodology (person-days calculation)
- Flexible resource allocation based on migration complexity

### 2. **Multi-Input Integration**
- 1. Processes migration strategy documents 
- 2. Incorporates wave planning data and timelines 
- 3. Utilises resource profile information for cost and skill matching
- Note: (a) The input for items 1 and 2 could be a migration strategy generated using a migration strategy sample `(pages/02_migration_strategy.py)` (b) The resource profile could be a CSV file `(sampledata/resource_profile_template.csv)`  that includes resource category (core, specialist, and support), resource role, resource level (junior, senior and principal), and resource charge

### 3. **Comprehensive Output Structure**
- Generates five key deliverables: executive summary, team evaluation, resource summary, wave planning, and role-based allocation
- Ensures mathematical consistency across all calculated totals and cost projections
- Provides detailed justification and rationale for recommendations

## Input Parameters

### Function: `get_resource_planning_prompt(migration_strategy, wave_planning_data, resource_details)`

| Parameter Name | Type | Description |
|----------------|------|-------------|
| `migration_strategy` | `str` | Complete migration strategy document `i.e. regnerated using (pages/02_migration_strategy.py)` content containing complexity analysis, technology stack composition, legacy system dependencies, and 6 R's migration approach details |
| `wave_planning_data` | `str` | Wave planning information including wave structure, timeline data, application distribution across waves, and workload volume metrics |
| `resource_details` | `str` | Available resource profile data containing skills inventory, role definitions, daily rates, resource constraints, and team capacity information |

### Declared Variables (Internal Configuration)

| Variable Name | Type | Description |
|---------------|------|-------------|
| `target_utilisation` | `str` | Target team utilisation percentage range (default: "85-95%") |
| `team_pods` | `str` | Recommended team pod size range (default: "3-5") |
| `contingency` | `str` | Contingency capacity percentage for risk mitigation (default: "15-20%") |
| `effort_estimation` | `str` | Standardised effort calculation methodology (default: "Use person-days where 8 hours = 1 day and 5 days = 1 week") |

## Expected Output Structure

The generated prompt produces a comprehensive resource planning document with the following structured sections:

### 1. **Executive Summary**
- High-level migration complexity assessment
- Wave structure overview and key considerations
- Effort estimation methodology narrative
- Recommended team structure approach summary

### 2. **Team Structure Evaluation and Recommendation**
- Hub-and-Spoke Model analysis with centralised CoE approach
- Wave-Based Approach evaluation with sequential team formation
- Comparative analysis identifying gaps and common elements
- Final synthesised structure recommendation with core team assignments

### 3. **Resource Summary**
- Total project duration (months)
- Total effort required (person-days)
- Peak team size requirements
- Recommended team structure selection

### 4. **Wave-Based Planning Table**
```
| Wave | Description | Workloads/Apps | Duration (weeks) | Required Team Size | Key Roles |
```

### 5. **Role-Based Resource Allocation Table**
```
| Role | Required FTE | Number of Days | Utilisation % | Daily Rate (£) | Total Cost (£) |
```

### 6. **Justification and Rationale**
- Team sizing rationale based on wave volumes and complexity
- Effort estimation methodology with complexity factors
- Cost optimisation strategy balancing efficiency and delivery acceleration

## Usage Context

This prompt library integrates with:
- `pages/03_resource_planning.py` - Main Streamlit interface for resource planning
