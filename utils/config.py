# utils/config.py
"""
Configuration settings for AWS migration and modernisation tools
"""

import os
from typing import Dict

# AWS Configuration
AWS_REGION = "us-east-1"
BEDROCK_CONFIG = {
    "read_timeout": 300,  # 5 minutes
    "connect_timeout": 60,
    "retries": {"max_attempts": 3},
}

# Model Configuration
CLAUDE_3_7_SONNET_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


# Default Model Parameters
DEFAULT_MAX_TOKENS = 121072
DEFAULT_TEMPERATURE = 0.7
DEFAULT_REASONING_BUDGET = 2000


# PDF Processing Configuration (only MEDIA_TYPE is used)
MEDIA_TYPE = "image/png"

# File Paths Configuration
FILE_PATHS = {"resource_profile": "sampledata/resource_profile_template.csv"}


def get_aws_region() -> str:
    """Get AWS region from environment or default"""
    return os.getenv("AWS_REGION", AWS_REGION)


def get_model_config(model_type: str = "claude_3_7") -> Dict:
    """Get model configuration based on type"""
    if model_type == "claude_3_7":
        return {
            "model_id": CLAUDE_3_7_SONNET_MODEL_ID,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "reasoning_budget": DEFAULT_REASONING_BUDGET,
        }
    raise ValueError(
        f"Unsupported model type: {model_type}. Currently only 'claude_3_7' is supported."
    )
