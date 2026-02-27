from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, Optional

import chromadb


class VectorStore:
    """Thin stable wrapper over Chroma collections with namespace isolation."""

    def __init__(self) -> None:
        self.prefix = os.getenv("CHROMA_COLLECTION_PREFIX", "grantflow")
        self._collections: Dict[str, Any] = {}
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._client_init_error: Optional[str] = None

        self._chroma_host = os.getenv("CHROMA_HOST")
        self._chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        self._persist_dir = (
            os.getenv("CHROMA_PERSIST_DIRECTORY")
            or os.getenv("GRANTFLOW_CHROMA_DIR")
            or os.getenv("AIDGRAPH_CHROMA_DIR")
            or "./chroma_db"
        )
        self.client: Any = None

        try:
            if self._chroma_host:
                self.client = chromadb.HttpClient(host=self._chroma_host, port=self._chroma_port)
            else:
                self.client = chromadb.PersistentClient(path=self._persist_dir)
        except Exception as exc:
            # Sandbox/runtime fallback: keep API alive and use in-memory vectors.
            self._client_init_error = str(exc)
            self.client = None

    @staticmethod
    def normalize_namespace(namespace: str) -> str:
        raw = str(namespace or "default").strip().lower()
        if not raw:
            return "default"
        raw = raw.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")
        # Chroma collection names are safer with a constrained token set.
        normalized = re.sub(r"[^a-z0-9_.-]+", "_", raw)
        normalized = re.sub(r"_+", "_", normalized).strip("._-")
        return normalized or "default"

    def _collection_name(self, namespace: str) -> str:
        ns = self.normalize_namespace(namespace)
        return f"{self.prefix}_{ns}"

    def _embed_texts(self, texts: list[str], dims: int = 16) -> list[list[float]]:
        """Deterministic lightweight embeddings for local/offline MVP smoke tests."""
        embeddings: list[list[float]] = []
        for text in texts:
            vec = [0.0] * dims
            data = (text or "").encode("utf-8", errors="ignore")
            digest = hashlib.sha256(data).digest()
            for i in range(dims):
                vec[i] = digest[i] / 255.0
            embeddings.append(vec)
        return embeddings

    def _cosine_like(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def _ensure_memory_namespace(self, namespace: str) -> Dict[str, Any]:
        name = self._collection_name(namespace)
        if name not in self._memory_store:
            self._memory_store[name] = {"name": name, "rows": {}}
        return self._memory_store[name]

    def get_collection(self, namespace: str):
        if self.client is None:
            return None
        name = self._collection_name(namespace)
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(name=name)
        return self._collections[name]

    def upsert(
        self,
        namespace: str,
        ids: list[str],
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        embeddings = self._embed_texts(documents)

        if self.client is None:
            ns = self._ensure_memory_namespace(namespace)
            rows = ns["rows"]
            for i, doc_id in enumerate(ids):
                rows[doc_id] = {
                    "id": doc_id,
                    "document": documents[i],
                    "metadata": (metadatas[i] if metadatas and i < len(metadatas) else None),
                    "embedding": embeddings[i],
                }
            return

        col = self.get_collection(namespace)
        kwargs: Dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "embeddings": embeddings,
        }
        if metadatas is not None:
            kwargs["metadatas"] = metadatas
        col.upsert(**kwargs)

    def query(
        self,
        namespace: str,
        query_texts: list[str] | str,
        n_results: int = 5,
        where: Optional[dict] = None,
        top_k: Optional[int] = None,
    ):
        if top_k is not None:
            n_results = top_k

        single_query = isinstance(query_texts, str)
        query_list = [query_texts] if single_query else list(query_texts)

        if self.client is None:
            ns = self._ensure_memory_namespace(namespace)
            rows = list(ns["rows"].values())
            docs_out = []
            metas_out = []
            ids_out = []
            for q in query_list:
                q_emb = self._embed_texts([q])[0]
                ranked = sorted(
                    rows,
                    key=lambda r: self._cosine_like(q_emb, r["embedding"]),
                    reverse=True,
                )[:n_results]
                docs_out.append([r["document"] for r in ranked])
                metas_out.append([r["metadata"] for r in ranked])
                ids_out.append([r["id"] for r in ranked])
            result = {"ids": ids_out, "documents": docs_out, "metadatas": metas_out}
            if single_query:
                return docs_out[0]
            return result

        col = self.get_collection(namespace)
        kwargs: Dict[str, Any] = {
            "query_embeddings": self._embed_texts(query_list),
            "n_results": n_results,
        }
        if where is not None:
            kwargs["where"] = where
        result = col.query(**kwargs)

        if single_query:
            return (result.get("documents") or [[]])[0]
        return result

    def get_stats(self, namespace: str) -> dict:
        if self.client is None:
            ns = self._ensure_memory_namespace(namespace)
            count = len(ns["rows"])
            return {
                "namespace": namespace,
                "collection": ns["name"],
                "count": count,
                "document_count": count,
                "backend": "memory",
                "client_init_error": self._client_init_error,
            }

        col = self.get_collection(namespace)
        count = col.count()
        return {
            "namespace": namespace,
            "collection": col.name,
            "count": count,
            "document_count": count,
            "backend": "chroma",
        }


vector_store = VectorStore()
