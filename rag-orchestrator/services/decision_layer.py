"""門檻讀值點（`DecisionConfig`）。

🔴 **2026-09-12 對碼改寫**：前一版 docstring 整段描述 `decide_arbitration()` 六 case
仲裁、`chat.py`／`conversational_engine.py` 的散落讀值點、`usage_metering.set_decision()`
快照鏈——**那些全部已隨舊 REST 對話鏈於 2026-09-11 刪除**（DSP-046）。本檔現在只剩
`DecisionConfig` 一個 frozen dataclass 與它的 `load()`／`config_hash()`。

## 誰在讀

唯一**活的**消費者是 **`services/agent/tools/kb.py`**，它讀 `DecisionConfig.load().kb_threshold`
當 `kb.search` 的相似度門檻。⚠️ `services/presales_gate.py::presales_threshold` 也讀它，
但那支函式**零生產呼叫端**（只有自己的測試）。其餘四個欄位（`form_trigger_threshold`／`sop_min`／
`knowledge_min`／`score_gap`）**目前沒有任何生產讀者**——它們是六 case 仲裁的常數，
仲裁本身已刪。⛔ 不在此刪欄位：`config_hash()` 進過快照歸因，砍欄位會讓舊快照的
雜湊對不上。

## ✅ `kb_threshold` 的 fallback 已與部署值對齊（2026-09-12）

**業主裁示後改**：`kb_threshold` 的程式 fallback 由 `0.55`
改為 **`0.65`**，與參數台帳（`docs/retrieval-parameters.md`）及
`docker-compose.prod.yml`／`dev.yml` 的顯式寫死值一致。

| 讀值點 | 改前 | 改後 |
|---|---|---|
| 本檔程式 fallback | 0.55 | **0.65** |
| 參數台帳 | 0.65 | 0.65 |
| 兩份 compose（顯式寫死，不走 env 插值） | 0.65 | 0.65 |

**為什麼非改不可**：這個分歧**已經造成過一次事故**——`tests/unit/_meta/test_env_parity_req.py`
檔頭記著「任務 3.1 實跑逼出：測試容器原本完全不帶 `.env` ⇒ 落回 0.55，而 production
跑 0.65；同一組測試在兩個門檻下候選集不同、紅的題目也不同，用錯門檻做的對照會得出
**完全相反的結論**」。線上有設所以沒事，但**新機器／CI／新起的容器**踩得到，
而且**沒有任何徵兆**。

⚠️ **這不是記憶裡那條「門檻對齊＝no-op、已 revert」**——那條講的是
`knowledge_min=0.6` 與 `KB_SIMILARITY_THRESHOLD=0.65` 之間沒有可回收區間，
是不同的命題。本節講的是 fallback 與部署值的分歧。

⛔ **不得改回 0.55**：失敗方向是「門檻悄悄變鬆、回出相關性較低的知識」，而且無聲。

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

    env 鍵名沿自散落讀值點，⛔ 不得改：
    - kb_threshold        ── KB_SIMILARITY_THRESHOLD（現由 `services/agent/tools/kb.py`
      的 `kb.search` 讀）。⚠️ **預設值已不是歷史 fallback**：2026-09-12 由 `0.55`
      對齊為 `0.65`（＝參數台帳與兩份 compose 的值），理由見檔頭。
    - form_trigger_threshold ── FORM_TRIGGER_THRESHOLD（面向進場＋表單觸發同一顆）
    - sop_min / knowledge_min / score_gap ── 六 case 仲裁硬編碼（原 chat.py 常數）
    """
    kb_threshold: float = 0.65        # 2026-09-12 由 0.55 對齊部署值，見檔頭
    form_trigger_threshold: float = 0.75
    sop_min: float = 0.55
    knowledge_min: float = 0.6
    score_gap: float = 0.15

    @classmethod
    def load(cls) -> "DecisionConfig":
        """讀 env 組出設定。每次呼叫即時讀（與原散落 os.getenv 同語義——
        原碼每請求讀一次 env，搬移後不得引入跨請求快取改變行為）。"""
        return cls(
            kb_threshold=float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.65")),
            form_trigger_threshold=float(os.getenv("FORM_TRIGGER_THRESHOLD", "0.75")),
            # 六 case 常數原為硬編碼、無 env——保留無 env 狀態（調參是 P1 任務 2.4，
            # 提前開 env 旋鈕會讓「等價驗證」失去對照意義）
        )

    def config_hash(self) -> str:
        """設定值雜湊（快照歸因用；任務 2.3 再納入 _generate_config_version）。"""
        body = json.dumps({f.name: getattr(self, f.name) for f in fields(self)},
                          sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:8]
