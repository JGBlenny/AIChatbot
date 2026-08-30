"""integration：B4-M1 —— 證明 legacy `tenant_keyword → user_id` wiring **確實存在**。

⚠️ 這是 `resolve_tenant_summary` 負控制的**前提事實**：若 legacy wiring 已改，
`identity assumed, not resolved` 的判定就要重審。
⚠️ 放 integration 層（需 DB），⛔ 不在 unit 層 shell out docker。
"""
import json
import os

import pytest

pytestmark = [pytest.mark.integration]

psycopg2 = pytest.importorskip("psycopg2", reason="需要 psycopg2 才能查 form_schemas")

DSN = dict(host=os.getenv("DB_HOST", "aichatbot-postgres"), port=int(os.getenv("DB_PORT", "5432")),
           user=os.getenv("DB_USER", "aichatbot"), dbname=os.getenv("DB_NAME", "aichatbot_admin"),
           password=os.getenv("DB_PASSWORD", "aichatbot123"))


@pytest.mark.req("T4B4_M1:1")
def test_legacy_tenant_wiring_passes_keyword_as_user_id():
    try:
        conn = psycopg2.connect(**DSN)
    except Exception as e:
        pytest.skip(f"env_skipped: DB 不可用（{e}）")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT api_config FROM form_schemas WHERE form_id='jgb_tenant_query'")
            row = cur.fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        pytest.skip("env_skipped: 本 DB 無 jgb_tenant_query 表單定義")
    cfg = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    params = cfg.get("params") or {}
    if isinstance(params, str):
        params = json.loads(params)
    assert params.get("user_id") == "{form.tenant_keyword}", (
        "legacy wiring 已改變 ⇒ 需重審 `identity assumed, not resolved` 判定："
        f"實得 {params.get('user_id')!r}")
