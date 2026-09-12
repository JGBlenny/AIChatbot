"""unit：`DecisionConfig` 的 env 鍵與預設值等價（任務 1.3｜R7.4）。

⚠️ 2026-09-12：本檔原本的主體是 `decide_arbitration()` 對「搬移前 chat.py
`_smart_retrieval_with_comparison` Step 3 的逐字複製參考實作」做全網格對拍。
`routers/chat.py` 已刪 ⇒ 那個「原版」只剩本檔自己抄的那一份，等於拿自己比自己；
且 `decide_arbitration`／`facet_entry_eligible`／`form_trigger_eligible` 三個函式
產品側已無任何呼叫端，一併刪除。

**保留的是 `DecisionConfig`**：它仍是活的——`services/agent/tools/kb.py` 與
`services/presales_gate.py` 讀它的門檻。本檔守的是「env 鍵名與預設值不被悄悄改掉」。
"""
import itertools
import os

import pytest

from services import decision_layer as dl

pytestmark = pytest.mark.unit


# 分數網格：0～1 步進 0.05（21 點）＋門檻邊界±ε 關鍵點——涵蓋 >、>=、+gap 的每個翻轉面
_EDGE = [0.549, 0.55, 0.551, 0.599, 0.6, 0.601, 0.699, 0.7, 0.701,
         0.749, 0.75, 0.751]
_SCORES = sorted({round(x * 0.05, 2) for x in range(21)} | set(_EDGE))
_FLAGS = list(itertools.product([False, True], repeat=4))  # cancelled/executed/response/action


# ════════════════════════════════════════════════════════════════════
# DecisionConfig：env 鍵與預設值等價（R7.4）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:7.4")
def test_config_defaults_match_legacy_values(monkeypatch):
    """未設 env 時的程式預設：KB **0.65**、FORM 0.75、六 case 0.55/0.6/0.15。

    🔴 **2026-09-12：`kb_threshold` 由 0.55 改為 0.65**（業主裁示）。原值是舊鏈散落
    讀值點的歷史 fallback，與參數台帳及兩份 compose 的顯式 `0.65` 不一致——
    該分歧已造成過一次事故（見 `tests/unit/_meta/test_env_parity_req.py` 檔頭：
    測試容器不帶 `.env` 落回 0.55、production 跑 0.65，同一組題在兩個門檻下
    紅的不同、結論相反）。⛔ 不得改回 0.55——失敗方向是門檻悄悄變鬆且無聲。
    ⚠️ 六 case 的三顆（sop_min／knowledge_min／score_gap）**不動**：它們無 env、
    也已無生產讀者，改它們沒有對齊對象。
    """
    monkeypatch.delenv("KB_SIMILARITY_THRESHOLD", raising=False)
    monkeypatch.delenv("FORM_TRIGGER_THRESHOLD", raising=False)
    c = dl.DecisionConfig.load()
    assert c.kb_threshold == 0.65
    assert c.form_trigger_threshold == 0.75
    assert (c.sop_min, c.knowledge_min, c.score_gap) == (0.55, 0.6, 0.15)


@pytest.mark.req("retrieval-decision-layer:7.4")
def test_config_env_override_same_keys(monkeypatch):
    """env 鍵名不變（KB_SIMILARITY_THRESHOLD／FORM_TRIGGER_THRESHOLD）；
    設了就生效——與原 os.getenv 每請求即時讀同語義。"""
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.62")
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.8")
    c = dl.DecisionConfig.load()
    assert c.kb_threshold == 0.62
    assert c.form_trigger_threshold == 0.8
    # 六 case 常數無 env 旋鈕（原碼即硬編碼；調參屬 P1 任務 2.4）
    assert (c.sop_min, c.knowledge_min, c.score_gap) == (0.55, 0.6, 0.15)


@pytest.mark.req("retrieval-decision-layer:8.3")
def test_config_hash_reflects_values(monkeypatch):
    monkeypatch.delenv("KB_SIMILARITY_THRESHOLD", raising=False)
    monkeypatch.delenv("FORM_TRIGGER_THRESHOLD", raising=False)
    h0 = dl.DecisionConfig.load().config_hash()
    assert h0 == dl.DecisionConfig.load().config_hash()      # 同值同雜湊
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.8")
    assert dl.DecisionConfig.load().config_hash() != h0      # 改值必變
