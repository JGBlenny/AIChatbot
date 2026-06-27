"""integration:知識 CRUD 生命週期(核心後台端點)。

TestClient + 真實 DB + 真實 embedding-api(create/update 會生成向量)。
需 RUN_INTEGRATION=1 + embedding-api 服務。
"""
import pytest

pytestmark = pytest.mark.integration

Q = "__qa_kb_crud_test__"


def _cleanup(db):
    with db.cursor() as cur:
        cur.execute("DELETE FROM knowledge_base WHERE question_summary = %s", (Q,))


def test_knowledge_crud_lifecycle(client, db):
    _cleanup(db)
    try:
        # 建立(生成 embedding)
        r = client.post("/api/knowledge", json={
            "question_summary": Q, "content": "原始答案",
            "categories": ["付款金流"], "keywords": ["繳費"],
        })
        assert r.status_code == 200, r.text
        kid = r.json()["id"]

        # DB 落地:categories 多值 + embedding 已生成
        with db.cursor() as cur:
            cur.execute(
                "SELECT question_summary, categories, embedding IS NOT NULL FROM knowledge_base WHERE id=%s",
                (kid,),
            )
            qs, cats, has_emb = cur.fetchone()
        assert qs == Q and cats == ["付款金流"] and has_emb is True

        # 讀取
        r = client.get(f"/api/knowledge/{kid}")
        assert r.status_code == 200 and Q in r.text

        # 更新(換 categories)
        r = client.put(f"/api/knowledge/{kid}", json={
            "question_summary": Q, "content": "更新後答案",
            "categories": ["帳單管理"], "keywords": [],
        })
        assert r.status_code == 200, r.text
        with db.cursor() as cur:
            cur.execute("SELECT categories FROM knowledge_base WHERE id=%s", (kid,))
            assert cur.fetchone()[0] == ["帳單管理"]

        # 刪除
        assert client.delete(f"/api/knowledge/{kid}").status_code == 200
        with db.cursor() as cur:
            cur.execute("SELECT 1 FROM knowledge_base WHERE id=%s", (kid,))
            assert cur.fetchone() is None
    finally:
        _cleanup(db)


def test_list_knowledge_returns_paged_shape(client):
    r = client.get("/api/knowledge", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body
