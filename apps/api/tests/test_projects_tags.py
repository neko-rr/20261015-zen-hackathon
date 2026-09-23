"""案件・タグ付き資料のテスト。"""

from fastapi.testclient import TestClient

from app.main import app
from app.rag import retrieve, upsert_index_entry

client = TestClient(app)


def _session() -> TestClient:
    started = TestClient(app)
    assert started.post("/sessions").status_code == 200
    return started


def test_project_create_and_material_filter() -> None:
    user = _session()
    created = user.post("/projects", json={"name": "夏の一枚"})
    assert created.status_code == 200
    project_id = created.json()["project"]["project_id"]

    uploaded = user.post(
        "/materials",
        params={"material_kind": "own_work", "project_id": project_id},
        files=[("files", ("ao.md", b"OC Aoki summer outfit", "text/markdown"))],
    )
    assert uploaded.status_code == 200
    doc = uploaded.json()["materials"][0]
    assert doc["project_id"] == project_id

    filtered = user.get("/materials", params={"project_id": project_id})
    assert len(filtered.json()["materials"]) == 1

    patched = user.patch(
        f"/materials/{doc['doc_id']}",
        json={"tags": ["OC:アオ", "衣装:夏服"]},
    )
    assert patched.status_code == 200
    assert patched.json()["material"]["tags"] == ["OC:アオ", "衣装:夏服"]

    listed = user.get("/materials")
    assert "OC:アオ" in listed.json()["tags"]


def test_retrieve_filters_by_project() -> None:
    owner = "owner-test-a"
    upsert_index_entry(
        owner,
        {
            "doc_id": "d1",
            "title": "a.md",
            "text": "tags: OC:アオ\ncat pose",
            "material_kind": "own_work",
            "project_id": "p1",
            "tags": ["OC:アオ"],
        },
    )
    upsert_index_entry(
        owner,
        {
            "doc_id": "d2",
            "title": "b.md",
            "text": "tags: OC:アオ\nother project cat",
            "material_kind": "own_work",
            "project_id": "p2",
            "tags": ["OC:アオ"],
        },
    )
    hits = retrieve(owner, "OC:アオ cat", project_id="p1")
    assert len(hits) == 1
    assert hits[0]["doc_id"] == "d1"


def test_delete_project_requires_empty() -> None:
    user = _session()
    project_id = user.post("/projects", json={"name": "作業中"}).json()["project"]["project_id"]
    user.post(
        "/materials",
        params={"material_kind": "third_party", "project_id": project_id},
        files=[("files", ("ref.txt", b"ref", "text/plain"))],
    )
    blocked = user.delete(f"/projects/{project_id}")
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "project_not_empty"
