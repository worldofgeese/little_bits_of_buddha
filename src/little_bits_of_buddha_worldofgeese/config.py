import logging

from dapr.clients import DaprClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DAPR_STORE_NAME = "kubernetes"

with DaprClient() as d:
    # Get the Telegram bot token from the Dapr state store
    key = "telegram-secret"
    secret = d.get_secret(DAPR_STORE_NAME, key=key)
    logging.info("Fetched Secret: %s", secret.secret)
    TRIOGRAM_TOKEN = secret.secret["token"]

with DaprClient() as d:
    # Get the OpenAI API key from the Dapr state store
    key = "openai-secret"
    secret = d.get_secret(DAPR_STORE_NAME, key=key)
    logging.info("Fetched Secret: %s", secret.secret)
    OPENAI_API_KEY = secret.secret["api-key"]
