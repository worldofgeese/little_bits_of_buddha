"""Breathing meditation workflow (ānāpānasati).

Workflow steps:
1. Get seeker state for personalization
2. Send welcome message
3. Settle timer (30 seconds)
4. Send breathing focus instruction
5. Main meditation timer (configurable: 5/10/15/20 minutes)
6. Send check-in bell
7. Wait for external event (user response) with 5-minute timeout
8. Close meditation + log sit + sutta suggestion

This is a GENERATOR-based workflow (uses yield, NOT async/await).
"""

from datetime import timedelta

from dapr.ext.workflow import DaprWorkflowContext, when_any

from meditation_workflow_service.templates import get_breathing_instruction


def breathing_meditation(ctx: DaprWorkflowContext):
    """Breathing meditation workflow.

    Input:
        chat_id: Telegram chat ID
        duration_minutes: Main meditation duration (default: 5)

    Yields control to the workflow runtime for activities and timers.
    """
    # Get workflow input
    input_data = ctx.get_input()
    chat_id = input_data["chat_id"]
    duration_minutes = input_data.get("duration_minutes", 5)

    # Step 1: Get seeker state for personalization
    seeker_state = yield ctx.call_activity(
        "get_seeker_state", input={"chat_id": chat_id}
    )
    practice_level = seeker_state.get("practice_level", "beginner")

    # Step 2: Send welcome message
    welcome_text = get_breathing_instruction("welcome", practice_level)
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": welcome_text}
    )

    # Step 3: Settle timer (30 seconds)
    settle_text = get_breathing_instruction("settle", practice_level)
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": settle_text}
    )
    yield ctx.create_timer(timedelta(seconds=30))

    # Step 4: Send breathing focus instruction
    focus_text = get_breathing_instruction("focus", practice_level)
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": focus_text}
    )

    # Step 5: Main meditation timer
    main_text = get_breathing_instruction("main_period", practice_level)
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": main_text}
    )
    yield ctx.create_timer(timedelta(minutes=duration_minutes))

    # Step 6: Send check-in bell
    checkin_text = get_breathing_instruction("checkin", practice_level)
    yield ctx.call_activity(
        "send_instruction", input={"chat_id": chat_id, "text": checkin_text}
    )

    # Step 7: Wait for external event (user response) with 5-minute timeout
    # User can share their experience, or we timeout gracefully
    timeout_task = ctx.create_timer(timedelta(minutes=5))
    event_task = ctx.wait_for_external_event("user_response")

    yield when_any([event_task, timeout_task])

    # Step 8: Close meditation (log sit, suggest sutta)
    yield ctx.call_activity(
        "close_meditation",
        input={
            "chat_id": chat_id,
            "type": "breathing",
            "duration_minutes": duration_minutes,
        },
    )

    return {"status": "completed", "duration_minutes": duration_minutes}
