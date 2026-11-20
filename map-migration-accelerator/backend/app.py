"""FastAPI backend - routes only."""

import csv
import io
import itertools
import json
import os
import re
from datetime import datetime

import logging

from architecture_agent import stream_diagram
from aws_cost_agent import stream_aws_cost
from chat_agent import stream_chat
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from landing_zone_agent import stream_landing_zone
from orchestrator_agent import run_assessment
from pydantic import BaseModel
from resource_planning_agent import stream_resource_planning
from strategy_agent import stream_strategy
from taiga_agent import stream_push_to_taiga
from task_breakdown_agent import stream_task_breakdown
from utils.config import CORS_ALLOWED_ORIGINS, SSE_MEDIA_TYPE
from wave_runbook_agent import stream_wave_runbook

app = FastAPI(title="Agentic App")
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["*"],
)


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
SAFE_CSV_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()-]{0,99}\.csv$", re.IGNORECASE)


def _safe_upload_path(upload_dir: str, filename: str) -> str | None:
    """Return a path inside upload_dir for a client-supplied CSV name, or None if unsafe."""
    name = os.path.basename(filename.replace("\\", "/"))
    if not SAFE_CSV_NAME.match(name):
        return None
    path = os.path.join(upload_dir, name)
    if os.path.dirname(os.path.realpath(path)) != os.path.realpath(upload_dir):
        return None
    return path


def _csv_content_error(content: bytes) -> str | None:
    """Return a reason the upload is not an acceptable CSV, or None if it is."""
    if not content:
        return "is empty"
    if len(content) > MAX_UPLOAD_BYTES:
        return f"exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
    if b"\x00" in content:
        return "is not a text CSV file"
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "must be UTF-8 encoded"
    try:
        rows = list(itertools.islice(csv.reader(io.StringIO(text)), 2))
    except csv.Error:
        return "is not a valid CSV file"
    if len(rows) < 2 or len([c for c in rows[0] if c.strip()]) < 2:
        return "must have a header row with at least 2 columns and at least 1 data row"
    return None


class GenerateRequest(BaseModel):
    description: str


class WavePlanRequest(BaseModel):
    prompt: str


class ChatRequest(BaseModel):
    message: str
    assessment: dict
    history: list[dict] | None = None


class StrategyRequest(BaseModel):
    drivers_and_scope: str
    timeline: str
    assessment: dict


class LandingZoneRequest(BaseModel):
    region: str
    account_strategy: str
    connectivity: str
    assessment: dict
    strategy: str


class TaskBreakdownRequest(BaseModel):
    assessment: dict
    strategy: str
    landing_zone: str


class TaigaPushRequest(BaseModel):
    task_breakdown: dict


class WaveRunbookRequest(BaseModel):
    assessment: dict
    strategy: str
    landing_zone: str


class ResourcePlanningRequest(BaseModel):
    strategy: str


