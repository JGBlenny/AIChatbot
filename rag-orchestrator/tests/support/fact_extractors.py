"""面向專屬的 **observation adapter**（任務 5.2 前置，依業主裁定 (b)）。

責任邊界（**寫死，不得逾越**）：

```text
formatter-specific extractor   →  observation（既有輸出中「觀測到哪些 fact」）
ChainClosureAssertion          →  judgment（delivery ＋ sufficiency）
```

⚠️ **B-1：extractor 不得擁有 sufficiency policy。**
它只回傳觀測到的 canonical fact keys，**不得**自己知道「哪幾個才算足夠」——
那是 5.2 凍結的 `required_grounding_facts` 與 `assert_chain_closure` 的職責。
**observer ≠ judge。**

⚠️ **B-2：不綁排版符號。** 以 formatter 的**語義欄位名**為觀測契約；
bullet、空白、全／半形冒號等 presentation detail 一律容忍——
`• 狀態：X` 與 `狀態：X` 必須觀測到同一個 fact，否則排版微調會讓閉環無故變紅。

⚠️ **兩個 extractor 輸出的是同一組 canonical key 空間**，故充分性判準仍然唯一：
`required_grounding_facts ⊆ observed_fact_keys`。
不同的只是**怎麼觀測**，不是**什麼叫充分**。
"""

import re

# ── bill_diagnosis：`【鍵】` 表示法 ────────────────────────────────────────
#: 實際輸出的括號鍵 → canonical fact key（來源：services/jgb/bills.py 的三個判定）
_DIAGNOSIS_BRACKET_MAP = {
    "發送判定": "send_determination",
    "取消判定": "cancel_determination",
    "手動到帳判定": "manual_complete_determination",
}

_BRACKET = re.compile(r"【([^】]+)】")

#: v2 amendment（`diagnosis-observation-audit-rule-frozen.md` 的 O-1／O-2 已查證）：
#: `_format_bill_status()`（services/jgb/bills.py:526-538）以
#: `• 金額：{_money(total)}` 呈現**應收金額**（`_bill_amount_due()` → `total`）。
#: ⚠️ 綁的是 **label ＋ 金額渲染**（`_money()` 的 `NT$ ` 形式），**不綁 bullet**（B-2）。
#: ⚠️ `（系統未記錄）` 是**缺值標記**，故意不匹配——沒有值就不是「fact 已送達」。
_DIAGNOSIS_FIELD_PATTERNS = {
    "amount_due": re.compile(r"金額\s*[：:]\s*NT\$"),
}


def diagnosis_bracket_fact_extractor(grounding: str) -> "set[str]":
    """`bill_diagnosis` 的觀測器：`【鍵】` ＋ 已查證的語義欄位 → canonical key。

    ⚠️ 未登錄的括號鍵**一律忽略**，不猜——未知鍵不是 fact，是尚未建立觀測契約的東西。
    ⚠️ 欄位型觀測僅限經 audit rule（O-1～O-6）證成者；**不得**因某個 case 需要就加。
    """
    text = grounding or ""
    keys = {
        _DIAGNOSIS_BRACKET_MAP[k]
        for k in _BRACKET.findall(text)
        if k in _DIAGNOSIS_BRACKET_MAP
    }
    keys |= {key for key, pat in _DIAGNOSIS_FIELD_PATTERNS.items() if pat.search(text)}
    return keys


# ── billing_anomaly：語義欄位表示法 ───────────────────────────────────────
#: canonical key → 觀測樣式（依 `_bill_head()` 與 anomaly builder 的**實際輸出**建立）。
#:
#: ⚠️ 樣式刻意包含各欄位的**識別性語境**，而非單一關鍵字：
#: 「金額」二字在任何句子裡都可能出現，故 amount 要求 `帳單金額 …（系統存值）` 的完整形狀。
_ANOMALY_FIELD_PATTERNS = {
    # `帳單「…」（編號 …）狀態：待繳費。`
    "bill_status": re.compile(r"狀態\s*[：:]\s*\S"),
    # `帳單金額 NT$ 18,000（系統存值）。`——存值語境是這個 formatter 的契約，不是排版
    "amount_stored": re.compile(r"帳單金額[^\n]*（系統存值）"),
    "due_date": re.compile(r"繳費期限\s*[：:]\s*\S"),
    "billing_period": re.compile(r"計費期間\s*[：:]\s*\S"),
}


def anomaly_labeled_field_extractor(grounding: str) -> "set[str]":
    """`billing_anomaly` 的觀測器：語義欄位 → canonical key。

    ⚠️ **不以 `•` 等排版符號為條件**（B-2）：`• 狀態：X` 與 `狀態：X` 觀測結果相同。
    ⚠️ 亦**不是** keyword spotting：句子裡出現「金額」「狀態」等詞而無欄位輸出結構者，
    不得被觀測成 fact（見本模組對應的 negative controls）。
    """
    text = grounding or ""
    return {key for key, pat in _ANOMALY_FIELD_PATTERNS.items() if pat.search(text)}


#: 供 5.2／5.3／5.4 引用：面向 → 觀測器。
#: ⚠️ 本表只決定**怎麼觀測**；**哪些 fact 才算足夠**由 5.2 的 `required_grounding_facts` 決定。
FACET_FACT_EXTRACTORS = {
    "條件診斷：帳單": diagnosis_bracket_fact_extractor,
    "帳單異常": anomaly_labeled_field_extractor,
}
