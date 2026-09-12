"""C1 DecisionLayer 決策中樞（spec retrieval-decision-layer 任務 1.3｜R7.4、R8.3）。

**這一步只做「搬移不重構」**：把散落在 chat.py／conversational_engine.py 的門檻讀值
（KB_SIMILARITY_THRESHOLD ×4、FORM_TRIGGER_THRESHOLD ×2）與六 case 答題仲裁的硬編碼
常數（0.15／0.55／0.6）收進唯一讀值點，仲裁判定邏輯**逐分支原樣搬入** `decide_arbitration()`
——六 case 結構不動（171 條整合測試護欄；gap-analysis G6 選項 A 定案）。

等價契約（審查修訂 1 第①層）：本模組的決定性子決策（門檻比對、分類路由 gate、六 case
仲裁）對任意輸入必須與搬移前的 inline 邏輯**嚴格同輸出**——unit 以逐字複製的參考實作
全域對拍（tests/unit/decision/）。調參、灰帶、識別碼訊號都是 P1 的事，不在此檔此版。

快照（R8.3）：`decide_arbitration()` 產出可歸因快照 dict，由呼叫端經
`usage_metering.set_decision()` 貢獻，最終由 `chat._finalize_decision_snapshot()`
在 dispatcher **唯一出口**組裝落地（任務 0.1）。仲裁只是其中一個貢獻者——
面向進場/續輪/退出、b2b 短路、快取命中各自貢獻；未貢獻的路徑落最小快照
（帶 `path` 與 `incomplete: true`），使覆蓋缺口成為可查事實而非靜默缺席。
（本檔頭原寫「從此每輪記下」，實測僅 54.8%、面向續輪 0%——D-19 已修正。）
"""
import hashlib
import json
import os
from dataclasses import dataclass, fields
from typing import Any, Dict, Optional

# 仲裁規則版本（快照歸因用）：判定結構或門檻語義改變時升版；
# 純搬移＝v1（與搬移前 inline 邏輯同構）。
DECISION_RULE_VERSION = "dl-v1"


@dataclass(frozen=True)
class DecisionConfig:
    """決策層唯一讀值點（R7.4）。

    值與預設**一字不改**沿自散落讀值點：
    - kb_threshold        ── KB_SIMILARITY_THRESHOLD（檢索過濾／Brain kb_search 同源）
    - form_trigger_threshold ── FORM_TRIGGER_THRESHOLD（面向進場＋表單觸發同一顆）
    - sop_min / knowledge_min / score_gap ── 六 case 仲裁硬編碼（原 chat.py 常數）
    """
    kb_threshold: float = 0.55
    form_trigger_threshold: float = 0.75
    sop_min: float = 0.55
    knowledge_min: float = 0.6
    score_gap: float = 0.15

    @classmethod
    def load(cls) -> "DecisionConfig":
        """讀 env 組出設定。每次呼叫即時讀（與原散落 os.getenv 同語義——
        原碼每請求讀一次 env，搬移後不得引入跨請求快取改變行為）。"""
        return cls(
            kb_threshold=float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.55")),
            form_trigger_threshold=float(os.getenv("FORM_TRIGGER_THRESHOLD", "0.75")),
            # 六 case 常數原為硬編碼、無 env——保留無 env 狀態（調參是 P1 任務 2.4，
            # 提前開 env 旋鈕會讓「等價驗證」失去對照意義）
        )

    def config_hash(self) -> str:
        """設定值雜湊（快照歸因用；任務 2.3 再納入 _generate_config_version）。"""
        body = json.dumps({f.name: getattr(self, f.name) for f in fields(self)},
                          sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:8]
