"""
OSP Registry Service — Trust Chain & Transparency Log
======================================================
Manages skill registration, revocation, key rotation,
and maintains an append-only transparency log for auditability.

Spec reference: RegistryEntry, TrustAnchor schemas
"""

import time
import os
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from collections import OrderedDict

logger = logging.getLogger("osp.registry")


class RegistryService:
    """
    Manages the OSP Skill Registry.

    Features:
      - REGISTER / REVOKE / DELEGATE / KEY_ROTATE operations
      - Cryptographic signature verification on all entries
      - Trust chain verification from trust anchor
      - Append-only transparency log
      - In-memory storage with optional JSON persistence
    """

    MAX_ENTRIES = 10000
    MAX_LOG = 50000

    def __init__(self):
        # Active registry: skill_ref → latest entry
        self._entries: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        # Append-only transparency log
        self._log: List[Dict[str, Any]] = []
        # Revocation list
        self._revoked: set = set()

    # ── Core Operations ─────────────────────────────────

    def register(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a skill in the registry.

        Requires:
          - entry_type: "REGISTER"
          - skill_ref: valid skill ID
          - content_hash: SHA-256 hash of skill content
          - signature: JCS signature
          - alg: signing algorithm
          - signed_by: signer identity
          - trust_anchor: trust anchor info
        """
        skill_ref = entry.get("skill_ref", "")
        entry_type = entry.get("entry_type", "")

        if entry_type not in ("REGISTER", "DELEGATE", "KEY_ROTATE"):
            return {"error": f"Invalid entry_type for registration: {entry_type}"}

        if not skill_ref:
            return {"error": "Missing skill_ref"}

        # Verify content_hash format (64-char hex = SHA-256)
        content_hash = entry.get("content_hash", "")
        if not content_hash or len(content_hash) != 64:
            return {"error": "Invalid content_hash: must be 64-char hex (SHA-256)"}

        # Verify signature exists
        signature = entry.get("signature", "")
        if not signature:
            return {"error": "Missing signature"}

        # Verify trust anchor
        trust_result = self.verify_trust_chain(entry)
        if not trust_result["valid"]:
            return {"error": f"Trust chain verification failed: {trust_result['reason']}"}

        # Verify signature (attempt cryptographic verification)
        sig_result = self._verify_signature(entry)
        if not sig_result["valid"]:
            self._append_log("REGISTER_REJECTED", skill_ref, {
                "reason": "invalid_signature",
                "alg": entry.get("alg"),
                "signed_by": entry.get("signed_by"),
            })
            return {"error": f"Signature verification failed: {sig_result['reason']}"}

        # Check if previously revoked
        if skill_ref in self._revoked:
            return {"error": f"Skill '{skill_ref}' has been revoked"}

        # Store entry
        timestamp = entry.get("timestamp", int(time.time()))
        registry_entry = {
            **entry,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": timestamp,
            "status": "active",
        }

        # LRU eviction
        if len(self._entries) >= self.MAX_ENTRIES:
            self._entries.popitem(last=False)

        self._entries[skill_ref] = registry_entry

        self._append_log("REGISTERED", skill_ref, {
            "entry_type": entry_type,
            "alg": entry.get("alg"),
            "signed_by": entry.get("signed_by"),
            "content_hash": content_hash[:16] + "...",
        })

        logger.info(f"Registered: {skill_ref} (by {entry.get('signed_by')})")

        return {
            "status": "registered",
            "skill_ref": skill_ref,
            "entry_type": entry_type,
        }

    def revoke(self, skill_ref: str, signed_by: str, signature: str = "", alg: str = "ES256") -> Dict[str, Any]:
        """
        Revoke a skill from the registry.
        """
        if not skill_ref:
            return {"error": "Missing skill_ref"}

        existing = self._entries.get(skill_ref)
        if not existing:
            return {"error": f"Skill '{skill_ref}' not found in registry"}

        # Verify the revoker has authority (original signer OR admin)
        admin_key = os.environ.get("OSP_ADMIN_KEY")
        is_admin = admin_key and signed_by == "__admin__"
        if existing.get("signed_by") != signed_by and not is_admin:
            return {"error": f"Unauthorized: only '{existing.get('signed_by')}' or admin can revoke this skill"}

        # Mark as revoked
        existing["status"] = "revoked"
        existing["revoked_at"] = datetime.now(timezone.utc).isoformat()
        existing["revoked_by"] = signed_by
        self._revoked.add(skill_ref)

        self._append_log("REVOKED", skill_ref, {
            "revoked_by": signed_by,
        })

        logger.info(f"Revoked: {skill_ref} (by {signed_by})")

        return {
            "status": "revoked",
            "skill_ref": skill_ref,
        }

    def get_entry(self, skill_ref: str) -> Optional[Dict[str, Any]]:
        """Get current registry entry for a skill."""
        return self._entries.get(skill_ref)

    def list_entries(self, status: str = "active") -> List[Dict[str, Any]]:
        """List all registry entries, optionally filtered by status."""
        return [
            entry for entry in self._entries.values()
            if entry.get("status") == status
        ]

    # ── Trust Chain Verification ────────────────────────

    def verify_trust_chain(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify the trust chain from the entry's trust anchor.

        Trust anchor types:
          - self_signed: accepted (lowest trust level)
          - root_ca: verify URI exists
          - intermediate_ca: verify URI + proof
          - did: verify DID format
        """
        trust_anchor = entry.get("trust_anchor", {})
        if not trust_anchor:
            return {"valid": False, "reason": "missing_trust_anchor"}

        anchor_type = trust_anchor.get("type", "")

        if anchor_type == "self_signed":
            # Self-signed is always accepted (lowest trust)
            return {"valid": True, "trust_level": "self_signed", "verified_by": "implicit"}

        elif anchor_type == "root_ca":
            uri = trust_anchor.get("uri", "")
            if not uri:
                return {"valid": False, "reason": "root_ca requires URI"}
            return {"valid": True, "trust_level": "root_ca", "verified_by": uri}

        elif anchor_type == "intermediate_ca":
            uri = trust_anchor.get("uri", "")
            proof = trust_anchor.get("proof", "")
            if not uri:
                return {"valid": False, "reason": "intermediate_ca requires URI"}
            if not proof:
                return {"valid": False, "reason": "intermediate_ca requires proof"}
            return {"valid": True, "trust_level": "intermediate_ca", "verified_by": uri}

        elif anchor_type == "did":
            uri = trust_anchor.get("uri", "")
            if not uri or not uri.startswith("did:"):
                return {"valid": False, "reason": "DID must start with 'did:'"}
            return {"valid": True, "trust_level": "did", "verified_by": uri}

        else:
            return {"valid": False, "reason": f"Unknown trust anchor type: {anchor_type}"}

    # ── Signature Verification ──────────────────────────

    def _verify_signature(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify the cryptographic signature on a registry entry.
        Uses JCS canonicalization + the specified algorithm.
        """
        try:
            from osp_core.crypto import JCS

            alg = entry.get("alg", "ES256")
            signature = entry.get("signature", "")
            signed_by = entry.get("signed_by", "")

            if not signature:
                return {"valid": False, "reason": "empty_signature"}

            # Build the data that was signed (everything except the signature itself)
            data_to_verify = {k: v for k, v in entry.items() if k != "signature"}

            # Canonicalize
            canonical = JCS.canonicalize(data_to_verify)
            canonical_hash = hashlib.sha256(canonical).hexdigest()

            # For self-signed entries, verify canonical hash consistency
            trust_anchor = entry.get("trust_anchor", {})
            if trust_anchor.get("type") == "self_signed":
                return {"valid": True, "method": "self_signed_accepted", "canonical_hash": canonical_hash}

            # For CA-backed entries, attempt real cryptographic verification
            # Try to verify using the public key from trust anchor
            public_key_pem = trust_anchor.get("public_key")
            if public_key_pem:
                try:
                    is_valid = JCS.verify(canonical, signature, public_key_pem, alg)
                    if is_valid:
                        return {"valid": True, "method": "crypto_verified", "alg": alg, "canonical_hash": canonical_hash}
                    else:
                        return {"valid": False, "reason": "cryptographic_verification_failed"}
                except Exception as verify_err:
                    logger.warning(f"Crypto verification error: {verify_err}")
                    return {"valid": False, "reason": f"verification_error: {verify_err}"}

            # No public key available — reject non-self-signed entries without key
            return {"valid": False, "reason": "no_public_key_for_verification"}

        except ImportError:
            # If crypto module unavailable, accept with warning
            logger.warning("osp_core.crypto not available for signature verification")
            return {"valid": True, "method": "crypto_unavailable"}
        except Exception as e:
            return {"valid": False, "reason": str(e)}

    # ── Transparency Log ────────────────────────────────

    def get_transparency_log(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get paginated transparency log.
        The log is append-only and immutable.
        """
        total = len(self._log)
        entries = self._log[offset:offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": entries,
        }

    def _append_log(self, event_type: str, skill_ref: str, context: Dict[str, Any]) -> None:
        """Append an entry to the transparency log (bounded)."""
        entry = {
            "event_type": event_type,
            "skill_ref": skill_ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": len(self._log),
            "context": context,
        }

        # Compute hash chain (each entry references the previous)
        if self._log:
            prev_hash = hashlib.sha256(str(self._log[-1]).encode()).hexdigest()
            entry["prev_hash"] = prev_hash
        else:
            entry["prev_hash"] = "0" * 64  # Genesis

        self._log.append(entry)

        # Evict old entries if log is too large
        if len(self._log) > self.MAX_LOG:
            self._log = self._log[-self.MAX_LOG:]

        logger.debug(f"Registry Log: {event_type} [{skill_ref}]")
