"""
Calculator Review Agent - Entry Point for AWS Transform.

Orchestrator agent that accepts an AWS Pricing Calculator URL (ESC or non-ESC),
fetches the estimate, and analyzes it for service breakdown, MAP qualification,
optimization opportunities, and modernization pathway classification.
"""

import argparse
import logging
import os
from pathlib import Path

from agent_builder_sdk.server.agent_runtime_server import AgentRuntimeServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load system prompt
PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text() if PROMPT_PATH.exists() else ""


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(description="Calculator Review Agent Runtime Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind server to")
    parser.add_argument(
        "--binary-location",
        default="/home/amazon/AgentBuilderAgenticMCP/bin/agent-builder-agentic-mcp",
        help="Path to the agentic MCP server binary",
    )
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    def agent_factory(mcp_client, storage_dir=None):
        """Create the Calculator Review orchestrator instance."""
        from agent_builder_sdk.orchestrator_strands.base_orchestrator import AsyncBaseOrchestrator
        from calculator_review_agent.tools.review_tools import analyze_calculator_url

        # Define orchestrator class INSIDE agent_factory (module-level hangs in containers)
        class CalculatorReviewOrchestrator(AsyncBaseOrchestrator):
            pass

        return CalculatorReviewOrchestrator(
            system_prompt=SYSTEM_PROMPT,
            mcp_clients=[mcp_client] if mcp_client is not None else None,
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            custom_tools=[analyze_calculator_url],
        )

    logger.info("Starting Calculator Review Agent Runtime Server...")
    server = AgentRuntimeServer(
        agent_factory=agent_factory,
        host=args.host,
        port=args.port,
        binary_location=args.binary_location,
        delayed_timeout=3600,
    )

    server.start()


if __name__ == "__main__":
    main()
