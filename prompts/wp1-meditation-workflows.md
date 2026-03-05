# Task: WP1 — Meditation Workflow Service (Dapr Workflows)

## Context
Little Bits of Buddha — a Telegram Dhamma teacher bot. Microservices with Dapr + Redis. Python 3.12, trio for existing services (but this NEW service uses Dapr Workflows which are generator-based, NOT trio/asyncio). Rootless Podman. Repo at current directory.

## Branch
Work on branch: `feat/meditation-workflows` (already checked out).
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_meditation_workflows.py`. Commit them.
Then implement until tests pass. Commit again.

## Existing Architecture (read these files first)
- `ARCHITECTURE.md` — overall system design
- `src/seeker_actor_service/` — Dapr Actor host, one per user
- `src/wisdom_service/` — LLM + RAG pipeline
- `src/telegram_bot_service/` — Telegram bot, pub/sub
- `compose.yaml` — current service topology
- `.dapr/components/` — Dapr component configs

## What to Build

### 1. New service: `src/meditation_workflow_service/`

Create these files:

**`src/meditation_workflow_service/__init__.py`** — empty

**`src/meditation_workflow_service/__main__.py`** — FastAPI app + WorkflowRuntime setup:
```python
from fastapi import FastAPI
from dapr.ext.workflow import WorkflowRuntime, DaprWorkflowContext, WorkflowActivityContext
from dapr.clients import DaprClient

app = FastAPI()
wfr = WorkflowRuntime()

# Import and register workflows
from .workflows.breathing import breathing_meditation
from .workflows.metta import metta_meditation
from .activities import send_instruction, close_meditation, get_seeker_state

# Start workflow runtime on app startup
@app.on_event("startup")
def startup():
    wfr.start()

@app.on_event("shutdown")  
def shutdown():
    wfr.shutdown()

# Endpoint to start a meditation (called by seeker-actor-service)
@app.post("/meditate/start")
def start_meditation(request: dict):
    from dapr.ext.workflow import DaprWorkflowClient
    client = DaprWorkflowClient()
    workflow_name = request.get("type", "breathing_meditation")
    instance_id = f"meditation-{request['chat_id']}-{int(time.time())}"
    client.schedule_new_workflow(
        workflow=workflow_name,
        input=request,
        instance_id=instance_id
    )
    return {"instance_id": instance_id, "status": "started"}

# Endpoint to raise external event (for user responses during meditation)
@app.post("/meditate/event")
def raise_event(request: dict):
    from dapr.ext.workflow import DaprWorkflowClient
    client = DaprWorkflowClient()
    client.raise_workflow_event(
        instance_id=request["instance_id"],
        event_name=request["event_name"],
        data=request.get("data")
    )
    return {"status": "event_raised"}

# Endpoint to check meditation status
@app.get("/meditate/status/{instance_id}")
def get_status(instance_id: str):
    from dapr.ext.workflow import DaprWorkflowClient
    client = DaprWorkflowClient()
    state = client.get_workflow_state(instance_id=instance_id)
    return {"instance_id": instance_id, "status": state.runtime_status.name if state else "not_found"}
```

**`src/meditation_workflow_service/workflows/__init__.py`** — empty

**`src/meditation_workflow_service/workflows/breathing.py`** — Breathing meditation (ānāpānasati):
- Generator-based workflow (yield, NOT async/await)
- Steps: welcome → settle timer (30s) → breathing focus instruction → main timer (configurable 5/10/15/20 min) → bell + check-in → wait for external event with 5-min timeout → closing + sutta suggestion
- Use `ctx.call_activity()` for sending messages, `ctx.create_timer()` for pauses, `ctx.wait_for_external_event()` for user input
- Template text should be warm, gentle, grounded in Early Buddhist tradition

**`src/meditation_workflow_service/workflows/metta.py`** — Loving-kindness meditation:
- Steps: welcome → self-directed metta phrases → pause → loved one → pause → neutral person → pause → difficult person → pause → all beings → closing
- Each phase: send instruction with specific phrases, timer for contemplation
- Phrases from Karaniya Metta Sutta (Snp 1.8)

**`src/meditation_workflow_service/activities.py`** — Shared activities:
```python
def send_instruction(ctx: WorkflowActivityContext, input: dict):
    """Send a meditation instruction to the seeker via Telegram pub/sub."""
    # Use DaprClient (sync) to publish to the 'responses' topic
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses", 
            data=json.dumps({"chat_id": input["chat_id"], "text": input["text"]}),
            data_content_type="application/json"
        )

def close_meditation(ctx: WorkflowActivityContext, input: dict):
    """Send closing message, log sit, suggest sutta."""
    # 1. Send closing message
    # 2. Call seeker-actor-service to log the sit (POST /actors/SeekerActor/{chat_id}/method/log_sit)
    # 3. Call wisdom-service to get a relevant sutta suggestion (POST /wisdom/ask with meditation context)
    # 4. Send sutta suggestion

def get_seeker_state(ctx: WorkflowActivityContext, input: dict):
    """Read seeker state to personalize instructions."""
    with DaprClient() as client:
        result = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{input['chat_id']}/method/get_state",
            http_verb="GET"
        )
        return json.loads(result.text())
```

**`src/meditation_workflow_service/templates.py`** — Meditation instruction texts:
- Define instruction text for each step of each meditation type
- Warm, gentle, grounded in Pali Canon tradition
- Adapt based on practice_level from seeker state (simpler language for newcomers)

**`src/meditation_workflow_service/requirements.txt`**:
```
dapr>=1.14.0
dapr-ext-workflow>=0.5.0
dapr-ext-fastapi>=1.14.0
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
```

### 2. Dapr components

**`.dapr/components/workflow.yaml`**:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: dapr
spec:
  type: workflow.dapr
  version: v1
```

### 3. Docker + Compose

**`Dockerfile`** — Add build target `meditation-workflow-service-production`:
- Base: `python:3.12-slim`
- Install requirements
- Copy src/meditation_workflow_service
- CMD: `uvicorn meditation_workflow_service.__main__:app --host 0.0.0.0 --port 8003`

**`compose.yaml`** — Add:
- `meditation-workflow-service` container (port 8003)
- `meditation-workflow-dapr` sidecar (app-id: meditation-workflow-service, app-port: 8003)
- Network configuration matching existing services

### 4. ADR

**`docs/adr/0014-dapr-workflows-for-guided-meditation.md`**:
- Context: Need durable multi-step guided meditations that survive container restarts
- Decision: Use Dapr Workflows (generator-based, separate process)
- Consequences: New service, no trio conflict, activities call existing services via Dapr

## Constraints
- Workflows are GENERATORS (yield), NOT async/await
- Activities are SYNC functions — use sync DaprClient and sync httpx
- This service is a SEPARATE process from trio-based services
- Do NOT modify existing service code (seeker-actor, wisdom, telegram) — only add new service + compose entries
- Python 3.12
- Use `when_any` from `dapr.ext.workflow` for event/timer races (NOT asyncio)

## Branch & Push
Work on branch: `feat/meditation-workflows`. Commit AND push to the branch when done.
The orchestrator handles merge to main after review.

## Self-Review (mandatory before final commit)
Re-read your entire diff (`git diff main..HEAD`). Write out:

**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
