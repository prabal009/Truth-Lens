"""
TruthLens — Heuristic Analyzer
5-layer rule-based analysis engine that supplements ML predictions.
Especially effective for short, student-specific messages.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Signal Libraries ───────────────────────────────────────────────────────────

URGENCY_WORDS = [
    "urgent", "immediately", "asap", "right now", "hurry", "don't wait",
    "emergency", "breaking", "alert", "warning", "critical", "must read",
    "important", "attention", "notice", "share now", "forward now",
    "last chance", "deadline", "act now", "time sensitive",
]

FEAR_WORDS = [
    "fail", "cancel", "cancelled", "postponed", "suspended", "banned",
    "expelled", "arrested", "danger", "threat", "beware", "avoid",
    "harmful", "dangerous", "virus", "infected", "affected", "victim",
    "loss", "fine", "penalty", "punishment", "illegal", "shutdown",
]

CLICKBAIT_PHRASES = [
    "you won't believe", "shocking", "unbelievable", "exposed",
    "secret", "hidden truth", "they don't want you to know",
    "must see", "what happened next", "this is why", "the real truth",
    "100% confirmed", "officially confirmed", "breaking news",
    "exclusive", "leaked", "viral", "trending",
]

FORWARD_PATTERNS = [
    r"forwarded as received",
    r"\*?forwarded\*?",
    r"message from (a )?(reliable|trusted|official|verified) source",
    r"received from",
    r"share (this )?(with|to) (all|everyone|your)",
    r"forward (to|this) (all|everyone|your|at least)",
    r"send (this )?(to|at least)",
    r"pass (this )?(on|to|along)",
]

SUSPICIOUS_URL_PATTERNS = [
    r"bit\.ly/", r"tinyurl\.com/", r"goo\.gl/",
    r"t\.co/", r"cutt\.ly/", r"rb\.gy/",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",   # bare IP addresses
]

PRESSURE_PHRASES = [
    "must share", "please share", "share with all", "spread the word",
    "tell everyone", "inform everyone", "let everyone know",
    "copy paste", "copy and paste", "don't ignore",
    "don't delete", "do not ignore", "don't miss",
]

SUPERLATIVES = [
    "never before", "first time ever", "biggest ever", "worst ever",
    "only one", "exclusive offer", "guaranteed", "100%", "no doubt",
    "definitely", "absolutely confirmed", "officially",
]

# ── Result Structures ──────────────────────────────────────────────────────────

@dataclass
class Evidence:
    layer: str
    severity: str        # "high" | "medium" | "low"
    message: str
    score_impact: int    # negative = reduces credibility

@dataclass
class HeuristicResult:
    score: int                          # 0–100 (100 = most credible)
    evidence: List[Evidence] = field(default_factory=list)

    def to_dict(self):
        return {
            "score": self.score,
            "evidence": [
                {
                    "layer": e.layer,
                    "severity": e.severity,
                    "message": e.message,
                    "score_impact": e.score_impact,
                }
                for e in self.evidence
            ],
        }

# ── Main Analyzer ──────────────────────────────────────────────────────────────

class HeuristicAnalyzer:

    def analyze(self, text: str) -> HeuristicResult:
        if not text or not text.strip():
            return HeuristicResult(score=50, evidence=[])

        evidence: List[Evidence] = []
        penalty = 0

        text_lower = text.lower()
        words      = text_lower.split()
        word_count = max(len(words), 1)

        # ── Layer 1: Lexical ───────────────────────────────────────────────
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.40:
            p = 20
            penalty += p
            evidence.append(Evidence("Lexical", "high",
                f"Excessive CAPS — {caps_ratio:.0%} of text is uppercase (normal < 15%)", -p))
        elif caps_ratio > 0.20:
            p = 10
            penalty += p
            evidence.append(Evidence("Lexical", "medium",
                f"High CAPS ratio ({caps_ratio:.0%})", -p))

        punct_count = len(re.findall(r"[!?]{2,}", text))
        if punct_count >= 3:
            p = 15
            penalty += p
            evidence.append(Evidence("Lexical", "high",
                f"Spam punctuation — {punct_count} occurrences of !! or ?? detected", -p))
        elif punct_count >= 1:
            p = 7
            penalty += p
            evidence.append(Evidence("Lexical", "medium",
                f"Excessive punctuation ({punct_count} occurrences)", -p))

        emoji_count = len(re.findall(
            r"[\U0001F300-\U0001FFFF\U00002600-\U000027BF]", text))
        density = emoji_count / word_count
        if density > 0.3:
            p = 12
            penalty += p
            evidence.append(Evidence("Lexical", "medium",
                f"High emoji density — {emoji_count} emojis in {word_count} words", -p))

        # ── Layer 2: Semantic ──────────────────────────────────────────────
        matched_urgency = [w for w in URGENCY_WORDS if w in text_lower]
        if len(matched_urgency) >= 2:
            p = 20
            penalty += p
            evidence.append(Evidence("Semantic", "high",
                f"Multiple urgency signals: {', '.join(matched_urgency[:4])}", -p))
        elif len(matched_urgency) == 1:
            p = 8
            penalty += p
            evidence.append(Evidence("Semantic", "low",
                f"Urgency language detected: '{matched_urgency[0]}'", -p))

        matched_fear = [w for w in FEAR_WORDS if w in text_lower]
        if len(matched_fear) >= 2:
            p = 15
            penalty += p
            evidence.append(Evidence("Semantic", "high",
                f"Fear/threat language: {', '.join(matched_fear[:4])}", -p))
        elif len(matched_fear) == 1:
            p = 7
            penalty += p
            evidence.append(Evidence("Semantic", "low",
                f"Fear language detected: '{matched_fear[0]}'", -p))

        matched_clickbait = [p for p in CLICKBAIT_PHRASES if p in text_lower]
        if matched_clickbait:
            p = 15
            penalty += p
            evidence.append(Evidence("Semantic", "high",
                f"Clickbait phrase detected: '{matched_clickbait[0]}'", -p))

        matched_pressure = [p for p in PRESSURE_PHRASES if p in text_lower]
        if matched_pressure:
            p = 18
            penalty += p
            evidence.append(Evidence("Semantic", "high",
                f"Social pressure to share: '{matched_pressure[0]}'", -p))

        matched_superlatives = [s for s in SUPERLATIVES if s in text_lower]
        if len(matched_superlatives) >= 2:
            p = 10
            penalty += p
            evidence.append(Evidence("Semantic", "medium",
                f"Overconfident/superlative language: {', '.join(matched_superlatives[:3])}", -p))

        # ── Layer 3: Source ────────────────────────────────────────────────
        has_source = bool(re.search(
            r"(prof|professor|dr|department|office|principal|hod|director|"
            r"admin|official|university|college|institute|management)\b",
            text_lower))
        has_name = bool(re.search(r"—\s*[A-Z][a-z]+ [A-Z][a-z]+", text))
        if not has_source and not has_name:
            p = 15
            penalty += p
            evidence.append(Evidence("Source", "high",
                "No identifiable source, author, or official designation found", -p))

        suspicious_url = any(re.search(pat, text_lower)
                             for pat in SUSPICIOUS_URL_PATTERNS)
        if suspicious_url:
            p = 20
            penalty += p
            evidence.append(Evidence("Source", "high",
                "Suspicious/shortened URL detected — common in phishing", -p))

        unverified_contact = bool(re.search(r"\b\d{10}\b", text))
        if unverified_contact and not has_source:
            p = 12
            penalty += p
            evidence.append(Evidence("Source", "medium",
                "Unverified phone number with no official source", -p))

        # ── Layer 4: Structural ────────────────────────────────────────────
        for pat in FORWARD_PATTERNS:
            if re.search(pat, text_lower):
                p = 18
                penalty += p
                evidence.append(Evidence("Structural", "high",
                    "Classic forwarded-message pattern detected", -p))
                break

        if word_count < 10 and any(w in text_lower for w in ["cancelled", "postponed", "emergency"]):
            p = 12
            penalty += p
            evidence.append(Evidence("Structural", "medium",
                "Very short message making significant claim — suspicious brevity", -p))

        # ── Layer 5: Temporal ──────────────────────────────────────────────
        has_date = bool(re.search(
            r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{1,2}(st|nd|rd|th)?\s+"
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))\b",
            text_lower))
        has_year = bool(re.search(r"\b202[0-9]\b", text))
        if not has_date and not has_year and word_count > 15:
            p = 8
            penalty += p
            evidence.append(Evidence("Temporal", "low",
                "No specific date or time reference — hard to verify or trace", -p))

        # ── Score ──────────────────────────────────────────────────────────
        score = max(0, min(100, 100 - penalty))

        # Bonus for strong positive signals
        if has_source and has_date and not matched_urgency:
            score = min(100, score + 10)
            evidence.append(Evidence("Source", "low",
                "Named official source and date present — positive indicator", +10))

        return HeuristicResult(score=score, evidence=evidence)


# ── Singleton ──────────────────────────────────────────────────────────────────
_analyzer = HeuristicAnalyzer()

def analyze(text: str) -> HeuristicResult:
    return _analyzer.analyze(text)


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        ("🚨🚨 URGENT!!! Tomorrow's exam has been CANCELLED!!! "
         "Forward this to all students IMMEDIATELY!!! 🚨🚨",
         "Expected: LOW score"),
        ("Dear Students, The mid-semester examination for CS301 is rescheduled "
         "to 25th May 2026 (Monday), 10:00 AM, Room 204. — Prof. Sharma, HOD",
         "Expected: HIGH score"),
    ]
    analyzer = HeuristicAnalyzer()
    for text, label in samples:
        r = analyzer.analyze(text)
        print(f"\n{label}")
        print(f"  Text    : {text[:70]}...")
        print(f"  Score   : {r.score}/100")
        for e in r.evidence:
            print(f"  [{e.layer}] {e.severity.upper():6} | {e.message}")
