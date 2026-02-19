from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, constr
import time
from datetime import datetime

# --- Base Models ---

class HashingConfig(BaseModel):
    method: Literal["sha256"] = "sha256"
    canonicalization: Literal["jcs"] = "jcs"

class TrustAnchor(BaseModel):
    type: Literal["root_ca", "intermediate_ca", "did", "self_signed"]
    uri: Optional[str] = None
    proof: Optional[str] = None

# --- Registry Entry ---

class RegistryEntry(BaseModel):
    entry_type: Literal["REGISTER", "REVOKE", "DELEGATE", "KEY_ROTATE"]
    skill_ref: constr(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*(@[0-9]+(\.[0-9]+)*)?$")
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    signed_by: str
    content_hash: constr(pattern=r"^[a-f0-9]{64}$")
    signature: str
    alg: Literal["ES256", "ES384", "ES512", "RS256", "RS384", "RS512", "EdDSA"]
    trust_anchor: TrustAnchor
    hashing_config: HashingConfig

    def sign(self, private_key_pem: bytes) -> None:
        from .crypto import JCS
        data_to_sign = self.model_dump(exclude={"signature"})
        self.signature = JCS.sign(data_to_sign, private_key_pem, self.alg)


# --- Skill Manifest ---

class SkillManifest(BaseModel):
    skill_id: constr(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    name: constr(min_length=1, max_length=256)
    version: str
    activation_strategy: Literal["lexical", "semantic", "hybrid"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    scope: str
    content_hash: Optional[constr(pattern=r"^[a-f0-9]{64}$")] = None
    hashing_config: Optional[HashingConfig] = None

# --- Routing Decision ---

class RoutingDecision(BaseModel):
    skill_ref: str
    decision_stability: str  # "exact", "approximate", "tie_break_*", "conflict_*", etc.
    estimated_cost: Optional[Dict[str, Any]] = None
    approximate: bool = False
    tie_break_applied: bool = False
    safety_clearance: str = "allow"
    trace_events: List[Dict[str, Any]] = []

# --- Safe Fallback Response ---

class SafeFallbackResponse(BaseModel):
    refusal: bool = True
    reason_code: str
    message: str
    safe_alternative: Optional[str] = None
    clarify: Optional[str] = None
    trace_events: List[Dict[str, Any]] = []

# --- Degrade Transition ---

class DegradeTransition(BaseModel):
    from_level: str  # D0, D1, D2, D3
    to_level: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    cooldown_until: Optional[str] = None  # ISO 8601
    reason: Optional[str] = None
    trigger: Literal["cpu", "ram", "manual", "cascade"] = "manual"

# --- Delivery Contract ---

class DeliveryContract(BaseModel):
    skill_ref: str
    ttl_seconds: int = 300  # 5 min default
    freshness: Literal["fresh", "stale", "expired"] = "fresh"
    issued_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    max_retries: int = 3
    idempotency_key: Optional[str] = None

# --- Trace Event ---

class TraceEvent(BaseModel):
    code: str
    stage_attempted: Any  # str or int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    context: Optional[Dict[str, Any]] = None
    min_count: Optional[int] = None
    max_count: Optional[int] = None

# --- Anomaly Profile ---

class AnomalyProfile(BaseModel):
    anomaly_type: str  # "distribution_shift", "model_drift_detected", etc.
    anomaly_confidence: float
    kl_divergence: Optional[float] = None
    lexical_distribution: Optional[List[float]] = None
    semantic_distribution: Optional[List[float]] = None
    threshold: float = 0.5
    action_taken: Literal["block", "warn", "pass"] = "warn"

# --- Conformance Report ---

class ConformanceReport(BaseModel):
    protocol_version: str = "OSP/1.0"
    server_version: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[Dict[str, Any]] = []

