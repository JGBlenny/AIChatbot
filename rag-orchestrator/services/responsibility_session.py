"""T4-A：**responsibility-mode session carrier ＋ resume contract**（2026-08-30，業主凍結）。

## scope 鎖死（⚠️ 本刀只做這一件事）

```text
✅ responsibility-mode session carrier ＋ mode discriminator ＋ resume contract
⛔ 不接 direct capability execution      ⛔ 不抽 GROUNDING_FACTS presentation
⛔ 不改 legacy show_knowledge semantics  ⛔ 不改 format_jgb_response
⛔ 不改 bills／contracts dispatcher       ⛔ 不改 conversational_engine
```

本刀要證的**只有一件事**：

> **authority 可以跨一次 asynchronous／form round-trip 不變。**

⚠️ `resume_fulfillment` 只**恢復計畫**，⛔ 不執行 capability——否則 T4-A 與 T4-C 的因果會混在一起。

## 兩種 mode 並存，⛔ 不讓 runtime 猜

```text
legacy_row      knowledge_id ＋ on_complete_action=show_knowledge   （行為逐位不變）
responsibility  responsibility_id ／ fulfillment_binding_id ／ fulfillment_strategy ／
                input_contract_id ＋ on_complete_action=resume_fulfillment
```

⛔ **不得**「欄位有哪個就猜 mode」；mode 必須明示。

## ⚠️ knowledge_id 在 responsibility mode 下是 **conflict**，不是 ignored

底層資料表可保留 nullable `knowledge_id`（backward compatibility），但 responsibility mode 下
**必須為 NULL**：帶著一個看起來有 authority 的 row id ⇒ `SessionAuthorityConflict`。
⚠️ 「默默 ignore」⛔ 不可稽核——hard fail 才看得見（F-C5：⛔ 不得從 knowledge_id 回收 authority）。

## binding 存 **穩定 ID**，⛔ 不存 callable

```text
fulfillment_binding_id = "receipt.actual_amount.v1"
resume 時再由 sealed executable fulfillment registry 解析成實際 adapter
⇒ 函式搬檔案 ⛔ 不會使既有 session contract 失效
```
"""
from typing import Any, Dict, Mapping, Optional

MODE_LEGACY = "legacy_row"
MODE_RESPONSIBILITY = "responsibility"
VALID_MODES = (MODE_LEGACY, MODE_RESPONSIBILITY)

ACTION_SHOW_KNOWLEDGE = "show_knowledge"
ACTION_RESUME_FULFILLMENT = "resume_fulfillment"

#: responsibility mode 的 **immutable authority**——form payload ⛔ 無權覆寫任何一項
AUTHORITY_FIELDS = ("responsibility_id", "fulfillment_binding_id",
                    "fulfillment_strategy", "input_contract_id")

#: **F-C28 的唯一來源**：`validate_session()` 視為 authority contract 的欄位，
#: 若跨 turn 需要成立，就必須由 persisted session carrier **原樣**承載。
#: ⚠️ writer（form_manager）一律引用本常數，⛔ 不得另外手抄一份欄位清單——
#:    2026-09-01 曾因手抄漏掉 `fulfillment_strategy` 而在 turn 2 才炸。
#: ⚠️ restore 端**只讀 DB 原值**，⛔ 不推導、⛔ 不補值：
#:    自動補值會讓 validate_session 對還原路徑恆真（normalization 而非 validation）。
PERSISTED_AUTHORITY_FIELDS = ("session_authority_mode", *AUTHORITY_FIELDS,
                              "on_complete_action")


class SessionAuthorityError(RuntimeError):
    """session authority 契約違反——⚠️ 一律**大聲失敗**，⛔ 不得默默降級或猜測。"""


class SessionAuthorityConflict(SessionAuthorityError):
    """responsibility mode 卻帶著看起來有 authority 的 row id（F-C5）。"""


