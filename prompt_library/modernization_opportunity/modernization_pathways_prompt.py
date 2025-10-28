def get_modernization_pathways_prompt(
    inventory_csv, architecture_description, scope_text
):
    prompt = f"""
        As an AWS migration expert, analyse the provided IT inventory, modernisation scope and target architecture analysis to develop an AWS modernisation strategy with implementation approach.
        Focus on cost optimisation and performance as key drivers.Always use USD($) as currency.
        
        IT Inventory:Ensure mathematical operations like addition, subtraction, multiplication, and division are correct for Compute, Storage and Database provided in the inventory
        {inventory_csv}

        Modernisation Scope:
        {scope_text}
        
        {"Target Architecture Analysis:" + architecture_description if architecture_description else "No target architecture provided."}
        
        To develop an AWS modernisation strategy with implementation approach: 
        (a) Use the following modernisation pathways and recommend AWS services for each applicable pathway:
        
        1. Move to Cloud Native: API Gateway, Lambda, EventBridge, Step Functions, SQS, SNS, Amazon MQ, AppSync, Cognito, Amplify, X-Ray, Migration Hub Refactor Spaces, CognitoSync
        2. Move to Containers: EKS, ECS, ECR, Fargate, App Runner
        3. Move to Open Source: RDS (MySQL, Postgres, MariaDB), Aurora, Linux containers on ECS/EKS/Fargate, Lambda
        4. Move to Managed Databases: RDS (MySQL, Postgres, MariaDB), Aurora, DocumentDB, KeySpaces, ElastiCache, MemoryDB, DMS, DynamoDB Accelerator (DAX), Neptune,KeySpaces, Timestream and MemoryDB
        5. Move to Managed Analytics: Lake Formation, Kinesis, EMR, Redshift, MSK, Athena, Glue, QuickSight, OpenSearch, Kendra, MWAA, Appflow, HealthLake
        6. Move to Modern DevOps: CloudFormation, Config, CodeBuild, CodeDeploy, CodePipeline, CodeGuru, Amplify, X-Ray, CodeArtifact, CodeCatalyst, Prometheus, DeviceFarm, DevOpsGuru
        7. Move to AI: Amazon Bedrock, Q Developer, Sagemaker, A2I, Forecast, Lex, Polly, Transcribe, Personalize, Comprehend, Textract, Rekognition, Comprehend Medical, Translate
        8. Additional AWS Services Assessment -Identify any additional AWS services required other the modernisation pathways
        
        Format your response as Table name 'High Level AWS Cost' with the following columns:
        Mondernization Pathway or Additional AWS Services
        AWS Service Name
        Recommend Service Configuration
        Monthly cost in USD($) for AWS region Europe (Ireland) eu-west-1
        Estimate ARR (annual recurring costs) in USD($) 

        (b) For each applicable pathway:
        1. Explain why this pathway is appropriate
        2. Recommend specific AWS services based on provided IT Inventory and include suggested AWS services configuration.
        3. Provide rational bheind selecting AWS services
        4. Estimate monthly costs in USD for all recommended services (provide a estimate in the range of $1,000-$50,000)
        4. Estimate ARR (annual recurring costs) in USD($) for all recommended services (provide a estimate in the range of $1,000-$50,000) for AWS region Europe (Ireland) eu-west-1

        (c) Develop high level implementation approach

        Format your response in markdown to make it readable and structured. Use British English standards.
        """
    return prompt
