"""
TruthLens — Similarity Engine
Detects recycled, rephrased, and near-duplicate messages using Jaccard similarity.
Fingerprints are stored in the SQLite database via app.py's DB layer.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

# ── Config ─────────────────────────────────────────────────────────────────────
SIMILAR_THRESHOLD   = 0.55   # ≥55% → "Similar"
DUPLICATE_THRESHOLD = 0.80   # ≥80% → "Near Duplicate"

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "at", "by", "for", "from",
    "in", "into", "of", "on", "to", "up", "with", "and", "but", "or",
    "if", "as", "it", "its", "this", "that", "these", "those", "not",
    "so", "we", "you", "he", "she", "they", "i", "my", "your", "our",
    "his", "her", "their", "all", "any", "more", "also", "just", "only",
    "very", "get", "got", "go", "went", "come", "came", "make", "made",
}


# ── Result Structures ──────────────────────────────────────────────────────────

@dataclass
class SimilarMatch:
    record_id: int
    original_text: str
    similarity: float
    match_type: str      # "duplicate" | "similar"
    original_verdict: str
    original_score: int

    def to_dict(self):
        return {
            "record_id":       self.record_id,
            "original_text":   self.original_text[:200] + ("…" if len(self.original_text) > 200 else ""),
            "similarity":      round(self.similarity * 100, 1),
            "match_type":      self.match_type,
            "original_verdict": self.original_verdict,
            "original_score":  self.original_score,
        }


# ── Core Engine ────────────────────────────────────────────────────────────────

class SimilarityEngine:

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, remove punctuation, collapse whitespace."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _tokenize(text: str) -> set:
        """Normalize → split → remove stopwords → return set of tokens."""
        tokens = SimilarityEngine._normalize(text).split()
        return {t for t in tokens if t not in STOPWORDS and len(t) > 2}

    @staticmethod
    def jaccard(set_a: set, set_b: set) -> float:
        """Compute Jaccard similarity coefficient."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union        = len(set_a | set_b)
        return intersection / union

    def find_matches(
        self,
        new_text: str,
        history: List[dict],   # [{ "id", "text", "verdict", "score" }, ...]
    ) -> List[SimilarMatch]:
        """
        Compare new_text against all stored records.
        Returns list of SimilarMatch sorted by similarity descending.
        """
        if not new_text.strip() or not history:
            return []

        new_tokens = self._tokenize(new_text)
        matches    = []

        for record in history:
            stored_tokens = self._tokenize(record.get("text", ""))
            sim = self.jaccard(new_tokens, stored_tokens)

            if sim >= SIMILAR_THRESHOLD:
                mtype = "duplicate" if sim >= DUPLICATE_THRESHOLD else "similar"
                matches.append(SimilarMatch(
                    record_id       = record.get("id", 0),
                    original_text   = record.get("text", ""),
                    similarity      = sim,
                    match_type      = mtype,
                    original_verdict = record.get("verdict", "unknown"),
                    original_score  = record.get("score", 0),
                ))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:5]   # return top-5 matches only

    def compute_pair(self, text_a: str, text_b: str) -> Tuple[float, str]:
        """Utility: directly compare two texts, return (similarity, match_type)."""
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        sim      = self.jaccard(tokens_a, tokens_b)
        if sim >= DUPLICATE_THRESHOLD:
            return sim, "duplicate"
        elif sim >= SIMILAR_THRESHOLD:
            return sim, "similar"
        return sim, "none"


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine = SimilarityEngine()

def find_matches(new_text: str, history: List[dict]) -> List[SimilarMatch]:
    return _engine.find_matches(new_text, history)

def compute_pair(text_a: str, text_b: str) -> Tuple[float, str]:
    return _engine.compute_pair(text_a, text_b)


# ── Self-test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = SimilarityEngine()
    a = "URGENT exam cancelled tomorrow forward immediately to all students"
    b = "URGENT!!! Tomorrow exam is CANCELLED!!! Please forward to everyone NOW!!!"
    c = "Dear students, the library will remain open till 10 PM during exams."
    sim_ab, type_ab = engine.compute_pair(a, b)
    sim_ac, type_ac = engine.compute_pair(a, c)
    print(f"A vs B: {sim_ab:.2%} → {type_ab}")
    print(f"A vs C: {sim_ac:.2%} → {type_ac}")
