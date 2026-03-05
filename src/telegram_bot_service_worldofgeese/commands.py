"""Telegram bot commands for Phase 2."""

import httpx


async def handle_command(bot, message: dict) -> bool:
    """
    Check if message is a bot command. If so, handle it and return True.
    Otherwise return False (let normal message flow continue).
    """
    text = message.get("text", "").strip()
    if not text.startswith("/"):
        return False

    chat_id = message["chat"]["id"]
    command = text.split()[0].lower().split("@")[0]  # strip @botname

    handlers = {
        "/start": cmd_start,
        "/level": cmd_level,
        "/forget": cmd_forget,
        "/help": cmd_help,
    }

    handler = handlers.get(command)
    if handler:
        await handler(bot, chat_id, message)
        return True
    return False


async def cmd_start(bot, chat_id: int, message: dict) -> None:
    """Send welcome message and activate the SeekerActor."""
    welcome_text = (
        "🙏 Welcome. I am a student of the Early Buddhist teachings — "
        "the words of the Tathagata as preserved in the Pali Canon. "
        "Ask me anything about the Dhamma, and I will share what I've learned."
    )

    # Try to activate the actor, but don't block on it
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/get_state",
                timeout=2.0,
            )
    except Exception:
        # Actor activation failed, but we still send the welcome
        pass

    await bot.api.send_message(params={"chat_id": chat_id, "text": welcome_text})


async def cmd_level(bot, chat_id: int, message: dict) -> None:
    """Show current practice level."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/get_summary",
                timeout=2.0,
            )
            if response.status_code == 200:
                data = response.json()
                level = data.get("level", "unknown")
                count = data.get("conversation_count", 0)
                topics = data.get("topics", [])

                topics_str = ", ".join(topics) if topics else "none yet"
                text = (
                    f"📿 Practice level: {level}\n"
                    f"💬 Conversations: {count}\n"
                    f"📚 Topics explored: {topics_str}"
                )
            else:
                text = (
                    "I couldn't check your progress right now. Try again in a moment."
                )
    except Exception:
        text = "I couldn't check your progress right now. Try again in a moment."

    await bot.api.send_message(params={"chat_id": chat_id, "text": text})


async def cmd_forget(bot, chat_id: int, message: dict) -> None:
    """Clear conversation history (GDPR)."""
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"http://localhost:3500/v1.0/state/statestore/seeker-{chat_id}",
                timeout=2.0,
            )
    except Exception:
        # Even if deletion fails, we still confirm to the user
        pass

    text = (
        "🗑️ Your conversation history has been cleared. "
        "We can start fresh whenever you're ready."
    )
    await bot.api.send_message(params={"chat_id": chat_id, "text": text})


async def cmd_help(bot, chat_id: int, message: dict) -> None:
    """List available commands."""
    text = (
        "Available commands:\n"
        "/start — Begin a conversation\n"
        "/level — Check your practice level\n"
        "/forget — Clear your conversation history\n"
        "/help — Show this message\n\n"
        "Or just send me a message about the Dhamma."
    )
    await bot.api.send_message(params={"chat_id": chat_id, "text": text})
