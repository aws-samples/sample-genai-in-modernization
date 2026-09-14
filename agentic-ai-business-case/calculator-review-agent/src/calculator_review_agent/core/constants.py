"""
Constants for Calculator Review Agent.
Ported from ui/backend/map_routes.py to keep the agent self-contained.
"""

# ============================================================================
# AWS Calculator API endpoints
# ============================================================================
CALC_CLOUDFRONT_URL = 'https://d3knqfixx3sbls.cloudfront.net/{}'
CALC_ESC_URL = 'https://pricing.calculator.aws.eu/getSavedEstimates/{}'
CALC_MANIFEST_URL = 'https://d3knqfixx3sbls.cloudfront.net/manifest.json'
FULL_TIME_HOURS_PER_WEEK = 168
HOURS_PER_MONTH = 730

# ============================================================================
# EC2 Savings Plans pricing
# ============================================================================
EC2_PRICING_BASE_URL = 'https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps'

# European Sovereign Cloud (ESC) configuration
ESC_PRICING_BASE_URL = 'https://artifacts.eusc-de-east-1.prod.plc.billing.a2z.eu/pricing/2.0/meteredUnitMaps/aws-eusc'
ESC_REGION_CODE = 'eusc-de-east-1'
ESC_CURRENCY = 'EUR'
ESC_REGION_NAME = 'AWS European Sovereign Cloud (Germany)'

# Data transfer pricing URLs
DT_PRICING_URL = 'https://calculator.aws/pricing/2.0/meteredUnitMaps/datatransfer/USD/current/datatransfer-calc.json'
ESC_DT_PRICING_URL = 'https://artifacts.eusc-de-east-1.prod.plc.billing.a2z.eu/pricing/2.0/meteredUnitMaps/aws-eusc/datatransfer/EUR/current/datatransfer-calc.json'
CF_PRICING_URL = 'https://calculator.aws/pricing/2.0/metaredUnitMaps/cloudfront/USD/current/cloudfront.json'

# EBS pricing URLs
EBS_PRICING_URL = 'https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ebs.json'
ESC_EBS_PRICING_URL = 'https://artifacts.eusc-de-east-1.prod.plc.billing.a2z.eu/pricing/2.0/meteredUnitMaps/aws-eusc/ec2/EUR/current/ebs-calculator.json'

# ============================================================================
# Region mappings
# ============================================================================
REGION_CODE_TO_NAME = {
    'us-east-1': 'US East (N. Virginia)',
    'us-east-2': 'US East (Ohio)',
    'us-west-1': 'US West (N. California)',
    'us-west-2': 'US West (Oregon)',
    'eu-central-1': 'EU (Frankfurt)',
    'eu-central-2': 'EU (Zurich)',
    'eu-west-1': 'EU (Ireland)',
    'eu-west-2': 'EU (London)',
    'eu-west-3': 'EU (Paris)',
    'eu-north-1': 'EU (Stockholm)',
    'eu-south-1': 'EU (Milan)',
    'eu-south-2': 'EU (Spain)',
    'ap-south-1': 'Asia Pacific (Mumbai)',
    'ap-south-2': 'Asia Pacific (Hyderabad)',
    'ap-northeast-1': 'Asia Pacific (Tokyo)',
    'ap-northeast-2': 'Asia Pacific (Seoul)',
    'ap-northeast-3': 'Asia Pacific (Osaka)',
    'ap-southeast-1': 'Asia Pacific (Singapore)',
    'ap-southeast-2': 'Asia Pacific (Sydney)',
    'ap-southeast-3': 'Asia Pacific (Jakarta)',
    'ap-southeast-4': 'Asia Pacific (Melbourne)',
    'ap-southeast-5': 'Asia Pacific (Malaysia)',
    'ap-southeast-7': 'Asia Pacific (Thailand)',
    'ca-central-1': 'Canada (Central)',
    'ca-west-1': 'Canada West (Calgary)',
    'sa-east-1': 'South America (Sao Paulo)',
    'ap-east-1': 'Asia Pacific (Hong Kong)',
    'me-south-1': 'Middle East (Bahrain)',
    'me-central-1': 'Middle East (UAE)',
    'af-south-1': 'Africa (Cape Town)',
    'il-central-1': 'Israel (Tel Aviv)',
    'mx-central-1': 'Mexico (Central)',
    'ap-southeast-6': 'Asia Pacific (Taipei)',
    'eusc-de-east-1': 'AWS European Sovereign Cloud (Germany)',
}

