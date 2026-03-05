#!/usr/bin/env python3
"""Migrate Phase 1 seeker state to Phase 2 actor state format.

Phase 1 format: key="seeker:{chat_id}", value=JSON array of messages
Phase 2 format: Dapr actor state keys follow the pattern:
    "actors||{actorType}||{actorId}||{stateKey}"

    For SeekerActor:
    - actorType: "SeekerActor"
    - actorId: chat_id (Telegram chat ID)
    - stateKey: "state" (the main state object)

This script:
1. Connects to Redis
2. Scans for all "seeker:*" keys
3. For each key, extracts the conversation history
4. Creates a new actor state with:
   - chat_id
   - practice_level: "newcomer" (default)
   - conversation_count: number of user messages
   - topics_explored: [] (empty, will be populated later)
   - history: existing messages
   - last_active: current timestamp
5. Writes to the actor state key format
6. Does NOT delete old keys (manual cleanup after verification)

Run once during Phase 2 deployment.

Usage:
    python scripts/migrate_state_to_actors.py --redis-host lbob-redis --redis-port 6379
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

import redis


def get_redis_client(host: str, port: int) -> redis.Redis:
    """Create Redis client."""
    return redis.Redis(host=host, port=port, decode_responses=True)


def scan_seeker_keys(client: redis.Redis) -> list[str]:
    """Scan Redis for all seeker:* keys."""
    keys = []
    for key in client.scan_iter(match="seeker:*", count=100):
        keys.append(key)
    return keys


def parse_chat_id(key: str) -> str:
    """Extract chat_id from seeker:* key."""
    # Format: seeker:{chat_id}
    return key.split(":", 1)[1]


def load_phase1_state(client: redis.Redis, key: str) -> list[dict]:
    """Load Phase 1 conversation history."""
    value = client.get(key)
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON for key {key}")
        return []


def count_user_messages(history: list[dict]) -> int:
    """Count user messages in conversation history."""
    return sum(1 for msg in history if msg.get("role") == "user")


def create_actor_state(chat_id: str, history: list[dict]) -> dict[str, Any]:
    """Create Phase 2 actor state from Phase 1 data."""
    return {
        "chat_id": chat_id,
        "practice_level": "newcomer",  # Default, will be updated by heuristic
        "conversation_count": count_user_messages(history),
        "topics_explored": [],  # Will be populated as themes are detected
        "last_active": datetime.now(timezone.utc).isoformat(),
        "preferences": {},
        "history": history,
    }


def get_actor_state_key(
    actor_type: str, actor_id: str, state_key: str = "state"
) -> str:
    """Generate Dapr actor state key.

    Format: actors||{actorType}||{actorId}||{stateKey}
    """
    return f"actors||{actor_type}||{actor_id}||{state_key}"


def write_actor_state(
    client: redis.Redis, actor_type: str, actor_id: str, state: dict[str, Any]
) -> None:
    """Write actor state to Redis in Dapr actor format."""
    key = get_actor_state_key(actor_type, actor_id)
    # Dapr stores actor state as JSON
    value = json.dumps(state)
    client.set(key, value)


def migrate_key(
    client: redis.Redis, phase1_key: str, actor_type: str, dry_run: bool = False
) -> tuple[str, dict[str, Any]] | None:
    """Migrate a single Phase 1 key to Phase 2 actor format.

    Returns (actor_id, state) if successful, None otherwise.
    """
    chat_id = parse_chat_id(phase1_key)
    history = load_phase1_state(client, phase1_key)

    if not history:
        print(f"  Skipping {phase1_key} (empty history)")
        return None

    state = create_actor_state(chat_id, history)

    if not dry_run:
        write_actor_state(client, actor_type, chat_id, state)

    return (chat_id, state)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Phase 1 seeker state to Phase 2 actor state"
    )
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--actor-type",
        default="SeekerActor",
        help="Actor type name (default: SeekerActor)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: don't write to Redis, just report what would be done",
    )

    args = parser.parse_args()

    # Connect to Redis
    print(f"Connecting to Redis at {args.redis_host}:{args.redis_port}...")
    try:
        client = get_redis_client(args.redis_host, args.redis_port)
        client.ping()
    except redis.ConnectionError as e:
        print(f"Error: Could not connect to Redis: {e}")
        sys.exit(1)

    # Scan for seeker keys
    print("Scanning for seeker:* keys...")
    keys = scan_seeker_keys(client)
    print(f"Found {len(keys)} seeker keys")

    if not keys:
        print("No keys to migrate. Exiting.")
        return

    # Migrate each key
    migrated = []
    skipped = []

    for key in keys:
        print(f"\nMigrating {key}...")
        result = migrate_key(client, key, args.actor_type, dry_run=args.dry_run)
        if result:
            actor_id, state = result
            migrated.append((actor_id, state))
            print(f"  ✓ Migrated to actor {args.actor_type}/{actor_id}")
            print(f"    - Conversation count: {state['conversation_count']}")
            print(f"    - History messages: {len(state['history'])}")
        else:
            skipped.append(key)

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total keys found:    {len(keys)}")
    print(f"Successfully migrated: {len(migrated)}")
    print(f"Skipped (empty):     {len(skipped)}")

    if args.dry_run:
        print("\n⚠️  DRY RUN: No changes were written to Redis")
    else:
        print("\n✓ Migration complete!")
        print("\nOld seeker:* keys have NOT been deleted.")
        print("After verifying the migration, manually delete them with:")
        print(
            f"  redis-cli -h {args.redis_host} -p {args.redis_port} --scan --pattern 'seeker:*' | xargs redis-cli -h {args.redis_host} DEL"
        )

    print("\nActor state keys created:")
    for actor_id, state in migrated[:5]:  # Show first 5
        key = get_actor_state_key(args.actor_type, actor_id)
        print(f"  {key}")
    if len(migrated) > 5:
        print(f"  ... and {len(migrated) - 5} more")


if __name__ == "__main__":
    main()
