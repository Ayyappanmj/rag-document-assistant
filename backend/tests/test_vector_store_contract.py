"""The same behaviour is required from every vector database, so these tests run against FAISS and Chroma."""
import numpy as np
import pytest

from app.rag.chunker import Chunk
from app.rag.vector_store import VectorStore
from tests.fakes import FakeEmbeddingService

emb = FakeEmbeddingService()


@pytest.fixture(params=["faiss", "chroma"])
def make_store(request, tmp_path):
    """Returns a function that opens the store on the same folder each time (like a server restart)."""
    if request.param == "faiss":
        return lambda: VectorStore(tmp_path / "faiss")
    pytest.importorskip("chromadb")
    from app.rag.chroma_store import ChromaVectorStore

    return lambda: ChromaVectorStore(tmp_path / "chroma")


def chunks_for(doc, texts, start=0, section=None):
    return [Chunk(f"{doc}_{start + i}", doc, f"{doc}.pdf", i + 1, start + i, t, section) for i, t in enumerate(texts)]


def add(store, chunks):
    store.add(chunks, emb.embed_texts([c.text for c in chunks]))


DOC1 = ["Revenue grew eighteen percent in fiscal 2025.", "The board approved a new dividend policy."]
DOC2 = ["Employees receive twenty vacation days per year."]


@pytest.fixture
def store(make_store):
    s = make_store()
    add(s, chunks_for("d1", DOC1))
    add(s, chunks_for("d2", DOC2))
    return s


def test_empty_store(make_store):
    s = make_store()
    assert s.count == 0 and s.search(emb.embed_query("anything")) == []


def test_has_name_and_index_type(store):
    assert store.name in ("faiss", "chroma") and store.index_type


def test_ranks_the_relevant_chunk_first(store):
    hits = store.search(emb.embed_query("vacation days for employees"), top_k=3)
    assert hits[0].document_id == "d2" and hits[0].chunk_id == "d2_0"
    assert hits[0].score >= hits[-1].score


def test_scores_are_cosine_similarity(store):
    top = store.search(emb.embed_query("Revenue grew eighteen percent in fiscal 2025."), top_k=1)[0]
    assert top.chunk_id == "d1_0" and top.score == pytest.approx(1.0, abs=1e-3)


def test_top_k_larger_than_the_index(store):
    assert len(store.search(emb.embed_query("revenue"), top_k=50)) == 3


def test_document_filter_single_and_multiple_and_unknown(store):
    q = emb.embed_query("revenue vacation dividend")
    assert {h.document_id for h in store.search(q, top_k=10, document_ids=["d2"])} == {"d2"}
    assert {h.document_id for h in store.search(q, top_k=10, document_ids=["d1", "d2"])} == {"d1", "d2"}
    assert store.search(q, top_k=10, document_ids=["nope"]) == []


def test_delete_document(store):
    assert store.delete_document("d1") == 2
    assert store.count == 1
    assert {h.document_id for h in store.search(emb.embed_query("revenue vacation"), top_k=5)} == {"d2"}
    assert store.delete_document("d1") == 0 and store.delete_document("never-existed") == 0


def test_survives_a_restart(make_store, store):
    reopened = make_store()
    assert reopened.count == 3
    assert reopened.search(emb.embed_query("dividend policy"), top_k=1)[0].chunk_id == "d1_1"


def test_page_number_document_name_and_section_round_trip(make_store):
    s = make_store()
    add(s, chunks_for("d9", ["Alpha beta gamma delta."], section="Introduction"))
    add(s, chunks_for("d8", ["Epsilon zeta eta theta."], section=None))
    hit = s.search(emb.embed_query("alpha beta gamma delta"), top_k=1)[0]
    assert (hit.document_name, hit.page_number, hit.section) == ("d9.pdf", 1, "Introduction")
    other = s.search(emb.embed_query("epsilon zeta eta theta"), top_k=1)[0]
    assert other.section is None


def test_dimension_and_length_mismatches_are_rejected(store):
    with pytest.raises(ValueError):
        store.add(chunks_for("d3", ["Some text here."]), np.ones((1, 8), dtype="float32"))
    with pytest.raises(ValueError):
        store.add(chunks_for("d3", ["one text", "two text"]), np.ones((1, 256), dtype="float32"))


def test_adding_nothing_is_a_no_op(store):
    store.add([], np.empty((0, 256), dtype="float32"))
    assert store.count == 3


def test_both_backends_find_the_same_best_chunk(tmp_path):
    pytest.importorskip("chromadb")
    from app.rag.chroma_store import ChromaVectorStore

    faiss_store, chroma_store = VectorStore(tmp_path / "f"), ChromaVectorStore(tmp_path / "c")
    texts = [f"document {i} talks about topic{i % 7} and subject{i % 11} in section{i % 5}" for i in range(60)]
    for s in (faiss_store, chroma_store):
        add(s, chunks_for("d1", texts))
    for query in ("document 17", "document 42", "document 5"):  # each number token appears in one chunk only
        q = emb.embed_query(query)
        assert faiss_store.search(q, 1)[0].chunk_id == chroma_store.search(q, 1)[0].chunk_id
