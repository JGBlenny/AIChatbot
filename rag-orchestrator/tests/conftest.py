"""統一測試前置（spec testing-traceability・元件 1・R1.1, R1.3, R2）。

責任：
1. 統一匯入路徑——讓測試可直接 `from services.x import ...` / `from routers.x import ...`，
   以及既有以 `services/` 為根的 bare import（`from form_manager import ...`），
   取代各檔案散落的 `sys.path.insert`（既有檔仍可保留，屬冗餘但無害；R9.1 不改其行為）。
2. 提供共用 fixtures（mock_db_pool / mock_llm / anyio_backend），新測試可直接取用。

本檔僅新增測試前置，不觸碰任何產品執行邏輯（R9.1）。
"""
import os
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock

# rag-orchestrator 根目錄（本檔位於 rag-orchestrator/tests/）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVICES = os.path.join(_ROOT, "services")
for _p in (_ROOT, _SERVICES):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── skip 型別前綴（spec conversational-routing-execution 任務 1.3｜R1.3）──
# 兩類略過必須在輸出上可分辨：
#   [gate] ＝ 標記未啟用（RUN_INTEGRATION / RUN_E2E 未設）——旗標傳到了就不該出現
#   [env]  ＝ 環境不足（DB／外部服務不可達）——屬正常，另計
# 分類規則：reason 以 GATE_SKIP_PREFIX 開頭者為 gate，其餘一律視為 env。
# ⚠️ 刻意不逐一改動各測試檔內既有的 pytest.skip()（69 處）——那些是各測試自己的
#    環境判定，改動它們會違反「既有測試判定邏輯零改動」。env 前綴於摘要顯示時補上。
GATE_SKIP_PREFIX: str = "[gate]"
ENV_SKIP_PREFIX: str = "[env]"

# ⚠️ pytest 會在 skip reason 前加上 "Skipped: "（實測 longrepr[2] ==
#    'Skipped: [gate] 需真實相依…'）。不剝掉它，startswith(GATE_SKIP_PREFIX)
#    永遠為 False → 全部被誤classify 成 env → 下方空跑守門變成永遠通過的假綠燈。
#    這正是本 spec 要防的「量測工具靜默失效」，故此處必須剝除後再比對。
_PYTEST_SKIPPED_PREFIX: str = "Skipped: "

# 結構性失效退出碼（spec conversational-routing-execution 任務 1.4｜R1.4）。
# 用 10 而非 3：pytest 保留 0–5（3 ＝ internal error），借用會使
# 「pytest 自己炸掉」與「本設計的不變量失敗」在 CI 報告上無法區分。
EXIT_STRUCTURAL_FAILURE: int = 10

#: 受 gate 管轄的層級 → 對應的啟用旗標環境變數
_GATED_LAYERS: "dict[str, str]" = {
    "integration": "RUN_INTEGRATION",
    "e2e": "RUN_E2E",
}


def _selected_gated_layers(session) -> "set[str]":
    """來源 B：pytest **實際選中**了哪些受 gate 管轄的層級（任務 1.10）。

    讀的是 pytest **完成 selection 之後**的 item 集合，
    **不解析 `-m` 運算式**——否定式、括號、`and`/`or`、`-k` 過濾、路徑選取
    全部交給 pytest 自己解析，本函式只讀結果。這與「不自行重建既有語義」一致。

    註：被 gate skip 的 item 仍留在 `session.items`（skip 是 marker，不是 deselect），
    所以「整層被 gate-skip」這個情境在此看得見——那正是 I2 要抓的東西。

    ⚠️ 判定用 **marker** 而非 `item.keywords`——後者含 parametrize 參數值，
    會把「參數叫 integration 的 unit 測試」誤判為 integration 層（見 collection hook 註解）。
    """
    layers = set()
    for item in getattr(session, "items", None) or []:
        for layer in _GATED_LAYERS:
            if item.get_closest_marker(layer) is not None:
                layers.add(layer)
    return layers


