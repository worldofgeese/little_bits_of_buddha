"""Meditation instruction templates.

Provides warm, gentle instruction text grounded in Early Buddhist tradition.
Templates adapt based on practice level (beginner, intermediate, advanced).
"""

# ===== Breathing Meditation (Ānāpānasati) Templates =====

BREATHING_TEMPLATES = {
    "welcome": {
        "beginner": """🧘 Welcome to breathing meditation (ānāpānasati).

This practice comes from the Buddha's teachings in the Ānāpānasati Sutta. It's simple but profound: we'll use the breath as an anchor for awareness.

No need to change your breathing — just notice it as it is. If your mind wanders (and it will!), gently return to the breath. That gentle return *is* the practice.

Let's begin.""",
        "intermediate": """🧘 Welcome to ānāpānasati — mindfulness of breathing.

As the Buddha taught, the breath is a reliable anchor for developing concentration and insight. Today we'll settle into simple awareness of breathing in and breathing out.

When the mind wanders, notice where it went, then gently return.""",
        "advanced": """🧘 Ānāpānasati — breathing mindfulness.

The Buddha said: "Mindful, they breathe in; mindful, they breathe out." We'll rest in this simple awareness, allowing the natural settling of mind that comes with sustained attention to the breath.""",
    },
    "settle": {
        "beginner": """Take a comfortable seat. Let your body settle. Notice any tension and allow it to soften.

For the next 30 seconds, simply arrive. Notice sounds, sensations, the feeling of sitting. There's nowhere to go, nothing to fix.

*[30-second settling period]*""",
        "intermediate": """Settle into your seat. Let awareness expand to include the whole body, then gently gather attention to the breath.

*[30-second settling period]*""",
        "advanced": """Establish posture. Allow settling.

*[30-second settling period]*""",
    },
    "focus": {
        "beginner": """Now, bring attention to the breath. You might notice it at the nostrils — the coolness of the in-breath, the warmth of the out-breath. Or at the belly — the gentle rise and fall.

Choose one place and stay with it. When the mind wanders (to thoughts, sounds, sensations), gently note where it went, then return to the breath.

The wandering mind isn't a problem — noticing and returning is the practice.""",
        "intermediate": """Gather attention to the breath — wherever you feel it most clearly. Nostrils, chest, or belly.

When awareness drifts, notice the distraction without judgment, then return to the breath. The quality of the return matters: gentle, patient, kind.""",
        "advanced": """Rest attention on the breath. Notice the full cycle: in-breath, out-breath, pauses.

When attention wanders, return. The simplicity itself is the practice.""",
    },
    "main_period": {
        "beginner": """Continue with the breath. Just this: breathing in, breathing out.

If it helps, you can mentally note "in" and "out" — or simply feel the sensations of breathing.

The mind will wander many times. That's completely normal. Each time you notice and return, you're strengthening awareness.

*[Main meditation period]*""",
        "intermediate": """Continue. Stay with the direct experience of breathing — sensations, not thoughts about breathing.

Notice the texture: rough or smooth, deep or shallow. No need to change anything. Just know what's happening.

*[Main meditation period]*""",
        "advanced": """*[Main meditation period]*

Breathing in, breathing out. The mind's natural resting place.""",
    },
    "checkin": {
        "beginner": """🔔 *Bell*

The main period is complete. Take a moment to notice: How do you feel? What did you observe?

You can share your experience, or simply sit with it for now.""",
        "intermediate": """🔔 *Bell*

Notice how the mind and body feel after sitting. Any observations to note?""",
        "advanced": """🔔 *Bell*

How was the sit?""",
    },
}

METTA_TEMPLATES = {
    "welcome": """🕊️ Welcome to metta bhāvanā — the cultivation of loving-kindness.

This practice comes from the Karaniya Metta Sutta and was taught by the Buddha as a way to develop boundless goodwill toward all beings.

We'll move through five phases:
1. Ourselves
2. A loved one
3. A neutral person
4. A difficult person
5. All beings everywhere

In each phase, we'll silently repeat phrases of well-wishing. Let the words resonate in the heart, not just the head.""",
    "self": """Begin with yourself. This can feel awkward, but it's essential — we can only offer others what we've cultivated within.

Place a hand on your heart if that feels natural. Silently repeat these phrases:

*May I be safe and protected*
*May I be peaceful and happy*
*May I be healthy and strong*
*May I live with ease*

Repeat slowly, letting each phrase settle. If resistance comes up, notice it gently. The phrases themselves are the practice.

*[2-minute period]*""",
    "loved_one": """Now bring to mind someone you love — someone for whom goodwill flows easily. See their face, feel their presence.

Offer them these phrases:

*May you be safe and protected*
*May you be peaceful and happy*
*May you be healthy and strong*
*May you live with ease*

*[2-minute period]*""",
    "neutral": """Now bring to mind someone neutral — someone you neither like nor dislike. Perhaps someone you see regularly but don't know well: a neighbor, a store clerk, someone you passed today.

See them as fully human, with their own joys and struggles. Offer them the same phrases:

*May you be safe and protected*
*May you be peaceful and happy*
*May you be healthy and strong*
*May you live with ease*

*[2-minute period]*""",
    "difficult": """Now — and this is challenging — bring to mind someone difficult. Not the most difficult person, just someone who irritates you or with whom there's tension.

Remember: this doesn't mean condoning harm. It means recognizing their humanity and wishing for their well-being (which might reduce the suffering they cause).

*May you be safe and protected*
*May you be peaceful and happy*
*May you be healthy and strong*
*May you live with ease*

*[2-minute period]*""",
    "all_beings": """Finally, expand the field of metta outward — to all beings in all directions.

*May all beings be safe and protected*
*May all beings be peaceful and happy*
*May all beings be healthy and strong*
*May all beings live with ease*

Let the phrases ripple outward: loved ones, strangers, those in conflict, animals, all forms of life. Boundless goodwill.

From the Karaniya Metta Sutta:

> *Even as a mother protects with her life*
> *Her child, her only child,*
> *So with a boundless heart*
> *Should one cherish all living beings.*

*[3-minute period]*""",
}


def get_breathing_instruction(stage: str, practice_level: str = "beginner") -> str:
    """Get breathing meditation instruction for a given stage.

    Args:
        stage: One of: welcome, settle, focus, main_period, checkin
        practice_level: beginner, intermediate, or advanced

    Returns:
        Instruction text
    """
    if stage not in BREATHING_TEMPLATES:
        return f"[No template for stage: {stage}]"

    stage_templates = BREATHING_TEMPLATES[stage]

    # If stage doesn't vary by level, return the common template
    if isinstance(stage_templates, str):
        return stage_templates

    # Return level-specific template, fallback to beginner
    return stage_templates.get(practice_level, stage_templates["beginner"])


def get_metta_instruction(phase: str) -> str:
    """Get metta meditation instruction for a given phase.

    Args:
        phase: One of: welcome, self, loved_one, neutral, difficult, all_beings

    Returns:
        Instruction text
    """
    return METTA_TEMPLATES.get(phase, f"[No template for phase: {phase}]")
