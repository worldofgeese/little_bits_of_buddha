"""Seeker Actor Service — stub for Phase 2 infrastructure.

Will host Dapr Virtual Actors (one per Telegram user).
"""

import trio
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


async def main():
    config = Config()
    config.bind = ["0.0.0.0:8081"]
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)


if __name__ == "__main__":
    trio.run(main)
