"""寫入動作的**表單**——5 支寫入動作共用一張表（plan-write-flow-program-owned-20261017 W1 §2.1(1)／DSP-085）。

## 為什麼要有這張表
寫入流程原本「要不要進寫入、還缺什麼、何時出卡」全綁在模型有沒有主動呼叫
`confirm.request`；缺欄計算也分三套（封閉三動作一套、修繕一套、延期繳費沒有）。
本檔把「必填／標籤／追問對象／型別」收成**同一張表**，三個用途都由它導出：

  ① `missing_labels(action, payload)`——5 支動作缺欄計算的**唯一**函式
     （`confirm.request` 在 `render()` 之前呼叫；封閉三動作經
     `confirm_card.missing_required_labels` 轉呼，輸出逐字不變）；
  ② `ask_target_for_missing(labels)`——缺欄追問的 `ask_target`（與改動前 runtime 寫死的
     「缺欄含『物件』⇒ estate；只缺『問題描述』⇒ description；其餘 None」逐位相同，但由表驅動）；
  ③ 會話草稿 `write_draft` 的鍵域、值的型別、`to_payload` 正規化、注入行文字、
     **意圖判斷呼叫**（W1b §8.1-1：runtime 另發的一次模型呼叫）的 schema、系統句與回應解析。

## 硬約束
- 封閉三動作**由 `confirm_card.CLOSED_ACTION_FIELDS`／`CLOSED_ACTION_ANY_OF`／
  `_REF_ALTERNATIVES` 導出**，⛔ 另抄一份欄位表。
- `repair_create`／`bill_due_extend` 在本檔宣告，**必填判準照現行程式行為**（⛔ 改行為）：
  修繕「問題描述」去空白後為空＝缺（A9；與 `REPAIR_CREATE_SPEC`「允許是空字串」不一致，
  爭議 DSP-082 待業主裁）；延期繳費必填＝`days` 且（`bill_id` 或 `estate_name`），
  期別**不是**必填（`_resolve_bill_by_period` 只檢查 `estate_name`；爭議 DSP-084 待裁）。
- `ask_target` 只能取既有 `ASK_TARGETS` 或 `None`（⛔ 新增值域：主輸出 `AgentOutput` 給模型
  的 schema 在 on／off 下都必須與改動前逐位相同，W1b 驗收 #6）。
- 表內 ⛔ 不得出現 `IDENTITY_OWNERSHIP_KEYS` 任一鍵（歸屬一律只取自 identity）。
- 本檔是**純資料＋純函式**：⛔ 不讀時鐘（`today` 由呼叫端傳）、⛔ 不查 DB、⛔ 不呼叫 LLM。
  唯一讀 env 的是 `write_draft_enabled_from_env()`（啟動期讀一次）。
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any, Final, Mapping, Optional, Tuple

from services.agent.confirm_card import (
    CLOSED_ACTION_ANY_OF,
    CLOSED_ACTION_EXTRA_KEYS,
    CLOSED_ACTION_FIELDS,
    CONFIRM_ACTIONS,
    CONTRACT_CREATE_ACTION,
    ESTATE_CREATE_ACTION,
    IDENTITY_OWNERSHIP_KEYS,
    MANUAL_BILL_CREATE_ACTION,
    _EMERGENCY_ZH,
    _REF_ALTERNATIVES,
    _given,
)
from services.agent.llm_output import final_segment, iter_json_objects
from services.agent.output_schema import ASK_TARGETS

# ---------------------------------------------------------------------------
# 欄位屬性的封閉值域
# ---------------------------------------------------------------------------
#: 欄位型別（plan §2.1(1)）。⛔ 新型別要先進這個集合，否則表寫錯在 import 期就炸。
FIELD_KINDS: Final[frozenset] = frozenset({
    "text", "int", "number", "date", "email", "phone", "enum", "sys_id", "category",
})
#: 欄位來源：`user_words`＝使用者口述（意圖判斷呼叫可抽取、須過值閘）；
#: `system`＝系統解析或程式導出（⛔ 進意圖判斷呼叫的鍵值域、⛔ 進草稿）。
SOURCE_USER_WORDS: Final[str] = "user_words"
SOURCE_SYSTEM: Final[str] = "system"
_SOURCES: Final[frozenset] = frozenset({SOURCE_USER_WORDS, SOURCE_SYSTEM})

#: 「有給」的兩種判準（照各動作現行程式，⛔ 統一成一種——統一就是改行為）：
#: `given`＝`confirm_card._given`（非 None、非空白字串；整數算有給）；
#: `nonblank_str`＝修繕 A9 現行判準（非字串或去空白後為空＝缺）。
PRESENCE_GIVEN: Final[str] = "given"
PRESENCE_NONBLANK_STR: Final[str] = "nonblank_str"

#: 追問對象（表內宣告）：物件名稱欄位＝`estate`、修繕問題描述＝`description`，
#: 其他欄位一律 `None`（plan §2.1(1)：重現現行「物件 ⇒ estate／只缺問題描述 ⇒ description」）。
_ASK_TARGET_BY_KEY: Final[dict] = {"estate_name": "estate", "description": "description"}

#: 沒宣告 `max_len` 的欄位，草稿讀回時的長度上限（數字／日期／編號類都遠短於此）。
_DEFAULT_VALUE_MAX: Final[int] = 64


@dataclass(frozen=True)
class FormField:
    """表單的一欄。

    `payload_type`：只對 `enum` 有意義——送進 `confirm.request` payload 時轉成哪一型
    （`emergency_status` ⇒ `int`，對 `confirm_card._EMERGENCY_ZH` 的整數鍵；封閉三動作的
    enum 仍為 `str`，照 `confirm_card._closed_value`）。
    """

    key: str
    label: str
    kind: str
    source: str = SOURCE_USER_WORDS
    ask_target: Optional[str] = None
    max_len: int = 0
    choices: Tuple[str, ...] = ()
    payload_type: str = "str"


@dataclass(frozen=True)
class Requirement:
    """一條必填規則（替代組）。

    `required_any_of`：任一組**全給**即滿足（單一必填＝只有一組、一個鍵）。
    `ask_group`：不滿足時要追問的鍵（只列其中**沒給**的那幾個的標籤）。
    `group_label`：有值 ⇒ 不滿足時只印這一個固定標籤（封閉表「至少給一個」組，
    例「承租人 Email 或電話」），`ask_group` 不用。
    """

    required_any_of: Tuple[Tuple[str, ...], ...]
    ask_group: Tuple[str, ...] = ()
    group_label: Optional[str] = None


@dataclass(frozen=True)
class WriteForm:
    action: str
    #: 注入行與 schema 說明用的動作中文名（固定詞彙）。
    title_zh: str
    fields: Tuple[FormField, ...]
    requirements: Tuple[Requirement, ...]
    presence: str = PRESENCE_GIVEN

    def field(self, key: Any) -> Optional[FormField]:
        for f in self.fields:
            if f.key == key:
                return f
        return None

    @property
    def keys(self) -> Tuple[str, ...]:
        return tuple(f.key for f in self.fields)

    @property
    def user_word_keys(self) -> Tuple[str, ...]:
        """意圖判斷呼叫可填的鍵（`system` 來源一律排除）。"""
        return tuple(f.key for f in self.fields if f.source == SOURCE_USER_WORDS)


# ---------------------------------------------------------------------------
# 封閉三動作：由 `confirm_card` 的欄位表導出（⛔ 另抄）
# ---------------------------------------------------------------------------
#: 封閉表欄位型別 → 表單型別（兩邊值域同名；`category` 只有修繕用）。
_CLOSED_KIND: Final[dict] = {
    "text": "text", "enum": "enum", "int": "int", "number": "number", "date": "date",
    "email": "email", "phone": "phone", "sys_id": "sys_id",
}

#: `_REF_ALTERNATIVES` 裡的替代鍵若不在該動作的封閉表內（例：`manual_bill_create` 的
#: `estate_name` 在 `CLOSED_ACTION_EXTRA_KEYS`），它的標籤與長度取自 `contract_create`
#: 表內同名欄位（同一個「物件」語義，⛔ 另寫字面量）。
_ESTATE_NAME_FIELD = next(f for f in CLOSED_ACTION_FIELDS[CONTRACT_CREATE_ACTION]
                          if f.key == "estate_name")

_CLOSED_TITLES: Final[dict] = {
    ESTATE_CREATE_ACTION: "建立物件",
    CONTRACT_CREATE_ACTION: "建立合約",
    MANUAL_BILL_CREATE_ACTION: "建立手動帳單",
}


def _closed_form(action: str) -> WriteForm:
    alternatives = _REF_ALTERNATIVES.get(action, {})
    fields: list = []
    for f in CLOSED_ACTION_FIELDS[action]:
        fields.append(FormField(
            key=f.key, label=f.label, kind=_CLOSED_KIND[f.kind],
            source=SOURCE_SYSTEM if f.kind == "sys_id" else SOURCE_USER_WORDS,
            ask_target=_ASK_TARGET_BY_KEY.get(f.key),
            max_len=f.max_len,
            choices=tuple(f.choices or ()),
        ))
    present = {f.key for f in fields}
    for alt_keys in alternatives.values():
        for alt in alt_keys:
            if alt in present or alt not in CLOSED_ACTION_EXTRA_KEYS[action]:
                continue
            if alt != _ESTATE_NAME_FIELD.key:   # 表寫錯（大聲失敗）
                raise AssertionError(f"{action}: 替代鍵 {alt!r} 沒有可導出的標籤")
            fields.append(FormField(
                key=alt, label=_ESTATE_NAME_FIELD.label, kind="text",
                ask_target=_ASK_TARGET_BY_KEY.get(alt), max_len=_ESTATE_NAME_FIELD.max_len,
            ))
            present.add(alt)
    requirements: list = []
    # ⚠️ 順序＝`confirm_card.missing_required_labels` 的原順序：先欄位表（必填、非 sys_id），
    #    再「至少給一個」組 ⇒ 缺欄標籤清單逐字不變。
    for f in CLOSED_ACTION_FIELDS[action]:
        if not f.required or f.kind == "sys_id":
            continue
        groups = ((f.key,),) + tuple((alt,) for alt in alternatives.get(f.key, ()))
        requirements.append(Requirement(required_any_of=groups, ask_group=(f.key,)))
    for keys, label in CLOSED_ACTION_ANY_OF[action]:
        requirements.append(Requirement(
            required_any_of=tuple((k,) for k in keys), group_label=label,
        ))
    return WriteForm(action=action, title_zh=_CLOSED_TITLES[action], fields=tuple(fields),
                     requirements=tuple(requirements), presence=PRESENCE_GIVEN)


# ---------------------------------------------------------------------------
# 修繕與延期繳費：本檔宣告（必填判準照現行程式行為）
# ---------------------------------------------------------------------------
#: 修繕。標籤＝卡上那一行的字（`confirm_card._render_repair_create`）。
#: `emergency_status` 值域照 `REPAIR_CREATE_SPEC`（1＝非緊急、2＝緊急；`_EMERGENCY_ZH` 真值）。
REPAIR_CREATE_FORM: Final[WriteForm] = WriteForm(
    action="repair_create",
    title_zh="建立修繕單",
    fields=(
        FormField("estate_name", "物件", "text", ask_target=_ASK_TARGET_BY_KEY["estate_name"],
                  max_len=_ESTATE_NAME_FIELD.max_len),
        FormField("description", "問題描述", "text",
                  ask_target=_ASK_TARGET_BY_KEY["description"], max_len=500),
        FormField("category_name", "修繕分類", "category", max_len=60),
        FormField("emergency_status", "急迫程度", "enum",
                  choices=tuple(str(k) for k in _EMERGENCY_ZH), payload_type="int"),
    ),
    # A9 現行：`estate_name`、`description` 皆「非字串或去空白後為空」＝缺；順序＝原
    # `confirm.py` 修繕缺欄區塊的順序（物件、問題描述）。
    requirements=(
        Requirement(required_any_of=(("estate_name",),), ask_group=("estate_name",)),
        Requirement(required_any_of=(("description",),), ask_group=("description",)),
    ),
    presence=PRESENCE_NONBLANK_STR,
)

#: 延期繳費。必填＝（`bill_id` 或 `estate_name`）且 `days`；缺物件時追問組一併請使用者講期別
#: （`BILL_DUE_EXTEND_SPEC`「⛔ 不為了取得帳單編號反問使用者」）。期別 ⛔ 必填（照程式）。
#: 原／新到期日由系統導出（`_fill_bill_fields`），屬 `system` 來源。
BILL_DUE_EXTEND_FORM: Final[WriteForm] = WriteForm(
    action="bill_due_extend",
    title_zh="延後帳單到期日",
    fields=(
        FormField("estate_name", "物件", "text", ask_target=_ASK_TARGET_BY_KEY["estate_name"],
                  max_len=_ESTATE_NAME_FIELD.max_len),
        FormField("period", "期別", "text", max_len=30),
        FormField("days", "延後天數", "int"),
        # 使用者口述的帳單編號屬 user_words（數字閘驗），系統解析的編號 ⛔ 進草稿。
        FormField("bill_id", "帳單編號", "int"),
        FormField("date_expire_before", "原到期日", "date", source=SOURCE_SYSTEM),
        FormField("date_expire_after", "新到期日", "date", source=SOURCE_SYSTEM),
    ),
    requirements=(
        Requirement(required_any_of=(("bill_id",), ("estate_name",)),
                    ask_group=("estate_name", "period")),
        Requirement(required_any_of=(("days",),), ask_group=("days",)),
    ),
    presence=PRESENCE_GIVEN,
)

#: 5 支動作的表單（順序＝`CONFIRM_ACTIONS`）。
FORMS: Final[dict] = {}
for _action in CONFIRM_ACTIONS:
    if _action in CLOSED_ACTION_FIELDS:
        FORMS[_action] = _closed_form(_action)
    elif _action == REPAIR_CREATE_FORM.action:
        FORMS[_action] = REPAIR_CREATE_FORM
    elif _action == BILL_DUE_EXTEND_FORM.action:
        FORMS[_action] = BILL_DUE_EXTEND_FORM
del _action


# ---------------------------------------------------------------------------
# 啟動斷言（任一不成立 ⇒ import 期大聲失敗）
# ---------------------------------------------------------------------------
def _assert_forms() -> None:
    from services.agent.tools import action as action_tools   # 延遲：只為斷言

    spec_actions = {
        str(spec.get("name", ""))[len("jgb2.action."):]
        for spec, _fn in action_tools.ACTION_SPECS
    }
    if not (set(FORMS) == set(CONFIRM_ACTIONS) == spec_actions):
        raise AssertionError(
            "write_forms：表單動作集合 ≠ CONFIRM_ACTIONS ≠ ACTION_SPECS 的動作名"
            f"（表單 {sorted(FORMS)}、CONFIRM_ACTIONS {sorted(CONFIRM_ACTIONS)}、"
            f"ACTION_SPECS {sorted(spec_actions)}）"
        )
    label_targets: dict = {}
    for form in FORMS.values():
        keys = set(form.keys)
        # W1b（§8.5-1）：`asked` 由缺欄**標籤**反查表單鍵 ⇒ 同一表單內標籤必須唯一。
        labels = [f.label for f in form.fields]
        if len(labels) != len(set(labels)):
            raise AssertionError(f"write_forms：{form.action} 表單內標籤重複（`asked` 反查會歧義）")
        if keys & IDENTITY_OWNERSHIP_KEYS:
            raise AssertionError(f"write_forms：{form.action} 含身分／歸屬鍵 {sorted(keys & IDENTITY_OWNERSHIP_KEYS)}")
        if form.presence not in (PRESENCE_GIVEN, PRESENCE_NONBLANK_STR):
            raise AssertionError(f"write_forms：{form.action} presence 值域外")
        for f in form.fields:
            if f.kind not in FIELD_KINDS or f.source not in _SOURCES:
                raise AssertionError(f"write_forms：{form.action}.{f.key} 型別或來源值域外")
            if f.ask_target is not None and f.ask_target not in ASK_TARGETS:
                raise AssertionError(f"write_forms：{form.action}.{f.key} ask_target 不在 ASK_TARGETS")
            if f.kind == "sys_id" and f.source != SOURCE_SYSTEM:
                raise AssertionError(f"write_forms：{form.action}.{f.key} sys_id 必須是 system 來源")
            if f.kind == "enum" and (not f.choices or f.payload_type not in ("str", "int")):
                raise AssertionError(f"write_forms：{form.action}.{f.key} enum 缺值域或 payload 型別")
            # 同一個標籤在各表單必須對到同一個 ask_target（缺欄追問的推導只看標籤）。
            if label_targets.setdefault(f.label, f.ask_target) != f.ask_target:
                raise AssertionError(f"write_forms：標籤 {f.label!r} 在不同表單對到不同 ask_target")
        for req in form.requirements:
            for group in req.required_any_of:
                if not set(group) <= keys:
                    raise AssertionError(f"write_forms：{form.action} 必填組含表外鍵 {group}")
            if not set(req.ask_group) <= keys:
                raise AssertionError(f"write_forms：{form.action} 追問組含表外鍵 {req.ask_group}")


_assert_forms()

# ---------------------------------------------------------------------------
# ① 缺欄計算（5 支共用）
# ---------------------------------------------------------------------------


def _present(form: WriteForm, value: Any) -> bool:
    if form.presence == PRESENCE_NONBLANK_STR:
        return isinstance(value, str) and bool(value.strip())
    return _given(value)


def missing_labels(action: Any, payload: Any) -> list:
    """缺必填欄位的**中文標籤**清單（固定詞彙，⛔ 不含任何使用者值）；表外動作或
    payload 不是物件 ⇒ `[]`。⚠️ `system` 來源（`sys_id`、系統導出的日期）不列為必填。"""
    form = FORMS.get(action) if isinstance(action, str) else None
    if form is None or not isinstance(payload, Mapping):
        return []
    labels: list = []
    for req in form.requirements:
        if any(all(_present(form, payload.get(k)) for k in group)
               for group in req.required_any_of):
            continue
        if req.group_label is not None:
            labels.append(req.group_label)
            continue
        for key in req.ask_group:
            if not _present(form, payload.get(key)):
                labels.append(form.field(key).label)
    return labels


#: 追問句只收的標籤詞彙＝全部表單的欄位標籤＋「至少給一個」組的固定標籤。
MISSING_LABEL_VOCAB: Final[frozenset] = frozenset(
    [f.label for form in FORMS.values() for f in form.fields]
    + [req.group_label for form in FORMS.values() for req in form.requirements
       if req.group_label is not None]
)

#: 標籤 → 表內宣告的 ask_target（只收有宣告的；啟動斷言保證同標籤同對象）。
LABEL_ASK_TARGETS: Final[dict] = {
    f.label: f.ask_target
    for form in FORMS.values() for f in form.fields if f.ask_target is not None
}


def ask_target_for_missing(labels: Any) -> Optional[str]:
    """缺欄追問的 `ask_target`（表驅動，與改動前逐位相同）：
    缺欄中有宣告 `ask_target=estate` 的欄位 ⇒ `estate`；否則恰缺一欄且該欄有宣告
    ask_target ⇒ 該值；其餘 ⇒ `None`。"""
    if not isinstance(labels, list):
        return None
    targets = [LABEL_ASK_TARGETS.get(lb) if isinstance(lb, str) else None for lb in labels]
    if "estate" in targets:
        return "estate"
    if len(labels) == 1 and targets[0] is not None:
        return targets[0]
    return None


# ---------------------------------------------------------------------------
# 開關（`AGENT_WRITE_DRAFT`）
# ---------------------------------------------------------------------------
WRITE_DRAFT_ENV: Final[str] = "AGENT_WRITE_DRAFT"


def write_draft_enabled_from_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    """`on`／`off`；**未設或空字串＝on**（比照 `AGENT_MAX_COMPLETION_TOKENS` 的 `.strip() or 預設`）。
    其他非空值 ⇒ `ValueError`（啟動失敗並說明原因）。"""
    env = os.environ if environ is None else environ
    raw = env.get(WRITE_DRAFT_ENV, "")
    value = (raw or "").strip() or "on"
    if value == "on":
        return True
    if value == "off":
        return False
    raise ValueError(
        f"{WRITE_DRAFT_ENV}={raw!r} 不在允許值域（on／off；未設或空字串＝on）"
    )


# ---------------------------------------------------------------------------
# 意圖判斷呼叫（W1b §8.1-1）：schema、系統句、回應解析
# ---------------------------------------------------------------------------
def _ordered_unique(items) -> Tuple[str, ...]:
    out: list = []
    for item in items:
        if item not in out:
            out.append(item)
    return tuple(out)


#: `fields[].key` 的值域＝各表單 `user_words` 來源鍵的聯集（`system` 鍵 ⛔ 在內）。
WRITE_INTENT_KEY_DOMAIN: Final[Tuple[str, ...]] = _ordered_unique(
    k for form in FORMS.values() for k in form.user_word_keys
)
#: 意圖判斷呼叫的「不是寫入」值（W1b §8.1-1：action 值域＝5 支動作名＋這一個）。
INTENT_NONE: Final[str] = "none"
INTENT_ACTION_DOMAIN: Final[Tuple[str, ...]] = tuple(FORMS) + (INTENT_NONE,)
#: 意圖判斷呼叫的 response_format 名稱（測試替身據此分辨意圖呼叫與主模型呼叫）。
WRITE_INTENT_SCHEMA_NAME: Final[str] = "WriteIntent"
#: 意圖判斷呼叫的輸出上限（W1b §8.5-4：與 `~/jgb-archive/bedrock-eval-20261017/w1/probe/` 一致）。
WRITE_INTENT_MAX_COMPLETION_TOKENS: Final[int] = 800


def write_intent_description() -> str:
    """意圖判斷呼叫的說明文字——動作名與各動作可填的鍵**由表單產生**（gpt-oss 不讀 enum，
    比照 `ask_target` 說明列值域的作法）。W1b：⛔ 再是主輸出 `AgentOutput` 的欄位說明。"""
    parts = []
    for form in FORMS.values():
        keys = []
        for f in form.fields:
            if f.source != SOURCE_USER_WORDS:
                continue
            if f.kind == "enum":
                keys.append(f"{f.key}（只能填 {'／'.join(f.choices)}）")
            else:
                keys.append(f.key)
        parts.append(f"{form.action}（{form.title_zh}）：{'、'.join(keys)}")
    return (
        "使用者這句是要建立或變更系統資料、或在回答「進行中的建立」時填對應動作；"
        f"改談別的事或一般問答 action 填 {INTENT_NONE}、fields 給空陣列。"
        "action 只能是下列動作之一，fields 每筆 {key, value}，key 只能用該動作列出的鍵；"
        "value 只填使用者原話裡出現的值（⛔ 推測、⛔ 代寫），使用者沒講的欄位不要列，"
        "只表達要建立而還沒講任何欄位時 fields 給空陣列；日期寫成 YYYY-MM-DD。"
        "可用的動作與鍵：" + "；".join(parts) + "。"
    )


#: W1c §9.1-3：意圖判斷說明末尾補的一句（逐字；第 0 步探測
#: `~/jgb-archive/bedrock-eval-20261017/w1/probe/probe3_w1c.py` 的 `ADD`，以 "\n" 接在原說明之後）。
#: ⛔ 改字面：用字變更須重跑該探測（D2 抽取率門檻 ≥2/3，計畫 §9.1b）。
WRITE_INTENT_NONE_RULE: Final[str] = (
    "使用者只說名詞或名詞片語、在問功能怎麼用、或在查資料 ⇒ none；"
    "只有使用者明確要系統替他建立或變更一筆資料，或正在回答進行中的建立所需的資料時，才填動作。"
)

#: 意圖判斷呼叫的系統句（原型＝`~/jgb-archive/bedrock-eval-20261017/w1/probe/probe_extract.py`
#: 的 `SYS`；值域與鍵由表單產生；W1c 末尾加 `WRITE_INTENT_NONE_RULE`）。⛔ 含任何使用者值或
#: 資料段——輸入只有本句＋對話歷史。
WRITE_INTENT_SYSTEM_PROMPT: Final[str] = (
    "你只做一件事：讀對話，判斷使用者**最新一句**（可參照前文）是不是在要求建立或變更系統資料，"
    "或是在回答進行中的建立所需的資料。"
    "是 ⇒ action 填對應動作，fields 只填使用者原話裡出現的值（照抄原話，⛔ 推測、⛔ 改寫）；"
    f"不是 ⇒ action 填 {INTENT_NONE}、fields 空陣列。\n"
    + write_intent_description()
    + "\n" + WRITE_INTENT_NONE_RULE
)


def write_intent_call_schema() -> dict:
    """意圖判斷呼叫的 strict schema（W1b §8.1-1；原型同上）：
    `{action: <5 支動作名＋none>, fields: [{key, value}]}`，每一層 object 都封閉。
    根層與 `action`／`key` 的 description 都列出表單導出的值域（gpt-oss 不讀 enum）。"""
    return {
        "type": "object",
        "description": write_intent_description(),
        "properties": {
            "action": {
                "type": "string", "enum": list(INTENT_ACTION_DOMAIN),
                "description": "只能是：" + "、".join(INTENT_ACTION_DOMAIN),
            },
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string", "enum": list(WRITE_INTENT_KEY_DOMAIN),
                            "description": "只能是：" + "、".join(WRITE_INTENT_KEY_DOMAIN),
                        },
                        "value": {"type": "string"},
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["action", "fields"],
        "additionalProperties": False,
    }


def write_intent_response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {"name": WRITE_INTENT_SCHEMA_NAME, "strict": True,
                        "schema": write_intent_call_schema()},
    }


#: 回應解析的三種結果（`parse_write_intent_content` 的第二格）。
PARSE_OK: Final[str] = "ok"
PARSE_UNPARSED: Final[str] = "unparsed"
PARSE_AMBIGUOUS: Final[str] = "ambiguous"


def parse_write_intent_content(content: Any) -> Tuple[Optional[dict], str]:
    """意圖判斷呼叫的原始回應 → `(物件, 狀態)`（W1b §8.1-1／安全處置 3c）。

    - 只解析**最後一個 `</reasoning>` 之後**的最終段（推理段裡的 JSON 樣字串 ⛔ 搶先被解析）；
      有 `<reasoning>` 卻沒有收尾 ⇒ 無最終段 ⇒ `unparsed`。
    - Bedrock 回傳前綴殘缺（例 `{`＋換行＋`"{"action":…}`，見 `w1/probe/probe_raw.json`）⇒ 對最終段
      **逐個 `{` 位置**試 `json.JSONDecoder().raw_decode`；解出的頂層物件（解出後跳過其範圍，
      巢狀的 `{key,value}` 不另算）中帶 `action` 鍵者為候選。
    - 候選 0 個 ⇒ `unparsed`；內容不同的候選多於 1 個 ⇒ `ambiguous`（視為 none）；
      其餘 ⇒ `ok`。⛔ 驗值域（那是呼叫端的事）。
    最終段切法與逐 `{` 解碼與主迴圈共用 `services.agent.llm_output`（正式接線 §3.2 抽出，行為不變）。
    """
    tail = final_segment(content)
    if tail is None:
        return None, PARSE_UNPARSED
    found: list = []
    for obj in iter_json_objects(tail):
        if isinstance(obj, dict) and "action" in obj:
            if obj not in found:
                found.append(obj)
    if not found:
        return None, PARSE_UNPARSED
    if len(found) > 1:
        return None, PARSE_AMBIGUOUS
    return found[0], PARSE_OK


# ---------------------------------------------------------------------------
# 數字與日期的解析（值閘與 `to_payload` 共用）
# ---------------------------------------------------------------------------
_INT_RE: Final = re.compile(r"[+-]?\d+")
_NUMBER_RE: Final = re.compile(r"[+-]?\d+(?:\.\d+)?")
_THOUSANDS_RE: Final = re.compile(r"(?<=\d)[,，](?=\d{3}(?!\d))")


def parse_number(value: Any, kind: str) -> Optional[Any]:
    """草稿字串 → `int`（kind=int）或 `int|float`（kind=number）；不合 ⇒ `None`。
    千分位逗號視同不存在（與 `runtime._number_in_texts` 同一條規則）。"""
    if not isinstance(value, str):
        return None
    text = _THOUSANDS_RE.sub("", unicodedata.normalize("NFKC", value).strip())
    if kind == "int":
        return int(text) if _INT_RE.fullmatch(text) else None
    if _INT_RE.fullmatch(text):
        return int(text)
    if _NUMBER_RE.fullmatch(text):
        return float(text)
    return None


#: W1c §9.11-1：意圖值裡的「數字 token」（NFKC＋千分位照 `_THOUSANDS_RE` 去掉之後再切）。
#: 帶正負號的寫法照 `_NUMBER_RE`（「-7」仍是 -7 ⇒ 之後過不了 `_number_in_texts`，與改動前同）。
_NUMBER_TOKEN_RE: Final = re.compile(r"[+-]?\d+(?:\.\d+)?")


def parse_number_token(value: Any, kind: str) -> Optional[Any]:
    """意圖判斷呼叫給的 `int`／`number` 值 → 數值（W1c §9.11-1）：意圖呼叫照抄原話時常帶單位或
    動詞（「7 天」「延 7 天」），整串比對會解析失敗（§9.10 根因 1）。值裡**恰好一個**數字 token
    ⇒ 用該 token 走 `parse_number`（型別不合，例 int 欄位給「7.5」⇒ `None`）；零個或多個（「七天」
    「7 到 10 天」）⇒ `None`。⚠️ 只是取值；呼叫端仍須以 `_number_in_texts` 驗它出現在使用者原話。"""
    if not isinstance(value, str):
        return None
    text = _THOUSANDS_RE.sub("", unicodedata.normalize("NFKC", value))
    tokens = _NUMBER_TOKEN_RE.findall(text)
    if len(tokens) != 1:
        return None
    return parse_number(tokens[0], kind)


_MODEL_DATE_RES: Final = (
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})"),
    re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日號号]?"),
)
#: 使用者原話裡「有年份」的寫法——**先比對**，比完把那一段挖掉，避免被 `M月D日` 截斷。
_USER_DATE_WITH_YEAR_RES: Final = (
    re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)"),
    re.compile(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)"),
    re.compile(r"(?<!\d)(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日號号]"),
)
_USER_DATE_NO_YEAR_RE: Final = re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日號号]")


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_model_date(value: Any) -> Optional[date]:
    """模型給的日期字串（`YYYY-MM-DD`／`YYYY/MM/DD`／`YYYYMMDD`／`YYYY年M月D日`）→ `date`。"""
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKC", value).strip()
    for rx in _MODEL_DATE_RES:
        m = rx.fullmatch(text)
        if m:
            return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def user_text_dates(texts: Any, today: date) -> set:
    """使用者訊息裡可解析出的日期集合（plan §2.1(3) 日期閘）：
    `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年M月D日／號`（用使用者講的年份），
    `M月D日／號`（無年份 ⇒ 今年或明年中第一個不早於 `today` 者）。"""
    found: set = set()
    for raw in texts or ():
        if not isinstance(raw, str):
            continue
        rest = unicodedata.normalize("NFKC", raw)
        for rx in _USER_DATE_WITH_YEAR_RES:
            for m in rx.finditer(rest):
                d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if d is not None:
                    found.add(d)
            rest = rx.sub(" ", rest)
        for m in _USER_DATE_NO_YEAR_RE.finditer(rest):
            month, day = int(m.group(1)), int(m.group(2))
            for year in (today.year, today.year + 1):
                d = _safe_date(year, month, day)
                if d is not None and d >= today:
                    found.add(d)
                    break
    return found


def iso_date(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"


# ---------------------------------------------------------------------------
# 草稿值 → payload 值（5 支共用）
# ---------------------------------------------------------------------------
def to_payload(action: Any, fields: Any) -> dict:
    """草稿欄位（一律字串）→ `confirm.request` payload 的值（**不含** `action` 鍵）。

    `int`／`number` 轉數值、`date` 轉 `confirm_card._parse_date` 收的 `YYYYMMDD`、`enum` 依
    表內 `payload_type` 轉（`emergency_status` ⇒ int）、其餘照原字串。轉換失敗的欄位
    ⛔ 放進 payload（＝缺 ⇒ 進缺欄追問）；表外鍵與 `system` 來源鍵一律丟掉。
    """
    form = FORMS.get(action) if isinstance(action, str) else None
    out: dict = {}
    if form is None or not isinstance(fields, Mapping):
        return out
    for f in form.fields:
        if f.source != SOURCE_USER_WORDS or f.key not in fields:
            continue
        value = fields[f.key]
        if not isinstance(value, str):
            continue
        if f.kind in ("int", "number"):
            num = parse_number(value, f.kind)
            if num is not None:
                out[f.key] = num
        elif f.kind == "date":
            d = parse_model_date(value)
            if d is not None:
                out[f.key] = f"{d.year:04d}{d.month:02d}{d.day:02d}"
        elif f.kind == "enum":
            if value in f.choices:
                out[f.key] = int(value) if f.payload_type == "int" else value
        else:
            out[f.key] = value
    return out


# ---------------------------------------------------------------------------
# 會話草稿 `write_draft` 的形狀（存在 `state["agent"]`，經 `AgentSession` 讀寫）
# ---------------------------------------------------------------------------
#: 草稿的封閉五鍵（⛔ token、⛔ 系統解析的編號類值）。W1b §8.5-1 加 `asked`＝上回合**程式缺欄
#: 追問**所問欄位的**表單鍵**清單（⛔ 中文標籤）；只對緊接的下一回合有效（讀出即清）。
DRAFT_KEYS: Final[frozenset] = frozenset(
    {"action", "fields", "idle_turns", "created_by_role", "asked"})
#: 連續幾回合沒有寫入相關動作（意圖判斷為 none 等）就清掉（使用者改談別的）。
DRAFT_IDLE_LIMIT: Final[int] = 2


def value_max_len(f: FormField) -> int:
    return f.max_len or _DEFAULT_VALUE_MAX


def new_draft(action: str, owner: str) -> dict:
    return {"action": action, "fields": {}, "idle_turns": 0, "created_by_role": owner, "asked": []}


#: 名稱欄位（W1b §8.5-2）：⛔ 以整句原文填入——物件名稱只由前置查詢唯一命中或意圖呼叫抽取；
#: 合約名稱只由意圖呼叫抽取（前置查詢只查物件）。
NAME_KEYS: Final[frozenset] = frozenset({"estate_name", "contract_ref"})


def asked_keys_for_labels(action: Any, labels: Any) -> list:
    """缺欄**標籤**（`missing_labels` 的輸出）→ `asked` 的**表單鍵**清單（W1b §8.5-1）。

    欄位標籤 ⇒ 該欄位鍵；「至少給一個」組的固定標籤 ⇒ 組內各鍵。只收 `user_words` 來源鍵、
    去重、保序；表外動作／非清單 ⇒ `[]`。標籤在同一表單內唯一（啟動斷言），反查不歧義。"""
    form = FORMS.get(action) if isinstance(action, str) else None
    if form is None or not isinstance(labels, list):
        return []
    keys: list = []
    for label in labels:
        if not isinstance(label, str):
            continue
        group = next((req.required_any_of for req in form.requirements
                      if req.group_label is not None and req.group_label == label), None)
        cands = ([k for g in group for k in g] if group is not None
                 else [f.key for f in form.fields if f.label == label])
        for key in cands:
            f = form.field(key)
            if f is not None and f.source == SOURCE_USER_WORDS and key not in keys:
                keys.append(key)
    return keys


def load_draft(raw: Any) -> Tuple[Optional[dict], bool]:
    """從 `form_sessions.collected_data` 讀回的草稿——**一律視為不可信**。

    回 `(draft, shape_invalid)`：沒有草稿 ⇒ `(None, False)`；形狀不合（鍵集合、動作、
    欄位鍵、值型別、長度上限、計數）⇒ `(None, True)`（呼叫端整份丟棄並記 violation）。
    """
    if raw is None:
        return None, False
    if not isinstance(raw, dict) or set(raw) != DRAFT_KEYS:
        return None, True
    action = raw.get("action")
    form = FORMS.get(action) if isinstance(action, str) and action in CONFIRM_ACTIONS else None
    fields = raw.get("fields")
    idle = raw.get("idle_turns")
    owner = raw.get("created_by_role")
    asked = raw.get("asked")
    if (form is None or not isinstance(fields, dict)
            or isinstance(idle, bool) or not isinstance(idle, int)
            or not 0 <= idle < DRAFT_IDLE_LIMIT
            or not isinstance(owner, str) or not owner):
        return None, True
    # W1b §8.5-1／安全處置 4b：`asked` 為清單、元素皆為**該動作**表單的 `user_words` 鍵、
    # 不重複、長度 ≤ 表單欄位數；不合 ⇒ 整份丟棄。
    if (not isinstance(asked, list) or len(asked) > len(form.fields)
            or len(set(k for k in asked if isinstance(k, str))) != len(asked)
            or any(not isinstance(k, str) or form.field(k) is None
                   or form.field(k).source != SOURCE_USER_WORDS for k in asked)):
        return None, True
    clean: dict = {}
    for key, value in fields.items():
        f = form.field(key)
        if (f is None or f.source != SOURCE_USER_WORDS or not isinstance(value, str)
                or not value.strip() or len(value) > value_max_len(f)):
            return None, True
        clean[key] = value
    return {"action": action, "fields": clean, "idle_turns": idle, "created_by_role": owner,
            "asked": list(asked)}, False


#: 草稿注入段的固定外框（⛔ 放使用者值，只放標籤）。
DRAFT_LINE_TEMPLATE: Final[str] = "進行中的建立：{title}；已有：{have}；還缺：{missing}"
DRAFT_LINE_NONE: Final[str] = "（無）"


def draft_injection_text(draft: Mapping[str, Any]) -> str:
    """「進行中的建立：<動作中文名>；已有：<標籤>；還缺：<標籤>」——**只放標籤**。"""
    form = FORMS[draft["action"]]
    fields = draft.get("fields") or {}
    have = [f.label for f in form.fields if f.key in fields]
    missing = missing_labels(form.action, to_payload(form.action, fields))
    return DRAFT_LINE_TEMPLATE.format(
        title=form.title_zh,
        have="、".join(have) or DRAFT_LINE_NONE,
        missing="、".join(missing) or DRAFT_LINE_NONE,
    )


# ---------------------------------------------------------------------------
# violation 固定字串（⛔ 帶值；trace／decision_snapshot 只見鍵名與這些常數）
# ---------------------------------------------------------------------------
V_OUT_OF_DOMAIN: Final[str] = "write_intent_out_of_domain"
V_NOT_VISIBLE: Final[str] = "write_intent_action_not_visible"
V_NOT_IN_USER_WORDS: Final[str] = "write_intent_value_not_in_user_words"
V_VALUE_OUT_OF_DOMAIN: Final[str] = "write_intent_value_out_of_domain"
V_VALUE_TOO_LONG: Final[str] = "write_intent_value_too_long"
V_CATEGORY_INVALID: Final[str] = "write_intent_category_invalid"
V_DRAFT_SHAPE_INVALID: Final[str] = "write_draft_shape_invalid"
V_PROGRAM_CONFIRM: Final[str] = "write_draft_program_confirm"
V_PROGRAM_NONTERMINAL: Final[str] = "write_draft_program_confirm_nonterminal"
V_DRAFT_CLEARED_IDLE: Final[str] = "write_draft_cleared_idle"
V_NAME_CAUGHT: Final[str] = "write_draft_name_caught"
V_ANSWER_FILLED: Final[str] = "write_draft_answer_filled"
#: W1b：意圖判斷呼叫的收尾（已完成且計量／失敗或逾時／被取消並以估算計入）與解析結果。
V_CALL: Final[str] = "write_intent_call"
V_CALL_FAILED: Final[str] = "write_intent_call_failed"
V_CALL_CANCELLED: Final[str] = "write_intent_call_cancelled"
V_UNPARSED: Final[str] = "write_intent_unparsed"
V_AMBIGUOUS: Final[str] = "write_intent_ambiguous"
#: W1b §8.5-3：程式追問後當句是問句 ⇒ 本回合草稿凍結（⛔ 合併意圖、⛔ 補名稱、⛔ 觸發）。
V_QUESTION_FROZEN: Final[str] = "write_draft_question_frozen"
#: W1c §9.7 F1：程式優先等意圖判斷呼叫逾時（task 未完成）⇒ 不走程式優先、意圖留給輸出後觸發點
#: （⛔ 記 `write_intent_call_failed`、⛔ 視為已取用）。
V_PROGRAM_FIRST_WAIT_TIMEOUT: Final[str] = "write_draft_program_first_wait_timeout"
#: W1c §9.11-2：本回合前置查詢唯一命中而寫進草稿的物件名稱（系統值）在場時，意圖呼叫的其他文字
#: 欄位值是該名稱或「當句被判為物件名稱那一段」的子字串 ⇒ 丟棄（同一段原話不填兩欄）。
V_VALUE_OVERLAPS_NAME: Final[str] = "write_intent_value_overlaps_name"
#: 「本回合草稿長什麼樣」的稽核：只有動作名與**鍵名**（封閉詞彙）。
TRACE_DRAFT_ACTION_PREFIX: Final[str] = "write_draft_action:"
TRACE_DRAFT_KEYS_PREFIX: Final[str] = "write_draft_keys:"


def draft_trace_marks(draft: Mapping[str, Any]) -> Tuple[str, str]:
    """草稿的兩個稽核字串（`write_draft_action:<動作>`、`write_draft_keys:<鍵,…>`）。"""
    keys = sorted(k for k in (draft.get("fields") or {}) if isinstance(k, str))
    return (f"{TRACE_DRAFT_ACTION_PREFIX}{draft.get('action')}",
            f"{TRACE_DRAFT_KEYS_PREFIX}{','.join(keys)}")


__all__ = [
    "FIELD_KINDS", "SOURCE_USER_WORDS", "SOURCE_SYSTEM", "PRESENCE_GIVEN", "PRESENCE_NONBLANK_STR",
    "FormField", "Requirement", "WriteForm", "FORMS",
    "REPAIR_CREATE_FORM", "BILL_DUE_EXTEND_FORM",
    "missing_labels", "MISSING_LABEL_VOCAB", "LABEL_ASK_TARGETS", "ask_target_for_missing",
    "WRITE_DRAFT_ENV", "write_draft_enabled_from_env",
    "WRITE_INTENT_KEY_DOMAIN", "INTENT_NONE", "INTENT_ACTION_DOMAIN", "WRITE_INTENT_SCHEMA_NAME",
    "WRITE_INTENT_MAX_COMPLETION_TOKENS", "write_intent_description", "WRITE_INTENT_SYSTEM_PROMPT",
    "write_intent_call_schema", "write_intent_response_format",
    "PARSE_OK", "PARSE_UNPARSED", "PARSE_AMBIGUOUS", "parse_write_intent_content",
    "parse_number", "parse_number_token", "parse_model_date", "user_text_dates", "iso_date", "to_payload",
    "DRAFT_KEYS", "DRAFT_IDLE_LIMIT", "value_max_len", "new_draft", "NAME_KEYS",
    "asked_keys_for_labels", "load_draft",
    "DRAFT_LINE_TEMPLATE", "DRAFT_LINE_NONE", "draft_injection_text",
    "V_OUT_OF_DOMAIN", "V_NOT_VISIBLE", "V_NOT_IN_USER_WORDS", "V_VALUE_OUT_OF_DOMAIN",
    "V_VALUE_TOO_LONG", "V_CATEGORY_INVALID", "V_DRAFT_SHAPE_INVALID", "V_PROGRAM_CONFIRM",
    "V_PROGRAM_NONTERMINAL", "V_DRAFT_CLEARED_IDLE", "V_NAME_CAUGHT", "V_ANSWER_FILLED",
    "V_CALL", "V_CALL_FAILED", "V_CALL_CANCELLED", "V_UNPARSED", "V_AMBIGUOUS", "V_QUESTION_FROZEN",
    "V_PROGRAM_FIRST_WAIT_TIMEOUT", "V_VALUE_OVERLAPS_NAME", "WRITE_INTENT_NONE_RULE",
    "TRACE_DRAFT_ACTION_PREFIX", "TRACE_DRAFT_KEYS_PREFIX", "draft_trace_marks",
]