REGION_NAME_TO_CODE = {v: k for k, v in REGION_CODE_TO_NAME.items()}

# ============================================================================
# Service display name mapping
# ============================================================================
SERVICE_DISPLAY_NAMES = {
    'ec2Enhancement': 'Amazon EC2',
    'amazonVirtualPrivateCloud': 'Amazon Virtual Private Cloud (VPC)',
    'dataTransferVpc': 'Data Transfer',
    'publicIpv4Address': 'Amazon Virtual Private Cloud (VPC)',
    'networkAddressTranslationNatGatewayVpc': 'Amazon Virtual Private Cloud (VPC)',
    'transitGatewayVpc': 'Amazon Virtual Private Cloud (VPC)',
    'awsKeyManagementService': 'AWS Key Management Service',
    'awsCloudTrail': 'AWS CloudTrail',
    'amazonCloudWatch': 'Amazon CloudWatch',
    'awsSystemsManagerAutomation': 'AWS Systems Manager',
    'aWSStorageGateway': 'AWS Storage Gateway',
    'amazonCloudFront': 'Amazon CloudFront',
    'awsWebApplicationFirewall': 'AWS Web Application Firewall (WAF)',
    'awsSecretsManager': 'AWS Secrets Manager',
    'applicationLoadBalancer': 'Elastic Load Balancing',
    'networkLoadBalancer': 'Elastic Load Balancing',
    'amazonS3Standard': 'Amazon Simple Storage Service (S3)',
    'awsS3DataTransfer': 'Amazon Simple Storage Service (S3)',
    'amazonRDSMySQLDB': 'Amazon RDS for MySQL',
    'amazonRDSPostgreSQLDB': 'Amazon RDS for PostgreSQL',
    'amazonRDSMariaDB': 'Amazon RDS for MariaDB',
    'amazonRDSForSQLServer': 'Amazon RDS for SQL Server',
    'amazonRDSAuroraPostgreSQLCompatibleDB': 'Amazon Aurora PostgreSQL-Compatible',
    'amazonAuroraMySQLCompatible': 'Amazon Aurora MySQL-Compatible',
    'amazonElastiCache': 'Amazon ElastiCache',
    'amazonEFS': 'Amazon Elastic File System (EFS)',
    'amazonDynamoDB': 'Amazon DynamoDB',
    'amazonDynamoDbOnDemand': 'Amazon DynamoDB',
    'awsFargate': 'AWS Fargate',
    'awsEks': 'Amazon EKS',
    'amazonElasticContainerRegistry': 'Amazon Elastic Container Registry',
    'aWSLambda': 'AWS Lambda',
    'amazonApiGateway': 'Amazon API Gateway',
    'amazonSageMaker': 'Amazon SageMaker',
    'amazonBedrock': 'Amazon Bedrock',
    'amazonRedshift': 'Amazon Redshift',
    'amazonElasticsearchService': 'Amazon OpenSearch Service',
    'amazonOpenSearchService': 'Amazon OpenSearch Service',
    'amazonKinesisDataStreams': 'Amazon Kinesis Data Streams',
    'amazonKinesisFirehose': 'Amazon Data Firehose',
    'amazonManagedStreamingForApacheKafkaMsk': 'Amazon MSK',
    'awsGlue': 'AWS Glue',
    'amazonAthena': 'Amazon Athena',
    'amazonCognito': 'Amazon Cognito',
    'amazonEventBridge': 'Amazon EventBridge',
    'amazonSimpleQueueService': 'Amazon SQS',
    'amazonSimpleNotificationService': 'Amazon SNS',
    'awsStepFunctions': 'AWS Step Functions',
    'amazonRoute53': 'Amazon Route 53',
    'awsConfig': 'AWS Config',
    'amazonGuardDuty': 'Amazon GuardDuty',
    'awsShield': 'AWS Shield',
    'amazonMQ': 'Amazon MQ',
    'awsCodeBuild': 'AWS CodeBuild',
    'awsCodePipeline': 'AWS CodePipeline',
    'amazonNeptune': 'Amazon Neptune',
    'amazonDocumentDB': 'Amazon DocumentDB',
    'amazonMemoryDbForRedis': 'Amazon MemoryDB',
    'amazonTimestream': 'Amazon Timestream',
    'awsAppRunner': 'AWS App Runner',
    'awsAmplify': 'AWS Amplify',
    'amazonS3GlacierDeepArhive': 'Amazon S3 Glacier Deep Archive',
    'AWSDeveloperSupport': 'AWS Developer Support',
    'AWSSupportBusiness': 'AWS Business Support',
    'AWSSupportEnterprise': 'AWS Enterprise Support',
    'AWSEnterpriseOnRamp': 'AWS Enterprise On-Ramp Support',
    'amazonSimpleStorageServiceGroup': 'Amazon Simple Storage Service (S3)',
}

