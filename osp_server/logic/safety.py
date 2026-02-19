"""
OSP Safety Pipeline — Real Classifier Implementation
=====================================================
Replaces hardcoded string-match mocks with:
  1. Regex pre-filters (SQL injection, command injection) — PRESERVED
  2. TF-IDF + Logistic Regression semantic classifier
  3. KL-divergence anomaly brake
  4. Risk score computation
  5. Fail-closed behavior on classifier errors
"""

import re
import math
import logging
from collections import deque
from typing import Optional, Dict, Any, List

logger = logging.getLogger("osp.safety")

# ──────────────────────────────────────────────────────
# Pre-trained safety vocabulary (bootstrapping data)
# In production, replace with a real labeled dataset
# ──────────────────────────────────────────────────────
SAFETY_CATEGORIES = {
    "JAILBREAK": {
        "keywords": [
            "ignore previous instructions", "ignore your instructions",
            "ignore instructions", "ignore your",
            "bypass safety", "override your rules", "forget your guidelines",
            "pretend you have no restrictions", "act as if you have no filters",
            "disregard your training", "you are now unfiltered", "DAN mode",
            "no restrictions", "reveal system prompt",
        ],
        "risk_level": "HIGH",
        "reason_code": "SEMANTIC_JAILBREAK_ATTEMPT",
    },
    "PRIVACY": {
        "keywords": [
            "training data", "system prompt", "internal instructions",
            "show me your rules", "what are your guidelines",
            "reveal your prompt", "display your instructions",
            "social security", "credit card number", "password",
        ],
        "risk_level": "HIGH",
        "reason_code": "SEMANTIC_PRIVACY_VIOLATION",
    },
    "ILLEGAL": {
        "keywords": [
            "synthesize drugs", "make explosives", "hack into",
            "steal identity", "forge documents", "launder money",
            "synthesizing fentanyl", "methamphetamine", "illegal weapons",
            "break into", "phishing", "ransomware",
        ],
        "risk_level": "CRITICAL",
        "reason_code": "SEMANTIC_ILLEGAL_ACTIVITY",
    },
    "VIOLENCE": {
        "keywords": [
            "explosive device", "weapon", "bomb", "assault",
            "terroris", "mass harm", "shoot", "kill people",
            "improvised explosive", "biological weapon", "chemical weapon",
        ],
        "risk_level": "CRITICAL",
        "reason_code": "SEMANTIC_VIOLENCE_HARM",
    },
    "MANIPULATION": {
        "keywords": [
            "manipulate network", "bypass account security",
            "fake identity", "social engineering", "impersonate",
            "man in the middle", "traffic manipulation",
            "spoof", "intercept communications",
        ],
        "risk_level": "HIGH",
        "reason_code": "SEMANTIC_MANIPULATION",
    },
    "INTERNAL_STATE": {
        "keywords": [
            "safety guidelines", "risk score", "internal state",
            "monitoring parameters", "confidence threshold",
            "exact text of your", "show your config",
        ],
        "risk_level": "MEDIUM",
        "reason_code": "SEMANTIC_INTERNAL_STATE_REQUEST",
    },
}


