# Architecture: AWS Transform Agent Composability

This document explains how the Calculator Review Agent works end-to-end, covering Bedrock AgentCore, AWS Transform (ATX) composability, the SDK, the runtime container, and the Agent Registry.

---

## System Overview

```
+---------------------------------------------------------------------------------+
|                         AWS Transform (ATX) Platform                            |
|                                                                                 |
|  +--------------+    +------------------+    +------------------------------+   |
|  |  Transform   |    |  ATX Agent       |    |  ATX Agentic API             |   |
|  |  Web Console |--->|  Registry        |--->|  (Job Orchestration)         |   |
|  |  (User Chat) |    |  (Discovery)     |    |  elasticgumbyagenticservice  |   |
|  +--------------+    +------------------+    +---------------+--------------+   |
|                                                              |                  |
+--------------------------------------------------------------+------------------+
                                                               |
                                              Assumes AWSTransformAgentInvokeRole
                                                               |
                                                               v
+---------------------------------------------------------------------------------+
|                         Amazon Bedrock AgentCore                                |
|                                                                                 |
|  +-------------------------------------------------------------------------+    |
|  |  Agent Runtime: calculator_review_agent_<timestamp>                     |    |
|  |  Status: READY | Network: PUBLIC | Role: AgentCoreExecutionRole         |    |
|  |                                                                         |    |
|  |  +-------------------------------------------------------------------+  |    |
|  |  |  Container (ARM64, Python 3.11)                                   |  |    |
|  |  |                                                                   |  |    |
|  |  |  +-----------------+   +------------------+   +--------------+    |  |    |
|  |  |  | AgentRuntime    |   | AsyncBase        |   | Agentic MCP  |    |  |    |
|  |  |  | Server          |-->| Orchestrator     |-->| Server       |    |  |    |
|  |  |  | (Flask :8080)   |   | (Strands Agent)  |   | (Tool Use)   |    |  |    |
|  |  |  +-----------------+   +--------+---------+   +--------------+    |  |    |
|  |  |                                 |                                 |  |    |
|  |  |                    +------------+------------+                    |  |    |
|  |  |                    v            v            v                    |  |    |
|  |  |           +--------------+ +----------+ +------------------+      |  |    |
|  |  |           | Custom Tools | | Bedrock  | | Agentic API      |      |  |    |
|  |  |           | (review_     | | Models   | | (invoke other    |      |  |    |
|  |  |           |  tools.py)   | | (Claude  | |  subagents)      |      |  |    |
|  |  |           |              | |  4.5     | |                  |      |  |    |
|  |  |           |              | | Sonnet)  | |                  |      |  |    |
|  |  |           +--------------+ +----------+ +------------------+      |  |    |
|  |  |                                                                   |  |    |
|  |  +-------------------------------------------------------------------+  |    |
|  +-------------------------------------------------------------------------+    |
|                                                                                 |
+---------------------------------------------------------------------------------+
                                       |
                                       | Pulls image from
                                       v
                              +------------------+
                              |  Amazon ECR      |
                              |  aws-transform-  |
                              |  agents/         |
                              |  calculator-     |
                              |  review-agent    |
                              +------------------+
```

---

## Component Deep Dive

### 1. AWS Transform (ATX) Platform

The ATX platform is the user-facing layer. It provides:

- **Web Console** — Where users (SAs, partners, customers) interact with agents via chat
- **Workspace** — A project context where multiple agents collaborate
- **Job Orchestration** — Routes user messages to the correct agent, manages job lifecycle

When a user sends a message in the Transform console:
1. Transform identifies which agent should handle it (based on agent capabilities in the registry)
2. Creates a "job" via the Agentic API
3. Invokes the agent's runtime via Bedrock AgentCore

### 2. ATX Agent Registry

The registry is the **discovery and composability layer**. It answers: "What agents exist, what can they do, and how do I invoke them?"

```
Registry Endpoint: https://iad.prod.agent-registry-external.elastic-gumby.ai.aws.dev
Service Name:      atxagentregistryexternal
```

**What's stored per agent:**

