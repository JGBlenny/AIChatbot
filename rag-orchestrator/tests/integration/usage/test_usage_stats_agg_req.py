"""integration：usage 統計聚合正確性（任務 3.2｜R2.1/2.2/4.1-4.4/5.3）。

固定種子事件（session 前綴 aggtest_，離今 2 日避開真流量）斷言各量值：
訊息/對話跨日首日歸屬/去重使用者/token/內部排除切換/重查冪等/不含 user_id 明細。
活體（admin API＋DB），RUN_INTEGRATION=1 啟用。
"""
import json
import os
import uuid
import datetime as dt

import pytest

pytestmark = pytest.mark.integration

ADMIN = os.getenv("ADMIN_API_URL", "http://localhost:8087")
D1 = (dt.date.today() - dt.timedelta(days=2)).isoformat()
D2 = (dt.date.today() - dt.timedelta(days=1)).isoformat()


def _db():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"))


SEEDS = [
    # (date, session, user, vendor, user_type, internal, pt, ct, status)
    (D1, "aggtest_s1", "u1", 901, "property_manager", False, 100, 10, "success"),
    (D1, "aggtest_s1", "u1", 901, "property_manager", False, 200, 20, "success"),
    (D1, "aggtest_s2", "u2", 901, "tenant",           False, 50,  5,  "error"),
    (D2, "aggtest_s1", "u1", 901, "property_manager", False, 300, 30, "success"),  # 跨日同 session→歸 D1
    (D2, "aggtest_s3", "u1", 902, "property_manager", False, 10,  1,  "success"),
    (D1, "aggtest_sI", "u9", 901, "property_manager", True,  999, 99, "success"),  # internal
]


@pytest.fixture(scope="module")
def seeded():
    import requests
    try:
        tok = requests.post(f"{ADMIN}/api/auth/login",
                            json={"username": "admin", "password": "admin123"}, timeout=5
                            ).json().get("access_token")
        assert tok
    except Exception:
        pytest.skip("admin API 不可達")
    conn = _db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM usage_events WHERE session_id LIKE 'aggtest_%'")
        for i, (d, sid, uid, vid, ut, internal, pt, ct, st) in enumerate(SEEDS):
            cur.execute("""INSERT INTO usage_events
                (request_id, ts, date_tpe, vendor_id, mode, user_type, user_id, session_id,
                 is_internal, internal_kind, message_len, status, llm_calls,
                 prompt_tokens, completion_tokens, est_cost_usd)
                VALUES (%s, %s::date + interval '3 hour' + (%s * interval '1 minute'),
                        %s, %s, 'b2b', %s, %s, %s, %s, %s, 10, %s, 1, %s, %s, 0.001)""",
                (str(uuid.uuid4()), d, i, d, vid, ut, uid, sid,
                 internal, 'backtest' if internal else None, st, pt, ct))
    conn.commit()
    yield tok
    with conn.cursor() as cur:
        cur.execute("DELETE FROM usage_events WHERE session_id LIKE 'aggtest_%'")
    conn.commit()
    conn.close()


def _stats(tok, **params):
    import requests
    base = {"date_from": D1, "date_to": D2, "vendor_id": ["901", "902"]}
    base.update(params)
    r = requests.get(f"{ADMIN}/api/usage/stats", params=base,
                     headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def test_totals_exclude_internal_by_default(seeded):
    d = _stats(seeded)
    assert d["totals"]["messages"] == 5           # 6 種子 - 1 internal
    assert d["totals"]["prompt_tokens"] == 660    # 100+200+50+300+10
    assert d["totals"]["errors"] == 1


def test_session_first_day_attribution(seeded):
    """跨日 session（s1 在 D1/D2 皆有事件）只歸 D1（R2.2）。"""
    d = _stats(seeded)
    by_bucket = {}
    for g in d["groups"]:
        by_bucket.setdefault(g["bucket"], 0)
        by_bucket[g["bucket"]] += g["sessions"]
    assert by_bucket[D1] == 2                     # s1＋s2
    assert by_bucket[D2] == 1                     # s3（s1 不重計）


def test_include_internal_toggle(seeded):
    d = _stats(seeded, include_internal="true")
    assert d["totals"]["messages"] == 6


def test_requery_idempotent(seeded):
    assert _stats(seeded) == _stats(seeded)       # R4.2 重算冪等


def test_no_user_id_leak(seeded):
    d = _stats(seeded)
    assert "u1" not in json.dumps(d)              # R5.3 不回傳 user_id 明細
    for g in d["groups"]:
        assert "user_id" not in g


def test_bad_params_400(seeded):
    import requests
    r = requests.get(f"{ADMIN}/api/usage/stats",
                     params={"date_from": "bad", "date_to": D2},
                     headers={"Authorization": f"Bearer {seeded}"}, timeout=10)
    assert r.status_code == 400
