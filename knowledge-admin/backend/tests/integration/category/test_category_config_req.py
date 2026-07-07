"""integration:category-config 兩層 + 守門 + 連動清理 + 篩選父層展開。固化手動 T1–T8。"""
import pytest

pytestmark = pytest.mark.integration

P, C, LEAF = "__qa_parent__", "__qa_child__", "__qa_leaf__"
K1, K2 = "__qa_cat_test1", "__qa_cat_test2"


def _cleanup(db):
    with db.cursor() as cur:
        cur.execute("DELETE FROM knowledge_base WHERE question_summary IN (%s,%s)", (K1, K2))
        cur.execute("DELETE FROM category_config WHERE category_value IN (%s,%s,%s)", (P, C, LEAF))


def _cat(client, value):
    cats = client.get("/api/category-config", params={"include_inactive": True}).json()["categories"]
    return next((c for c in cats if c["category_value"] == value), None)


def test_two_level_guard_rejects_child_as_parent(client, db):
    _cleanup(db)
    try:
        assert client.post("/api/category-config", json={"category_value": P, "display_name": P}).status_code == 200
        assert client.post("/api/category-config", json={"category_value": C, "display_name": C, "parent_value": P}).status_code == 200
        # C 已是子層,拿它當別人父層 → 400(維持兩層)
        r = client.post("/api/category-config", json={"category_value": LEAF, "display_name": LEAF, "parent_value": C})
        assert r.status_code == 400, r.text
    finally:
        _cleanup(db)


def test_usage_aggregate_delete_guard_and_cascade(client, db):
    _cleanup(db)
    try:
        client.post("/api/category-config", json={"category_value": LEAF, "display_name": LEAF})
        with db.cursor() as cur:
            cur.execute("INSERT INTO knowledge_base (question_summary,answer,categories,is_active) VALUES (%s,'a',ARRAY[%s],TRUE)", (K1, LEAF))
        cid = _cat(client, LEAF)["id"]
        # 使用數 = 1
        assert _cat(client, LEAF)["usage_count"] == 1
        # 刪除使用中 → 只停用
        r = client.delete(f"/api/category-config/{cid}")
        assert r.status_code == 200 and "停用" in r.json()["message"]
        assert _cat(client, LEAF)["is_active"] is False
        # 連動清理 → 從知識移除
        r = client.post(f"/api/category-config/{cid}/remove-from-knowledge")
        assert r.status_code == 200 and r.json()["removed_count"] == 1
        with db.cursor() as cur:
            cur.execute("SELECT categories FROM knowledge_base WHERE question_summary=%s", (K1,))
            assert cur.fetchone()[0] == []
    finally:
        _cleanup(db)


def test_parent_with_children_blocks_delete(client, db):
    _cleanup(db)
    try:
        client.post("/api/category-config", json={"category_value": P, "display_name": P})
        client.post("/api/category-config", json={"category_value": C, "display_name": C, "parent_value": P})
        pid = _cat(client, P)["id"]
        assert client.delete(f"/api/category-config/{pid}").status_code == 400  # 有子分類
    finally:
        _cleanup(db)


def test_knowledge_filter_parent_expansion(client, db):
    _cleanup(db)
    try:
        client.post("/api/category-config", json={"category_value": P, "display_name": P})
        client.post("/api/category-config", json={"category_value": C, "display_name": C, "parent_value": P})
        with db.cursor() as cur:
            cur.execute("INSERT INTO knowledge_base (question_summary,answer,categories,is_active) VALUES (%s,'a',ARRAY[%s],TRUE)", (K2, C))
        # 篩父層 P → 展開到子層 C → 撈到該知識
        r = client.get("/api/knowledge", params={"category": P, "limit": 100})
        assert r.status_code == 200
        titles = [k["question_summary"] for k in r.json()["items"]]
        assert K2 in titles
    finally:
        _cleanup(db)