def _skip_reason(rep_obj) -> str:
    """取出 skip 的原因字串，並剝除 pytest 自加的 'Skipped: ' 前綴。"""
    longrepr = getattr(rep_obj, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        reason = str(longrepr[2])
    elif longrepr is not None:
        reason = str(longrepr)
    else:
        reason = ""
    if reason.startswith(_PYTEST_SKIPPED_PREFIX):
        reason = reason[len(_PYTEST_SKIPPED_PREFIX):]
    return reason.lstrip()


def _classify_skips(stats) -> "tuple[list, list]":
    """把 skipped 報告分成 (gate, env) 兩類。分類唯一依據＝是否帶 GATE_SKIP_PREFIX。"""
    gate, env = [], []
    for rep_obj in stats.get("skipped", []):
        reason = _skip_reason(rep_obj)
        (gate if reason.startswith(GATE_SKIP_PREFIX) else env).append(reason)
    return gate, env


#: runner／CI 明示本次執行「請求了哪些受 gate 管轄的層級」（逗號分隔）。
#: 這是 requested-layer 的**唯一權威來源**。
_REQUESTED_LAYERS_ENV: str = "REQUESTED_TEST_LAYERS"


def _requested_gated_layers(config) -> "set[str]":
    """本次執行「明確請求」了哪些受 gate 管轄的層級。

    ⚠️ **只讀 `REQUESTED_TEST_LAYERS`，不解析 `-m` 運算式**
    （spec conversational-routing-execution 任務 1.8｜業主裁示 2026-08-23）。

    為什麼不 parse markexpr：`-m` 是布林運算式，正規表示式只看字面出現，
    實測 `-m "not integration"` → `re.search(r"\bintegration\b", ...)` 命中
    → 誤判成「請求了 integration」→ **無辜硬擋（假紅燈）**。
    繼續補排除規則（`not`、括號、`and`/`or`…）等於自己寫一個 pytest `-m` parser，
    與本 spec「不自行重建既有語義」的原則相違。
    `-m` 只負責 pytest 自己的 selection，**不拿來推導執行意圖**。

    設定點（見 scripts/run-tests.sh 與 .github/workflows/tests.yml）：
        LAYER=integration → REQUESTED_TEST_LAYERS=integration
        LAYER=e2e         → REQUESTED_TEST_LAYERS=e2e
        LAYER=all         → REQUESTED_TEST_LAYERS=integration,e2e
        LAYER=unit／自訂 marker／裸跑 → 不設 → 不受空跑守門管轄

    ⚠️ **語義邊界**：裸跑 `pytest` 不保證 requested-layer 語義；
    正式驗收入口是 `make` / `scripts/run-tests.sh` 與 CI job。
    """
    raw = os.getenv(_REQUESTED_LAYERS_ENV, "") or ""
    named = {part.strip().lower() for part in raw.split(",") if part.strip()}
    unknown = named - set(_GATED_LAYERS)
    if unknown:
        print(f"⚠️ {_REQUESTED_LAYERS_ENV} 含未知層級（已忽略）：{sorted(unknown)}")
    return named & set(_GATED_LAYERS)


# ---------------------------------------------------------------------------
# 測試分層（spec testing-traceability 元件 3・R2）
#
# 全測試一律以顯式 @pytest.mark.unit/integration/e2e 標記層級（檔頭 pytestmark 或逐函式）。
# 舊有「按檔名集中指派 layer」的清單已隨舊測試移除而退場——不再需要。
# 本檔只負責：依顯式 marker 套用 skip gate（integration/e2e 在無相依時標示略過）。
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """依顯式 marker 套用 skip gate（R4.5）。

    integration 預設略過，除非 RUN_INTEGRATION=1；e2e 預設略過，除非 RUN_E2E=1。
    如此 CI 預設只跑 unit、離線全綠；真實相依層「標示略過」而非假綠燈。
    層級一律由各測試以顯式 @pytest.mark.unit/integration/e2e 自標，conftest 不再代為指派。
    """
    run_integration = os.getenv("RUN_INTEGRATION") == "1"
    run_e2e = os.getenv("RUN_E2E") == "1"
    skip_integration = pytest.mark.skip(
        reason=f"{GATE_SKIP_PREFIX} 需真實相依（DB/外部服務），未設 RUN_INTEGRATION=1 → 標示略過（R4.5）"
    )
    skip_e2e = pytest.mark.skip(
        reason=f"{GATE_SKIP_PREFIX} 需整服務（API/SSE），未設 RUN_E2E=1 → 標示略過（R4.5）"
    )
    # ⚠️ 層級判定用 **marker**，不用 `item.keywords`（任務 1.10 實測逼出）：
    #    `keywords` 會把 parametrize 的**參數值**一起算進去，因此一個
    #    `@pytest.mark.parametrize("layer", ["integration", ...])` 的 **unit** 測試
    #    會被誤判成 integration 層而 gate-skip——正是一個會靜默製造假綠燈的類別。
    #    全套 1274 筆實測：keywords 與 marker 判定僅 2 筆分歧，且都是該類參數化測試，
    #    既有測試分層零變動。
    for item in items:
        if item.get_closest_marker("integration") is not None and not run_integration:
            item.add_marker(skip_integration)
        if item.get_closest_marker("e2e") is not None and not run_e2e:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """anyio/pytest-asyncio backend；統一用 asyncio。"""
    return "asyncio"


@pytest.fixture
def mock_db_pool() -> "AsyncMock":
    """共用 asyncpg pool mock。

    支援 `async with pool.acquire() as conn:` 與 conn.fetch/fetchrow/fetchval/execute，
    皆回傳 AsyncMock，測試可依需要覆寫回傳值。
    """
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="")

    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)
    # 方便測試取用底層 conn：pool._conn
    pool._conn = conn
    return pool


