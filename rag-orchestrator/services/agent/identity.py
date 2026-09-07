"""呼叫者身分（spec agentic-mcp-orchestration・任務 1.1／1.3）。

1.1 建立知識池可見性所需的三欄；1.3 擴充 jgb2 雙證與工具 registry 所需欄位
（role_id／user_id／session_id／api_key_id／audience）。⛔ **向後相容**：
新增欄位一律有預設值，既有三欄名稱／順序不改——
`vendor_knowledge_retriever_v2.build_visibility_predicate` 與既有測試
（`tests/unit/retrieval/test_visibility_predicate_req.py`）皆用位置／關鍵字
建構既有三欄，不得因擴充而破。

信任邊界（DSP-011，業主 2026-09-04 裁）：這些欄位是**上游信任輸入**——
個資可見範圍由 jgb2 `external/v1` 的兩層權限裁，本系統 ⛔ 不自建授權層。
**例外**：知識池可見性（vendor_ids／business_types／target_user／保留分類）
住本系統 DB，仍由本系統的 `build_visibility_predicate` 謂詞守。
"""
from dataclasses import dataclass
from typing import Any, Literal, Optional

Audience = Literal["prospect", "property_manager", "tenant"]
Stage = Literal["M0", "M1", "M2", "M3", "M4", "M5"]
IdentitySource = Literal["entry", "anonymous"]

#: 呼叫入口（DSP-038-1／子 spec `agent-write-tools` W1）。⛔ **不是認證訊號**，
#: 也不是 `IdentitySource`（那是「有沒有帶 role_id／user_id」的對話控制值）——
#: 這一欄回答的是「這個身分是從哪一道門進來的」，唯一用途是
#: `ToolRegistry.specs_for` 的 `mcp_only` 閘與 Runtime 的確認兌現段守門。
EntryChannel = Literal["mcp", "rest"]

#: `Identity.entry` 的預設值＝**fail-closed**：任何沒有明示自己是 `/mcp` 的
#: 建構點一律算 `rest`，於是 `mcp_only=True` 的寫入型工具對它永遠不可見。
#: ⛔ 不得改成 `"mcp"`——那會讓「忘了設」變成「預設拿到寫入權」。
DEFAULT_ENTRY_CHANNEL: EntryChannel = "rest"

# Stage 全序（元件 2 `specs_for`／`ToolRegistry.call` 比較用）；⛔ 唯一定義來源。
STAGE_ORDER: tuple[Stage, ...] = ("M0", "M1", "M2", "M3", "M4", "M5")

#: `mode` 的封閉值域（唯一定義來源；`mcp_facade._VALID_MODES` 是本常數的別名，
#: ⛔ 不另抄第二份）。
ENTRY_MODES: tuple[str, ...] = ("b2b", "b2c")

#: 缺漏／非法 `mode` 的預設值（同上，唯一定義來源）。
DEFAULT_ENTRY_MODE: str = "b2c"


def audience_of(
    mode: Optional[str],
    target_user: Optional[str],
    role_id: Optional[str] = None,
) -> Audience:
    """決定性推導，⛔ 不看 user 自述、⛔ 不看 role_id。

    判準（與既有兩處同判準，⛔ 不得另立第三套）：
    - prospect ⇔ `target_user == 'prospect'`
      （與 `routers/chat.py:CONVERSATIONAL_ENABLED_ROLES` 同判準）。
    - property_manager ⇔ `target_user in {'property_manager', 'system_admin'}
      or mode == 'b2b'`
      （與 `vendor_knowledge_retriever_v2.build_visibility_predicate` 的
      `is_b2b_mode` 同式，兩條件 OR）。
    - 其餘（含 `target_user is None`）⇒ tenant。

    純函式、決定性——同輸入必同輸出，無副作用、不查任何外部狀態。
    """
    if target_user == "prospect":
        return "prospect"
    if target_user in ("property_manager", "system_admin") or mode == "b2b":
        return "property_manager"
    return "tenant"


