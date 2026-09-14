# Calculator Review Agent for AWS Transform

AI-powered agent that analyzes AWS Pricing Calculator URLs for infrastructure completeness, MAP qualification, cost optimization, and modernization readiness. Deployed to Bedrock AgentCore and registered with the AWS Transform Agent Registry for composability.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed explanation of how all the components (Bedrock AgentCore, AWS Transform, SDK, Registry, etc.) fit together.

---

## Quick Deploy (One-Click CloudFormation)

Download **[cloudformation-deploy.yaml](infrastructure/cloudformation-deploy.yaml)** and upload it to the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home#/stacks/create).

**Prerequisites**: AWS account with Bedrock model access enabled (Claude Sonnet).

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Admin Email | Cognito user (receives temp password) | `you@example.com` |
| Cognito Domain Prefix | Globally unique prefix | `calc-review-agent-myteam` |
| Git Repo URL | Source repository | *(pre-filled)* |
| Agent Name | Registry name | `calculator-review-agent` |
| Agent Version | Semantic version | `1.0.0` |

Stack creation takes ~10-15 minutes. It automatically:
1. Creates IAM roles (AgentCoreExecutionRole with `bedrock:Converse*`, Bedrock AgentCore permissions, Transform Agent permissions)
2. Creates ECR repository
3. Builds ARM64 container via CodeBuild (installs SDK from PyPI)
4. Deploys to Bedrock AgentCore and polls until READY
5. Registers with Agent Registry and enables access
6. Creates Cognito User Pool for direct API access

No manual post-deploy steps required.

### Verify Deployment

```bash
aws cloudformation describe-stacks --stack-name CalculatorReviewAgent \
  --query "Stacks[0].Outputs" --output table
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11–3.13 | AWS Transform Agent SDK |
| AWS CLI | 2.x | Deployment and management |
| Finch or Docker | Any | ARM64 container builds |
| Bedrock Model Access | Enabled | Claude Sonnet in your deployment region |

### IAM Roles Required

Deploy the IAM roles before your first deployment:

```bash
aws cloudformation deploy \
  --template-file infrastructure/iam-roles.yaml \
  --stack-name calculator-review-agent-roles \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

This creates:
- **AgentCoreExecutionRole** — assumed by Bedrock AgentCore to run your container (Bedrock model access, ECR pull, CloudWatch logs, X-Ray, workload identity tokens)
- **AWSTransformAgentInvokeRole** — assumed by the AWS Transform platform to invoke your agent runtime (`bedrock-agentcore:InvokeAgentRuntime`)

---

## Project Structure

```
calculator-review-agent/
├── Dockerfile                          # ARM64 container with AWS Transform SDK
├── build.sh                            # Builds container image
├── deploy.sh                           # Full pipeline: build → ECR → AgentCore
├── requirements.txt                    # Python dependencies (strands-agents, requests)
├── .gitignore                          # Excludes sdk_wheels/ and botocore-models/
├── infrastructure/
│   ├── iam-roles.yaml                  # CloudFormation for IAM roles
│   └── cloudformation-deploy.yaml      # One-click full deployment
├── src/calculator_review_agent/
│   ├── calculator_review_cli.py        # Entry point: AgentRuntimeServer + factory
│   ├── core/
│   │   ├── analyzer.py                 # Calculator URL parsing and analysis logic
│   │   └── constants.py                # MAP-qualified services, thresholds
│   ├── prompts/
│   │   └── system_prompt.md            # LLM system prompt for the orchestrator
│   └── tools/
│       └── review_tools.py             # Custom tool: analyze_calculator_url
├── ARCHITECTURE.md                     # System architecture documentation
└── LICENSE                             # MIT-0 License
```

---

## Build and Deploy

### Method 1: Kiro Power MCP Tools (Recommended for quick deploys)

If you have the **AWS Transform Agent Toolkit** Kiro Power installed, deploy with a single command in Kiro chat:

```
Deploy my calculator-review-agent from ./calculator-review-agent
```

Or call the MCP tool directly:

