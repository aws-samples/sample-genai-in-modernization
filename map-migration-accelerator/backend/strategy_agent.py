import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.strategy.strategy_prompt import get_strategy_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_strategy(
    drivers_and_scope: str,
    timeline: str,
    discovery_json: str,
    dependency_json: str,
) -> AsyncIterator[str]:
    """Stream a migration strategy response.

    Args:
        drivers_and_scope: Free-text migration drivers and scope.
        timeline: Free-text timeline and expected start date.
        discovery_json: Serialized JSON of the discovery result.
        dependency_json: Serialized JSON of the dependency result.

    Yields:
        SSE events: lifecycle (progress), done (full text), error.
    """
    prompt = get_strategy_prompt(drivers_and_scope, timeline, discovery_json, dependency_json)

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        callback_handler=None,
    )

    yield _sse("lifecycle", "📋 Analyzing migration inputs...")

    try:
        full_text = ""
        yield _sse("lifecycle", "🔍 Evaluating migration strategies...")
        prompt = (
            "Analyze the provided inputs and generate the migration strategy"
            " following all 4 steps. Use markdown tables for all tabular output."
        )
        async for event in agent.stream_async(prompt):
            if "data" in event:
                chunk = event["data"]
                full_text += chunk
                # Emit lifecycle events as we detect section transitions
                if "## Comparative Analysis" in chunk:
                    yield _sse("lifecycle", "📊 Building comparative analysis...")
                elif "## Final Recommendation" in chunk:
                    yield _sse("lifecycle", "🎯 Synthesizing final recommendation...")
                elif "## Wave Plan" in chunk:
                    yield _sse("lifecycle", "📅 Generating wave plan...")

        yield _sse("lifecycle", "✅ Strategy generation complete")
        yield _sse("done", full_text)
    except Exception as e:
        yield _sse("error", str(e))
