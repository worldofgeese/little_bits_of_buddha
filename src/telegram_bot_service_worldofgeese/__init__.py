import logging
import os

from dapr.clients import DaprClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DAPR_STORE_NAME = "azure-key-vault-secret-store"


def init_secrets():
    with DaprClient() as d:
        # Get the Telegram bot token from the Dapr state store
        telegram_key = "telegram-secret"
        secret = d.get_secret(DAPR_STORE_NAME, key=telegram_key)
        logging.info("Fetched Secret: %s", secret.secret)
        os.environ["TRIOGRAM_TOKEN"] = secret.secret["telegram-secret"]