class AwsCostRequest(BaseModel):
    assessment: dict
    strategy: str


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    try:
        return StreamingResponse(
            stream_diagram(req.description),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception as e:
        logger.exception("Error in /api/generate")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/migration/upload")
async def migration_upload(
    app_file: UploadFile = File(...),
    infra_file: UploadFile = File(None),
):
    try:
        # Validate that at least the required app_file has content
        if not app_file or not app_file.filename:
            return JSONResponse(status_code=400, content={"error": "app_file is required"})

        # Validate CSV extension for app_file
        if not app_file.filename.lower().endswith(".csv"):
            return JSONResponse(
                status_code=400,
                content={"error": "app_file must be a CSV file"},
            )

        # Validate CSV extension for infra_file if provided
        if infra_file and infra_file.filename:
            if not infra_file.filename.lower().endswith(".csv"):
                return JSONResponse(
                    status_code=400,
                    content={"error": "infra_file must be a CSV file"},
                )

        # Create timestamped upload folder (YY-MM-DD-SS)
        now = datetime.now()
        folder_name = now.strftime("%y-%m-%d-%S")
        upload_dir = os.path.join("uploads", folder_name)

        # Reject unsafe client file names before anything is written to disk
        app_csv_path = _safe_upload_path(upload_dir, app_file.filename)
        if not app_csv_path:
            return JSONResponse(status_code=400, content={"error": "Invalid app_file name"})
        infra_csv_path = None
        if infra_file and infra_file.filename:
            infra_csv_path = _safe_upload_path(upload_dir, infra_file.filename)
            if not infra_csv_path:
                return JSONResponse(status_code=400, content={"error": "Invalid infra_file name"})
        # Read and validate both files before anything is written to disk
        app_content = await app_file.read(MAX_UPLOAD_BYTES + 1)
        error = _csv_content_error(app_content)
        if error:
            return JSONResponse(status_code=400, content={"error": f"app_file {error}"})
        infra_content = None
        if infra_csv_path:
            infra_content = await infra_file.read(MAX_UPLOAD_BYTES + 1)
            error = _csv_content_error(infra_content)
            if error:
                return JSONResponse(status_code=400, content={"error": f"infra_file {error}"})

        os.makedirs(upload_dir, exist_ok=True)
        with open(app_csv_path, "wb") as f:
            f.write(app_content)
        if infra_csv_path:
            with open(infra_csv_path, "wb") as f:
                f.write(infra_content)

        # Stream assessment results via SSE (Discovery → Dependency pipeline)
        return StreamingResponse(
            run_assessment(app_csv_path, infra_csv_path),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/migration/upload")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/migration/chat")
async def migration_chat(req: ChatRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.message or not req.message.strip():
            return JSONResponse(status_code=400, content={"error": "Message is required"})

        assessment_json = json.dumps(req.assessment)
        return StreamingResponse(
            stream_chat(req.message, assessment_json, req.history),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/migration/chat")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/migration/strategy")
async def migration_strategy(req: StrategyRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.drivers_and_scope or not req.drivers_and_scope.strip():
            return JSONResponse(
                status_code=400, content={"error": "Migration drivers/scope is required"}
            )
        if not req.timeline or not req.timeline.strip():
            return JSONResponse(status_code=400, content={"error": "Timeline is required"})

        discovery_json = json.dumps(req.assessment.get("discovery", {}))
        dependency_json = json.dumps(req.assessment.get("dependency", {}))
        return StreamingResponse(
            stream_strategy(req.drivers_and_scope, req.timeline, discovery_json, dependency_json),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/migration/strategy")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/execution/landing-zone")
async def execution_landing_zone(req: LandingZoneRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.strategy or not req.strategy.strip():
            return JSONResponse(status_code=400, content={"error": "Strategy data is required"})
        if not req.region or not req.region.strip():
            return JSONResponse(status_code=400, content={"error": "Region is required"})

        discovery_json = json.dumps(req.assessment.get("discovery", {}))
        dependency_json = json.dumps(req.assessment.get("dependency", {}))
        return StreamingResponse(
            stream_landing_zone(
                req.region,
                req.account_strategy,
                req.connectivity,
                discovery_json,
                dependency_json,
                req.strategy,
            ),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/execution/landing-zone")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/execution/task-breakdown")
async def execution_task_breakdown(req: TaskBreakdownRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.strategy or not req.strategy.strip():
            return JSONResponse(status_code=400, content={"error": "Strategy data is required"})
        if not req.landing_zone or not req.landing_zone.strip():
            return JSONResponse(status_code=400, content={"error": "Landing zone data is required"})

        assessment_json = json.dumps(req.assessment)
        return StreamingResponse(
            stream_task_breakdown(assessment_json, req.strategy, req.landing_zone),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/execution/task-breakdown")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/execution/push-to-taiga")
async def execution_push_to_taiga(req: TaigaPushRequest):
    try:
        if not req.task_breakdown:
            return JSONResponse(status_code=400, content={"error": "Task breakdown data is required"})

        task_breakdown_json = json.dumps(req.task_breakdown)
        return StreamingResponse(
            stream_push_to_taiga(task_breakdown_json),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/execution/push-to-taiga")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/execution/wave-runbook")
async def execution_wave_runbook(req: WaveRunbookRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.strategy or not req.strategy.strip():
            return JSONResponse(status_code=400, content={"error": "Strategy data is required"})
        if not req.landing_zone or not req.landing_zone.strip():
            return JSONResponse(status_code=400, content={"error": "Landing zone data is required"})

        assessment_json = json.dumps(req.assessment)
        return StreamingResponse(
            stream_wave_runbook(assessment_json, req.strategy, req.landing_zone),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/execution/wave-runbook")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/execution/resource-planning")
async def execution_resource_planning(req: ResourcePlanningRequest):
    try:
        if not req.strategy or not req.strategy.strip():
            return JSONResponse(status_code=400, content={"error": "Strategy data is required"})

        return StreamingResponse(
            stream_resource_planning(req.strategy),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/execution/resource-planning")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/api/cost/aws-cost")
async def cost_aws_cost(req: AwsCostRequest):
    try:
        if not req.assessment:
            return JSONResponse(status_code=400, content={"error": "Assessment data is required"})
        if not req.strategy or not req.strategy.strip():
            return JSONResponse(status_code=400, content={"error": "Strategy data is required"})

        assessment_json = json.dumps(req.assessment)
        return StreamingResponse(
            stream_aws_cost(assessment_json, req.strategy),
            media_type=SSE_MEDIA_TYPE,
        )
    except Exception:
        logger.exception("Error in /api/cost/aws-cost")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
