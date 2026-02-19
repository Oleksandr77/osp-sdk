import unittest
from fastapi.testclient import TestClient
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.main import app, system

class TestKnowledge(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Ensure Vector DB is ready (even if mocked or real)
        if not system.agent_manager.vector_db:
             from ai_core.vector_handler import VectorHandler
             system.agent_manager.vector_db = VectorHandler()

    def test_knowledge_page(self):
        response = self.client.get("/knowledge")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Knowledge Base", response.text)

    def test_upload_document(self):
        filename = "test_knowledge_doc.txt"
        content = b"This is a secret knowledge document about Project X."
        
        files = {'file': (filename, content, 'text/plain')}
        
        response = self.client.post("/api/knowledge/upload", files=files)
        self.assertEqual(response.status_code, 200)
        
        json_resp = response.json()
        self.assertEqual(json_resp["status"], "success")
        self.assertTrue("doc_id" in json_resp)
        
        # Verify it's searchable (if real DB)
        if system.agent_manager.vector_db:
             results = system.agent_manager.vector_db.search("Project X")
             # We might not get it immediately if async/indexing, but Chroma is usually sync
             found = any("Project X" in r['text'] for r in results)
             self.assertTrue(found)

        print("Knowledge Endpoint Verified!")

if __name__ == '__main__':
    unittest.main()
