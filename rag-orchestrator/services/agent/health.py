"""Agent 健康檢查核心邏輯（spec agentic-mcp-orchestration・任務 1.8）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 4（`/api/v1/agent/health`
段落）。⛔ 本檔不建路由——`routers/agent.py` 是唯一呼叫端；`services/pipeline_health_service.py`
的 `Agent` 子項 checker 也呼叫本函式（同一份邏輯，⛔ 不複製）。

## 這個端點在量什麼
1. **工具可達**：`registry` 有 spec（`union_specs` 非空）；`kb.get` 以固定假身分＋
   必然不存在的數字 `kb_id` 直呼（**不經 `registry.call()`**，避免混進速率限制／
   計量——這是健康探針，不是一次真實工具呼叫）。`ToolResult(error="NO_MATCH")`
   即代表 DB／可見性謂詞這條路線可達；探針本身丟例外（連線失敗等）才算紅。
2. **大綱 version／sha**（3.2 未落地）與 **rules_sha**（2.3 未落地）：固定回
   `"pending"`，⛔ 不算紅——這是「尚未建置」不是「建置後壞了」。
3. **DSP-011 前提偵測四項**（`mcp_facade.premise_stats()`；design 元件 4）：
   `mcp_calls_by_api_key`／`vendor_not_in_table`／`origin_not_allowed` 任一非零，
   或 `enforce_off_with_mcp_traffic` 為真 ⇒ 列入 `premise.red_flags` 並致紅。
   ⚠️ 第一項非零**不代表出事**——`/mcp` 是刻意的低量非公開通道，這是「有流量了，
   去看一眼是不是預期中的呼叫方」的告警，不是錯誤（見 mcp_facade 模組 docstring
   「兩條 P0 REJECT 的補償條件」）。
4. **MCP SDK 是否可匯入**（`mcp_sdk_available()`）：DSP-014 A 之後 SDK 已是正式
   相依，這裡只是防禦性守衛；否 ⇒ `"unavailable (DSP-014)"`，⛔ 不算紅
   （`/mcp` 服務層閘仍生效，只是工具面未掛載）。
5. **`api_keys` 的 agent 作用域兩欄是否已建**（`api_keys_agent_scope_ready`，1.10 P2）：
   否 ⇒ **紅**。理由：`is_internal`／`vendor_ids` 缺欄時 `verify_api_key` 會降級成
   `vendor_ids=None`，而那個值的語義是「**不限業者**」——migration 沒套等於每一把 key
   都變成全業者通行，卻沒有任何地方會叫。
   ⚠️ **有 pool 才驗得準**：呼叫端有給 `get_api_key_pool` 時當場探測；沒給時只讀
   `api_key_auth.agent_scope_cols_state()` 的行程級快取，該行程若還沒驗過任何
   API key 就是 `None`＝**尚未證明** ⇒ 一樣算紅（⛔ 不把「不知道」印成綠）。
   `RAG_API_AUTH_ENFORCE` 開著時每個非豁免請求都會驗 key，快取通常在第一個
   請求就被填上。

HTTP 一律 200（健檢 API 慣例，見任務 brief）；紅以 `status` 欄位表達，
⛔ 不藉由 non-2xx 讓呼叫端誤判成「這支 API 本身壞了」。
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from services import api_key_auth
from services.agent import mcp_facade
from services.agent.identity import Identity, Stage
from services.agent.tools.kb import kb_get

#: 健康探針用的固定假身分——不落地任何真實呼叫方資料。
#: ⚠️ `mode="b2b"` 是刻意的：`build_visibility_predicate` 的 b2c 分支會另外
#: 查 `vendors` 表取業態（`VendorParameterResolver.get_vendor_info`，走它自己
#: 的 DB 連線，與這裡的 `get_kb_pool` 無關）；b2b 分支固定用
#: `business_types=['system_provider']`、不觸發那次額外查詢，讓這個探針只測
#: 一條路徑（`fetch_visible_row` 走 `get_kb_pool`）。
_PROBE_IDENTITY = Identity(
    vendor_id=None, target_user="tenant", mode="b2b", session_id="agent-health-probe"
)
#: 必然不存在的數字 kb_id（`fetch_visible_row` 對它一律回 `None` ⇒ `NO_MATCH`）。
_PROBE_KB_ID = "0"


async def _check_kb_reachable(get_kb_pool: Optional[Callable[[], Any]]) -> tuple:
    """回傳 `(reachable, detail)`。

    `NO_MATCH`（含 `INVALID_INPUT`——理論上不會發生，`_PROBE_KB_ID` 固定合法）
    都代表探針跑完全程，DB／謂詞可達；只有探針本身拋例外才算不可達。
    """
    pool = get_kb_pool() if get_kb_pool else None
    if pool is None:
        return False, "kb_pool unavailable"
    try:
        await kb_get(_PROBE_IDENTITY, {"kb_id": _PROBE_KB_ID}, db_pool=pool)
    except Exception as e:  # noqa: BLE001 — 探針：任何例外都代表這條路線不可達
        return False, f"{type(e).__name__}: {e}"
    return True, "ok"


_SCOPE_NOT_READY = (
    "api_keys 缺 is_internal／vendor_ids（migration "
    "20260904_api_keys_agent_scope.sql 未套）⇒ verify_api_key 降級成 "
    "vendor_ids=None＝不限業者"
)


async def _check_agent_scope_ready(get_api_key_pool) -> tuple:
    """回傳 `(ready, detail)`；`ready` 只有在**兩欄都證實存在**時才是 True。"""
    pool = get_api_key_pool() if get_api_key_pool else None
    if pool is not None:
        ready = await api_key_auth.detect_agent_scope_cols(pool)
        return ready, ("ok" if ready else _SCOPE_NOT_READY)
    state = api_key_auth.agent_scope_cols_state()
    if state is True:
        return True, "ok（沿用行程級偵測快取）"
    if state is False:
        return False, _SCOPE_NOT_READY
    return False, ("尚未偵測——本行程還沒驗過任何 API key，健檢也沒拿到可探測的 pool；"
                   "⛔ 不把「不知道」當成 ready")


def _premise_flags(stats: dict) -> list:
    """DSP-011 前提偵測四項：前三項任一非零，或第四項為真 ⇒ 列名。"""
    flags = []
    if stats.get("mcp_calls_by_api_key"):
        flags.append("mcp_calls_by_api_key")
    if stats.get("vendor_not_in_table"):
        flags.append("vendor_not_in_table")
    if stats.get("origin_not_allowed"):
        flags.append("origin_not_allowed")
    if stats.get("enforce_off_with_mcp_traffic"):
        flags.append("enforce_off_with_mcp_traffic")
    return flags


async def compute_agent_health(
    *,
    registry,
    get_kb_pool: Optional[Callable[[], Any]],
    stage: Stage,
    get_api_key_pool: Optional[Callable[[], Any]] = None,
) -> dict:
    """`/api/v1/agent/health` 與 `system_health` 的 `Agent` 子項共用的核心邏輯。

    Args:
        registry: `ToolRegistry`（`mcp_facade.build_registry()` 建的那份）。
        get_kb_pool: `kb.get` 用的 psycopg2 風格 pool getter（可為 `None`）。
        stage: 部署里程碑（`mcp_facade.current_stage()`）。
        get_api_key_pool: `api_keys` 欄位偵測用的 **asyncpg** pool getter
            （可為 `None`；沒給就只讀行程級偵測快取，見模組 docstring 第 5 點）。

    Returns:
        `{"status": "ok" | "red", "checks": {...}}`。
    """
    specs = mcp_facade.union_specs(registry, stage)
    spec_count = len(specs)

    kb_reachable, kb_detail = await _check_kb_reachable(get_kb_pool)

    sdk_ok, sdk_reason = mcp_facade.mcp_sdk_available()

    stats = mcp_facade.premise_stats()
    flags = _premise_flags(stats)

    scope_ready, scope_detail = await _check_agent_scope_ready(get_api_key_pool)

    red = spec_count == 0 or not kb_reachable or bool(flags) or not scope_ready

    return {
        "status": "red" if red else "ok",
        "checks": {
            "tools": {
                "spec_count": spec_count,
                "kb_get_reachable": kb_reachable,
                "detail": kb_detail,
            },
            "outline_version": "pending",
            "rules_sha": "pending",
            "premise": {
                "mcp_calls_by_api_key": stats.get("mcp_calls_by_api_key", {}),
                "vendor_not_in_table": stats.get("vendor_not_in_table", 0),
                "origin_not_allowed": stats.get("origin_not_allowed", 0),
                "enforce_off_with_mcp_traffic": stats.get(
                    "enforce_off_with_mcp_traffic", False
                ),
                "metering_unavailable": stats.get("metering_unavailable", 0),
                "red_flags": flags,
            },
            "mcp_sdk": "ok" if sdk_ok else "unavailable (DSP-014)",
            "api_keys_agent_scope_ready": scope_ready,
            "api_keys_agent_scope_detail": scope_detail,
        },
    }
