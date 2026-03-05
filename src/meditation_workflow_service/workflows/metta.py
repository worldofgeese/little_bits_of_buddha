"""Metta (loving-kindness) meditation workflow.

Workflow steps:
1. Get seeker state
2. Send welcome message
3. Self-directed metta (2 minutes)
4. Loved one (2 minutes)
5. Neutral person (2 minutes)
6. Difficult person (2 minutes)
7. All beings (3 minutes)
8. Close meditation + log sit + sutta suggestion

Each phase: send instruction, create timer, then move to next phase.
Phrases from Karaniya Metta Sutta (Snp 1.8).

This is a GENERATOR-based workflow (uses yield, NOT async/await).
"""

from datetime import timedelta
from dapr.ext.workflow import DaprWorkflowContext

from meditation_workflow_service.templates import get_metta_instruction


def metta_meditation(ctx: DaprWorkflowContext):
    """Metta (loving-kindness) meditation workflow.

    Input:
        chat_id: Telegram chat ID

    Yields control to the workflow runtime for activities and timers.
    """
    # Get workflow input
    input_data = ctx.get_input()
    chat_id = input_data["chat_id"]

    # Total duration for logging: 2+2+2+2+3 = 11 minutes
    total_duration = 11

    # Step 1: Get seeker state (for potential future personalization)
    seeker_state = yield ctx.call_activity(
        "get_seeker_state", input={"chat_id": chat_id}
    )

    # Step 2: Send welcome message
    welcome_text = get_metta_instruction("welcome")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": welcome_text}
    )

    # Brief pause after welcome
    yield ctx.create_timer(timedelta(seconds=10))

    # Step 3: Self-directed metta (2 minutes)
    self_text = get_metta_instruction("self")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": self_text}
    )
    yield ctx.create_timer(timedelta(minutes=2))

    # Step 4: Loved one (2 minutes)
    loved_text = get_metta_instruction("loved_one")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": loved_text}
    )
    yield ctx.create_timer(timedelta(minutes=2))

    # Step 5: Neutral person (2 minutes)
    neutral_text = get_metta_instruction("neutral")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": neutral_text}
    )
    yield ctx.create_timer(timedelta(minutes=2))

    # Step 6: Difficult person (2 minutes)
    difficult_text = get_metta_instruction("difficult")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": difficult_text}
    )
    yield ctx.create_timer(timedelta(minutes=2))

    # Step 7: All beings (3 minutes)
    all_beings_text = get_metta_instruction("all_beings")
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": all_beings_text}
    )
    yield ctx.create_timer(timedelta(minutes=3))

    # Step 8: Close meditation (log sit, suggest sutta)
    yield ctx.call_activity(
        "close_meditation",
        input={
            "chat_id": chat_id,
            "type": "metta",
            "duration_minutes": total_duration,
        },
    )

    return {"status": "completed", "duration_minutes": total_duration}
