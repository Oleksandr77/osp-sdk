"""
OSP Registry Service Tests
============================
Tests for skill registration, revocation, trust chain verification,
and append-only transparency log.
"""

import os
import sys
import unittest
import hashlib

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from osp_server.logic.registry import RegistryService


def _make_entry(skill_ref="org.test.calculator", entry_type="REGISTER",
                signed_by="test-signer", alg="ES256",
                trust_type="self_signed"):
    """Helper to create a valid registry entry."""
    content = f"{skill_ref}:{entry_type}:v1.0"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return {
        "entry_type": entry_type,
        "skill_ref": skill_ref,
        "signed_by": signed_by,
        "content_hash": content_hash,
        "signature": "MEUCIQD" + "A" * 80 + "==",  # Mock base64 signature
        "alg": alg,
        "trust_anchor": {
            "type": trust_type,
        },
    }


class TestRegistryService(unittest.TestCase):
    """Test the RegistryService."""

    def setUp(self):
        self.registry = RegistryService()

    # ── Registration ────────────────────────────────────

    def test_register_skill_valid(self):
        """A valid entry should register successfully."""
        entry = _make_entry()
        result = self.registry.register(entry)
        self.assertEqual(result["status"], "registered")
        self.assertEqual(result["skill_ref"], "org.test.calculator")

    def test_register_invalid_entry_type(self):
        """Invalid entry_type should be rejected."""
        entry = _make_entry(entry_type="INVALID")
        result = self.registry.register(entry)
        self.assertIn("error", result)

    def test_register_missing_skill_ref(self):
        """Missing skill_ref should be rejected."""
        entry = _make_entry()
        entry["skill_ref"] = ""
        result = self.registry.register(entry)
        self.assertIn("error", result)

    def test_register_invalid_content_hash(self):
        """Invalid content_hash should be rejected."""
        entry = _make_entry()
        entry["content_hash"] = "short"
        result = self.registry.register(entry)
        self.assertIn("error", result)

    def test_register_missing_signature(self):
        """Missing signature should be rejected."""
        entry = _make_entry()
        entry["signature"] = ""
        result = self.registry.register(entry)
        self.assertIn("error", result)

    def test_register_multiple_skills(self):
        """Multiple skills should coexist in the registry."""
        e1 = _make_entry(skill_ref="org.test.a")
        e2 = _make_entry(skill_ref="org.test.b")
        self.registry.register(e1)
        self.registry.register(e2)

        entries = self.registry.list_entries()
        refs = [e["skill_ref"] for e in entries]
        self.assertIn("org.test.a", refs)
        self.assertIn("org.test.b", refs)

    # ── Revocation ──────────────────────────────────────

    def test_revoke_skill(self):
        """Revoking a registered skill should mark it as revoked."""
        entry = _make_entry(skill_ref="org.test.revokable")
        self.registry.register(entry)

        result = self.registry.revoke("org.test.revokable", "test-signer")
        self.assertEqual(result["status"], "revoked")

    def test_revoke_not_found(self):
        """Revoking a non-existent skill should error."""
        result = self.registry.revoke("org.test.nonexistent", "test-signer")
        self.assertIn("error", result)

    def test_revoke_unauthorized(self):
        """Only the original signer can revoke."""
        entry = _make_entry(skill_ref="org.test.protected", signed_by="alice")
        self.registry.register(entry)

        result = self.registry.revoke("org.test.protected", "bob")
        self.assertIn("error", result)
        self.assertIn("Unauthorized", result["error"])

    def test_register_after_revoke_rejected(self):
        """Re-registering a revoked skill should be rejected."""
        entry = _make_entry(skill_ref="org.test.once")
        self.registry.register(entry)
        self.registry.revoke("org.test.once", "test-signer")

        result = self.registry.register(_make_entry(skill_ref="org.test.once"))
        self.assertIn("error", result)
        self.assertIn("revoked", result["error"])

    # ── Trust Chain Verification ────────────────────────

    def test_trust_chain_self_signed(self):
        """Self-signed trust should always be accepted."""
        entry = _make_entry(trust_type="self_signed")
        result = self.registry.verify_trust_chain(entry)
        self.assertTrue(result["valid"])
        self.assertEqual(result["trust_level"], "self_signed")

    def test_trust_chain_root_ca(self):
        """Root CA trust requires a URI."""
        entry = _make_entry()
        entry["trust_anchor"] = {"type": "root_ca", "uri": "https://ca.example.com/root.pem"}
        result = self.registry.verify_trust_chain(entry)
        self.assertTrue(result["valid"])

    def test_trust_chain_root_ca_missing_uri(self):
        """Root CA without URI should fail."""
        entry = _make_entry()
        entry["trust_anchor"] = {"type": "root_ca"}
        result = self.registry.verify_trust_chain(entry)
        self.assertFalse(result["valid"])

    def test_trust_chain_did(self):
        """DID trust requires did: prefix."""
        entry = _make_entry()
        entry["trust_anchor"] = {"type": "did", "uri": "did:key:z6MkhaXg..."}
        result = self.registry.verify_trust_chain(entry)
        self.assertTrue(result["valid"])

    def test_trust_chain_did_invalid(self):
        """DID without did: prefix should fail."""
        entry = _make_entry()
        entry["trust_anchor"] = {"type": "did", "uri": "https://example.com"}
        result = self.registry.verify_trust_chain(entry)
        self.assertFalse(result["valid"])

    def test_trust_chain_intermediate_ca(self):
        """Intermediate CA requires both URI and proof."""
        entry = _make_entry()
        entry["trust_anchor"] = {
            "type": "intermediate_ca",
            "uri": "https://ca.example.com/intermediate.pem",
            "proof": "MEUCIQD...",
        }
        result = self.registry.verify_trust_chain(entry)
        self.assertTrue(result["valid"])

    def test_trust_chain_missing(self):
        """Missing trust anchor should fail."""
        entry = _make_entry()
        entry.pop("trust_anchor")
        result = self.registry.verify_trust_chain(entry)
        self.assertFalse(result["valid"])

    # ── Transparency Log ────────────────────────────────

    def test_transparency_log_append_only(self):
        """Each operation should append to the transparency log."""
        e1 = _make_entry(skill_ref="org.test.log1")
        e2 = _make_entry(skill_ref="org.test.log2")
        self.registry.register(e1)
        self.registry.register(e2)

        log = self.registry.get_transparency_log()
        self.assertEqual(log["total"], 2)
        self.assertEqual(log["entries"][0]["event_type"], "REGISTERED")
        self.assertEqual(log["entries"][1]["event_type"], "REGISTERED")

    def test_transparency_log_has_hash_chain(self):
        """Each log entry should reference the previous entry's hash."""
        e1 = _make_entry(skill_ref="org.test.chain1")
        e2 = _make_entry(skill_ref="org.test.chain2")
        self.registry.register(e1)
        self.registry.register(e2)

        log = self.registry.get_transparency_log()
        self.assertEqual(log["entries"][0]["prev_hash"], "0" * 64)  # Genesis
        self.assertNotEqual(log["entries"][1]["prev_hash"], "0" * 64)  # Chained

    def test_transparency_log_includes_revocation(self):
        """Revocation should also appear in the transparency log."""
        entry = _make_entry(skill_ref="org.test.revlog")
        self.registry.register(entry)
        self.registry.revoke("org.test.revlog", "test-signer")

        log = self.registry.get_transparency_log()
        events = [e["event_type"] for e in log["entries"]]
        self.assertIn("REGISTERED", events)
        self.assertIn("REVOKED", events)

    def test_transparency_log_pagination(self):
        """Log pagination should work correctly."""
        for i in range(5):
            self.registry.register(_make_entry(skill_ref=f"org.test.page{i}"))

        page1 = self.registry.get_transparency_log(limit=2, offset=0)
        page2 = self.registry.get_transparency_log(limit=2, offset=2)

        self.assertEqual(len(page1["entries"]), 2)
        self.assertEqual(len(page2["entries"]), 2)
        self.assertEqual(page1["total"], 5)

    # ── Get / List ──────────────────────────────────────

    def test_get_entry(self):
        """get_entry should return the registered entry."""
        entry = _make_entry(skill_ref="org.test.get")
        self.registry.register(entry)
        result = self.registry.get_entry("org.test.get")
        self.assertIsNotNone(result)
        self.assertEqual(result["skill_ref"], "org.test.get")

    def test_get_entry_not_found(self):
        """get_entry for unknown skill should return None."""
        result = self.registry.get_entry("org.test.notfound")
        self.assertIsNone(result)

    def test_list_entries_filter_active(self):
        """list_entries should filter by status."""
        self.registry.register(_make_entry(skill_ref="org.test.active"))
        self.registry.register(_make_entry(skill_ref="org.test.willrevoke"))
        self.registry.revoke("org.test.willrevoke", "test-signer")

        active = self.registry.list_entries(status="active")
        revoked = self.registry.list_entries(status="revoked")

        active_refs = [e["skill_ref"] for e in active]
        self.assertIn("org.test.active", active_refs)
        self.assertNotIn("org.test.willrevoke", active_refs)
        self.assertEqual(len(revoked), 1)


if __name__ == "__main__":
    unittest.main()
