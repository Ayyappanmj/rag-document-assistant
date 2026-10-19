import json

from app.rag.chunker import Chunk
from app.rag.vector_store import META_FILE, VectorStore
from tests.fakes import FakeEmbeddingService

emb = FakeEmbeddingService()


def _chunks(doc, texts, start=0):
    return [Chunk(f"{doc}_{start + i}", doc, f"{doc}.pdf", 1, start + i, t) for i, t in enumerate(texts)]


def _add(store, chunks):
    store.add(chunks, emb.embed_texts([c.text for c in chunks]))


def test_top_k_larger_than_index_returns_everything(tmp_path):
    store = VectorStore(tmp_path)
    _add(store, _chunks("d1", ["alpha beta", "gamma delta"]))
    assert len(store.search(emb.embed_query("alpha"), top_k=50)) == 2


def test_adding_after_reload_does_not_reuse_ids(tmp_path):
    first = VectorStore(tmp_path)
    _add(first, _chunks("d1", ["alpha beta", "gamma delta", "epsilon zeta"]))
    second = VectorStore(tmp_path)                       # simulates a server restart
    _add(second, _chunks("d2", ["eta theta", "iota kappa"]))
    assert second.count == 5
    found = {h.chunk_id for h in second.search(emb.embed_query("alpha eta"), top_k=5)}
    assert {"d1_0", "d2_0"} <= found


def test_deleting_unknown_document_is_a_no_op(tmp_path):
    store = VectorStore(tmp_path)
    _add(store, _chunks("d1", ["alpha beta"]))
    assert store.delete_document("nope") == 0 and store.count == 1


def test_index_without_metadata_starts_empty_instead_of_crashing(tmp_path):
    store = VectorStore(tmp_path)
    _add(store, _chunks("d1", ["alpha beta"]))
    (tmp_path / META_FILE).unlink()
    assert VectorStore(tmp_path).count == 0


def test_metadata_file_is_valid_json_after_every_write(tmp_path):
    store = VectorStore(tmp_path)
    _add(store, _chunks("d1", ["alpha beta"]))
    store.delete_document("d1")
    data = json.loads((tmp_path / META_FILE).read_text(encoding="utf-8"))
    assert data["items"] == {} and data["next_id"] == 1


def test_scores_are_cosine_similarities_between_minus_one_and_one(tmp_path):
    store = VectorStore(tmp_path)
    _add(store, _chunks("d1", ["alpha beta", "gamma delta"]))
    for hit in store.search(emb.embed_query("alpha beta"), top_k=2):
        assert -1.0001 <= hit.score <= 1.0001
    assert store.search(emb.embed_query("alpha beta"), top_k=1)[0].score > 0.99  # identical text
