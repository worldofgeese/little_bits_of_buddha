# Task: WP5 — Structured Learning Paths

## Context
Little Bits of Buddha — Telegram Dhamma teacher bot. Python 3.12, trio (NOT asyncio). SeekerActor (Dapr Virtual Actor) holds per-user state including practice_level, topics_explored, and practice_journal. We want to add a structured curriculum that tracks what each seeker has learned and suggests what to explore next.

## Branch
Work on branch: `feat/learning-paths` (already checked out).
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_learning_paths.py`. Commit them.
Then implement until tests pass. Commit again.

## Existing Files to Read First
- `src/seeker_actor_service/seeker_actor.py` — Actor with SeekerState (practice_level, topics_explored, practice_journal)
- `src/seeker_actor_service/seeker_interface.py` — ActorInterface
- `src/telegram_bot_service_worldofgeese/commands.py` — Existing commands (/sit, /journal, /start, /level, /forget)
- `tests/test_seeker_actor.py` — Existing actor tests

## What to Build

### 1. `src/seeker_actor_service/learning_paths.py`

Curriculum definition and progress tracking:

```python
"""Structured learning paths for Early Buddhist teachings."""

CURRICULUM = {
    "1": {
        "title": "The Four Noble Truths",
        "topics": {
            "1.1": {"title": "Dukkha (suffering/unsatisfactoriness)", "keywords": ["dukkha", "suffering", "unsatisfactoriness", "first noble truth"]},
            "1.2": {"title": "Samudaya (origin — craving)", "keywords": ["samudaya", "craving", "tanha", "origin", "second noble truth", "cause of suffering"]},
            "1.3": {"title": "Nirodha (cessation)", "keywords": ["nirodha", "cessation", "third noble truth", "end of suffering", "nibbana"]},
            "1.4": {"title": "Magga (the path)", "keywords": ["magga", "path", "fourth noble truth", "eightfold path"]},
        }
    },
    "2": {
        "title": "The Noble Eightfold Path",
        "topics": {
            "2.1": {"title": "Right View (sammā diṭṭhi)", "keywords": ["right view", "samma ditthi", "wise understanding"]},
            "2.2": {"title": "Right Intention (sammā saṅkappa)", "keywords": ["right intention", "right thought", "samma sankappa"]},
            "2.3": {"title": "Right Speech (sammā vācā)", "keywords": ["right speech", "samma vaca"]},
            "2.4": {"title": "Right Action (sammā kammanta)", "keywords": ["right action", "samma kammanta", "sila", "ethics"]},
            "2.5": {"title": "Right Livelihood (sammā ājīva)", "keywords": ["right livelihood", "samma ajiva"]},
            "2.6": {"title": "Right Effort (sammā vāyāma)", "keywords": ["right effort", "samma vayama"]},
            "2.7": {"title": "Right Mindfulness (sammā sati)", "keywords": ["right mindfulness", "samma sati", "sati", "satipatthana"]},
            "2.8": {"title": "Right Concentration (sammā samādhi)", "keywords": ["right concentration", "samma samadhi", "jhana", "samadhi"]},
        }
    },
    "3": {
        "title": "Meditation Practices",
        "topics": {
            "3.1": {"title": "Ānāpānasati (breathing)", "keywords": ["anapanasati", "breathing", "breath meditation", "mindfulness of breathing"]},
            "3.2": {"title": "Mettā bhāvanā (loving-kindness)", "keywords": ["metta", "loving-kindness", "lovingkindness", "metta bhavana"]},
            "3.3": {"title": "Body contemplation", "keywords": ["body scan", "body contemplation", "kayanupassana", "body meditation"]},
            "3.4": {"title": "Walking meditation", "keywords": ["walking meditation", "cankama", "walking practice"]},
        }
    },
    "4": {
        "title": "Key Doctrines",
        "topics": {
            "4.1": {"title": "Dependent Origination (paṭiccasamuppāda)", "keywords": ["dependent origination", "paticcasamuppada", "conditioned arising", "twelve links"]},
            "4.2": {"title": "Three Marks of Existence", "keywords": ["three marks", "tilakkhana", "anicca", "impermanence", "anatta", "not-self", "dukkha"]},
            "4.3": {"title": "Five Aggregates (khandhas)", "keywords": ["khandha", "aggregates", "five aggregates", "skandha", "form", "feeling", "perception", "formations", "consciousness"]},
        }
    }
}

# Progress states
NOT_STARTED = "not_started"
INTRODUCED = "introduced"    # LLM discussed it
EXPLORED = "explored"        # 3+ conversations touching it
PRACTICED = "practiced"      # Meditation topics only, after logged sits

def detect_topics(text: str, detected_themes: list[str] = None) -> list[str]:
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

def update_progress(current_progress: dict, detected_topics: list[str], practice_journal: list = None) -> dict:
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
            "walking": "3.4"
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
                    "section": section["title"]
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
                icon = {"introduced": "🔵", "explored": "🟢", "practiced": "⭐"}[status]
            else:
                icon = "⚪"
            lines.append(f"  {icon} {topic['title']}")
    
    legend = "\n⚪ Not started · 🔵 Introduced · 🟢 Explored · ⭐ Practiced"
    return "\n".join(lines) + "\n" + legend
```

### 2. Add path_progress to SeekerActor state

In `src/seeker_actor_service/seeker_actor.py`:
- Add `"path_progress": {}` to default state
- After every `receive_message`, detect topics in the response and update progress:
```python
# In receive_message, after getting wisdom response:
from .learning_paths import detect_topics, update_progress
topics = detect_topics(message_text, wisdom_response.get("detected_themes", []))
if topics:
    state["path_progress"] = update_progress(
        state.get("path_progress", {}), topics, state.get("practice_journal", [])
    )
```

Add actor method:
- `get_path_progress(data: dict) -> dict` — Returns current path_progress + formatted display + next suggestion

### 3. Add `/path` Telegram command

In `src/telegram_bot_service_worldofgeese/commands.py`:
- `/path` — Call actor's `get_path_progress`, display formatted map
- Include the next suggested topic at the bottom

### 4. Tests (`tests/test_learning_paths.py`)

Write FIRST as failing tests:
1. **Curriculum structure** — All 4 sections, 15 topics present
2. **detect_topics** — "What is dukkha?" → ["1.1"]
3. **detect_topics multiple** — "Tell me about metta and right speech" → ["2.3", "3.2"]
4. **detect_topics from themes** — detected_themes=["suffering", "craving"] → ["1.1", "1.2"]
5. **update_progress new topic** — not_started → introduced
6. **update_progress count** — touch_count increments
7. **update_progress explored** — 3 touches → explored
8. **update_progress practiced** — meditation topic + matching sit → practiced
9. **Progress never decreases** — explored stays explored even if update_progress called with fewer touches
10. **suggest_next** — returns first not_started topic
11. **suggest_next all done** — returns None when all introduced
12. **format_path_progress** — correct icons for each status

## Constraints
- This project uses **trio**, NOT asyncio. Use `@pytest.mark.trio` for async tests.
- DaprClient is sync-only — wrap with `trio.to_thread.run_sync`.
- Progress NEVER goes backward (not_started → introduced → explored → practiced)
- Only section 3 (meditation) topics can reach "practiced" status
- Topic detection is keyword-based (not LLM) — fast and deterministic
- Curriculum is Early Buddhism only — no Mahayana, Vajrayana, or Zen topics

## Branch & Push
Work on branch: `feat/learning-paths`. Commit AND push when done.

## Self-Review (mandatory before final commit)
**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