```
deploy_agent_full_pipeline(
    agent_path="./calculator-review-agent",
    agent_name="calculator-review-agent",
    agent_version="1.0.0",
    job_orchestrator=True,
    a2a_supported=True
)
```

This handles the entire pipeline: build ARM64 image → push to ECR → create AgentCore runtime → register with Agent Registry → enable access control.

**Other useful Power commands:**

| Task | MCP Tool |
|------|----------|
| Build only | `build_agent_image(agent_path="./calculator-review-agent", agent_name="calculator-review-agent")` |
| Deploy to AgentCore only | `deploy_agent_to_agentcore(image_uri="<ecr-uri>", agent_name="calculator-review-agent", execution_role_arn="<role-arn>")` |
| Publish new version | `publish_agent_version(name="calculator-review-agent", version="1.0.1", configuration={...})` |
| Check agent status | `validate_agent_setup(agent_name="calculator-review-agent", agent_version="1.0.0")` |
| View logs | `fetch_logs(log_group_name="/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT", relative_time="5m")` |
| Grant access | `update_publisher_access_control(agent_name="calculator-review-agent", customer_account_id="<account-id>", access_control="ENABLED")` |

### Method 2: Manual CLI (Full control)

Use the provided scripts for step-by-step deployment with full visibility:

```bash
# Full pipeline: build → push to ECR → create AgentCore runtime
./deploy.sh
```

Or step by step:

#### 1. Build the container image

```bash
./build.sh calculator-review-agent latest
```

#### 2. Push to ECR

```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

aws ecr get-login-password --region $REGION | \
  finch login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com

finch tag calculator-review-agent:latest $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/calculator-review-agent:latest
finch push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/calculator-review-agent:latest
```

#### 3. Create AgentCore Runtime

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "calculator_review_agent_v1" \
  --agent-runtime-artifact '{"containerConfiguration":{"containerUri":"'$AWS_ACCOUNT'.dkr.ecr.'$REGION'.amazonaws.com/calculator-review-agent:latest"}}' \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --role-arn "arn:aws:iam::$AWS_ACCOUNT:role/AgentCoreExecutionRole" \
  --region $REGION
```

Poll until READY:
```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id "<runtime-id-from-above>" \
  --region $REGION \
  --query '{status:status, arn:agentRuntimeArn}'
```

#### 4. Register with AWS Transform Agent Registry

```bash
python3 -c "
import boto3, json

client = boto3.client('atxagentregistryexternal', region_name='us-east-1')

AWS_ACCOUNT = boto3.client('sts').get_caller_identity()['Account']
RUNTIME_ARN = '<runtime-arn-from-step-3>'

