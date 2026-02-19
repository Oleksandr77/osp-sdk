import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))
from ai_core.routing.deterministic import DeterministicRouter

def test_router():
    router = DeterministicRouter()
    
    skills = [
        {
            "id": "youtube",
            "activation_keywords": ["youtube", "video"]
        },
        {
            "id": "drive",
            "activation_keywords": ["drive", "file"]
        }
    ]
    
    # Case 1: Youtube
    candidates = router.filter_candidates("I want to watch a youtube video", skills)
    print(f"Query: 'youtube video' -> Candidates: {[s['id'] for s in candidates]}")
    assert len(candidates) == 1
    assert candidates[0]['id'] == 'youtube'
    
    # Case 2: Drive
    candidates = router.filter_candidates("find file in drive", skills)
    print(f"Query: 'find file' -> Candidates: {[s['id'] for s in candidates]}")
    assert len(candidates) == 1
    assert candidates[0]['id'] == 'drive'
    
    # Case 3: No match
    candidates = router.filter_candidates("cook dinner", skills)
    print(f"Query: 'cook dinner' -> Candidates: {[s['id'] for s in candidates]}")
    assert len(candidates) == 0

if __name__ == "__main__":
    try:
        test_router()
        print("✅ Router Tests Passed!")
    except AssertionError as e:
        print(f"❌ Router Tests Failed: {e}")
