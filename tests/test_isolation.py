import requests
import time
import sys
import os
import json

# Add project root to path for crypto
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
try:
    from osp_core.crypto import JCS
except ImportError:
    print("Cannot import JCS. Ensure you run this from project root or set valid PYTHONPATH.")
    sys.exit(1)

BASE_URL = "http://localhost:8000"

def run_tests():
    print("🚀 Starting Plane Isolation Tests...")
    
    # 1. Fetch Keys
    print("🔑 Fetching Debug Keys...")
    resp = requests.get(f"{BASE_URL}/admin/debug/keys")
    if resp.status_code != 200:
        print(f"❌ Failed to get keys: {resp.status_code}")
        return
        
    keys = resp.json()
    priv_pem = keys["private_key"].encode('utf-8')
    pub_pem = keys["public_key"].encode('utf-8')
    print("   ✅ Keys fetched.")

    # 2. Prepare Valid Request
    payload = {
        "jsonrpc": "2.0",
        "method": "osp.execute",
        "params": {
            "skill_id": "org.antigravity.youtube.analyzer",
            "arguments": {"url": "https://youtube.com/watch?v=signed123"}
        },
        "id": "test-sig-1"
    }
    
    # 3. Sign it
    print("📝 Signing Request...")
    # Ideally sign the JSON bytes exactly as sent.
    # Here we rely on JCS canonicalization both sides.
    # Note: requests.post(json=...) serializes. We need to match that or use data=bytes.
    # To be safe: Serialize first.
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Wait, JCS.sign takes an object and canonicalizes it.
    # The server parses JSON, then passes bytes? 
    # The middleware in server.py does: `data = json.loads(body_bytes); is_valid = JCS.verify(data, ...)`
    # So `JCS.verify` will recalculate canonical form of `data`.
    # So we just need to sign the object.
    signature = JCS.sign(payload, priv_pem, "ES256")
    print(f"   Signature: {signature[:20]}...")

    # 4. Send Signed Request
    print("📨 Sending Signed Request...")
    headers = {"X-OSP-Signature": signature}
    resp = requests.post(f"{BASE_URL}/asp-rpc", json=payload, headers=headers)
    
    if resp.status_code == 200:
        print("   ✅ Valid Signature Accepted.")
    else:
        print(f"   ❌ Valid Signature Rejected: {resp.status_code} {resp.text}")

    # 5. Send Unsigned Request (Should FAIL in Strict Mode)
    print("📨 Sending Unsigned Request (Strict Mode Check)...")
    resp_unsigned = requests.post(f"{BASE_URL}/asp-rpc", json=payload)
    if resp_unsigned.status_code == 401:
        print("   ✅ Unsigned Rejected (Expected for Strict Mode).")
    else:
        print(f"   ❌ Unsigned NOT Rejected: {resp_unsigned.status_code} (Expected 401)")

    # 6. Send Invalid Signature
    print("📨 Sending Invalid Signature...")
    bad_headers = {"X-OSP-Signature": "badsignature123"}
    resp_bad = requests.post(f"{BASE_URL}/asp-rpc", json=payload, headers=bad_headers)
    
    if resp_bad.status_code == 401:
        print("   ✅ Invalid Signature Rejected (Expected 401).")
    else:
        print(f"   ❌ Invalid Signature NOT Rejected: {resp_bad.status_code}")

if __name__ == "__main__":
    time.sleep(2)
    run_tests()
