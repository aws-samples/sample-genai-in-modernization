FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install AWS Transform SDK from PyPI (public release v1.0.1+)
RUN pip install --no-cache-dir \
    agent-builder-sdk-aws-transform \
    agent-builder-agentic-mcp-aws-transform \
    agent-builder-types-aws-transform \
    agent-builder-mcp-client-aws-transform

# Set ATX platform environment variables
ENV STAGE=prod
ENV AWS_REGION=us-east-1

# Register botocore service models (bundled in the SDK package)
RUN pip install --no-cache-dir awscli && \
    SDK_MODELS=$(python -c "from importlib.resources import files; print(files('agent_builder_sdk').joinpath('botocore_models'))") && \
    aws configure add-model --service-name atxagentregistryexternal \
      --service-model "file://${SDK_MODELS}/atxagentregistryexternal/2022-07-26/service-2.json" && \
    aws configure add-model --service-name transformagenticservice \
      --service-model "file://${SDK_MODELS}/transformagenticservice/2018-05-10/service-2.json"

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create MCP server wrapper binary (matches SDK default path)
RUN mkdir -p /home/amazon/AgentBuilderAgenticMCP/bin && \
    echo '#!/bin/bash' > /home/amazon/AgentBuilderAgenticMCP/bin/agent-builder-agentic-mcp && \
    echo 'python -m agent_builder_agentic_mcp "$@"' >> /home/amazon/AgentBuilderAgenticMCP/bin/agent-builder-agentic-mcp && \
    chmod +x /home/amazon/AgentBuilderAgenticMCP/bin/agent-builder-agentic-mcp

# Copy subagent source
COPY src/calculator_review_agent/ ./calculator_review_agent/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

ENTRYPOINT ["python", "-m", "calculator_review_agent.calculator_review_cli"]
