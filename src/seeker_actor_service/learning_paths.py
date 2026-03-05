"""Structured learning paths for Early Buddhist teachings."""

CURRICULUM = {
    "1": {
        "title": "The Four Noble Truths",
        "topics": {
            "1.1": {
                "title": "Dukkha (suffering/unsatisfactoriness)",
                "keywords": [
                    "dukkha",
                    "suffering",
                    "unsatisfactoriness",
                    "first noble truth",
                ],
            },
            "1.2": {
                "title": "Samudaya (origin — craving)",
                "keywords": [
                    "samudaya",
                    "craving",
                    "tanha",
                    "origin",
                    "second noble truth",
                    "cause of suffering",
                ],
            },
            "1.3": {
                "title": "Nirodha (cessation)",
                "keywords": [
                    "nirodha",
                    "cessation",
                    "third noble truth",
                    "end of suffering",
                    "nibbana",
                ],
            },
            "1.4": {
                "title": "Magga (the path)",
                "keywords": [
                    "magga",
                    "path",
                    "fourth noble truth",
                    "eightfold path",
                ],
            },
        },
    },
    "2": {
        "title": "The Noble Eightfold Path",
        "topics": {
            "2.1": {
                "title": "Right View (sammā diṭṭhi)",
                "keywords": ["right view", "samma ditthi", "wise understanding"],
            },
            "2.2": {
                "title": "Right Intention (sammā saṅkappa)",
                "keywords": ["right intention", "right thought", "samma sankappa"],
            },
            "2.3": {
                "title": "Right Speech (sammā vācā)",
                "keywords": ["right speech", "samma vaca"],
            },
            "2.4": {
                "title": "Right Action (sammā kammanta)",
                "keywords": ["right action", "samma kammanta", "sila", "ethics"],
            },
            "2.5": {
                "title": "Right Livelihood (sammā ājīva)",
                "keywords": ["right livelihood", "samma ajiva"],
            },
            "2.6": {
                "title": "Right Effort (sammā vāyāma)",
                "keywords": ["right effort", "samma vayama"],
            },
            "2.7": {
                "title": "Right Mindfulness (sammā sati)",
                "keywords": [
                    "right mindfulness",
                    "samma sati",
                    "sati",
                    "satipatthana",
                ],
            },
            "2.8": {
                "title": "Right Concentration (sammā samādhi)",
                "keywords": [
                    "right concentration",
                    "samma samadhi",
                    "jhana",
                    "samadhi",
                ],
            },
        },
    },
    "3": {
        "title": "Meditation Practices",
        "topics": {
            "3.1": {
                "title": "Ānāpānasati (breathing)",
                "keywords": [
                    "anapanasati",
                    "breathing",
                    "breath meditation",
                    "mindfulness of breathing",
                ],
            },
            "3.2": {
                "title": "Mettā bhāvanā (loving-kindness)",
                "keywords": [
                    "metta",
                    "loving-kindness",
                    "lovingkindness",
                    "metta bhavana",
                ],
            },
            "3.3": {
                "title": "Body contemplation",
                "keywords": [
                    "body scan",
                    "body contemplation",
                    "kayanupassana",
                    "body meditation",
                ],
            },
            "3.4": {
                "title": "Walking meditation",
                "keywords": [
                    "walking meditation",
                    "cankama",
                    "walking practice",
                ],
            },
        },
    },
    "4": {
        "title": "Key Doctrines",
        "topics": {
            "4.1": {
                "title": "Dependent Origination (paṭiccasamuppāda)",
                "keywords": [
                    "dependent origination",
                    "paticcasamuppada",
                    "conditioned arising",
                    "twelve links",
                ],
            },
            "4.2": {
                "title": "Three Marks of Existence",
                "keywords": [
                    "three marks",
                    "tilakkhana",
                    "anicca",
                    "impermanence",
                    "anatta",
                    "not-self",
                    "dukkha",
                ],
            },
            "4.3": {
                "title": "Five Aggregates (khandhas)",
                "keywords": [
                    "khandha",
                    "aggregates",
                    "five aggregates",
                    "skandha",
                    "form",
                    "feeling",
                    "perception",
                    "formations",
                    "consciousness",
                ],
            },
        },
    },
}

# Progress states
NOT_STARTED = "not_started"
INTRODUCED = "introduced"  # LLM discussed it
EXPLORED = "explored"  # 3+ conversations touching it
PRACTICED = "practiced"  # Meditation topics only, after logged sits


def detect_topics(text: str, detected_themes: list[str] | None = None) -> list[str]:
    """Detect which curriculum topics are referenced in text/themes.

    Returns list of topic IDs (e.g., ["1.1", "2.7"]).
    """
    found = []
    text_lower = text.lower()
    all_terms = (detected_themes or []) + [text_lower]
    search_text = " ".join(all_terms).lower()

    for section_id, section in CURRICULUM.items():
        for topic_id, topic in section["topics"].items():
            for keyword in topic["keywords"]:
                if keyword.lower() in search_text:
                    found.append(topic_id)
                    break
    return list(set(found))


def update_progress(
    current_progress: dict, detected_topics: list[str], practice_journal: list | None = None
) -> dict:
    """Update learning path progress based on detected topics.

    Rules:
    - not_started → introduced: when topic is detected in conversation
    - introduced → explored: when topic has been detected in 3+ separate conversations
    - explored → practiced: only for section 3 (meditation) topics, when matching sits are logged
    - Progress NEVER goes backward
    """
    progress = dict(current_progress)  # shallow copy

    for topic_id in detected_topics:
        if topic_id not in progress:
            progress[topic_id] = {"status": INTRODUCED, "touch_count": 1}
        else:
            entry = progress[topic_id]
            entry["touch_count"] = entry.get("touch_count", 0) + 1

            if entry["status"] == INTRODUCED and entry["touch_count"] >= 3:
                entry["status"] = EXPLORED

    # Check meditation practice topics (section 3)
    if practice_journal:
        practice_types = {e.get("practice_type", "") for e in practice_journal}
        type_to_topic = {
            "breathing": "3.1",
            "metta": "3.2",
            "body_scan": "3.3",
            "walking": "3.4",
        }
        for ptype, topic_id in type_to_topic.items():
            if ptype in practice_types and topic_id in progress:
                if progress[topic_id]["status"] in (INTRODUCED, EXPLORED):
                    progress[topic_id]["status"] = PRACTICED

    return progress


def suggest_next(progress: dict, practice_level: str) -> dict | None:
    """Suggest the next topic to explore based on current progress.

    Strategy: sequential within sections, sections unlocked progressively.
    Returns topic dict with id, title, section_title, or None if all explored.
    """
    for section_id, section in CURRICULUM.items():
        for topic_id, topic in section["topics"].items():
            if topic_id not in progress or progress[topic_id]["status"] == NOT_STARTED:
                return {
                    "id": topic_id,
                    "title": topic["title"],
                    "section": section["title"],
                }
    return None  # All topics at least introduced


def format_path_progress(progress: dict) -> str:
    """Format progress as a readable map for /path command."""
    lines = []
    for section_id, section in CURRICULUM.items():
        lines.append(f"\n📚 *{section['title']}*")
        for topic_id, topic in section["topics"].items():
            if topic_id in progress:
                status = progress[topic_id]["status"]
                icon = {"introduced": "🔵", "explored": "🟢", "practiced": "⭐"}[
                    status
                ]
            else:
                icon = "⚪"
            lines.append(f"  {icon} {topic['title']}")

    legend = "\n⚪ Not started · 🔵 Introduced · 🟢 Explored · ⭐ Practiced"
    return "\n".join(lines) + "\n" + legend
