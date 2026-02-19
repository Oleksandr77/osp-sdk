import math
from collections import Counter
from typing import List, Dict, Any

class BM25Scorer:
    """
    Implements Okapi BM25 ranking algorithm for Skill Routing.
    
    References:
    - Robertson, S. E., Walker, S., Jones, S., Hancock-Beaulieu, M. M., & Gatford, M. (1995).
      Okapi at TREC-3. NIST Special Publication 500-225, 109-126.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.corpus = []
        
    def fit(self, corpus: List[List[str]]):
        """
        Fits the BM25 model to the given corpus (list of tokenized documents).
        """
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # Calculate TF and DF
        df = {}
        for doc in corpus:
            distinct_tokens = set(doc)
            for token in distinct_tokens:
                df[token] = df.get(token, 0) + 1
        
        # Calculate IDF
        self.idf = {}
        for token, freq in df.items():
            # IDF formula: log((N - n + 0.5) / (n + 0.5) + 1)
            self.idf[token] = math.log(((self.corpus_size - freq + 0.5) / (freq + 0.5)) + 1)
            
    def score(self, query: List[str], index: int) -> float:
        """
        Calculates the BM25 score for a specific document index against the query.
        """
        score = 0.0
        doc_len = self.doc_len[index]
        doc = self.corpus[index]
        doc_counter = Counter(doc)
        
        for token in query:
            if token not in self.corpus[index]:
                continue
                
            freq = doc_counter[token]
            idf = self.idf.get(token, 0)
            
            # BM25 formula
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
            
            score += idf * (numerator / denominator)
            
        return score

    def search(self, query: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Returns top_k document indices and scores.
        """
        scores = []
        for i in range(self.corpus_size):
            s = self.score(query, i)
            if s > 0:
                scores.append({"index": i, "score": s})
        
        # Sort by score descending
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
