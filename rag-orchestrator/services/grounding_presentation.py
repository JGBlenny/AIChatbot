"""T4-D2：**post-authority** GROUNDING_FACTS presentation adapter（2026-08-30，業主凍結）。

## F-C8 — PRESENTATION_AFTER_AUTHORITY

```text
GROUNDING_FACTS adapter **只能**做 presentation ／ packaging；
semantic owner、builder、responsibility 必須在**進 adapter 之前**已經確定。
```

## ⚠️ 這不是把 conversational_engine 那段搬過來

而是**從需求反推一個純輸入 contract**。判斷抽取邊界是否夠 post-authority 的檢查很簡單：

> 如果為了讓它工作又必須把 `user_question` ／ `face` ／ `config` ／ `endpoint` ／ `mapping`
> 塞回來，就表示邊界還不夠 post-authority ⇒ **應停**。

本模組的 signature 裡 ⛔ **沒有**：
`user_question`／`face`／`category`／`config`／`endpoint`／`mapping`／`_domain_key`。

## ⛔ 明確不得帶進本層

```text
⛔ BILL_FACE_BUILDERS.get(face)        ⛔ is_point_refund_intent(user_question)
⛔ 任何依 user_message 重新選 owner    ⛔ 任何 knowledge／member row answer fallback
```

## 收的是 **already-classified outcome**，⛔ 不是 raw rows

```text
T4-C    selection ／ capability execution     ← select_point_refund 在這裡跑
T4-D2   把**已經決定好的** execution outcome 呈現出去
```
⇒ 本層 ⛔ 不重跑 `select_point_refund()`。
"""
from typing import Any, Dict, List, Mapping, Optional

#: 已分類的 outcome（由 T4-C 決定，⛔ 不在本層重新判定）
OUTCOME_FACTS = "FACTS"            # 單一 entity 已選定，facts 已產出
OUTCOME_CANDIDATES = "CANDIDATES"  # 多筆待使用者選
OUTCOME_NOT_FOUND = "NOT_FOUND"
OUTCOME_TYPE_MISMATCH = "TYPE_MISMATCH"
VALID_OUTCOMES = (OUTCOME_FACTS, OUTCOME_CANDIDATES, OUTCOME_NOT_FOUND, OUTCOME_TYPE_MISMATCH)

KIND_CONVERGE = "converge"
KIND_ASK = "ask"

#: grounding_note 的既有截斷長度（沿用 conversational_engine 的慣例）
GROUNDING_NOTE_LIMIT = 600


class GroundingPresentationError(RuntimeError):
    """presentation 前置不成立——⚠️ 大聲失敗，⛔ 不得 fallback 到 canonical text／member answer。"""


class GroundingPresentationInput(dict):
    """⚠️ **typed** input。⛔ 不含 user_question／face／category／config／endpoint／mapping。"""


class GroundingPresentationResult(dict):
    pass


def _head(entity_id: Any, entity_label: Optional[str]) -> str:
    """`識別值｜名稱` 抬頭（沿用既有慣例）。

    ⚠️ 目的與既有實作相同：使用者常用 id 稱呼，但 facts 只帶名稱；
    grounding 不含 id 時，下游會誤判成「這不是他問的那筆」而推託。
    ⚠️ `entity_id` 為 None 時（例如內部個資需遮罩）只留名稱——由**呼叫端**決定，
    ⛔ 本層不自行判斷哪些欄位是個資。
    """
    return "｜".join(str(p) for p in (entity_id, entity_label) if p not in (None, ""))


def present(payload: Mapping[str, Any]) -> GroundingPresentationResult:
    """把**已分類的** outcome 包成後段對話生成的合法輸入。

    ⚠️ 本層 ⛔ 不決定「該由誰回答」，只決定「已決定的東西怎麼呈現」。
    """
    outcome = payload.get("outcome")
    if outcome not in VALID_OUTCOMES:
        raise GroundingPresentationError(
            f"未知的 outcome：{outcome!r}——⛔ 本層不重新分類（那是 T4-C 的責任）")
    rid = payload.get("responsibility_id")
    if not rid:
        raise GroundingPresentationError("缺 responsibility_id——⛔ authority 必須在進本層前已確定")

    if outcome == OUTCOME_FACTS:
        facts = payload.get("grounding_facts")
        # ⚠️ D2-G4：⛔ 不得 fallback canonical text／member answer
        if not isinstance(facts, str) or not facts.strip():
            raise GroundingPresentationError(
                "grounding_facts 缺漏／為空——⛔ 不得改用 canonical_responsibility "
                "或 member row 的 answer 補值")
        head = _head(payload.get("entity_id"), payload.get("entity_label"))
        grounding = "\n".join(p for p in (head, facts) if p)
        return GroundingPresentationResult(
            kind=KIND_CONVERGE, responsibility_id=rid, grounding=grounding,
            state_updates={"grounding_note": grounding[:GROUNDING_NOTE_LIMIT]},
            _not_generated="⚠️ 本層只產出**餵給後段生成**的 grounding；"
                           "⛔ 不負責最終 LLM 回答的正確性（另一層）")

    if outcome == OUTCOME_CANDIDATES:
        cands: List[dict] = list(payload.get("candidates") or [])
        if not cands:
            raise GroundingPresentationError("CANDIDATES outcome 卻沒有候選")
        # ⚠️ D2-G5：⛔ 絕不自行 candidates[0]——多筆一律列給使用者選
        listing = "\n".join(f"{i + 1}. {c.get('label') or c.get('title') or c.get('id')}"
                            for i, c in enumerate(cands))
        return GroundingPresentationResult(
            kind=KIND_ASK, responsibility_id=rid,
            answer=f"找到多筆資料，請問您指的是哪一筆？\n{listing}",
            candidates=cands,
            quick_replies=[{"text": (c.get("label") or c.get("title") or str(c.get("id"))),
                            "value": str(c.get("id"))} for c in cands],
            state_updates={})

    # NOT_FOUND ／ TYPE_MISMATCH：由 T4-C 提供的 reviewed 說明文字呈現
    note = payload.get("outcome_note")
    if not isinstance(note, str) or not note.strip():
        raise GroundingPresentationError(
            f"{outcome} 需要 outcome_note（由 T4-C 的 capability 提供）"
            f"——⛔ 本層不自行編話術")
    return GroundingPresentationResult(
        kind=KIND_ASK, responsibility_id=rid, answer=note, candidates=None,
        quick_replies=None, state_updates={})
