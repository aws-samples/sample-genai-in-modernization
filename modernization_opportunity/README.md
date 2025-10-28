# Modernization Opportunity Prompt Library

## Description

The modernization opportunity Prompt Library provides a prompt generation functionality designed to generate AWS modernization strategies. This library contains three specialized prompt functions that work together to assess inventory data, analyze architecture diagrams, and recommend [modernization pathways](https://aws.amazon.com/blogs/migration-and-modernization/move-to-ai-pathway/) with cost projections.

## Library Components

### 1. Inventory Analysis Prompt (`inventory_analysis_prompt.py`)

#### Primary Purpose
Conducts highlevel analysis of IT inventory data with emphasis on cost optimization, performance metrics, disaster recovery capabilities, and strategic planning for AWS migration.

#### Key Features
- Asset categorization across multiple technology domains
- Performance and capacity analysis with utilization metrics
- Disaster recovery and business continuity assessment
- Risk assessment and end-of-life planning
- Cost optimization opportunity identification
- Pattern and anomaly detection

#### Input Parameters

| Parameter Name | Type | Description |
|----------------|------|-------------|
| `inventory_csv` | String/DataFrame | IT inventory data in CSV format containing asset information, specifications, and performance metrics |

#### Expected Output Structure

- Asset categorization by type (Compute, Storage, Database, etc.)
- Performance trends and underutilized resources
- End-of-life identification and security vulnerabilities
- Usage patterns and asset dependencies
- Technology stack and any DR dependencies analysis
- Executive summary
- Migration priorities identification

---

### 2. Modernization Pathways Prompt (`modernization_pathways_prompt.py`)

#### Primary Purpose
Develops AWS modernization strategies with implementation approaches based on IT inventory analysis, modernization scope, and optional architecture descriptions.

#### Key Features
- Eight distinct modernization pathway recommendations
- AWS service mapping and configuration suggestions
- Cost estimation for recommended services
- Implementation approach development
- Regional pricing considerations `(EU-West-1)`

#### Input Parameters

| Parameter Name | Type | Description |
|----------------|------|-------------|
| `inventory_csv` | String/DataFrame | IT inventory data containing compute, storage, and database information |
| `architecture_description` | String (Optional) | Detailed analysis of on-premises architecture from image analysis |
| `scope_text` | String | Modernization scope and requirements definition |

#### Expected Output Structure
1. **High Level AWS Cost Table**
   - Modernization Pathway or Additional AWS Services
   - AWS Service Name and recommended configuration
   - Monthly cost estimates in USD for `EU-West-1` region
   - Annual Recurring Revenue (ARR) estimates

2. **Pathway Analysis** (for each applicable pathway)
   - Pathway appropriateness explanation
   - Specific AWS service recommendations with configurations
   - Service selection rationale
   - Monthly and annual cost estimates ($1,000-$50,000 range)

3. **Implementation Approach**
   - High-level implementation strategy and timeline

**Supported Modernization Pathways:**
- Move to Cloud Native
- Move to Containers
- Move to Open Source
- Move to Managed Databases
- Move to Managed Analytics
- Move to Modern DevOps
- Move to AI
- Additional AWS Services Assessment

---

### 3. On-Premises Architecture Prompt (`onprem_architecture_prompt.py`)

#### Primary Purpose
Provides analysis of on premises architecture diagrams (JPG, JPEG, PNG formats) to identify infrastructure components, security controls, and integration patterns for modernization planning.

#### Key Features
- Systematic architecture diagram review
- Multi-domain analysis (infrastructure, network, security, applications)
- Comprehensive component identification
- Integration and dependency mapping

#### Declared Variables
- `prompt_template`: String containing the structured architecture analysis prompt

#### Expected Output Structure
1. **Executive Summary**
   - High-level architecture overview and key findings

2. **Detailed Analysis and Findings**
   - **Physical/Virtual Infrastructure**: Storage components and infrastructure elements
   - **Network Architecture**: Topology, segmentation, security zones, load balancing, and redundancy
   - **Security Controls**: Firewalls, IDS/IPS, authentication, and authorization mechanisms
   - **Application Architecture**: Tiers, integration patterns, and dependencies
   - **Deployment Environment**: Components and environment configuration
   - **Database Architecture**: Data flows, integration, and ETL processes
   - **Monitoring Capabilities**: Alerting and monitoring infrastructure
   - **Analytics Environment**: Big data components and analytics capabilities

## Usage Integration

These prompts are designed to work together in the modernization assessment workflow:

1. **Architecture Analysis**: Use `get_onprem_architecture_prompt()` to analyze uploaded architecture diagrams
2. **Inventory Assessment**: Use `get_inventory_analysis_prompt()` with CSV inventory data for comprehensive asset analysis
3. **Modernization Strategy**: Use `get_modernization_pathways_prompt()` combining inventory data, scope requirements, and optional architecture analysis to generate AWS modernization recommendations