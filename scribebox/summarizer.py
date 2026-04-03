"""Extractive summarization using TextRank.

Lightweight, no model download required. Works entirely offline.
Summarizes rolling windows of transcript text.
"""

import math
import re
from collections import Counter


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Simple sentence splitter for transcription text
    sentences = re.split(r'(?<=[.!?])\s+|(?<=\.\.\.)\s+|\n+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _word_frequencies(text: str) -> Counter:
    """Compute word frequencies, excluding stop words."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "about",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "because", "but", "and", "or", "if", "while", "that", "this", "it",
        "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
        "his", "she", "her", "they", "them", "their", "what", "which", "who",
        "whom", "these", "those", "am", "um", "uh", "like", "know", "yeah",
        "okay", "right", "well", "going", "got", "get", "thing", "things",
        "kind", "actually", "basically", "literally", "really", "said",
    }
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return Counter(w for w in words if w not in stop_words and len(w) > 2)


def _sentence_similarity(s1: str, s2: str) -> float:
    """Compute similarity between two sentences using word overlap."""
    words1 = set(re.findall(r'\b[a-z]+\b', s1.lower()))
    words2 = set(re.findall(r'\b[a-z]+\b', s2.lower()))
    if not words1 or not words2:
        return 0.0
    overlap = words1 & words2
    return len(overlap) / (math.log(len(words1) + 1) + math.log(len(words2) + 1))


def textrank_summarize(text: str, num_sentences: int = 3, damping: float = 0.85,
                       iterations: int = 30) -> str:
    """Summarize text using TextRank algorithm.

    Args:
        text: Input text to summarize.
        num_sentences: Number of sentences in the summary.
        damping: Damping factor for TextRank (like PageRank).
        iterations: Number of iterations for convergence.

    Returns:
        Summary string composed of the top-ranked sentences.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= num_sentences:
        return text

    n = len(sentences)

    # Build similarity matrix
    sim_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim = _sentence_similarity(sentences[i], sentences[j])
            sim_matrix[i][j] = sim
            sim_matrix[j][i] = sim

    # Initialize scores
    scores = [1.0 / n] * n

    # Iterate TextRank
    for _ in range(iterations):
        new_scores = [0.0] * n
        for i in range(n):
            rank_sum = 0.0
            for j in range(n):
                if i == j:
                    continue
                neighbors_sum = sum(sim_matrix[j])
                if neighbors_sum > 0:
                    rank_sum += sim_matrix[j][i] / neighbors_sum * scores[j]
            new_scores[i] = (1 - damping) / n + damping * rank_sum
        scores = new_scores

    # Rank sentences and pick top ones (preserving original order)
    ranked = sorted(range(n), key=lambda i: scores[i], reverse=True)
    top_indices = sorted(ranked[:num_sentences])

    return " ".join(sentences[i] for i in top_indices)


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Extract top keywords from text."""
    freqs = _word_frequencies(text)
    return [word for word, _ in freqs.most_common(top_n)]


class RollingSummarizer:
    """Maintains a rolling window of transcript text and produces summaries."""

    def __init__(self, window_seconds: int = 120):
        self._window_seconds = window_seconds
        self._segments: list[tuple[float, str]] = []  # (timestamp, text)

    def add_text(self, text: str, timestamp: float):
        """Add transcribed text with its timestamp."""
        if text.strip():
            self._segments.append((timestamp, text.strip()))
            self._prune()

    def _prune(self):
        """Remove segments outside the rolling window."""
        if not self._segments:
            return
        cutoff = self._segments[-1][0] - self._window_seconds
        self._segments = [(t, s) for t, s in self._segments if t >= cutoff]

    def get_summary(self, num_sentences: int = 3) -> str:
        """Get summary of text within the rolling window."""
        full_text = " ".join(s for _, s in self._segments)
        if len(full_text) < 100:
            return full_text
        return textrank_summarize(full_text, num_sentences=num_sentences)

    def get_keywords(self, top_n: int = 5) -> list[str]:
        """Get keywords from the rolling window."""
        full_text = " ".join(s for _, s in self._segments)
        return extract_keywords(full_text, top_n=top_n)

    def get_full_text(self) -> str:
        """Get all text in the current window."""
        return " ".join(s for _, s in self._segments)