response = client.publish_agent_version(
    name='calculator-review-agent',
    version='1.0.0',
    configuration={
        'shortDescription': 'Analyzes AWS Pricing Calculator URLs for infrastructure completeness and cost optimization',
        'agentCard': {
            'name': 'Calculator Review Agent',
            'description': 'Analyzes AWS Pricing Calculator for completeness and optimization',
            'id': 'calculator-review-agent',
            'capabilities': {
                'restartable': True,
                'a2aSupported': True,
                'webAppV2': True,
                'legacyRestartable': False,
                'legacyDashboard': False,
                'legacyTaskLink': False,
                'extensions': []
            },
            'version': '1.0.0'
        },
        'computeConfiguration': {
            'provisionedComputeConfiguration': {
                'agentCoreConfiguration': {
                    'atxAccessRoleArn': f'arn:aws:iam::{AWS_ACCOUNT}:role/AWSTransformAgentInvokeRole',
                    'runtimeArn': RUNTIME_ARN,
                    'qualifier': 'DEFAULT'
                }
            }
        },
        'inputPayloadSchema': {'type': 'object'},
        'outputPayloadSchema': {'type': 'object'},
        'monitoringType': 'HEALTHCHECK',
        'notificationsEnabled': 'ENABLED',
        'objectiveNegotiationPrompt': '',
        'stopAgentConfiguration': {
            'enableStoppingWindow': False,
            'stoppingTimeWindowInMinutes': 0
        }
    }
)
print(f'Published: {response[\"name\"]} v{response[\"version\"]} - {response[\"status\"]}')
"
```

#### 5. Grant Access (if restricted visibility)

```bash
python3 -c "
import boto3
client = boto3.client('atxagentregistryexternal', region_name='us-east-1')
client.update_publisher_access_control(
    agentName='calculator-review-agent',
    customerAccountId='<target-account-id>',
    accessControl='ENABLED'
)
print('Access granted')
"
```

### Comparison: Kiro Power vs Manual CLI

| | Kiro Power (Method 1) | Manual CLI (Method 2) |
|---|---|---|
| **Speed** | Single command, ~5 min | Multiple steps, ~10 min |
| **Visibility** | Abstracted — shows summary | Full control over each step |
| **CI/CD** | Not suitable (requires Kiro) | Scripts work in any CI pipeline |
| **Prerequisites** | Kiro + Power installed + MCP connected | Just AWS CLI + finch/docker |
| **Customization** | Limited to tool parameters | Full Dockerfile/script control |
| **Best for** | Iterative development, quick updates | First deploy, CI/CD, custom pipelines |

---

## SDK Details

### Public PyPI Packages

The AWS Transform Agent SDK is publicly available on PyPI:

```bash
pip install agent-builder-sdk-aws-transform \
    agent-builder-agentic-mcp-aws-transform \
    agent-builder-types-aws-transform \
    agent-builder-mcp-client-aws-transform
```

**Note:** Requires Python >=3.11, <3.14.

| Package | PyPI Name | Module |
|---------|-----------|--------|
| Base Agent SDK | `agent-builder-sdk-aws-transform` | `agent_builder_sdk` |
| Agentic MCP | `agent-builder-agentic-mcp-aws-transform` | `agent_builder_agentic_mcp` |
| MCP Client | `agent-builder-mcp-client-aws-transform` | `agent_builder_mcp_client` |
| Types | `agent-builder-types-aws-transform` | `agent_builder_types` |

### Key Imports

```python
from agent_builder_sdk.server.agent_runtime_server import AgentRuntimeServer
from agent_builder_sdk.orchestrator_strands.base_orchestrator import AsyncBaseOrchestrator
```

### Botocore Service Models

The SDK bundles botocore models that must be registered at build time. This is handled automatically in the Dockerfile:

```bash
SDK_MODELS=$(python -c "from importlib.resources import files; print(files('agent_builder_sdk').joinpath('botocore_models'))")
aws configure add-model --service-name atxagentregistryexternal \
  --service-model "file://${SDK_MODELS}/atxagentregistryexternal/2022-07-26/service-2.json"
aws configure add-model --service-name transformagenticservice \
  --service-model "file://${SDK_MODELS}/transformagenticservice/2018-05-10/service-2.json"
```

---

## Local Testing

```bash
# Build the image
./build.sh calculator-review-agent latest

# Run locally (pass your AWS credentials)
finch run -p 8080:8080 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  calculator-review-agent:latest

# Health check
curl http://localhost:8080/ping

# Test invocation (simulates what AgentCore sends)
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this calculator: https://calculator.aws/#/estimate?id=abc123"}'
```

---

## Updating the Agent

When you make code changes (prompts, tools, analyzer logic), follow this workflow to deploy the update:

### Quick Update

```bash
# Set the new version tag
export VERSION=v2  # increment each time

# 1. Build
./build.sh calculator-review-agent $VERSION

# 2. Push to ECR
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region us-east-1 | \
  finch login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
finch tag calculator-review-agent:$VERSION $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/calculator-review-agent:$VERSION
finch push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/calculator-review-agent:$VERSION

# 3. Create new AgentCore runtime
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "calculator_review_agent_$VERSION" \
  --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"$AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/calculator-review-agent:$VERSION\"}}" \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --role-arn "arn:aws:iam::$AWS_ACCOUNT:role/AgentCoreExecutionRole" \
  --region us-east-1

