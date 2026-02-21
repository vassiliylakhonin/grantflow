# aidgraph/memory_bank/vector_store.py

from __future__ import annotations

import chromadb
from typing import List, Dict, Any, Optional

class VectorStore:
    """
    Namespace-isolated RAG хранилище на ChromaDB.
    Каждый донор имеет свою коллекцию.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self._collections: Dict[str, chromadb.Collection] = {}
    
    def get_collection(self, namespace: str) -> chromadb.Collection:
        """Получает или создаёт коллекцию для namespace (донора)."""
        if namespace not in self._collections:
            self._collections[namespace] = self.client.get_or_create_collection(
                name=namespace,
                metadata={"description": f"RAG collection for {namespace}"}
            )
        return self._collections[namespace]
    
    def upsert(self, namespace: str, documents: List[str], 
               metadatas: Optional[List[Dict[str, Any]]] = None,
               ids: Optional[List[str]] = None) -> None:
        """Добавляет документы в коллекцию донора."""
        collection = self.get_collection(namespace)
        
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(self, namespace: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Запрашивает релевантные документы из коллекции донора."""
        collection = self.get_collection(namespace)
        results = collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return formatted
    
    def get_stats(self, namespace: str) -> Dict[str, Any]:
        """Возвращает статистику по коллекции."""
        collection = self.get_collection(namespace)
        count = collection.count()
        return {
            "namespace": namespace,
            "document_count": count
        }

vector_store = VectorStore()
