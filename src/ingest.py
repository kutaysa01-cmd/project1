"""Build / rebuild the vector database from tickets and manuals.

Usage:
    python -m src.ingest              # Full rebuild
    python -m src.ingest --append     # Add new files without wiping DB
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import chromadb
import yaml
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from tqdm import tqdm

from src.parser import chunk_text, parse_tickets_dir


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_pdfs(manuals_dir: str) -> list[tuple[str, str]]:
    """Return (filename, text) for each PDF under manuals_dir."""
    base = Path(manuals_dir)
    if not base.exists():
        return []
    out = []
    for pdf_path in sorted(base.glob("**/*.pdf")):
        try:
            reader = PdfReader(str(pdf_path))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[Page {i+1}]\n{text}")
            if pages:
                out.append((str(pdf_path), "\n\n".join(pages)))
        except Exception as e:
            print(f"[WARN] Failed to read PDF {pdf_path}: {e}")
    return out


def build_index(config: dict, append: bool = False) -> None:
    db_path = Path(config["vectordb"]["path"])
    collection_name = config["vectordb"]["collection"]

    # Reset DB on full rebuild
    if not append and db_path.exists():
        print(f"[INFO] Wiping existing vector DB at {db_path}")
        shutil.rmtree(db_path)
    db_path.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Loading embedding model: {config['embedding']['model']}")
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config["embedding"]["model"],
        device=config["embedding"]["device"],
    )

    client = chromadb.PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    chunk_size = config["chunking"]["chunk_size"]
    overlap = config["chunking"]["chunk_overlap"]

    documents, metadatas, ids = [], [], []

    # ----- Ingest tickets -----
    print(f"[INFO] Parsing tickets from {config['data']['tickets_dir']}")
    tickets = parse_tickets_dir(config["data"]["tickets_dir"])
    print(f"[INFO] Found {len(tickets)} tickets")

    for ticket in tqdm(tickets, desc="Tickets"):
        text = ticket.to_document()
        if not text.strip():
            continue
        chunks = chunk_text(text, chunk_size, overlap)
        base_id = ticket.ticket_id or Path(ticket.source_file).stem
        for i, chunk in enumerate(chunks):
            meta = ticket.metadata()
            meta["type"] = "ticket"
            meta["chunk"] = i
            documents.append(chunk)
            metadatas.append(meta)
            ids.append(f"ticket::{base_id}::{i}")

    # ----- Ingest manuals -----
    print(f"[INFO] Loading manuals from {config['data']['manuals_dir']}")
    manuals = _load_pdfs(config["data"]["manuals_dir"])
    print(f"[INFO] Found {len(manuals)} manual PDFs")

    for source, text in tqdm(manuals, desc="Manuals"):
        chunks = chunk_text(text, chunk_size, overlap)
        base_id = Path(source).stem
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "source": source,
                "type": "manual",
                "chunk": i,
                "title": Path(source).stem,
            })
            ids.append(f"manual::{base_id}::{i}")

    if not documents:
        print("[WARN] No documents to index. Put HTML tickets in "
              f"{config['data']['tickets_dir']} or PDFs in "
              f"{config['data']['manuals_dir']} and re-run.")
        return

    print(f"[INFO] Embedding and inserting {len(documents)} chunks...")
    # Insert in batches to keep memory reasonable
    BATCH = 64
    for i in tqdm(range(0, len(documents), BATCH), desc="Indexing"):
        collection.add(
            documents=documents[i:i + BATCH],
            metadatas=metadatas[i:i + BATCH],
            ids=ids[i:i + BATCH],
        )

    print(f"[OK] Indexed {len(documents)} chunks "
          f"({len(tickets)} tickets, {len(manuals)} manuals)")
    print(f"[OK] Vector DB saved to {db_path.resolve()}")


def main():
    ap = argparse.ArgumentParser(description="Build vector DB from tickets + manuals")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--append", action="store_true",
                    help="Add to existing DB instead of wiping")
    args = ap.parse_args()
    build_index(load_config(args.config), append=args.append)


if __name__ == "__main__":
    main()
