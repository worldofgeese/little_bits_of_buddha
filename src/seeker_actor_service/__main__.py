"""Seeker Actor Service — hosts Dapr Virtual Actors (one per Telegram user)."""

import uvicorn
from dapr.ext.fastapi import DaprActor
from fastapi import FastAPI

from seeker_actor_service.seeker_actor import SeekerActor

app = FastAPI()
actor = DaprActor(app)


@app.on_event("startup")
async def startup():
    """Register the SeekerActor with Dapr on startup."""
    await actor.register_actor(SeekerActor)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    # Use uvicorn with asyncio (required by Dapr actor SDK)
    uvicorn.run(app, host="0.0.0.0", port=8081)
