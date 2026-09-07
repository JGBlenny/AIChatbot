"""Agent 健康檢查核心邏輯（spec agentic-mcp-orchestration・任務 1.8）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 4（`/api/v1/agent/health`
段落）。⛔ 本檔不建路由——`routers/agent.py` 是唯一呼叫端；`services/pipeline_health_service.py`
的 `Agent` 子項 checker 也呼叫本函式（同一份邏輯，⛔ 不複製）。

## 這個端點在量什麼
1. **工具可達**：`registry` 有 spec（`union_specs` 非空）；`kb.get` 以固定假身分＋
   必然不存在的數字 `kb_id` 直呼（**不經 `registry.call()`**，避免混進速率限制／
   計量——這是健康探針，不是一次真實工具呼叫）。`ToolResult(error="NO_MATCH")`
   即代表 DB／可見性謂詞這條路線可達；探針本身丟例外（連線失敗等）才算紅。
2. **大綱 version／sha**：`app.state.agent_runtime.outline_sha`（取不到 ⇒ `"pending"`）；
   **`canon`**（3.2）另印 `resolve_canon_dir()` 的 resolved path 與本行程**已註冊**正本的
   `canon_sha256`——「這台機器讀的是哪一份正本」要看得見（⛔ 不重讀檔重算）；
   **`canon.index`**（3.3a）再印每個受眾 `FineIndex` 的三態（`absent`／`not_ready`／`ready`）
   與 `prepared_sha`／索引項數／維度，⛔ 同樣不致紅（`not_ready` 的正確行為是退回整份正本）。**`rules_sha`**（任務 2.6）
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
5b. **三支旗標（DSP-038-1／S-5／R8，皆為觀測值、⛔ 不致紅）**：
   `verifier_observe_only`＝`AGENT_VERIFIER_OBSERVE_ONLY`（見 `verifier_observe_only()`）；
   `write_tools_enabled`＝這個 registry 這一刻採用的 `AGENT_WRITE_TOOLS_ENABLED`
   （建構時釘住的值優先於 env）；`use_mock_jgb_api`＝`USE_MOCK_JGB_API`（**預設 true**，
   故「true」不代表有人刻意打開替身，見 `_use_mock_jgb_api`）。
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

import os
from typing import Any, Callable, Optional

from services import api_key_auth
from services.agent import mcp_facade
from services.agent.identity import Identity, Stage
from services.agent.tools.kb import kb_get
from services.agent.tools.registry import write_tools_enabled

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

#: 替身開關的 env 名（DSP-038／S-5）。⚠️ **只讀 env、⛔ 不 import
#: `services.jgb_system_api`**：那支在 import 期就會把 mock transport 那一整條
#: 分支拉進健檢行程（`JGBSystemAPI.__init__` 讀同一個 env 並裝配 transport），
#: 健檢只需要回答「這台機器現在設成打替身還是打真 API」。
#: 解析式**逐字對齊** `services/jgb_system_api.py` 的
#: `os.getenv("USE_MOCK_JGB_API", "true").lower() == "true"`（含「預設 true」
#: 這一點）——⛔ 兩邊語義不得分岔：健檢說 false、實際卻在打替身，比沒有這個
#: 旗更糟。
USE_MOCK_JGB_API_ENV = "USE_MOCK_JGB_API"


#: Verifier「只觀察不擋」對照實驗旗（R8）。⚠️ **⛔ 非正式組態**：開著代表引用類
#: 拒因只被記錄、不觸發改寫／轉人，⇒ 這台機器輸出的答案沒有經過完整的尺。
#: `app.py:_wrap_verifier_observe_only` 讀的就是本函式（**唯一讀值點**，
#: ⛔ 不在兩邊各寫一份 truthy 解析——健檢說 false、實際卻在觀察模式，比沒有這個旗更糟）。
AGENT_VERIFIER_OBSERVE_ONLY_ENV = "AGENT_VERIFIER_OBSERVE_ONLY"
_OBSERVE_TRUTHY = frozenset({"1", "true", "yes", "on"})


def verifier_observe_only() -> bool:
    """`AGENT_VERIFIER_OBSERVE_ONLY` ∈ {1,true,yes,on}（不分大小寫）⇒ True；
    未設或其他值 ⇒ **False**（fail-closed＝尺照常擋）。

    ⚠️ 與 `entry`／`write_tools_enabled` 無關：它是 Verifier 的行為旗，
    ⛔ 不參與任何可見性或授權判定。
    """
    return (os.getenv(AGENT_VERIFIER_OBSERVE_ONLY_ENV) or "").strip().lower() in (
        _OBSERVE_TRUTHY
    )


def _use_mock_jgb_api() -> bool:
    """`USE_MOCK_JGB_API`（預設 **true**）——觀測值，⛔ 不致紅。

    ⚠️ 這一旗預設為真，所以「它是 true」不代表有人刻意打開了替身；
    要判「這台機器是不是接到真 JGB」必須看它是 **false**。S-5 的處置是讓它
    **看得見**，⛔ 不是讓它變成閘門。
    """
    return os.getenv(USE_MOCK_JGB_API_ENV, "true").lower() == "true"


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


def _index_state() -> dict:
    """`{audience: {state, prepared_sha, entries, dim, content_keys}}`（3.3a／3.7｜元件 6 `FineIndex`）。

    只讀**本行程已註冊**的索引（`fine_index.get_index`），⛔ 不重建、⛔ 不觸發任何 embedding。
    未註冊 ⇒ `absent`；取值失敗 ⇒ 同樣降級成觀測值。
    ⚠️ **4.1 接線後：agent 開關任一開且非 ready ⇒ 紅**（`compute_agent_health` 的
    `red` 條件另外判——本函式只負責回傳觀測值，⛔ 不在此自己判紅）。3.3a／3.7
    時期「不致紅」僅限**尚未接線**那段期間：那時索引 `not_ready` 的正確行為是
    selector 回 `None`＝退回整份正本，服務並未壞掉；接線後同一個 `not_ready`
    代表產線正在用降級路徑服務，才需要在健檢上看得見。
    """
    try:
        from services.agent.canon.fine_index import index_registry_states
        return index_registry_states()
    except Exception as e:  # noqa: BLE001 — 健檢不因取值失敗而崩
        return {"detail": f"{type(e).__name__}: {e}"}


def _canon_state() -> dict:
    """`{"dir": …, "sha256": {audience: canon_sha256}, "index": {audience: {…}}}`（3.2＋3.3a）。

    `dir` 是 `resolve_canon_dir()` 的 **resolved path**——`AGENT_CANON_DIR` 只在
    `DB_ENV=test` 生效，健檢印出實際採用的那一個，讓「這台機器讀的是哪份正本」
    可觀測（security-reviewer P3-1）。`sha256` 只讀**本行程已註冊**的正本，
    ⛔ 不重讀檔案重算（重算量到的是磁碟現況，不是行程實際帶的那份）。
    取不到 ⇒ 空值，⛔ 不致紅（「尚未建置」不是「建置後壞了」，與 `rules_sha` 同語義）。
    """
    try:
        from services.agent.canon.canon_assembler import (
            canon_registry_shas, resolve_canon_dir,
        )
        state = {"dir": str(resolve_canon_dir()), "sha256": canon_registry_shas()}
    except Exception as e:  # noqa: BLE001 — 健檢不因取值失敗而崩
        state = {"dir": "pending", "sha256": {}, "detail": f"{type(e).__name__}: {e}"}
    # 索引另包一層 try（`_index_state`）——正本目錄取不到 ⛔ 不該連帶把索引狀態一起抹掉，反之亦然。
    state["index"] = _index_state()
    return state


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
    canon_state = _canon_state()

    # 任務 4.1／Plan §2.1-7：agent 任一開關開著、且**任一受檢受眾**的索引非 ready
    # （`absent`／`not_ready`）⇒ 紅——「索引不在」在接線後代表產線正在降級服務。
    # DSP-037／S1b：受檢集合＝`prospect`（基準受眾，永遠檢；⛔ 不因註冊表是空的就
    # 變綠——「不知道」不是 ready）∪ **本行程已註冊正本**的受眾（pm 正本上線後就會
    # 多它一個）。tenant 沒有正本、也不會被註冊 ⇒ 不在集合內，語義與 S1b 前相同。
    # ⚠️ 以**模組屬性**呼叫（`mcp_facade.agent_configured()`），⛔ `from … import`——
    # 讓 `monkeypatch.setattr(mcp_facade, "agent_configured", ...)` 生效。
    index_states = canon_state.get("index")
    index_states = index_states if isinstance(index_states, dict) else {}
    registered_shas = canon_state.get("sha256")
    checked_audiences = {"prospect"} | set(
        registered_shas if isinstance(registered_shas, dict) else {}
    )

    def _state_of(audience: str):
        observed = index_states.get(audience)
        return observed.get("state") if isinstance(observed, dict) else None

    not_ready = sorted(a for a in checked_audiences if _state_of(a) != "ready")
    agent_index_red = mcp_facade.agent_configured() and bool(not_ready)

    red = spec_count == 0 or not kb_reachable or bool(flags) or not scope_ready or agent_index_red

    return {
        "status": "red" if red else "ok",
        "checks": {
            "tools": {
                "spec_count": spec_count,
                "kb_get_reachable": kb_reachable,
                "detail": kb_detail,
            },
            "outline_version": _outline_sha(get_runtime),
            "canon": canon_state,
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
                # 任務 4.2（Plan §4.1-1／§4.3-9）：入口 mode 正規化次數——
                # **純觀測值**，⛔ 不進 `red_flags`、⛔ 不致紅：正規化是刻意的
                # 入口行為（prospect ⇒ b2b），不是 DSP-011 前提破裂。
                "identity_mode_normalized": stats.get("identity_mode_normalized", 0),
                "red_flags": flags,
            },
            # DSP-038-1／S-5：兩支旗標**看得見**。⛔ 兩者皆不致紅——
            # `write_tools_enabled` 關著是預設也是安全狀態；`use_mock_jgb_api`
            # 是「打替身或打真 API」的事實，不是故障。
            # `write_tools_enabled` 取自 **registry 這一刻實際採用的值**
            # （建構時釘住的值優先），⛔ 不在此另讀一次 env——那會在 registry
            # 被明示釘住時印出與實際不符的綠字。
            "write_tools_enabled": (
                registry.write_tools_enabled()
                if hasattr(registry, "write_tools_enabled")
                else write_tools_enabled()
            ),
            "use_mock_jgb_api": _use_mock_jgb_api(),
            # R8：Verifier 對照實驗旗——**觀測值、⛔ 不致紅**（它不是故障，
            # 是一個刻意的非正式組態）；但它必須看得見，否則「這台機器的答案
            # 有沒有經過尺」從外面完全問不出來。
            "verifier_observe_only": verifier_observe_only(),
            "mcp_sdk": "ok" if sdk_ok else "unavailable (DSP-014)",
            "api_keys_agent_scope_ready": scope_ready,
            "api_keys_agent_scope_detail": scope_detail,
        },
    }
