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
from typing import Any, Callable, Final, Mapping, Optional, Tuple

# A8（單一動作登錄）：動作值域在呼叫當下以模組參照讀，⛔ import 期複製。
from services.agent import confirm_card as _confirm_card
from services.agent.confirm_card import (
    CLOSED_ACTION_ANY_OF,
    CLOSED_ACTION_EXTRA_KEYS,
    CLOSED_ACTION_FIELDS,
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
#: 期別片 P-2：`period`＝期別（值閘比**解析後的年月**，草稿存程式正規化的 `YYYY/MM`
#: ／`YYYY/MM 未繳`／`未繳`，見 `runtime._write_draft_gate_value`；`to_payload` 照字串送出，
#: 由 `tools.confirm._resolve_bill_by_period` 以 `bill_period.parse_period` 讀回）。
FIELD_KINDS: Final[frozenset] = frozenset({
    "text", "int", "number", "date", "email", "phone", "enum", "sys_id", "category", "period",
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

    `choice_labels`（第 3 步 A4）：只對 `enum` 有意義——與 `choices` **逐位對應**的標籤，
    取自卡上顯示用的同一份對照（`confirm_card._EMERGENCY_ZH`／封閉表 `_ClosedField.choices`
    的值），⛔ 另抄字面量。意圖判斷呼叫只看得到、只能填標籤；標籤 → 代碼由程式依本欄轉。
    """

    key: str
    label: str
    kind: str
    source: str = SOURCE_USER_WORDS
    ask_target: Optional[str] = None
    max_len: int = 0
    choices: Tuple[str, ...] = ()
    payload_type: str = "str"
    choice_labels: Tuple[str, ...] = ()


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
class FormPrecheck:
    """第 3 步 A6：出卡前預檢的**表單宣告**（共用出卡流程 `confirm.request` 依宣告執行，
    流程層 ⛔ 出現動作名）。

    - `id_key`：哪個欄位是既有資料的編號（payload 該欄有值才執行）；
    - `lookup`：帶 viewer 的唯讀單筆查詢，`async (api, role_id, user_id, ref) ->
      ("one"|"none"|"error", row)`（⛔ 寫入端點、⛔ token）；
    - `derive`：從讀到的列算出系統欄位並寫回 payload，`(payload, row, *, today) -> bool`
      （`False` ⇒ 算不出 ⇒ 不出卡，回封閉樣板）；
    - `derived_keys`：`derive` 會寫的 `SOURCE_SYSTEM` 欄位（啟動斷言核對）。
    """

    id_key: str
    lookup: Callable
    derive: Callable
    derived_keys: Tuple[str, ...]


@dataclass(frozen=True)
class WriteForm:
    action: str
    #: 注入行與 schema 說明用的動作中文名（固定詞彙）。
    title_zh: str
    fields: Tuple[FormField, ...]
    requirements: Tuple[Requirement, ...]
    presence: str = PRESENCE_GIVEN
    #: 第 3 步 A6：選填的出卡前預檢宣告（`None` ⇒ 不預檢＝現行）。
    precheck: Optional[FormPrecheck] = None

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
            # A4：標籤＝卡上中文（同一個 Mapping 的值，與 `choices` 逐位對應）。
            choice_labels=tuple((f.choices or {}).values()),
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
                  choices=tuple(str(k) for k in _EMERGENCY_ZH), payload_type="int",
                  # A4：標籤＝卡上「急迫程度」那一行印的字（同一份 `_EMERGENCY_ZH`）。
                  choice_labels=tuple(_EMERGENCY_ZH.values())),
    ),
    # A9 現行：`estate_name`、`description` 皆「非字串或去空白後為空」＝缺；順序＝原
    # `confirm.py` 修繕缺欄區塊的順序（物件、問題描述）。
    requirements=(
        Requirement(required_any_of=(("estate_name",),), ask_group=("estate_name",)),
        Requirement(required_any_of=(("description",),), ask_group=("description",)),
    ),
    presence=PRESENCE_NONBLANK_STR,
)

async def _bill_precheck_lookup(api: Any, role_id: Any, user_id: Any, ref: Any) -> tuple:
    """延期繳費預檢的查詢：重用兌現端同一個單筆探測（`tools.action.viewer_bill_row`，A0 RC1）。
    （延遲 import：`tools.confirm` 會 import 本檔，避免循環。）"""
    from services.agent.tools.action import viewer_bill_row
    return await viewer_bill_row(api, role_id, user_id, ref)


def _bill_precheck_derive(payload: dict, row: dict, *, today: date) -> bool:
    """延期繳費預檢的系統值重算：重用既有 `tools.confirm._fill_bill_fields`（§7 F8：有編號的
    延期卡以 viewer 讀到的列重算原到期日，⛔ 信模型填的值）。"""
    from services.agent.tools.confirm import _fill_bill_fields
    return _fill_bill_fields(payload, row, today=today)


#: 延期繳費。必填＝（`bill_id` 或 `estate_name`）且 `days`；缺物件時追問組一併請使用者講期別
#: （`BILL_DUE_EXTEND_SPEC`「⛔ 不為了取得帳單編號反問使用者」）。期別 ⛔ 必填（照程式）。
#: 原／新到期日由系統導出（`_fill_bill_fields`），屬 `system` 來源。
BILL_DUE_EXTEND_FORM: Final[WriteForm] = WriteForm(
    action="bill_due_extend",
    title_zh="延後帳單到期日",
    fields=(
        FormField("estate_name", "物件", "text", ask_target=_ASK_TARGET_BY_KEY["estate_name"],
                  max_len=_ESTATE_NAME_FIELD.max_len),
        # 期別片 P-2：`period` 型（⛔ `text` 的原話子字串規則：模型正規化成「2027/05」會被丟掉）。
        FormField("period", "期別", "period", max_len=30),
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
    # 第 3 步 A6／F8：有帳單編號 ⇒ 出卡前以 viewer 單筆讀該帳單、由那一列重算原／新到期日。
    precheck=FormPrecheck(
        id_key="bill_id", lookup=_bill_precheck_lookup, derive=_bill_precheck_derive,
        derived_keys=("date_expire_before", "date_expire_after"),
    ),
)

#: 5 支動作的表單（順序＝`CONFIRM_ACTIONS`）。
FORMS: Final[dict] = {}
for _action in _confirm_card.CONFIRM_ACTIONS:
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
    if not (set(FORMS) == set(_confirm_card.CONFIRM_ACTIONS) == spec_actions):
        raise AssertionError(
            "write_forms：表單動作集合 ≠ CONFIRM_ACTIONS ≠ ACTION_SPECS 的動作名"
            f"（表單 {sorted(FORMS)}、CONFIRM_ACTIONS {sorted(_confirm_card.CONFIRM_ACTIONS)}、"
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
            # A4：enum 標籤與代碼逐位對應、標籤不重複、標籤與代碼不交疊（轉碼不歧義）。
            if f.kind == "enum" and (
                len(f.choice_labels) != len(f.choices)
                or len(set(f.choice_labels)) != len(f.choice_labels)
                or not all(isinstance(lb, str) and lb.strip() for lb in f.choice_labels)
            ):
                raise AssertionError(f"write_forms：{form.action}.{f.key} enum 標籤與代碼不逐位對應")
            # 同一個標籤在各表單必須對到同一個 ask_target（缺欄追問的推導只看標籤）。
            if label_targets.setdefault(f.label, f.ask_target) != f.ask_target:
                raise AssertionError(f"write_forms：標籤 {f.label!r} 在不同表單對到不同 ask_target")
        if form.precheck is not None:
            pc = form.precheck
            system_keys = {f.key for f in form.fields if f.source == SOURCE_SYSTEM}
            if (pc.id_key not in keys or not callable(pc.lookup) or not callable(pc.derive)
                    or not set(pc.derived_keys) <= system_keys):
                raise AssertionError(f"write_forms：{form.action} 預檢宣告不合（編號欄／系統欄位）")
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


def missing_label_vocab() -> frozenset:
    """追問句只收的標籤詞彙＝全部表單的欄位標籤＋「至少給一個」組的固定標籤
    （第 3 步 #2：**呼叫當下**讀 `FORMS`——只在表單登錄加入的動作，標籤也進詞彙）。"""
    return frozenset(
        [f.label for form in FORMS.values() for f in form.fields]
        + [req.group_label for form in FORMS.values() for req in form.requirements
           if req.group_label is not None]
    )


def label_ask_targets() -> dict:
    """標籤 → 表內宣告的 ask_target（只收有宣告的；啟動斷言保證同標籤同對象；呼叫當下讀 `FORMS`）。"""
    return {
        f.label: f.ask_target
        for form in FORMS.values() for f in form.fields if f.ask_target is not None
    }


#: 追問句只收的標籤詞彙（import 期快照；流程一律呼叫 `missing_label_vocab()`，常數保留相容）。
MISSING_LABEL_VOCAB: Final[frozenset] = missing_label_vocab()

#: 標籤 → ask_target（import 期快照；流程一律呼叫 `label_ask_targets()`，常數保留相容）。
LABEL_ASK_TARGETS: Final[dict] = label_ask_targets()


def ask_target_for_missing(labels: Any) -> Optional[str]:
    """缺欄追問的 `ask_target`（表驅動，與改動前逐位相同）：
    缺欄中有宣告 `ask_target=estate` 的欄位 ⇒ `estate`；否則恰缺一欄且該欄有宣告
    ask_target ⇒ 該值；其餘 ⇒ `None`。"""
    if not isinstance(labels, list):
        return None
    by_label = label_ask_targets()
    targets = [by_label.get(lb) if isinstance(lb, str) else None for lb in labels]
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
# 開關（`AGENT_WRITE_LIFECYCLE`）：主線第 3 步 A 片 A1～A4、A6 共用
# ---------------------------------------------------------------------------
#: 第 3 步 A 片（A1 草稿生命週期、A2 卡後改欄位、A3「修改」按鈕、A4 enum 由程式轉碼、A6 出卡前
#: 預檢）共用一個開關。讀法比照 `AGENT_WRITE_DRAFT`：**未設或空字串＝on**、`off`＝現行行為。
#: ⚠️ A7（唯一有效卡）與 A0 RC1（兌現端單筆可見性探測）**不隨本開關關閉**（安全強化／語義
#:    不變的錯誤修正；回退＝git revert）。
WRITE_LIFECYCLE_ENV: Final[str] = "AGENT_WRITE_LIFECYCLE"


def write_lifecycle_enabled_from_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    """`on`／`off`；**未設或空字串＝on**。其他非空值 ⇒ `ValueError`（啟動失敗並說明原因）。"""
    env = os.environ if environ is None else environ
    raw = env.get(WRITE_LIFECYCLE_ENV, "")
    value = (raw or "").strip() or "on"
    if value == "on":
        return True
    if value == "off":
        return False
    raise ValueError(
        f"{WRITE_LIFECYCLE_ENV}={raw!r} 不在允許值域（on／off；未設或空字串＝on）"
    )


# ---------------------------------------------------------------------------
# 開關（`AGENT_WRITE_PROPOSAL`）：A+ 片（出卡只由程式依草稿觸發）
# ---------------------------------------------------------------------------
#: A+ 片 AP-0：模型自己呼叫 `confirm.request` 改為「提議」（合併進草稿、下一步由程式決定）、
#: 「卡片還在」重出同卡、綁定卡狀態唯讀查詢、值相同改比正規化值。讀法比照 `AGENT_WRITE_DRAFT`：
#: **未設或空字串＝on**、`off`＝現行行為。⚠️ 本片行為只在 `AGENT_WRITE_DRAFT`、
#: `AGENT_WRITE_LIFECYCLE` 與本開關**三者皆 on** 時生效。
WRITE_PROPOSAL_ENV: Final[str] = "AGENT_WRITE_PROPOSAL"


def write_proposal_enabled_from_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    """`on`／`off`；**未設或空字串＝on**。其他非空值 ⇒ `ValueError`（啟動失敗並說明原因）。"""
    env = os.environ if environ is None else environ
    raw = env.get(WRITE_PROPOSAL_ENV, "")
    value = (raw or "").strip() or "on"
    if value == "on":
        return True
    if value == "off":
        return False
    raise ValueError(
        f"{WRITE_PROPOSAL_ENV}={raw!r} 不在允許值域（on／off；未設或空字串＝on）"
    )


#: A+ 片 AP-2（業主原話 2）：綁定卡有效、本回合寫進草稿的值與卡相同 ⇒ 程式固定句＋同一張卡文字
#: （⛔ 交模型；⛔ 新 token）。
CARD_STILL_VALID_TEXT: Final[str] = "卡片還在，請按確認。"
#: A+ 片 AP-2（業主 2026-10-19 裁 Q2）：同上，但本回合**使用者句子**帶出的值（意圖合併或整句
#: 填入）有被值閘丟掉 ⇒ 改說沒套用（模型提議被丟的值不算）。
CARD_UNCHANGED_TEXT: Final[str] = (
    "這次的修改沒有套用，卡片內容沒變；要送出請按確認，要改請按「我要修改」"
)


#: A3：按「修改」⇒ 程式固定句問要改哪一項（⛔ 放使用者值，只列表單宣告的欄位標籤）。
EDIT_ASK_TEMPLATE: Final[str] = (
    "好的，這張確認卡先不送出。要修改哪一項？卡上可以改的有：{labels}。"
    "請直接告訴我要改成什麼，我再幫您重新整理確認卡。"
)
#: 動作不在表單內（理論上不會發生：pending 的動作已過封閉值域）⇒ 不列標籤的同一句。
EDIT_ASK_FALLBACK_TEXT: Final[str] = (
    "好的，這張確認卡先不送出。要修改哪一項？請直接告訴我要改成什麼，我再幫您重新整理確認卡。"
)


#: 第 3 步 #9g（業主 2026-10-19 裁定）：送出成功後，使用者下一句經意圖判斷為「修改剛送出的那一筆」
#: ⇒ 程式固定句（⛔ 放使用者值、⛔ 交模型改寫；無新卡、不建草稿）。
SUBMITTED_EDIT_TEXT: Final[str] = (
    "剛才那筆已經送出，這裡沒辦法修改；如果要另外再送一筆，請直接告訴我要辦什麼。"
)
#: 第 3 步 #9b（Q5）：A2 已燒掉綁定卡、但這一回合的新卡沒出成（`confirm.request` 非終結結果：
#: render 失敗、日期早於今天、未帶查無標記的 NO_MATCH、例外）⇒ 程式固定句結束回合
#: （⛔ 交模型：模型可能自由寫出「請確認」而實際上沒有任何一張可送出的卡）。
REISSUE_NOT_ISSUED_TEXT: Final[str] = (
    "原本那張確認卡已經失效；修改後的內容這次沒辦法產生新的確認卡，這筆還沒有送出。"
    "請再告訴我一次要怎麼改。"
)


#: A+ 片 r3 AP-7 (2)(a)（業主 2026-10-19 裁示，計畫 §9.6）：模型提議沒有任何值進草稿、綁定卡仍有效且
#: 草稿值＝卡 ⇒ 程式中性句＋同一張卡（⛔ 宣稱有修改嘗試、⛔ 說「卡片還在」；⛔ 新 token）。
PROPOSAL_NO_VALUE_CARD_TEXT: Final[str] = (
    "這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」"
    "或直接說要改哪一項、改成什麼。"
)
#: A+ 片 r3 AP-7 (2)(b)：模型提議沒有任何值進草稿、(a) 不成立 ⇒ 程式固定句（⛔ 放使用者值，只列表單
#: 宣告的欄位標籤；標籤規則同 `edit_ask_text`）。
PROPOSAL_NO_VALUE_TEXT: Final[str] = (
    "這句我沒有讀到要填寫或修改的內容，目前沒有更新。可以填寫或修改的有：{labels}。"
    "請直接說哪一項、內容是什麼，我再幫您整理成確認卡。"
)
#: 同上，無標籤（動作不在表單內、或表單沒有 `user_words` 欄位）⇒ 去掉中間那句。
PROPOSAL_NO_VALUE_FALLBACK_TEXT: Final[str] = (
    "這句我沒有讀到要填寫或修改的內容，目前沒有更新。"
    "請直接說哪一項、內容是什麼，我再幫您整理成確認卡。"
)


def _user_word_labels(action: Any, payload: Any) -> Tuple[str, ...]:
    """表單宣告的欄位標籤：**有值**的 `user_words` 欄位；都沒有值 ⇒ 該表單全部 `user_words` 欄位；
    動作不在表單內 ⇒ 空（⛔ 動作名／欄位名分支；⛔ 回任何值）。`edit_ask_text` 與
    `proposal_no_value_text` 共用。"""
    form = FORMS.get(action) if isinstance(action, str) else None
    if form is None:
        return ()
    values = payload if isinstance(payload, Mapping) else {}
    user_fields = [f for f in form.fields if f.source == SOURCE_USER_WORDS]
    labels = [f.label for f in user_fields if _given(values.get(f.key))]
    if not labels:
        labels = [f.label for f in user_fields]
    return tuple(labels)


def edit_ask_text(action: Any, payload: Any) -> str:
    """A3「修改」的程式固定句：列**卡上有值**、使用者可改（`user_words` 來源）的欄位標籤
    （取自表單宣告，⛔ 動作名／欄位名分支）；卡上沒有任何這類欄位有值 ⇒ 列該表單全部
    `user_words` 欄位標籤。"""
    labels = _user_word_labels(action, payload)
    if not labels:
        return EDIT_ASK_FALLBACK_TEXT
    return EDIT_ASK_TEMPLATE.format(labels="、".join(labels))


def proposal_no_value_text(action: Any, payload: Any) -> str:
    """A+ 片 r3 AP-7 (2)(b)：`payload`＝`to_payload(草稿)`；標籤規則同 `edit_ask_text`
    （`_user_word_labels`）；無標籤 ⇒ `PROPOSAL_NO_VALUE_FALLBACK_TEXT`。"""
    labels = _user_word_labels(action, payload)
    if not labels:
        return PROPOSAL_NO_VALUE_FALLBACK_TEXT
    return PROPOSAL_NO_VALUE_TEXT.format(labels="、".join(labels))


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


def enum_code_for_label(f: Any, label: Any) -> Optional[str]:
    """第 3 步 A4：enum 欄位的標籤 → 代碼（表單 `choice_labels` 與 `choices` 逐位對應）。
    不是該欄的標籤（含代碼本身、近義詞、空白）⇒ `None`（呼叫端視為缺值）。
    ⛔ 語意比對、⛔ 詞表：只認表單宣告的標籤原字（前後空白不計）。"""
    if not isinstance(label, str) or getattr(f, "kind", None) != "enum":
        return None
    text = label.strip()
    for code, lb in zip(f.choices, f.choice_labels):
        if text == lb:
            return code
    return None


def intent_action_domain() -> Tuple[str, ...]:
    """意圖判斷呼叫的 action 值域（**呼叫當下**讀 `FORMS`；常數 `INTENT_ACTION_DOMAIN` 保留相容）。"""
    return tuple(FORMS) + (INTENT_NONE,)


def write_intent_key_domain() -> Tuple[str, ...]:
    """`fields[].key` 值域（呼叫當下讀 `FORMS`；常數 `WRITE_INTENT_KEY_DOMAIN` 保留相容）。"""
    return _ordered_unique(k for form in FORMS.values() for k in form.user_word_keys)


def write_intent_description(*, enum_labels: bool = True) -> str:
    """意圖判斷呼叫的說明文字——動作名與各動作可填的鍵**由表單產生**（gpt-oss 不讀 enum，
    比照 `ask_target` 說明列值域的作法）。W1b：⛔ 再是主輸出 `AgentOutput` 的欄位說明。

    第 3 步 A4：`enum_labels=True`（`AGENT_WRITE_LIFECYCLE` on）⇒ enum 欄位列**標籤**（例
    「非緊急／緊急」，程式再轉代碼）；`False`（off）⇒ 現行列代碼。"""
    parts = []
    for form in FORMS.values():
        keys = []
        for f in form.fields:
            if f.source != SOURCE_USER_WORDS:
                continue
            if f.kind == "enum":
                shown = f.choice_labels if enum_labels else f.choices
                keys.append(f"{f.key}（只能填 {'／'.join(shown)}）")
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

#: 第 3 步 #9g：意圖判斷呼叫的布林欄位（開關 on 才進 schema 與系統句；off 時兩者逐字不變）。
MODIFIES_SUBMITTED_KEY: Final[str] = "modifies_submitted"
#: 欄位說明（schema `description`），同一句也接在 on 的系統句末尾（gpt-oss 不讀 schema 說明）。
MODIFIES_SUBMITTED_RULE: Final[str] = (
    "modifies_submitted：使用者最新一句是不是要修改「剛剛已經送出（已完成）的那一筆」；"
    "是 ⇒ true（action 照上面的規則填那一筆的動作）；不是、或沒有已送出的那一筆 ⇒ false。"
)


#: 意圖判斷呼叫的系統句（原型＝`~/jgb-archive/bedrock-eval-20261017/w1/probe/probe_extract.py`
#: 的 `SYS`；值域與鍵由表單產生；W1c 末尾加 `WRITE_INTENT_NONE_RULE`）。⛔ 含任何使用者值或
#: 資料段——輸入只有本句＋對話歷史。
def write_intent_system_prompt(*, enum_labels: bool = True,
                               modifies_flag: Optional[bool] = None) -> str:
    """意圖判斷呼叫的系統句（呼叫當下由 `FORMS` 產生；A4 `enum_labels` 見
    `write_intent_description`）。第 3 步 #9g：`modifies_flag`（預設跟 `enum_labels`＝開關 on）⇒
    第一段末尾（說明之前）接 `MODIFIES_SUBMITTED_RULE`；系統句結尾仍是「說明＋\\n＋
    `WRITE_INTENT_NONE_RULE`」（W1c §9.1-3 核可的接法不動）。off ⇒ 與改動前逐字相同。"""
    flag = enum_labels if modifies_flag is None else modifies_flag
    return (
        "你只做一件事：讀對話，判斷使用者**最新一句**（可參照前文）是不是在要求建立或變更系統資料，"
        "或是在回答進行中的建立所需的資料。"
        "是 ⇒ action 填對應動作，fields 只填使用者原話裡出現的值（照抄原話，⛔ 推測、⛔ 改寫）；"
        f"不是 ⇒ action 填 {INTENT_NONE}、fields 空陣列。"
        + (MODIFIES_SUBMITTED_RULE if flag else "")
        + "\n"
        + write_intent_description(enum_labels=enum_labels)
        + "\n" + WRITE_INTENT_NONE_RULE
    )


#: 預設（開關 on）的系統句；保留常數供既有引用（runtime 改呼叫 `write_intent_system_prompt`）。
WRITE_INTENT_SYSTEM_PROMPT: Final[str] = write_intent_system_prompt()


def write_intent_call_schema(*, enum_labels: bool = True,
                             modifies_flag: Optional[bool] = None) -> dict:
    """意圖判斷呼叫的 strict schema（W1b §8.1-1；原型同上）：
    `{action: <5 支動作名＋none>, fields: [{key, value}]}`，每一層 object 都封閉。
    根層與 `action`／`key` 的 description 都列出表單導出的值域（gpt-oss 不讀 enum）。
    值域於呼叫當下由 `FORMS` 導出（第 3 步 #2：只在表單登錄加入的動作也進值域）。"""
    actions = intent_action_domain()
    keys = write_intent_key_domain()
    flag = enum_labels if modifies_flag is None else modifies_flag
    schema = {
        "type": "object",
        "description": write_intent_description(enum_labels=enum_labels),
        "properties": {
            "action": {
                "type": "string", "enum": list(actions),
                "description": "只能是：" + "、".join(actions),
            },
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string", "enum": list(keys),
                            "description": "只能是：" + "、".join(keys),
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
    if flag:
        # 第 3 步 #9g（開關 on）：必填布林欄位；off ⇒ schema 與改動前逐位相同。
        schema["properties"][MODIFIES_SUBMITTED_KEY] = {
            "type": "boolean", "description": MODIFIES_SUBMITTED_RULE,
        }
        schema["required"] = ["action", "fields", MODIFIES_SUBMITTED_KEY]
    return schema


def write_intent_response_format(*, enum_labels: bool = True,
                                 modifies_flag: Optional[bool] = None) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {"name": WRITE_INTENT_SCHEMA_NAME, "strict": True,
                        "schema": write_intent_call_schema(enum_labels=enum_labels,
                                                           modifies_flag=modifies_flag)},
    }


def intent_modifies_submitted(obj: Any) -> bool:
    """意圖判斷呼叫解析出的原始物件 → 布林欄位是否**恰為** `true`（字串 "true"、1 等一律不算）。
    `WriteIntent`（pydantic）忽略多餘鍵，故由原始物件讀。"""
    return isinstance(obj, Mapping) and obj.get(MODIFIES_SUBMITTED_KEY) is True


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
    表內 `payload_type` 轉（`emergency_status` ⇒ int）、其餘（含 `period`：草稿裡已是值閘
    正規化的字串）照原字串。轉換失敗的欄位
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
    form = FORMS.get(action) if isinstance(action, str) and action in _confirm_card.CONFIRM_ACTIONS else None
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


#: 第 3 步 #9g：「最近送出」標記（`agent_state["last_submitted"]`，經 `AgentSession` 讀寫）的封閉三鍵
#: （⛔ token、⛔ payload、⛔ 使用者值）。
LAST_SUBMITTED_KEYS: Final[frozenset] = frozenset({"action", "pending_id", "idle_turns"})
_PENDING_ID_MAX: Final[int] = 64


def new_last_submitted(action: str, pending_id: str) -> dict:
    return {"action": action, "pending_id": pending_id, "idle_turns": 0}


def load_last_submitted(raw: Any) -> Tuple[Optional[dict], bool]:
    """讀回的「最近送出」標記——**一律視為不可信**（同 `load_draft`）。回 `(mark, shape_invalid)`。"""
    if raw is None:
        return None, False
    if not isinstance(raw, dict) or set(raw) != LAST_SUBMITTED_KEYS:
        return None, True
    action = raw.get("action")
    pid = raw.get("pending_id")
    idle = raw.get("idle_turns")
    if (not isinstance(action, str) or action not in FORMS
            or action not in _confirm_card.CONFIRM_ACTIONS
            or not isinstance(pid, str) or not pid or len(pid) > _PENDING_ID_MAX
            or not pid.isascii() or not pid.isalnum()
            or isinstance(idle, bool) or not isinstance(idle, int)
            or not 0 <= idle < DRAFT_IDLE_LIMIT):
        return None, True
    return {"action": action, "pending_id": pid, "idle_turns": idle}, False


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
#: 第 3 步 #9g：「修改剛送出的那一筆」⇒ 程式固定句擋下（無新卡、不建草稿）；標記讀回形狀不合；
#: 標記因無關回合達上限而清掉。
V_SUBMITTED_EDIT_BLOCKED: Final[str] = "write_draft_submitted_edit_blocked"
V_LAST_SUBMITTED_SHAPE_INVALID: Final[str] = "last_submitted_shape_invalid"
V_LAST_SUBMITTED_CLEARED_IDLE: Final[str] = "last_submitted_cleared_idle"
#: 第 3 步 #9b（Q5）：A2 燒卡後新卡沒出成 ⇒ 程式固定句結束回合。
V_REISSUE_NOT_ISSUED: Final[str] = "write_draft_reissue_not_issued"
#: A+ 片 AP-1：模型自己呼叫 `confirm.request`（每次提議記一筆）。
V_WRITE_PROPOSAL: Final[str] = "write_proposal"
#: A+ 片 AP-1：提議這次沒有轉成程式呼叫 ⇒ 回模型封閉工具結果。
V_WRITE_PROPOSAL_NOT_ISSUED: Final[str] = "write_proposal_not_issued"
#: A+ 片 AP-2：綁定卡有效、值相同 ⇒ 程式重出同卡（V2 以它計入程式路徑）。
V_CARD_STILL_VALID: Final[str] = "write_draft_card_still_valid"
#: A+ 片 r3 AP-7 (1)：提議 payload 是 `{action, payload:{…}}` 巢狀形狀、已解開一層合併。
V_WRITE_PROPOSAL_UNWRAPPED: Final[str] = "write_proposal_unwrapped"
#: A+ 片 r3 AP-7 (2)(b)：提議沒有任何值進草稿 ⇒ 程式固定句（無卡）結束回合。
V_WRITE_PROPOSAL_NO_VALUE: Final[str] = "write_proposal_no_value"
#: A+ 片 r3 AP-7 (2)(a)：同上、綁定卡有效且草稿＝卡 ⇒ 程式中性句＋同一張卡（同記 `V_CARD_STILL_VALID`）。
V_WRITE_PROPOSAL_NO_VALUE_CARD: Final[str] = "write_proposal_no_value_card"
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
    "FormField", "FormPrecheck", "Requirement", "WriteForm", "FORMS",
    "REPAIR_CREATE_FORM", "BILL_DUE_EXTEND_FORM",
    "missing_labels", "MISSING_LABEL_VOCAB", "LABEL_ASK_TARGETS", "ask_target_for_missing",
    "missing_label_vocab", "label_ask_targets",
    "WRITE_DRAFT_ENV", "write_draft_enabled_from_env",
    "WRITE_LIFECYCLE_ENV", "write_lifecycle_enabled_from_env", "EDIT_ASK_TEMPLATE",
    "EDIT_ASK_FALLBACK_TEXT", "edit_ask_text", "SUBMITTED_EDIT_TEXT", "REISSUE_NOT_ISSUED_TEXT",
    "MODIFIES_SUBMITTED_KEY", "MODIFIES_SUBMITTED_RULE", "intent_modifies_submitted",
    "LAST_SUBMITTED_KEYS", "new_last_submitted", "load_last_submitted",
    "V_SUBMITTED_EDIT_BLOCKED", "V_LAST_SUBMITTED_SHAPE_INVALID", "V_LAST_SUBMITTED_CLEARED_IDLE",
    "V_REISSUE_NOT_ISSUED",
    "WRITE_PROPOSAL_ENV", "write_proposal_enabled_from_env", "CARD_STILL_VALID_TEXT",
    "CARD_UNCHANGED_TEXT", "V_WRITE_PROPOSAL", "V_WRITE_PROPOSAL_NOT_ISSUED", "V_CARD_STILL_VALID",
    "PROPOSAL_NO_VALUE_CARD_TEXT", "PROPOSAL_NO_VALUE_TEXT", "PROPOSAL_NO_VALUE_FALLBACK_TEXT",
    "proposal_no_value_text", "V_WRITE_PROPOSAL_UNWRAPPED", "V_WRITE_PROPOSAL_NO_VALUE",
    "V_WRITE_PROPOSAL_NO_VALUE_CARD",
    "WRITE_INTENT_KEY_DOMAIN", "INTENT_NONE", "INTENT_ACTION_DOMAIN", "WRITE_INTENT_SCHEMA_NAME",
    "WRITE_INTENT_MAX_COMPLETION_TOKENS", "write_intent_description", "WRITE_INTENT_SYSTEM_PROMPT",
    "write_intent_system_prompt", "enum_code_for_label", "intent_action_domain",
    "write_intent_key_domain",
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
