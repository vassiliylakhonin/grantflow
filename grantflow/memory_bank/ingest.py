# grantflow/memory_bank/ingest.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from grantflow.memory_bank.vector_store import vector_store


def load_pdf_pages(pdf_path: str) -> List[str]:
    """Извлекает текст постранично из PDF. Требует pymupdf."""
    try:
        import fitz  # pymupdf

        doc = fitz.open(pdf_path)
        pages: List[str] = []
        for page in doc:
            pages.append(page.get_text() or "")
        doc.close()
        return pages
    except ImportError as exc:
        raise ImportError("Установите pymupdf: pip install pymupdf") from exc


def load_pdf_text(pdf_path: str) -> str:
    """Извлекает текст из PDF. Требует pymupdf."""
    return "".join(load_pdf_pages(pdf_path))


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Разбивает текст на чанки с перекрытием."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def chunk_pages(
    pages: List[str],
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[Dict[str, Any]]:
    """Разбивает PDF-текст на чанки с trace metadata по страницам."""
    records: List[Dict[str, Any]] = []
    chunk_index = 0
    for page_number, page_text in enumerate(pages, start=1):
        if not page_text:
            continue
        page_chunks = chunk_text(page_text, chunk_size=chunk_size, overlap=overlap)
        for page_chunk_index, chunk in enumerate(page_chunks):
            records.append(
                {
                    "text": chunk,
                    "chunk": chunk_index,
                    "page": page_number,
                    "page_start": page_number,
                    "page_end": page_number,
                    "page_chunk": page_chunk_index,
                }
            )
            chunk_index += 1
    return records


def ingest_pdf_to_namespace(
    pdf_path: str,
    namespace: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Загружает PDF в указанную коллекцию (namespace) донора."""
    pages = load_pdf_pages(pdf_path)
    chunk_records = chunk_pages(pages)

    # Fallback for unusual extractors/files that return no per-page chunks but some text.
    if not chunk_records:
        text = "".join(pages)
        for idx, chunk in enumerate(chunk_text(text) if text else []):
            chunk_records.append({"text": chunk, "chunk": idx})

    ids: List[str] = []
    chunks: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    stem = Path(pdf_path).stem
    for record in chunk_records:
        page = record.get("page")
        page_chunk = record.get("page_chunk")
        chunk_idx = int(record.get("chunk", len(ids)))
        if page is not None and page_chunk is not None:
            doc_id = f"{namespace}_{stem}_p{page}_c{page_chunk}"
        else:
            doc_id = f"{namespace}_{stem}_{chunk_idx}"
        ids.append(doc_id)
        chunks.append(str(record.get("text", "")))
        metadatas.append(
            {
                **{
                    "source": pdf_path,
                    "chunk": chunk_idx,
                    "chunk_id": doc_id,
                    **({k: v for k, v in record.items() if k != "text"}),
                },
                **(metadata or {}),
            }
        )

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
