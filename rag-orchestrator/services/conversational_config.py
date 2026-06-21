"""
對話式回答設定層（option-routing R19 / 元件 15）。

「對話式回答模式」是一個通用回答模式（不綁售前）：每個面向以一筆 ConversationalConfig
opt-in 啟用 conversational（多輪自適應問答→收斂）；未設定的面向一律 direct（單次直答）。

一筆設定 = 一個面向，含：
  - answer_mode：direct | conversational
  - persona_role：規則載入用角色鍵（對應 target_user；規則由 conversational_rules 依此載入）
  - grounding_scope：收斂時檢索的範圍（target_user / mode / vendor_id），多面向不互撈
  - entry：入口（哪個選單表單的哪些選項 value 進此面向）
  - seed：可選起手主軸

**新增面向 / 角色 = 加一筆設定（與規則資料），不動程式。**
售前（prospect）為第一個 conversational 設定。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationalConfig:
    key: str
    answer_mode: str = "conversational"
    persona_role: Optional[str] = None
    grounding_scope: Dict[str, Any] = field(default_factory=dict)
    entry: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[str] = None


# 售前適配：第一個 conversational 設定（persona=售前顧問、target_user=prospect、
# grounding=prospect 售前知識）。entry＝presales_entry 選單的「fit / pain」兩選項。
PRESALES_CONFIG = ConversationalConfig(
    key="presales",
    answer_mode="conversational",
    persona_role="prospect",
    grounding_scope={"target_user": "prospect", "mode": "b2b", "vendor_id": 1},
    entry={"form_id": "presales_entry", "option_values": ["fit", "pain"]},
)

# 設定註冊表（之後加面向＝在此註冊一筆，並補對應規則資料）
_REGISTRY: Dict[str, ConversationalConfig] = {
    PRESALES_CONFIG.key: PRESALES_CONFIG,
}


def get_config(key: str) -> Optional[ConversationalConfig]:
    """依設定鍵取設定。"""
    return _REGISTRY.get(key)


def config_for_target_user(target_user: Optional[str]) -> Optional[ConversationalConfig]:
    """
    answer_mode dispatch（R19.1/19.2）：依角色取「該角色的 conversational 設定」。
    未設定（回 None）者一律走 direct（呼叫端不進對話迴圈）。
    """
    if not target_user:
        return None
    for cfg in _REGISTRY.values():
        if cfg.answer_mode == "conversational" and cfg.persona_role == target_user:
            return cfg
    return None


def config_for_entry(form_id: str, option_value: Any) -> Optional[ConversationalConfig]:
    """
    依選單入口取設定：某選單表單的某選項 value 是否為某 conversational 面向的入口。
    供 presales_entry「fit / pain」選項 seed 對話引擎。
    """
    if not form_id:
        return None
    for cfg in _REGISTRY.values():
        if cfg.answer_mode != "conversational":
            continue
        entry = cfg.entry or {}
        if entry.get("form_id") == form_id:
            values = entry.get("option_values") or []
            if option_value in values or str(option_value) in [str(v) for v in values]:
                return cfg
    return None
