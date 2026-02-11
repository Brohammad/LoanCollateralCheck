"""Abstract vector store interface and simple in-memory fallback.

Adapters for Pinecone and Chroma are provided as scaffolds and are optional.
"""
from typing import List, Dict, Any
import os

class VectorStore:
    def add(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        raise NotImplementedError()

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError()


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._data = []  # list of tuples (id, embedding, metadata)

    def add(self, ids, embeddings, metadatas):
        for _id, emb, md in zip(ids, embeddings, metadatas):
            self._data.append((_id, emb, md))

    def _cosine_sim(self, a, b):
        # very small helper; assumes equal length
        try:
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x * x for x in a) ** 0.5
            mag_b = sum(y * y for y in b) ** 0.5
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot / (mag_a * mag_b)
        except Exception:
            return 0.0

    def search(self, query_embedding, top_k=5):
        scored = []
        for _id, emb, md in self._data:
            score = self._cosine_sim(query_embedding, emb)
            scored.append({"id": _id, "score": score, "metadata": md})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# Optional adapters (scaffolds). Importing pinecone or chromadb only when used.
class PineconeAdapter(VectorStore):
    def __init__(self, api_key: str | None = None, env: str | None = None, index_name: str | None = None):
        try:
            import pinecone
        except Exception as e:
            raise RuntimeError("Pinecone client not installed. Install pinecone-client to use this adapter.")
        self.api_key = api_key or os.environ.get("PINECONE_API_KEY")
        self.env = env or os.environ.get("PINECONE_ENV")
        self.index_name = index_name or os.environ.get("PINECONE_INDEX")
        pinecone.init(api_key=self.api_key, environment=self.env)
        self.index = pinecone.GRPCIndex(self.index_name)

    def add(self, ids, embeddings, metadatas):
        self.index.upsert(vectors=list(zip(ids, embeddings, metadatas)))

    def search(self, query_embedding, top_k=5):
        res = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        return [{"id": match.id, "score": match.score, "metadata": match.metadata} for match in res.matches]


class ChromaAdapter(VectorStore):
    def __init__(self, persist_directory: str | None = None):
        try:
            import chromadb
        except Exception:
            raise RuntimeError("Chroma not installed. Install chromadb to use this adapter.")
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions
        persist = persist_directory or os.environ.get("CHROMA_PERSIST_DIR")
        client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist))
        self.col = client.get_or_create_collection("default")

    def add(self, ids, embeddings, metadatas):
        self.col.add(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def search(self, query_embedding, top_k=5):
        res = self.col.query(query_embeddings=[query_embedding], n_results=top_k)
        # res format depends on chroma; normalize to list of dicts
        out = []
        for i, _id in enumerate(res.get("ids", [[]])[0]):
            out.append({"id": _id, "score": float(res.get("distances", [[0]])[0][i]), "metadata": res.get("metadatas", [[None]])[0][i]})
        return out
