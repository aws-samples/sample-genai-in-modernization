import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.wave_runbook.wave_runbook_prompt import get_wave_runbook_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_wave_runbook(
    assessment_json: str,
    strategy_json: str,
    landing_zone_json: str,
) -> AsyncIterator[str]:
    """Stream wave runbook generation via SSE.

    Args:
        assessment_json: Serialized JSON of the full assessment result.
        strategy_json: Strategy result text.
        landing_zone_json: Landing zone result text.

    Yields:
        SSE events: lifecycle (progress), done (full text), error.
    """
    prompt = get_wave_runbook_prompt(assessment_json, strategy_json, landing_zone_json)

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        callback_handler=None,
    )

    yield _sse("lifecycle", "📋 Preparing wave runbook generation...")

    try:
        full_text = ""
        yield _sse("lifecycle", "🔍 Analyzing Wave 1 migration data...")
        async for event in agent.stream_async(
            "Generate the Wave 1 runbook following the output format exactly. Keep it concise."
        ):
            if "data" in event:
                chunk = event["data"]
                full_text += chunk
                if "## Pre-Migration" in chunk:
                    yield _sse("lifecycle", "✅ Building pre-migration checklist...")
                elif "## Test Cutover" in chunk:
                    yield _sse("lifecycle", "🧪 Defining test cutover steps...")
                elif "## Cutover Execution" in chunk:
                    yield _sse("lifecycle", "🚀 Planning cutover execution...")
                elif "## Rollback" in chunk:
                    yield _sse("lifecycle", "🔄 Documenting rollback plan...")
                elif "## Communication" in chunk:
                    yield _sse("lifecycle", "📢 Building communication plan...")
                elif "## Timeline" in chunk:
                    yield _sse("lifecycle", "📅 Creating timeline...")

        yield _sse("lifecycle", "✅ Wave runbook generation complete")
        yield _sse("done", full_text)
    except Exception as e:
        yield _sse("error", str(e))
