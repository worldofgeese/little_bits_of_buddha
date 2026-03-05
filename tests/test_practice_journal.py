"""Tests for practice journal functionality (WP6)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from dapr.actor import ActorId

from src.seeker_actor_service.seeker_actor import SeekerActor


class TestLogSit:
    """Test log_sit actor method."""

    @pytest.mark.trio
    async def test_log_sit_adds_entry_to_journal(self):
        """log_sit should add entry to journal and return correct total."""
        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
                "practice_journal": [],
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        result = await actor.log_sit({
            "duration_minutes": 20,
            "practice_type": "breathing",
            "notes": "Focused session",
            "from_workflow": False,
        })

        assert result["status"] == "logged"
        assert result["total_sits"] == 1

        # Verify state was saved with journal entry
        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]
        assert len(final_state["practice_journal"]) == 1
        assert final_state["practice_journal"][0]["duration_minutes"] == 20
        assert final_state["practice_journal"][0]["practice_type"] == "breathing"

    @pytest.mark.trio
    async def test_log_sit_from_workflow_flag_stored(self):
        """log_sit should correctly store from_workflow flag."""
        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
                "practice_journal": [],
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        await actor.log_sit({
            "duration_minutes": 15,
            "practice_type": "metta",
            "from_workflow": True,
        })

        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]
        assert final_state["practice_journal"][0]["from_workflow"] is True

    @pytest.mark.trio
    async def test_90_day_pruning(self):
        """Entries older than 90 days should be removed on log_sit."""
        actor_id = ActorId("12345")

        # Create journal with old entries
        old_timestamp = (datetime.now() - timedelta(days=95)).isoformat()
        recent_timestamp = (datetime.now() - timedelta(days=10)).isoformat()

        existing_journal = [
            {
                "timestamp": old_timestamp,
                "duration_minutes": 10,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
            {
                "timestamp": recent_timestamp,
                "duration_minutes": 20,
                "practice_type": "metta",
                "notes": None,
                "from_workflow": False,
            },
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(
            return_value=(
                True,
                {
                    "chat_id": "12345",
                    "practice_level": "newcomer",
                    "conversation_count": 0,
                    "topics_explored": [],
                    "history": [],
                    "signal_history": [],
                    "last_active": datetime.now().isoformat(),
                    "preferences": {},
                    "practice_journal": existing_journal,
                },
            )
        )
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
                "practice_journal": existing_journal,
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        await actor.log_sit({
            "duration_minutes": 15,
            "practice_type": "walking",
        })

        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        # Old entry should be pruned, recent one + new one should remain
        assert len(final_state["practice_journal"]) == 2
        for entry in final_state["practice_journal"]:
            assert entry["timestamp"] != old_timestamp


class TestGetJournal:
    """Test get_journal actor method."""

    @pytest.mark.trio
    async def test_get_journal_returns_entries_within_date_range(self):
        """get_journal should return only entries from last N days."""
        actor_id = ActorId("12345")

        # Create journal with various timestamps
        now = datetime.now()
        entries = [
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "duration_minutes": 20,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
            {
                "timestamp": (now - timedelta(days=10)).isoformat(),
                "duration_minutes": 15,
                "practice_type": "metta",
                "notes": None,
                "from_workflow": False,
            },
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(
            return_value=(
                True,
                {
                    "chat_id": "12345",
                    "practice_level": "newcomer",
                    "conversation_count": 0,
                    "topics_explored": [],
                    "history": [],
                    "signal_history": [],
                    "last_active": now.isoformat(),
                    "preferences": {},
                    "practice_journal": entries,
                },
            )
        )
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": now.isoformat(),
                "preferences": {},
                "practice_journal": entries,
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        result = await actor.get_journal({"days": 7})

        # Only entry from 2 days ago should be returned
        assert len(result["entries"]) == 1
        assert result["entries"][0]["duration_minutes"] == 20
        assert result["total_duration_minutes"] == 20

    @pytest.mark.trio
    async def test_get_journal_empty_for_new_seeker(self):
        """get_journal on new seeker should return empty list."""
        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
                "practice_journal": [],
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        result = await actor.get_journal({"days": 7})

        assert result["entries"] == []
        assert result["total_duration_minutes"] == 0

    @pytest.mark.trio
    async def test_get_journal_default_7_days(self):
        """get_journal should default to 7 days if not specified."""
        actor_id = ActorId("12345")

        now = datetime.now()
        entries = [
            {
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "duration_minutes": 20,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": now.isoformat(),
                "preferences": {},
                "practice_journal": entries,
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        result = await actor.get_journal({})

        assert len(result["entries"]) == 1


class TestGetWeeklySummary:
    """Test get_weekly_summary actor method."""

    @pytest.mark.trio
    async def test_weekly_summary_calculations(self):
        """get_weekly_summary should correctly calculate all statistics."""
        actor_id = ActorId("12345")

        now = datetime.now()
        entries = [
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "duration_minutes": 30,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "duration_minutes": 20,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
            {
                "timestamp": (now - timedelta(days=3)).isoformat(),
                "duration_minutes": 15,
                "practice_type": "metta",
                "notes": None,
                "from_workflow": False,
            },
            {
                "timestamp": (now - timedelta(days=4)).isoformat(),
                "duration_minutes": 25,
                "practice_type": "breathing",
                "notes": None,
                "from_workflow": False,
            },
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": now.isoformat(),
                "preferences": {},
                "practice_journal": entries,
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        await actor._on_activate()
        result = await actor.get_weekly_summary({})

        assert result["total_sits"] == 4
        assert result["total_minutes"] == 90
        assert result["most_practiced_type"] == "breathing"
        assert result["longest_sit"] == 30
        assert result["streak"] >= 1


class TestSitCommandParsing:
    """Test /sit command parsing in Telegram bot."""

    @pytest.mark.trio
    async def test_parse_sit_command_basic(self):
        """Parse /sit 20 breathing -> duration=20, type=breathing."""
        from src.telegram_bot_service_worldofgeese.commands import parse_sit_command

        duration, practice_type, notes = parse_sit_command("/sit 20 breathing")

        assert duration == 20
        assert practice_type == "breathing"
        assert notes is None

    @pytest.mark.trio
    async def test_parse_sit_command_with_notes(self):
        """Parse /sit 10 metta "Focused on family" -> correct parsing."""
        from src.telegram_bot_service_worldofgeese.commands import parse_sit_command

        duration, practice_type, notes = parse_sit_command('/sit 10 metta "Focused on family"')

        assert duration == 10
        assert practice_type == "metta"
        assert notes == "Focused on family"

    @pytest.mark.trio
    async def test_parse_sit_command_default_type(self):
        """Parse /sit 15 -> type defaults to 'other'."""
        from src.telegram_bot_service_worldofgeese.commands import parse_sit_command

        duration, practice_type, notes = parse_sit_command("/sit 15")

        assert duration == 15
        assert practice_type == "other"
        assert notes is None
