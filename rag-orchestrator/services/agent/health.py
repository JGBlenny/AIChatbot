"""Agent 健康檢查核心邏輯（spec agentic-mcp-orchestration・任務 1.8）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 4（`/api/v1/agent/health`
段落）。⛔ 本檔不建路由——`routers/agent.py` 是唯一呼叫端；`services/pipeline_health_service.py`
的 `Agent` 子項 checker 也呼叫本函式（同一份邏輯，⛔ 不複製）。

## 這個端點在量什麼
1. **工具可達**：`registry` 有 spec（`union_specs` 非空）；`kb.get` 以固定假身分＋
   必然不存在的數字 `kb_id` 直呼（**不經 `registry.call()`**，避免混進速率限制／
   計量——這是健康探針，不是一次真實工具呼叫）。`ToolResult(error="NO_MATCH")`
   即代表 DB／可見性謂詞這條路線可達；探針本身丟例外（連線失敗等）才算紅。
2. **大綱 version／sha**（3.2 未接線）固定回 `"pending"`；**`rules_sha`**（任務 2.6）
   改讀 `app.state.agent_runtime.rules_sha`（由 `bootstrap.build_runtime` 在啟動
   時掛上，值＝`VerifierRules.load()` 對規則檔位元組算的 sha256）——**呼叫端要用
   `get_runtime` 把那個物件的 getter 交進來**；沒交、或 runtime 還沒建起來 ⇒ 回
   `"pending"`。兩者皆 ⛔ 不算紅：「尚未建置」不是「建置後壞了」。
   ⚠️ `rules_sha` 是**觀測值**——要判「這台機器帶的是哪一版尺」得拿它跟預期的
   sha 比對，那是部署驗收的事（5.1 回切演練），⛔ 不在本函式裡硬編一個期望值。
3. **DSP-011 前提偵測四項**（`mcp_facade.premise_stats()`；design 元件 4）：
   第一項（任務 2.8 修正語義）改判 `mcp_calls_flagged_by_api_key`——`/mcp`
   出現**未登錄**（`verify_api_key` 查無）或**已登錄但非 `is_internal`** 的
   `api_key_id` 才致紅；`mcp_calls_by_api_key` 整體分佈仍輸出為觀測值，⛔
   不再以「非零即紅」判。第二、三項（`vendor_not_in_table`／
   `origin_not_allowed`）任一非零，或第四項 `enforce_off_with_mcp_traffic`
   為真 ⇒ 同樣列入 `premise.red_flags` 並致紅。
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

6. **NLI 接地檢查（DSP-033）**：`nli_ready` 由 `nli-model` 的 `/health` **透傳**
   （該服務自己跑 canary＋權重目錄指紋比對，r18 F-6）——⛔ 本檔不重算、
   也不自己載模型驗一次。`nli_model_sha`／`nli_tau` 是觀測值。
   **致紅條件（F-10）**：
     * `nli_ready` 為 `false`（含探測失敗＝取不到）⇒ **紅**。
       「連不上」與「服務說自己不 ready」是同一件事：這台機器上的 Verifier
       正在跑降級尺，而降級尺比較鬆（62%／9% vs 69%／9%）。
     * 近 5 分鐘降級比率：`degraded/total > 2%` **連兩窗**、
       或**單窗 100% 且 turns ≥ 5** ⇒ 紅。
       ⚠️ 用比率不用次數：低流量時偶發一次降級不該告警，⛔ 但 100% 降級
       即使只有 5 個回合也一定要響——那代表 NLI 根本沒接上。
   ⚠️ **`get_runtime` 沒給／runtime 還沒建起來 ⇒ `"pending"`，⛔ 不算紅**
   （與 `rules_sha` 同一個慣例：「尚未建置」不是「建置後壞了」）。
   ⚠️ 部署順序後果：`bootstrap.build_runtime` **一定**會建出 NLI client，所以
   一旦本版上線而 `nli-model` 容器還沒起來，agent health 就會是紅的。這是
   刻意的（fail-loud），runbook 要先起 `nli-model` 再推 orchestrator。

HTTP 一律 200（健檢 API 慣例，見任務 brief）；紅以 `status` 欄位表達，
⛔ 不藉由 non-2xx 讓呼叫端誤判成「這支 API 本身壞了」。
"""
from __future__ import annotations

import time
from collections import deque
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


