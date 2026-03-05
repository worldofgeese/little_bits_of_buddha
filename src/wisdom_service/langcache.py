"""Semantic response cache using Redis vector similarity.

This module provides a cache for LLM responses that uses semantic similarity
to return cached responses for questions that are similar in meaning, even if
the exact wording differs.

Example:
    "What is dukkha?" and "Can you explain suffering?" would hit the same cache entry.

Uses the same all-MiniLM-L6-v2 embedding model as sutta_search for consistency.
"""

import logging
import os
import uuid
from typing import Any

import numpy as np
import redis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimensionality


class LangCache:
    """Semantic response cache using Redis vector similarity."""

    def __init__(
        self,
        redis_client: redis.Redis,
        embedding_model: SentenceTransformer,
        similarity_threshold: float = 0.92,
    ):
        """Initialize the LangCache.

        Args:
            redis_client: Redis client instance
            embedding_model: Sentence transformer model (all-MiniLM-L6-v2)
            similarity_threshold: Minimum similarity score for cache hit (default: 0.92)
        """
        self.redis = redis_client
        self.model = embedding_model
        self.threshold = similarity_threshold
        self.index_name = "langcache_idx"
        self.prefix = "langcache:"
        self.ttl_seconds = 7 * 24 * 3600  # 7 days

    def setup_index(self):
        """Create Redis Search index for cached responses.

        Creates an index with 384-dimensional vectors for semantic search.
        Fields: query_embedding (VECTOR), response (TEXT), practice_level (TAG),
        timestamp (NUMERIC).
        """
        # Define schema
        schema = [
            VectorField(
                "$.query_embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": EMBEDDING_DIM,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="query_embedding",
            ),
            TextField("$.response", as_name="response"),
            TagField("$.practice_level", as_name="practice_level"),
            NumericField("$.timestamp", as_name="timestamp"),
        ]

        # Try to drop existing index
        try:
            self.redis.ft(self.index_name).dropindex(delete_documents=True)
        except redis.exceptions.ResponseError:
            pass  # Index doesn't exist, that's fine

        # Create index
        try:
            self.redis.ft(self.index_name).create_index(
                fields=schema,
                definition=IndexDefinition(
                    prefix=[self.prefix], index_type=IndexType.JSON
                ),
            )
            logger.info(f"Created LangCache index: {self.index_name}")
        except redis.exceptions.ResponseError as e:
            if "Index already exists" not in str(e):
                raise
            logger.debug(f"LangCache index already exists: {self.index_name}")

    def lookup(self, query: str, practice_level: str) -> str | None:
        """Find cached response for semantically similar query at same practice level.

        Args:
            query: User's query text
            practice_level: Practice level (e.g., "beginner", "experienced")

        Returns:
            Cached response text if similar query found above threshold, None otherwise
        """
        # Generate query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        # Build KNN search query with practice_level filter
        # Note: Redis returns cosine distance (lower is more similar)
        # We search for the closest match and then check if it's above our threshold
        q = (
            Query(
                f"(@practice_level:{{{practice_level}}})=>[KNN 1 @query_embedding $query_vec AS score]"
            )
            .sort_by("score")
            .return_fields("response", "score")
            .dialect(2)
        )

        try:
            results = self.redis.ft(self.index_name).search(
                q, query_params={"query_vec": query_vector}
            )
        except redis.exceptions.ResponseError as e:
            logger.warning(f"LangCache search failed: {e}")
            return None

        # Check if we got a result and if it's above threshold
        if not results.docs:
            logger.debug(f"LangCache miss: no results for query at {practice_level}")
            return None

        doc = results.docs[0]
        score = float(getattr(doc, "score", 1.0))

        # Convert cosine distance to similarity (1 - distance)
        # Redis COSINE metric returns distance in [0, 2], where 0 is identical
        similarity = 1.0 - (score / 2.0)

        logger.debug(
            f"LangCache search result: score={score}, similarity={similarity}, threshold={self.threshold}"
        )

        if similarity >= self.threshold:
            response = getattr(doc, "response", None)
            logger.info(
                f"LangCache HIT: similarity={similarity:.3f} for {practice_level}"
            )
            return response
        else:
            logger.debug(
                f"LangCache miss: similarity {similarity:.3f} below threshold {self.threshold}"
            )
            return None

    def store(self, query: str, response: str, practice_level: str):
        """Cache a response for future similar queries.

        Args:
            query: User's query text
            response: LLM response to cache
            practice_level: Practice level (e.g., "beginner", "experienced")
        """
        # Generate query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)

        # Prepare document
        import time

        doc_id = str(uuid.uuid4())
        doc = {
            "query_embedding": query_embedding.astype(np.float32).tolist(),
            "response": response,
            "practice_level": practice_level,
            "timestamp": time.time(),
        }

        # Store in Redis as JSON with TTL
        key = f"{self.prefix}{doc_id}"
        try:
            self.redis.json().set(key, "$", doc)
            self.redis.expire(key, self.ttl_seconds)
            logger.info(f"LangCache stored response for {practice_level} (key={key})")
        except Exception as e:
            logger.error(f"Failed to store in LangCache: {e}")

    def invalidate_all(self):
        """Clear all cached responses.

        Use this when system prompts change or when you need to reset the cache.
        """
        try:
            # Find all keys with our prefix
            keys = list(self.redis.scan_iter(match=f"{self.prefix}*"))

            if keys:
                self.redis.delete(*keys)
                logger.info(f"LangCache invalidated {len(keys)} entries")
            else:
                logger.info("LangCache invalidation: no entries to clear")
        except Exception as e:
            logger.error(f"Failed to invalidate LangCache: {e}")
