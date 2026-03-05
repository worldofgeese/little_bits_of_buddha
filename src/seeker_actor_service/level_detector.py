"""Practice level detection for Buddhist practitioners."""


def detect_practice_level(
    current_level: str,
    message: str,
    conversation_count: int,
    signal_history: list[dict],
) -> tuple[str, list[dict]]:
    """
    Analyze a message and return (new_level, updated_signal_history).

    Rules:
    - Level can only go UP, never down
    - Promotion requires accumulated signals at the new level across multiple messages
    - conversation_count sets a floor
    - Returns updated signal_history for actor to persist
    """
    # Placeholder implementation to make tests fail with meaningful errors
    raise NotImplementedError("detect_practice_level not yet implemented")
