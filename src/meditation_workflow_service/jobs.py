"""Dapr Jobs handlers for scheduled delivery."""

import json
import logging

from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


def handle_daily_sutta(job_data: dict):
    """Called by Dapr Scheduler for daily sutta delivery.

    1. Read seeker state (practice_level, topics_explored)
    2. Call wisdom-service to get a sutta matching level + unexplored topics
    3. Send sutta to Telegram via pub/sub
    """
    chat_id = job_data["chat_id"]
    with DaprClient() as client:
        # Get seeker state
        state = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{chat_id}/method/get_state",
            http_verb="GET",
        )
        seeker = json.loads(state.text())

        # Ask wisdom-service for a sutta recommendation
        response = client.invoke_method(
            app_id="wisdom-service",
            method_name="wisdom/ask",
            data=json.dumps(
                {
                    "chat_id": chat_id,
                    "message": "Share a sutta that would be helpful for my practice today.",
                    "context": {
                        "practice_level": seeker.get("practice_level", "newcomer"),
                        "topics_explored": seeker.get("topics_explored", []),
                        "history": [],
                        "is_daily_sutta": True,
                    },
                }
            ),
            content_type="application/json",
            http_verb="POST",
        )
        wisdom = json.loads(response.text())

        # Send via pub/sub to Telegram
        message_text = f"🌅 *Daily Sutta*\n\n{wisdom['response']}"
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": chat_id, "text": message_text}),
            data_content_type="application/json",
        )


def handle_weekly_checkin(job_data: dict):
    """Called by Dapr Scheduler for weekly practice check-in.

    1. Read seeker's practice journal (last 7 days)
    2. Generate warm summary via wisdom-service
    3. Send to Telegram
    """
    chat_id = job_data["chat_id"]
    with DaprClient() as client:
        # Get weekly summary from actor
        summary = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{chat_id}/method/get_weekly_summary",
            data=json.dumps({"days": 7}),
            content_type="application/json",
            http_verb="POST",
        )
        summary_data = json.loads(summary.text())

        # Ask wisdom-service to generate a warm check-in message
        response = client.invoke_method(
            app_id="wisdom-service",
            method_name="wisdom/ask",
            data=json.dumps(
                {
                    "chat_id": chat_id,
                    "message": f"Generate a warm weekly practice check-in based on this data: {json.dumps(summary_data)}",
                    "context": {
                        "practice_level": summary_data.get(
                            "practice_level", "newcomer"
                        ),
                        "is_weekly_checkin": True,
                    },
                }
            ),
            content_type="application/json",
            http_verb="POST",
        )
        wisdom = json.loads(response.text())

        message_text = f"🙏 *Weekly Practice Check-in*\n\n{wisdom['response']}"
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": chat_id, "text": message_text}),
            data_content_type="application/json",
        )