| Field | Purpose |
|-------|---------|
| `name` | Unique identifier (e.g., `calculator-review-agent`) |
| `version` | Semantic version (e.g., `1.0.0`) |
| `metadata.type` | `ORCHESTRATOR_AGENT` or `SUBAGENT` |
| `agentCard` | A2A-style card describing capabilities |
| `computeConfiguration.runtimeArn` | Points to the Bedrock AgentCore runtime |
| `computeConfiguration.atxAccessRoleArn` | IAM role Transform assumes to invoke |
| `visibility` | `PUBLIC` or `RESTRICTED` |
| `status` | `ACTIVE`, `INACTIVE`, `DEPRECATED` |

**Key operations:**

| Operation | Purpose |
|-----------|---------|
| `RegisterAgent` | Create a new agent entry |
| `PublishAgentVersion` | Publish a version with configuration |
| `GetAgent` / `GetAgentVersion` | Retrieve agent metadata |
| `UpdatePublisherAccessControl` | Grant/revoke account access |
| `ListAgentsByPublisher` | List your published agents |

**Composability:** When an orchestrator agent wants to invoke a subagent, it discovers it through the registry. The registry provides the runtime ARN and access role needed to make the call.

### 3. Amazon Bedrock AgentCore

AgentCore is the **compute and hosting layer**. It:

- Pulls your container image from ECR
- Runs it on managed ARM64 infrastructure
- Handles scaling, health checks, and networking
- Provides the invocation endpoint that Transform calls

```
Service: bedrock-agentcore-control (management)
         bedrock-agentcore (data plane / invocation)
```

**Runtime lifecycle:**

```
create-agent-runtime --> CREATING --> READY --> (invocable)
                                           --> FAILED (if health check fails)
```

**Runtime naming convention:**
The deploy scripts generate runtime names using the pattern `calculator_review_agent_<timestamp>` (e.g., `calculator_review_agent_1716048000`). The CloudFormation deployment uses `calculator_review_agent_<unix_epoch>`.

**What AgentCore provides to your container:**
- Network connectivity (PUBLIC mode = outbound internet)
- IAM credentials via the execution role (for calling Bedrock models, other AWS services)
- Workload identity tokens (for agent-to-agent auth)
- Health check monitoring (`GET /ping` every 30s)

### 4. The AWS Transform Agent SDK

The SDK is the **framework layer** that runs inside your container. It handles all the platform integration so you only write business logic.

```
Package: agent_builder_sdk (agent-builder-sdk-aws-transform on PyPI)
Version: 1.0.1+
Requires: Python >=3.11, <3.14
```

**Key classes:**

| Class | Module | Purpose |
|-------|--------|---------|
| `AgentRuntimeServer` | `agent_builder_sdk.server.agent_runtime_server` | Flask server that handles `/ping`, `/invoke`, message routing |
| `AsyncBaseOrchestrator` | `agent_builder_sdk.orchestrator_strands.base_orchestrator` | Base class for orchestrator agents (multi-source conversation, Strands integration) |
| `AsyncBaseSubagent` | `agent_builder_sdk.base_subagent.base_subagent` | Base class for subagents |

**What the SDK does for you:**
1. Starts a Flask server on port 8080
2. Handles health checks (`/ping`)
3. Receives invocation messages from AgentCore
4. Manages conversation history (multi-source: human, subagent, notification)
5. Integrates with Strands Agents for LLM orchestration
6. Provides the Agentic MCP server for tool use (invoke subagents, manage jobs)
7. Handles workload identity and auth token refresh

**Server configuration:**
- `host`: `0.0.0.0` (all interfaces)
- `port`: `8080`
- `delayed_timeout`: `3600` (1 hour max invocation time)

### 5. The Agentic MCP Server

The MCP (Model Context Protocol) server runs as a sidecar process inside the container. It exposes platform operations as tools that the LLM can call.

```
Binary: /home/amazon/AgentBuilderAgenticMCP/bin/agent-builder-agentic-mcp
Module: agent_builder_agentic_mcp
PyPI:   agent-builder-agentic-mcp-aws-transform
```

