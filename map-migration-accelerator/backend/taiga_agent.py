import json
import os
import sys
from collections.abc import AsyncIterator

import requests
from strands import Agent, tool

# Allow imports from project root for prompt_library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_model

from prompt_library.taiga.taiga_prompt import get_taiga_prompt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _load_config() -> dict:
    """Load Taiga settings from backend/utils/taiga_config.json.

    Credentials are read from the TAIGA_USERNAME and TAIGA_PASSWORD
    environment variables so they are never stored in the repository.
    """
    config_path = os.path.join(os.path.dirname(__file__), "utils", "taiga_config.json")
    with open(config_path) as f:
        cfg = json.load(f)
    cfg["taiga"]["username"] = os.environ.get("TAIGA_USERNAME", "")
    cfg["taiga"]["password"] = os.environ.get("TAIGA_PASSWORD", "")
    return cfg


def _api(method: str, path: str, token: str, **kwargs) -> dict | None:
    """Common API helper for Taiga REST calls."""
    cfg = _load_config()
    base_url = cfg["taiga"]["base_url"]
    timeout = cfg["settings"]["timeout"]
    verify_ssl = cfg["settings"]["verify_ssl"]
    url = f"{base_url}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.request(
        method, url, headers=headers, timeout=timeout, verify=verify_ssl, **kwargs
    )
    resp.raise_for_status()
    return resp.json() if resp.content else None


# ---------------------------------------------------------------------------
# @tool functions — called by the Strands Agent
# ---------------------------------------------------------------------------


@tool
def authenticate_taiga() -> dict:
    """Authenticate with Taiga API and return auth token."""
    cfg = _load_config()
    taiga = cfg["taiga"]
    if not taiga["username"] or not taiga["password"]:
        raise ValueError("Set TAIGA_USERNAME and TAIGA_PASSWORD environment variables")
    resp = requests.post(
        f"{taiga['base_url']}/auth",
        json={"type": "normal", "username": taiga["username"], "password": taiga["password"]},
        timeout=cfg["settings"]["timeout"],
        verify=cfg["settings"]["verify_ssl"],
    )
    resp.raise_for_status()
    data = resp.json()
    return {"token": data["auth_token"]}


@tool
def get_project(token: str) -> dict:
    """Get project by slug, ensure epics/backlog modules are enabled.
    Returns project_id, default_status_id, and points_map."""
    cfg = _load_config()
    slug = cfg["taiga"]["project_slug"]

    project = _api("GET", f"projects/by_slug?slug={slug}", token)
    project_id = project["id"]

    # Ensure modules
    patch = {}
    if not project.get("is_epics_activated"):
        patch["is_epics_activated"] = True
    if not project.get("is_backlog_activated"):
        patch["is_backlog_activated"] = True
    if patch:
        _api("PATCH", f"projects/{project_id}", token, json=patch)
        project = _api("GET", f"projects/{project_id}", token)

    # Default status (first non-closed)
    statuses = _api("GET", f"userstory-statuses?project={project_id}", token)
    default_status_id = statuses[0]["id"]
    for s in statuses:
        if not s.get("is_closed", False):
            default_status_id = s["id"]
            break

    # Points map (8 points per computable role)
    points = project.get("points", [])
    roles = project.get("roles", [])
    point_id = next((p["id"] for p in points if p.get("value") == 8), None)
    points_map = {}
    if point_id:
        points_map = {str(r["id"]): point_id for r in roles if r.get("computable", False)}

    return {
        "project_id": project_id,
        "default_status_id": default_status_id,
        "points_map": points_map,
        "project_url": f"https://tree.taiga.io/project/{slug}",
    }


@tool
def create_epic_in_taiga(token: str, project_id: int, subject: str, description: str) -> dict:
    """Create an epic in Taiga. Returns epic_id."""
    result = _api(
        "POST",
        "epics",
        token,
        json={
            "project": project_id,
            "subject": subject,
            "description": description,
        },
    )
    return {"epic_id": result["id"], "subject": subject}


@tool
def create_user_story_in_taiga(
    token: str,
    project_id: int,
    subject: str,
    description: str,
    status_id: int,
    points_map: dict,
) -> dict:
    """Create a user story in Taiga. Returns story_id."""
    payload = {
        "project": project_id,
        "subject": subject,
        "description": description,
        "status": status_id,
        "milestone": None,
    }
    if points_map:
        payload["points"] = points_map
    result = _api("POST", "userstories", token, json=payload)
    return {"story_id": result["id"], "subject": subject}


@tool
def link_story_to_epic(token: str, epic_id: int, story_id: int) -> dict:
    """Link a user story to an epic."""
    _api(
        "POST",
        f"epics/{epic_id}/related_userstories",
        token,
        json={
            "epic": epic_id,
            "user_story": story_id,
        },
    )
    return {"linked": True, "epic_id": epic_id, "story_id": story_id}


@tool
def create_task_in_taiga(
    token: str,
    project_id: int,
    story_id: int,
    subject: str,
    description: str,
) -> dict:
    """Create a task linked to a user story. Returns task_id."""
    result = _api(
        "POST",
        "tasks",
        token,
        json={
            "project": project_id,
            "user_story": story_id,
            "subject": subject,
            "description": description,
        },
    )
    return {"task_id": result["id"], "subject": subject}


# ---------------------------------------------------------------------------
# Streaming entry point
# ---------------------------------------------------------------------------


async def stream_push_to_taiga(task_breakdown_json: str) -> AsyncIterator[str]:
    """Stream Taiga push progress via SSE events.

    Args:
        task_breakdown_json: Serialized JSON of the task breakdown result.

    Yields:
        SSE events: lifecycle (progress), done (summary), error.
    """
    # Pre-count items from input data for accurate summary
    try:
        tb_data = json.loads(task_breakdown_json)
    except json.JSONDecodeError:
        yield _sse("error", "Invalid task breakdown JSON")
        return

    epic_count = 0
    story_count = 0
    task_count = 0
    for wave in tb_data.get("waves", []):
        for epic in wave.get("epics", []):
            epic_count += 1
            for story in epic.get("stories", []):
                story_count += 1
                task_count += len(story.get("tasks", []))

    # Load config to get project URL for summary
    cfg = _load_config()
    project_url = f"https://tree.taiga.io/project/{cfg['taiga']['project_slug']}"

    prompt = get_taiga_prompt(task_breakdown_json)

    agent = Agent(
        system_prompt=prompt,
        model=get_model(),
        tools=[
            authenticate_taiga,
            get_project,
            create_epic_in_taiga,
            create_user_story_in_taiga,
            link_story_to_epic,
            create_task_in_taiga,
        ],
        callback_handler=None,
    )

    yield _sse("lifecycle", "🔐 Authenticating with Taiga...")
    yield _sse(
        "lifecycle", f"� Will ccreate {epic_count} epics, {story_count} stories, {task_count} tasks"
    )

    try:
        full_text = ""
        async for event in agent.stream_async(
            "Push all task breakdown data to Taiga now. Follow the instructions exactly."
        ):
            if "data" in event:
                full_text += event["data"]

        yield _sse("lifecycle", "🎉 Push to Taiga complete!")

        summary = {
            "success": True,
            "epics_created": epic_count,
            "stories_created": story_count,
            "tasks_created": task_count,
            "project_url": project_url,
        }
        yield _sse("done", json.dumps(summary))

    except Exception as e:
        yield _sse("error", str(e))