def _rules_sha(get_runtime: Optional[Callable[[], Any]]) -> str:
    """`app.state.agent_runtime.rules_sha`；取不到一律 `"pending"`（任務 2.6）。

    ⛔ 不在這裡 fallback 去 `VerifierRules.load(DEFAULT_RULES_PATH)` 自己算一次——
    健檢要回報的是「**這個行程實際帶著的那把尺**是哪一版」，重讀檔案只會得到
    「磁碟上現在是哪一版」，兩者不同時（改了檔沒重啟）健檢會給出綠色的假象。
    """
    if get_runtime is None:
        return "pending"
    try:
        runtime = get_runtime()
    except Exception:  # noqa: BLE001 — 健檢不因取值失敗而崩
        return "pending"
    return str(getattr(runtime, "rules_sha", "") or "") or "pending"


def _outline_sha(get_runtime: Optional[Callable[[], Any]]) -> str:
    """同 `_rules_sha`：回這個行程實際載入的大綱 sha（`bootstrap.build_runtime` 外掛的
    `runtime.outline_sha`），取不到 ⇒ `"pending"`。⛔ 不重組大綱來算。"""
    if get_runtime is None:
        return "pending"
    try:
        runtime = get_runtime()
    except Exception:  # noqa: BLE001
        return "pending"
    return str(getattr(runtime, "outline_sha", "") or "") or "pending"


#: DSP-033 F-10：降級告警的窗長與門檻（⛔ 常數，不吃 env——調它等於調告警靈敏度，
#: 那要走規則集／DECISIONS，不該是一個 env 就能悄悄關掉的東西）。
NLI_WINDOW_S = 300.0
NLI_DEGRADED_RATIO_RED = 0.02
NLI_SINGLE_WINDOW_MIN_TURNS = 5

#: 近 10 分鐘（兩個窗）的回合事件 `(ts, degraded)`。
#: ⚠️ 行程級、⛔ 不落 DB：它只回答「這台機器現在正不正常」，跨機彙總是
#: `usage_events.decision_snapshot.agent.violations` 的事（那裡有 `nli_degraded`）。
_NLI_TURNS: deque = deque()


def record_nli_turn(degraded: bool, *, now: Optional[float] = None) -> None:
    """每個 agent 回合結束時記一筆（`services/agent/runtime.py:run_turn`）。

    ⚠️ 一回合一筆，⛔ 不是一次 verifier 嘗試一筆——比率的分母是回合數。
    """
    ts = time.monotonic() if now is None else now
    _NLI_TURNS.append((ts, bool(degraded)))
    _prune_nli_turns(ts)


def _prune_nli_turns(now: float) -> None:
    cutoff = now - 2 * NLI_WINDOW_S
    while _NLI_TURNS and _NLI_TURNS[0][0] < cutoff:
        _NLI_TURNS.popleft()


def reset_nli_turns() -> None:
    """測試用：清掉行程級視窗。⛔ 產線路徑不呼叫。"""
    _NLI_TURNS.clear()


def _window_counts(now: float, start_ago: float, end_ago: float) -> tuple:
    """`(now-start_ago, now-end_ago]` 這個**左開右閉**窗內的 `(degraded, total)`。

    ⚠️ 右端刻意含 `now`：剛剛記下的那一筆就是最新的一筆，把它排除在當前窗外
    會讓「單窗 100%」在流量很低時永遠差最後一筆才成立——而那正是要抓的
    「NLI 根本沒接上」那種情況。兩個窗因此不重疊也不留縫。
    """
    lo, hi = now - start_ago, now - end_ago
    degraded = total = 0
    for ts, is_degraded in _NLI_TURNS:
        if lo < ts <= hi:
            total += 1
            degraded += 1 if is_degraded else 0
    return degraded, total


def nli_degraded_stats(*, now: Optional[float] = None) -> dict:
    """近 5 分鐘與其前一個 5 分鐘的降級比率，以及是否致紅（F-10）。

    🔴 `total == 0` 的窗**不參與判定**——沒有流量不等於一切正常，也不等於
    出事；把它算成 0% 會讓「連兩窗超標」在流量斷斷續續時永遠湊不齊。
    """
    now = time.monotonic() if now is None else now
    _prune_nli_turns(now)
    d0, t0 = _window_counts(now, NLI_WINDOW_S, 0.0)
    d1, t1 = _window_counts(now, 2 * NLI_WINDOW_S, NLI_WINDOW_S)
    r0 = (d0 / t0) if t0 else None
    r1 = (d1 / t1) if t1 else None
    two_windows_over = (
        r0 is not None and r1 is not None
        and r0 > NLI_DEGRADED_RATIO_RED and r1 > NLI_DEGRADED_RATIO_RED
    )
    single_window_total = (
        t0 >= NLI_SINGLE_WINDOW_MIN_TURNS and d0 == t0
    )
    return {
        "window_s": NLI_WINDOW_S,
        "degraded": d0,
        "turns": t0,
        "ratio": r0,
        "prev_degraded": d1,
        "prev_turns": t1,
        "prev_ratio": r1,
        "red": bool(two_windows_over or single_window_total),
    }