**Tools it provides to the orchestrator:**
- `invoke_agent` — Call another agent (subagent) via the Agentic API
- `get_job_status` — Check the status of an async job
- `send_notification` — Send status updates back to the user
- `get_agent_info` — Look up agent capabilities from the registry

This is how **composability** works: your orchestrator's LLM can decide to invoke other agents as tools, creating multi-agent workflows.

### 6. The Runtime Container

The container is the **deployment artifact**. It packages everything needed to run your agent.

```dockerfile
FROM python:3.11-slim (ARM64)

Contents:
+-- ATX SDK wheels (from PyPI: agent-builder-sdk-aws-transform)
+-- ATX MCP package (from PyPI: agent-builder-agentic-mcp-aws-transform)
+-- ATX types package (from PyPI: agent-builder-types-aws-transform)
+-- ATX MCP client (from PyPI: agent-builder-mcp-client-aws-transform)
+-- Botocore service models (bundled in SDK, registered at build time)
+-- MCP server wrapper script (/home/amazon/AgentBuilderAgenticMCP/bin/)
+-- Your agent source code (calculator_review_agent/)
+-- requirements.txt dependencies (requests, strands-agents)
+-- ENTRYPOINT: python -m calculator_review_agent.calculator_review_cli
```

**Container startup sequence:**
1. `calculator_review_cli.py` runs
2. Creates `AgentRuntimeServer` with your `agent_factory` and `delayed_timeout=3600`
3. Server starts Flask on `0.0.0.0:8080`
4. AgentCore sends `/ping` — container responds 200 → runtime becomes READY
5. When a job arrives, server calls `agent_factory(mcp_client)`
6. Factory creates `CalculatorReviewOrchestrator` instance with:
   - System prompt loaded from `prompts/system_prompt.md`
   - Model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
   - Custom tools: `[analyze_calculator_url]`
   - MCP clients: `[mcp_client]` (for Agentic API tools)
7. Orchestrator processes the message using Strands + Claude Sonnet 4.5 + your tools

---

## Request Flow: End to End

```
User types in Transform Console
        |
        v
+-------------------------------------------------------------+
| 1. Transform Platform                                        |
|    - Identifies agent from registry (calculator-review-agent)|
|    - Creates job via Agentic API                             |
|    - Assumes AWSTransformAgentInvokeRole                     |
+---------------------------------+---------------------------+
                                  |
                                  v
+-------------------------------------------------------------+
| 2. Bedrock AgentCore                                         |
|    - Receives InvokeAgentRuntime call                        |
|    - Routes to container at :8080/invoke                     |
|    - Passes message payload + context                        |
+---------------------------------+---------------------------+
                                  |
                                  v
+-------------------------------------------------------------+
| 3. AgentRuntimeServer (inside container)                     |
|    - Deserializes request into ProcessMessageRequest         |
|    - Calls agent_factory() to get orchestrator instance      |
|    - Passes message to AsyncBaseOrchestrator                 |
+---------------------------------+---------------------------+
                                  |
                                  v
+-------------------------------------------------------------+
| 4. AsyncBaseOrchestrator (CalculatorReviewOrchestrator)      |
|    - Manages conversation history (multi-source)             |
|    - Sends system_prompt + message to Strands Agent          |
|    - Strands Agent calls Claude Sonnet 4.5 (via Bedrock)     |
|    - Claude decides to use tools (analyze_calculator_url)    |
|    - Tool executes, result returned to Claude                |
|    - Claude generates final response (3 tabs)                |
+---------------------------------+---------------------------+
                                  |
                                  v
+-------------------------------------------------------------+
| 5. Response flows back                                       |
|    Container --> AgentCore --> Agentic API --> Transform UI  |
|    User sees the analysis in the chat window                 |
+-------------------------------------------------------------+
```

---

## Tool: `analyze_calculator_url`

The single custom tool exposed to the LLM. Implemented in `tools/review_tools.py`, backed by `core/analyzer.py`.

**Input:** AWS Pricing Calculator URL (ESC or non-ESC)

**Output:** Structured analysis covering three tabs:

