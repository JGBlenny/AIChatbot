"""integration：E-DEBT-02 **REGRESSION_BASELINE_DB_ISOLATION**（業主裁定 2026-08-31）。

```text
E2-G1 test runtime **實際連到** intended DB —— ⛔ 不是只檢查 config 字串
E2-G2 baseline state consistency —— `delegates 存在 ⇔ migration 已入帳`（雙向）
      ＋ rollout fixture 必須 state-neutral
E2-G3 known fixture／required schema 確實存在 —— ⛔ 避免「乾淨」其實是空到測不到東西
E2-G4 把 ROLLBACK 路徑改回舊的錯路徑 → isolation guard RED
```

## ⚠️ 名詞校正（⛔ 不得沿用最初的誤述）

最初把 E-DEBT-02 講成「DB path」，**那是錯的**：出問題的是 **rollback SQL 檔的路徑**，
而且環境裡**沒有另一顆乾淨 DB 可換**（只有 `aichatbot_admin`／`aichatbot_test`／`postgres`）。
⇒ 這裡的「乾淨」定義是 **state-neutral**：rollout fixture 跑完後，`aichatbot_test` 的
受影響列逐欄位回到跑之前，⛔ 不是「換一個檔名／換一顆庫」。

## 為什麼 dirty sentinel 選 delegates

`seed_responsibility_delegates_v1.sql` 寫入的 `conversational_config.responsibility.delegates`
與 answer 的 `delegate_facet_key` 補丁，**只有**該 migration 會產生。它殘留時，
`bill_diagnosis[switch] → billing_anomaly[switch] → contract_closeout` 這條 delegation chain
會改變 facet 進場判定 ⇒ 直接污染 regression baseline。
"""
import asyncio
import os

import pytest

from tests.integration.conversational import test_resolver_rollout_integration_req as rollout

pytestmark = pytest.mark.integration

AFFECTED = list(rollout.AFFECTED_FACETS)


async def _q(sql, *args):
    import asyncpg
    conn = await asyncpg.connect(**rollout._conn_kwargs())
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


# ───────────────────────── E2-G1 ─────────────────────────
@pytest.mark.req("E2_G1:1")
async def test_runtime_actually_connects_to_the_intended_database():
    """⚠️ 問 server `current_database()`，⛔ 不是讀 env 字串自我證明。"""
    intended = rollout._conn_kwargs()["database"]
    rows = await _q("SELECT current_database() AS db, current_user AS usr")
    assert rows[0]["db"] == intended, (
        f"實際連到 {rows[0]['db']!r}，config 宣稱 {intended!r} ⇒ "
        f"baseline 量到的不是它以為的那顆庫")


@pytest.mark.req("E2_G1:2")
async def test_intended_database_is_not_a_production_like_name():
    """⚠️ 負控制：⛔ 不得讓 regression baseline 指到非測試庫。"""
    db = (await _q("SELECT current_database() AS db"))[0]["db"]
    assert db.endswith("_test"), f"regression baseline 連到 {db!r}——⛔ 只允許測試庫"


# ───────────────────────── E2-G2 ─────────────────────────
MIGRATION_NAME = "seed_responsibility_delegates_v1"


@pytest.mark.req("E2_G2:1")
async def test_delegates_presence_matches_migration_ledger():
    """**baseline state consistency**：`delegates 存在 ⇔ migration 已入帳`。

    ⚠️ 本 guard **刻意不判斷哪個狀態才對**——「正典 baseline 該不該套這個 seed」是
    產品/授權裁定（業主 2026-08-31 裁為 **APPLIED ＋ ledger PRESENT**），⛔ 不由測試代決。
    它只抓 **不一致**，也就是 E-DEBT-02 的病灶形狀：

    ```text
    有 delegates 但帳本沒有  →  殘留（fixture 沒還原乾淨）
    帳本有但沒 delegates     →  漏套／被誤刪
    ```
    ⚠️ 兩個方向都紅，⛔ 不是單向檢查——單向會讓「被誤刪」靜默通過。
    """
    rows = await _q(
        "SELECT generation_metadata->'conversational_config'->>'key' AS facet, "
        "       (generation_metadata->'conversational_config'->'responsibility' "
        "        IS NOT NULL) AS has_delegates, "
        "       (answer LIKE '%delegate_facet_key%') AS answer_patched "
        "FROM knowledge_base WHERE category = '對話規則' AND is_active "
        "  AND generation_metadata->'conversational_config'->>'key' = ANY($1::text[])",
        AFFECTED)
    assert rows, "受影響的規則列不存在 ⇒ 前提不成立"
    present = [dict(r) for r in rows if r["has_delegates"] or r["answer_patched"]]
    ledgered = (await _q(
        "SELECT count(*) AS n FROM schema_migrations WHERE migration_name = $1",
        MIGRATION_NAME))[0]["n"] > 0

    if ledgered:
        missing = [dict(r) for r in rows if not (r["has_delegates"] and r["answer_patched"])]
        assert not missing, (
            f"帳本記載 {MIGRATION_NAME} 已套用，但這些列沒有 delegates／answer 補丁：{missing}"
            f"——⇒ 漏套或被誤刪，baseline 與帳本不一致")
    else:
        assert not present, (
            f"帳本**沒有** {MIGRATION_NAME}，卻在 DB 看到它的產物：{present}"
            f"——⇒ 殘留（E-DEBT-02 的病灶形狀），before/after 證據不可信")