async def _check_nli(get_runtime: Optional[Callable[[], Any]]) -> tuple:
    """回 `(nli_ready, model_sha, tau, red)`。

    `nli_ready` 的三態：`True`／`False`／`"pending"`。
    🔴 `False`（服務說不 ready，或探不到）⇒ **紅**；`"pending"`（本行程還沒建
    runtime／沒有 client）⇒ ⛔ 不紅——與 `rules_sha` 同一個慣例。
    ⛔ 探測失敗**不得**回 `"pending"`：那會把「NLI 掛了」印成「還沒接線」。
    """
    runtime = None
    if get_runtime is not None:
        try:
            runtime = get_runtime()
        except Exception:  # noqa: BLE001 — 健檢不因取值失敗而崩
            runtime = None
    client = getattr(runtime, "nli_client", None) if runtime is not None else None
    tau = getattr(runtime, "nli_tau", None) if runtime is not None else None
    if client is None:
        return "pending", "pending", tau, False
    try:
        info = await client.health()
    except Exception:  # noqa: BLE001 — 探針：任何例外都代表這條路線不可達
        info = None
    if not info:
        return False, "pending", tau, True
    ready = bool(info.get("nli_ready"))
    return ready, (str(info.get("model_sha") or "") or "pending"), tau, not ready


def _premise_flags(stats: dict) -> list:
    """DSP-011 前提偵測四項：前三項任一非零，或第四項為真 ⇒ 列名。

    任務 2.8：第一項的致紅依據改為 `mcp_calls_flagged_by_api_key`（未登錄、
    或已登錄但非 `is_internal` 的 api_key_id）——`mcp_calls_by_api_key`
    的整體分佈仍輸出為觀測值，⛔ 不再以「非零即紅」判。
    """
    flags = []
    if stats.get("mcp_calls_flagged_by_api_key"):
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
    get_runtime: Optional[Callable[[], Any]] = None,
) -> dict:
    """`/api/v1/agent/health` 與 `system_health` 的 `Agent` 子項共用的核心邏輯。

    Args:
        registry: `ToolRegistry`（`mcp_facade.build_registry()` 建的那份）。
        get_kb_pool: `kb.get` 用的 psycopg2 風格 pool getter（可為 `None`）。
        stage: 部署里程碑（`mcp_facade.current_stage()`）。
        get_api_key_pool: `api_keys` 欄位偵測用的 **asyncpg** pool getter
            （可為 `None`；沒給就只讀行程級偵測快取，見模組 docstring 第 5 點）。
        get_runtime: `AgentRuntime` 的 getter，正產線傳
            `lambda: getattr(request.app.state, "agent_runtime", None)`；
            用來讀 `rules_sha`。`None`／getter 回 `None`／物件沒有該屬性
            ⇒ `rules_sha` 回 `"pending"`（⛔ 不致紅）。

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

    rules_sha = _rules_sha(get_runtime)

    nli_ready, nli_model_sha, nli_tau, nli_red = await _check_nli(get_runtime)
    nli_degraded = nli_degraded_stats()

    red = (
        spec_count == 0
        or not kb_reachable
        or bool(flags)
        or not scope_ready
        or nli_red
        or bool(nli_degraded["red"])
    )

    return {
        "status": "red" if red else "ok",
        "checks": {
            "tools": {
                "spec_count": spec_count,
                "kb_get_reachable": kb_reachable,
                "detail": kb_detail,
            },
            "outline_version": _outline_sha(get_runtime),
            "rules_sha": rules_sha,
            "premise": {
                "mcp_calls_by_api_key": stats.get("mcp_calls_by_api_key", {}),
                "mcp_calls_flagged_by_api_key": stats.get(
                    "mcp_calls_flagged_by_api_key", {}
                ),
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
            # DSP-033：`nli_ready` 是 nli-model `/health` 的**透傳**（⛔ 本檔不重算）；
            # `"pending"` ＝本行程還沒建 runtime／沒有 client，⛔ 不算紅。
            "nli_ready": nli_ready,
            "nli_model_sha": nli_model_sha,
            "nli_tau": nli_tau,
            "nli_degraded": nli_degraded,
        },
    }
