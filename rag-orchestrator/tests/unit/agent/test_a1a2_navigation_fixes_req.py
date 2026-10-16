"""unit：2026-10-15 上線後 A1／A2 修正。

A1（`issues-after-golive-20261015.md`）：目錄與粗目細目清單**印出 `kb.get` 可直接使用的完整 id**
（`outline:<id>`）。正式機實測：只印裸 id 時，模型把資料段標記尾端的 `§<n>` 當 id 呼叫
`kb.get("outline:32")`，或照抄裸細目 id 漏前綴，重試到預算用完轉人。

A2：上一回合追問名稱（`last_ask_target` ∈ 物件／社區／地址）時，使用者這句若是 7～30 字、無句讀的一串名稱，也拿去
比對物件（正式機：「學生獨立套房可租補」被當成新的知識題、或被拆成物件＋描述）。
"""
from __future__ import annotations

import pytest

from services.agent.canon.canon_assembler import (
    build_canon_toc,
    register_canon,
    reset_canon_registry,
    resolve_canon_section,
)
from services.agent.canon.canon_parser import parse_canon_text
from services.agent.identity import Identity
from services.agent.outline import make_outline_resolver
from services.agent.runtime import _PRE_LOOKUP_NAME_ASK_TARGETS, _pre_lookup_trigger
from services.agent.tools.kb import kb_get

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

_CANON = """---
audience: prospect
version: 2026-10-15.a1-test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
### 標題X {#prospect/A/visible-fine}
- sources: [kb:1]
- target_user: [prospect]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-10-15}
- instance_applicability: general
內容X
"""
_FINE = "prospect/A/visible-fine"
_ID = Identity(vendor_id=1, target_user="prospect", mode="b2b")


@pytest.fixture(autouse=True)
def _reset():
    reset_canon_registry()
    yield
    reset_canon_registry()


# ── A1 ──────────────────────────────────────────────────────────────────────
def test_toc_lines_start_with_the_full_kb_get_id():
    doc = parse_canon_text(_CANON)
    toc = build_canon_toc(doc, _ID, vendor_business_types=frozenset())
    lines = toc.text.splitlines()
    assert lines == ["outline:A｜合成粗目｜1"]


def test_coarse_listing_lines_start_with_the_full_kb_get_id():
    doc = parse_canon_text(_CANON)
    res = resolve_canon_section(doc, _ID, "outline:A", vendor_business_types=frozenset())
    assert res.ok is True
    assert res.text_for_model.splitlines() == [f"outline:{_FINE}｜標題X"]


async def test_ids_copied_verbatim_from_toc_and_listing_open_the_sections():
    """模型照抄目錄行首 → 粗目清單行首 → 讀到細目內容（兩跳都成功）。"""
    doc = parse_canon_text(_CANON)
    register_canon(doc)
    resolver = make_outline_resolver()
    toc = await kb_get(_ID, {"kb_id": "outline:toc"}, db_pool=None, outline_resolver=resolver)
    coarse_id = toc.text_for_model.splitlines()[0].split("｜")[0]
    listing = await kb_get(_ID, {"kb_id": coarse_id}, db_pool=None, outline_resolver=resolver)
    fine_id = listing.text_for_model.splitlines()[0].split("｜")[0]
    fine = await kb_get(_ID, {"kb_id": fine_id}, db_pool=None, outline_resolver=resolver)
    assert (toc.ok, listing.ok, fine.ok) == (True, True, True)
    assert fine.text_for_model == "內容X" and fine.provenance[0].citable is True


# ── A2 ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("message,after_q,expected", [
    ("學生獨立套房可租補", True, ("keyword", "學生獨立套房可租補")),
    ("學生獨立套房可租補", False, None),                      # 沒追問 ⇒ 維持舊規則（>6 字不觸發）
    ("捷仕堂 溫馨雅房可租補", True, ("keyword", "捷仕堂 溫馨雅房可租補")),  # 名稱內含空白
    ("【智慧電錶】台北大安-景觀雅房7C", True, ("keyword", "智慧電錶】台北大安-景觀雅房7C")),  # 頭尾標點照既有規則去掉
    ("冷氣不冷，麻煩盡快處理", True, None),                   # 句中有逗號 ⇒ 是句子不是名稱
    ("帳單為什麼發不出去？", True, ("keyword", "帳單為什麼發不出去")),  # 尾端問號被去掉後仍是一串字（查無不注入）
    ("一" * 31, True, None),                                 # 超過 30 字
    ("信仰", False, ("keyword", "信仰")),                      # 舊的短名詞規則不變
])
def test_pre_lookup_trigger_after_name_ask(message, after_q, expected):
    assert _pre_lookup_trigger(message, after_name_ask=after_q) == expected


