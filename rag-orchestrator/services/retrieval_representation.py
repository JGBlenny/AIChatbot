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


def is_authoritative(knowledge: Optional[dict]) -> bool:
    """provenance 是否為被承認的來源。⛔ proposal 不算。"""
    meta = (knowledge or {}).get("generation_metadata")
    if not isinstance(meta, dict):
        return False
    prov = meta.get(PROVENANCE_KEY)
    src = prov.get("source") if isinstance(prov, dict) else None
    return src in APPROVED_SOURCES
