"""Common backend configuration for agents and AWS services."""

import os

# ---------------------------------------------------------------------------
# AWS Configuration
# ---------------------------------------------------------------------------
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", None)

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------
CLAUDE_SONNET_5_5_MODEL_ID = "us.anthropic.claude-sonnet-5-5"
CLAUDE_SONNET_4_6_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

# Override with the BEDROCK_MODEL_ID environment variable if needed
DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", CLAUDE_SONNET_5_5_MODEL_ID)

# ---------------------------------------------------------------------------
# Model Parameters
# ---------------------------------------------------------------------------
DEFAULT_MAX_TOKENS = 65536
DEFAULT_TEMPERATURE = 0.7
DEFAULT_REASONING_BUDGET = 2000

# ---------------------------------------------------------------------------
# SSE / Streaming
# ---------------------------------------------------------------------------
SSE_MEDIA_TYPE = "text/event-stream"

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_aws_region() -> str:
    """Return the configured AWS region."""
    return AWS_REGION
