import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import numpy as np
from app.models.schemas import Chunk, LegalCategory
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    method: str


class RetrievalService:
    def __init__(self):
        self.settings = get_settings()
        self.bm25 = None
        self.chunks: List[Chunk] = []
        self.embedding_model = None
        self.chunk_embeddings: Optional[np.ndarray] = None

    def index_chunks(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        tokenized = [chunk.text.lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized)

        if not self.settings.enable_embeddings:
            logger.info("Embedding retrieval disabled; using BM25 retrieval.")
            self.embedding_model = None
            self.chunk_embeddings = None
            return

        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            texts = [chunk.text for chunk in chunks]
            self.chunk_embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            logger.info(f"Indexed {len(chunks)} chunks with BM25 and embeddings")
        except Exception as e:
            logger.warning(f"Embedding model not available: {e}")
            self.embedding_model = None
            self.chunk_embeddings = None

    def retrieve_bm25(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        if not self.bm25 or not self.chunks:
            return []

        top_k = top_k or self.settings.retrieval_top_k
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(RetrievalResult(
                    chunk=self.chunks[idx],
                    score=float(scores[idx]),
                    method="bm25",
                ))
        return results

    def retrieve_embedding(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        if self.embedding_model is None or self.chunk_embeddings is None:
            return []

        top_k = top_k or self.settings.retrieval_top_k
        query_embedding = self.embedding_model.encode([query])
        similarities = np.dot(self.chunk_embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append(RetrievalResult(
                    chunk=self.chunks[idx],
                    score=float(similarities[idx]),
                    method="embedding",
                ))
        return results

    def retrieve_hybrid(self, query: str, top_k: int = None, category: LegalCategory = None) -> List[RetrievalResult]:
        top_k = top_k or self.settings.retrieval_top_k

        bm25_results = self.retrieve_bm25(query, top_k * 2)
        embedding_results = self.retrieve_embedding(query, top_k * 2)

        chunk_scores: Dict[str, Dict[str, float]] = {}

        for r in bm25_results:
            chunk_scores[r.chunk.id] = {"bm25": r.score, "embedding": 0.0, "chunk": r.chunk}

        for r in embedding_results:
            if r.chunk.id in chunk_scores:
                chunk_scores[r.chunk.id]["embedding"] = r.score
            else:
                chunk_scores[r.chunk.id] = {"bm25": 0.0, "embedding": r.score, "chunk": r.chunk}

        for chunk_id, data in chunk_scores.items():
            bm25_norm = data["bm25"]
            emb_norm = data["embedding"]
            if bm25_results:
                max_bm25 = max(r.score for r in bm25_results) or 1
                bm25_norm = data["bm25"] / max_bm25
            if embedding_results:
                max_emb = max(r.score for r in embedding_results) or 1
                emb_norm = data["embedding"] / max_emb

            data["hybrid"] = (
                self.settings.bm25_weight * bm25_norm +
                self.settings.embedding_weight * emb_norm
            )

        if category:
            filtered = {
                k: v for k, v in chunk_scores.items()
                if category.value.lower() in v["chunk"].text.lower()
                or category.value.lower() in v["chunk"].heading.lower()
            }
            if filtered:
                chunk_scores = filtered

        sorted_chunks = sorted(chunk_scores.values(), key=lambda x: x["hybrid"], reverse=True)

        results = []
        for data in sorted_chunks[:top_k]:
            results.append(RetrievalResult(
                chunk=data["chunk"],
                score=data["hybrid"],
                method="hybrid",
            ))

        return results

    def retrieve_by_category(self, category: LegalCategory, top_k: int = None) -> List[RetrievalResult]:
        if not self.chunks:
            return []

        top_k = top_k or self.settings.retrieval_top_k
        category_keywords = category.value.lower().split()
        results = []

        for chunk in self.chunks:
            text_lower = chunk.text.lower()
            heading_lower = chunk.heading.lower()
            score = sum(1 for kw in category_keywords if kw in text_lower or kw in heading_lower)
            if score > 0:
                results.append(RetrievalResult(chunk=chunk, score=float(score), method="category"))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def retrieve_by_keywords(self, keywords: List[str], top_k: int = None) -> List[RetrievalResult]:
        if not self.chunks:
            return []

        top_k = top_k or self.settings.retrieval_top_k
        results = []

        for chunk in self.chunks:
            text_lower = chunk.text.lower()
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                results.append(RetrievalResult(chunk=chunk, score=float(score), method="keyword"))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]