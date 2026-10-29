"""RAG query layer: retrieve relevant chunks from Chroma, hand to LLM."""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


class Retriever:
    def __init__(self, config: dict):
        self.config = config
        db_path = Path(config["vectordb"]["path"])
        if not db_path.exists():
            raise FileNotFoundError(
                f"Vector DB bulunamadı: {db_path}\n"
                "Önce 'python -m src.ingest' çalıştır."
            )
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config["embedding"]["model"],
            device=config["embedding"]["device"],
        )
        client = chromadb.PersistentClient(path=str(db_path))
        self.collection = client.get_collection(
            name=config["vectordb"]["collection"],
            embedding_function=embed_fn,
        )

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """Returns a list of {document, metadata, score} dicts."""
        top_k = top_k or self.config["retrieval"]["top_k"]
        min_score = self.config["retrieval"]["min_score"]

        res = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        out = []
        for doc, meta, dist in zip(docs, metas, dists):
            # Chroma returns distance; convert to similarity score (cosine)
            score = 1.0 - float(dist)
            if score < min_score:
                continue
            out.append({
                "document": doc,
                "metadata": meta or {},
                "score": score,
            })
        return out

    def count(self) -> int:
        return self.collection.count()
