from __future__ import annotations

import chromadb
from chromadb.utils import embedding_functions
import os
from typing import List, Dict, Any, Optional


class VectorStore:
    """ Namespace-isolated RAG хранилище на ChromaDB. Использует OpenAI Embeddings для высокой семантической точности. """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self._collections: Dict[str, chromadb.Collection] = {}
        
        # Настраиваем мощную функцию эмбеддингов от OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: OPENAI_API_KEY not found. Falling back to default embeddings.")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        else:
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small"  # Лучшая модель цена/качество на 2026 год
            )
    
    def get_collection(self, namespace: str) -> chromadb.Collection:
        """Получает или создаёт коллекцию для namespace (донора)."""
        if namespace not in self._collections:
            self._collections[namespace] = self.client.get_or_create_collection(
                name=namespace,
                embedding_function=self.embedding_function,
                # <-- ПРИВЯЗЫВАЕМ СЮДА
                metadata={"description": f"RAG collection for {namespace}"}
            )
        return self._collections[namespace]