| Tab | Content |
|-----|---------|
| **Tab 1: Service Breakdown** | Per-service costs, MAP-qualified MRR, data transfer exclusions, EC2 Savings Plans, RDS/Redshift/ElastiCache/OpenSearch RI, EBS gp2→gp3 and io1→io2, Fargate Compute SP, Graviton migration |
| **Tab 2: Modernization Pathways** | 6 pathway classifications (Move to AI, Cloud Native, Containers, Managed Analytics, Managed Databases, Modern DevOps), Modernization Index, per-pathway ARR |
| **Tab 3: Service Completeness** | AI-powered gap analysis across 6 categories (Backup, Storage, DR/HA, Network, Observability, Security), compute/non-compute ratio vs 56/44 benchmark, missing services with estimated costs |

**Core analysis engine** (`core/analyzer.py` — `CalcReviewAnalyzer`):

| Method | Purpose |
|--------|---------|
| `analyze_url()` | Main entry point — fetches estimate, runs all analysis |
| `_process_node()` | Recursively walks estimate tree |
| `_extract_service_entry()` | Extracts cost data per service |
| `_run_ec2_sp_optimization()` | EC2 Savings Plans pricing lookups |
| `_run_ri_optimization()` | Reserved Instance optimization (RDS, Redshift, ElastiCache, OpenSearch) |
| `_run_ebs_optimization()` | EBS volume migration (gp2→gp3, io1→io2) |
| `_add_advisory_notes()` | Fargate Compute SP and Graviton recommendations |
| `_calculate_outbound_dt_cost()` | Data transfer exclusion calculations |
| `_aggregate_services()` | Combines line items into service-level view |
| `_calculate_pathways()` | Modernization pathway classification |
| `_fetch_pricing_json()` | Fetches real-time AWS pricing data |
| `_load_service_manifest()` | Loads calculator service manifest |

---

## IAM Role Chain

Understanding who assumes what role and why:

```
+------------------+         +-----------------------------+
| User (Identity   |         | AWSTransformAgentInvokeRole |
| Center / Console)|-------->|                             |
|                  | assumes |  Trusted by:                |
+------------------+         |   prod.us-east-1.compute.   |
                             |   elastic-gumby.aws.internal|
                             |                             |
                             | Permissions:                |
                             |  - bedrock-agentcore:       |
                             |    InvokeAgentRuntime       |
                             |  - bedrock-agentcore:       |
                             |    GetAgentRuntime          |
                             |  - bedrock-agentcore:       |
                             |    GetAgentRuntimeEndpoint  |
                             +---------------+-------------+
                                             | calls
                                             v
                             +-----------------------------+
                             | Bedrock AgentCore           |
                             | (runs your container with   |
                             |  AgentCoreExecutionRole)    |
                             +---------------+-------------+
                                             | container uses
                                             v
                             +-----------------------------+
                             | AgentCoreExecutionRole      |
                             |                             |
                             | Trusted by:                 |
                             |  bedrock-agentcore.         |
                             |  amazonaws.com              |
                             |                             |
                             | Permissions:                |
                             |  - bedrock:InvokeModel      |
                             |  - bedrock:Converse         |
                             |  - transform-agents:*       |
                             |  - eg-agenticapi:*          |
                             |  - ecr:GetDownloadUrl...    |
                             |  - logs:PutLogEvents        |
                             |  - xray:PutTraceSegments    |
                             |  - bedrock-agentcore:       |
                             |    GetWorkloadAccessToken   |
                             +-----------------------------+
```

**Key insight:** The container itself doesn't have AWS credentials baked in. AgentCore injects credentials via the execution role, similar to how ECS task roles work.

---

## Composability: Multi-Agent Workflows

The real power of ATX is composability — agents invoking other agents:

```
+-----------------------------------------------------------------+
|                    ATX Workspace                                 |
|                                                                  |
|  User: "Review this calculator and create a migration plan"      |
|                                                                  |
|  +----------------------------------------------------------+    |
|  |  Workspace Orchestrator (ATX built-in)                    |   |
|  |  Decides which agents to invoke based on capabilities     |   |
|  +----------------+-------------------------+---------------+    |
|                   |                         |                    |
|                   v                         v                    |
|  +------------------------+   +----------------------------+     |
|  |  Calculator Review     |   |  Migration Planning        |     |
|  |  Agent (yours)         |   |  Agent (another team's)    |     |
|  |                        |   |                            |     |
|  |  Analyzes pricing URL  |   |  Creates wave plan from    |     |
|  |  Returns: cost data,   |   |  inventory + cost data     |     |
|  |  MAP MRR, optimization |   |                            |     |
|  +------------------------+   +----------------------------+     |
|                                                                  |
+-----------------------------------------------------------------+
```

