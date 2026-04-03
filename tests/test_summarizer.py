"""Tests for the summarizer module."""

import pytest

from scribebox.summarizer import (
    textrank_summarize,
    extract_keywords,
    RollingSummarizer,
    _split_sentences,
    _word_frequencies,
    _sentence_similarity,
)


class TestSentenceSplitting:
    def test_basic_split(self):
        text = "Hello world. This is a test sentence. And another one here."
        sentences = _split_sentences(text)
        assert len(sentences) == 3

    def test_short_fragments_filtered(self):
        text = "OK. This is a real sentence with enough words. Hi."
        sentences = _split_sentences(text)
        # "OK." and "Hi." are < 10 chars, should be filtered
        assert len(sentences) == 1

    def test_newline_splitting(self):
        text = "First sentence is here\nSecond sentence is here too"
        sentences = _split_sentences(text)
        assert len(sentences) == 2


class TestWordFrequencies:
    def test_stop_words_excluded(self):
        text = "the cat is on the mat and the dog"
        freqs = _word_frequencies(text)
        assert "the" not in freqs
        assert "cat" in freqs
        assert "mat" in freqs
        assert "dog" in freqs

    def test_transcription_fillers_excluded(self):
        text = "um uh like basically actually yeah okay"
        freqs = _word_frequencies(text)
        assert len(freqs) == 0


class TestSentenceSimilarity:
    def test_identical_sentences(self):
        s = "the quick brown fox jumps over the lazy dog"
        sim = _sentence_similarity(s, s)
        assert sim > 0

    def test_different_sentences(self):
        s1 = "the quick brown fox jumps"
        s2 = "python programming language features"
        sim = _sentence_similarity(s1, s2)
        assert sim == 0.0

    def test_overlapping_sentences(self):
        s1 = "machine learning algorithms are powerful"
        s2 = "deep learning algorithms use neural networks"
        sim = _sentence_similarity(s1, s2)
        assert sim > 0


class TestTextRankSummarize:
    def test_short_text_returned_as_is(self):
        text = "Short text here."
        result = textrank_summarize(text, num_sentences=3)
        assert result == text

    def test_summarization_reduces_length(self):
        sentences = [
            "Artificial intelligence is transforming the technology landscape significantly.",
            "Machine learning models can process vast amounts of data efficiently.",
            "Natural language processing enables computers to understand human speech.",
            "Computer vision allows machines to interpret visual information accurately.",
            "Reinforcement learning teaches agents through trial and error processes.",
            "Deep learning uses neural networks with multiple processing layers.",
            "Transfer learning applies knowledge from one domain to another effectively.",
            "Generative models can create new content based on training data patterns.",
        ]
        text = " ".join(sentences)
        summary = textrank_summarize(text, num_sentences=2)
        # Summary should be shorter than original
        assert len(summary) < len(text)
        # Summary should contain actual sentences from the text
        for s in summary.split(". "):
            s_clean = s.strip().rstrip(".")
            assert any(s_clean in orig for orig in sentences)

    def test_preserves_sentence_order(self):
        sentences = [
            "First important point about the discussion topic.",
            "Second tangential remark about something else entirely.",
            "Third crucial argument that supports the main thesis.",
            "Fourth minor detail that adds little to discourse.",
            "Fifth concluding statement that wraps everything up nicely.",
        ]
        text = " ".join(sentences)
        summary = textrank_summarize(text, num_sentences=2)
        # The selected sentences should maintain original order
        parts = summary.split(". ")
        if len(parts) >= 2:
            for i, part in enumerate(parts[:-1]):
                idx_a = text.find(part.strip())
                idx_b = text.find(parts[i + 1].strip())
                if idx_a >= 0 and idx_b >= 0:
                    assert idx_a < idx_b


class TestExtractKeywords:
    def test_basic_extraction(self):
        text = ("transcription transcription transcription "
                "audio audio speech recognition recognition")
        keywords = extract_keywords(text, top_n=3)
        assert "transcription" in keywords
        assert len(keywords) <= 3

    def test_empty_text(self):
        assert extract_keywords("", top_n=5) == []


class TestRollingSummarizer:
    def test_add_and_retrieve(self):
        rs = RollingSummarizer(window_seconds=60)
        rs.add_text("Hello this is a test sentence.", 100.0)
        rs.add_text("Another sentence about testing things.", 105.0)
        text = rs.get_full_text()
        assert "Hello" in text
        assert "Another" in text

    def test_rolling_window_prunes(self):
        rs = RollingSummarizer(window_seconds=10)
        rs.add_text("Old text that should be pruned eventually.", 100.0)
        rs.add_text("New text that should remain in window.", 115.0)
        text = rs.get_full_text()
        assert "Old" not in text
        assert "New" in text

    def test_summary_generation(self):
        rs = RollingSummarizer(window_seconds=120)
        for i in range(10):
            rs.add_text(
                f"Sentence number {i} discussing various important topics in detail.",
                float(i * 10),
            )
        summary = rs.get_summary(num_sentences=2)
        assert len(summary) > 0

    def test_keywords(self):
        rs = RollingSummarizer(window_seconds=120)
        rs.add_text("transcription audio speech recognition processing", 1.0)
        rs.add_text("transcription audio capture microphone recording", 2.0)
        keywords = rs.get_keywords(top_n=3)
        assert len(keywords) > 0
