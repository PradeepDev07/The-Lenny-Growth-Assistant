import os
import sys
import glob
import json
import argparse
from typing import List, Dict, Any

from ingestion.chunker import chunk_transcript
from backend.app.retrieval.vector_store import vector_store

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_raw_episodes(data_dir: str = DATA_DIR) -> List[Dict[str, Any]]:
    """Load all transcript JSON files from the data directory."""
    files = glob.glob(os.path.join(data_dir, "*.json"))
    episodes = []
    for filepath in sorted(files):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            episodes.append(data)
    return episodes


def run_ingestion(refresh: bool = False, data_dir: str = DATA_DIR):
    """Run chunking and indexing pipeline."""
    print("[*] Starting Lenny Podcast Transcript Ingestion Pipeline...")
    if refresh:
        print("[-] Refresh flag detected: clearing existing index...")
        vector_store.clear()

    episodes = load_raw_episodes(data_dir)
    print(f"[+] Loaded {len(episodes)} podcast episodes from '{data_dir}'.")

    all_chunks = []
    for ep in episodes:
        chunks = chunk_transcript(ep, max_chars=1200, overlap_chars=200)
        print(f"  • '{ep.get('title')}' -> {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"[+] Total chunks to index: {len(all_chunks)}")
    vector_store.add_documents(all_chunks)
    print(f"[✓] Successfully indexed {len(vector_store.documents)} chunks into vector store.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Lenny Podcast Transcripts")
    parser.add_argument("--refresh", action="store_true", help="Clear and re-index all documents")
    parser.add_argument("--dir", default=DATA_DIR, help="Path to raw transcript JSON directory")
    args = parser.parse_args()

    run_ingestion(refresh=args.refresh, data_dir=args.dir)
