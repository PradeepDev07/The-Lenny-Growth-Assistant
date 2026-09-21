import pytest
from ingestion.chunker import chunk_transcript
from backend.app.retrieval.vector_store import VectorStore


@pytest.fixture
def store():
    # Fresh vector store instance reading the generated cache
    s = VectorStore()
    return s


def test_chunker_metadata_and_overlap():
    episode = {
        "episode_id": "test-ep-01",
        "title": "Test Growth Strategy",
        "guest": "Test Guest",
        "url": "https://lennyspodcast.com/test",
        "transcript": "First paragraph.\n\nSecond paragraph discussing viral growth loops.\n\nThird paragraph on retention."
    }
    chunks = chunk_transcript(episode, max_chars=100, overlap_chars=20)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk["episode_id"] == "test-ep-01"
        assert chunk["source_title"] == "Test Growth Strategy"
        assert chunk["guest"] == "Test Guest"
        assert "id" in chunk
        assert "content" in chunk


def test_retrieval_brian_balfour_growth_loops(store):
    results = store.search("Brian Balfour growth loops vs traditional marketing funnels", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["guest"] == "Brian Balfour"
    assert "loop" in top["content"].lower()
    assert top["score"] > 0.05


def test_retrieval_elena_verna_activation(store):
    results = store.search("Elena Verna activation metrics and product-led growth", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["guest"] == "Elena Verna"
    assert "activation" in top["content"].lower()


def test_retrieval_shreyas_doshi_lno_framework(store):
    results = store.search("Shreyas Doshi LNO framework leverage neutral overhead", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["guest"] == "Shreyas Doshi"
    assert "lno" in top["content"].lower()


def test_retrieval_lenny_pmf_signals(store):
    results = store.search("Lenny Rachitsky product market fit signals flat retention curve", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["guest"] == "Lenny Rachitsky"
    assert "retention" in top["content"].lower() or "pmf" in top["content"].lower()


def test_similarity_threshold_rejects_unrelated_queries(store):
    """
    Asserts that completely out-of-domain queries score below the similarity
    threshold and return [] to trigger grounded refusal rather than hallucination.
    """
    unrelated_queries = [
        "quantum mechanics wave function collapse and particle entanglement",
        "recipe for double chocolate fudge brownies with walnuts",
        "how to change the transmission fluid on a 1998 honda civic"
    ]
    for query in unrelated_queries:
        results = store.search(query, top_k=3, min_score=0.1)
        assert len(results) == 0, f"Unrelated query '{query}' returned chunks instead of refusing!"