def normalize_entry_mode(target_user: Any, mode: Any) -> str:
    """入口 `mode` 正規化（任務 4.2／Plan §4.1-1，業主 2026-09-07 裁 (a)）。

    `target_user == 'prospect'` ⇒ **一律 `'b2b'`**——含缺漏、非法值、以及
    **明送 `'b2c'`**。理由：售前池是 b2b 池（`build_visibility_predicate` 的
    `business_types && ['system_provider']`），而 `audience_of` 對 prospect
    根本不看 mode ⇒ 放著會變成「受眾說 prospect、可見性謂詞說 b2c」的分裂身分，
    其失敗形狀是**靜默零內容**（候選選取 `none_visible`），⛔ 不是大聲的錯誤。
    ⛔ 不 400：入口是上游可信輸入（DSP-011），不在線上端點新增外顯失敗。

    其餘 `target_user`：合法 `mode` 原樣，缺漏／非法 ⇒ `DEFAULT_ENTRY_MODE`。

    ⚠️ 呼叫端必須**先**把 `target_user` 正規化（`_normalize_target_user`／
    `_effective_target_user`）再呼叫本函式——payload 的合法形狀含 list
    （`["prospect"]`），拿原值比 `== "prospect"` 會是 False。

    純函式、決定性；⛔ 不看 role_id／user_id／vendor_id。
    """
    if target_user == "prospect":
        return "b2b"
    return mode if mode in ENTRY_MODES else DEFAULT_ENTRY_MODE


def derive_identity_source(identity: "Identity") -> IdentitySource:
    """對話控制用的身分來源（任務 4.2／Plan §4.1-2）。

    規則＝`entry` ⇔ `role_id` 或 `user_id` 任一非 None；否則 `anonymous`
    （契約見 `docs/jgb2-chat-integration.md` §3／§4／§8）。

    ⛔ **不看 `vendor_id`**：MCP 的 `vendor_id` 是 API key 所屬業者，不是使用者
    身分；照它判會把每個帶 key 的匿名 prospect 判成 `entry`。

    ⚠️ **不是認證訊號**：呼叫端可以送任意 `role_id` 把值翻成 `entry`
    （DSP-011：`role_id` 的信任由上游承擔）。本值只餵 prompt 的對話控制
    （不再重問身分），⛔ 不進任何可見性謂詞、⛔ 不進 DB。
    """
    if identity.role_id is not None or identity.user_id is not None:
        return "entry"
    return "anonymous"


@dataclass(frozen=True)
class Identity:
    """一次檢索／工具呼叫的呼叫者身分。

    Attributes:
        vendor_id: 業者 ID；決定 `vendor_ids` 過濾與（b2c）業態查詢。
        target_user: 角色。⚠️ **原值**——`is_b2b` 判定讀原值，
            正規化（未知／空 ⇒ tenant）只發生在**參數側**，見
            `VendorKnowledgeRetrieverV2._effective_target_user`。
        mode: `'b2c'`／`'b2b'`；與 target_user 兩條件 OR 決定 b2b 池。
        role_id: jgb2 雙證欄位之一（1.3 起）；`None` 代表未提供（例如
            prospect 或未圈定的租客組合）。
        user_id: jgb2 雙證欄位之二（1.3 起）；`None` 代表未提供。
        session_id: 對話 session 識別碼（1.3 起）；⛔ **不參與**
            `ToolRegistry.call` 的速率限制 key（key 只用
            `(api_key_id, vendor_id)`，見 registry 模組 docstring）。
        api_key_id: 呼叫端 API key 的資料庫 id（1.3 起）；`None` 代表
            尚未解析出（例如測試假身分）。
        audience: 若上游已算好可直接帶入；預設 `None`，由
            `resolved_audience()` 依 `audience_of` 即時推導，⛔ 不在
            建構時強制計算（避免與未來欄位變動時的推導時機耦合）。
        entry: 呼叫入口（DSP-038-1）。預設 `"rest"`＝fail-closed——只有
            `/mcp` 門面自己的身分解析（`mcp_facade.parse_identity`／
            `union_specs` 的探針，屬子切片 W1b）才把它設成 `"mcp"`；
            `routers/agent_entry.build_identity`、`health._PROBE_IDENTITY`、
            `outline.py`、`tools/agent_eval.py` 一律**不帶** ⇒ 落 `"rest"`
            ⇒ `mcp_only=True` 的寫入型工具對它們永遠不可見、也呼叫不到。
            ⛔ 不是認證欄位：它由建構點決定，不由呼叫端 payload 決定。
    """

    vendor_id: Optional[int]
    target_user: Any = "tenant"
    mode: str = "b2c"
    role_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: str = ""
    api_key_id: Optional[int] = None
    audience: Optional[Audience] = None
    # ⚠️ 新欄位一律**加在有預設值的欄位之後**（見模組 docstring 的向後相容約束）。
    entry: EntryChannel = DEFAULT_ENTRY_CHANNEL

    def resolved_audience(self) -> Audience:
        """`self.audience` 有值即回傳；否則以 `audience_of` 即時推導。"""
        if self.audience is not None:
            return self.audience
        return audience_of(self.mode, self.target_user, self.role_id)
