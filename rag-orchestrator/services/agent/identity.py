"""呼叫者身分（spec agentic-mcp-orchestration・任務 1.1）。

本輪只放**知識池可見性**需要的三個欄位。⚠️ 任務 1.3 會擴充
（role_id／user_id／session_id 等 jgb2 雙證欄位），⛔ 本檔不預先塞。

信任邊界（DSP-011，業主 2026-09-04 裁）：這些欄位是**上游信任輸入**——
個資可見範圍由 jgb2 `external/v1` 的兩層權限裁，本系統 ⛔ 不自建授權層。
**例外**：知識池可見性（vendor_ids／business_types／target_user／保留分類）
住本系統 DB，仍由本系統的 `build_visibility_predicate` 謂詞守。
"""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Identity:
    """一次檢索／工具呼叫的呼叫者身分（可見性所需最小欄位）。

    Attributes:
        vendor_id: 業者 ID；決定 `vendor_ids` 過濾與（b2c）業態查詢。
        target_user: 角色。⚠️ **原值**——`is_b2b` 判定讀原值，
            正規化（未知／空 ⇒ tenant）只發生在**參數側**，見
            `VendorKnowledgeRetrieverV2._effective_target_user`。
        mode: `'b2c'`／`'b2b'`；與 target_user 兩條件 OR 決定 b2b 池。
    """

    vendor_id: Optional[int]
    target_user: Any = 'tenant'
    mode: str = 'b2c'