# 4. Wait for READY (usually ~15 seconds)
# Use the runtime ID from step 3 output
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id "<runtime-id>" \
  --region us-east-1 --query '{status:status}'

# 5. Publish new registry version pointing to new runtime
python3 -c "
import boto3
client = boto3.client('atxagentregistryexternal', region_name='us-east-1')
AWS_ACCOUNT = boto3.client('sts').get_caller_identity()['Account']
NEW_RUNTIME = 'arn:aws:bedrock-agentcore:us-east-1:' + AWS_ACCOUNT + ':runtime/<new-runtime-id>'

r = client.publish_agent_version(name='calculator-review-agent', version='1.0.1', configuration={
    'shortDescription': 'Analyzes AWS Pricing Calculator URLs for infrastructure completeness and cost optimization',
    'agentCard': {'name': 'Calculator Review Agent', 'id': 'calculator-review-agent',
        'description': 'Analyzes AWS Pricing Calculator for completeness, MAP qualification, and optimization',
        'capabilities': {'restartable': True, 'a2aSupported': True, 'webAppV2': True,
            'legacyRestartable': False, 'legacyDashboard': False, 'legacyTaskLink': False,
            'extensions': []}, 'version': '1.0.1'},
    'computeConfiguration': {'provisionedComputeConfiguration': {'agentCoreConfiguration': {
        'atxAccessRoleArn': f'arn:aws:iam::{AWS_ACCOUNT}:role/AWSTransformAgentInvokeRole',
        'runtimeArn': NEW_RUNTIME, 'qualifier': 'DEFAULT'}}},
    'inputPayloadSchema': {'type': 'object'}, 'outputPayloadSchema': {'type': 'object'},
    'monitoringType': 'HEALTHCHECK', 'notificationsEnabled': 'ENABLED',
    'objectiveNegotiationPrompt': '',
    'stopAgentConfiguration': {'enableStoppingWindow': False, 'stoppingTimeWindowInMinutes': 0}
})
print(f'{r[\"name\"]}: v{r[\"version\"]} - {r[\"status\"]}')
"
```

### What Requires a Redeploy

| Change | Redeploy Needed? | Why |
|--------|-----------------|-----|
| System prompt (`prompts/system_prompt.md`) | Yes | Baked into container image |
| Tool code (`tools/review_tools.py`) | Yes | Baked into container image |
| Analyzer logic (`core/analyzer.py`) | Yes | Baked into container image |
| IAM role permissions | No | Takes effect immediately |
| Registry metadata (description, card) | No | Just publish new version |
| Model ID change | Yes | Set in `calculator_review_cli.py` |

### Cleanup Old Runtimes (Optional)

Old runtimes keep running and incur costs. Delete them after confirming the new version works:

```bash
# List all your runtimes
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1 \
  --query 'agentRuntimeSummaries[*].[agentRuntimeId,status]' --output table

# Delete old ones (only after new version is confirmed working)
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id "<old-runtime-id>" \
  --region us-east-1
