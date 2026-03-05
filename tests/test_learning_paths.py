"""Tests for learning paths curriculum tracking."""

import pytest

from src.seeker_actor_service.learning_paths import (
    CURRICULUM,
    NOT_STARTED,
    INTRODUCED,
    EXPLORED,
    PRACTICED,
    detect_topics,
    update_progress,
    suggest_next,
    format_path_progress,
)


class TestCurriculum:
    """Test curriculum structure."""

    def test_curriculum_has_four_sections(self):
        """Curriculum should have 4 main sections."""
        assert len(CURRICULUM) == 4
        assert "1" in CURRICULUM
        assert "2" in CURRICULUM
        assert "3" in CURRICULUM
        assert "4" in CURRICULUM

    def test_curriculum_has_19_topics(self):
        """Curriculum should have exactly 19 topics across all sections (4+8+4+3)."""
        total_topics = sum(len(section["topics"]) for section in CURRICULUM.values())
        assert total_topics == 19

    def test_section_1_four_noble_truths(self):
        """Section 1 should be The Four Noble Truths with 4 topics."""
        section = CURRICULUM["1"]
        assert section["title"] == "The Four Noble Truths"
        assert len(section["topics"]) == 4
        assert "1.1" in section["topics"]
        assert "1.4" in section["topics"]

    def test_section_2_eightfold_path(self):
        """Section 2 should be The Noble Eightfold Path with 8 topics."""
        section = CURRICULUM["2"]
        assert section["title"] == "The Noble Eightfold Path"
        assert len(section["topics"]) == 8

    def test_section_3_meditation_practices(self):
        """Section 3 should be Meditation Practices with 4 topics."""
        section = CURRICULUM["3"]
        assert section["title"] == "Meditation Practices"
        assert len(section["topics"]) == 4

    def test_section_4_key_doctrines(self):
        """Section 4 should be Key Doctrines with 3 topics."""
        section = CURRICULUM["4"]
        assert section["title"] == "Key Doctrines"
        assert len(section["topics"]) == 3


class TestDetectTopics:
    """Test topic detection from text."""

    def test_detect_single_topic_dukkha(self):
        """Should detect topic 1.1 from dukkha-related text."""
        topics = detect_topics("What is dukkha?")
        assert "1.1" in topics

    def test_detect_single_topic_suffering(self):
        """Should detect topic 1.1 from suffering keyword."""
        topics = detect_topics("Tell me about suffering")
        assert "1.1" in topics

    def test_detect_multiple_topics(self):
        """Should detect multiple topics from text."""
        topics = detect_topics("Tell me about metta and right speech")
        assert "2.3" in topics  # Right Speech
        assert "3.2" in topics  # Metta

    def test_detect_topics_from_themes(self):
        """Should detect topics from detected_themes list."""
        topics = detect_topics("Question about practice", detected_themes=["suffering", "craving"])
        assert "1.1" in topics  # Dukkha
        assert "1.2" in topics  # Samudaya (craving)

    def test_detect_topics_case_insensitive(self):
        """Topic detection should be case-insensitive."""
        topics = detect_topics("What is DUKKHA and METTA?")
        assert "1.1" in topics
        assert "3.2" in topics

    def test_detect_topics_pali_terms(self):
        """Should detect Pali terms in topics."""
        topics = detect_topics("I practice anapanasati daily")
        assert "3.1" in topics  # Breathing meditation

    def test_detect_topics_returns_unique_list(self):
        """Should return unique topic IDs even if multiple keywords match."""
        topics = detect_topics("suffering dukkha unsatisfactoriness")
        # All three keywords match 1.1
        assert topics.count("1.1") == 1

    def test_detect_no_topics(self):
        """Should return empty list when no topics detected."""
        topics = detect_topics("Hello, how are you?")
        assert topics == []


