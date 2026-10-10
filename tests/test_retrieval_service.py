"""
tests/test_retrieval_service.py
Unit and integration tests for local Sentence Transformers embeddings and FAISS index search.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from database import db
from services.embedding_service import load_model, embed_texts, embed_query
from services.retrieval_service import (
    build_index,
    load_index,
    index_paper,
    search_index,
    search_papers,
)


class TestEmbeddingService:
    def test_load_model_cached(self):
        m1 = load_model()
        m2 = load_model()
        assert m1 is m2

    def test_embed_texts_shape_and_norm(self):
        texts = [
            "Transformer architectures rely on multi-head attention.",
            "Convolutional neural networks extract local spatial features.",
        ]
        embeddings = embed_texts(texts)
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (2, 384)
        assert embeddings.dtype == np.float32

        # Check L2 normalization (norm should be ~1.0)
        norms = np.linalg.norm(embeddings, axis=1)
        np.testing.assert_allclose(norms, [1.0, 1.0], atol=1e-4)

    def test_embed_empty_texts(self):
        embeddings = embed_texts([])
        assert embeddings.shape == (0, 384)
        assert embeddings.dtype == np.float32

    def test_embed_query(self):
        vec = embed_query("What is self-attention?")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)
        assert vec.dtype == np.float32
        norm = np.linalg.norm(vec)
        np.testing.assert_allclose(norm, 1.0, atol=1e-4)

    def test_embed_empty_query(self):
        vec = embed_query("")
        assert vec.shape == (384,)
        assert np.all(vec == 0.0)


class TestRetrievalService:
    def test_build_and_load_index(self, tmp_path):
        texts = ["Artificial intelligence", "Natural language processing"]
        embeddings = embed_texts(texts)

        index_file = tmp_path / "test.index"
        built_index = build_index(embeddings, index_file)
        assert index_file.exists()
        assert built_index.ntotal == 2

        loaded_index = load_index(index_file)
        assert loaded_index.ntotal == 2

    def test_search_index_finds_most_relevant(self):
        texts = [
            "Deep learning models for medical image segmentation.",
            "Photosynthesis in marine phytoplankton ecosystems.",
        ]
        chunks = [
            {"chunk_index": 0, "page_number": 1, "text": texts[0]},
            {"chunk_index": 1, "page_number": 2, "text": texts[1]},
        ]
        embeddings = embed_texts(texts)
        index = build_index(embeddings, Path("unused"))

        query_vec = embed_query("CT scans and MRI tumor segmentation")
        results = search_index(query_vec, index, chunks, top_k=2)

        assert len(results) == 2
        # The medical chunk must score significantly higher than marine biology
        assert results[0]["chunk_index"] == 0
        assert results[0]["score"] > results[1]["score"]
        assert "medical image segmentation" in results[0]["text"]

    def test_index_paper_and_search_papers(self, tmp_path):
        # 1. Insert two papers with chunks into DB
        p1 = db.insert_paper(
            file_path="/tmp/p1.pdf",
            file_hash="hash_retrieval_1",
            title="Transformer Scaling Laws",
            authors=["Kaplan", "McCandlish"],
            year=2020,
        )
        p1_chunks = [
            {"chunk_index": 0, "page_number": 1, "text": "We study empirical scaling laws for language model performance."},
            {"chunk_index": 1, "page_number": 2, "text": "Cross-entropy loss scales as a power-law with compute and dataset size."},
        ]
        db.insert_chunks(p1, p1_chunks)

        p2 = db.insert_paper(
            file_path="/tmp/p2.pdf",
            file_hash="hash_retrieval_2",
            title="ResNet Deep Residual Learning",
            authors=["He", "Zhang"],
            year=2016,
        )
        p2_chunks = [
            {"chunk_index": 0, "page_number": 1, "text": "Deeper neural networks are more difficult to train due to vanishing gradients."},
            {"chunk_index": 1, "page_number": 2, "text": "We introduce residual skip connections to reformulate layers as residual functions."},
        ]
        db.insert_chunks(p2, p2_chunks)

        # 2. Build index for paper 1
        idx_path = index_paper(p1)
        assert idx_path is not None
        assert idx_path.exists()

        paper1_record = db.get_paper(p1)
        assert paper1_record["index_path"] == str(idx_path)

        # 3. Query across both papers (paper 2 index will build dynamically)
        results = search_papers("power law scaling with compute", paper_ids=[p1, p2], top_k=2)

        assert len(results) == 2
        top_match = results[0]
        assert top_match["paper_id"] == p1
        assert "scaling laws" in top_match["text"].lower() or "power-law" in top_match["text"].lower()
        assert top_match["title"] == "Transformer Scaling Laws"
        assert top_match["score"] > 0.4
