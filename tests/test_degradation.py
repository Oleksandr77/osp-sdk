import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def set_degradation(level):
    print(f"\n🔧 Setting Degradation Level to {level}...")
    try:
        resp = requests.post(f"{BASE_URL}/admin/degradation", json={"level": level})
        print(f"   Response: {resp.status_code} {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"   Failed to set level: {e}")
        return False

def test_agent_execution(session_id, query, expect_failure=False):
    print(f"🧪 Testing Query: '{query}' (Expect Failure: {expect_failure})")
    try:
        resp = requests.post(f"{BASE_URL}/osp-agent/execute", json={
            "session_id": session_id,
            "input_text": query
        })
        
        if expect_failure:
            if resp.status_code == 503:
                print("   ✅ Correctly received 503 Service Unavailable")
            else:
                print(f"   ❌ Expected 503, got {resp.status_code}")
        else:
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("message", "")
                print(f"   ✅ Success. Message: {msg}")
                # Check if message indicates degraded routing
                if "Degraded Routing" in msg:
                    print("   🔍 Verified: Used Degraded Routing (No LLM)")
                elif "Hybrid Routing" in msg:
                    print("   🔍 Verified: Used Hybrid Routing (LLM)")
            else:
                print(f"   ❌ Failed: {resp.status_code} {resp.text}")
                
    except Exception as e:
        print(f"   Error: {e}")

def run_tests():
    # 1. Start Agent
    print("🚀 Starting Agent Session...")
    try:
        resp = requests.post(f"{BASE_URL}/osp-agent/start", json={
            "expertise_profile": {"name": "TestAgent", "persona": {"system_prompt": "You are a test agent."}}
        })
        if resp.status_code != 200:
            print("❌ Failed to start agent")
            return
        session_id = resp.json()["session_id"]
        print(f"   Session ID: {session_id}")
    except Exception as e:
        print(f"❌ Server likely not running: {e}")
        return

    # 2. Test D0 (Normal)
    if set_degradation("D0_NORMAL"):
        test_agent_execution(session_id, "analyze youtube https://youtube.com/watch?v=123")
    
    # 3. Test D1 (Reduced - No LLM)
    if set_degradation("D1_REDUCED_INTELLIGENCE"):
        test_agent_execution(session_id, "analyze youtube https://youtube.com/watch?v=456")
        
    # 4. Test D3 (Critical - Load Shedding)
    if set_degradation("D3_CRITICAL"):
        test_agent_execution(session_id, "analyze youtube", expect_failure=True)
        # Verify Start also blocked
        print("🧪 Testing Agent Start (Should fail)...")
        resp = requests.post(f"{BASE_URL}/osp-agent/start", json={"expertise_profile": {}})
        if resp.status_code == 503:
            print("   ✅ Start Blocked (503)")
        else:
            print(f"   ❌ Start Not Blocked: {resp.status_code}")

    # Reset
    set_degradation("D0_NORMAL")

if __name__ == "__main__":
    time.sleep(2) # Wait for server
    run_tests()
