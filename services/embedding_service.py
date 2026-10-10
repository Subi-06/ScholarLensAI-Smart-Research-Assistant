"""
services/embedding_service.py
Local embedding generation using Sentence Transformers.
Custom implementation without LangChain.
"""
from __future__ import annotations

from typing import Any
import numpy as np
from sentence_transformers import SentenceTransformer

from utils import config

# Global in-memory cache for loaded embedding models
_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def load_model(model_name: str | None = None) -> SentenceTransformer:
    """
    Load and cache a SentenceTransformer model by name.
    Reuses the in-memory instance and uses local cached files for instant retrieval.
    """
    if not model_name:
        model_name = config.EMBEDDING_MODEL

    if model_name not in _MODEL_CACHE:
        try:
            # Fast offline load from cached weights without querying HuggingFace Hub network
            model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            model = SentenceTransformer(model_name)
        _MODEL_CACHE[model_name] = model

    return _MODEL_CACHE[model_name]


def embed_texts(
    texts: list[str],
    model: SentenceTransformer | None = None,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Generate normalized embeddings for a list of texts.

    Returns:
        numpy.ndarray of shape (len(texts), embedding_dim) and dtype float32.
    """
    if not texts:
        # Return empty 2D array with standard dim (or dynamically from model)
        m = model or load_model()
        dim = getattr(m, "get_embedding_dimension", getattr(m, "get_sentence_embedding_dimension", lambda: 384))() or 384
        return np.empty((0, dim), dtype=np.float32)

    if model is None:
        model = load_model()

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    return np.asarray(embeddings, dtype=np.float32)


def embed_query(
    query: str,
    model: SentenceTransformer | None = None,
) -> np.ndarray:
    """
    Generate a normalized embedding for a single query string.

    Returns:
        numpy.ndarray of shape (embedding_dim,) and dtype float32.
    """
    if model is None:
        model = load_model()

    cleaned_query = (query or "").strip()
    if not cleaned_query:
        # Return zero vector with correct dimension
        dim = getattr(model, "get_embedding_dimension", getattr(model, "get_sentence_embedding_dimension", lambda: 384))() or 384
        return np.zeros((dim,), dtype=np.float32)

    embedding = model.encode(
        cleaned_query,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    return np.asarray(embedding, dtype=np.float32)