def test_name_ask_targets_are_closed_name_kinds():
    """只認名稱類追問；問描述、急迫、編號時不擴大比對（避免把描述句拿去查物件）。"""
    from services.agent.output_schema import ASK_TARGETS
    assert _PRE_LOOKUP_NAME_ASK_TARGETS == {"estate", "community", "address"}
    assert _PRE_LOOKUP_NAME_ASK_TARGETS <= set(ASK_TARGETS)


# ── A3：驗證關「轉人字眼」只擋引文沒有支撐的 ──────────────────────────────────
from types import SimpleNamespace  # noqa: E402

from services.agent.provenance_units import ResolvedRef  # noqa: E402
from services.agent.verifier import _uncovered_handoff_mention  # noqa: E402

_QUOTE = "逾期未繳的帳單，系統會自動寄送催繳通知；此操作需由 JGB 客服協助，業者端沒有自助重發的介面。"


def _out(*texts):
    sents = [SimpleNamespace(text=t, refs=["r"]) for t in texts]
    return SimpleNamespace(answer="".join(texts), sentences=sents)


def test_a3_handoff_word_backed_by_citable_quote_is_not_flagged():
    out = _out("可以，需由 JGB 客服協助代發，業者端沒有自助重發的介面。")
    resolved = {(0, 0): ResolvedRef(quote=_QUOTE, citable=True, source="outline:x")}
    assert _uncovered_handoff_mention(out, resolved) is False


def test_a3_handoff_word_not_in_quote_is_flagged():
    out = _out("帳單會自動寄出，有問題請找客服。")
    resolved = {(0, 0): ResolvedRef(quote="逾期未繳的帳單，系統會自動寄送催繳通知。", citable=True, source="outline:x")}
    assert _uncovered_handoff_mention(out, resolved) is True


def test_a3_non_citable_quote_does_not_back_the_word():
    out = _out("需由 JGB 客服協助代發。")
    resolved = {(0, 0): ResolvedRef(quote=_QUOTE, citable=False, source="outline:toc")}
    assert _uncovered_handoff_mention(out, resolved) is True


def test_a3_word_only_in_answer_without_sentences_is_flagged():
    out = SimpleNamespace(answer="請洽客服。", sentences=[])
    assert _uncovered_handoff_mention(out, {}) is True


def test_a3_quote_of_another_sentence_does_not_back_the_word():
    out = _out("系統會自動寄送催繳通知。", "其他問題請找客服。")
    resolved = {(0, 0): ResolvedRef(quote=_QUOTE, citable=True, source="outline:x")}
    assert _uncovered_handoff_mention(out, resolved) is True


def test_a3_no_handoff_word_is_not_flagged():
    assert _uncovered_handoff_mention(_out("系統會自動寄送催繳通知。"), {}) is False


# ── A9／缺描述：修繕單缺物件或問題描述 ⇒ 程式追問（⛔ 出卡）─────────────────────
from services.agent.tools import confirm as C  # noqa: E402


@pytest.mark.parametrize("payload,missing", [
    ({"action": "repair_create"}, ["物件", "問題描述"]),
    ({"action": "repair_create", "estate_name": "學生獨立套房可租補"}, ["問題描述"]),
    ({"action": "repair_create", "estate_name": "學生獨立套房可租補", "description": "  "}, ["問題描述"]),
    ({"action": "repair_create", "description": "冷氣不冷"}, ["物件"]),
])
async def test_repair_missing_fields_return_ask_not_card(payload, missing):
    import json
    ident = Identity(vendor_id=4, target_user="property_manager", mode="b2b",
                     role_id="20151", user_id="12291", api_key_id=1)
    res = await C.confirm_request(ident, {"summary": "報修", "payload": json.dumps(payload, ensure_ascii=False)},
                                  db_pool=None)
    assert (res.ok, res.error) == (False, "INVALID_INPUT")
    assert res.data["missing_fields"] == missing
    assert "card" not in (res.data or {})
    text = C.missing_fields_ask_text(res)
    assert text is not None and all(lb in text for lb in missing)


# ── 修繕單細項：jgb2 POST /repairs 規定 item_id 必填 ───────────────────────────
from services.agent.tools import action as _action  # noqa: E402

_TREE = [
    {"id": 6, "name": "家電維修", "items": [{"id": 61, "name": "冷氣機"}, {"id": 62, "name": "電視"}]},
    {"id": 11, "name": "其他", "items": [{"id": 111, "name": "自定義"}]},
    {"id": 12, "name": "空大類", "items": []},
]


def test_single_leaf_parent_gets_its_only_item():
    assert _action._single_leaf_item_id(_TREE, 11) == 111


def test_multi_leaf_parent_is_not_guessed():
    assert _action._single_leaf_item_id(_TREE, 6) is None      # 正對照：多個細項 ⛔ 代選
    assert _action._single_leaf_item_id(_TREE, 12) is None     # 沒有細項
    assert _action._single_leaf_item_id(_TREE, 999) is None    # 不存在的大類
