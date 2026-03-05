#!/usr/bin/env python3
"""
Fetch and process suttas from SuttaCentral's sc-data repository.

This script:
1. Clones/fetches Bhikkhu Sujato's English translations from sc-data repo
2. Parses bilara JSON files and concatenates segments
3. Filters to a curated list of essential suttas
4. Assigns theme tags based on keyword heuristics
5. Outputs suttas.json in the expected format
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def load_curated_ids(curated_path: Path) -> set[str]:
    """Load the curated sutta IDs from curated_ids.txt."""
    ids = set()
    with open(curated_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                ids.add(line.lower())
    return ids


def clone_sc_data(target_dir: Path) -> None:
    """Clone the sc-data repository with sparse checkout."""
    repo_url = "https://github.com/suttacentral/sc-data.git"

    print(f"Cloning sc-data repository to {target_dir}...")

    # Clone with depth 1 and blob filter for speed
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            repo_url,
            str(target_dir),
        ],
        check=True,
    )

    # Set up sparse checkout for only the translation directory
    subprocess.run(
        [
            "git",
            "-C",
            str(target_dir),
            "sparse-checkout",
            "set",
            "sc_bilara_data/translation/en/sujato/sutta",
        ],
        check=True,
    )

    print("Repository cloned successfully.")


def concatenate_segments(bilara_data: dict[str, str]) -> str:
    """
    Concatenate bilara JSON segments in order.

    Segments are stored as {segment_id: text} and should be
    concatenated in lexical order of segment IDs.
    Strips HTML tags if present.
    """
    # Sort by segment ID (they sort lexically within a sutta)
    sorted_segments = sorted(bilara_data.items(), key=lambda x: x[0])

    # Concatenate text values
    full_text = "".join(text for _, text in sorted_segments)

    # Strip HTML tags
    full_text = re.sub(r"<[^>]+>", "", full_text)

    return full_text.strip()


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Truncate text to max_length at the nearest sentence boundary.

    If text exceeds max_length, truncates to the last complete
    sentence before max_length and appends '[text truncated]'.
    """
    if len(text) <= max_length:
        return text

    # Find the last sentence-ending punctuation before max_length
    truncated = text[:max_length]

    # Look for sentence boundaries (. ! ?)
    sentence_endings = [m.end() for m in re.finditer(r"[.!?]\s+", truncated)]

    if sentence_endings:
        # Truncate at the last sentence boundary
        last_boundary = sentence_endings[-1]
        return truncated[:last_boundary].rstrip() + " [text truncated]"
    else:
        # No sentence boundary found, just truncate and add marker
        return truncated.rstrip() + " [text truncated]"


def assign_themes(text: str, title: str) -> list[str]:
    """
    Assign theme tags based on keyword heuristics.

    Searches for Pali and English terms in the text and title,
    returns 2-5 relevant theme tags.
    """
    # Combine text and title (title has more weight)
    searchable = (title.lower() + " " + text.lower())[:5000]  # First 5000 chars

    theme_keywords = {
        "suffering": ["suffering", "dukkha", "pain", "stress"],
        "mindfulness": ["mindfulness", "sati", "awareness", "attention"],
        "meditation": ["meditation", "jhana", "samadhi", "concentration", "contemplation"],
        "impermanence": ["impermanent", "anicca", "change", "transient", "arising and passing"],
        "non-self": ["not-self", "anatta", "non-self", "selfless"],
        "eightfold path": ["eightfold path", "noble eightfold", "eight factors"],
        "dependent origination": [
            "dependent origination",
            "conditions",
            "conditioned",
            "paticca samuppada",
            "paticcasamuppada",
        ],
        "ethics": ["ethics", "precepts", "sila", "virtue", "moral", "conduct"],
        "loving-kindness": ["loving-kindness", "metta", "friendliness", "goodwill"],
        "equanimity": ["equanimity", "upekkha", "balance", "equipoise"],
        "craving": ["craving", "tanha", "desire", "thirst", "attachment"],
        "nibbana": ["nibbana", "nirvana", "extinguishment", "unbinding", "liberation"],
        "kamma": ["kamma", "karma", "action", "deed", "volitional"],
        "rebirth": ["rebirth", "lives", "reincarnation", "becoming", "birth"],
        "lay life": ["lay life", "householder", "family", "laypeople"],
        "wisdom": ["wisdom", "insight", "understanding", "discernment", "panna"],
        "compassion": ["compassion", "karuna", "sympathy"],
        "death": ["death", "dying", "mortality", "aging"],
        "right view": ["right view", "samma ditthi", "correct view"],
        "emptiness": ["emptiness", "empty", "void", "sunyata"],
        "sense bases": ["sense bases", "six senses", "eye", "ear", "contact"],
        "aggregates": ["aggregates", "khandha", "form", "feeling", "perception"],
        "four noble truths": ["four noble truths", "noble truth"],
        "renunciation": ["renunciation", "letting go", "relinquishment"],
    }

    assigned_themes = []
    for theme, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in searchable:
                assigned_themes.append(theme)
                break  # Don't add the same theme twice

    # If no themes found, assign generic "dhamma" theme
    if not assigned_themes:
        assigned_themes = ["dhamma"]

    # Limit to 5 themes
    return assigned_themes[:5]


