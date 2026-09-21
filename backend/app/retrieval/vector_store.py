import json
import os
import re
import math
from typing import Any, Dict, List, Optional, Set
from collections import Counter

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}


def _find_cache_file() -> str:
    """Resolve vector_cache.json path across local, monorepo, and container environments."""
    if "VECTOR_CACHE_FILE" in os.environ and os.path.exists(os.environ["VECTOR_CACHE_FILE"]):
        return os.environ["VECTOR_CACHE_FILE"]

    candidates = [
        # Project root
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "vector_cache.json")),
        # Backend folder
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vector_cache.json")),
        # Docker container standard paths
        "/app/vector_cache.json",
        "/app/backend/vector_cache.json",
        "vector_cache.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


CHUNKS_CACHE_FILE = _find_cache_file()


def tokenize(text: str) -> List[str]:
    """Tokenize text into lower-case alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Retriever:
    """
    High-accuracy, deterministic BM25 search engine with metadata field boosting,
    stopword filtering, and query term coverage validation.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.total_docs: int = 0
        self.doc_term_freqs: List[Counter] = []

    def fit(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.total_docs = len(documents)
        self.doc_lengths = []
        self.doc_term_freqs = []
        self.doc_freqs = {}

        if not documents:
            self.avg_doc_len = 0.0
            return

        total_len = 0
        for doc in documents:
            text = f"{doc.get('source_title', '')} {doc.get('guest', '')} {doc.get('content', '')}"
            tokens = [t for t in tokenize(text) if t not in STOPWORDS]
            length = len(tokens)
            self.doc_lengths.append(length)
            total_len += length

            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)

            for token in tf.keys():
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = total_len / max(1, self.total_docs)

    def idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

    def score(self, query: str) -> List[float]:
        raw_tokens = tokenize(query)
        if not raw_tokens or self.total_docs == 0:
            return [0.0] * self.total_docs

        # Filter query tokens using stopwords
        q_tokens = [t for t in raw_tokens if t not in STOPWORDS]
        if not q_tokens:
            q_tokens = raw_tokens

        unique_q_tokens = set(q_tokens)
        scores = [0.0] * self.total_docs
        matched_terms: List[Set[str]] = [set() for _ in range(self.total_docs)]

        for token in q_tokens:
            token_idf = self.idf(token)
            if token_idf <= 0:
                continue

            for idx in range(self.total_docs):
                tf = self.doc_term_freqs[idx].get(token, 0)
                if tf == 0:
                    continue

                matched_terms[idx].add(token)
                doc_len = self.doc_lengths[idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len)))
                term_score = token_idf * ((tf * (self.k1 + 1.0)) / denom)

                # Metadata boosting: give outsized weight when query matches the speaker or episode topic
                doc = self.documents[idx]
                if token in tokenize(doc.get("guest", "")):
                    term_score *= 2.5
                elif token in tokenize(doc.get("source_title", "")):
                    term_score *= 1.8

                scores[idx] += term_score

        # Query Term Coverage Guard:
        # If the user asked a multi-term question (>= 3 terms), matching only 1 single term
        # (e.g. matching only "change" in "how to change transmission fluid on civic")
        # is an accidental lexical match, not topical relevance.
        min_terms_required = 2 if len(unique_q_tokens) >= 3 else 1
        for idx in range(self.total_docs):
            if len(matched_terms[idx]) < min_terms_required:
                scores[idx] = 0.0

        return scores


class VectorStore:
    """
    Persistent vector and document store with metadata-boosted ranking,
    term coverage validation, and similarity thresholding.
    """

    def __init__(self, cache_file: str = CHUNKS_CACHE_FILE):
        self.cache_file = os.path.abspath(cache_file)
        self.retriever = BM25Retriever()
        self.documents: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        """Load indexed chunks from disk cache if present."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.retriever.fit(self.documents)
            except Exception:
                self.documents = []

    def save(self):
        """Save indexed documents to disk."""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        data = {
            "documents": self.documents,
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_documents(self, chunks: List[Dict[str, Any]]):
        """Add new chunks and re-index."""
        existing_ids = {doc["id"] for doc in self.documents}
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]

        if not new_chunks:
            self.retriever.fit(self.documents)
            return

        self.documents.extend(new_chunks)
        self.retriever.fit(self.documents)
        self.save()

    def clear(self):
        """Clear all indexed documents."""
        self.documents = []
        self.retriever.fit([])
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except OSError:
                pass

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> List[Dict[str, Any]]:
        """
        Search top-k most relevant chunks using boosted BM25.
        Enforces min_score threshold: if scores fall below min_score, returns [] (triggering refusal).
        """
        if not self.documents or not query.strip():
            return []

        scores = self.retriever.score(query)
        scored_pairs = list(enumerate(scores))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored_pairs[:top_k]:
            if score >= min_score:
                doc_copy = dict(self.documents[idx])
                doc_copy["score"] = round(float(score), 4)
                results.append(doc_copy)

        return results


# Global vector store instance
vector_store = VectorStore()