class TestUpdateProgress:
    """Test progress tracking updates."""

    def test_new_topic_becomes_introduced(self):
        """A newly detected topic should move to introduced status."""
        progress = {}
        topics = ["1.1"]

        updated = update_progress(progress, topics)

        assert "1.1" in updated
        assert updated["1.1"]["status"] == INTRODUCED
        assert updated["1.1"]["touch_count"] == 1

    def test_touch_count_increments(self):
        """Touch count should increment when topic detected again."""
        progress = {"1.1": {"status": INTRODUCED, "touch_count": 1}}
        topics = ["1.1"]

        updated = update_progress(progress, topics)

        assert updated["1.1"]["touch_count"] == 2

    def test_introduced_becomes_explored_after_3_touches(self):
        """Topic should move to explored status after 3 touches."""
        progress = {"1.1": {"status": INTRODUCED, "touch_count": 2}}
        topics = ["1.1"]

        updated = update_progress(progress, topics)

        assert updated["1.1"]["status"] == EXPLORED
        assert updated["1.1"]["touch_count"] == 3

    def test_meditation_topic_becomes_practiced_with_sits(self):
        """Meditation topics (section 3) should become practiced when sits logged."""
        progress = {"3.1": {"status": EXPLORED, "touch_count": 5}}
        topics = []
        practice_journal = [
            {"practice_type": "breathing", "duration_minutes": 20},
            {"practice_type": "breathing", "duration_minutes": 15},
        ]

        updated = update_progress(progress, topics, practice_journal)

        assert updated["3.1"]["status"] == PRACTICED

    def test_meditation_topic_practice_type_mapping(self):
        """Different practice types should map to correct meditation topics."""
        progress = {
            "3.1": {"status": INTRODUCED, "touch_count": 1},
            "3.2": {"status": INTRODUCED, "touch_count": 1},
            "3.3": {"status": EXPLORED, "touch_count": 3},
            "3.4": {"status": EXPLORED, "touch_count": 3},
        }
        practice_journal = [
            {"practice_type": "breathing", "duration_minutes": 20},
            {"practice_type": "metta", "duration_minutes": 15},
            {"practice_type": "body_scan", "duration_minutes": 10},
            {"practice_type": "walking", "duration_minutes": 25},
        ]

        updated = update_progress(progress, [], practice_journal)

        assert updated["3.1"]["status"] == PRACTICED  # breathing
        assert updated["3.2"]["status"] == PRACTICED  # metta
        assert updated["3.3"]["status"] == PRACTICED  # body_scan
        assert updated["3.4"]["status"] == PRACTICED  # walking

    def test_non_meditation_topic_cannot_be_practiced(self):
        """Non-meditation topics should not reach practiced status."""
        progress = {"1.1": {"status": EXPLORED, "touch_count": 5}}
        practice_journal = [{"practice_type": "breathing", "duration_minutes": 20}]

        updated = update_progress(progress, [], practice_journal)

        # 1.1 is not a meditation topic, should stay explored
        assert updated["1.1"]["status"] == EXPLORED

    def test_progress_never_decreases(self):
        """Status should never go backward."""
        progress = {"1.1": {"status": EXPLORED, "touch_count": 5}}
        topics = ["1.1"]

        # Even though we're updating, explored should stay explored
        updated = update_progress(progress, topics)

        assert updated["1.1"]["status"] == EXPLORED

    def test_practiced_status_never_decreases(self):
        """Practiced status should remain practiced."""
        progress = {"3.1": {"status": PRACTICED, "touch_count": 10}}
        topics = ["3.1"]

        updated = update_progress(progress, topics)

        assert updated["3.1"]["status"] == PRACTICED

    def test_update_progress_does_not_mutate_input(self):
        """update_progress should not mutate the input progress dict."""
        progress = {"1.1": {"status": INTRODUCED, "touch_count": 1}}
        topics = ["1.1"]

        updated = update_progress(progress, topics)

        # Original should not be changed
        assert progress["1.1"]["touch_count"] == 1
        # Updated should have incremented
        assert updated["1.1"]["touch_count"] == 2


class TestSuggestNext:
    """Test next topic suggestions."""

    def test_suggest_first_topic_when_empty(self):
        """Should suggest 1.1 when no progress exists."""
        progress = {}

        suggestion = suggest_next(progress, "newcomer")

        assert suggestion is not None
        assert suggestion["id"] == "1.1"
        assert "Dukkha" in suggestion["title"]
        assert suggestion["section"] == "The Four Noble Truths"

    def test_suggest_next_sequential_topic(self):
        """Should suggest next sequential topic in same section."""
        progress = {
            "1.1": {"status": INTRODUCED, "touch_count": 1},
        }

        suggestion = suggest_next(progress, "newcomer")

        assert suggestion["id"] == "1.2"
        assert "Samudaya" in suggestion["title"]

    def test_suggest_next_section_after_completing_section(self):
        """Should suggest first topic of next section after completing previous."""
        progress = {
            "1.1": {"status": EXPLORED, "touch_count": 3},
            "1.2": {"status": EXPLORED, "touch_count": 3},
            "1.3": {"status": EXPLORED, "touch_count": 3},
            "1.4": {"status": INTRODUCED, "touch_count": 1},
        }

        suggestion = suggest_next(progress, "beginner")

        # 2.1 should be next (first topic of section 2)
        assert suggestion["id"] == "2.1"
        assert "Right View" in suggestion["title"]

    def test_suggest_none_when_all_introduced(self):
        """Should return None when all topics at least introduced."""
        progress = {
            f"{section}.{topic}": {"status": INTRODUCED, "touch_count": 1}
            for section in ["1", "2", "3", "4"]
            for topic in ["1", "2", "3", "4"][:len(CURRICULUM[section]["topics"])]
        }
        # Need to build proper topic IDs
        progress = {}
        for section_id, section in CURRICULUM.items():
            for topic_id in section["topics"].keys():
                progress[topic_id] = {"status": INTRODUCED, "touch_count": 1}

        suggestion = suggest_next(progress, "experienced")

        assert suggestion is None


class TestFormatPathProgress:
    """Test progress formatting."""

    def test_format_empty_progress(self):
        """Should format empty progress with all topics not started."""
        progress = {}

        formatted = format_path_progress(progress)

        assert "📚" in formatted
        assert "The Four Noble Truths" in formatted
        assert "⚪" in formatted  # Not started icon
        assert "Legend" in formatted or "⚪ Not started" in formatted

    def test_format_with_various_statuses(self):
        """Should show correct icons for different statuses."""
        progress = {
            "1.1": {"status": INTRODUCED, "touch_count": 1},
            "1.2": {"status": EXPLORED, "touch_count": 3},
            "3.1": {"status": PRACTICED, "touch_count": 5},
        }

        formatted = format_path_progress(progress)

        assert "🔵" in formatted  # Introduced
        assert "🟢" in formatted  # Explored
        assert "⭐" in formatted  # Practiced
        assert "⚪" in formatted  # Not started

    def test_format_includes_all_sections(self):
        """Should include all 4 sections in output."""
        progress = {}

        formatted = format_path_progress(progress)

        assert "The Four Noble Truths" in formatted
        assert "The Noble Eightfold Path" in formatted
        assert "Meditation Practices" in formatted
        assert "Key Doctrines" in formatted

    def test_format_includes_legend(self):
        """Should include a legend explaining the icons."""
        progress = {}

        formatted = format_path_progress(progress)

        assert "⚪" in formatted and "Not started" in formatted
        assert "🔵" in formatted and "Introduced" in formatted
        assert "🟢" in formatted and "Explored" in formatted
        assert "⭐" in formatted and "Practiced" in formatted
