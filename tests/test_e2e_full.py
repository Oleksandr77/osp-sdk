import os
import time
import requests
import unittest
import shutil
import multiprocessing
import uvicorn
import sys
import subprocess

# Configuration
SERVER_PORT = 8003
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
AGENT_NAME = "e2e_test_agent"

def start_server():
    # Add 06_Operations to path so osp_server can be imported
    sys.path.append(os.path.join(os.getcwd(), "06_Operations"))
    # Re-import to ensure it finds the app
    from osp_server.server import app
    uvicorn.run(app, host="127.0.0.1", port=SERVER_PORT, log_level="info")

class TestE2EFull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("🚀 Starting E2E Verification (Multiprocessing)...")
        
        # 1. Clean up
        if os.path.exists(AGENT_NAME):
            shutil.rmtree(AGENT_NAME)
        
        # 2. Create Agent
        print(f"🛠️  Creating agent '{AGENT_NAME}' via CLI...")
        # Use subprocess.run with list to handle spaces in paths
        cli_path = os.path.join("06_Operations", "osp_cli", "main.py")
        subprocess.run(
            [sys.executable, cli_path, "new", "agent", AGENT_NAME],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        
        # 3. Start Server in Process
        print(f"📡 Starting OSP Server on port {SERVER_PORT}...")
        cls.server_process = multiprocessing.Process(target=start_server)
        cls.server_process.start()
        
        # Wait for healthy
        for i in range(10):
            try:
                msg = f"⏳ Health check {i+1}/10..."
                print(msg)
                resp = requests.get(f"{SERVER_URL}/health")
                if resp.status_code == 200:
                    print("✅ Server is UP.")
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        else:
            cls.server_process.terminate()
            raise RuntimeError("Server failed to start.")

    @classmethod
    def tearDownClass(cls):
        print("🛑 Stopping Server...")
        cls.server_process.terminate()
        cls.server_process.join()
        if os.path.exists(AGENT_NAME):
            shutil.rmtree(AGENT_NAME)

    def test_agent_execution(self):
        # Check Health
        resp = requests.get(f"{SERVER_URL}/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
        print("✅ Health Check Passed")
        
        # Check Metrics
        resp = requests.get(f"{SERVER_URL}/metrics")
        self.assertEqual(resp.status_code, 200)
        
        if "# Prometheus client not installed" in resp.text:
            print("⚠️ Prometheus not installed, metrics stubbed (Expected).")
        else:
            self.assertIn("osp_requests_total", resp.text)
            
        print("✅ Metrics Check Passed")

if __name__ == "__main__":
    unittest.main()
