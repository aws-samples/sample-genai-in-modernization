#!/usr/bin/env python3
"""
AWS CDK Stack for Business Case Generator - Option 4 (Simple ALB)

Architecture:
- ALB with OIDC authentication
- ECS Fargate service (Flask serves both frontend and API)
- S3 buckets for file storage
- DynamoDB for case metadata
- Route 53 for custom domain

Build timestamp: 2026-03-05 12:00 - 3yr RI pricing + removed ARR Calculator
"""

from aws_cdk import (
    App, Stack, Duration, RemovalPolicy, SecretValue,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct
import os

class BusinessCaseGeneratorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Configuration - All from environment variables (no hardcoded values)
        domain_name = os.environ.get('DOMAIN_NAME')
        certificate_arn = os.environ.get('CERTIFICATE_ARN')
        hosted_zone_id = os.environ.get('HOSTED_ZONE_ID')
        
        # OIDC Configuration
        oidc_issuer = os.environ.get('OIDC_ISSUER')
        oidc_client_id = os.environ.get('OIDC_CLIENT_ID')
        oidc_client_secret = os.environ.get('OIDC_CLIENT_SECRET')
        oidc_authorization_endpoint = os.environ.get('OIDC_AUTHORIZATION_ENDPOINT')
        oidc_token_endpoint = os.environ.get('OIDC_TOKEN_ENDPOINT')
        oidc_user_info_endpoint = os.environ.get('OIDC_USER_INFO_ENDPOINT')
        
        # Validate required parameters
        required_params = {
            'DOMAIN_NAME': domain_name,
            'CERTIFICATE_ARN': certificate_arn,
            'HOSTED_ZONE_ID': hosted_zone_id,
            'OIDC_ISSUER': oidc_issuer,
            'OIDC_CLIENT_ID': oidc_client_id,
            'OIDC_CLIENT_SECRET': oidc_client_secret,
            'OIDC_AUTHORIZATION_ENDPOINT': oidc_authorization_endpoint,
            'OIDC_TOKEN_ENDPOINT': oidc_token_endpoint,
            'OIDC_USER_INFO_ENDPOINT': oidc_user_info_endpoint,
        }
        
        missing_params = [k for k, v in required_params.items() if not v]
        if missing_params:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_params)}\n"
                f"Please run deploy.sh which will prompt for these values."
            )
        
        # ====================================================================
        # VPC
        # ====================================================================
        vpc = ec2.Vpc(
            self, "VPC",
            max_azs=2,
            nat_gateways=1,  # Cost optimization
        )
        
        # ====================================================================
        # S3 Buckets
        # ====================================================================
        input_bucket = s3.Bucket(
            self, "InputBucket",
            bucket_name=f"business-case-input-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        
        output_bucket = s3.Bucket(
            self, "OutputBucket",
            bucket_name=f"business-case-output-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        
        # ====================================================================
        # DynamoDB Table
        # ====================================================================
        table = dynamodb.Table(
            self, "CasesTable",
            table_name="business-case-cases",
            partition_key=dynamodb.Attribute(
                name="caseId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )
        
        # Add GSI for user queries
        table.add_global_secondary_index(
            index_name="UserIdIndex",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
        )
        
        # ====================================================================
        # ECS Cluster
        # ====================================================================
        cluster = ecs.Cluster(
            self, "Cluster",
            cluster_name="business-case-cluster",
            vpc=vpc,
            container_insights=True,
        )
        
        # ====================================================================
        # Task Definition
        # ====================================================================
        task_definition = ecs.FargateTaskDefinition(
            self, "TaskDef",
            memory_limit_mib=2048,
            cpu=1024,
        )
        
        # Grant permissions
        input_bucket.grant_read_write(task_definition.task_role)
        output_bucket.grant_read_write(task_definition.task_role)
        table.grant_read_write_data(task_definition.task_role)
        
        # Grant Bedrock permissions (all regions for cross-region inference)
        task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*:*:foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            )
        )
        
        # Grant AWS Pricing API permissions (for real-time pricing)
        task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "pricing:GetProducts",
                    "pricing:DescribeServices",
                    "pricing:GetAttributeValues",
                ],
                resources=["*"],  # Pricing API doesn't support resource-level permissions
            )
        )
        
        # Grant Savings Plans API permissions (for real-time savings plan rates)
        task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "savingsplans:DescribeSavingsPlansOfferingRates",
                    "savingsplans:DescribeSavingsPlansOfferings",
                ],
                resources=["*"],  # Savings Plans API doesn't support resource-level permissions
            )
        )
        
        # Build and add container
        # Use platform specification to ensure compatibility
        container = task_definition.add_container(
            "AppContainer",
            image=ecs.ContainerImage.from_asset(
                directory=os.path.join(os.path.dirname(__file__), "../.."),  # Project root
                file="infrastructure/Dockerfile",
                platform=ecr_assets.Platform.LINUX_AMD64,  # Specify platform
                # Use bundling to build in cloud if local Docker not available
                build_args={
                    "BUILDKIT_INLINE_CACHE": "1",
                },
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="business-case",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "FLASK_ENV": "production",
                "AWS_REGION": self.region,
                "S3_INPUT_BUCKET": input_bucket.bucket_name,
                "S3_OUTPUT_BUCKET": output_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": table.table_name,
                "AUTO_SAVE_TO_DYNAMODB": "true",
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')\" || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )
        
        container.add_port_mappings(
            ecs.PortMapping(container_port=8080, protocol=ecs.Protocol.TCP)
        )
        
        # ====================================================================
        # Application Load Balancer with OIDC
        # ====================================================================
        
        # Import existing certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate",
            certificate_arn=certificate_arn
        )
        
        # Create ALB
        alb = elbv2.ApplicationLoadBalancer(
            self, "ALB",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name="business-case-alb",
            idle_timeout=Duration.seconds(600),  # 10 minutes for long-running requests
        )
        
        # Create target group
        target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroup",
            vpc=vpc,
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/api/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )
        
        # Create ECS service
        service = ecs.FargateService(
            self, "Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            service_name="business-case-service",
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60),
        )
        
        # Attach service to target group
        service.attach_to_application_target_group(target_group)
        
        # HTTPS Listener with OIDC
        listener = alb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[certificate],
            default_action=elbv2.ListenerAction.authenticate_oidc(
                issuer=oidc_issuer,
                client_id=oidc_client_id,
                client_secret=SecretValue.unsafe_plain_text(oidc_client_secret),
                authorization_endpoint=oidc_authorization_endpoint,
                token_endpoint=oidc_token_endpoint,
                user_info_endpoint=oidc_user_info_endpoint,
                next=elbv2.ListenerAction.forward([target_group]),
            ),
        )
        
        # HTTP to HTTPS redirect
        alb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.redirect(
                protocol="HTTPS",
                port="443",
                permanent=True,
            ),
        )
        
        # ====================================================================
        # Route 53
        # ====================================================================
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=domain_name,
        )
        
        route53.ARecord(
            self, "AliasRecord",
            zone=hosted_zone,
            record_name=domain_name,
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(alb)
            ),
        )
        
        # ====================================================================
        # Outputs
        # ====================================================================
        from aws_cdk import CfnOutput
        
        CfnOutput(self, "LoadBalancerDNSOutput", value=alb.load_balancer_dns_name)
        CfnOutput(self, "ApplicationURLOutput", value=f"https://{domain_name}")
        CfnOutput(self, "InputBucketOutput", value=input_bucket.bucket_name)
        CfnOutput(self, "OutputBucketOutput", value=output_bucket.bucket_name)
        CfnOutput(self, "DynamoDBTableOutput", value=table.table_name)

# ============================================================================
# App
# ============================================================================
app = App()

BusinessCaseGeneratorStack(
    app, "BusinessCaseGeneratorStack",
    env={
        "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
        "region": os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    },
)

app.synth()
