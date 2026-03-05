# Task: WP3 — Practice Level Detection

## Context

Little Bits of Buddha (LBOB) is a Telegram chatbot that teaches the Early Buddhist Dhamma using LLM + semantic sutta search. Phase 2 adds Dapr Virtual Actors per user. This task implements the practice level detection module — a pure-logic heuristic that scores a user's practice level from their conversation patterns.

**Repo:** `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
**Python:** 3.12+
**Branch:** `feat/practice-level`

## What to Build

### `src/seeker_actor_service/level_detector.py`

Also create `src/seeker_actor_service/__init__.py` (empty or minimal).

#### Practice Levels
- `newcomer` — Default for new users. No Buddhist background assumed.
- `beginner` — Recognizes basic concepts. Has started practice.
- `intermediate` — Familiar with core doctrines. Regular practice.
- `experienced` — Deep knowledge. Can discuss subtle points in Pali.

#### Detection Signals

**1. Vocabulary Signal** — Detect Pali/Buddhist terms in user messages.

Score per term category:
- **Basic** (1 point): dukkha, sutta, dharma/dhamma, karma/kamma, nirvana/nibbana, sangha, buddha, meditation, mindfulness, metta, sila, dana
- **Intermediate** (2 points): anicca, anatta, sati, samadhi, jhana/dhyana, vipassana, panna/prajna, vedana, sankhara, upekkha, paticcasamuppada, dependent origination, five aggregates, four noble truths, eightfold path, three marks
- **Advanced** (3 points): nimitta, bhavanga, cessation, nirodha, sotapanna, stream-entry, arahat/arahant, asava, tanha, avijja, nama-rupa, ayatana, khanda, parinibbana, abhidhamma

Case-insensitive matching. Match whole words only (avoid matching "karma" inside "karmatic").

**2. Question Complexity** — Score based on question structure.
- Simple questions (1 point): "What is X?", "How do I meditate?", "Who was the Buddha?"
- Comparative (2 points): "How does X differ from Y?", "What's the relationship between X and Y?"
- Analytical (3 points): Questions referencing specific suttas, asking about edge cases in doctrine, questions about meditation stages

Detect via simple heuristics:
- Contains "what is" or "how do I" → simple
- Contains "differ", "relationship", "compared to", "versus" → comparative
- Contains sutta references (SN, MN, DN, AN pattern) or stage terms (jhana, nimitta, sotapanna) → analytical

**3. Practice References** — Detect mentions of personal practice.
- "I meditate" / "my practice" / "when I sit" / "on the cushion" → beginner minimum
- "retreats" / "teacher" / "sangha" (in practice context) → intermediate signal
- Specific technique mentions ("noting", "body scanning", "kasina", "anapanasati practice") → intermediate/experienced

**4. Conversation Count Thresholds** — Floor values.
- 0-2 conversations: newcomer (regardless of signals)
- 3-10 conversations: beginner minimum
- 11-30 conversations: can reach intermediate
- 31+: can reach experienced

#### Core Function

```python
def detect_practice_level(
    current_level: str,
    message: str,
    conversation_count: int,
    signal_history: list[dict],  # prior signal scores
) -> tuple[str, list[dict]]:
    """
    Analyze a message and return (new_level, updated_signal_history).
    
    Rules:
    - Level can only go UP, never down
    - Promotion requires 3+ signals at the new level across multiple messages
    - conversation_count sets a floor
    - Returns updated signal_history for actor to persist
    """
```

#### Level Thresholds

To promote from current → next:
- `newcomer → beginner`: 3+ signals at beginner level AND conversation_count >= 3
- `beginner → intermediate`: 5+ signals at intermediate level AND conversation_count >= 11
- `intermediate → experienced`: 7+ signals at experienced level AND conversation_count >= 31

"Signals at X level" = total accumulated signal points from vocabulary + complexity + practice, where each message contributes its scores to the history.

### Tests: `tests/test_level_detector.py`

**Write tests FIRST, commit them, THEN implement.**

Test cases:
1. New user starts as newcomer
2. Vocabulary scoring: basic, intermediate, advanced terms
3. Question complexity: simple, comparative, analytical
4. Practice reference detection
5. Level never decreases (set to intermediate, send newcomer-level message → stays intermediate)
6. Promotion requires 3+ signals (2 signals insufficient)
7. Conversation count floor (experienced vocab at conversation 1 → still newcomer)
8. Multi-message accumulation (signals accumulate across messages)
9. Whole-word matching ("karma" matches, "karmatic" doesn't match on "karma")
10. Case insensitivity

Use pytest. All sync (no trio needed — this is pure logic).

## Constraints

- Only create files in `src/seeker_actor_service/` and `tests/`
- No external dependencies — stdlib only (re, collections)
- Do NOT modify any existing files
- Keep signal_history as simple dicts (must be JSON-serializable for Dapr actor state)

## Branch & Push

Work on branch: `feat/practice-level`. Commit AND push when done.
TDD: commit failing tests first, then implementation in a separate commit.

## Self-Review

Re-read your diff. Write out 3 concerns, TDD compliance check.
