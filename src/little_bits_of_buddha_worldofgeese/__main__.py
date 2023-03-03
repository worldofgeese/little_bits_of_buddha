import trio
import triogram
from fastapi import FastAPI
from hypercorn.config import Config as HyperConfig
from hypercorn.trio import serve

from little_bits_of_buddha_worldofgeese.chatbot import the_buddha

app = FastAPI()


@app.get("/")
async def main():
    """
    Starts the bot and event handlers.
    """
    print("Starting bot...")
    bot = triogram.make_bot()
    async with bot, trio.open_nursery() as nursery:
        nursery.start_soon(bot)
        nursery.start_soon(the_buddha, bot)
    print("Bot started.")
    return {"message": "Bot started."}


if __name__ == "__main__":
    print("Starting server...")
    config = HyperConfig()
    config.bind = [f"0.0.0.0:8000"]
    trio.run(serve, app, config)
