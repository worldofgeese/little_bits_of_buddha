"""SeekerActor — Dapr Virtual Actor for LBOB seekers (one per Telegram user)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import httpx
from dapr.actor import Actor, ActorInterface, actormethod

from .level_detector import detect_practice_level


@dataclass
class SitEntry:
    """A single meditation session entry."""

    timestamp: str  # ISO 8601
    duration_minutes: int
    practice_type: str  # "breathing" | "metta" | "body_scan" | "walking" | "other"
    notes: str | None = None
    from_workflow: bool = False  # True if auto-logged after guided meditation


class SeekerActorInterface(ActorInterface):
    """Interface for SeekerActor methods."""

    @actormethod(name="receive_message")
    async def receive_message(self, text: str) -> dict:
        """Receive a message from the seeker and return a response."""
        ...

    @actormethod(name="get_state")
    async def get_state(self) -> dict:
        """Get the current seeker state."""
        ...

    @actormethod(name="update_practice_level")
    async def update_practice_level(self, level: str) -> None:
        """Manually update the practice level."""
        ...

    @actormethod(name="get_summary")
    async def get_summary(self) -> dict:
        """Get conversation summary statistics."""
        ...

    @actormethod(name="log_sit")
    async def log_sit(self, data: dict) -> dict:
        """Log a meditation session."""
        ...

    @actormethod(name="get_journal")
    async def get_journal(self, data: dict) -> dict:
        """Get journal entries from last N days."""
        ...

    @actormethod(name="get_weekly_summary")
    async def get_weekly_summary(self, data: dict) -> dict:
        """Get weekly summary statistics."""
        ...


class SeekerActor(Actor, SeekerActorInterface):
    """One actor per Telegram user (actor_id = chat_id)."""

    async def _on_activate(self) -> None:
        """Load or initialize seeker state from Dapr state store."""
        has_state, state = await self._state_manager.try_get_state("seeker_state")

        if not has_state:
            # Initialize default state
            default_state = {
                "chat_id": str(self.id.id),
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
                "practice_journal": [],  # List of SitEntry dicts, max 90 days
            }
            await self._state_manager.set_state("seeker_state", default_state)

    async def receive_message(self, text: str) -> dict:
        """
        Main entry point. Called by telegram-bot-service via pub/sub → actor invocation.
        1. Load state
        2. Update conversation history
        3. Detect practice level change (using level_detector)
        4. Call wisdom-service via Dapr service invocation
        5. Save state
        6. Return response
        """
        # Load current state
        state = await self._state_manager.get_state("seeker_state")

        # Add user message to history
        user_message = {
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat(),
        }
        state["history"].append(user_message)

        # Call wisdom service via Dapr service invocation
        try:
            wisdom_response = await self._call_wisdom_service(text, state)
            response_text = wisdom_response["response"]
            suttas_cited = wisdom_response.get("suttas_cited", [])
            detected_themes = wisdom_response.get("detected_themes", [])
        except Exception:
            # Graceful fallback when wisdom service is unreachable
            response_text = (
                "I'm having trouble reaching my library right now. "
                "Please try again in a moment."
            )
            suttas_cited = []
            detected_themes = []

        # Add bot response to history
        bot_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
        }
        state["history"].append(bot_message)

        # Cap history at 20 messages (10 exchanges)
        if len(state["history"]) > 20:
            state["history"] = state["history"][-20:]

        # Update conversation count
        state["conversation_count"] += 1

        # Detect practice level change
        new_level, updated_signals = detect_practice_level(
            current_level=state["practice_level"],
            message=text,
            conversation_count=state["conversation_count"],
            signal_history=state["signal_history"],
        )
        state["practice_level"] = new_level
        state["signal_history"] = updated_signals

        # Update topics explored (add new themes, maintain uniqueness)
        for theme in detected_themes:
            if theme not in state["topics_explored"]:
                state["topics_explored"].append(theme)

        # Update last_active timestamp
        state["last_active"] = datetime.now().isoformat()

        # Save updated state
        await self._state_manager.set_state("seeker_state", state)

        # Return response
        return {
            "response": response_text,
            "suttas_cited": suttas_cited,
            "detected_themes": detected_themes,
        }

    async def get_state(self) -> dict:
        """Return current seeker state as dict."""
        return await self._state_manager.get_state("seeker_state")

    async def update_practice_level(self, level: str) -> None:
        """Manual override of practice level."""
        state = await self._state_manager.get_state("seeker_state")
        state["practice_level"] = level
        await self._state_manager.set_state("seeker_state", state)

    async def get_summary(self) -> dict:
        """Return conversation stats."""
        state = await self._state_manager.get_state("seeker_state")
        return {
            "chat_id": state["chat_id"],
            "practice_level": state["practice_level"],
            "conversation_count": state["conversation_count"],
            "topics_count": len(state["topics_explored"]),
            "last_active": state["last_active"],
        }

    async def log_sit(self, data: dict) -> dict:
        """
        Log a meditation session.

        Args:
            data: dict with duration_minutes, practice_type, notes, from_workflow

        Returns:
            dict with status and total_sits
        """
        state = await self._state_manager.get_state("seeker_state")

        # Ensure practice_journal exists (for backward compatibility)
        if "practice_journal" not in state:
            state["practice_journal"] = []

        # Create new entry
        entry = SitEntry(
            timestamp=datetime.now().isoformat(),
            duration_minutes=data["duration_minutes"],
            practice_type=data["practice_type"],
            notes=data.get("notes"),
            from_workflow=data.get("from_workflow", False),
        )

        # Add to journal
        state["practice_journal"].append(asdict(entry))

        # Prune entries older than 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        state["practice_journal"] = [
            e for e in state["practice_journal"]
            if datetime.fromisoformat(e["timestamp"]) >= cutoff_date
        ]

        # Save state
        await self._state_manager.set_state("seeker_state", state)

        return {
            "status": "logged",
            "total_sits": len(state["practice_journal"]),
        }

    async def get_journal(self, data: dict) -> dict:
        """
        Get journal entries from last N days.

        Args:
            data: dict with optional 'days' parameter (default 7)

        Returns:
            dict with entries and total_duration_minutes
        """
        state = await self._state_manager.get_state("seeker_state")

        # Ensure practice_journal exists (for backward compatibility)
        if "practice_journal" not in state:
            state["practice_journal"] = []

        # Get days parameter (default 7)
        days = data.get("days", 7)

        # Filter entries within date range
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_entries = [
            e for e in state["practice_journal"]
            if datetime.fromisoformat(e["timestamp"]) >= cutoff_date
        ]

        # Calculate total duration
        total_duration = sum(e["duration_minutes"] for e in filtered_entries)

        return {
            "entries": filtered_entries,
            "total_duration_minutes": total_duration,
        }

    async def get_weekly_summary(self, data: dict) -> dict:
        """
        Get weekly summary statistics.

        Returns:
            dict with total_sits, total_minutes, most_practiced_type, longest_sit, streak
        """
        state = await self._state_manager.get_state("seeker_state")

        # Ensure practice_journal exists (for backward compatibility)
        if "practice_journal" not in state:
            state["practice_journal"] = []

        # Get last 7 days of entries
        cutoff_date = datetime.now() - timedelta(days=7)
        weekly_entries = [
            e for e in state["practice_journal"]
            if datetime.fromisoformat(e["timestamp"]) >= cutoff_date
        ]

        if not weekly_entries:
            return {
                "total_sits": 0,
                "total_minutes": 0,
                "most_practiced_type": None,
                "longest_sit": 0,
                "streak": 0,
            }

        # Calculate statistics
        total_sits = len(weekly_entries)
        total_minutes = sum(e["duration_minutes"] for e in weekly_entries)
        longest_sit = max(e["duration_minutes"] for e in weekly_entries)

        # Find most practiced type
        type_counts = {}
        for entry in weekly_entries:
            practice_type = entry["practice_type"]
            type_counts[practice_type] = type_counts.get(practice_type, 0) + 1
        most_practiced_type = max(type_counts, key=type_counts.get)

        # Calculate streak (consecutive days with at least one sit)
        # Get unique dates of sits
        sit_dates = set()
        for entry in weekly_entries:
            entry_date = datetime.fromisoformat(entry["timestamp"]).date()
            sit_dates.add(entry_date)

        # Count consecutive days from today backwards
        streak = 0
        current_date = datetime.now().date()
        while current_date in sit_dates:
            streak += 1
            current_date -= timedelta(days=1)

        return {
            "total_sits": total_sits,
            "total_minutes": total_minutes,
            "most_practiced_type": most_practiced_type,
            "longest_sit": longest_sit,
            "streak": streak,
        }

    async def _call_wisdom_service(self, message: str, state: dict) -> dict:
        """Call wisdom service via Dapr service invocation (httpx to Dapr sidecar)."""
        dapr_port = 3500  # Default Dapr sidecar HTTP port

        # Prepare context for wisdom service
        context = {
            "practice_level": state["practice_level"],
            "history": state["history"][-10:],  # Last 10 messages
            "topics_explored": state["topics_explored"],
        }

        payload = {
            "chat_id": state["chat_id"],
            "message": message,
            "context": context,
        }

        # Call via Dapr service invocation
        url = (
            f"http://localhost:{dapr_port}/v1.0/invoke/wisdom-service/method/wisdom/ask"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
