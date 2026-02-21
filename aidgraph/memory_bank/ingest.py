# aidgraph/memory_bank/ingest.py

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from aidgraph.memory_bank.vector_store import vector_store

def load_pdf_text(pdf_path: str) -> str:
    """Извлекает текст из PDF. Требует pymupdf."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        raise ImportError("Установите pymupdf: pip install pymupdf")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Разбивает текст на чанки с перекрытием."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

def ingest_pdf_to_namespace(pdf_path: str, namespace: str, 
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Загружает PDF в указанную коллекцию (namespace) донора."""
    text = load_pdf_text(pdf_path)
    chunks = chunk_text(text)
    
    ids = [f"{namespace}_{Path(pdf_path).stem}_{i}" for i in range(len(chunks))]
    metadatas = [
        {**{"source": pdf_path, "chunk": i}, **(metadata or {})}
        for i in range(len(chunks))
    ]
    
    vector_store.upsert(namespace, chunks, metadatas, ids)
    
    return {
        "namespace": namespace,
        "source": pdf_path,
        "chunks_ingested": len(chunks)
    }

def ingest_folder_to_namespace(folder_path: str, namespace: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Загружает все PDF из папки в коллекцию донора."""
    results = []
    for file in Path(folder_path).glob("*.pdf"):
        result = ingest_pdf_to_namespace(str(file), namespace, metadata)
        results.append(result)
    return results

if __name__ == "__main__":
    # Пример использования
    print("Usage: python -c 'from aidgraph.memory_bank.ingest import ingest_pdf_to_namespace; ingest_pdf_to_namespace(\"path/to.pdf\", \"namespace\")'")