# Services whose cost should always be excluded (data transfer, not MAP eligible)
ALWAYS_EXCLUDE_DT_SERVICES = {
    'dataTransferVpc', 'networkAddressTranslationNatGatewayVpc',
    'awsS3DataTransfer',
}

# ============================================================================
# Modernization pathway mapping
# ============================================================================
_PATHWAY_SERVICE_KEYS = {
    "Move to AI": [
        "amazon augmented ai", "amazon bedrock", "amazon comprehend", "amazon comprehend medical",
        "amazon forecast", "amazon lex", "amazon personalize", "amazon polly",
        "amazon q developer", "amazon rekognition", "amazon sagemaker",
        "amazon sagemaker ground truth", "amazon textract", "amazon transcribe",
        "amazon transcribe medical", "amazon translate", "amazon bedrock agentcore",
    ],
    "Move to Cloud Native": [
        "aws appsync", "aws lambda", "aws step functions", "amazon api gateway",
        "amazon cognito", "amazon eventbridge", "amazon mq",
        "amazon simple notification service", "amazon simple queue service",
        "awslambda", "amazonapigateway", "amazoncognito", "amazoneventbridge",
        "amazonsqs", "amazonsns", "awsstepfunctions",
    ],
    "Move to Containers": [
        "aws app runner", "aws fargate", "amazon eks", "amazon elastic container registry",
        "amazon ecs", "awseks", "awsfargate", "awsapprunner",
    ],
    "Move to Managed Analytics": [
        "aws glue", "aws lake formation", "amazon appflow", "amazon athena",
        "amazon data firehose", "amazon emr", "amazon healthlake", "amazon kendra",
        "amazon kinesis data streams", "amazon kinesis video streams",
        "amazon managed service for apache flink",
        "amazon managed streaming for apache kafka",
        "amazon managed workflows for apache airflow",
        "amazon opensearch service", "amazon quicksight", "amazon redshift",
        "amazon kinesis",
        "amazonelasticsearchservice", "amazonopensearchservice",
        "amazonredshift", "amazonathena", "awsglue", "amazonmsk",
    ],
    "Move to Managed Databases": [
        "aws database migration service", "amazon aurora",
        "amazon documentdb", "amazon dynamodb", "amazon elasticache",
        "amazon keyspaces", "amazon managed blockchain", "amazon memorydb",
        "amazon neptune", "amazon rds", "amazon timestream",
        "amazonelasticache", "amazondynamodb", "amazonaurora", "amazonneptune",
        "amazondocumentdb", "amazonmemorydb", "amazonrds",
    ],
    "Move to Modern DevOps": [
        "aws amplify", "aws cloudformation", "aws codeartifact", "aws codebuild",
        "aws codedeploy", "aws codepipeline", "aws config", "aws device farm",
        "aws x-ray", "amazon codeguru", "amazon managed service for prometheus",
    ],
}

# Build the lookup: for each pathway, store lowercased service name keys
_PATHWAY_LOOKUP = []
for _pathway_name, _service_names in _PATHWAY_SERVICE_KEYS.items():
    for _svc in _service_names:
        _PATHWAY_LOOKUP.append((_svc.lower().replace(' ', ''), _pathway_name))
# Sort longest first so more specific matches win
_PATHWAY_LOOKUP.sort(key=lambda x: len(x[0]), reverse=True)

# RDS service codes
RDS_SERVICE_CODES = {
    'amazonRDSMySQLDB', 'amazonRDSPostgreSQLDB', 'amazonRDSMariaDB',
    'amazonRDSForSQLServer', 'amazonAuroraMySQLCompatible',
    'amazonRDSAuroraPostgreSQLCompatibleDB',
}

