def get_migration_patterns_prompt(services_summary, scope_text):
    prompt = f"""
        As an AWS migration expert, please develope an AWS migration strategy based on the following AWS calculator data: {services_summary} Ensure mathematical operations like addition, subtraction, multiplication, and division are correct for Compute, Storage and Database provided in the services_summary.
        
        Additional scope information {scope_text if scope_text else ""}
        
        In order to develop an AWS migration strategy adhere to the following fix structure only in response. Always use USD($) as currency. Use British English standards.
        1. Analyse the calculator data focusing on cost optimisation and performance as key drivers.
        2. Generate three different patterns to modernize these workloads, progressing from minimal changes to more comprehensive modernization.
        3. Compare these three approaches and identify the most common or consistent elements across all strategies.
        4. Based on this analysis, synthesise a final strategy that incorporates the most consistent aspects from all three approaches.
        5. Create a migration wave plan for the final strategy with in a table format:
           - Table header 'High Level Wave Plan'
           - Wave number and description
           - Services/workloads included in each wave
           - Estimated duration for each wave
           - Calculate the cumulative USD($) spend for each wave in a table format
        6. Answer the following questions:
           (1) Predict the month where partner will achieve the first 50,000 USD($) milestone in cumulative spend.
           (2) If the first 50,000 USD($) milestone in cumulative spend takes longer than four months, provide recommendations and strategies to accelerate migration for the first 50,000 USD($) milestone within the first three months.
           (3) Include appropriate risks and assumptions involved in the strategy to accelerate migration.
           (4) Include rational, reasoning and assumptions for the estimated duration for each wave
        
        Format your response in markdown to make it readable and structured. 
        """
    return prompt