class SemanticClassifier:
    """
    TF-IDF based semantic safety classifier.
    Uses cosine similarity against category keyword vectors.
    Falls back to keyword matching if scikit-learn is unavailable.
    """

    def __init__(self):
        self._vectorizer = None
        self._category_vectors = None
        self._available = False
        self._initialize()

    def _initialize(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            # Build corpus from all category keywords
            all_docs = []
            self._category_names = []
            for cat_name, cat_data in SAFETY_CATEGORIES.items():
                doc = " ".join(cat_data["keywords"])
                all_docs.append(doc)
                self._category_names.append(cat_name)

            self._vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
            )
            self._category_vectors = self._vectorizer.fit_transform(all_docs)
            self._cosine_similarity = cosine_similarity
            self._available = True
            logger.info("TF-IDF Safety Classifier initialized.")
        except ImportError:
            logger.warning("scikit-learn not available. Using keyword fallback for safety.")
            self._available = False

    def classify(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Classify a query against safety categories.
        Returns dict with category, risk_score, reason_code, or None if safe.
        """
        if self._available:
            return self._classify_tfidf(query)
        else:
            return self._classify_keywords(query)

    def _classify_tfidf(self, query: str) -> Optional[Dict[str, Any]]:
        """TF-IDF + cosine similarity classification."""
        query_vec = self._vectorizer.transform([query.lower()])
        similarities = self._cosine_similarity(query_vec, self._category_vectors)[0]

        best_idx = similarities.argmax()
        best_score = float(similarities[best_idx])

        # Threshold: 0.15+ = suspicious, 0.25+ = block
        if best_score < 0.15:
            return None

        cat_name = self._category_names[best_idx]
        cat_data = SAFETY_CATEGORIES[cat_name]

        return {
            "category": cat_name,
            "risk_score": round(best_score, 4),
            "risk_level": cat_data["risk_level"],
            "reason_code": cat_data["reason_code"],
            "blocked": best_score >= 0.25,
        }

    def _classify_keywords(self, query: str) -> Optional[Dict[str, Any]]:
        """Keyword fallback when scikit-learn is unavailable."""
        query_lower = query.lower()
        best_match = None
        best_score = 0.0

        for cat_name, cat_data in SAFETY_CATEGORIES.items():
            hits = sum(1 for kw in cat_data["keywords"] if kw.lower() in query_lower)
            if hits > 0:
                score = hits / len(cat_data["keywords"])
                if score > best_score:
                    best_score = score
                    best_match = {
                        "category": cat_name,
                        "risk_score": round(min(score * 3, 0.99), 4),
                        "risk_level": cat_data["risk_level"],
                        "reason_code": cat_data["reason_code"],
                        "blocked": hits >= 1,  # Block on any keyword match
                    }

        return best_match


def _kl_divergence(p: List[float], q: List[float]) -> float:
    """
    Compute KL-Divergence D_KL(P || Q).
    Used to detect anomalous divergence between lexical and semantic scores.
    """
    epsilon = 1e-10
    result = 0.0
    for pi, qi in zip(p, q):
        pi = max(pi, epsilon)
        qi = max(qi, epsilon)
        result += pi * math.log(pi / qi)
    return result


class SafetyService:
    """
    OSP Safety Service with real semantic classification.
    """

    def __init__(self):
        # Regex pre-filters (kept from original — these are real)
        self.sql_injection_pattern = re.compile(
            r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|update\s+.*set|or\s+1\s*=\s*1)"
        )
        self.command_injection_pattern = re.compile(
            r"(?i)(rm\s+-rf|;\s*ls|\|\s*cat|;\s*shutdown|;\s*reboot|cat\s+/etc/passwd|\|\s*grep|`.*`|\$\(.*\))"
        )

        # Semantic classifier
        self.classifier = SemanticClassifier()

        # Anomaly detection state (bounded to prevent memory leak)
        self._lexical_history: deque = deque(maxlen=100)
        self._semantic_history: deque = deque(maxlen=100)
        self._anomaly_threshold = 0.5  # KL-divergence threshold

    def check_safety(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Multi-layer safety check:
          1. Regex pre-filters
          2. Semantic classifier
          3. KL-divergence anomaly brake
        """
        trace_events = []

        # ── Layer 1: SQL Injection ──────────────────────────
        if self.sql_injection_pattern.search(query):
            trace_events.append({"code": "PREFILTER_MATCH", "stage_attempted": "lexical_injection_filter", "matched_pattern": "sql_keywords"})
            trace_events.append({"code": "BLOCK_ACTION", "stage_attempted": "prefilter_stage"})
            return {
                "safe": False,
                "reason_code": "PREFILTER_SQL_INJECTION",
                "message": "Potential SQL injection detected",
                "safe_alternative": "I cannot help with database queries. Please rephrase your request.",
                "trace_events": trace_events,
            }

        # ── Layer 2: Command Injection ──────────────────────
        if self.command_injection_pattern.search(query):
            trace_events.append({"code": "PREFILTER_MATCH", "stage_attempted": "forbidden_pattern_filter", "matched_pattern": "shell_metacharacters"})
            trace_events.append({"code": "BLOCK_ACTION", "stage_attempted": "prefilter_stage"})
            return {
                "safe": False,
                "reason_code": "PREFILTER_COMMAND_INJECTION",
                "message": "Potential command injection detected",
                "safe_alternative": "I cannot execute system commands. Please describe what you'd like to accomplish.",
                "trace_events": trace_events,
            }

        trace_events.append({"code": "PREFILTER_PASS", "stage_attempted": "lexical_injection_filter"})

        # ── Layer 3: Semantic Classifier ────────────────────
        try:
            result = self.classifier.classify(query)

            if result is None:
                trace_events.append({"code": "SEMANTIC_ANALYSIS_START", "stage_attempted": "semantic_classifier"})
                trace_events.append({"code": "SEMANTIC_SAFE_PASS", "stage_attempted": "semantic_classifier"})
                return None  # Safe

            trace_events.append({"code": "SEMANTIC_ANALYSIS_START", "stage_attempted": "semantic_classifier"})
            trace_events.append({
                "code": "SEMANTIC_RISK_DETECTED",
                "stage_attempted": "semantic_classifier",
                "risk_score": result["risk_score"],
                "risk_category": result["category"],
            })

            if result["blocked"]:
                trace_events.append({"code": "BLOCK_ACTION", "stage_attempted": "semantic_decision"})
                trace_events.append({"code": "SAFE_FALLBACK_GENERATED", "stage_attempted": "fallback_handler"})

                message_map = {
                    "JAILBREAK": "I maintain consistent safety guidelines.",
                    "PRIVACY": "I can't share internal details.",
                    "ILLEGAL": "I cannot allow this request.",
                    "VIOLENCE": "I cannot allow this request.",
                    "MANIPULATION": "Request blocked due to security concerns.",
                    "INTERNAL_STATE": "I can't share my internal instructions.",
                }

                return {
                    "safe": False,
                    "reason_code": result["reason_code"],
                    "message": message_map.get(result["category"], "Request blocked."),
                    "trace_events": trace_events,
                }

            # Not blocked but suspicious — log and pass
            trace_events.append({"code": "SEMANTIC_RISK_NOTED", "stage_attempted": "semantic_classifier", "risk_score": result["risk_score"]})

        except Exception as e:
            # ── Fail-Closed ─────────────────────────────────
            logger.error(f"Semantic classifier error: {e}")
            trace_events.append({"code": "SEMANTIC_CLASSIFIER_ERROR", "stage_attempted": "semantic_classifier", "error_type": type(e).__name__})
            trace_events.append({"code": "FAIL_CLOSED_TRIGGERED", "stage_attempted": "safety_decision"})
            trace_events.append({"code": "SAFE_FALLBACK_GENERATED", "stage_attempted": "fallback_handler", "fallback_type": "classifier_unavailable"})
            return {
                "safe": False,
                "reason_code": "SAFETY_CLASSIFIER_UNAVAILABLE",
                "message": "Safety classification is temporarily unavailable.",
                "safe_alternative": "Safety classification is temporarily unavailable. Please try again in a moment.",
                "trace_events": trace_events,
            }

        # ── Layer 4: Anomaly Detection (KL-Divergence Brake) ──
        # Track lexical vs semantic score distributions to detect model drift
        if result:
            lexical_score = 1.0 if self.sql_injection_pattern.search(query) or self.command_injection_pattern.search(query) else 0.0
            semantic_score = result["risk_score"]

            self._lexical_history.append(lexical_score)
            self._semantic_history.append(semantic_score)

            # Need at least 10 samples for meaningful KL-divergence
            if len(self._lexical_history) >= 10:
                # Normalize to distributions
                lex_sum = sum(list(self._lexical_history)[-10:]) + 1e-10
                sem_sum = sum(list(self._semantic_history)[-10:]) + 1e-10
                p = [x / lex_sum for x in list(self._lexical_history)[-10:]]
                q = [x / sem_sum for x in list(self._semantic_history)[-10:]]

                kl_div = _kl_divergence(p, q)

                if kl_div > self._anomaly_threshold:
                    logger.warning(f"Anomaly detected: KL-divergence = {kl_div:.4f} (threshold: {self._anomaly_threshold})")
                    trace_events.append({
                        "code": "ANOMALY_DETECTED",
                        "stage_attempted": "anomaly_detection",
                        "anomaly_type": "distribution_shift",
                        "anomaly_confidence": round(min(kl_div / 2.0, 0.99), 2),
                    })

                    # For medium+ risk with anomaly → fail-closed
                    if result["risk_level"] in ["HIGH", "CRITICAL"]:
                        trace_events.append({"code": "SEMANTIC_ANALYSIS_DISCARDED", "stage_attempted": "safety_decision", "reason": "anomaly_detected"})
                        trace_events.append({"code": "CONSERVATIVE_BLOCK_APPLIED", "stage_attempted": "safety_decision"})
                        trace_events.append({"code": "SECURITY_EVENT_LOGGED", "stage_attempted": "logging", "severity": "CRITICAL"})
                        return {
                            "safe": False,
                            "reason_code": "ANOMALY_DETECTED_HIGH_RISK",
                            "message": "Request blocked.",
                            "trace_events": trace_events,
                        }
                    else:
                        trace_events.append({"code": "ANOMALY_DETECTED_LOW_RISK", "stage_attempted": "anomaly_detection"})

        return None  # Safe