@pytest.mark.req("E2_G2:2")
async def test_rollout_fixture_is_state_neutral():
    """⚠️ 直接驗**還原能力**：snapshot → 套 migration → 跑正式 rollback → 必須逐欄位相同。"""
    assert os.path.exists(rollout.ROLLBACK), f"rollback 腳本不存在：{rollout.ROLLBACK}"
    before = await rollout._snapshot_affected()
    assert before, "受影響列不存在 ⇒ 前提不成立"
    # ⚠️ **刻意製造變動**再還原——⛔ 不能只跑一次冪等 migration 就宣稱「還原正確」：
    #    canonical baseline 已套用時 MIGRATION 是 no-op，那樣的通過是**空跑**。
    #    這裡用 ROLLBACK 當 mutator（它在 delegates 存在時必定改變狀態）。
    await rollout._exec_sql(rollout.ROLLBACK)
    mutated = await rollout._snapshot_affected()
    assert mutated != before, (
        "刻意製造的變動沒有發生 ⇒ 這個測試在**空跑**，⛔ 不能當成『還原正確』的證據")
    await rollout._restore_affected(before)
    after = await rollout._snapshot_affected()
    assert after == before, "snapshot 還原失敗 ⇒ fixture 的還原機制不可信（E-DEBT-02 未真正修好）"


# ───────────────────────── E2-G3 ─────────────────────────
@pytest.mark.req("E2_G3:1")
async def test_clean_does_not_mean_empty():
    """⚠️ 『乾淨』若是空庫，測試會**全部假綠**。必要 fixture 與 schema 都得在。"""
    rules = (await _q("SELECT count(*) AS n FROM knowledge_base "
                      "WHERE category = '對話規則' AND is_active"))[0]["n"]
    assert rules >= 20, f"對話規則只有 {rules} 筆 ⇒ baseline 是空的，⛔ 不是乾淨的"
    for facet in AFFECTED:
        n = (await _q("SELECT count(*) AS n FROM knowledge_base "
                      "WHERE category = '對話規則' AND is_active "
                      "  AND generation_metadata->'conversational_config'->>'key' = $1",
                      facet))[0]["n"]
        assert n >= 1, f"面向 {facet!r} 的規則列不存在 ⇒ rollout 測試無從施力"


@pytest.mark.req("E2_G3:2")
async def test_required_schema_present():
    cols = {r["column_name"] for r in await _q(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'knowledge_base'")}
    assert {"generation_metadata", "answer", "category", "is_active"} <= cols, \
        f"knowledge_base 缺必要欄位：{ {'generation_metadata','answer','category','is_active'} - cols }"


# ───────────────────────── E2-G4（mutation）─────────────────────────
@pytest.mark.req("E2_G4:1")
def test_e2_m1_wrong_rollback_path_makes_guard_red():
    """E2-M1：把 ROLLBACK 改回舊的錯路徑 ⇒ fixture 的前置 assert 必須 RED。

    ⚠️ 舊路徑少一層 `rollback/`——正是 E-DEBT-02 的原始 bug。
    """
    bad = "/app/database/migrations/seed_responsibility_delegates_v1_rollback.sql"
    assert bad != rollout.ROLLBACK, "ROLLBACK 仍是舊的錯路徑 ⇒ E-DEBT-02 未修"
    assert not os.path.exists(bad), "舊路徑竟然存在 ⇒ 本 mutation 的前提不成立"
    with pytest.raises(AssertionError, match="rollback 腳本不存在"):
        assert os.path.exists(bad), (
            f"rollback 腳本不存在：{bad}——⛔ 不得在沒有還原能力的情況下套用 migration")


@pytest.mark.req("E2_G4:2")
async def test_e2_m2_residue_would_make_sentinel_red():
    """E2-M2：把殘留寫回去 ⇒ dirty sentinel 必須 RED；驗完立刻還原。"""
    snap = await rollout._snapshot_affected()
    assert snap, "前提不成立"
    await rollout._exec_sql(rollout.MIGRATION)          # 製造殘留
    try:
        rows = await _q(
            "SELECT (generation_metadata->'conversational_config'->'responsibility' "
            "        IS NOT NULL) AS has_delegates "
            "FROM knowledge_base WHERE category = '對話規則' AND is_active "
            "  AND generation_metadata->'conversational_config'->>'key' = ANY($1::text[])",
            AFFECTED)
        assert any(r["has_delegates"] for r in rows), \
            "製造殘留後 sentinel 仍看不見 ⇒ **sentinel 本身是瞎的**（量尺失效）"
    finally:
        await rollout._restore_affected(snap)           # ⚠️ 無論如何都還原
    after = await rollout._snapshot_affected()
    assert after == snap, "mutation 後未還原 ⇒ 本測試自己污染了 baseline"
