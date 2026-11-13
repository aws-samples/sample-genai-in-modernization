# MAP Agentic Accelerator

> [!WARNING]
> **Demo use only — not for production.**
> This repository is a sample to show what generative AI can do in AWS migration and modernisation. It has not been hardened for production or real customer data.
>
> - Authentication, session handling and IAM permissions are simplified for demo purposes.
> - The deployment templates create a **public** load balancer. If you deploy, restrict access to trusted IP ranges, set a strong random `FLASK_SECRET_KEY`, and tear the stack down when the demo is over.
> - Use sample or synthetic data only. Do not upload confidential or personal data.
> - Bedrock model IDs and dependencies may be out of date. Check the [Bedrock model lifecycle](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html) before running.
>
> You are responsible for reviewing and securing any code you deploy into your own AWS account. See the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/).

An AI-powered platform for AWS cloud migration — from initial assessment through business case generation and execution planning. Built with multi-agent orchestration on Amazon Bedrock.

## Components

This repository contains two independent but complementary toolsets:

| Component | Description | Docs |
| --------- | ----------- | ---- |
| **MAP Migration Accelerator** | End-to-end migration lifecycle: portfolio discovery, dependency analysis, strategy, cost estimation, landing zone design, task breakdown, runbooks, and resource planning. Built with Strands Agents SDK and Claude Sonnet 4. | [map-migration-accelerator/README.md](map-migration-accelerator/README.md) |
| **Business Case Generator** | Multi-agent business case generation with real-time AWS pricing, Excel exports, EKS analysis, backup cost modelling, and 9 standalone GenAI use cases. | [agentic-ai-business-case/README.md](agentic-ai-business-case/README.md) |

## Use Cases at a Glance

### MAP Migration Accelerator

| # | Use Case | What It Does |
| - | -------- | ------------ |
| 1 | Portfolio Discovery & Dependency Analysis | Classifies applications, builds dependency graphs, scores migration complexity |
| 2 | Migration & Modernisation Strategy | Evaluates 5 wave planning strategies (WP1–WP5), R-type classification, Gantt charts |
| 3 | AWS Cost Estimation & MAP Milestone Prediction | Monthly/annual cost projections, $50K MAP milestone forecasting |
| 4 | Landing Zone Design | Architecture design, CloudFormation IaC templates, Draw.io diagrams |
| 5 | Task Breakdown & Taiga Integration | Waves → Epics → Stories → Tasks hierarchy, push to Taiga for Kanban tracking |
| 6 | Wave Runbook Generation | Pre-migration checklists, cutover steps, rollback plans, comms templates |
| 7 | Resource Planning | Hub-and-Spoke vs Wave-Based team models, role-based costing |
| 8 | What-If Scenario Chat | Multi-turn chat across any combination of generated outputs |
| 9 | Reports & Artifacts Download | One-click download of all outputs (JSON, MD, YAML, Draw.io XML) |
| 10 | Architecture Diagram Generation | Describe AWS architecture in natural language, generate professional Draw.io XML diagrams |

### Business Case Generator & GenAI Use Cases

| # | Use Case | What It Does |
| - | -------- | ------------ |
| 1 | Business Case Generation | 9-agent system generating 7-section business case with real-time AWS pricing and Excel exports |
| 2 | Learning Pathway | Personalised AWS training and certification roadmaps based on team profiles |
| 3 | Business Case Review | Validate existing business case PDFs against AWS best practices |
| 4 | Service Analysis | Identify missing AWS services and ARR opportunities from Calculator exports |
| 5 | OLA Analysis | Licensing optimisation (Windows, SQL Server, Oracle) with bin-packing and BYOL guidance |
| 6 | EKS Container Migration | Deterministic 4-tier recommendation engine for EC2 vs EKS decisions |
| 7 | AWS Backup Cost Analysis | Intelligent storage tiering with environment-aware retention (up to 85% savings) |
| 8 | Chat Assistant | Context-aware chat with access to all generated outputs |

## Quick Start

### Running the MAP Migration Accelerator

```bash
cd map-migration-accelerator
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
aws configure
uvicorn backend.app:app --host 0.0.0.0 --port 8000  # backend
cd frontend && npm run dev                            # frontend (separate terminal)
```

Full setup: [map-migration-accelerator/README.md](map-migration-accelerator/README.md#quick-start)

### Running the Business Case Generator

```bash
cd agentic-ai-business-case
./setup.sh
./start-all.sh
```

Full setup and AWS deployment options: [agentic-ai-business-case/README.md](agentic-ai-business-case/README.md#quick-start)

## Technology Stack

| Layer | Technology |
| ----- | ---------- |
| **Frontend** | React 18, TypeScript, Cloudscape Design System, Mermaid.js |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI/ML** | Strands Agents SDK, Claude Sonnet 4 / Claude 3 Sonnet (Amazon Bedrock) |
| **Infrastructure** | ECS Fargate, ALB, S3, DynamoDB, Cognito, CloudFormation, CDK |
| **External Services** | Amazon Bedrock, AWS Price List API, Taiga, Draw.io |

## Project Structure

```text
├── map-migration-accelerator/      # MAP Migration Accelerator
│   ├── backend/                    # FastAPI + 12 agents
│   ├── frontend/                   # React + Cloudscape UI
│   ├── prompt_library/             # Per-agent system prompts (12 domains)
│   ├── sample_output/              # Example generated outputs
│   └── README.md                   # Full documentation
├── agentic-ai-business-case/       # Business Case Generator (9-agent system + GenAI use cases)
│   ├── agents/                     # Multi-agent system (analysis, pricing, strategy, export, OLA)
│   └── infrastructure/             # CloudFormation and CDK deployment
├── Usecases_ Streamlit/            # Standalone GenAI use cases (Streamlit UI)
└── README.md                       # ← You are here
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Licence

This project is licensed under the MIT Licence. See the [LICENCE](LICENCE) file for details.

## Support

- Create an issue in the GitHub repository
- [Amazon Bedrock documentation](https://docs.aws.amazon.com/bedrock/)
- [Strands Agents SDK documentation](https://github.com/strands-agents/sdk-python)
- [Cloudscape Design System documentation](https://cloudscape.design/)
- [Business Case Generator setup guide](agentic-ai-business-case/SETUP_GUIDE.md)
- [Business Case Generator architecture](agentic-ai-business-case/SYSTEM_ARCHITECTURE.md)
