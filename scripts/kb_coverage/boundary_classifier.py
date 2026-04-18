"""
SOP/KB 分工邊界分類器

決策樹邏輯：
  1. 涉及 2 步以上操作流程 → SOP
  2. 需觸發表單或 API → SOP
  3. 回答「是什麼 / 為什麼」→ KB
  4. 需查詢即時數據 → KB

同一主題可同時擁有 SOP（怎麼做）和 KB（是什麼/為什麼）。
"""

from __future__ import annotations

from typing import Dict, List, Literal

KnowledgeType = Literal["sop", "kb"]


# ---------------------------------------------------------------------------
# SOP 信號關鍵字 — 出現時傾向判定為 SOP
# ---------------------------------------------------------------------------
_SOP_SIGNALS: List[str] = [
    # 多步驟操作
    "流程", "步驟", "操作", "申請", "辦理", "執行",
    "提交", "填寫", "上傳", "送出", "簽署",
    # 觸發表單 / API
    "表單", "系統操作", "線上申請", "掃碼", "刷卡",
    # 明確的動作序列
    "怎麼做", "如何操作", "如何申請", "如何辦理", "如何繳費",
    "如何報修", "如何退租", "如何搬入", "如何搬出",
]

# ---------------------------------------------------------------------------
# KB 信號關鍵字 — 出現時傾向判定為 KB
# ---------------------------------------------------------------------------
_KB_SIGNALS: List[str] = [
    # 解答性 / 事實性
    "是什麼", "為什麼", "什麼是", "定義", "規定", "說明",
    "差異", "比較", "區別", "上限", "下限", "條件",
    "權益", "責任", "歸屬", "原則", "標準", "資格",
    # 查詢即時數據
    "查詢", "多少錢", "金額", "費用", "行情", "明細",
]


def classify_knowledge_type(topic: str) -> KnowledgeType:
    """
    根據主題描述判定該知識應歸入 SOP 還是 KB。

    決策樹：
      1. 計算 SOP 信號與 KB 信號的命中數
      2. 若 SOP 信號 > KB 信號 → SOP
      3. 若 KB 信號 >= SOP 信號 → KB（平手時偏向 KB，因為多數主題是解答性的）

    Parameters
    ----------
    topic : str
        知識主題的文字描述（例如「押金規定」「報修流程」）

    Returns
    -------
    "sop" | "kb"
    """
    if not topic or not topic.strip():
        return "kb"

    sop_score = sum(1 for kw in _SOP_SIGNALS if kw in topic)
    kb_score = sum(1 for kw in _KB_SIGNALS if kw in topic)

    if sop_score > kb_score:
        return "sop"
    return "kb"


# ---------------------------------------------------------------------------
# 對照範例常數 — 至少 5 組（同一主題下 SOP vs KB 的歸屬示範）
# ---------------------------------------------------------------------------
BOUNDARY_EXAMPLES: List[Dict[str, str]] = [
    {
        "topic": "押金（保證金）",
        "sop_example": "押金退還流程：租約到期 → 點交確認 → 扣除損壞費用 → 退還押金 → 簽收",
        "sop_reason": "多步驟操作流程，有觸發條件（租約到期），涉及簽收表單",
        "kb_example": "押金規定說明：法定上限為 2 個月租金，房東應於租約終止後返還，扣除條件包含修繕費用與欠繳租金",
        "kb_reason": "解答「押金是什麼、上限多少、何時返還」，屬事實性知識",
    },
    {
        "topic": "報修",
        "sop_example": "報修申請流程：租客提交報修單 → 管理師確認 → 派工 → 維修 → 驗收簽名",
        "sop_reason": "多步驟操作流程，需提交報修表單，涉及派工與驗收",
        "kb_example": "修繕責任歸屬說明：房東負責結構與主要設備維修，租客負責日常消耗品更換",
        "kb_reason": "解答「誰負責修繕」，屬責任歸屬的事實性知識",
    },
    {
        "topic": "管理費",
        "sop_example": "管理費繳費流程：查詢帳單 → 選擇繳費方式 → 完成繳費 → 取得收據",
        "sop_reason": "多步驟操作流程，涉及系統查詢與繳費表單",
        "kb_example": "管理費收費規則說明：包租業代收轉付模式與代管業服務費比例的差異解釋",
        "kb_reason": "解答「管理費怎麼算、兩種模式差異是什麼」，屬規則說明",
    },
    {
        "topic": "合約（租賃契約）",
        "sop_example": "簽約流程：審閱契約 → 確認條款 → 雙方簽署 → 上傳系統 → 存檔",
        "sop_reason": "多步驟操作流程，需簽署與上傳表單",
        "kb_example": "租賃契約必備條款說明：定期 vs 不定期契約差異、契約審閱期規定、應記載事項",
        "kb_reason": "解答「契約要包含什麼、有什麼類型」，屬法規與常識性知識",
    },
    {
        "topic": "繳費",
        "sop_example": "線上繳費操作流程：登入系統 → 查詢待繳帳單 → 選擇付款方式 → 確認付款 → 取得收據",
        "sop_reason": "多步驟操作流程，需系統操作與付款表單",
        "kb_example": "繳費方式與規定說明：可用銀行轉帳、超商代收、信用卡等方式，逾期需加收滯納金",
        "kb_reason": "解答「有哪些繳費方式、逾期怎麼辦」，屬規定性知識",
    },
    {
        "topic": "退租",
        "sop_example": "退租辦理流程：提前通知 → 預約點交 → 現場點交 → 押金結算 → 歸還鑰匙",
        "sop_reason": "多步驟操作流程，涉及通知、點交、結算等步驟",
        "kb_example": "提前解約條件說明：法定解約事由、違約金上限、通知期限規定",
        "kb_reason": "解答「什麼情況可以提前解約、違約金怎麼算」，屬法規知識",
    },
]


