"""integration:api_keys CRUD 端點(TestClient + 真實 DB)。固化手動 E1–E2。"""
import hashlib

import pytest

pytestmark = pytest.mark.integration

NAME = "__qa_apikey_test__"


def _cleanup(db):
    with db.cursor() as cur:
        cur.execute("DELETE FROM api_keys WHERE name = %s", (NAME,))


def test_api_key_crud_and_no_secret_leak(client, db):
    _cleanup(db)
    try:
        # 建立 → 回明文一次 + 前綴
        r = client.post("/api/api-keys", json={"name": NAME, "description": "t"})
        assert r.status_code == 200, r.text
        d = r.json()
        plain, kid = d["api_key"], d["id"]
        assert len(plain) > 20 and d["key_prefix"] == plain[:8]

        # DB 存的是 hash 不是明文
        with db.cursor() as cur:
            cur.execute("SELECT key_hash, key_prefix FROM api_keys WHERE id=%s", (kid,))
            key_hash, prefix = cur.fetchone()
        assert key_hash == hashlib.sha256(plain.encode()).hexdigest()
        assert prefix == plain[:8]

        # 列表:不洩漏明文/hash,只露前綴
        item = [k for k in client.get("/api/api-keys").json()["api_keys"] if k["name"] == NAME][0]
        assert "api_key" not in item and "key_hash" not in item
        assert item["key_prefix"] == plain[:8]

        # 停用
        assert client.put(f"/api/api-keys/{kid}", json={"is_active": False}).status_code == 200
        with db.cursor() as cur:
            cur.execute("SELECT is_active FROM api_keys WHERE id=%s", (kid,))
            assert cur.fetchone()[0] is False

        # 刪除
        assert client.delete(f"/api/api-keys/{kid}").status_code == 200
        with db.cursor() as cur:
            cur.execute("SELECT 1 FROM api_keys WHERE id=%s", (kid,))
            assert cur.fetchone() is None
    finally:
        _cleanup(db)


def test_create_rejects_blank_name(client, db):
    r = client.post("/api/api-keys", json={"name": "  "})
    assert r.status_code == 400
