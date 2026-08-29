"""Instance applicability —— **與 candidate identity 正交**的第二個維度（U1／P1a）。

## 為什麼要有這個模組（2026-08-29 U1 第一刀的結論）

全量盤查證明了兩件事：

```text
(a) category 對「提名誰」其實很確定——可提名的 189 筆中 184 筆（97.4%）
    只產生唯一候選，歧義率 0.6%。⇒ 主要問題**不是** owner ambiguity。
(c) 真正缺的是另一個維度：「這一題需不需要讀使用者自己的資料」——
    而 `knowledge_base` 的 49 個欄位裡**沒有任何欄位表達它**。
```

⇒ 所以修法不是把 category 切得更細，而是**把缺失的語義落成資料**。

## 兩層契約，⚠️ 語義不同，⛔ 不得同名靠上下文猜

```text
Face 層   `grounding_scope.requires_instance_reference`
          問：這個 Face 的正常進場，是否以「需要個別資料」為適格條件？
          ＝ **responsibility contract**

Knowledge 層  `generation_metadata.instance_applicability`
          問：這筆知識代表的問題，需不需要讀使用者自己的系統資料才能正確完成？
          ＝ **applicability metadata**
```

## 三態，⚠️ **缺宣告 ≠ false**

```text
"instance"  明示需要個別資料
"general"   明示不需要
缺 / 無法辨識 → **UNKNOWN**
```

⛔ **UNKNOWN 不得取得任何正向授權含義。** 這正是本輪要修掉的病灶：
`is_instance_requiring_face()` 的 `scope.get(KEY) is True` 讓「不知道」被
默默讀成「不需要」，於是 gate 的條件 C 恆為 False——**授權機制是在一個
授權輸入結構性缺席的系統上被評估的**。

## ⛔ 本模組**不得**從其他欄位推導

`form_id`／`action_type`／`api_config` 編碼的是**執行**，不是**實值依賴**。
反證：知識 3509「訂閱扣款失敗導致功能異常」是 `direct_answer`、無 `form_id`，
卻必須查該帳號的訂閱狀態。⇒ 用執行能力當代理會**系統性漏掉**這一類。
（同 `instance_reference_gate` 對 Face 層的 no-fallback 原則。）
"""
from typing import Any, Optional

#: knowledge 層宣告鍵（放 `generation_metadata`；⛔ 不可挪用 `knowledge_base.scope`
#: ——那是 global/vendor 的**可見範圍**，語義完全不同）
KNOWLEDGE_APPLICABILITY_KEY = "instance_applicability"

#: Face 層宣告鍵（與 `instance_reference_gate.INSTANCE_REFERENCE_KEY` 同一個契約）
FACE_INSTANCE_REQUIREMENT_KEY = "requires_instance_reference"

APPLICABILITY_INSTANCE = "instance"
APPLICABILITY_GENERAL = "general"
APPLICABILITY_UNKNOWN = "unknown"

#: 合法宣告值（⛔ 不接受其他字串——寫錯字必須落到 UNKNOWN 而不是被猜對）
DECLARED_VALUES = frozenset({APPLICABILITY_INSTANCE, APPLICABILITY_GENERAL})


def knowledge_applicability(knowledge: Optional[dict]) -> str:
    """讀 knowledge row 的 applicability 宣告。**只讀宣告，⛔ 不推導。**

    回三態之一；缺宣告／值不合法／型別不對 → `UNKNOWN`。
    ⚠️ 值不合法時**刻意**不猜（例如 "Instance"、"true"、"是"）——
    容忍變體等於讓資料品質問題靜默通過，而這一層的整個重點就是「不知道要說不知道」。
    """
    meta = (knowledge or {}).get("generation_metadata")
    if not isinstance(meta, dict):
        return APPLICABILITY_UNKNOWN
    value = meta.get(KNOWLEDGE_APPLICABILITY_KEY)
    if isinstance(value, str) and value in DECLARED_VALUES:
        return value
    return APPLICABILITY_UNKNOWN


def face_instance_requirement(config: Any) -> Optional[bool]:
    """讀 Face 的 responsibility 宣告，**三態**：`True` / `False` / `None`（未宣告）。

    ⚠️ 與 `instance_reference_gate.is_instance_requiring_face()` 的差別：
    後者是**現役 routing 述詞**，缺欄位回 `False`（fail-closed by scope）。
    本函式回 `None`，讓呼叫端能分辨「明示不需要」與「根本沒宣告」——
    P1a 只建立這個分辨能力，⛔ **不改變現役 routing 行為**（那是 P1c）。
    """
    scope = getattr(config, "grounding_scope", None)
    if not isinstance(scope, dict):
        scope = (config or {}).get("grounding_scope") if isinstance(config, dict) else None
    if not isinstance(scope, dict):
        return None
    value = scope.get(FACE_INSTANCE_REQUIREMENT_KEY)
    return value if isinstance(value, bool) else None


def grants_positive_authorization(applicability: str) -> bool:
    """UNKNOWN **不得**取得任何正向授權含義——這條是本輪契約的核心。

    ⚠️ 只有明示 `instance` 才算「這一題需要個別資料」。
    `general` 與 `unknown` 都回 False，但**理由不同**：前者是明示否定，
    後者是未知；呼叫端若需要區分，讀 `knowledge_applicability()` 原值。
    """
    return applicability == APPLICABILITY_INSTANCE
