import logging
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DAPR_STORE_NAME = "local-secret-store"


def init_secrets():
    # Prefer environment variable (set by compose/systemd) over Dapr secret store
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        logging.info("Using ANTHROPIC_AUTH_TOKEN from environment")
        return

    from dapr.clients import DaprClient

    with DaprClient() as d:
        # Get the Anthropic API key from the Dapr state store
        anthropic_key = "anthropic-secret"
        secret = d.get_secret(DAPR_STORE_NAME, key=anthropic_key)
        logging.info("Fetched Secret: %s", secret.secret)
        os.environ["ANTHROPIC_AUTH_TOKEN"] = secret.secret["anthropic-secret"]
