import unittest
from ai_core.routing.deterministic import DeterministicRouter

class TestRealRouting(unittest.TestCase):
    def setUp(self):
        self.router = DeterministicRouter()
        self.skills = [
            {
                "id": "skill.weather",
                "name": "Weather Reporter",
                "description": "Get current weather forecasts and conditions.",
                "activation_keywords": ["weather", "forecast", "rain", "sun"]
            },
            {
                "id": "skill.finance",
                "name": "Finance Analyst",
                "description": "Analyze stock market trends and prices.",
                "activation_keywords": ["stock", "price", "market", "finance"]
            },
            {
                "id": "skill.joke",
                "name": "Joke Teller",
                "description": "Tell funny jokes and humorous stories.",
                "activation_keywords": ["joke", "funny", "laugh", "humor"]
            }
        ]

    def test_bm25_exact_match(self):
        # "weather" should match skill.weather
        candidates = self.router.filter_candidates("Check the weather", self.skills)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["id"], "skill.weather")
        print(f"Exact Match Score: {candidates[0].get('_routing_score')}")

    def test_bm25_partial_match(self):
        # "Is it going to rain?" -> "rain" is in weather keywords
        candidates = self.router.filter_candidates("Is it going to rain today?", self.skills)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["id"], "skill.weather")

    def test_bm25_description_match(self):
        # "forecasts" is in description of weather (lemmatization not implemented but exact word "forecasts" matches if in desc?)
        # Desc has "forecasts".
        candidates = self.router.filter_candidates("forecasts", self.skills)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["id"], "skill.weather")

    def test_bm25_irrelevant(self):
        # "Banana smoothie" matches nothing
        # BM25 should return empty if score is 0
        candidates = self.router.filter_candidates("Banana smoothie recipe", self.skills)
        self.assertEqual(len(candidates), 0)

if __name__ == '__main__':
    unittest.main()
