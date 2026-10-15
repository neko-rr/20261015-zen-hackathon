"""File Search は人のストアだけを使い、他人の断片は捨てる。"""

from types import SimpleNamespace

from app import file_search
from app.rag import retrieve, upsert_index_entry


def _chunk(doc_id: str, text: str, document_name: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        retrieved_context=SimpleNamespace(
            text=text,
            title="note",
            document_name=document_name,
            page_number="",
            custom_metadata=[SimpleNamespace(key="doc_id", string_value=doc_id)],
        )
    )


def test_hits_drop_other_owners_and_projects() -> None:
    rows = [
        {
            "doc_id": "mine",
            "title": "a.md",
            "text": "summer kimono",
            "material_kind": "own_work",
            "project_id": "p1",
            "tags": [],
            "file_search_document": "fileSearchStores/aaa/documents/mine",
        }
    ]
    hits = file_search.hits_from_chunks(
        [
            _chunk("mine", "夏の着物"),
            _chunk("other-user", "secret notes"),
            _chunk("mine-other-project", "ignored"),
        ],
        rows,
        "p1",
        4,
    )
    assert [hit["doc_id"] for hit in hits] == ["mine"]
    assert hits[0]["text"] == "夏の着物"


def test_metadata_filter_rejects_unsafe_values() -> None:
    assert file_search.metadata_filter("p1") == 'project_id = "p1"'
    assert file_search.metadata_filter('p1" or true') is None
    assert file_search.metadata_filter("") is None


def test_retrieve_uses_semantic_hits(monkeypatch) -> None:
    owner = "owner-semantic"
    upsert_index_entry(
        owner,
        {
            "doc_id": "d1",
            "title": "pose.md",
            "text": "腕を上げた立ち姿",
            "material_kind": "own_work",
            "project_id": "",
            "tags": [],
        },
    )
    monkeypatch.setattr("app.rag.rag_engine_enabled", lambda: True)

    def fake_search(owner_id, query, rows, limit, project_id):
        assert owner_id == owner
        assert "raised arm" in query
        return [
            {
                "url": "material://d1",
                "title": "pose.md",
                "text": "腕を上げた立ち姿",
                "material_kind": "own_work",
                "media_type": "note",
                "page": "unknown",
                "doc_id": "d1",
                "project_id": "",
                "tags": [],
            }
        ]

    monkeypatch.setattr("app.file_search.search", fake_search)
    hits = retrieve(owner, "raised arm standing")
    assert hits[0]["doc_id"] == "d1"


def test_retrieve_falls_back_to_keywords(monkeypatch) -> None:
    owner = "owner-keyword"
    upsert_index_entry(
        owner,
        {
            "doc_id": "d9",
            "title": "note.md",
            "text": "exact token apricot",
            "material_kind": "third_party",
            "project_id": "",
            "tags": [],
        },
    )
    monkeypatch.setattr("app.rag.rag_engine_enabled", lambda: True)
    monkeypatch.setattr("app.file_search.search", lambda *args, **kwargs: [])
    hits = retrieve(owner, "apricot")
    assert hits[0]["doc_id"] == "d9"


def test_remove_document_stays_inside_owner_store(monkeypatch) -> None:
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    file_search._stores["owner-a"] = "fileSearchStores/aaa"
    deleted: list[str] = []

    class Docs:
        def delete(self, *, name: str) -> None:
            deleted.append(name)

    class Stores:
        documents = Docs()

    class Client:
        file_search_stores = Stores()

    monkeypatch.setattr(file_search, "_client", lambda: Client())
    file_search.remove_document("owner-a", "fileSearchStores/bbb/documents/x")
    file_search.remove_document("owner-a", "fileSearchStores/aaa/documents/x")
    assert deleted == ["fileSearchStores/aaa/documents/x"]
    file_search._stores.pop("owner-a", None)
