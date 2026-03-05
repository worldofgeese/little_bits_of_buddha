"""Tests for the SuttaCentral data fetcher script."""

import json
import sys
from pathlib import Path

import pytest

# Add the scripts directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from fetch_sc_suttas import (
        assign_themes,
        concatenate_segments,
        extract_metadata_from_path,
        load_curated_ids,
        truncate_text,
    )
except ImportError:
    # Module doesn't exist yet - tests will fail as expected in TDD
    assign_themes = None
    concatenate_segments = None
    extract_metadata_from_path = None
    load_curated_ids = None
    truncate_text = None


class TestCuratedIds:
    """Test the curated sutta IDs list."""

    def test_curated_ids_file_exists(self):
        """Test that curated_ids.txt exists."""
        curated_path = Path(__file__).parent.parent / "sutta_corpus" / "curated_ids.txt"
        assert curated_path.exists(), "curated_ids.txt must exist"

    def test_curated_ids_has_200_plus_entries(self):
        """Test that curated_ids.txt has at least 200 entries."""
        if load_curated_ids is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        curated_path = Path(__file__).parent.parent / "sutta_corpus" / "curated_ids.txt"
        ids = load_curated_ids(curated_path)
        assert len(ids) >= 200, f"Expected at least 200 IDs, got {len(ids)}"


class TestSegmentConcatenation:
    """Test the segment concatenation logic."""

    def test_concatenate_segments_basic(self):
        """Test basic segment concatenation."""
        if concatenate_segments is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        bilara_data = {
            "mn10:0.1": "Middle Discourses 10 ",
            "mn10:0.2": "Mindfulness Meditation ",
            "mn10:1.1": "So I have heard. ",
            "mn10:1.2": "At one time the Buddha was staying near Sāvatthī. ",
        }
        result = concatenate_segments(bilara_data)
        expected = (
            "Middle Discourses 10 Mindfulness Meditation "
            "So I have heard. At one time the Buddha was staying near Sāvatthī."
        )
        assert result.strip() == expected.strip()

    def test_concatenate_segments_preserves_order(self):
        """Test that segments are concatenated in correct order."""
        if concatenate_segments is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        bilara_data = {
            "sn1.1:2.3": "third ",
            "sn1.1:1.1": "first ",
            "sn1.1:2.1": "second ",
        }
        result = concatenate_segments(bilara_data)
        assert result.strip() == "first second third"

    def test_concatenate_segments_handles_html(self):
        """Test that HTML tags are stripped if present."""
        if concatenate_segments is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        bilara_data = {
            "test:1.1": "Some <em>emphasized</em> text. ",
            "test:1.2": "And <strong>bold</strong> text. ",
        }
        result = concatenate_segments(bilara_data)
        # Should strip HTML tags
        assert "<em>" not in result
        assert "<strong>" not in result
        assert "emphasized" in result
        assert "bold" in result


class TestThemeAssignment:
    """Test the theme assignment heuristic."""

    def test_assign_themes_mindfulness(self):
        """Test that mindfulness theme is assigned correctly."""
        if assign_themes is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = "This sutta teaches mindfulness meditation and sati practice."
        title = "On Mindfulness"
        themes = assign_themes(text, title)
        assert "mindfulness" in themes

    def test_assign_themes_suffering(self):
        """Test that suffering theme is assigned correctly."""
        if assign_themes is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = "The Buddha taught about dukkha and the end of suffering."
        title = "On Suffering"
        themes = assign_themes(text, title)
        assert "suffering" in themes

    def test_assign_themes_multiple(self):
        """Test that multiple themes are assigned."""
        if assign_themes is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = (
            "The Buddha taught mindfulness meditation to overcome suffering "
            "and understand impermanence through jhana and samadhi practice."
        )
        title = "Mixed Teachings"
        themes = assign_themes(text, title)
        assert len(themes) >= 2, "Should assign multiple themes"
        assert len(themes) <= 5, "Should not assign more than 5 themes"

    def test_assign_themes_loving_kindness(self):
        """Test that loving-kindness theme is assigned correctly."""
        if assign_themes is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = "Cultivate metta and loving-kindness towards all beings."
        title = "Metta Sutta"
        themes = assign_themes(text, title)
        assert "loving-kindness" in themes