@pytest.fixture
def mock_llm() -> "MagicMock":
    """共用 LLM provider mock（決定性回傳）。

    預設 chat_completion 回固定內容；測試可覆寫 return_value 模擬不同決策。
    """
    llm = MagicMock()
    llm.chat_completion = MagicMock(return_value={"content": ""})
    return llm


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """skip 分類統計（spec conversational-routing-execution 任務 1.3｜R1.3）。

    把「因標記未啟用略過」與「因環境不足略過」分開列出，
    使「整層沒跑」與「環境不足」在輸出上不再無法分辨。
    """
    gate, env = _classify_skips(terminalreporter.stats)
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    terminalreporter.write_sep("─", "skip 分類（R1.3）")
    terminalreporter.write_line(
        f"passed={passed}  failed={failed}  "
        f"gate_skipped={len(gate)}  env_skipped={len(env)}"
    )
    if gate:
        terminalreporter.write_line(
            f"  {GATE_SKIP_PREFIX} 標記未啟用：{len(gate)} 筆"
            "（旗標已注入時此數應為 0）"
        )
    if env:
        terminalreporter.write_line(f"  {ENV_SKIP_PREFIX} 環境不足：{len(env)} 筆")


def pytest_sessionfinish(session, exitstatus) -> None:
    """空跑守門——**雙來源交叉校驗**（任務 1.4／1.8／1.10｜R1.4）。

    只靠 runner 宣告會有**共因失效**：`RUN_*` 旗標與 `REQUESTED_TEST_LAYERS`
    出自 `run-tests.sh` 的同一個 `case` 注入點，該注入若壞掉，兩者一起消失
    → 守門判「未請求」→ 不管轄 → 整層 skip 卻回 0 → 靜默假綠燈。
    **守門會連同它要防的東西一起消失。** 故改為兩個獨立來源互相校驗：

        來源 A（declared）：REQUESTED_TEST_LAYERS —— runner 宣告「我打算跑什麼」
        來源 B（selected）：pytest 最終 item 集合 —— pytest 實際決定「這次會跑什麼」

    兩條不變量：
        I1  declared layer → 對應 RUN_* 旗標必須存在，且該層應有 item 被選中
        I2  selected gated layer → 對應 RUN_* 旗標必須存在，**不論有無宣告**

    ⚠️ I2 使**裸跑 `pytest`** 也受管轄（2026-08-23 業主裁示，取代先前
    「裸跑不保證 requested-layer 語義」的取捨）：裸跑整套卻讓 integration／e2e
    靜默 skip，本來就不該回綠。只想跑 unit 就明確 `-m unit` 或走正式 runner。

    ⚠️ 退出碼在此決定，**shell 不得解析人類可讀 summary**。
    """
    declared = _requested_gated_layers(session.config)
    selected = _selected_gated_layers(session)

    problems = []
    for layer in sorted(declared | selected):          # I1 前半 ＋ I2
        env_key = _GATED_LAYERS[layer]
        if os.getenv(env_key) != "1":
            src = []
            if layer in declared:
                src.append(f"{_REQUESTED_LAYERS_ENV} 宣告")
            if layer in selected:
                src.append("pytest 實際選中")
            problems.append(
                f"[{'／'.join(src)}] {layer} 層要跑，但 {env_key} 未設為 1"
                "（旗標未傳遞到容器內）")

    for layer in sorted(declared - selected):          # I1 後半
        problems.append(
            f"[{_REQUESTED_LAYERS_ENV} 宣告] {layer} 層，"
            "但 pytest 實際未選中任何該層測試（宣告與 selection 不符）")

    reporter = session.config.pluginmanager.getplugin("terminalreporter")
    gate, _env = _classify_skips(reporter.stats if reporter is not None else {})
    if gate and (declared or selected):               # 交叉檢查
        problems.append(f"存在 {len(gate)} 筆 gate-skip（不變量要求為 0）")

    if problems:
        print("\n" + "=" * 72)
        print(f"❌ 結構性失效（R1.4）——退出碼 {EXIT_STRUCTURAL_FAILURE}")
        print(f"   declared={sorted(declared) or '—'}  selected={sorted(selected) or '—'}")
        for p in problems:
            print(f"   ・{p}")
        print("   這不是「測試沒過」，是「量測工具沒真的跑」。兩者不可混為一談。")
        print("=" * 72)
        session.exitstatus = EXIT_STRUCTURAL_FAILURE
