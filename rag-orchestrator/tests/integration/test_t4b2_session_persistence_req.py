"""integration：T4-B2 form_sessions responsibility carrier 的 persistence round-trip。

```text
B2-G1 additive migration 已套：五個 nullable 欄位存在
B2-G2 **NO HISTORICAL BACKFILL**：既有列 session_authority_mode 全為 NULL
B2-G3 responsibility session 寫入→讀回，authority 四欄 **exact restore**
B2-G4 legacy session（mode NULL ＋ knowledge_id）行為不變，且仍被 application 視為 legacy
B2-G5 responsibility session 的 knowledge_id 必須 NULL（application invariant 在 DB 往返後仍成立）
```
⚠️ DB **⛔ 未加 enum／CHECK／NOT NULL**（業主明示）——不變量由 application 守；
   本層只證 **persistence transport** 不吃掉 authority。
"""
import os
import uuid

import pytest

from services import responsibility_session as rsess

pytestmark = [pytest.mark.integration]

psycopg2 = pytest.importorskip("psycopg2", reason="需要 psycopg2 才能驗 persistence")

DSN = dict(host=os.getenv("DB_HOST", "aichatbot-postgres"), port=int(os.getenv("DB_PORT", "5432")),
           user=os.getenv("DB_USER", "aichatbot"), dbname=os.getenv("DB_NAME", "aichatbot_admin"),
           password=os.getenv("DB_PASSWORD", "aichatbot123"))
NEW_COLS = ("session_authority_mode", "responsibility_id", "fulfillment_binding_id",
            "fulfillment_strategy", "input_contract_id")
R29 = dict(responsibility_id="R-29", fulfillment_binding_id="receipt.actual_amount.v1",
           fulfillment_strategy="CAPABILITY", input_contract_id="bill.by_ref.v1")


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg2.connect(**DSN)
    except Exception as e:                      # ⚠️ 環境不可用要標明，⛔ 不靜默 pass
        pytest.skip(f"env_skipped: DB 不可用（{e}）")
    c.autocommit = True
    yield c
    c.close()


@pytest.fixture
def form_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT form_id FROM form_schemas LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("env_skipped: form_schemas 無資料（FK 需要）")
    return row[0]


def _insert(conn, form_id, **cols):
    sid = f"t4b2-{uuid.uuid4().hex[:12]}"
    keys = ["session_id", "form_id", "state"] + list(cols)
    vals = [sid, form_id, "collecting"] + [cols[k] for k in cols]
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO form_sessions ({','.join(keys)}) "
                    f"VALUES ({','.join(['%s'] * len(keys))}) RETURNING id", vals)
        rid = cur.fetchone()[0]
    return sid, rid


def _read(conn, rid):
    cols = ("session_authority_mode", "responsibility_id", "fulfillment_binding_id",
            "fulfillment_strategy", "input_contract_id", "knowledge_id", "state")
    with conn.cursor() as cur:
        cur.execute(f"SELECT {','.join(cols)} FROM form_sessions WHERE id=%s", (rid,))
        return dict(zip(cols, cur.fetchone()))


def _cleanup(conn, rid):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM form_sessions WHERE id=%s", (rid,))


@pytest.mark.req("T4B2_G1:1")
def test_b2_g1_columns_exist(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_name='form_sessions' AND column_name = ANY(%s)", (list(NEW_COLS),))
        got = dict(cur.fetchall())
    assert set(got) == set(NEW_COLS), f"缺欄位：{set(NEW_COLS) - set(got)}"
    assert all(v == "YES" for v in got.values()), "⛔ 本刀不得加 NOT NULL"


@pytest.mark.req("T4B2_G2:1")
def test_b2_g2_no_historical_backfill(conn):
    """⚠️ 正對照：表內**有**歷史列，且其 mode 全為 NULL（⛔ 未被 backfill）。"""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), count(session_authority_mode) FROM form_sessions")
        total, non_null = cur.fetchone()
    assert total > 0, "表是空的 ⇒ 這條檢查無效（⛔ 不是「沒有 backfill」）"
    assert non_null == 0, "歷史列被 backfill 了 ⇒ 違反 LEGACY_SESSION_COMPATIBILITY"


@pytest.mark.req("T4B2_G3:1")
def test_b2_g3_authority_exact_restore(conn, form_id):
    sess = rsess.build_responsibility_session(**R29)
    _sid, rid = _insert(conn, form_id,
                        session_authority_mode=sess["session_authority_mode"],
                        **{k: sess[k] for k in rsess.AUTHORITY_FIELDS})
    try:
        got = _read(conn, rid)
        restored = {"session_authority_mode": got["session_authority_mode"],
                    "on_complete_action": rsess.ACTION_RESUME_FULFILLMENT,
                    "knowledge_id": got["knowledge_id"],
                    **{k: got[k] for k in rsess.AUTHORITY_FIELDS}}
        assert rsess.validate_session(restored) == rsess.MODE_RESPONSIBILITY
        plan = rsess.resume_fulfillment(restored, {"bill_ref": "716317"})
        for f in rsess.AUTHORITY_FIELDS:
            assert plan[f] == R29[f], f"{f} 經 DB 往返後改變"
    finally:
        _cleanup(conn, rid)


@pytest.mark.req("T4B2_G4:1")
def test_b2_g4_legacy_row_unchanged(conn, form_id):
    """legacy 列：mode NULL ＋ knowledge_id ⇒ 新欄位全 NULL，行為不變。"""
    _sid, rid = _insert(conn, form_id, knowledge_id=3496)
    try:
        got = _read(conn, rid)
        assert got["knowledge_id"] == 3496 and got["state"] == "collecting"
        assert all(got[c] is None for c in NEW_COLS), "legacy 列被寫入了 responsibility 欄位"
        legacy = {"session_authority_mode": rsess.MODE_LEGACY, "knowledge_id": got["knowledge_id"],
                  "on_complete_action": rsess.ACTION_SHOW_KNOWLEDGE}
        assert rsess.validate_session(legacy) == rsess.MODE_LEGACY
    finally:
        _cleanup(conn, rid)


@pytest.mark.req("T4B2_G5:1")
def test_b2_g5_responsibility_with_knowledge_id_is_conflict(conn, form_id):
    """⚠️ DB **允許**寫入（無 CHECK），但 application 讀回時必須 hard fail。"""
    sess = rsess.build_responsibility_session(**R29)
    _sid, rid = _insert(conn, form_id, knowledge_id=3496,
                        session_authority_mode=sess["session_authority_mode"],
                        **{k: sess[k] for k in rsess.AUTHORITY_FIELDS})
    try:
        got = _read(conn, rid)
        assert got["knowledge_id"] == 3496, "DB 這一層不擋（本刀刻意不加 CHECK）"
        restored = {"session_authority_mode": got["session_authority_mode"],
                    "on_complete_action": rsess.ACTION_RESUME_FULFILLMENT,
                    "knowledge_id": got["knowledge_id"],
                    **{k: got[k] for k in rsess.AUTHORITY_FIELDS}}
        with pytest.raises(rsess.SessionAuthorityConflict):
            rsess.validate_session(restored)
    finally:
        _cleanup(conn, rid)
