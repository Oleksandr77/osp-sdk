from typing import List, Dict, Any
import re
from .bm25 import BM25Scorer

class DeterministicRouter:
    """
    Stage 1 Router: Lexical Matching via BM25.
    Filters skills based on statistical relevance of name, description, and keywords.
    """
    
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())
    
    def filter_candidates(self, query: str, skills: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Returns a list of skills that match the query using BM25 scoring.
        """
        if not skills:
            return []
            
        # 1. Prepare Corpus
        # Combine name, description, and keywords into a "document" for each skill
        corpus = []
        for skill in skills:
            # Boost keywords by repeating them? Or just concat.
            # Let's concat: name (1x) + description (1x) + keywords (3x boost)
            name = skill.get("name", "")
            desc = skill.get("description", "")
            keywords = " ".join(skill.get("activation_keywords", []))
            
            # Simple "document" construction
            full_text = f"{name} {desc} {keywords} {keywords} {keywords}"
            corpus.append(self._tokenize(full_text))
            
        # 2. Fit BM25
        scorer = BM25Scorer()
        scorer.fit(corpus)
        
        # 3. Score Query
        query_tokens = self._tokenize(query)
        results = scorer.search(query_tokens, top_k=top_k)
        
        # 4. Map back to skills
        candidates = []
        for res in results:
            idx = res["index"]
            score = res["score"]
            skill = skills[idx]
            # Inject score for debugging/Stage 2
            skill["_routing_score"] = score
            candidates.append(skill)
            
        return candidates
