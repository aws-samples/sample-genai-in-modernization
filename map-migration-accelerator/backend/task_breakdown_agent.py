import json
import os
import re
import sys
from collections.abc import AsyncIterator

from strands import Agent

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.task_breakdown.task_breakdown_prompt import get_task_breakdown_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from agent output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_wave_plan(strategy_text: str) -> list[dict]:
    """Extract wave plan rows from strategy markdown table.

    Looks for the table under '## Wave Plan' with columns:
    Wave | Timeframe | Application Group | Migration R-Type | ...

    Returns list of dicts with keys: wave, timeframe, app_group, r_type,
    dependency_constraint, risk_tier, prerequisites, notes.
    """
    waves: list[dict] = []
    # Use a simple string split approach to avoid polynomial regex on user data
    marker = "## Wave Plan"
    start_idx = strategy_text.find(marker)
    if start_idx == -1:
        return waves

    # Find the end of the section (next ## heading or end of string)
    section_start = start_idx + len(marker)
    next_heading = strategy_text.find("\n## ", section_start)
    section = strategy_text[section_start:next_heading] if next_heading != -1 else strategy_text[section_start:]
    table_lines = [
        line.strip()
        for line in section.split("\n")
        if line.strip().startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", line.strip())
    ]
    if len(table_lines) < 2:
        return waves

    for row in table_lines[1:]:
        cols = [c.strip() for c in row.split("|") if c.strip()]
        if len(cols) >= 3:
            waves.append(
                {
                    "wave": cols[0] if len(cols) > 0 else "",
                    "timeframe": cols[1] if len(cols) > 1 else "",
                    "app_group": cols[2] if len(cols) > 2 else "",
                    "r_type": cols[3] if len(cols) > 3 else "",
                    "dependency_constraint": cols[4] if len(cols) > 4 else "",
                    "risk_tier": cols[5] if len(cols) > 5 else "",
                    "prerequisites": cols[6] if len(cols) > 6 else "",
                    "notes": cols[7] if len(cols) > 7 else "",
                }
            )
    return waves


async def stream_task_breakdown(
    assessment_json: str,
    strategy_json: str,
    landing_zone_json: str,
) -> AsyncIterator[str]:
    """Stream a task breakdown response.

    Args:
        assessment_json: Serialized JSON of the full assessment result.
        strategy_json: Serialized JSON/text of the strategy result.
        landing_zone_json: Serialized JSON/text of the landing zone result.

    Yields:
        SSE events: lifecycle (progress), done (structured JSON), error.
    """
    # Parse wave plan from strategy markdown for explicit context
    wave_plan = _parse_wave_plan(strategy_json)
    wave_plan_json = json.dumps(wave_plan) if wave_plan else "[]"

    prompt = get_task_breakdown_prompt(
        assessment_json,
        strategy_json,
        landing_zone_json,
        wave_plan_json,
    )

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        callback_handler=None,
    )

    yield _sse("lifecycle", "📋 Analyzing wave plan...")

    try:
        full_text = ""
        yield _sse("lifecycle", "🔨 Building task breakdown...")
        async for event in agent.stream_async(
            "Produce the task breakdown JSON for all migration waves. Output ONLY valid JSON."
        ):
            if "data" in event:
                full_text += event["data"]

        yield _sse("lifecycle", "✅ Task breakdown complete")

        result = _extract_json(full_text)
        if result is None:
            yield _sse("error", "Failed to parse task breakdown output as JSON")
            return

        yield _sse("done", json.dumps(result))
    except Exception as e:
        yield _sse("error", str(e))
