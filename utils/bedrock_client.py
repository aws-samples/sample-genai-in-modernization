"""
AWS Bedrock client utilities for invoking various models.
"""

import json

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .config import BEDROCK_CONFIG, get_aws_region, get_model_config


def _create_bedrock_client():
    """Create and return AWS Bedrock runtime client."""
    config = Config(**BEDROCK_CONFIG)
    return boto3.client("bedrock-runtime", region_name=get_aws_region(), config=config)


def invoke_bedrock_model_without_reasoning(text_content):
    """
    Invoke Bedrock model without reasoning capabilities.

    Args:
        text_content (str): The text content to process

    Returns:
        str: The model's response text, or None if an error occurs
    """
    model_config = None
    try:
        client = _create_bedrock_client()
        model_config = get_model_config("claude_3_7")

        # Use provided parameters or defaults from config
        max_tokens = model_config["max_tokens"]
        # Prepare the request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,  # Increased for longer PDF analysis
            "messages": [{"role": "user", "content": text_content}],
        }

        # Make the API call
        response = client.invoke_model(
            modelId=model_config["model_id"], body=json.dumps(body)
        )

        # Parse response
        response_content = json.loads(response["body"].read())
        return response_content["content"][0]["text"]

    except (BotoCoreError, ClientError) as e:
        model_id = (
            model_config["model_id"]
            if model_config and "model_id" in model_config
            else "claude_3_7"
        )
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return None
    except KeyError as e:
        print(f"ERROR: Missing key in response: {e}")
        return None
    except (json.JSONDecodeError, TypeError) as e:
        print(f"ERROR: Failed to parse response: {e}")
        return None


def invoke_bedrock_model_with_reasoning(prompt: str):
    """
    Invoke Bedrock model with reasoning capabilities using configuration settings from config.py.

    Args:
        prompt (str): The user prompt for the model

    Returns:
        dict: Dictionary containing both reasoning and response text
    """
    model_config = None
    try:
        client = _create_bedrock_client()
        model_config = get_model_config("claude_3_7")

        # Create the message with the user's prompt
        conversation = [
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ]

        # Configure reasoning parameters with specified token budget
        reasoning_config = {
            "thinking": {
                "type": "enabled",
                "budget_tokens": model_config["reasoning_budget"],
            }
        }

        # Send message and reasoning configuration to the model
        response = client.converse(
            modelId=model_config["model_id"],
            messages=conversation,
            additionalModelRequestFields=reasoning_config,
        )

        # Extract the list of content blocks from the model's response
        content_blocks = response["output"]["message"]["content"]

        reasoning = None
        text = None

        # Process each content block to find reasoning and response text
        for block in content_blocks:
            if "reasoningContent" in block:
                reasoning = block["reasoningContent"]["reasoningText"]["text"]
            if "text" in block:
                text = block["text"]

        return {
            "reasoning": reasoning,
            "response": text if text else "No text response received from the model.",
            "success": True,
        }

    except (BotoCoreError, ClientError) as e:
        model_id = (
            model_config["model_id"]
            if model_config and "model_id" in model_config
            else "claude_3_7"
        )
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return {"reasoning": None, "response": None, "success": False, "error": str(e)}
    except KeyError as e:
        print(f"ERROR: Missing key in response: {e}")
        return {"reasoning": None, "response": None, "success": False, "error": str(e)}


def invoke_bedrock_model_for_image_analysis(onprem_image, prompt, image_type):
    """
    Invoke Bedrock model for image analysis with text prompt.

    Args:
        onprem_image (str): Base64 encoded image data
        prompt (str): Text prompt for image analysis
        image_type (str): MIME type of the image

    Returns:
        str: The model's analysis response, or None if an error occurs
    """
    model_config = None
    try:
        client = _create_bedrock_client()
        model_config = get_model_config("claude_3_7")

        # Use provided parameters or defaults from config
        max_tokens = model_config["max_tokens"]
        image_format = image_type

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_format,
                                "data": onprem_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }

        response = client.invoke_model(
            modelId=model_config["model_id"], body=json.dumps(body)
        )

        response_content = json.loads(response["body"].read())
        return response_content["content"][0]["text"]

    except (BotoCoreError, ClientError) as e:
        model_id = (
            model_config["model_id"]
            if model_config and "model_id" in model_config
            else "claude_3_7"
        )
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return None
    except KeyError as e:
        print(f"ERROR: Missing key in response: {e}")
        return None
    except (json.JSONDecodeError, TypeError) as e:
        print(f"ERROR: Failed to parse response: {e}")
        return None
