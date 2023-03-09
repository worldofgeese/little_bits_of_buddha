import trio
import triogram

from little_bits_of_buddha_worldofgeese.chatbot import the_buddha



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