```

---

## What the Agent Analyzes

### Tab 1: Service Breakdown & Cost Analysis

| Feature | Description |
|---------|-------------|
| ESC + non-ESC URLs | Supports `calculator.aws` and `pricing.calculator.aws.eu` |
| MAP-qualified MRR | Excludes data transfer, Glacier Deep Archive, Support |
| EC2 Savings Plans | Real-time pricing API lookups (1yr/No Upfront) |
| RI Optimization | RDS, Redshift, ElastiCache, OpenSearch |
| EBS Optimization | gp2→gp3, io1→io2 migration savings |
| Graviton Advisory | Identifies non-Graviton instances with migration recommendations |
| Fargate SP | Compute Savings Plan calculations |

### Tab 2: Modernization Pathways

| Feature | Description |
|---------|-------------|
| Modernization Index | % of qualified ARR in modern pathways |
| Pathway Classification | AI, Cloud Native, Containers, Analytics, Databases, DevOps |
| Validation | Optimization coverage threshold check |

### Tab 3: Service Completeness (6-Pillar Gap Analysis)

| Category | What It Checks |
|----------|---------------|
| Backup & Recovery (2-3%) | AWS Backup, EBS snapshots, S3 Glacier, cross-region replication |
| Storage (25-30%) | S3 tiers, EFS, FSx, Storage Gateway, EBS |
| DR/HA (1-2%) | Multi-AZ, cross-region replication, Elastic DR, Route 53 health checks |
| Network (10-15%) | ALB/NLB, CloudFront, Route 53, Transit GW, Direct Connect, NAT GW, IPv4 |
| Observability (2-4%) | CloudWatch, CloudTrail, X-Ray, VPC Flow Logs, Config, Systems Manager |
| Security (2-4%) | KMS, WAF, Shield, GuardDuty, Security Hub, Secrets Manager, Network Firewall |

Output includes: Cost Breakdown table, Service Gap Analysis by Category, Missing Services Summary with estimated costs, and Red Flags with conservative/realistic gap estimates.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Container starts but no invocations arrive | SDK not installed correctly | Rebuild with `pip install agent-builder-sdk-aws-transform` |
| `Either endpoint_url or both stage and region must be provided` | Missing `STAGE` env var | Add `ENV STAGE=prod` to Dockerfile |
| `AccessDeniedException` on Bedrock calls | Bedrock resource ARN too restrictive | Set Bedrock actions to `Resource: *` in IAM policy |
| Jobs fail ~8 min after start | Missing Transform Agent permissions on execution role | Update AgentCoreExecutionRole policy |
| Runtime stuck in CREATING | Container health check failing | Check `/ping` endpoint, verify HEALTHCHECK in Dockerfile |
| Agent not discoverable in Transform | Not registered or access not granted | Run `publish_agent_version` + `update_publisher_access_control` |
| Credentials expire during deploy | Session token timeout | Re-run `aws sts get-session-token` or re-authenticate |
| Auth token refresh `KeyError: 'authorizationToken'` | Non-fatal on first request | Ignore — token works, refresh recovers on next cycle |
| Service completeness not showing | Missing from system prompt | Ensure `prompts/system_prompt.md` includes Tab 3 instructions |

---

## Granting Access to Other AWS Accounts

By default, the agent is registered with **RESTRICTED** visibility. Only your own AWS account can discover and invoke it in the Transform console.

### When you need this

- A partner or customer wants to use your agent in their Transform workspace
- Another team in a different AWS account needs to invoke your agent
- You want to share the agent across multiple accounts in your organization

### How to grant access

Using the **AWS Transform Agent Toolkit** Kiro Power:

```
Ask Kiro: "Grant account 123456789012 access to calculator-review-agent"
```

Or via the Power's MCP tool:
```
update_publisher_access_control(
    agent_name="calculator-review-agent",
    customer_account_id="123456789012",
    access_control="ENABLED"
)
```

Using **boto3**:

```python
import boto3

client = boto3.client('atxagentregistryexternal', region_name='us-east-1')

# Grant access to another AWS account
client.update_publisher_access_control(
    agentName='calculator-review-agent',
    customerAccountId='<target-account-id>',
    accessControl='ENABLED'
)
print('Access granted')
```

To revoke access:
```python
client.update_publisher_access_control(
    agentName='calculator-review-agent',
    customerAccountId='<target-account-id>',
    accessControl='DISABLED'
)
```

To list who currently has access:
```python
response = client.list_agent_access_control(name='calculator-review-agent')
print('Accounts with access:', response.get('customerAccountIdList', []))
```

> **Note:** The SDK resolves the Agent Registry endpoint automatically from `STAGE` and `AWS_REGION` environment variables. You do not need to specify an `endpoint_url` when using the SDK inside a deployed container.

---

## Security

See [LICENSE](LICENSE) for license information.

If you discover a potential security issue, please notify AWS Security via our [vulnerability reporting page](https://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

When contributing:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-improvement`)
5. Open a Pull Request
