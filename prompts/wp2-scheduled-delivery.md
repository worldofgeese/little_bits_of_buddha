# Task: WP2 — Dapr Jobs for Scheduled Delivery

## Context
Little Bits of Buddha — Telegram Dhamma teacher bot. Python 3.12, trio (NOT asyncio except workflow service). Dapr + Redis microservices. The `meditation-workflow-service` already exists (Dapr Workflows). We now add Dapr Jobs to it for scheduled delivery.

## Branch
Work on branch: `feat/scheduled-delivery` (already checked out).
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_scheduled_delivery.py`. Commit them.
Then implement until tests pass. Commit again.

## Existing Files to Read First
- `src/meditation_workflow_service/__main__.py` — FastAPI app hosting Dapr Workflows
- `src/seeker_actor_service/seeker_actor.py` — Actor with SeekerState (has practice_level, topics_explored, practice_journal)
- `src/wisdom_service/__main__.py` — LLM + RAG + sutta search
- `compose.yaml` — current service topology
- `.dapr/components/` — existing Dapr components

## What to Build

### 1. Add Jobs handler to meditation-workflow-service

The meditation-workflow-service already runs FastAPI. Add a job callback endpoint.

**`src/meditation_workflow_service/jobs.py`**:
```python
"""Dapr Jobs handlers for scheduled delivery."""
import json
import logging
from dapr.clients import DaprClient

logger = logging.getLogger(__name__)

def handle_daily_sutta(job_data: dict):
    """Called by Dapr Scheduler for daily sutta delivery.
    
    1. Read seeker state (practice_level, topics_explored)
    2. Call wisdom-service to get a sutta matching level + unexplored topics
    3. Send sutta to Telegram via pub/sub
    """
    chat_id = job_data["chat_id"]
    with DaprClient() as client:
        # Get seeker state
        state = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{chat_id}/method/get_state",
            http_verb="GET"
        )
        seeker = json.loads(state.text())
        
        # Ask wisdom-service for a sutta recommendation
        response = client.invoke_method(
            app_id="wisdom-service",
            method_name="wisdom/ask",
            data=json.dumps({
                "chat_id": chat_id,
                "message": "Share a sutta that would be helpful for my practice today.",
                "context": {
                    "practice_level": seeker.get("practice_level", "newcomer"),
                    "topics_explored": seeker.get("topics_explored", []),
                    "history": [],
                    "is_daily_sutta": True
                }
            }),
            content_type="application/json",
            http_verb="POST"
        )
        wisdom = json.loads(response.text())
        
        # Send via pub/sub to Telegram
        message_text = f"🌅 *Daily Sutta*\n\n{wisdom['response']}"
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": chat_id, "text": message_text}),
            data_content_type="application/json"
        )

def handle_weekly_checkin(job_data: dict):
    """Called by Dapr Scheduler for weekly practice check-in.
    
    1. Read seeker's practice journal (last 7 days)
    2. Generate warm summary via wisdom-service
    3. Send to Telegram
    """
    chat_id = job_data["chat_id"]
    with DaprClient() as client:
        # Get weekly summary from actor
        summary = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{chat_id}/method/get_weekly_summary",
            data=json.dumps({"days": 7}),
            content_type="application/json",
            http_verb="POST"
        )
        summary_data = json.loads(summary.text())
        
        # Ask wisdom-service to generate a warm check-in message
        response = client.invoke_method(
            app_id="wisdom-service",
            method_name="wisdom/ask",
            data=json.dumps({
                "chat_id": chat_id,
                "message": f"Generate a warm weekly practice check-in based on this data: {json.dumps(summary_data)}",
                "context": {
                    "practice_level": summary_data.get("practice_level", "newcomer"),
                    "is_weekly_checkin": True
                }
            }),
            content_type="application/json",
            http_verb="POST"
        )
        wisdom = json.loads(response.text())
        
        message_text = f"🙏 *Weekly Practice Check-in*\n\n{wisdom['response']}"
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": chat_id, "text": message_text}),
            data_content_type="application/json"
        )
```

**In `src/meditation_workflow_service/__main__.py`**, add the job callback endpoint:
```python
@app.post("/job/{job_name}")
def handle_job(job_name: str, request: dict):
    """Dapr Jobs callback endpoint."""
    if job_name.startswith("daily-sutta-"):
        handle_daily_sutta(request)
    elif job_name.startswith("weekly-checkin-"):
        handle_weekly_checkin(request)
    return {"status": "ok"}