# ---------------------------------------------------------------------------
# Self-test — TDD assertions
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # --- RED → GREEN tests ---

    # Test 1: SOP 案例 — 包含多步驟操作流程關鍵字
    assert classify_knowledge_type("報修申請流程") == "sop", \
        "報修申請流程應為 SOP（多步驟操作）"

    assert classify_knowledge_type("退租辦理流程步驟") == "sop", \
        "退租辦理流程步驟應為 SOP"

    assert classify_knowledge_type("如何操作線上繳費") == "sop", \
        "如何操作線上繳費應為 SOP（操作 + 繳費流程）"

    assert classify_knowledge_type("如何申請報修表單") == "sop", \
        "如何申請報修表單應為 SOP（申請 + 表單）"

    # Test 2: KB 案例 — 解答性 / 事實性知識
    assert classify_knowledge_type("押金規定") == "kb", \
        "押金規定應為 KB（事實性知識）"

    assert classify_knowledge_type("管理費是什麼") == "kb", \
        "管理費是什麼應為 KB（解答性問題）"

    assert classify_knowledge_type("違約金上限說明") == "kb", \
        "違約金上限說明應為 KB（規定性知識）"

    assert classify_knowledge_type("包租業與代管業差異比較") == "kb", \
        "包租業與代管業差異比較應為 KB"

    assert classify_knowledge_type("修繕責任歸屬") == "kb", \
        "修繕責任歸屬應為 KB"

    # Test 3: 邊界案例 — 空字串應回傳 KB
    assert classify_knowledge_type("") == "kb", \
        "空字串應預設為 KB"

    assert classify_knowledge_type("   ") == "kb", \
        "僅空白應預設為 KB"

    # Test 4: BOUNDARY_EXAMPLES 至少 5 組
    assert len(BOUNDARY_EXAMPLES) >= 5, \
        f"BOUNDARY_EXAMPLES 應至少 5 組，目前 {len(BOUNDARY_EXAMPLES)} 組"

    # Test 5: 每組範例結構完整
    required_keys = {"topic", "sop_example", "sop_reason", "kb_example", "kb_reason"}
    for i, ex in enumerate(BOUNDARY_EXAMPLES):
        missing = required_keys - set(ex.keys())
        assert not missing, f"範例 {i} 缺少欄位: {missing}"

    # Test 6: 驗證 BOUNDARY_EXAMPLES 中的 SOP 範例確實被分類為 SOP
    sop_topics_from_examples = [
        "押金退還流程",
        "報修申請流程",
        "管理費繳費流程",
        "簽約流程",
        "線上繳費操作流程",
    ]
    for t in sop_topics_from_examples:
        assert classify_knowledge_type(t) == "sop", \
            f"'{t}' 應被分類為 SOP"

    # Test 7: 驗證 BOUNDARY_EXAMPLES 中的 KB 範例確實被分類為 KB
    kb_topics_from_examples = [
        "押金規定說明",
        "修繕責任歸屬說明",
        "管理費收費規則說明",
        "租賃契約必備條款說明",
        "繳費方式與規定說明",
    ]
    for t in kb_topics_from_examples:
        assert classify_knowledge_type(t) == "kb", \
            f"'{t}' 應被分類為 KB"

    print("=" * 60)
    print("All boundary_classifier self-tests passed!")
    print(f"  - classify_knowledge_type(): SOP/KB 分類正確")
    print(f"  - BOUNDARY_EXAMPLES: {len(BOUNDARY_EXAMPLES)} 組對照範例驗證通過")
    print("=" * 60)
