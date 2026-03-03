#!/usr/bin/env python3
"""
CLI script to index suttas into Redis with vector embeddings.

Usage:
    python scripts/embed_suttas.py [--corpus-path CORPUS_PATH]
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai_service_worldofgeese.sutta_search import index_suttas


def main():
    """Load suttas and index them into Redis."""
    parser = argparse.ArgumentParser(
        description="Index suttas into Redis with vector embeddings"
    )
    parser.add_argument(
        "--corpus-path",
        type=Path,
        default=Path(__file__).parent.parent / "sutta_corpus" / "suttas.json",
        help="Path to suttas.json file (default: sutta_corpus/suttas.json)",
    )
    args = parser.parse_args()

    # Load suttas
    print(f"Loading suttas from {args.corpus_path}...")
    if not args.corpus_path.exists():
        print(f"Error: Corpus file not found at {args.corpus_path}", file=sys.stderr)
        return 1

    with open(args.corpus_path, "r", encoding="utf-8") as f:
        suttas = json.load(f)

    print(f"Loaded {len(suttas)} suttas")

    # Validate structure
    required_fields = {"id", "title", "collection", "text", "themes"}
    for i, sutta in enumerate(suttas):
        missing = required_fields - set(sutta.keys())
        if missing:
            print(f"Error: Sutta {i} is missing fields: {missing}", file=sys.stderr)
            return 1

    # Index suttas
    print("Indexing suttas (this may take a minute to download the embedding model)...")
    try:
        count = index_suttas(suttas)
        print(f"✓ Successfully indexed {count} suttas")
        print("✓ Index name: sutta_idx")
        print("✓ Embedding model: all-MiniLM-L6-v2 (384 dimensions)")
        return 0
    except Exception as e:
        print(f"Error during indexing: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
