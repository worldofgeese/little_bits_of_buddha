import logging
import os

from dapr.clients import DaprClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DAPR_STORE_NAME = "azure-key-vault-secret-store"


def init_secrets():
    with DaprClient() as d:
        # Get the OpenAI API key from the Dapr state store
        openai_key = "openai-secret"
        secret = d.get_secret(DAPR_STORE_NAME, key=openai_key)
        logging.info("Fetched Secret: %s", secret.secret)
        os.environ["OPENAI_API_KEY"] = secret.secret["openai-secret"]
