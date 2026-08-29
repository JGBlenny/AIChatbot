"""Retrieval semantic contract —— 「這筆 Knowledge 實際承接哪些使用者語義」（D1，2026-08-29）。

## 為什麼要有這個欄位（R8 已證的結構性缺口）

```text
系統宣告某 row 能承接的責任（Face／downstream capability）
**比** 系統拿去做 retrieval scoring 的文字（question_summary）**更寬**
⇒ 4656 的 capability 是「該筆帳單完整現況」，而 scoring surface 只有
  「查帳單 帳單編號查詢」＋keywords「帳單／查詢／編號」
  —— 已繳／未繳・已寄出／草稿 **一個字都沒有**
```

## ⚠️ 這個欄位**不是**什麼（⛔ 角色邊界）

```text
⛔ 不是 answer          （answer 回到「回答／grounding」的角色）
⛔ 不是 question_summary 的長版（summary 回到「人類簡短題意」）
⛔ 不是 keywords 集合    （keywords 降回 optional retrieval aid）
⛔ 不是 Face responsibility
⛔ 不是 applicability authority
⛔ 不是 routing policy
⚠️ 尤其**不得**成為新的 authority source。
```

## 與 applicability 正交

```text
`instance_applicability`   這個 intent 是否依賴 user-specific data？
`retrieval_representation` 這筆 row 能承接什麼 semantic intent？
⇒ 兩者**正交**，⛔ 不得互相推導
```

## D2：預設 **同一份** semantic surface

```text
DEFAULT: embedding surface ＝ reranker surface ＝ retrieval_representation
⚠️ 允許 stage-specific divergence，但**必須是明示契約**：
   embedding_representation / reranker_representation ＋ reason ＋ validation
⛔ 不得再因為某支服務「順手只拿 summary」就形成不同的 semantic universe。
```

## D3：**reviewed migration only**

```text
⛔ summary＋keywords 自動拼接        → 不得成為 contract truth
⛔ summary＋answer 自動拼接          → 不得
⛔ LLM 自動摘要後直接寫 DB           → 不得
✅ machine-generated proposal（可選）→ reviewer 對照 responsibility／answer／capability
                                    → reviewed declaration → 才寫入
provenance 必須保留 source 與 evidence。
```
"""
from typing import Any, Optional

#: 宣告鍵（置於 `generation_metadata`，與 instance_applicability 同慣例）
REPRESENTATION_KEY = "retrieval_representation"
PROVENANCE_KEY = "retrieval_representation_provenance"

#: production transport 欄位（retriever 的扁平投影；比照 knowledge_instance_applicability）
TRANSPORT_FIELD = "retrieval_representation"
#: provenance 的扁平投影欄位。
#: ⚠️ **必須**與 representation 一起投影：production row 不帶 generation_metadata，
#: 只投影文字而不投影 provenance 會讓 consumer 無法分辨 reviewed 與 proposal
#: —— 那正是 D3 要擋的事。
PROVENANCE_TRANSPORT_FIELD = "retrieval_representation_source"

#: 唯一被承認的 provenance（⛔ 自動拼接／自動摘要皆不在此列）
APPROVED_SOURCES = frozenset({"reviewed_product_declaration"})
#: 提案狀態——⛔ **不得**被 production 消費
PROPOSAL_SOURCE = "retrieval_representation_proposal"


def retrieval_representation(knowledge: Optional[dict]) -> Optional[str]:
    """讀 row 的 retrieval representation。**只讀宣告，⛔ 不推導、⛔ 不拼接。**

    ⚠️ 讀取順序比照 `instance_applicability`：production 扁平欄位優先、
    巢狀 `generation_metadata` 為相容備援。
    ⚠️ ⛔ 缺宣告時**不得** fallback 到 question_summary／answer／keywords
    —— 那正是本契約要根除的「偷偷補齊」。
    """
    row = knowledge or {}
    value = row.get(TRANSPORT_FIELD)
    if value is None:
        meta = row.get("generation_metadata")
        value = meta.get(REPRESENTATION_KEY) if isinstance(meta, dict) else None
    if isinstance(value, str) and value.strip():
        return value
    return None


def representation_source(knowledge: Optional[dict]) -> Optional[str]:
    """讀 provenance 的 source 字串。扁平投影優先、巢狀為相容備援。"""
    row = knowledge or {}
    src = row.get(PROVENANCE_TRANSPORT_FIELD)
    if src is None:
        meta = row.get("generation_metadata")
        prov = meta.get(PROVENANCE_KEY) if isinstance(meta, dict) else None
        src = prov.get("source") if isinstance(prov, dict) else None
    return src if isinstance(src, str) and src.strip() else None


def is_authoritative(knowledge: Optional[dict]) -> bool:
    """provenance 是否為被承認的來源。⛔ proposal 不算。"""
    return representation_source(knowledge) in APPROVED_SOURCES


# --------------------------------------------------------------------------
# D2 的**唯一**實作點：scoring surface
# --------------------------------------------------------------------------
#: 本 row 的 scoring 文字取自 reviewed declaration
SURFACE_SOURCE_DECLARED = "declared_representation"
#: 本 row 尚未 migrate，仍用 legacy question_summary
SURFACE_SOURCE_LEGACY_SUMMARY = "legacy_question_summary"
#: 連 question_summary 都沒有（⚠️ 應為 0；出現即為資料缺陷）
SURFACE_SOURCE_EMPTY = "empty"

#: 送進 reranker payload 的欄位名（api_server 優先採用它）
SURFACE_FIELD = "scoring_surface"
SURFACE_SOURCE_FIELD = "scoring_surface_source"


def scoring_surface(knowledge: Optional[dict]) -> tuple:
    """回傳 `(text, source)` —— **retrieval scoring 實際看到的那段文字**。

    ⚠️ 這是 D2「embedding surface ＝ reranker surface」的**唯一**實作點：
    embedding 產生端與 reranker payload 端都必須呼叫本函式，
    ⛔ 不得各自寫一份 `question_summary or answer` 的優先序
    —— 兩份實作就是兩個 semantic universe，那正是 R8 診斷出的病灶。

    ## ⚠️ `SURFACE_SOURCE_LEGACY_SUMMARY` **不是** contract fallback

    ```text
    `retrieval_representation()` ⛔ 不 fallback ——「宣告是什麼」不得被猜測。
    `scoring_surface()`   **必須**有 legacy 分支 —— 否則未 migrate 的 row
                          會在 scoring 階段拿到空字串，那是**擴大**故障而非修復。
    ⇒ 兩者不同層：前者是 truth 的讀取，後者是 migration 期間的**明示**降級，
      且降級**必被計數**（source 欄位隨 payload 一起傳，可統計覆蓋率）。
    ```
    ⚠️ 這個 legacy 分支是**過渡**，⛔ 不是終局；覆蓋率到 100% 前不得移除。
    """
    row = knowledge or {}
    declared = retrieval_representation(row)
    if declared is not None and is_authoritative(row):
        return declared, SURFACE_SOURCE_DECLARED
    summary = row.get("question_summary")
    if isinstance(summary, str) and summary.strip():
        return summary, SURFACE_SOURCE_LEGACY_SUMMARY
    return "", SURFACE_SOURCE_EMPTY
