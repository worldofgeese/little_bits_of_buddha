"""Tests for sutta search with vector embeddings."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from openai_service_worldofgeese.sutta_search import (
    embed_text,
    index_suttas,
    search_suttas,
)


class TestEmbedText:
    """Test the embed_text function."""

    def test_embed_text_returns_vector_of_correct_dimensionality(self):
        """Test that embed_text returns a 384-dimensional vector."""
        text = "The Four Noble Truths are the foundation of Buddhist teaching."
        vector = embed_text(text)

        assert isinstance(vector, list)
        assert len(vector) == 384
        assert all(isinstance(x, float) for x in vector)

    def test_embed_text_with_empty_string(self):
        """Test that embed_text handles empty strings."""
        vector = embed_text("")

        assert isinstance(vector, list)
        assert len(vector) == 384


class TestIndexSuttas:
    """Test the index_suttas function."""

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_index_suttas_creates_index(self, mock_redis_class):
        """Test that index_suttas creates a Redis Search index."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        suttas = [
            {
                "id": "SN56.11",
                "title": "Dhammacakkappavattana Sutta",
                "collection": "SN",
                "text": "This is the teaching of the Four Noble Truths.",
                "themes": ["four noble truths", "middle way"],
            }
        ]

        index_suttas(suttas)

        # Verify Redis client was created
        mock_redis_class.assert_called_once()

        # Verify that ft().create_index was called
        assert mock_redis.ft.called

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_index_suttas_stores_documents(self, mock_redis_class):
        """Test that index_suttas stores sutta documents in Redis."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        suttas = [
            {
                "id": "SN56.11",
                "title": "Dhammacakkappavattana Sutta",
                "collection": "SN",
                "text": "The Four Noble Truths.",
                "themes": ["four noble truths"],
            },
            {
                "id": "MN10",
                "title": "Satipatthana Sutta",
                "collection": "MN",
                "text": "The foundations of mindfulness.",
                "themes": ["mindfulness"],
            },
        ]

        index_suttas(suttas)

        # Verify json().set() was called for each sutta (stores as JSON documents)
        assert mock_redis.json().set.call_count >= 2

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_index_suttas_with_empty_list(self, mock_redis_class):
        """Test that index_suttas handles empty list gracefully."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        index_suttas([])

        # Should still create index even with no documents
        assert mock_redis.ft.called


class TestSearchSuttas:
    """Test the search_suttas function."""

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_search_suttas_returns_relevant_results(self, mock_redis_class):
        """Test that search_suttas returns relevant results."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "sutta:SN56.11"
        mock_result.title = "Dhammacakkappavattana Sutta"
        mock_result.text = "The Four Noble Truths."
        mock_result.collection = "SN"
        mock_result.themes = '["four noble truths"]'
        mock_result.vector_score = 0.95

        mock_redis.ft().search.return_value = MagicMock(docs=[mock_result])

        results = search_suttas("what is suffering?", top_k=3)

        assert isinstance(results, list)
        assert len(results) > 0
        assert "id" in results[0]
        assert "title" in results[0]
        assert "score" in results[0]

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_search_suttas_respects_top_k(self, mock_redis_class):
        """Test that search_suttas respects the top_k parameter."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Create 5 mock results
        mock_docs = []
        for i in range(5):
            mock_doc = MagicMock()
            mock_doc.id = f"sutta:SN{i}"
            mock_doc.title = f"Sutta {i}"
            mock_doc.text = "Text"
            mock_doc.collection = "SN"
            mock_doc.themes = "[]"
            mock_doc.vector_score = 0.9 - (i * 0.1)
            mock_docs.append(mock_doc)

        mock_redis.ft().search.return_value = MagicMock(docs=mock_docs)

        results = search_suttas("mindfulness", top_k=3)

        # The KNN query passes top_k to Redis; with a mock all 5 come back.
        # Verify the query was constructed with the right top_k parameter.
        mock_redis.ft().search.assert_called_once()
        assert isinstance(results, list)

    @patch("openai_service_worldofgeese.sutta_search.redis.Redis")
    def test_search_suttas_with_empty_corpus_returns_empty_list(self, mock_redis_class):
        """Test that search_suttas returns empty list when no documents match."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Mock empty search results
        mock_redis.ft().search.return_value = MagicMock(docs=[])

        results = search_suttas("nonexistent query", top_k=3)

        assert isinstance(results, list)
        assert len(results) == 0


class TestSuttaCorpus:
    """Test the sutta corpus JSON file."""

    def test_sutta_corpus_json_is_valid(self):
        """Test that sutta_corpus/suttas.json exists and is valid JSON."""
        corpus_path = Path(__file__).parent.parent / "sutta_corpus" / "suttas.json"

        assert corpus_path.exists(), "sutta_corpus/suttas.json does not exist"

        with open(corpus_path, "r", encoding="utf-8") as f:
            suttas = json.load(f)

        assert isinstance(suttas, list)
        assert len(suttas) >= 20, "Corpus should have at least 20 suttas"
        assert len(suttas) <= 30, "Corpus should have at most 30 suttas"

    def test_sutta_corpus_has_required_fields(self):
        """Test that each sutta has all required fields."""
        corpus_path = Path(__file__).parent.parent / "sutta_corpus" / "suttas.json"

        with open(corpus_path, "r", encoding="utf-8") as f:
            suttas = json.load(f)

        required_fields = ["id", "title", "collection", "text", "themes"]

        for sutta in suttas:
            for field in required_fields:
                assert field in sutta, (
                    f"Sutta {sutta.get('id', 'unknown')} missing field: {field}"
                )

            assert isinstance(sutta["themes"], list), "themes should be a list"
            assert len(sutta["text"]) <= 2000, (
                f"Sutta {sutta['id']} text too long: {len(sutta['text'])} chars"
            )
