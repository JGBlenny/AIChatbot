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

# Stage 全序（元件 2 `specs_for`／`ToolRegistry.call` 比較用）；⛔ 唯一定義來源。
STAGE_ORDER: tuple[Stage, ...] = ("M0", "M1", "M2", "M3", "M4", "M5")


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
    """

    vendor_id: Optional[int]
    target_user: Any = "tenant"
    mode: str = "b2c"
    role_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: str = ""
    api_key_id: Optional[int] = None
    audience: Optional[Audience] = None

    def resolved_audience(self) -> Audience:
        """`self.audience` 有值即回傳；否則以 `audience_of` 即時推導。"""
        if self.audience is not None:
            return self.audience
        return audience_of(self.mode, self.target_user, self.role_id)