**How discovery works:**
1. Agents register in the ATX Agent Registry with an `agentCard` describing capabilities
2. The workspace orchestrator queries the registry to find agents matching the task
3. It invokes them via the Agentic API using their `runtimeArn`
4. Results flow back and are composed into a unified response

**How invocation works (agent-to-agent):**
```python
# Inside an orchestrator, the Agentic MCP server provides invoke_agent as a tool
# The LLM decides when to call it based on the task

# Under the hood:
# 1. MCP server calls elasticgumbyagenticservice.InvokeAgent
# 2. Agentic API assumes the target agent's invoke role
# 3. Calls bedrock-agentcore:InvokeAgentRuntime
# 4. Target agent processes and responds
# 5. Response returned to calling orchestrator
```

---

## Project Structure

```
calculator-review-agent/
+-- src/
|   +-- calculator_review_agent/
|       +-- __init__.py
|       +-- calculator_review_cli.py        # Entry point (AgentRuntimeServer)
|       +-- core/
|       |   +-- __init__.py
|       |   +-- analyzer.py                 # CalcReviewAnalyzer (analysis engine)
|       |   +-- constants.py                # Pricing URLs, region maps, pathway mappings
|       +-- prompts/
|       |   +-- system_prompt.md            # LLM system prompt (3-tab output format)
|       +-- tools/
|           +-- __init__.py
|           +-- review_tools.py             # @tool analyze_calculator_url
+-- infrastructure/
|   +-- cloudformation-deploy.yaml          # One-click deployment (ECR + CodeBuild + AgentCore + Registry)
|   +-- iam-roles.yaml                      # Standalone IAM role definitions
+-- Dockerfile                              # ARM64 container build
+-- build.sh                                # Local container build script
+-- deploy.sh                               # Full deploy pipeline (build + ECR + AgentCore)
+-- requirements.txt                        # Python deps (requests, strands-agents)
+-- README.md                               # Setup and usage guide
+-- ARCHITECTURE.md                         # This file
+-- LICENSE
```

---

## Deployment Pipeline

```
+----------+    +----------+    +----------+    +----------+    +----------+
|  Source  |    |  Build   |    |   ECR    |    | AgentCore|    | Registry |
|  Code    |--->|  Image   |--->|  Push    |--->|  Deploy  |--->| Publish  |
|          |    | (ARM64)  |    |          |    |          |    |          |
+----------+    +----------+    +----------+    +----------+    +----------+
                     |
                     | pip install from PyPI
                     v
            +------------------+
            | PyPI Packages    |
            | agent-builder-   |
            | sdk-aws-transform|
            | (v1.0.1+)        |
            +------------------+
```

| Stage | Tool | What Happens |
|-------|------|--------------|
| Build | `finch build` or CodeBuild | Installs SDK from PyPI, creates MCP wrapper, copies agent source |
| Push | `finch push` or CodeBuild | Pushes ARM64 image to ECR (`aws-transform-agents/calculator-review-agent`) |
| Deploy | `aws bedrock-agentcore-control create-agent-runtime` | Creates runtime, AgentCore pulls image, starts container, polls `/ping` |
| Register | CloudFormation custom resource or manual | Publishes version with runtime ARN to ATX Agent Registry |

**Two deployment paths:**

1. **Manual** (`deploy.sh`): Build locally with finch/docker, push to ECR, create AgentCore runtime
2. **CloudFormation** (`infrastructure/cloudformation-deploy.yaml`): One-click deployment — creates ECR repo, triggers CodeBuild (ARM64), deploys AgentCore runtime, registers with ATX Agent Registry, sets up Cognito auth

---

## Key Endpoints and Service Names

