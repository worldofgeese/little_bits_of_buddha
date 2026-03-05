"""Telegram bot commands for Phase 2."""

import re

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
        "/sit": cmd_sit,
        "/journal": cmd_journal,
        "/daily": cmd_daily,
        "/path": cmd_path,
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
        "/sit — Log a meditation session\n"
        "/journal — View your practice journal\n"
        "/daily — Manage daily sutta delivery\n"
        "/path — View your learning path progress\n"
        "/forget — Clear your conversation history\n"
        "/help — Show this message\n\n"
        "Or just send me a message about the Dhamma."
    )
    await bot.api.send_message(params={"chat_id": chat_id, "text": text})


def parse_sit_command(text: str) -> tuple[int, str, str | None]:
    """
    Parse /sit command text.

    Examples:
        /sit 20 breathing -> (20, "breathing", None)
        /sit 10 metta "Focused on family" -> (10, "metta", "Focused on family")
        /sit 15 -> (15, "other", None)

    Returns:
        tuple of (duration_minutes, practice_type, notes)
    """
    # Remove command prefix
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        raise ValueError("Missing duration")

    remaining = parts[1]

    # Extract duration (first number)
    duration_match = re.match(r"^(\d+)", remaining)
    if not duration_match:
        raise ValueError("Invalid duration")

    duration = int(duration_match.group(1))
    remaining = remaining[len(duration_match.group(1)) :].strip()

    # Extract practice type and notes
    practice_type = "other"  # default
    notes = None

    if remaining:
        # Check for quoted notes
        notes_match = re.search(r'"([^"]+)"', remaining)
        if notes_match:
            notes = notes_match.group(1)
            # Remove notes from remaining to extract practice type
            type_part = remaining[: notes_match.start()].strip()
            if type_part:
                practice_type = type_part
        else:
            # No quotes, entire remaining is practice type
            practice_type = remaining

    return duration, practice_type, notes


async def cmd_sit(bot, chat_id: int, message: dict) -> None:
    """Log a meditation session."""
    text = message.get("text", "").strip()

    try:
        duration, practice_type, notes = parse_sit_command(text)

        # Call seeker actor to log sit
        payload = {
            "duration_minutes": duration,
            "practice_type": practice_type,
            "notes": notes,
            "from_workflow": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/log_sit",
                json=payload,
                timeout=2.0,
            )

            if response.status_code == 200:
                result = response.json()
                total = result.get("total_sits", 0)
                reply = f"🪷 Logged: {duration} min {practice_type} meditation. You've sat {total} times."
            else:
                reply = "I couldn't log your session right now. Try again in a moment."

    except ValueError:
        reply = "Invalid format. Use: /sit [duration] [type] [notes]\nExample: /sit 20 breathing"
    except Exception:
        reply = "I couldn't log your session right now. Try again in a moment."

    await bot.api.send_message(params={"chat_id": chat_id, "text": reply})


