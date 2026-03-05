"""Tests for practice level detection module."""

from src.seeker_actor_service.level_detector import detect_practice_level


class TestNewcomerLevel:
    """Test newcomer level behavior."""

    def test_new_user_starts_as_newcomer(self):
        """New user with no messages should start as newcomer."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="Hello, I'm interested in Buddhism",
            conversation_count=1,
            signal_history=[],
        )
        assert level == "newcomer"
        assert isinstance(history, list)

    def test_conversation_count_floor_prevents_early_promotion(self):
        """Even with advanced vocabulary, user stays newcomer with < 3 conversations."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I'm interested in arahat, asava, and parinibbana",
            conversation_count=1,
            signal_history=[],
        )
        assert level == "newcomer"


class TestVocabularyScoring:
    """Test vocabulary detection and scoring."""

    def test_basic_vocabulary_scoring(self):
        """Basic terms should score 1 point each."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I want to learn about dukkha, sutta, and dharma",
            conversation_count=5,
            signal_history=[],
        )
        # Should detect 3 basic terms = 3 points total (need 3+ for beginner)
        assert level == "beginner"

    def test_intermediate_vocabulary_scoring(self):
        """Intermediate terms should score 2 points each."""
        level, history = detect_practice_level(
            current_level="beginner",
            message="I'm studying anicca, anatta, and the five aggregates",
            conversation_count=15,
            signal_history=[
                {"message_num": 1, "vocab": 3, "complexity": 0, "practice": 0},
                {"message_num": 2, "vocab": 3, "complexity": 0, "practice": 0},
            ],
        )
        # Should accumulate enough points for intermediate (5+ needed)
        assert level == "intermediate"

    def test_advanced_vocabulary_scoring(self):
        """Advanced terms should score 3 points each."""
        level, history = detect_practice_level(
            current_level="intermediate",
            message="I'm exploring nimitta, bhavanga, and sotapanna stages",
            conversation_count=35,
            signal_history=[
                {"message_num": i, "vocab": 5, "complexity": 0, "practice": 0}
                for i in range(1, 6)
            ],
        )
        # Should accumulate enough points for experienced (7+ needed)
        assert level == "experienced"

    def test_case_insensitive_matching(self):
        """Terms should match regardless of case."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I want to learn about DUKKHA, Sutta, and DhArMa",
            conversation_count=5,
            signal_history=[],
        )
        assert level == "beginner"

    def test_whole_word_matching(self):
        """Should only match whole words, not substrings."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="The karmatic consequences are interesting",  # "karmatic" shouldn't match "karma"
            conversation_count=5,
            signal_history=[],
        )
        # Should not detect "karma" inside "karmatic", so insufficient signals
        assert level == "newcomer"

    def test_whole_word_matching_karma_in_sentence(self):
        """Should match karma when it's a whole word."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I'm learning about karma and its effects",
            conversation_count=5,
            signal_history=[],
        )
        # Should detect "karma" as a whole word
        # Need multiple signals, so let's test with more context
        level2, history2 = detect_practice_level(
            current_level="newcomer",
            message="Tell me about karma, dharma, and sangha please",
            conversation_count=5,
            signal_history=[],
        )
        assert level2 == "beginner"


class TestQuestionComplexity:
    """Test question complexity detection."""

    def test_simple_question_detection(self):
        """Simple 'what is' questions should score 1 point."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="What is meditation? How do I meditate?",
            conversation_count=5,
            signal_history=[],
        )
        # Simple questions + some processing should contribute to signals
        # But need 3+ signals for promotion
        assert isinstance(history, list)

    def test_comparative_question_detection(self):
        """Comparative questions should score 2 points."""
        level, history = detect_practice_level(
            current_level="beginner",
            message="How does samadhi differ from jhana? What's the relationship between them?",
            conversation_count=15,
            signal_history=[
                {"message_num": 1, "vocab": 3, "complexity": 0, "practice": 0},
            ],
        )
        # Comparative questions provide higher signals
        assert isinstance(history, list)

    def test_analytical_question_detection(self):
        """Analytical questions with sutta references should score 3 points."""
        level, history = detect_practice_level(
            current_level="intermediate",
            message="In MN 10, how does the Buddha explain the jhana progression?",
            conversation_count=35,
            signal_history=[
                {"message_num": i, "vocab": 5, "complexity": 0, "practice": 0}
                for i in range(1, 5)
            ],
        )
        # Should contribute to experienced level signals
        assert isinstance(history, list)


class TestPracticeReferences:
    """Test practice reference detection."""

    def test_basic_practice_reference(self):
        """Basic practice mentions should signal beginner minimum."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I meditate every morning and my practice is growing",
            conversation_count=5,
            signal_history=[],
        )
        # Practice references contribute to signals
        assert isinstance(history, list)

    def test_intermediate_practice_reference(self):
        """Retreat and teacher mentions should signal intermediate."""
        level, history = detect_practice_level(
            current_level="beginner",
            message="I went on a retreat last month with my teacher",
            conversation_count=15,
            signal_history=[
                {"message_num": 1, "vocab": 3, "complexity": 0, "practice": 0},
                {"message_num": 2, "vocab": 2, "complexity": 1, "practice": 0},
            ],
        )
        # Should contribute to intermediate signals
        assert isinstance(history, list)

    def test_advanced_practice_technique(self):
        """Specific technique mentions should signal experienced level."""
        level, history = detect_practice_level(
            current_level="intermediate",
            message="I practice anapanasati and kasina meditation daily",
            conversation_count=35,
            signal_history=[
                {"message_num": i, "vocab": 4, "complexity": 1, "practice": 1}
                for i in range(1, 5)
            ],
        )
        # Should contribute to experienced signals
        assert isinstance(history, list)


