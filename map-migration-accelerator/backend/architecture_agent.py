"""Strands Agent for generating Draw.io XML architecture diagrams."""

import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.architecture_diagram.architecture_diagram_prompt import (
    get_architecture_diagram_prompt,
)


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_diagram(description: str) -> AsyncIterator[str]:
    prompt = get_architecture_diagram_prompt(description)

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        callback_handler=None,
    )

    full_text = ""

    async for event in agent.stream_async(prompt):
        if event.get("init_event_loop"):
            yield _sse("lifecycle", "🔄 Initialising agent...")
        elif event.get("start_event_loop"):
            yield _sse("lifecycle", "▶️ Processing cycle starting...")
        elif event.get("reasoningText"):
            yield _sse("thinking", event["reasoningText"])
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            yield _sse("tool", f"🔧 Using tool: {event['current_tool_use']['name']}")
        elif "data" in event:
            full_text += event["data"]
            yield _sse("text", event["data"])
        elif "result" in event:
            yield _sse("lifecycle", "✅ Generation complete")

    # Validate and clean the XML
    xml = full_text.replace("```xml", "").replace("```", "").strip()
    if "<?xml" not in xml:
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml

    required = ["<mxfile", "<diagram", "<mxGraphModel"]
    missing = [el for el in required if el not in xml]
    if missing:
        yield _sse("error", f"Invalid XML, missing: {missing}")
        return

    yield _sse("done", xml)
