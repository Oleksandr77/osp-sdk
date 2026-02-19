"""
OSP Delivery Contract Tests
============================
Tests for TTL tracking, freshness lifecycle, idempotency, and proof log.
"""

import os
import sys
import time
import unittest

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from osp_server.logic.delivery import DeliveryContractEnforcer


class TestDeliveryContractEnforcer(unittest.TestCase):
    """Test the DeliveryContractEnforcer."""

    def setUp(self):
        self.enforcer = DeliveryContractEnforcer()

    # ── Issue Contract ──────────────────────────────────

    def test_issue_contract_creates_valid_contract(self):
        """A new contract should have all required fields."""
        contract = self.enforcer.issue_contract("org.test.calculator", ttl_seconds=60)

        self.assertEqual(contract["skill_ref"], "org.test.calculator")
        self.assertEqual(contract["ttl_seconds"], 60)
        self.assertEqual(contract["freshness"], "fresh")
        self.assertIn("issued_at", contract)
        self.assertIn("expires_at", contract)
        self.assertIn("idempotency_key", contract)
        self.assertEqual(contract["max_retries"], 3)
        self.assertEqual(contract["execution_status"], "pending")

    def test_issue_contract_custom_idempotency_key(self):
        """A custom idempotency key should be used when provided."""
        contract = self.enforcer.issue_contract("org.test.calc", idempotency_key="my-custom-key")
        self.assertEqual(contract["idempotency_key"], "my-custom-key")

    def test_idempotent_return_same_contract(self):
        """Issuing with the same key should return the existing contract."""
        c1 = self.enforcer.issue_contract("org.test.calc", idempotency_key="key-1")
        c2 = self.enforcer.issue_contract("org.test.calc", idempotency_key="key-1")
        self.assertEqual(c1["idempotency_key"], c2["idempotency_key"])
        self.assertEqual(c1["issued_at"], c2["issued_at"])

    # ── Freshness Lifecycle ─────────────────────────────

    def test_contract_fresh_within_ttl(self):
        """A contract should be 'fresh' when < 80% of TTL has elapsed."""
        contract = self.enforcer.issue_contract("org.test.calc", ttl_seconds=60)
        validated = self.enforcer.validate_contract(contract)
        self.assertEqual(validated["freshness"], "fresh")

    def test_contract_expired_after_ttl(self):
        """A contract should be 'expired' when TTL has fully elapsed."""
        contract = self.enforcer.issue_contract("org.test.calc", ttl_seconds=1)
        # Simulate expiry by waiting
        time.sleep(1.1)
        validated = self.enforcer.validate_contract(contract)
        self.assertEqual(validated["freshness"], "expired")

    # ── Execute with Contract ───────────────────────────

    def test_execute_with_contract_success(self):
        """Successful execution should record proof and return result."""
        def mock_skill(args):
            return {"answer": args.get("x", 0) + args.get("y", 0)}

        result = self.enforcer.execute_with_contract(
            skill_ref="org.test.calc",
            execute_fn=mock_skill,
            arguments={"x": 2, "y": 3},
            ttl_seconds=60,
            idempotency_key="exec-1",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["answer"], 5)
        self.assertEqual(result["contract"]["execution_status"], "completed")

    def test_execute_with_contract_retry_on_failure(self):
        """Execution should retry on failure up to max_retries."""
        call_count = 0

        def flaky_skill(args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return {"ok": True}

        result = self.enforcer.execute_with_contract(
            skill_ref="org.test.flaky",
            execute_fn=flaky_skill,
            arguments={},
            ttl_seconds=60,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(call_count, 3)

    def test_execute_with_contract_all_retries_exhausted(self):
        """If all retries fail, status should be 'failed'."""
        def always_fail(args):
            raise RuntimeError("Always fails")

        result = self.enforcer.execute_with_contract(
            skill_ref="org.test.broken",
            execute_fn=always_fail,
            arguments={},
            ttl_seconds=60,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)

    def test_idempotent_execution_returns_cached(self):
        """Re-executing with same key should return cached result."""
        def mock_skill(args):
            return {"computed": True}

        r1 = self.enforcer.execute_with_contract(
            skill_ref="org.test.calc",
            execute_fn=mock_skill,
            arguments={},
            idempotency_key="idem-2",
        )

        r2 = self.enforcer.execute_with_contract(
            skill_ref="org.test.calc",
            execute_fn=mock_skill,
            arguments={},
            idempotency_key="idem-2",
        )

        self.assertTrue(r2.get("idempotent", False))
        self.assertEqual(r1["result"], r2["result"])

    # ── Proof Log ───────────────────────────────────────

    def test_get_proof_returns_audit_trail(self):
        """Proof should contain contract + all log entries."""
        def mock_skill(args):
            return {"done": True}

        self.enforcer.execute_with_contract(
            skill_ref="org.test.calc",
            execute_fn=mock_skill,
            arguments={},
            idempotency_key="proof-key-1",
        )

        proof = self.enforcer.get_proof("proof-key-1")
        self.assertIsNotNone(proof)
        self.assertIn("contract", proof)
        self.assertIn("proof_log", proof)
        self.assertGreater(proof["total_events"], 0)

    def test_get_proof_not_found(self):
        """Proof for unknown key should return None."""
        proof = self.enforcer.get_proof("nonexistent-key")
        self.assertIsNone(proof)

    def test_get_all_proofs_pagination(self):
        """All proofs should support pagination."""
        def mock_skill(args):
            return {"ok": True}

        for i in range(5):
            self.enforcer.execute_with_contract(
                skill_ref="org.test.calc",
                execute_fn=mock_skill,
                arguments={},
                idempotency_key=f"page-{i}",
            )

        result = self.enforcer.get_all_proofs(limit=3, offset=0)
        self.assertLessEqual(len(result["entries"]), 3)
        self.assertGreater(result["total"], 0)


if __name__ == "__main__":
    unittest.main()