# io2 supported regions
IO2_SUPPORTED_REGIONS = {
    'US East (Ohio)', 'US East (N. Virginia)', 'US West (N. California)', 'US West (Oregon)',
    'Asia Pacific (Hong Kong)', 'Asia Pacific (Mumbai)', 'Asia Pacific (Seoul)',
    'Asia Pacific (Singapore)', 'Asia Pacific (Sydney)', 'Asia Pacific (Tokyo)',
    'Canada (Central)', 'Europe (Frankfurt)', 'Europe (Ireland)', 'Europe (London)',
    'Europe (Stockholm)', 'Middle East (Bahrain)', 'AWS European Sovereign Cloud (Germany)',
}

# CloudFront calculator field suffix to region name mapping
CF_CALC_REGION_MAP = {
    '_US': 'United States', '_Canada': 'Canada', '_AP': 'Asia Pacific',
    '_Australia': 'Australia', '_EU': 'EU', '_India': 'India',
    '_Japan': 'Japan', '_ME': 'Middle East', '_SA': 'South Africa',
    '_SouthAmerica': 'South America',
}

# CloudFront tiers (in GB)
CF_TIERS = [
    ('First 10 TB', 0, 10240),
    ('Next 40 TB', 10240, 51200),
    ('next 100 TB', 51200, 153600),
    ('Next 350 TB', 153600, 512000),
    ('next 524 TB', 512000, 1048576),
    ('Next 4 PB', 1048576, 5242880),
    ('Over 5 PB', 5242880, float('inf')),
]

# Data transfer region mapping
DT_REGION_TO_LOCATION = {
    'us-east-1': 'US East (N. Virginia)', 'us-east-2': 'US East (Ohio)',
    'us-west-1': 'US West (N. California)', 'us-west-2': 'US West (Oregon)',
    'eu-central-1': 'EU (Frankfurt)', 'eu-central-2': 'EU (Zurich)',
    'eu-west-1': 'EU (Ireland)', 'eu-west-2': 'EU (London)',
    'eu-west-3': 'EU (Paris)', 'eu-north-1': 'EU (Stockholm)',
    'eu-south-1': 'EU (Milan)', 'eu-south-2': 'EU (Spain)',
    'ap-south-1': 'Asia Pacific (Mumbai)', 'ap-south-2': 'Asia Pacific (Hyderabad)',
    'ap-northeast-1': 'Asia Pacific (Tokyo)', 'ap-northeast-2': 'Asia Pacific (Seoul)',
    'ap-northeast-3': 'Asia Pacific (Osaka)',
    'ap-southeast-1': 'Asia Pacific (Singapore)', 'ap-southeast-2': 'Asia Pacific (Sydney)',
    'ap-southeast-3': 'Asia Pacific (Jakarta)', 'ap-southeast-4': 'Asia Pacific (Melbourne)',
    'ap-southeast-5': 'Asia Pacific (Malaysia)', 'ap-southeast-7': 'Asia Pacific (Thailand)',
    'ca-central-1': 'Canada (Central)', 'ca-west-1': 'Canada West (Calgary)',
    'sa-east-1': 'South America (Sao Paulo)',
    'ap-east-1': 'Asia Pacific (Hong Kong)', 'me-south-1': 'Middle East (Bahrain)',
    'me-central-1': 'Middle East (UAE)',
    'af-south-1': 'Africa (Cape Town)', 'il-central-1': 'Israel (Tel Aviv)',
    'mx-central-1': 'Mexico (Central)', 'ap-southeast-6': 'Asia Pacific (Taipei)',
    'eusc-de-east-1': 'AWS European Sovereign Cloud (Germany)',
}


def classify_service_pathway(service_name: str) -> str:
    """Classify a service into its modernization pathway."""
    normalized = service_name.lower().replace(' ', '')

    # Special case: RDS for SQL Server and Oracle are NOT modern
    if 'rdsforsql' in normalized or 'rdsfororacle' in normalized:
        return 'Non Modern'

    for svc_key, pathway in _PATHWAY_LOOKUP:
        if svc_key in normalized:
            return pathway
    return 'Non Modern'


def get_service_name(service_code: str, manifest: list) -> str:
    """Get display name for a service code."""
    if service_code in SERVICE_DISPLAY_NAMES:
        return SERVICE_DISPLAY_NAMES[service_code]
    for svc in manifest:
        if svc.get('serviceCode') == service_code:
            return svc.get('name', service_code)
    return service_code
