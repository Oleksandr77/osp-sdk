"""
OSP Delivery Contract Enforcement
===================================
Implements TTL tracking, freshness lifecycle, idempotency keys,
and an append-only proof log for auditable skill execution.

Spec reference: DeliveryContract schema (JSON Schema Draft 2020-12)
"""

import uuid
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from collections import OrderedDict

logger = logging.getLogger("osp.delivery")


class DeliveryContractEnforcer:
    """
    Manages delivery contracts for skill execution.

    Each execution is wrapped in a contract that tracks:
      - TTL (time-to-live) in seconds
      - Freshness state: fresh → stale → expired
      - Idempotency key for deduplication
      - Proof log for auditability
    """

    # Maximum contracts to keep in memory (LRU eviction)
    MAX_CONTRACTS = 1000
    MAX_PROOF_LOG = 5000

    def __init__(self):
        # Active contracts: idempotency_key → contract dict
        self._contracts: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        # Append-only proof log
        self._proof_log: List[Dict[str, Any]] = []

    # ── Contract Lifecycle ──────────────────────────────

    def issue_contract(
        self,
        skill_ref: str,
        ttl_seconds: int = 300,
        max_retries: int = 3,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Issue a new delivery contract for a skill execution.

        Returns a contract dict matching the DeliveryContract schema.
        """
        now = datetime.now(timezone.utc)
        key = idempotency_key or str(uuid.uuid4())

        # Idempotency check: if contract already exists and is fresh/stale, return it
        if key in self._contracts:
            existing = self._contracts[key]
            freshness = self._compute_freshness(existing)
            if freshness != "expired":
                existing["freshness"] = freshness
                logger.info(f"Idempotent hit: {key} (freshness={freshness})")
                return existing

        contract = {
            "skill_ref": skill_ref,
            "ttl_seconds": ttl_seconds,
            "freshness": "fresh",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            "max_retries": max_retries,
            "idempotency_key": key,
            "retries_used": 0,
            "execution_result": None,
            "execution_status": "pending",
        }

        # LRU eviction
        if len(self._contracts) >= self.MAX_CONTRACTS:
            self._contracts.popitem(last=False)

        self._contracts[key] = contract

        self._append_proof("CONTRACT_ISSUED", key, {
            "skill_ref": skill_ref,
            "ttl_seconds": ttl_seconds,
        })

        logger.info(f"Contract issued: {key} for {skill_ref} (TTL={ttl_seconds}s)")
        return contract

    def validate_contract(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a contract's freshness state.

        Returns the contract with updated freshness field.
        """
        freshness = self._compute_freshness(contract)
        contract["freshness"] = freshness
        return contract

    def execute_with_contract(
        self,
        skill_ref: str,
        execute_fn,
        arguments: Dict[str, Any],
        ttl_seconds: int = 300,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a skill with delivery contract enforcement.

        1. Issue contract
        2. Validate freshness (abort if expired)
        3. Execute skill
        4. Record proof
        5. Return result with contract metadata
        """
        contract = self.issue_contract(
            skill_ref=skill_ref,
            ttl_seconds=ttl_seconds,
            idempotency_key=idempotency_key,
        )
        key = contract["idempotency_key"]

        # Check if already executed (idempotency)
        if contract["execution_status"] == "completed":
            self._append_proof("IDEMPOTENT_RETURN", key, {
                "reason": "already_executed",
            })
            return {
                "result": contract["execution_result"],
                "contract": contract,
                "idempotent": True,
            }

        # Validate freshness
        contract = self.validate_contract(contract)
        if contract["freshness"] == "expired":
            self._append_proof("CONTRACT_EXPIRED", key, {
                "skill_ref": skill_ref,
            })
            return {
                "error": "Contract expired before execution",
                "contract": contract,
            }

        # Execute with retry logic
        last_error = None
        max_retries = contract["max_retries"]

        for attempt in range(max_retries + 1):
            try:
                t0 = time.time()
                result = execute_fn(arguments)
                elapsed_ms = round((time.time() - t0) * 1000, 2)

                # Success
                contract["execution_result"] = result
                contract["execution_status"] = "completed"
                contract["freshness"] = self._compute_freshness(contract)

                self._append_proof("EXECUTION_SUCCESS", key, {
                    "skill_ref": skill_ref,
                    "attempt": attempt + 1,
                    "latency_ms": elapsed_ms,
                })

                return {
                    "result": result,
                    "contract": contract,
                    "status": "success",
                }

            except Exception as e:
                last_error = str(e)
                contract["retries_used"] = attempt + 1
                self._append_proof("EXECUTION_RETRY", key, {
                    "skill_ref": skill_ref,
                    "attempt": attempt + 1,
                    "error": last_error,
                })
                logger.warning(f"Execution attempt {attempt + 1} failed: {e}")

        # All retries exhausted
        contract["execution_status"] = "failed"
        self._append_proof("EXECUTION_FAILED", key, {
            "skill_ref": skill_ref,
            "retries_exhausted": max_retries + 1,
            "last_error": last_error,
        })

        return {
            "error": f"Execution failed after {max_retries + 1} attempts: {last_error}",
            "contract": contract,
            "status": "failed",
        }

    def get_proof(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Get the full audit trail for a delivery contract.

        Returns contract + all related proof log entries, or None if not found.
        """
        contract = self._contracts.get(idempotency_key)
        if not contract:
            return None

        # Refresh freshness
        contract["freshness"] = self._compute_freshness(contract)

        # Collect all proof entries for this key
        proof_entries = [
            entry for entry in self._proof_log
            if entry.get("idempotency_key") == idempotency_key
        ]

        return {
            "contract": contract,
            "proof_log": proof_entries,
            "total_events": len(proof_entries),
        }

    def get_all_proofs(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get paginated proof log for transparency.
        """
        total = len(self._proof_log)
        entries = self._proof_log[offset:offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": entries,
        }

    # ── Internal Helpers ────────────────────────────────

    def _compute_freshness(self, contract: Dict[str, Any]) -> str:
        """
        Compute the freshness of a contract based on its TTL.

        - fresh: < 80% of TTL elapsed
        - stale: 80-100% of TTL elapsed
        - expired: > 100% of TTL elapsed
        """
        expires_at_str = contract.get("expires_at")
        if not expires_at_str:
            return "expired"

        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Ensure timezone-aware comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)

            if now >= expires_at:
                return "expired"

            issued_at_str = contract.get("issued_at", "")
            issued_at = datetime.fromisoformat(issued_at_str)
            if issued_at.tzinfo is None:
                issued_at = issued_at.replace(tzinfo=timezone.utc)

            total_ttl = (expires_at - issued_at).total_seconds()
            elapsed = (now - issued_at).total_seconds()

            if total_ttl <= 0:
                return "expired"

            ratio = elapsed / total_ttl
            if ratio < 0.8:
                return "fresh"
            else:
                return "stale"

        except (ValueError, TypeError):
            return "expired"

    def _append_proof(self, event_type: str, idempotency_key: str, context: Dict[str, Any]) -> None:
        """Append an entry to the proof log (bounded)."""
        entry = {
            "event_type": event_type,
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context,
        }
        self._proof_log.append(entry)

        # Evict old entries if log is too large
        if len(self._proof_log) > self.MAX_PROOF_LOG:
            self._proof_log = self._proof_log[-self.MAX_PROOF_LOG:]

        logger.debug(f"Proof: {event_type} [{idempotency_key}]")
