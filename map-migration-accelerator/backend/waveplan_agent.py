"""Strands agent with CreateWavePlan and GetWavePlan tools for Taiga project management."""

import json
import os
from collections.abc import AsyncIterator

import requests
from strands import Agent, tool

# --- Taiga API helpers (from test_epic.py) ---

_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_DIR, "..", "test_project", "taiga_config.json")
DATA_PATH = os.path.join(_DIR, "..", "test_project", "project_data.json")

with open(CONFIG_PATH) as f:
    _cfg = json.load(f)

BASE_URL = _cfg["taiga"]["base_url"]
USERNAME = os.environ.get("TAIGA_USERNAME", "")
PASSWORD = os.environ.get("TAIGA_PASSWORD", "")
PROJECT_SLUG = _cfg["taiga"]["project_slug"]
TIMEOUT = _cfg["settings"]["timeout"]
VERIFY_SSL = _cfg["settings"]["verify_ssl"]
DEFAULT_POINTS = 8


def _api(method, path, token, **kwargs):
    url = f"{BASE_URL}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.request(
        method, url, headers=headers, timeout=TIMEOUT, verify=VERIFY_SSL, **kwargs
    )
    resp.raise_for_status()
    return resp.json() if resp.content else None


def _get_auth_token():
    resp = requests.post(
        f"{BASE_URL}/auth",
        json={"type": "normal", "username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT,
        verify=VERIFY_SSL,
    )
    resp.raise_for_status()
    return resp.json()["auth_token"]


def _get_project(token):
    return _api("GET", f"projects/by_slug?slug={PROJECT_SLUG}", token)


def _ensure_modules(token, project_id):
    project = _api("GET", f"projects/{project_id}", token)
    patch = {}
    if not project.get("is_epics_activated"):
        patch["is_epics_activated"] = True
    if not project.get("is_backlog_activated"):
        patch["is_backlog_activated"] = True
    if patch:
        _api("PATCH", f"projects/{project_id}", token, json=patch)
    return project


def _get_default_status(token, project_id):
    statuses = _api("GET", f"userstory-statuses?project={project_id}", token)
    for s in statuses:
        if not s.get("is_closed", False):
            return s["id"]
    return statuses[0]["id"]


def _build_points_map(project):
    points = project.get("points", [])
    roles = project.get("roles", [])
    point_id = next((p["id"] for p in points if p.get("value") == DEFAULT_POINTS), None)
    if not point_id:
        return {}
    return {str(r["id"]): point_id for r in roles if r.get("computable", False)}


# --- Strands Tools ---


@tool
def CreateWavePlan(wave_data_json: str) -> str:
    """Create a wave plan in Taiga with epics, user stories, and tasks.

    Args:
        wave_data_json: JSON string with the wave plan structure. Expected format:
            {"epics": [{"subject": "...", "description": "...", "stories": [
                {"subject": "...", "description": "...", "tasks": [
                    {"subject": "...", "description": "..."}
                ]}
            ]}]}
            If empty or "default", loads from the project_data.json file.

    Returns:
        JSON summary of all created items with their IDs.
    """
    try:
        if not wave_data_json or wave_data_json.strip().lower() == "default":
            with open(DATA_PATH) as f:
                data = json.load(f)
        else:
            data = json.loads(wave_data_json)

        token = _get_auth_token()
        project = _get_project(token)
        project_id = project["id"]
        project_detail = _ensure_modules(token, project_id)
        default_status = _get_default_status(token, project_id)
        points_map = _build_points_map(project_detail)

        created = {"epics": []}

        for epic_data in data.get("epics", []):
            epic_result = _api(
                "POST",
                "epics",
                token,
                json={
                    "project": project_id,
                    "subject": epic_data["subject"],
                    "description": epic_data.get("description", ""),
                },
            )
            epic_id = epic_result["id"]
            epic_record = {"id": epic_id, "subject": epic_data["subject"], "stories": []}

            for story_data in epic_data.get("stories", []):
                payload = {
                    "project": project_id,
                    "subject": story_data["subject"],
                    "description": story_data.get("description", ""),
                    "status": default_status,
                    "milestone": None,
                }
                if points_map:
                    payload["points"] = points_map
                story = _api("POST", "userstories", token, json=payload)
                story_id = story["id"]
                _api(
                    "POST",
                    f"epics/{epic_id}/related_userstories",
                    token,
                    json={"epic": epic_id, "user_story": story_id},
                )

                story_record = {"id": story_id, "subject": story_data["subject"], "tasks": []}

                for task_data in story_data.get("tasks", []):
                    task = _api(
                        "POST",
                        "tasks",
                        token,
                        json={
                            "project": project_id,
                            "user_story": story_id,
                            "subject": task_data["subject"],
                            "description": task_data.get("description", ""),
                        },
                    )
                    story_record["tasks"].append(
                        {"id": task["id"], "subject": task_data["subject"]}
                    )

                epic_record["stories"].append(story_record)
            created["epics"].append(epic_record)

        return json.dumps({"status": "success", "created": created}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def GetWavePlan(include_tasks: str = "true") -> str:
    """Retrieve the current wave plan from Taiga including epics, user stories,
    and optionally tasks.

    Args:
        include_tasks: Whether to include tasks for each user story.
            "true" or "false". Defaults to "true".

    Returns:
        JSON summary of all epics, user stories, and tasks in the project.
    """
    try:
        token = _get_auth_token()
        project = _get_project(token)
        project_id = project["id"]
        fetch_tasks = include_tasks.strip().lower() != "false"

        epics = _api("GET", f"epics?project={project_id}", token) or []
        stories = _api("GET", f"userstories?project={project_id}", token) or []

        # Build epic lookup
        epic_map = {}
        for e in epics:
            epic_map[e["id"]] = {
                "id": e["id"],
                "subject": e["subject"],
                "description": e.get("description", ""),
                "status": e.get("status_extra_info", {}).get("name", ""),
                "stories": [],
            }

        # Map stories to epics
        for s in stories:
            story_record = {
                "id": s["id"],
                "subject": s["subject"],
                "description": s.get("description", ""),
                "total_points": s.get("total_points"),
                "status": s.get("status_extra_info", {}).get("name", ""),
                "location": "Backlog" if s.get("milestone") is None else f"Sprint {s['milestone']}",
            }

            if fetch_tasks:
                tasks = _api("GET", f"tasks?project={project_id}&user_story={s['id']}", token) or []
                story_record["tasks"] = [
                    {
                        "id": t["id"],
                        "subject": t["subject"],
                        "status": t.get("status_extra_info", {}).get("name", ""),
                    }
                    for t in tasks
                ]

            story_epics = [ep["id"] for ep in s.get("epics", [])]
            for eid in story_epics:
                if eid in epic_map:
                    epic_map[eid]["stories"].append(story_record)

            # Stories not linked to any epic
            if not story_epics:
                epic_map.setdefault(
                    "unlinked",
                    {
                        "id": None,
                        "subject": "Unlinked Stories",
                        "description": "",
                        "status": "",
                        "stories": [],
                    },
                )
                epic_map["unlinked"]["stories"].append(story_record)

        result = {"project": PROJECT_SLUG, "epics": list(epic_map.values())}
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# --- Agent definition ---

SYSTEM_PROMPT = """You are a Wave Plan Manager for AWS cloud migration projects.

You help users create and retrieve wave plans in Taiga project management.

- Use CreateWavePlan to create epics, user stories, and tasks from a wave plan structure.
  Pass "default" to load from the project_data.json file, or provide custom JSON.
- Use GetWavePlan to retrieve the current state of all epics, stories, and tasks.

Always confirm what was created or retrieved by summarizing the results clearly."""


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_waveplan(prompt: str) -> AsyncIterator[str]:
    """Stream agent responses as SSE events."""
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[CreateWavePlan, GetWavePlan],
        callback_handler=None,
    )

    yield _sse("lifecycle", "🚀 Wave Plan agent started")

    try:
        full_text = ""
        async for event in agent.stream_async(prompt):
            if "data" in event:
                full_text += event["data"]
                yield _sse("text", event["data"])
    except Exception as e:
        yield _sse("error", f"Agent error: {e}")
        full_text = ""

    yield _sse("lifecycle", "✅ Wave Plan agent complete")
    yield _sse("done", full_text)
