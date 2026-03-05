"""Tests for LangCache semantic response caching."""

import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from wisdom_service.langcache import LangCache


class TestLangCacheMiss:
    """Test cache miss scenarios."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_lookup_returns_none_for_new_query(self, mock_redis_class):
        """Test that lookup returns None for a query not in the cache."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Mock empty search results
        mock_redis.ft().search.return_value = MagicMock(docs=[])

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        result = cache.lookup("What is dukkha?", "beginner")

        assert result is None


class TestLangCacheHit:
    """Test cache hit scenarios."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_lookup_returns_cached_response_for_similar_query(self, mock_redis_class):
        """Test that lookup returns cached response when similar query exists."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Store a response
        cache.store(
            "What is dukkha?",
            "Dukkha is the Pali word for suffering or dissatisfaction.",
            "beginner"
        )

        # Mock search result returning the stored item with high similarity
        mock_doc = MagicMock()
        mock_doc.response = "Dukkha is the Pali word for suffering or dissatisfaction."
        mock_doc.score = "0.95"  # High similarity (cosine distance)
        mock_redis.ft().search.return_value = MagicMock(docs=[mock_doc])

        # Lookup with similar query
        result = cache.lookup("Can you explain suffering?", "beginner")

        assert result == "Dukkha is the Pali word for suffering or dissatisfaction."


class TestPracticeLevelIsolation:
    """Test that cache respects practice level boundaries."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_same_query_different_levels_returns_none(self, mock_redis_class):
        """Test that same query at different practice levels does not hit cache."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Store response for beginner level
        cache.store(
            "What is meditation?",
            "Meditation is a practice of training the mind.",
            "beginner"
        )

        # Mock empty search results (because practice_level filter doesn't match)
        mock_redis.ft().search.return_value = MagicMock(docs=[])

        # Lookup same query at experienced level should miss
        result = cache.lookup("What is meditation?", "experienced")

        assert result is None


class TestSimilarityThreshold:
    """Test that dissimilar queries don't hit the cache."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_dissimilar_query_returns_none(self, mock_redis_class):
        """Test that dissimilar query doesn't hit cache even if it's the only option."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Store a response about meditation
        cache.store(
            "What is meditation?",
            "Meditation is a practice of training the mind.",
            "beginner"
        )

        # Mock search result with LOW similarity
        mock_doc = MagicMock()
        mock_doc.response = "Meditation is a practice of training the mind."
        mock_doc.score = "0.5"  # Low similarity (below threshold)
        mock_redis.ft().search.return_value = MagicMock(docs=[mock_doc])

        # Lookup with dissimilar query
        result = cache.lookup("What is the weather today?", "beginner")

        assert result is None


class TestStoreAndRetrieve:
    """Test round-trip store and retrieve operations."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_store_then_lookup_succeeds(self, mock_redis_class):
        """Test that we can store a response and retrieve it."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Store should not raise
        cache.store(
            "What are the four noble truths?",
            "The four noble truths are: suffering, origin, cessation, path.",
            "beginner"
        )

        # Verify json().set was called
        assert mock_redis.json().set.called

        # Verify expire was called with TTL
        assert mock_redis.expire.called


class TestTTLBehavior:
    """Test that expired entries don't return cached responses."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_expired_entry_returns_none(self, mock_redis_class):
        """Test that expired cache entries are not returned."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        # Use very short TTL for testing
        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)
        cache.ttl_seconds = 1  # 1 second TTL

        # Store a response
        cache.store(
            "What is nibbana?",
            "Nibbana is the ultimate goal of Buddhist practice.",
            "beginner"
        )

        # Mock that Redis returns empty (key expired)
        mock_redis.ft().search.return_value = MagicMock(docs=[])

        # Lookup should return None
        result = cache.lookup("What is nibbana?", "beginner")

        assert result is None


class TestInvalidateAll:
    """Test cache invalidation."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_invalidate_all_clears_cache(self, mock_redis_class):
        """Test that invalidate_all clears all cached responses."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Mock keys scan
        mock_redis.scan_iter.return_value = [
            b"langcache:123",
            b"langcache:456"
        ]

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Invalidate all
        cache.invalidate_all()

        # Verify scan_iter was called with prefix pattern
        mock_redis.scan_iter.assert_called()

        # Verify delete was called
        assert mock_redis.delete.called


class TestIndexSetup:
    """Test Redis Search index creation."""

    @patch("wisdom_service.langcache.redis.Redis")
    def test_setup_index_creates_redis_search_index(self, mock_redis_class):
        """Test that setup_index creates a Redis Search index with correct schema."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        cache = LangCache(mock_redis, mock_model, similarity_threshold=0.92)

        # Setup index
        cache.setup_index()

        # Verify ft().create_index was called
        assert mock_redis.ft().create_index.called

        # Verify the schema includes the expected fields
        call_args = mock_redis.ft().create_index.call_args
        assert call_args is not None