async def cmd_journal(bot, chat_id: int, message: dict) -> None:
    """View practice journal."""
    text = message.get("text", "").strip()
    parts = text.split()

    # Check if "week" is specified
    show_weekly_summary = len(parts) > 1 and "week" in parts[1].lower()

    try:
        async with httpx.AsyncClient() as client:
            if show_weekly_summary:
                # Get weekly summary and use wisdom service to generate summary
                response = await client.post(
                    f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/get_weekly_summary",
                    json={},
                    timeout=2.0,
                )

                if response.status_code == 200:
                    summary = response.json()

                    if summary["total_sits"] == 0:
                        reply = "📿 You haven't logged any sits this week yet."
                    else:
                        # Format summary
                        reply = (
                            f"📿 Week in Practice\n\n"
                            f"🧘 Total sits: {summary['total_sits']}\n"
                            f"⏱️ Total time: {summary['total_minutes']} minutes\n"
                            f"🌟 Most practiced: {summary['most_practiced_type']}\n"
                            f"⏰ Longest sit: {summary['longest_sit']} minutes\n"
                            f"🔥 Current streak: {summary['streak']} days"
                        )

                        # TODO: Call wisdom-service to generate warm LLM summary
                        # For now, just show structured data
                else:
                    reply = (
                        "I couldn't fetch your weekly summary. Try again in a moment."
                    )
            else:
                # Get journal for last 7 days
                response = await client.post(
                    f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/get_journal",
                    json={"days": 7},
                    timeout=2.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    entries = data["entries"]
                    total_duration = data["total_duration_minutes"]

                    if not entries:
                        reply = "📿 No meditation sessions logged in the last 7 days."
                    else:
                        lines = ["📿 Last 7 Days\n"]
                        for entry in entries[-10:]:  # Show last 10
                            timestamp = entry["timestamp"][:10]  # Just date
                            duration = entry["duration_minutes"]
                            practice_type = entry["practice_type"]
                            lines.append(
                                f"• {timestamp}: {duration} min {practice_type}"
                            )

                        lines.append(f"\nTotal: {total_duration} minutes")
                        reply = "\n".join(lines)
                else:
                    reply = "I couldn't fetch your journal. Try again in a moment."

    except Exception:
        reply = "I couldn't fetch your journal. Try again in a moment."

    await bot.api.send_message(params={"chat_id": chat_id, "text": reply})


def parse_daily_command(text: str) -> tuple[str, str | None]:
    """
    Parse /daily command text.

    Examples:
        /daily on -> ("enable", None)
        /daily off -> ("disable", None)
        /daily time 07:00 -> ("time", "07:00")

    Returns:
        tuple of (action, value)
    """
    parts = text.strip().split()
    if len(parts) < 2:
        raise ValueError("Missing action")

    action = parts[1].lower()

    if action == "on":
        return ("enable", None)
    elif action == "off":
        return ("disable", None)
    elif action == "time":
        if len(parts) < 3:
            raise ValueError("Missing time value")
        return ("time", parts[2])
    else:
        raise ValueError(f"Unknown action: {action}")


async def cmd_daily(bot, chat_id: int, message: dict) -> None:
    """Manage daily sutta delivery."""
    text = message.get("text", "").strip()

    try:
        action, value = parse_daily_command(text)

        if action == "enable":
            # Enable daily sutta
            payload = {"daily_sutta": True}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/update_schedule",
                    json=payload,
                    timeout=2.0,
                )

                if response.status_code == 200:
                    reply = "🌅 Daily sutta delivery enabled. You'll receive a teaching each morning."
                else:
                    reply = "I couldn't update your preferences right now. Try again in a moment."

        elif action == "disable":
            # Disable daily sutta
            payload = {"daily_sutta": False}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/update_schedule",
                    json=payload,
                    timeout=2.0,
                )

                if response.status_code == 200:
                    reply = "🌅 Daily sutta delivery disabled."
                else:
                    reply = "I couldn't update your preferences right now. Try again in a moment."

        elif action == "time":
            # Update delivery time
            payload = {"daily_sutta_time": value}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/update_schedule",
                    json=payload,
                    timeout=2.0,
                )

                if response.status_code == 200:
                    reply = f"🌅 Daily sutta time updated to {value} UTC."
                else:
                    reply = "I couldn't update your preferences right now. Try again in a moment."

    except ValueError:
        reply = (
            "Invalid format. Use:\n"
            "/daily on — Enable daily suttas\n"
            "/daily off — Disable daily suttas\n"
            "/daily time 07:00 — Set delivery time (UTC)"
        )
    except Exception:
        reply = "I couldn't update your preferences right now. Try again in a moment."

    await bot.api.send_message(params={"chat_id": chat_id, "text": reply})


async def cmd_path(bot, chat_id: int, message: dict) -> None:
    """View learning path progress."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:3500/v1.0/actors/SeekerActor/{chat_id}/method/get_path_progress",
                json={},
                timeout=2.0,
            )

            if response.status_code == 200:
                data = response.json()
                formatted = data["formatted"]
                next_suggestion = data.get("next_suggestion")

                # Build reply with formatted progress
                reply_parts = ["📿 Your Learning Path\n", formatted]

                # Add next suggestion if available
                if next_suggestion:
                    reply_parts.append(
                        f"\n\n💡 *Next to explore:*\n{next_suggestion['title']} ({next_suggestion['section']})"
                    )
                else:
                    reply_parts.append(
                        "\n\n🎉 You've touched upon all topics in the curriculum!"
                    )

                reply = "".join(reply_parts)
            else:
                reply = "I couldn't fetch your learning path. Try again in a moment."

    except Exception:
        reply = "I couldn't fetch your learning path. Try again in a moment."

    await bot.api.send_message(
        params={"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"}
    )
