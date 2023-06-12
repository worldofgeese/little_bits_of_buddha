import openai

import little_bits_of_buddha_worldofgeese.config as secrets

MAX_TOKENS = (
    8192  # Set maximum number of messages to process before resetting chat history
)

SYSTEM_MSG = "You are the Buddha. You teach only the Dhamma, only what is fundamental to the holy life as you profess in the Simsapa Sutta."
USER_MSG_PROMPT = "You speak in the style of the Tathagata, the Buddha, the Awakened One of the Early Buddhist Canon. "

openai.api_key = secrets.OPENAI_API_KEY


def check_message(update):
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
    messages.append({"role": "system", "content": SYSTEM_MSG})
    counter = 0  # Keep track of total tokens processed
    # Use the bot.sub() method to subscribe to updates filtered by check_message
    async with bot.sub(check_message) as updates:
        # Use async for to iterate through incoming updates
        async for update in updates:
            message = USER_MSG_PROMPT + update["message"]["text"]
            messages.append({"role": "user", "content": message})
            response = openai.ChatCompletion.create(model="gpt-4", messages=messages)
            reply = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            await bot.api.send_message(
                params={
                    "chat_id": update["message"]["chat"]["id"],
                    "text": reply,
                }
            )
            token_count = response["usage"][
                "total_tokens"
            ]  # Get total number of tokens used by API call
            counter += token_count  # Add token count to counter variable
            if counter >= MAX_TOKENS:
                messages.clear()  # Clear messages list
                await bot.api.send_message(
                    params={
                        "chat_id": update["message"]["chat"]["id"],
                        "text": "This Buddha's time on this earth has ended. The arrival of the next Tathagata is imminent.",
                    }
                )
                messages.append(
                    {"role": "system", "content": SYSTEM_MSG}
                )  # Reset chat history
                counter = 0  # Reset counter variable