| Service | Endpoint | CLI Service Name |
|---------|----------|-----------------|
| ATX Agent Registry | `https://iad.prod.agent-registry-external.elastic-gumby.ai.aws.dev` | `atxagentregistryexternal` |
| ATX Agentic API | (internal, via MCP server) | `elasticgumbyagenticservice` / `transformagenticservice` |
| Bedrock AgentCore Control | `https://bedrock-agentcore-control.us-east-1.amazonaws.com` | `bedrock-agentcore-control` |
| Bedrock AgentCore Data | `https://bedrock-agentcore.us-east-1.amazonaws.com` | `bedrock-agentcore` |
| ECR | `https://<account>.dkr.ecr.us-east-1.amazonaws.com` | `ecr` |

---

## Botocore Service Models

The AWS Transform APIs are not in the public AWS SDK. The `agent-builder-sdk-aws-transform` package bundles custom botocore models that must be registered:

```bash
# Models are bundled inside the SDK package
SDK_MODELS=$(python -c "from importlib.resources import files; print(files('agent_builder_sdk').joinpath('botocore_models'))")

# Agent Registry API
aws configure add-model --service-name atxagentregistryexternal \
  --service-model "file://${SDK_MODELS}/atxagentregistryexternal/2022-07-26/service-2.json"

# Agentic API (job orchestration, agent invocation)
aws configure add-model --service-name transformagenticservice \
  --service-model "file://${SDK_MODELS}/transformagenticservice/2018-05-10/service-2.json"
```

These get installed to `~/.aws/models/` and enable `aws atxagentregistryexternal ...` and `aws transformagenticservice ...` CLI commands. The Dockerfile registers these models at build time.

---

## Security Model

```
+-------------------------------------------------------------+
|                    Trust Boundaries                          |
|                                                              |
|  +--------------------------------------------------------+  |
|  | ATX Platform (trusted)                                  | |
|  |  - Authenticates users via Identity Center              | |
|  |  - Assumes AWSTransformAgentInvokeRole to call agents   | |
|  +--------------------------------------------------------+  |
|                          |                                   |
|                          v                                   |
|  +--------------------------------------------------------+  |
|  | Bedrock AgentCore (trusted)                             | |
|  |  - Validates IAM caller has InvokeAgentRuntime          | |
|  |  - Injects execution role credentials into container    | |
|  |  - Provides workload identity tokens for A2A auth       | |
|  +--------------------------------------------------------+  |
|                          |                                   |
|                          v                                   |
|  +--------------------------------------------------------+  |
|  | Your Container (your code)                              | |
|  |  - Runs with AgentCoreExecutionRole permissions         | |
|  |  - Can call Bedrock models, write logs                  | |
|  |  - Can invoke other agents via Agentic API              | |
|  |  - Cannot access resources outside its role policy      | |
|  +--------------------------------------------------------+  |
|                                                              |
+-------------------------------------------------------------+
```

**Agent-to-Agent authentication:**
When your orchestrator invokes a subagent, the Agentic MCP server uses workload identity tokens (obtained via `bedrock-agentcore:GetWorkloadAccessToken`) to authenticate. The target agent's invoke role trusts the ATX platform service principal.

---

## Glossary

| Term | Definition |
|------|-----------|
| **AgentCore** | AWS managed service that hosts and runs agent containers |
| **Runtime** | A deployed instance of your agent container in AgentCore |
| **Agent Registry** | ATX service for publishing and discovering agents |
| **Agentic API** | ATX service for job management and agent-to-agent invocation |
| **Agent Card** | A2A-style metadata describing an agent's capabilities |
| **Composability** | The ability for agents to discover and invoke each other |
| **MCP** | Model Context Protocol — standard for exposing tools to LLMs |
| **Strands** | AWS agent framework (Strands Agents) used by the SDK for LLM orchestration |
| **Workload Identity** | Token-based auth for agent-to-agent communication |
| **ATX** | AWS Transform — the platform for modernization and migration |
| **MAP** | Migration Acceleration Program — AWS incentive program |
| **ESC** | European Sovereign Cloud — separate AWS partition with EUR pricing |
| **MRR** | Monthly Recurring Revenue — MAP-qualified spend metric |