class TestTextTruncation:
    """Test the text truncation logic."""

    def test_truncate_text_no_truncation_needed(self):
        """Test that short text is not truncated."""
        if truncate_text is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = "Short text. Another sentence."
        result = truncate_text(text, max_length=4000)
        assert result == text
        assert "[text truncated]" not in result

    def test_truncate_text_at_sentence_boundary(self):
        """Test that truncation happens at sentence boundaries."""
        if truncate_text is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        # Create a text longer than the limit
        sentences = ["Sentence number {}.".format(i) for i in range(200)]
        text = " ".join(sentences)
        result = truncate_text(text, max_length=500)

        assert len(result) <= 500 + 50, "Should be close to max_length"
        assert result.endswith("[text truncated]")
        # Should end at a sentence boundary (period before the truncation marker)
        assert ". [text truncated]" in result or ".[text truncated]" in result

    def test_truncate_text_preserves_complete_sentences(self):
        """Test that truncation preserves complete sentences."""
        if truncate_text is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        text = "First sentence. " + "x" * 400 + " Second sentence. Third sentence."
        result = truncate_text(text, max_length=450)

        # Should not cut mid-sentence
        if "[text truncated]" in result:
            truncation_marker_pos = result.find("[text truncated]")
            text_before_marker = result[:truncation_marker_pos].rstrip()
            # Check that we end with sentence-ending punctuation
            assert text_before_marker[-1] in ".!?", "Should end at sentence boundary"


class TestMetadataExtraction:
    """Test the metadata extraction from file paths."""

    def test_extract_metadata_mn(self):
        """Test metadata extraction for MN suttas."""
        if extract_metadata_from_path is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        path = "sc_bilara_data/translation/en/sujato/sutta/mn/mn10_translation-en-sujato.json"
        metadata = extract_metadata_from_path(path)
        assert metadata["collection"] == "MN"
        assert metadata["sutta_id"] == "mn10"

    def test_extract_metadata_sn(self):
        """Test metadata extraction for SN suttas."""
        if extract_metadata_from_path is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        path = "sc_bilara_data/translation/en/sujato/sutta/sn/sn56.11_translation-en-sujato.json"
        metadata = extract_metadata_from_path(path)
        assert metadata["collection"] == "SN"
        assert metadata["sutta_id"] == "sn56.11"

    def test_extract_metadata_an(self):
        """Test metadata extraction for AN suttas."""
        if extract_metadata_from_path is None:
            pytest.skip("fetch_sc_suttas module not implemented yet")

        path = "sc_bilara_data/translation/en/sujato/sutta/an/an8.54_translation-en-sujato.json"
        metadata = extract_metadata_from_path(path)
        assert metadata["collection"] == "AN"
        assert metadata["sutta_id"] == "an8.54"


class TestOutputFormat:
    """Test that the output format matches the expected schema."""

    def test_output_format_validation(self):
        """Test that generated suttas match the expected JSON schema."""
        # This will test the actual output file after running the scraper
        output_path = Path(__file__).parent.parent / "sutta_corpus" / "suttas.json"

        if not output_path.exists():
            pytest.skip("suttas.json not generated yet")

        with open(output_path, "r", encoding="utf-8") as f:
            suttas = json.load(f)

        assert isinstance(suttas, list), "Output should be a JSON array"
        assert len(suttas) >= 200, f"Expected at least 200 suttas, got {len(suttas)}"

        # Check first sutta has required fields
        if len(suttas) > 0:
            first_sutta = suttas[0]
            assert "id" in first_sutta, "Sutta must have 'id' field"
            assert "title" in first_sutta, "Sutta must have 'title' field"
            assert "collection" in first_sutta, "Sutta must have 'collection' field"
            assert "text" in first_sutta, "Sutta must have 'text' field"
            assert "themes" in first_sutta, "Sutta must have 'themes' field"

            # Validate types
            assert isinstance(first_sutta["id"], str)
            assert isinstance(first_sutta["title"], str)
            assert isinstance(first_sutta["collection"], str)
            assert isinstance(first_sutta["text"], str)
            assert isinstance(first_sutta["themes"], list)

            # Check that text is not empty
            assert len(first_sutta["text"]) > 0, "Text field should not be empty"

            # Check that themes are reasonable
            assert 2 <= len(first_sutta["themes"]) <= 5, "Should have 2-5 themes"

    def test_no_empty_text_fields(self):
        """Test that no suttas have empty text fields."""
        output_path = Path(__file__).parent.parent / "sutta_corpus" / "suttas.json"

        if not output_path.exists():
            pytest.skip("suttas.json not generated yet")

        with open(output_path, "r", encoding="utf-8") as f:
            suttas = json.load(f)

        for sutta in suttas:
            assert sutta.get("text", "").strip() != "", f"Sutta {sutta.get('id')} has empty text"
