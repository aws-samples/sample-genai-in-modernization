def get_inventory_analysis_prompt(inventory_csv):
    prompt = f"""
        As an AWS migration expert, conduct a comprehensive analysis of the provided IT inventory with emphasis on cost optimisation, performance metrics, disaster recovery capabilities, and strategic planning.

        **IMPORTANT: Do not assume, estimate, or calculate any costs, prices, or financial figures unless explicitly provided in the inventory data. Only analyse and report on cost-related information that is directly available in the provided dataset.**

        IT Inventory: Ensure mathematical operations like addition, subtraction, multiplication, and division are correct for Compute, Storage and Database provided in the inventory.
        {inventory_csv}

        Perform a thorough analysis and provide your response in the following structured order:

        ## (1) Inventory Insight & Cost Verification
        - **Asset Categorisation**: Identify and categorise by Compute, Storage, Database, Networking, Security, Monitoring, DevOps, AI, ML
        - **Purchase Price Verification**: 
            - Check first if purchase prices, acquisition dates, and depreciation schedules are available. If available, then only review and validate purchase prices, acquisition dates, and depreciation schedules
        - **Cost Categorisation**: 
            - Check first if costs are available for assets. If available, then only break down costs by asset type with detailed cost allocation
        - **Service Level Agreements**: 
            - Check first if any SLAs, performance guarantees, and associated penalty clauses are available. If available, then only review existing SLAs, performance guarantees, and associated penalty clauses

        ## (2) Capacity & Performance Analysis
        - **Utilisation Metrics**: CPU usage, memory usage, storage usage, and network bandwidth patterns
        - **Critical Capacity Issues**: Identify systems operating above 80% capacity with immediate action requirements
        - **Performance Trends**: Analyse utilisation patterns, peak usage times, and growth trajectories
        - **Underutilised Resources**: Highlight assets with consistently low utilisation rates

        ## (3) Disaster Recovery & Business Continuity Analysis
        - **Storage Systems Assessment**: 
            - Analyse storage infrastructure (SAN, NAS, local storage) with capacity, performance metrics, and backup capabilities
            - Identify storage dependencies and single points of failure
        - **Recovery Requirements (RTO/RPO)**:
            - Check if RTO (Recovery Time Objective) and RPO (Recovery Point Objective) requirements are documented
            - If available, analyse business impact classifications and acceptable downtime windows
            - Assess data loss tolerance requirements per application/system
        - **Backup Strategies Analysis**:
            - Review backup frequency schedules and retention policies if documented
            - Analyse backup testing procedures and success rates if available
            - Identify gaps in backup coverage or untested backup systems
        - **Replication Mechanisms**:
            - Identify existing replication setups (real-time vs. batch processing)
            - Document synchronous vs. asynchronous replication methods if present
            - Analyse replication targets and geographic distribution
        - **Current DR Capabilities**:
            - Assess existing disaster recovery sites and their capacity
            - Review DR testing history and procedures if documented
            - Identify critical systems without adequate DR protection

        ## (4) Risk Assessment & End-of-Life Planning
        - **End-of-Life Identification**: List all hardware approaching end-of-life within 12 months
        - **Security Vulnerabilities**: Identify unsupported or obsolete systems posing security risks
        - **Business Continuity Impact**: Assess potential service disruption risks and DR readiness gaps
        - **Single Points of Failure**: Highlight critical systems without redundancy or DR protection

        ## (5) Cost Optimisation Opportunities
        - **Licence Consolidation Savings**: Check if any licence details are available. If licence details are available, then only identify potential software licence optimisation and consolidation opportunities for Microsoft and Oracle
        - **Immediate Cost Reduction**: Identify quick wins for cost reduction (redundant systems, over-provisioned resources)
        - **DR Cost Efficiency**: Analyse DR infrastructure costs and identify optimisation opportunities if cost data is available

        ## (6) Patterns, Anomalies & Dependencies
        - **Usage Patterns**: Identify trends, seasonal variations, and anomalous behaviour
        - **Asset Dependencies**: Map critical relationships and dependencies between systems
        - **Technology Stack Analysis**: Highlight integration points and potential single points of failure
        - **DR Dependencies**: Analyse cross-system dependencies that impact disaster recovery strategies

        ## (7) Strategic Recommendations & Key Findings
        - **Executive Summary**: Data-driven insights based solely on available data
        - **DR Readiness Assessment**: Overall disaster recovery maturity and gaps
        - **Migration Priorities**: Systems requiring immediate attention for DR improvement
        
        **REMINDER: Base all analysis strictly on the provided inventory data. Do not introduce external cost estimates, market pricing, or assumed financial figures. For DR analysis, only report on disaster recovery information that is explicitly documented in the inventory.**
        
        Format your response in markdown with clear headings, bullet points, and tables where appropriate. Use British English standards throughout.
        """
    return prompt
