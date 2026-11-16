import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.chat.chat_prompt import get_chat_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat(
    message: str,
    assessment_json: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Stream a chat response over the assessment context.

    Args:
        message: The user's current question.
        assessment_json: Serialized JSON of the full assessment result.
        history: Optional list of prior messages, each with "role" and "content".

    Yields:
        SSE events: text (incremental tokens), done (empty), error.
    """
    system_prompt = get_chat_prompt(assessment_json)

    agent = Agent(
        system_prompt=system_prompt,
        model=get_model(),
        callback_handler=None,
    )

    # Prepopulate agent.messages with conversation history for multi-turn context.
    # Strands maintains history in agent.messages — we inject prior turns so the
    # agent sees the full conversation when processing the current message.
    if history:
        for msg in history:
            agent.messages.append(
                {
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}],
                }
            )

    try:
        full_text = ""
        # Pass current user message as a plain string — Strands pattern
        async for event in agent.stream_async(message):
            if "data" in event:
                full_text += event["data"]
                yield _sse("text", event["data"])

        yield _sse("done", full_text)
    except Exception as e:
        yield _sse("error", str(e))
