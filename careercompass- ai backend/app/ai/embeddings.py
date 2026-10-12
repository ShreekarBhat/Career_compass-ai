"""Text embeddings.

Primary: sentence-transformers (all-MiniLM-L6-v2, 384 dims).
Fallback: deterministic hashing embedder, so the system still runs offline / without torch.
IMPORTANT: if you switch backend, run `python -m scripts.reindex_embeddings` so stored vectors match.
"""
import hashlib
import logging
import re
import threading

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)
_TOKEN = re.compile(r"[a-z0-9\+#\.]+")


class Embedder:
    def __init__(self) -> None:
        self.dim = settings.embedding_dim
        self.backend = "hashing"
        self._model = None
        self._loaded = False
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            if not settings.use_sentence_transformers:
                return
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(settings.embedding_model)
                if model.get_sentence_embedding_dimension() != self.dim:
                    logger.warning("Embedding model dim != EMBEDDING_DIM (%s); using hashing fallback",
                                   self.dim)
                    return
                self._model = model
                self.backend = "sentence-transformers"
                logger.info("Embeddings: %s", settings.embedding_model)
            except Exception as exc:
                logger.warning("sentence-transformers unavailable (%s); using hashing fallback", exc)

    def _hash_embed(self, text: str) -> np.ndarray:
        tokens = _TOKEN.findall(text.lower())
        feats = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vec = np.zeros(self.dim, dtype=np.float32)
        for f in feats:
            h = int(hashlib.md5(f.encode("utf-8")).hexdigest(), 16)
            sign = 1.0 if (h >> 64) & 1 else -1.0
            vec[h % self.dim] += sign * (1.5 if "_" in f else 1.0)
        vec = np.sign(vec) * np.log1p(np.abs(vec))
        n = np.linalg.norm(vec)
        return vec / n if n else vec

    def embed(self, texts: list[str]) -> np.ndarray:
        self._load()
        texts = [t if t and t.strip() else " " for t in texts]
        if self._model is not None:
            return np.asarray(self._model.encode(texts, normalize_embeddings=True,
                                                 show_progress_bar=False), dtype=np.float32)
        return np.vstack([self._hash_embed(t) for t in texts])

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


embedder = Embedder()


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if not na or not nb:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
