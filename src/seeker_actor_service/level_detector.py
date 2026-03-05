"""Practice level detection for Buddhist practitioners."""

import re

# Practice levels in order
LEVELS = ["newcomer", "beginner", "intermediate", "experienced"]

# Vocabulary terms and their scores
VOCAB_BASIC = {
    "dukkha",
    "sutta",
    "dharma",
    "dhamma",
    "karma",
    "kamma",
    "nirvana",
    "nibbana",
    "sangha",
    "buddha",
    "meditation",
    "mindfulness",
    "metta",
    "sila",
    "dana",
}

VOCAB_INTERMEDIATE = {
    "anicca",
    "anatta",
    "sati",
    "samadhi",
    "jhana",
    "dhyana",
    "vipassana",
    "panna",
    "prajna",
    "vedana",
    "sankhara",
    "upekkha",
    "paticcasamuppada",
    "dependent origination",
    "five aggregates",
    "four noble truths",
    "eightfold path",
    "three marks",
}

VOCAB_ADVANCED = {
    "nimitta",
    "bhavanga",
    "cessation",
    "nirodha",
    "sotapanna",
    "stream-entry",
    "arahat",
    "arahant",
    "asava",
    "tanha",
    "avijja",
    "nama-rupa",
    "ayatana",
    "khanda",
    "parinibbana",
    "abhidhamma",
}

# Simple question patterns
SIMPLE_PATTERNS = [
    r"\bwhat\s+is\b",
    r"\bhow\s+do\s+i\b",
    r"\bwho\s+was\b",
]

# Comparative question patterns
COMPARATIVE_PATTERNS = [
    r"\bdiffer",
    r"\brelationship",
    r"\bcompared\s+to\b",
    r"\bversus\b",
]

# Analytical question patterns (sutta references)
SUTTA_PATTERNS = [
    r"\b(SN|MN|DN|AN)\s*\d+",
]

# Analytical practice terms
ANALYTICAL_TERMS = {"jhana", "nimitta", "sotapanna", "stream-entry"}

# Practice reference patterns
PRACTICE_BASIC = [
    r"\bi\s+meditate\b",
    r"\bmy\s+practice\b",
    r"\bwhen\s+i\s+sit\b",
    r"\bon\s+the\s+cushion\b",
]

PRACTICE_INTERMEDIATE = [
    r"\bretreats?\b",
    r"\bteacher\b",
    r"\bsangha\b",
]

PRACTICE_ADVANCED = [
    r"\bnoting\b",
    r"\bbody\s+scanning\b",
    r"\bkasina\b",
    r"\banapanasati\s+practice\b",
]

# Promotion thresholds
PROMOTION_THRESHOLDS = {
    "newcomer": {"signals": 3, "conversations": 3, "next": "beginner"},
    "beginner": {"signals": 5, "conversations": 11, "next": "intermediate"},
    "intermediate": {"signals": 7, "conversations": 31, "next": "experienced"},
    "experienced": {"signals": float("inf"), "conversations": float("inf"), "next": None},
}


def _count_vocabulary_score(message: str) -> int:
    """Count vocabulary signals in a message."""
    message_lower = message.lower()
    score = 0

    # Match whole words only using word boundaries
    for term in VOCAB_BASIC:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, message_lower):
            score += 1

    for term in VOCAB_INTERMEDIATE:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, message_lower):
            score += 2

    for term in VOCAB_ADVANCED:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, message_lower):
            score += 3

    return score


def _count_complexity_score(message: str) -> int:
    """Count question complexity signals."""
    message_lower = message.lower()
    score = 0

    # Check for analytical (highest priority)
    for pattern in SUTTA_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            score = max(score, 3)

    # Check for analytical terms
    for term in ANALYTICAL_TERMS:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, message_lower):
            score = max(score, 3)

    # Check for comparative
    for pattern in COMPARATIVE_PATTERNS:
        if re.search(pattern, message_lower):
            score = max(score, 2)

    # Check for simple
    for pattern in SIMPLE_PATTERNS:
        if re.search(pattern, message_lower):
            score = max(score, 1)

    return score


def _count_practice_score(message: str) -> int:
    """Count practice reference signals."""
    message_lower = message.lower()
    score = 0

    # Check for advanced practice
    for pattern in PRACTICE_ADVANCED:
        if re.search(pattern, message_lower):
            score = max(score, 3)

    # Check for intermediate practice
    for pattern in PRACTICE_INTERMEDIATE:
        if re.search(pattern, message_lower):
            score = max(score, 2)

    # Check for basic practice
    for pattern in PRACTICE_BASIC:
        if re.search(pattern, message_lower):
            score = max(score, 1)

    return score


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
    # Score the current message
    vocab_score = _count_vocabulary_score(message)
    complexity_score = _count_complexity_score(message)
    practice_score = _count_practice_score(message)

    # Create signal record for this message
    message_num = len(signal_history) + 1
    signal_record = {
        "message_num": message_num,
        "vocab": vocab_score,
        "complexity": complexity_score,
        "practice": practice_score,
    }

    # Update history
    updated_history = signal_history + [signal_record]

    # Calculate total signals
    total_signals = sum(
        record["vocab"] + record["complexity"] + record["practice"]
        for record in updated_history
    )

    # Determine the new level
    new_level = current_level

    # Check if we can promote
    current_level_index = LEVELS.index(current_level)

    # Try to promote to the next level(s)
    for level_index in range(current_level_index, len(LEVELS) - 1):
        level = LEVELS[level_index]
        threshold = PROMOTION_THRESHOLDS[level]

        # Check if we meet the requirements for promotion to the next level
        if (
            total_signals >= threshold["signals"]
            and conversation_count >= threshold["conversations"]
        ):
            new_level = threshold["next"]
        else:
            # Stop trying to promote if we don't meet this threshold
            break

    return new_level, updated_history
