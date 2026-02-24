# grantflow/memory_bank/ingest.py

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional

from grantflow.memory_bank.vector_store import vector_store


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
    except ImportError as exc:
        raise ImportError("Установите pymupdf: pip install pymupdf") from exc


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


def ingest_pdf_to_namespace(
    pdf_path: str,
    namespace: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Загружает PDF в указанную коллекцию (namespace) донора."""
    text = load_pdf_text(pdf_path)
    chunks = chunk_text(text)

    ids = [f"{namespace}_{Path(pdf_path).stem}_{i}" for i in range(len(chunks))]
    metadatas = [
        {**{"source": pdf_path, "chunk": i}, **(metadata or {})}
        for i in range(len(chunks))
    ]

    vector_store.upsert(namespace=namespace, ids=ids, documents=chunks, metadatas=metadatas)

    return {
        "namespace": namespace,
        "source": pdf_path,
        "chunks_ingested": len(chunks),
        "stats": vector_store.get_stats(namespace),
    }


def ingest_folder_to_namespace(
    folder_path: str,
    namespace: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Загружает все PDF из папки в коллекцию донора."""
    results = []
    for file in Path(folder_path).glob("*.pdf"):
        results.append(ingest_pdf_to_namespace(str(file), namespace, metadata))
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest PDF(s) into GrantFlow Chroma namespace")
    parser.add_argument("path", nargs="?", help="PDF file path or folder containing PDFs")
    parser.add_argument("namespace", nargs="?", help="Target namespace/collection suffix")
    parser.add_argument("--folder", action="store_true", help="Treat path as folder and ingest all PDFs")
    args = parser.parse_args()

    if not args.path or not args.namespace:
        print("Usage: python -m grantflow.memory_bank.ingest <path> <namespace> [--folder]")
    elif args.folder:
        print(ingest_folder_to_namespace(args.path, args.namespace))
    else:
        print(ingest_pdf_to_namespace(args.path, args.namespace))