def build_responsibility_session(responsibility_id: str, fulfillment_binding_id: str,
                                 fulfillment_strategy: str, input_contract_id: str,
                                 **extra: Any) -> Dict[str, Any]:
    """建立 responsibility-mode session carrier。

    ⚠️ ⛔ 不接受 `knowledge_id`——responsibility mode 下它 ⛔ 不是 compatibility field，
    而是 authority conflict 的來源。
    """
    if "knowledge_id" in extra and extra["knowledge_id"] is not None:
        raise SessionAuthorityConflict(
            "responsibility mode ⛔ 不得攜帶 non-null knowledge_id"
            "——⛔ 它不得成為 authority recovery source")
    given = {"responsibility_id": responsibility_id,
             "fulfillment_binding_id": fulfillment_binding_id,
             "fulfillment_strategy": fulfillment_strategy,
             "input_contract_id": input_contract_id}
    missing = [f for f in AUTHORITY_FIELDS if not given.get(f)]
    if missing:
        raise SessionAuthorityError(f"responsibility mode 缺少 authority 欄位：{missing}")
    session = {"session_authority_mode": MODE_RESPONSIBILITY,
               "responsibility_id": responsibility_id,
               "fulfillment_binding_id": fulfillment_binding_id,
               "fulfillment_strategy": fulfillment_strategy,
               "input_contract_id": input_contract_id,
               "on_complete_action": ACTION_RESUME_FULFILLMENT,
               "knowledge_id": None}      # ⚠️ 明示 NULL，⛔ 非 compatibility 值
    session.update({k: v for k, v in extra.items() if k != "knowledge_id"})
    return session


def validate_session(session: Mapping[str, Any]) -> str:
    """驗證 mode exactness，回傳 mode。⛔ 不得由「欄位有哪個」推測 mode。"""
    mode = session.get("session_authority_mode")
    if mode is None:
        raise SessionAuthorityError("session 缺少 session_authority_mode"
                                    "——⛔ 不得由欄位存在與否猜測 mode")
    if mode not in VALID_MODES:
        raise SessionAuthorityError(f"未知的 session_authority_mode：{mode!r}")
    action = session.get("on_complete_action")
    if mode == MODE_RESPONSIBILITY:
        missing = [f for f in AUTHORITY_FIELDS if not session.get(f)]
        if missing:
            raise SessionAuthorityError(f"responsibility mode 缺少 authority 欄位：{missing}")
        if session.get("knowledge_id") is not None:
            raise SessionAuthorityConflict(
                f"responsibility mode 卻帶 knowledge_id={session['knowledge_id']!r}"
                f"——⛔ 不得從 knowledge_id 回收 authority（F-C5）")
        if action == ACTION_SHOW_KNOWLEDGE:
            raise SessionAuthorityError(
                "responsibility mode ⛔ 不得使用 show_knowledge 作 completion authority（F-C4）"
                "——它的 contract 本身就是 row authority")
        if action != ACTION_RESUME_FULFILLMENT:
            raise SessionAuthorityError(
                f"responsibility mode 的 on_complete_action 必須是 {ACTION_RESUME_FULFILLMENT}"
                f"，實際為 {action!r}")
    else:
        if any(session.get(f) for f in AUTHORITY_FIELDS):
            raise SessionAuthorityError(
                "legacy_row mode ⛔ 不得攜帶 responsibility authority 欄位"
                "——⛔ 不做讓 runtime 猜誰優先的混合 session")
        if action == ACTION_RESUME_FULFILLMENT:
            raise SessionAuthorityError(
                "legacy_row mode ⛔ 不得使用 responsibility-only 的 resume_fulfillment")
    return mode


def resume_fulfillment(session: Mapping[str, Any],
                       collected_inputs: Optional[Mapping[str, Any]] = None
                       ) -> Dict[str, Any]:
    """form 完成後**恢復計畫**——⚠️ 到此為止，⛔ 不執行 capability（那是 T4-C）。

    ⚠️ **使用者輸入只能滿足 input contract，⛔ 不能修改 execution authority。**
    payload 若嘗試覆寫任何 AUTHORITY_FIELDS ⇒ 立即失敗。
    """
    if validate_session(session) != MODE_RESPONSIBILITY:
        raise SessionAuthorityError("legacy_row session ⛔ 不得走 resume_fulfillment")
    inputs = dict(collected_inputs or {})
    attempted = sorted(f for f in AUTHORITY_FIELDS if f in inputs)
    if attempted:
        raise SessionAuthorityError(
            f"form payload 嘗試覆寫 execution authority：{attempted}"
            f"——⛔ 使用者輸入只能滿足 input contract")
    if "session_authority_mode" in inputs or "on_complete_action" in inputs:
        raise SessionAuthorityError("form payload ⛔ 不得改寫 session mode／completion action")
    return {"kind": "resumed_fulfillment_plan",
            # ⚠️ 逐欄由 session 復原（**exact**），⛔ 不由 payload、⛔ 不由 knowledge_id 推導
            **{f: session[f] for f in AUTHORITY_FIELDS},
            "resolved_inputs": inputs,
            "_not_executed": "⚠️ T4-A 只恢復計畫；capability 執行是 T4-C，"
                             "⛔ 不在此處呼叫，以免 A 與 C 的因果混淆",
            "_entity_resolution": "⚠️ resolved_inputs 只是**表單收到的值**；"
                                  "「是否解析到正確的那一筆 entity」是 T4-B，尚未證"}
