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

### ⚠️ 兩個值的**證據門檻不對稱**（業主裁定②，2026-08-29）

```text
instance  可由**可重播的 machine capability evidence**（診斷引擎契約／識別碼表單／
          動作端點）建立，或由 reviewed declaration 建立
general   **必須**有正面的 reviewed declaration：
          「此 knowledge intent 的正確完成不依賴任何使用者特定 runtime state，
            即使相關 user-specific capability 存在也不需要讀取」
          ⛔ **不得**由 absence-of-instance-evidence 推導
unknown   正常的 migration state
```

⚠️ 實證依據：P1e-1 兩位隔離標註者對 839 筆達成 97.5% 一致，
但把**已證實需要實值**的知識 3509 合議判成 `general`——
因為它的答案文字寫成通用指引。⇒ **knowledge text alone is insufficient
evidence for authoritative `general` classification.**

⚠️ 也因此，⛔ 不得用「這一題若能讀到使用者自己的資料會不會答得更好」來判 general：
那是把判準從**必要性**偷換成**有沒有增益**。
「合約有哪些狀態？」讀到我的合約當然能答得更貼近，但它仍是純制度問題。

```text
user-specific data would improve answer  ≠  user-specific data is required
```

⚠️ UNKNOWN **比 false general 安全**，也比假的資料完整度誠實——
⛔ 不得為了壓低 UNKNOWN 而放寬 general 的證據門檻。

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

#: Face 層三態（⛔ 刻意**不用** bool——`None` 很容易在下游被 `is True` 悄悄降成 False，
#: 而「Face 契約缺失」不得被解讀成「這個 Face 不要求 instance」）
FACE_REQUIRED = "required"
FACE_NOT_REQUIRED = "not_required"
FACE_UNKNOWN = "unknown"

#: 交叉判定的四個結果
DECISION_ELIGIBLE = "eligible"
DECISION_INELIGIBLE = "ineligible"
DECISION_UNKNOWN = "unknown"
DECISION_NOT_APPLICABLE = "not_applicable"

APPLICABILITY_INSTANCE = "instance"
APPLICABILITY_GENERAL = "general"
APPLICABILITY_UNKNOWN = "unknown"

#: 合法宣告值（⛔ 不接受其他字串——寫錯字必須落到 UNKNOWN 而不是被猜對）
DECLARED_VALUES = frozenset({APPLICABILITY_INSTANCE, APPLICABILITY_GENERAL})


def knowledge_instance_applicability(knowledge: Optional[dict]) -> str:
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


def face_instance_requirement(config: Any) -> str:
    """讀 Face 的 responsibility 宣告，**三態**：`REQUIRED` / `NOT_REQUIRED` / `UNKNOWN`。

    ⚠️ 回字串不回 `Optional[bool]`：`None` 在下游一個 `is True` 就會被悄悄降成 False，
    而那正是本輪要根除的病灶——**Face 契約缺失不等於「這個 Face 不要求 instance」**。
    """
    scope = getattr(config, "grounding_scope", None)
    if not isinstance(scope, dict) and isinstance(config, dict):
        scope = config.get("grounding_scope")
    if not isinstance(scope, dict):
        return FACE_UNKNOWN
    value = scope.get(FACE_INSTANCE_REQUIREMENT_KEY)
    if value is True:
        return FACE_REQUIRED
    if value is False:
        return FACE_NOT_REQUIRED
    return FACE_UNKNOWN


def instance_applicability_decision(knowledge: Optional[dict], config: Any) -> str:
    """兩軸交叉的**純函式**判定。⛔ 這裡只表達契約，**不表達 rollout 政策**。

    ```text
    knowledge   face            結果
    instance    REQUIRED     →  ELIGIBLE
    general     REQUIRED     →  INELIGIBLE
    UNKNOWN     REQUIRED     →  UNKNOWN          ⛔ 不得取得正向 authorization
    任意        NOT_REQUIRED →  NOT_APPLICABLE   ⛔ 不得被 instance 規則誤傷
    任意        UNKNOWN      →  UNKNOWN          ⛔ Face 契約缺失 ≠ 不要求 instance
    ```

    ⚠️ **本函式刻意不決定 UNKNOWN 未來怎麼 route**。
    「UNKNOWN → suppress」或「UNKNOWN → allow」都是 rollout／authorization 政策，
    不是資料契約；把它偷渡進這裡會讓政策變更需要改契約，兩者從此糾纏。
    """
    requirement = face_instance_requirement(config)
    if requirement == FACE_NOT_REQUIRED:
        return DECISION_NOT_APPLICABLE
    if requirement == FACE_UNKNOWN:
        return DECISION_UNKNOWN
    applicability = knowledge_instance_applicability(knowledge)
    if applicability == APPLICABILITY_INSTANCE:
        return DECISION_ELIGIBLE
    if applicability == APPLICABILITY_GENERAL:
        return DECISION_INELIGIBLE
    return DECISION_UNKNOWN


def grants_positive_authorization(applicability: str) -> bool:
    """UNKNOWN **不得**取得任何正向授權含義——這條是本輪契約的核心。

    ⚠️ 只有明示 `instance` 才算「這一題需要個別資料」。
    `general` 與 `unknown` 都回 False，但**理由不同**：前者是明示否定，
    後者是未知；呼叫端若需要區分，讀 `knowledge_applicability()` 原值。
    """
    return applicability == APPLICABILITY_INSTANCE
