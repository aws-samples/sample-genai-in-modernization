"""Common backend configuration for agents and AWS services."""

import os

from botocore.config import Config as BotocoreConfig
from strands.models.bedrock import BedrockModel

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

# Thinking effort: low, medium, high (empty = model default, no thinking fields sent)
DEFAULT_EFFORT = os.getenv("BEDROCK_EFFORT", "medium")

# Seconds to wait for the next streamed chunk (long thinking can be silent)
BEDROCK_READ_TIMEOUT = int(os.getenv("BEDROCK_READ_TIMEOUT", "600"))

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


def get_model() -> BedrockModel:
    """Return the shared Bedrock model with token, timeout and thinking settings."""
    extra = None
    if DEFAULT_EFFORT:
        extra = {"thinking": {"type": "adaptive"}, "output_config": {"effort": DEFAULT_EFFORT}}
    return BedrockModel(
        model_id=DEFAULT_MODEL_ID,
        max_tokens=DEFAULT_MAX_TOKENS,
        boto_client_config=BotocoreConfig(read_timeout=BEDROCK_READ_TIMEOUT),
        additional_request_fields=extra,
    )
