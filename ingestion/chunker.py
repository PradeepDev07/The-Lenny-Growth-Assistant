import re
from typing import Any, Dict, List


def clean_text(text: str) -> str:
    """Normalize whitespace and clean transcript text."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_transcript(
    episode: Dict[str, Any],
    max_chars: int = 1200,
    overlap_chars: int = 200,
) -> List[Dict[str, Any]]:
    """
    Split a transcript into overlapping semantic chunks preserving episode metadata.
    Window size of ~1200 characters corresponds to ~400-600 tokens with 10-15% overlap.
    """
    transcript = clean_text(episode.get("transcript", ""))
    paragraphs = transcript.split("\n\n")

    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
        else:
            if current_chunk:
                chunks.append({
                    "id": f"{episode.get('episode_id', 'ep')}-chunk-{chunk_index}",
                    "episode_id": episode.get("episode_id", ""),
                    "source_title": episode.get("title", "Lenny's Podcast"),
                    "guest": episode.get("guest", "Guest"),
                    "url": episode.get("url", "https://www.lennyspodcast.com"),
                    "chunk_index": chunk_index,
                    "content": current_chunk,
                })
                chunk_index += 1

                # Carry over overlap to maintain context continuity across chunk boundaries
                overlap = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                current_chunk = f"{overlap}\n\n{para}".strip()
            else:
                # Single paragraph exceeds max_chars, split strictly
                chunks.append({
                    "id": f"{episode.get('episode_id', 'ep')}-chunk-{chunk_index}",
                    "episode_id": episode.get("episode_id", ""),
                    "source_title": episode.get("title", "Lenny's Podcast"),
                    "guest": episode.get("guest", "Guest"),
                    "url": episode.get("url", "https://www.lennyspodcast.com"),
                    "chunk_index": chunk_index,
                    "content": para[:max_chars],
                })
                chunk_index += 1
                current_chunk = para[max_chars - overlap_chars:]

    if current_chunk:
        chunks.append({
            "id": f"{episode.get('episode_id', 'ep')}-chunk-{chunk_index}",
            "episode_id": episode.get("episode_id", ""),
            "source_title": episode.get("title", "Lenny's Podcast"),
            "guest": episode.get("guest", "Guest"),
            "url": episode.get("url", "https://www.lennyspodcast.com"),
            "chunk_index": chunk_index,
            "content": current_chunk,
        })

    return chunks
