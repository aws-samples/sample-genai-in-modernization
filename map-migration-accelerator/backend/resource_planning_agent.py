import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.resource_planning.resource_planning_prompt import get_resource_planning_prompt

RESOURCE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "utils", "resource_profile_template.csv"
)


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _load_resource_csv() -> str:
    with open(RESOURCE_CSV_PATH, newline="") as f:
        return f.read()


async def stream_resource_planning(strategy_json: str) -> AsyncIterator[str]:
    resource_details = _load_resource_csv()
    prompt = get_resource_planning_prompt(strategy_json, strategy_json, resource_details)

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        callback_handler=None,
    )

    yield _sse("lifecycle", "📊 Preparing resource planning analysis...")

    try:
        full_text = ""
        yield _sse("lifecycle", "🔍 Analysing migration strategy and wave data...")
        async for event in agent.stream_async(
            "Generate the resource planning report following the output format exactly."
        ):
            if "data" in event:
                chunk = event["data"]
                full_text += chunk
                if "## Executive Summary" in chunk:
                    yield _sse("lifecycle", "📋 Building executive summary...")
                elif "Team structure" in chunk:
                    yield _sse("lifecycle", "🏗️ Evaluating team structures...")
                elif "Resource summary" in chunk:
                    yield _sse("lifecycle", "📈 Calculating resource summary...")
                elif "Role-Based" in chunk:
                    yield _sse("lifecycle", "👥 Allocating roles and costs...")
                elif "Justification" in chunk:
                    yield _sse("lifecycle", "📝 Writing justification...")

        yield _sse("lifecycle", "✅ Resource planning complete")
        yield _sse("done", full_text)
    except Exception as e:
        yield _sse("error", str(e))
