import json
import os
import sys
from collections.abc import AsyncIterator

from strands import Agent
from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.aws_cost.aws_cost_prompt import get_modernization_pathways_cost_prompt
from prompt_library.partner_50k_milestone.partner_50k_milestone import get_milestone_prompt


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


_NODE_EVENT_MAP = {
    "cost_calculator": "cost_done",
    "milestone_prediction": "milestone_done",
}

_NODE_LABELS = {
    "cost_calculator": "AWS cost analysis",
    "milestone_prediction": "Milestone prediction",
}


async def stream_aws_cost(
    assessment_json: str,
    strategy_json: str,
) -> AsyncIterator[str]:
    assessment = json.loads(assessment_json)
    discovery = assessment.get("discovery", {})
    app_analysis = json.dumps(discovery.get("app_analysis", {}))
    infra_analysis = json.dumps(discovery.get("infra_analysis", {}))
    inventory_csv = (
        f"Application Analysis:\n{app_analysis}\n\nInfrastructure Components:\n{infra_analysis}"
    )

    cost_prompt = get_modernization_pathways_cost_prompt(inventory_csv, strategy_json)
    milestone_prompt = get_milestone_prompt("{input}", strategy_json)

    yield _sse("lifecycle", "Starting AWS cost analysis workflow...")

    cost_agent = Agent(
        name="cost_calculator",
        system_prompt=cost_prompt,
        model=get_model(),
        callback_handler=None,
    )
    milestone_agent = Agent(
        name="milestone_prediction",
        system_prompt=milestone_prompt,
        model=get_model(),
        callback_handler=None,
    )

    builder = GraphBuilder()
    builder.add_node(cost_agent, "cost_calculator")
    builder.add_node(milestone_agent, "milestone_prediction")
    builder.add_edge("cost_calculator", "milestone_prediction")
    builder.set_entry_point("cost_calculator")
    builder.set_execution_timeout(600)
    graph = builder.build()

    yield _sse("lifecycle", "Analysing modernisation pathways and estimating costs...")

    node_outputs: dict[str, str] = {}

    try:
        async for event in graph.stream_async(
            "Analyse the IT inventory and generate the AWS modernisation cost analysis. "
            "Use markdown tables for all tabular output."
        ):
            event_type = event.get("type", "")

            if event_type == "multiagent_node_start":
                node_id = event["node_id"]
                label = _NODE_LABELS.get(node_id, node_id)
                yield _sse("lifecycle", f"Starting {label}...")

            elif event_type == "multiagent_node_stream":
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
                    result_text = node_outputs.get(node_id, "")
                    if not result_text and node_result.result:
                        result_text = str(node_result.result)

                    yield _sse("lifecycle", f"{label} complete")
                    if sse_event:
                        yield _sse(sse_event, result_text)
                else:
                    yield _sse("error", f"{label} agent failed")

    except Exception as e:
        yield _sse("error", f"AWS cost workflow failed: {e}")

    yield _sse("lifecycle", "AWS cost workflow complete")
