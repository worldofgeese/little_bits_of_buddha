"""Wisdom Service — stub for Phase 2 infrastructure.

Will host LLM + RAG pipeline, called by SeekerActor via Dapr service invocation.
"""
import trio
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/wisdom/ask")
async def ask():
    return {"response": "stub", "suttas_cited": [], "detected_themes": []}

async def main():
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)

if __name__ == "__main__":
    trio.run(main)