```

### 2. Job registration functions

**`src/meditation_workflow_service/scheduler.py`**:
```python
"""Schedule and manage Dapr Jobs for per-user delivery."""
import httpx

DAPR_HTTP_PORT = 3500  # Dapr sidecar HTTP port

def schedule_daily_sutta(chat_id: str, time_utc: str = "06:00", timezone: str = "UTC"):
    """Register a daily sutta delivery job for a seeker."""
    job_name = f"daily-sutta-{chat_id}"
    # Use Dapr Jobs HTTP API (alpha)
    response = httpx.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}",
        json={
            "data": {"chat_id": chat_id},
            "schedule": f"0 0 {int(time_utc.split(':')[0])} * * *",
            "overwrite": True
        }
    )
    response.raise_for_status()
    return job_name

def cancel_daily_sutta(chat_id: str):
    """Cancel daily sutta delivery for a seeker."""
    job_name = f"daily-sutta-{chat_id}"
    response = httpx.delete(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}"
    )
    return response.status_code == 204

def schedule_weekly_checkin(chat_id: str, day_of_week: int = 0):
    """Register a weekly check-in job (default: Sunday)."""
    job_name = f"weekly-checkin-{chat_id}"
    response = httpx.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}",
        json={
            "data": {"chat_id": chat_id},
            "schedule": f"0 0 9 * * {day_of_week}",
            "overwrite": True
        }
    )
    response.raise_for_status()
    return job_name

def cancel_weekly_checkin(chat_id: str):
    """Cancel weekly check-in for a seeker."""
    job_name = f"weekly-checkin-{chat_id}"
    response = httpx.delete(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}"
    )
    return response.status_code == 204
```

### 3. Add schedule preferences to SeekerActor

In `src/seeker_actor_service/seeker_actor.py`, add to default state:
```python
"schedule_preferences": {
    "daily_sutta": False,
    "daily_sutta_time": "07:00",
    "weekly_checkin": False,
    "timezone": "UTC"
}
```

Add actor methods:
- `update_schedule(data: dict) -> dict` — Update schedule preferences, call scheduler to register/cancel jobs
- The method should call the meditation-workflow-service's scheduler endpoints via Dapr service invocation

### 4. Add `/daily` Telegram command

In `src/telegram_bot_service_worldofgeese/commands.py`, add:
- `/daily on` — Enable daily sutta delivery, call actor's `update_schedule`
- `/daily off` — Disable
- `/daily time 07:00` — Set delivery time
- Respond with confirmation message

### 5. Dapr components

**`.dapr/components/scheduler.yaml`** (if not already present):
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component  
metadata:
  name: scheduler
spec:
  type: scheduler.dapr
  version: v1alpha1
```

### 6. Tests (`tests/test_scheduled_delivery.py`)

Write FIRST as failing tests:
1. **Schedule daily sutta** — registers job with correct cron expression
2. **Cancel daily sutta** — removes job
3. **Schedule weekly checkin** — correct cron for specified day
4. **Job callback routing** — daily-sutta-* routes to handle_daily_sutta
5. **Job callback routing** — weekly-checkin-* routes to handle_weekly_checkin
6. **Actor schedule update** — update_schedule stores preferences + triggers job registration
7. **Opt-in/opt-out** — toggling daily_sutta on/off creates/cancels job
8. **Parse /daily command** — "on", "off", "time 07:00" all parse correctly

## Constraints
- Jobs API is alpha (`v1.0-alpha1`) — use HTTP API via httpx
- This project uses **trio** for actor/telegram services, NOT asyncio. Use `@pytest.mark.trio` for async tests.
- DaprClient is sync-only — wrap with `trio.to_thread.run_sync` where needed.
- Proactive delivery is OPT-IN ONLY. The Buddha does not nudge.
- Job names: `daily-sutta-{chat_id}`, `weekly-checkin-{chat_id}`
- Daily sutta schedule stored per-user in actor state

## Branch & Push
Work on branch: `feat/scheduled-delivery`. Commit AND push when done.

## Self-Review (mandatory before final commit)
**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
