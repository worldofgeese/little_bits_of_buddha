"""Tests for Meditation Workflow Service (WP1).

Test-Driven Development approach:
1. Write these failing tests first
2. Commit them
3. Implement until tests pass
4. Commit implementation

These tests verify:
- Breathing meditation workflow execution
- Metta meditation workflow execution
- Activity functions (send_instruction, close_meditation, get_seeker_state)
- Workflow state management
- External event handling for user responses
"""

import json
from unittest.mock import Mock, patch

import pytest

# Use pytest.importorskip to gracefully skip if dapr.ext.workflow is not available
dapr_workflow = pytest.importorskip(
    "dapr.ext.workflow", reason="dapr.ext.workflow not available"
)


class TestBreathingMeditationWorkflow:
    """Test the breathing meditation (ānāpānasati) workflow."""

    @pytest.mark.integration
    @patch("meditation_workflow_service.activities.DaprClient")
    def test_breathing_workflow_complete_path(self, mock_dapr_client_class):
        """Test complete breathing meditation from start to finish."""
        # Mock DaprClient for activities
        mock_dapr = Mock()
        mock_dapr_client_class.return_value.__enter__.return_value = mock_dapr
        mock_dapr.publish_event.return_value = None
        mock_dapr.invoke_method.return_value.text.return_value = json.dumps(
            {"practice_level": "beginner", "meditation_count": 3}
        )

        from meditation_workflow_service.workflows.breathing import breathing_meditation

        # Mock workflow context
        mock_ctx = Mock()
        mock_ctx.get_input.return_value = {"chat_id": 12345, "duration_minutes": 5}

        # Track activity calls
        activity_calls = []

        def mock_call_activity(activity_name, input_data):
            activity_calls.append((activity_name, input_data))
            if activity_name == "get_seeker_state":
                return {"practice_level": "beginner", "meditation_count": 3}
            return None

        mock_ctx.call_activity = mock_call_activity

        # Mock timers
        timer_calls = []

        def mock_create_timer(duration):
            timer_calls.append(duration)
            return Mock()

        mock_ctx.create_timer = mock_create_timer

        # Mock external event
        mock_ctx.wait_for_external_event.return_value = "I feel calm and focused"

        # Execute workflow (generator-based)
        workflow_gen = breathing_meditation(mock_ctx)
        try:
            while True:
                next(workflow_gen)
        except StopIteration:
            pass

        # Verify workflow executed all steps
        assert len(activity_calls) >= 4, "Should call multiple activities"
        assert any("send_instruction" in call[0] for call in activity_calls), (
            "Should send instructions"
        )
        assert any("close_meditation" in call[0] for call in activity_calls), (
            "Should close meditation"
        )
        assert any("get_seeker_state" in call[0] for call in activity_calls), (
            "Should get seeker state"
        )

        # Verify timers were created (settle + main)
        assert len(timer_calls) >= 2, "Should create at least 2 timers (settle + main)"

        # Verify external event wait was called
        mock_ctx.wait_for_external_event.assert_called()

    @pytest.mark.integration
    @patch("meditation_workflow_service.activities.DaprClient")
    def test_breathing_workflow_timeout_path(self, mock_dapr_client_class):
        """Test breathing meditation when user doesn't respond (timeout)."""
        # Mock DaprClient for activities
        mock_dapr = Mock()
        mock_dapr_client_class.return_value.__enter__.return_value = mock_dapr
        mock_dapr.publish_event.return_value = None
        mock_dapr.invoke_method.return_value.text.return_value = json.dumps(
            {"practice_level": "intermediate", "meditation_count": 15}
        )

        from meditation_workflow_service.workflows.breathing import breathing_meditation

        mock_ctx = Mock()
        mock_ctx.get_input.return_value = {"chat_id": 12345, "duration_minutes": 5}

        activity_calls = []

        def mock_call_activity(activity_name, input_data):
            activity_calls.append((activity_name, input_data))
            if activity_name == "get_seeker_state":
                return {"practice_level": "intermediate", "meditation_count": 15}
            return None

        mock_ctx.call_activity = mock_call_activity
        mock_ctx.create_timer = lambda dur: Mock()

        # Simulate timeout by returning timeout event
        mock_ctx.wait_for_external_event.side_effect = TimeoutError("Event timeout")

        # Execute workflow
        workflow_gen = breathing_meditation(mock_ctx)
        try:
            while True:
                next(workflow_gen)
        except StopIteration:
            pass

        # Should still close meditation gracefully
        assert any("close_meditation" in call[0] for call in activity_calls), (
            "Should close meditation even on timeout"
        )


