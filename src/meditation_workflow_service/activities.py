"""Meditation workflow activities.

Activities are synchronous functions executed by the workflow.
They interact with other services via Dapr (pub/sub, service invocation).
"""

import json
from dapr.clients import DaprClient
from dapr.ext.workflow import WorkflowActivityContext


def send_instruction(ctx: WorkflowActivityContext, input: dict):
    """Send a meditation instruction to the seeker via Telegram pub/sub.

    Args:
        ctx: Workflow activity context
        input: Dict with keys:
            - chat_id: Telegram chat ID
            - text: Instruction text to send
    """
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": input["chat_id"], "text": input["text"]}),
            data_content_type="application/json",
        )


def get_seeker_state(ctx: WorkflowActivityContext, input: dict):
    """Read seeker state to personalize instructions.

    Args:
        ctx: Workflow activity context
        input: Dict with keys:
            - chat_id: Telegram chat ID

    Returns:
        Dict with seeker state (practice_level, meditation_count, etc.)
    """
    with DaprClient() as client:
        result = client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{input['chat_id']}/method/get_state",
            http_verb="GET",
        )
        return json.loads(result.text())


def close_meditation(ctx: WorkflowActivityContext, input: dict):
    """Send closing message, log sit, suggest sutta.

    Args:
        ctx: Workflow activity context
        input: Dict with keys:
            - chat_id: Telegram chat ID
            - type: Meditation type (breathing, metta)
            - duration_minutes: Duration in minutes
    """
    chat_id = input["chat_id"]
    meditation_type = input["type"]
    duration = input.get("duration_minutes", 5)

    with DaprClient() as client:
        # 1. Send closing message
        closing_text = f"🙏 Thank you for sitting with awareness. May the merit of this practice benefit all beings.\n\n_You practiced {meditation_type} meditation for {duration} minutes._"
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="responses",
            data=json.dumps({"chat_id": chat_id, "text": closing_text}),
            data_content_type="application/json",
        )

        # 2. Log the sit via seeker actor
        client.invoke_method(
            app_id="seeker-actor-service",
            method_name=f"actors/SeekerActor/{chat_id}/method/log_sit",
            http_verb="POST",
            data=json.dumps(
                {"type": meditation_type, "duration_minutes": duration}
            ),
        )

        # 3. Get sutta suggestion from wisdom service
        context = f"The user just completed a {duration}-minute {meditation_type} meditation session."
        question = f"Can you suggest a relevant sutta from the Pali Canon that relates to {meditation_type} meditation? Just give the sutta name and a brief excerpt."

        wisdom_response = client.invoke_method(
            app_id="wisdom-service",
            method_name="wisdom/ask",
            http_verb="POST",
            data=json.dumps({"chat_id": chat_id, "question": question, "context": context}),
        )

        # 4. Send sutta suggestion
        try:
            wisdom_data = json.loads(wisdom_response.text())
            sutta_text = wisdom_data.get("response", "")
            if sutta_text:
                client.publish_event(
                    pubsub_name="pubsub",
                    topic_name="responses",
                    data=json.dumps(
                        {
                            "chat_id": chat_id,
                            "text": f"📖 *Further Reading*\n\n{sutta_text}",
                        }
                    ),
                    data_content_type="application/json",
                )
        except Exception:
            # If wisdom service fails, continue gracefully
            pass
