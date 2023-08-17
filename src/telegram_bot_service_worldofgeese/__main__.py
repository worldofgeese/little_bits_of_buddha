import json
import logging
import time

import requests
import trio
import triogram
from dapr.clients import DaprClient
from dapr.ext.fastapi import DaprApp
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve
from pydantic import BaseModel
from trio import to_thread

from telegram_bot_service_worldofgeese import init_secrets

logging.basicConfig(level=logging.INFO)

app = FastAPI()
dapr_app = DaprApp(app)
config = Config()
config.bind = ["0.0.0.0:8090"]

# TODO remove this
# TODO consider bringing back wait_for_dapr_ready function
# os.environ["TRIOGRAM_TOKEN"] = "xxxxxxxx:xxxxxxxx"


def check_message(update):
    """
    A helper function that checks if an update contains a text message.

    Args:
        update (dict): A dictionary containing information about the update.


    Returns:
        bool: True if the update contains a text message, False otherwise.
    """
    return "message" in update and "text" in update["message"]


class CloudEvent(BaseModel):
    datacontenttype: str
    source: str
    topic: str
    pubsubname: str
    data: dict
    id: str
    specversion: str
    tracestate: str
    type: str
    traceid: str


async def send_message_to_pubsub(bot):
    """
    The send_message_to_pubsub() async function relays messages to and from the Telegram bot and the OpenAI service via the Dapr pubsub.

    Parameters:
    bot (triogram.Bot): The Telegram bot object.

    Functionality:
    - Uses bot.sub(check_message) to subscribe to messages that contain text.
    - Loops through the updates and extracts the chat ID and message text.
    - Constructs a message dictionary with the chat ID and text.
    - Publishes the message to the "messages" topic of the pubsub using the DaprClient.
    - The message is processed by the OpenAI service and a response is sent to the "responses" topic of the pubsub.
    - Subscribes to the processed "responses" topic of the pubsub using the DaprClient and sends the response to the user.
    """

    async with bot.sub(check_message) as updates:
        async for update in updates:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"]["text"]

            # Prepare the message
            message = {
                "chat_id": chat_id,
                "text": text,
            }

            # Publish the message to the message bus
            logging.info(f"Sending response: {message}")
            with DaprClient() as dapr_client:
                print(f"chat_id: {chat_id}")
                print(f"text: {text}")
                dapr_client.publish_event(
                    pubsub_name="scaleway-redis-cluster-pubsub",
                    topic_name="messages",
                    data=json.dumps(message),
                    data_content_type="application/json",
                )


@dapr_app.subscribe(pubsub="scaleway-redis-cluster-pubsub", topic="responses")
async def send_response_to_user(event: CloudEvent):
    logging.info(f"Received message: {event.data}")
    chat_id = event.data.get("chat_id")
    text = event.data.get("text")
    bot = triogram.make_bot()
    async with bot:
        print(f"chat_id: {chat_id}")
        print(f"text: {text}")
        await bot.api.send_message(
            params={
                "chat_id": chat_id,
                "text": text,
            }
        )

    return {"success": True}


def wait_for_dapr_ready(
    dapr_port=3500, retries=20, delay=2, task_status=trio.TASK_STATUS_IGNORED
):
    """Wait for the Dapr sidecar to be ready.

    Arguments:
    dapr_port -- The port on which the Dapr sidecar is listening.
    retries -- The number of times to check if Dapr is ready before giving up.
    delay -- The delay between checks.
    """
    dapr_url = f"http://localhost:{dapr_port}/v1.0/healthz"
    for _ in range(retries):
        try:
            response = requests.get(dapr_url)
            if response.status_code == 204:
                print("Dapr is ready.")
                task_status.started()
                return
        except Exception as e:
            print(f"Dapr is not ready yet: {e}")
        time.sleep(delay)

    raise RuntimeError("Dapr sidecar is not ready.")


# Define an async wrapper for wait_for_dapr_ready that reports when it's done
async def async_wait_for_dapr_ready(task_status=trio.TASK_STATUS_IGNORED):
    result = await to_thread.run_sync(wait_for_dapr_ready)
    task_status.started()  # signal that this task is ready
    return result


# Define an async wrapper for init_secrets that reports when it's done
async def async_init_secrets(task_status=trio.TASK_STATUS_IGNORED):
    result = await to_thread.run_sync(init_secrets)
    task_status.started()  # signal that this task is ready
    return result


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)
        await nursery.start(async_wait_for_dapr_ready)
        await nursery.start(async_init_secrets)

        bot = triogram.make_bot()

        nursery.start_soon(bot)
        nursery.start_soon(send_message_to_pubsub, bot)


if __name__ == "__main__":
    trio.run(main)