class TestMettaMeditationWorkflow:
    """Test the loving-kindness (metta) meditation workflow."""

    @pytest.mark.integration
    @patch("meditation_workflow_service.activities.DaprClient")
    def test_metta_workflow_complete_path(self, mock_dapr_client_class):
        """Test complete metta meditation through all phases."""
        # Mock DaprClient for activities
        mock_dapr = Mock()
        mock_dapr_client_class.return_value.__enter__.return_value = mock_dapr
        mock_dapr.publish_event.return_value = None
        mock_dapr.invoke_method.return_value.text.return_value = json.dumps(
            {"practice_level": "beginner", "meditation_count": 1}
        )

        # Metta phases: self → loved one → neutral person → difficult person → all beings
        from meditation_workflow_service.workflows.metta import metta_meditation

        mock_ctx = Mock()
        mock_ctx.get_input.return_value = {"chat_id": 12345}

        activity_calls = []

        def mock_call_activity(activity_name, input_data):
            activity_calls.append((activity_name, input_data))
            if activity_name == "get_seeker_state":
                return {"practice_level": "beginner", "meditation_count": 1}
            return None

        mock_ctx.call_activity = mock_call_activity
        mock_ctx.create_timer = lambda dur: Mock()

        # Execute workflow
        workflow_gen = metta_meditation(mock_ctx)
        try:
            while True:
                next(workflow_gen)
        except StopIteration:
            pass

        # Verify all phases were sent
        instruction_calls = [
            call for call in activity_calls if "send_instruction" in call[0]
        ]
        assert len(instruction_calls) >= 5, (
            "Should send instructions for all 5 metta phases"
        )

        # Verify closing
        assert any("close_meditation" in call[0] for call in activity_calls), (
            "Should close meditation"
        )


class TestMeditationActivities:
    """Test meditation activity functions."""

    @pytest.mark.integration
    def test_send_instruction_publishes_to_telegram(self):
        """Test send_instruction activity publishes via Dapr pub/sub."""
        from meditation_workflow_service.activities import send_instruction

        mock_ctx = Mock()

        with patch("meditation_workflow_service.activities.DaprClient") as mock_dapr:
            mock_client = Mock()
            mock_dapr.return_value.__enter__.return_value = mock_client

            send_instruction(
                mock_ctx, {"chat_id": 12345, "text": "Focus on the breath..."}
            )

            # Verify Dapr publish was called
            mock_client.publish_event.assert_called_once()
            call_args = mock_client.publish_event.call_args
            assert call_args[1]["pubsub_name"] == "pubsub"
            assert call_args[1]["topic_name"] == "responses"

            # Verify message content
            data = json.loads(call_args[1]["data"])
            assert data["chat_id"] == 12345
            assert "breath" in data["text"].lower()

    @pytest.mark.integration
    def test_get_seeker_state_calls_actor(self):
        """Test get_seeker_state activity invokes seeker actor."""
        from meditation_workflow_service.activities import get_seeker_state

        mock_ctx = Mock()

        with patch("meditation_workflow_service.activities.DaprClient") as mock_dapr:
            mock_client = Mock()
            mock_client.invoke_method.return_value.text.return_value = json.dumps(
                {
                    "practice_level": "intermediate",
                    "meditation_count": 42,
                    "last_meditation": "2026-03-01",
                }
            )
            mock_dapr.return_value.__enter__.return_value = mock_client

            result = get_seeker_state(mock_ctx, {"chat_id": 12345})

            # Verify actor invocation
            mock_client.invoke_method.assert_called_once()
            call_args = mock_client.invoke_method.call_args
            assert call_args[1]["app_id"] == "seeker-actor-service"
            assert "12345" in call_args[1]["method_name"]
            assert call_args[1]["http_verb"] == "GET"

            # Verify state returned
            assert result["practice_level"] == "intermediate"
            assert result["meditation_count"] == 42

    @pytest.mark.integration
    def test_close_meditation_logs_sit_and_suggests_sutta(self):
        """Test close_meditation activity logs sit and gets sutta suggestion."""
        from meditation_workflow_service.activities import close_meditation

        mock_ctx = Mock()

        with patch("meditation_workflow_service.activities.DaprClient") as mock_dapr:
            mock_client = Mock()
            mock_client.invoke_method.return_value.text.return_value = json.dumps(
                {
                    "sutta": "Anapanasati Sutta (MN 118)",
                    "excerpt": "Mindful, they breathe in; mindful, they breathe out...",
                }
            )
            mock_dapr.return_value.__enter__.return_value = mock_client

            close_meditation(
                mock_ctx,
                {"chat_id": 12345, "type": "breathing", "duration_minutes": 10},
            )

            # Should call both seeker actor (log_sit) and wisdom service (sutta suggestion)
            assert mock_client.invoke_method.call_count >= 2
            assert mock_client.publish_event.call_count >= 2  # closing message + sutta