def extract_title_from_segments(bilara_data: dict[str, str]) -> str:
    """
    Extract the title from bilara segments.

    Title is typically in segment ending with :0.2, or :0.1 if no :0.2.
    """
    # Try to find :0.2 segment (usually the title)
    for seg_id, text in bilara_data.items():
        if seg_id.endswith(":0.2"):
            return text.strip()

    # Fallback to :0.1
    for seg_id, text in bilara_data.items():
        if seg_id.endswith(":0.1"):
            return text.strip()

    # If neither found, return empty string
    return "Untitled"


def extract_metadata_from_path(file_path: str) -> dict[str, str]:
    """
    Extract metadata from the file path.

    Returns:
        dict with 'collection' and 'sutta_id'
    """
    # File path example: translation/en/sujato/sutta/mn/mn10_translation-en-sujato.json
    # Or: translation/en/sujato/sutta/sn/sn56/sn56.11_translation-en-sujato.json

    path = Path(file_path)
    filename = path.stem  # e.g., "mn10_translation-en-sujato"

    # Extract sutta ID from filename (before first underscore)
    sutta_id = filename.split("_")[0]  # e.g., "mn10" or "sn56.11"

    # Extract collection from sutta ID
    # Collection is the letters at the start (DN, MN, SN, AN, KN)
    collection_match = re.match(r"([a-z]+)", sutta_id.lower())
    if collection_match:
        collection = collection_match.group(1).upper()
    else:
        collection = "UNKNOWN"

    return {"collection": collection, "sutta_id": sutta_id}


def process_sutta_file(
    file_path: Path,
    curated_ids: set[str],
) -> dict[str, Any] | None:
    """
    Process a single bilara JSON file.

    Returns a sutta dict if the sutta is in the curated list, None otherwise.
    """
    # Check if this sutta is in the curated list
    metadata = extract_metadata_from_path(str(file_path))
    sutta_id = metadata["sutta_id"].lower()

    if sutta_id not in curated_ids:
        return None

    # Load the bilara JSON
    with open(file_path, "r", encoding="utf-8") as f:
        bilara_data = json.load(f)

    # Extract title
    title = extract_title_from_segments(bilara_data)

    # Concatenate segments to full text
    full_text = concatenate_segments(bilara_data)

    # Truncate if needed
    full_text = truncate_text(full_text)

    # Assign themes
    themes = assign_themes(full_text, title)

    # Build the sutta dict
    sutta = {
        "id": sutta_id.upper(),  # e.g., "MN10"
        "title": title,
        "collection": metadata["collection"],
        "text": full_text,
        "themes": themes,
    }

    return sutta


def main():
    """Main entry point for the scraper."""
    # Paths
    project_root = Path(__file__).parent.parent
    curated_path = project_root / "sutta_corpus" / "curated_ids.txt"
    output_path = project_root / "sutta_corpus" / "suttas.json"

    # Load curated IDs
    print(f"Loading curated IDs from {curated_path}...")
    curated_ids = load_curated_ids(curated_path)
    print(f"Loaded {len(curated_ids)} curated sutta IDs.")

    # Clone sc-data to a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "sc-data"
        clone_sc_data(temp_path)

        # Find all translation JSON files
        translation_dir = temp_path / "sc_bilara_data" / "translation" / "en" / "sujato" / "sutta"
        json_files = list(translation_dir.glob("**/*_translation-en-sujato.json"))
        print(f"Found {len(json_files)} translation files.")

        # Process each file
        suttas = []
        for json_file in json_files:
            sutta = process_sutta_file(json_file, curated_ids)
            if sutta:
                suttas.append(sutta)
                print(f"  Processed: {sutta['id']} - {sutta['title']}")

        print(f"\nProcessed {len(suttas)} suttas from curated list.")

        # Sort by ID for consistency
        suttas.sort(key=lambda s: s["id"])

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(suttas, f, indent=2, ensure_ascii=False)

        print(f"\nWrote {len(suttas)} suttas to {output_path}")

        # Report any missing suttas
        found_ids = {s["id"].lower() for s in suttas}
        missing_ids = curated_ids - found_ids
        if missing_ids:
            print(f"\nWarning: {len(missing_ids)} curated IDs not found in sc-data:")
            for missing_id in sorted(missing_ids):
                print(f"  - {missing_id}")


if __name__ == "__main__":
    main()
