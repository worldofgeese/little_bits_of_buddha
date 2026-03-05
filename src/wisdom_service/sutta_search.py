"""
Sutta vector search using Redis and sentence-transformers.

This module provides semantic search over a curated corpus of Buddhist suttas
using vector embeddings and Redis Search.
"""

import json
import os
from typing import Any

import numpy as np
import redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import (
    IndexDefinition,
    IndexType,
)
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

# Global model instance (lazy-loaded)
_model = None

# Constants
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimensionality
INDEX_NAME = "sutta_idx"
DOC_PREFIX = "sutta:"


def get_embedding_model() -> SentenceTransformer:
    """Get or create the sentence transformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_redis_client() -> redis.Redis:
    """Get Redis client from environment or use default localhost."""
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    return redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=False,  # We need bytes for vector fields
        encoding="utf-8",
    )


def embed_text(text: str) -> list[float]:
    """
    Generate embedding vector for the given text.

    Args:
        text: Input text to embed

    Returns:
        List of floats representing the embedding vector (384-dimensional)
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def index_suttas(suttas: list[dict[str, Any]]) -> int:
    """
    Create Redis Search index and store all suttas with their embeddings.

    Args:
        suttas: List of sutta dictionaries with id, title, collection, text, themes

    Returns:
        Number of suttas indexed
    """
    client = get_redis_client()

    # Define schema
    schema = [
        TextField("$.id", as_name="id"),
        TextField("$.title", as_name="title"),
        TextField("$.collection", as_name="collection"),
        TextField("$.text", as_name="text"),
        TagField("$.themes", as_name="themes"),
        VectorField(
            "$.embedding",
            "FLAT",
            {
                "TYPE": "FLOAT32",
                "DIM": EMBEDDING_DIM,
                "DISTANCE_METRIC": "COSINE",
            },
            as_name="embedding",
        ),
    ]

    # Try to create index, drop if exists
    try:
        client.ft(INDEX_NAME).dropindex(delete_documents=True)
    except redis.exceptions.ResponseError:
        pass  # Index doesn't exist, that's fine

    # Create index
    try:
        client.ft(INDEX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.JSON),
        )
    except redis.exceptions.ResponseError as e:
        if "Index already exists" not in str(e):
            raise

    # Index all suttas
    model = get_embedding_model()
    indexed_count = 0

    for sutta in suttas:
        # Generate embedding
        embedding = model.encode(sutta["text"], convert_to_numpy=True)

        # Prepare document
        doc = {
            "id": sutta["id"],
            "title": sutta["title"],
            "collection": sutta["collection"],
            "text": sutta["text"],
            "themes": sutta["themes"],
            "embedding": embedding.astype(np.float32).tolist(),
        }

        # Store in Redis as JSON
        key = f"{DOC_PREFIX}{sutta['id']}"
        client.json().set(key, "$", doc)
        indexed_count += 1

    return indexed_count


def search_suttas(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Perform semantic search over suttas.

    Args:
        query: Search query text
        top_k: Number of results to return (default: 3)

    Returns:
        List of sutta dictionaries with score field added
    """
    client = get_redis_client()

    # Generate query embedding
    query_embedding = embed_text(query)
    query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

    # Build search query
    q = (
        Query(f"(*)=>[KNN {top_k} @embedding $query_vec AS score]")
        .sort_by("score")
        .return_fields("id", "title", "collection", "text", "themes", "score")
        .dialect(2)
    )

    # Execute search
    try:
        results = client.ft(INDEX_NAME).search(
            q, query_params={"query_vec": query_vector}
        )
    except redis.exceptions.ResponseError:
        # Index doesn't exist or is empty
        return []

    # Format results
    formatted_results = []
    for doc in results.docs:
        # Extract fields
        result = {
            "id": doc.id.replace(DOC_PREFIX, "") if hasattr(doc, "id") else "",
            "title": getattr(doc, "title", ""),
            "collection": getattr(doc, "collection", ""),
            "text": getattr(doc, "text", ""),
            "themes": json.loads(getattr(doc, "themes", "[]"))
            if hasattr(doc, "themes")
            else [],
            "score": float(getattr(doc, "score", 0.0)),
        }
        formatted_results.append(result)

    return formatted_results