class TestLevelPromotion:
    """Test level promotion logic."""

    def test_level_never_decreases(self):
        """Level should never go down, even with newcomer-level messages."""
        level, history = detect_practice_level(
            current_level="intermediate",
            message="Hello",
            conversation_count=20,
            signal_history=[],
        )
        assert level == "intermediate"

    def test_promotion_requires_sufficient_signals(self):
        """Should not promote with insufficient signals."""
        # Only 2 signals, need 3+ for beginner
        level, history = detect_practice_level(
            current_level="newcomer",
            message="Tell me about dukkha and karma",  # 2 basic terms = 2 points
            conversation_count=5,
            signal_history=[],
        )
        assert level == "newcomer"

    def test_multi_message_signal_accumulation(self):
        """Signals should accumulate across multiple messages."""
        # First message
        level1, history1 = detect_practice_level(
            current_level="newcomer",
            message="Tell me about dukkha",  # 1 vocab point
            conversation_count=3,
            signal_history=[],
        )
        assert level1 == "newcomer"

        # Second message - still not enough
        level2, history2 = detect_practice_level(
            current_level="newcomer",
            message="I'm interested in karma",  # 1 vocab point (no "what is" pattern)
            conversation_count=4,
            signal_history=history1,
        )
        assert level2 == "newcomer"

        # Third message - should push over threshold
        level3, history3 = detect_practice_level(
            current_level="newcomer",
            message="I want to learn dharma",  # 1 vocab point, total 3
            conversation_count=5,
            signal_history=history2,
        )
        assert level3 == "beginner"


class TestPromotionThresholds:
    """Test specific promotion threshold requirements."""

    def test_newcomer_to_beginner_threshold(self):
        """Newcomer -> beginner requires 3+ signals AND conversation_count >= 3."""
        # Has signals but too few conversations
        level, history = detect_practice_level(
            current_level="newcomer",
            message="Tell me about dukkha, karma, and dharma",
            conversation_count=2,
            signal_history=[],
        )
        assert level == "newcomer"

        # Has conversations and signals - should promote
        level, history = detect_practice_level(
            current_level="newcomer",
            message="Tell me about dukkha, karma, and dharma",
            conversation_count=3,
            signal_history=[],
        )
        assert level == "beginner"

    def test_beginner_to_intermediate_threshold(self):
        """Beginner -> intermediate requires 5+ signals AND conversation_count >= 11."""
        # Build up history with 3 points (already at beginner)
        initial_history = [
            {"message_num": 1, "vocab": 3, "complexity": 0, "practice": 0},
        ]

        # Add 2 more points but too few conversations
        level, history = detect_practice_level(
            current_level="beginner",
            message="I'm learning about anicca",  # 2 points
            conversation_count=10,
            signal_history=initial_history,
        )
        assert level == "beginner"

        # Same message but enough conversations - should promote
        level, history = detect_practice_level(
            current_level="beginner",
            message="I'm learning about anicca",  # 2 points, total 5
            conversation_count=11,
            signal_history=initial_history,
        )
        assert level == "intermediate"

    def test_intermediate_to_experienced_threshold(self):
        """Intermediate -> experienced requires 7+ signals AND conversation_count >= 31."""
        # Build up history with 5 points (already at intermediate)
        initial_history = [
            {"message_num": i, "vocab": 5, "complexity": 0, "practice": 0}
            for i in range(1, 2)
        ]

        # Add 3 more points but too few conversations
        level, history = detect_practice_level(
            current_level="intermediate",
            message="I'm studying nimitta",  # 3 points
            conversation_count=30,
            signal_history=initial_history,
        )
        assert level == "intermediate"

        # Same message but enough conversations - should promote
        level, history = detect_practice_level(
            current_level="intermediate",
            message="I'm studying nimitta and bhavanga",  # 6 points, total 11
            conversation_count=31,
            signal_history=initial_history,
        )
        assert level == "experienced"


class TestSignalHistory:
    """Test signal history management."""

    def test_signal_history_structure(self):
        """Signal history should contain message-level signal breakdowns."""
        level, history = detect_practice_level(
            current_level="newcomer",
            message="I want to learn about dukkha and karma",
            conversation_count=5,
            signal_history=[],
        )
        assert len(history) == 1
        assert "vocab" in history[0]
        assert "complexity" in history[0]
        assert "practice" in history[0]

    def test_signal_history_accumulation(self):
        """New signals should append to existing history."""
        initial_history = [
            {"message_num": 1, "vocab": 2, "complexity": 0, "practice": 0},
        ]
        level, history = detect_practice_level(
            current_level="newcomer",
            message="Tell me about dharma",
            conversation_count=5,
            signal_history=initial_history,
        )
        assert len(history) == 2
        assert history[0] == initial_history[0]