class TestMeditationTemplates:
    """Test meditation instruction templates (no dapr dependencies)."""

    def test_breathing_templates_exist_for_all_levels(self):
        """Test breathing meditation templates exist for all practice levels."""
        # Import templates directly - no dapr imports needed
        import importlib.util

        # Load templates module directly without importing workflow modules
        spec = importlib.util.spec_from_file_location(
            "templates",
            "/home/node/.openclaw/workspace/projects/little_bits_of_buddha/src/meditation_workflow_service/templates.py",
        )
        templates = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(templates)

        # Should have templates for different levels
        beginner = templates.get_breathing_instruction(
            "welcome", practice_level="beginner"
        )
        intermediate = templates.get_breathing_instruction(
            "welcome", practice_level="intermediate"
        )
        advanced = templates.get_breathing_instruction(
            "welcome", practice_level="advanced"
        )

        assert beginner is not None
        assert intermediate is not None
        assert advanced is not None

        # Beginner should be simpler/more detailed
        assert len(beginner) >= len(advanced) or "new" in beginner.lower()

    def test_metta_templates_exist_for_all_phases(self):
        """Test metta meditation templates exist for all phases."""
        # Import templates directly - no dapr imports needed
        import importlib.util

        # Load templates module directly without importing workflow modules
        spec = importlib.util.spec_from_file_location(
            "templates",
            "/home/node/.openclaw/workspace/projects/little_bits_of_buddha/src/meditation_workflow_service/templates.py",
        )
        templates = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(templates)

        phases = ["self", "loved_one", "neutral", "difficult", "all_beings"]

        for phase in phases:
            instruction = templates.get_metta_instruction(phase)
            assert instruction is not None
            assert len(instruction) > 0

            # Verify Pali phrases are included
            if phase == "self":
                assert (
                    "may i" in instruction.lower() or "happiness" in instruction.lower()
                )


class TestWorkflowAPIEndpoints:
    """Test FastAPI endpoints for meditation workflow service."""

    @pytest.mark.integration
    @patch("meditation_workflow_service.__main__.DaprWorkflowClient")
    def test_start_meditation_endpoint(self, mock_workflow_client_class):
        """Test POST /meditate/start endpoint."""
        from fastapi.testclient import TestClient

        from meditation_workflow_service.__main__ import app

        # Mock the workflow client
        mock_client = Mock()
        mock_client.schedule_new_workflow.return_value = None
        mock_workflow_client_class.return_value = mock_client

        client = TestClient(app)
        response = client.post(
            "/meditate/start",
            json={
                "chat_id": 12345,
                "type": "breathing_meditation",
                "duration_minutes": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "instance_id" in data
        assert data["status"] == "started"

        # Verify workflow was scheduled
        mock_client.schedule_new_workflow.assert_called_once()

    @pytest.mark.integration
    @patch("meditation_workflow_service.__main__.DaprWorkflowClient")
    def test_raise_event_endpoint(self, mock_workflow_client_class):
        """Test POST /meditate/event endpoint."""
        from fastapi.testclient import TestClient

        from meditation_workflow_service.__main__ import app

        # Mock the workflow client
        mock_client = Mock()
        mock_client.raise_workflow_event.return_value = None
        mock_workflow_client_class.return_value = mock_client

        client = TestClient(app)
        response = client.post(
            "/meditate/event",
            json={
                "instance_id": "meditation-12345-1234567890",
                "event_name": "user_response",
                "data": "I feel peaceful",
            },
        )

        assert response.status_code == 200

        # Verify event was raised
        mock_client.raise_workflow_event.assert_called_once()

    @pytest.mark.integration
    @patch("meditation_workflow_service.__main__.DaprWorkflowClient")
    def test_get_status_endpoint(self, mock_workflow_client_class):
        """Test GET /meditate/status/{instance_id} endpoint."""
        from fastapi.testclient import TestClient

        from meditation_workflow_service.__main__ import app

        # Mock the workflow client and state
        mock_client = Mock()
        mock_state = Mock()
        mock_state.runtime_status.name = "COMPLETED"
        mock_client.get_workflow_state.return_value = mock_state
        mock_workflow_client_class.return_value = mock_client

        client = TestClient(app)
        response = client.get("/meditate/status/meditation-12345-1234567890")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
