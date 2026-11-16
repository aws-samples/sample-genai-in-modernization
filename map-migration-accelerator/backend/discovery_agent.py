"""Strands Agent for CSV-based application and infrastructure discovery analysis.

Architecture:
- analysis_of_application tool: parses CSV, then uses a sub-agent to classify/analyze apps
- analysis_of_infrastructure tool: parses CSV, then uses a sub-agent to analyze infra
- create_*_agent helpers: factory functions for GraphBuilder orchestration
"""

import csv
import io
import json
import os
import sys

from strands import Agent, tool

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.discovery.discovery_prompt import (
    get_app_analysis_prompt,
    get_infra_analysis_prompt,
    get_summary_prompt,
)

# ---------------------------------------------------------------------------
# Internal helper — CSV parsing
# ---------------------------------------------------------------------------


def parse_csv(csv_content: str) -> str:
    """Parse a CSV string, auto-detect columns, and return a JSON array of row dicts."""
    if not csv_content or not csv_content.strip():
        return json.dumps([])

    # Clean BOM and normalize — handle CSVs where entire rows are quoted as single fields
    cleaned = csv_content.strip().lstrip("\ufeff")
    lines = cleaned.split("\n")
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('"') and stripped.count('"') == 2:
            stripped = stripped[1:-1]
        fixed_lines.append(stripped)
    cleaned = "\n".join(fixed_lines)

    reader = csv.reader(io.StringIO(cleaned))

    try:
        headers = next(reader)
    except StopIteration:
        return json.dumps([])

    headers = [h.strip().strip('"') for h in headers]
    if not headers or all(h == "" for h in headers):
        return json.dumps([])

    rows = []
    for row in reader:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        row_dict = {}
        for i, header in enumerate(headers):
            if not header:
                continue
            row_dict[header] = row[i].strip().strip('"') if i < len(row) else ""
        rows.append(row_dict)

    return json.dumps(rows)


# ---------------------------------------------------------------------------
# Sub-agent helper — runs a prompt against an LLM and returns the text
# ---------------------------------------------------------------------------


def _run_analysis(system_prompt: str, data_json: str) -> str:
    """Create a temporary agent with the given system prompt, pass it the
    parsed data, and return the agent's text response."""
    sub_agent = Agent(
        system_prompt=system_prompt,
        model=get_model(),
        callback_handler=None,
    )
    result = sub_agent(f"Analyze this data and return the JSON result:\n\n{data_json}")
    return str(result)


# ---------------------------------------------------------------------------
# Agent factory helpers — used by GraphBuilder orchestration
# ---------------------------------------------------------------------------


def create_app_analysis_agent(app_csv_content: str) -> Agent:
    """Create an Agent for app analysis with CSV data embedded in system prompt.

    Parses CSV to JSON and embeds it in the system prompt so the agent
    carries its own data regardless of what task input the graph provides.
    """
    parsed = parse_csv(app_csv_content)
    system_prompt = get_app_analysis_prompt() + f"\n\n## DATA TO ANALYZE\n{parsed}"
    return Agent(
        name="app_analyst",
        system_prompt=system_prompt,
        model=get_model(),
        callback_handler=None,
    )


def create_infra_analysis_agent(infra_csv_content: str) -> Agent:
    """Create an Agent for infra analysis with CSV data embedded in system prompt.

    Parses CSV to JSON and embeds it in the system prompt so the agent
    carries its own data regardless of what task input the graph provides.
    """
    parsed = parse_csv(infra_csv_content)
    system_prompt = get_infra_analysis_prompt() + f"\n\n## DATA TO ANALYZE\n{parsed}"
    return Agent(
        name="infra_analyst",
        system_prompt=system_prompt,
        model=get_model(),
        callback_handler=None,
    )


def create_summary_agent(dependency_json: str) -> tuple[Agent, str]:
    """Create an Agent for narrative summary and return (agent, task_input).

    Receives dependency analysis JSON, produces migration_rationale,
    circular_dependencies_detail, and enriched executive_summary.
    """
    agent = Agent(
        name="summary_analyst",
        system_prompt=get_summary_prompt(),
        model=get_model(),
        callback_handler=None,
    )
    task = f"Analyze this dependency data and return the enriched JSON:\n\n{dependency_json}"
    return agent, task


# ---------------------------------------------------------------------------
# Strands @tool functions
# ---------------------------------------------------------------------------


@tool
def analysis_of_application(app_csv_content: str) -> str:
    """Parse and analyze application inventory CSV data.

    Parses the raw CSV into structured rows, then runs a dedicated
    analysis agent that classifies each app, identifies risk signals,
    and assesses criticality.

    Args:
        app_csv_content: Raw CSV string of the application inventory.

    Returns:
        JSON string containing the complete app_analysis section with
        applications array and app_summary.
    """
    parsed = parse_csv(app_csv_content)
    prompt = get_app_analysis_prompt()
    return _run_analysis(prompt, parsed)


@tool
def analysis_of_infrastructure(infra_csv_content: str) -> str:
    """Parse and analyze infrastructure inventory CSV data.

    Parses the raw CSV into structured rows, then runs a dedicated
    analysis agent that identifies risk signals, shared servers,
    and maps applications to infrastructure.

    Args:
        infra_csv_content: Raw CSV string of the infrastructure inventory.

    Returns:
        JSON string containing the complete infra_analysis section with
        components array and infra_summary.
    """
    parsed = parse_csv(infra_csv_content)
    prompt = get_infra_analysis_prompt()
    return _run_analysis(prompt, parsed)
