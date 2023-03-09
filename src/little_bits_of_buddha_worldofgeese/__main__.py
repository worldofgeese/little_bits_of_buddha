import os

import trio
import triogram

import little_bits_of_buddha_worldofgeese.config as secrets
from little_bits_of_buddha_worldofgeese.chatbot import the_buddha


# access the environment variables directly using os.environ
os.environ["TRIOGRAM_TOKEN"] = secrets.TRIOGRAM_TOKEN


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
    trio.run(main)
