"""Meditation Workflow Service — FastAPI app + Dapr WorkflowRuntime.

Endpoints:
- POST /meditate/start — Start a meditation workflow
- POST /meditate/event — Raise external event (user response)
- GET /meditate/status/{instance_id} — Check workflow status
- GET /healthz — Health check
"""

import time

import uvicorn
from dapr.ext.workflow import DaprWorkflowClient, WorkflowRuntime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import activities
from meditation_workflow_service.activities import (
    close_meditation,
    get_seeker_state,
    send_instruction,
)

# Import workflows
from meditation_workflow_service.workflows.breathing import breathing_meditation
from meditation_workflow_service.workflows.metta import metta_meditation

# FastAPI app
app = FastAPI(title="Meditation Workflow Service")

# Workflow runtime
wfr = WorkflowRuntime()

# Register workflows
wfr.register_workflow(breathing_meditation)
wfr.register_workflow(metta_meditation)

# Register activities
wfr.register_activity(send_instruction)
wfr.register_activity(close_meditation)
wfr.register_activity(get_seeker_state)


# Pydantic models for request validation
class StartMeditationRequest(BaseModel):
    chat_id: int
    type: str = "breathing_meditation"
    duration_minutes: int = 5


class RaiseEventRequest(BaseModel):
    instance_id: str
    event_name: str
    data: str | None = None


@app.on_event("startup")
def startup():
    """Start workflow runtime on app startup."""
    wfr.start()


@app.on_event("shutdown")
def shutdown():
    """Shutdown workflow runtime on app shutdown."""
    wfr.shutdown()


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/meditate/start")
def start_meditation(request: StartMeditationRequest):
    """Start a meditation workflow.

    Args:
        request: StartMeditationRequest with chat_id, type, duration_minutes

    Returns:
        Dict with instance_id and status
    """
    client = DaprWorkflowClient()

    # Generate unique instance ID
    instance_id = f"meditation-{request.chat_id}-{int(time.time())}"

    # Prepare input for workflow
    workflow_input = {
        "chat_id": request.chat_id,
        "duration_minutes": request.duration_minutes,
    }

    # Map workflow type to workflow function name
    workflow_map = {
        "breathing_meditation": breathing_meditation,
        "metta_meditation": metta_meditation,
    }

    workflow_func = workflow_map.get(request.type, breathing_meditation)

    # Schedule workflow
    client.schedule_new_workflow(
        workflow=workflow_func, input=workflow_input, instance_id=instance_id
    )

    return {"instance_id": instance_id, "status": "started"}


@app.post("/meditate/event")
def raise_event(request: RaiseEventRequest):
    """Raise an external event to a running workflow.

    Used to send user responses back to the workflow (e.g., check-in feedback).

    Args:
        request: RaiseEventRequest with instance_id, event_name, data

    Returns:
        Dict with status
    """
    client = DaprWorkflowClient()

    client.raise_workflow_event(
        instance_id=request.instance_id,
        event_name=request.event_name,
        data=request.data,
    )

    return {"status": "event_raised"}


@app.get("/meditate/status/{instance_id}")
def get_status(instance_id: str):
    """Get the status of a meditation workflow.

    Args:
        instance_id: Workflow instance ID

    Returns:
        Dict with instance_id and status
    """
    client = DaprWorkflowClient()

    try:
        state = client.get_workflow_state(instance_id=instance_id)
        if state:
            return {"instance_id": instance_id, "status": state.runtime_status.name}
        else:
            return {"instance_id": instance_id, "status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run with uvicorn (no trio — workflows are generator-based)
    uvicorn.run(app, host="0.0.0.0", port=8003)
