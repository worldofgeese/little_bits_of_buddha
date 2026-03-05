"""SeekerActor — Dapr Virtual Actor for LBOB seekers (one per Telegram user)."""

from datetime import datetime

import httpx
from dapr.actor import Actor, ActorInterface, actormethod

from .level_detector import detect_practice_level


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
