import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent
from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.landing_zone.landing_zone_diagram_prompt import (
    get_landing_zone_diagram_prompt,
)
from prompt_library.landing_zone.landing_zone_prompt import get_landing_zone_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# IaC Agent inline system prompt (no separate prompt file needed)
# ---------------------------------------------------------------------------
IAC_SYSTEM_PROMPT = """You are an AWS CloudFormation specialist.
Given the landing zone design context provided as input from the previous agent,
generate production-ready CloudFormation YAML templates.

## INSTRUCTIONS
Generate CloudFormation YAML snippets for these core landing zone components:
1. Organisation OU Structure — AWS::Organizations resources
2. VPC with Subnets — public, private, and isolated subnets across AZs
3. Transit Gateway Attachment — TGW and VPC attachment
4. IAM Identity Centre Permission Set — SSO permission set configuration

RULES:
- Output ONLY CloudFormation YAML code blocks with brief ## section headers
- Each template must be a complete, deployable YAML wrapped in a ```yaml code block
- Use parameters and mappings where appropriate for reusability
- Include brief comments in YAML for clarity
- No prose explanations — the Design Agent already covers rationale
- Reference specific values from the design (CIDRs, account names, OU names)"""


# ---------------------------------------------------------------------------
# Node-to-SSE event mapping
# ---------------------------------------------------------------------------
_NODE_EVENT_MAP = {
    "design": "design_done",
    "diagram": "diagram_done",
    "iac": "iac_done",
}

_NODE_LABELS = {
    "design": "Landing zone design",
    "diagram": "Architecture diagram",
    "iac": "IaC templates",
}


def _validate_diagram_xml(raw: str) -> str:
    """Clean and validate Draw.io XML from diagram agent output.

    LLMs often wrap the XML in code fences and/or add explanatory prose
    before/after the actual XML.  We extract only the XML portion
    (from ``<?xml`` or ``<mxfile`` through ``</mxfile>``) so the
    frontend viewer receives clean, parseable XML.

    Also fixes common LLM XML mistakes:
    - Unescaped ``&`` in attribute values → ``&amp;``
    """
    import re

    # Strip markdown code fences
    xml = raw.replace("```xml", "").replace("```", "").strip()

    # Extract just the XML portion — LLM may add prose before/after
    match = re.search(r"(<\?xml.*?</mxfile>)", xml, re.DOTALL)
    if not match:
        match = re.search(r"(<mxfile.*?</mxfile>)", xml, re.DOTALL)
    if match:
        xml = match.group(1)
        if "<?xml" not in xml:
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
    else:
        if "<?xml" not in xml:
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml

    # Fix unescaped & — replace bare & that aren't already a valid XML entity
    xml = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", "&amp;", xml)

    required = ["<mxfile", "<diagram", "<mxGraphModel"]
    missing = [el for el in required if el not in xml]
    if missing:
        raise ValueError(f"Invalid diagram XML, missing elements: {missing}")
    return xml


# ---------------------------------------------------------------------------
# Main streaming entry point
# ---------------------------------------------------------------------------


async def stream_landing_zone(
    region: str,
    account_strategy: str,
    connectivity: str,
    discovery_json: str,
    dependency_json: str,
    strategy_json: str,
) -> AsyncIterator[str]:
    """Stream landing zone outputs from three agents via a single SSE endpoint.

    Uses Strands Agent Graph pattern:
      - design + diagram are entry points (run in parallel)
      - design → iac edge (IaC runs after design completes)

    Yields SSE events: lifecycle, design_done, diagram_done, iac_done, error.
    """
    design_prompt = get_landing_zone_prompt(
        region,
        account_strategy,
        connectivity,
        discovery_json,
        dependency_json,
        strategy_json,
    )
    diagram_prompt = get_landing_zone_diagram_prompt(
        region,
        account_strategy,
        connectivity,
        discovery_json,
        dependency_json,
        strategy_json,
    )

    yield _sse("lifecycle", "Starting landing zone multi-agent workflow...")

    # ------------------------------------------------------------------
    # Create the three specialised agents
    # ------------------------------------------------------------------
    design_agent = Agent(
        name="design_agent",
        system_prompt=design_prompt,
        model=get_model(),
        callback_handler=None,
    )
    diagram_agent = Agent(
        name="diagram_agent",
        system_prompt=diagram_prompt,
        model=get_model(),
        callback_handler=None,
    )
    iac_agent = Agent(
        name="iac_agent",
        system_prompt=IAC_SYSTEM_PROMPT,
        model=get_model(),
        callback_handler=None,
    )

    # ------------------------------------------------------------------
    # Build the Graph
    # ------------------------------------------------------------------
    builder = GraphBuilder()
    builder.add_node(design_agent, "design")
    builder.add_node(diagram_agent, "diagram")
    builder.add_node(iac_agent, "iac")

    # IaC depends on design (design output propagated automatically)
    builder.add_edge("design", "iac")

    # Both design and diagram are entry points (run in parallel)
    builder.set_entry_point("design")
    builder.set_entry_point("diagram")

    builder.set_execution_timeout(600)  # 10 minute safety timeout

    graph = builder.build()

    # ------------------------------------------------------------------
    # Stream graph execution and map events to SSE
    # ------------------------------------------------------------------
    yield _sse("lifecycle", "Designing landing zone and generating architecture diagram...")

    node_outputs: dict[str, str] = {}

    try:
        async for event in graph.stream_async(
            "Design the AWS landing zone following all sections. "
            "Use markdown tables for all tabular output."
        ):
            event_type = event.get("type", "")

            if event_type == "multiagent_node_start":
                node_id = event["node_id"]
                label = _NODE_LABELS.get(node_id, node_id)
                yield _sse("lifecycle", f"Starting {label}...")

            elif event_type == "multiagent_node_stream":
                # Collect streaming text per node
                inner = event.get("event", {})
                node_id = event.get("node_id", "")
                if "data" in inner and node_id:
                    node_outputs.setdefault(node_id, "")
                    node_outputs[node_id] += inner["data"]

            elif event_type == "multiagent_node_stop":
                node_id = event["node_id"]
                node_result = event.get("node_result")
                label = _NODE_LABELS.get(node_id, node_id)
                sse_event = _NODE_EVENT_MAP.get(node_id)

                if node_result and node_result.status == Status.COMPLETED:
                    # Extract the full text from the agent result
                    result_text = node_outputs.get(node_id, "")
                    if not result_text and node_result.result:
                        result_text = str(node_result.result)

                    # Post-process diagram XML
                    if node_id == "diagram":
                        try:
                            result_text = _validate_diagram_xml(result_text)
                        except ValueError as e:
                            yield _sse("error", f"Diagram Agent failed: {e}")
                            continue

                    yield _sse("lifecycle", f"{label} complete")
                    if sse_event:
                        yield _sse(sse_event, result_text)
                else:
                    yield _sse("error", f"{label} agent failed")

            elif event_type == "multiagent_result":
                # Final result — workflow complete
                pass

    except Exception as e:
        yield _sse("error", f"Landing zone workflow failed: {e}")

    yield _sse("lifecycle", "Landing zone workflow complete")
