import openai


def text_message(update):
    """
    A helper function that checks if an update contains a text message.

    Args:
        update (dict): A dictionary containing information about the update.

    Returns:
        bool: True if the update contains a text message, False otherwise.
    """
    return "message" in update and "text" in update["message"]


async def the_buddha(bot):
    """
    Waits for new messages and responds with the output from the ChatGPT API.
    """
    messages = []
    system_msg = "You are the Buddha."
    messages.append({"role": "system", "content": system_msg})
    # Use the bot.sub() method to subscribe to updates filtered by text_message
    async with bot.sub(text_message) as updates:
        # Use async for to iterate through incoming updates
        async for update in updates:
            message = update["message"]["text"]
            messages.append({"role": "user", "content": message})
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=messages
            )
            reply = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            await bot.api.send_message(
                params={
                    "chat_id": update["message"]["chat"]["id"],
                    "text": reply,
                }
            )
