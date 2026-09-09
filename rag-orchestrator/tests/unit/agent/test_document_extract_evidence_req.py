"""unit：文件擷取的**證據閘**（line-bot #5／Plan 第六批單元 C）。

病灶：同一張水電費單擷取五次，日期五種答案——文件上其實沒有開立日期，模型在猜。
處置面＝兩半：① 提示詞只加**定義**（`DOCUMENT_SYSTEM_PROMPT` 最後一句：附片段、
片段找不到就留 null）；② 程式端 `apply_evidence_gate` **覆核**——片段空、或片段
比對不上值 ⇒ 該欄變 `None`，⛔ 不只靠提示詞那句話（提示詞管不了模型會不會照做）。

⚠️ `evidence` 走 `fields` 的**同層姊妹物件**（不混進 `fields` 內部）——
`test_document_turn_req.py` 直接拿 `fields` 的鍵集／行數對照組句結果與 schema
形狀，混進去會讓那些既有正對照組全部跟著漂；本檔只管 `evidence` 這條新路徑，
⛔ 不改動、不重跑既有檔覆蓋的斷言。
"""
from __future__ import annotations

import pytest

from services.agent import document_extract as dx

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R10"


# ═══════════════════════════════════════════════════════════════════
# 素材
# ═══════════════════════════════════════════════════════════════════
def _bill_fields(**over) -> dict:
    base = {
        "issuer": "合成物業管理股份有限公司",
        "payer": "王小明",
        "amount": 19520,
        "currency": "TWD",
        "date": "2026-08-15",
        "items": [{"name": "租金", "amount": 18000}],
        "payment_method": "轉帳",
        "reference_no": "R2026081500042",
    }
    base.update(over)
    return base


def _bill_result(*, evidence=None, **field_over) -> dict:
    """已過 `validate_extraction` 的形狀（含新增的 `evidence` 鍵）。"""
    return {
        "kind": "bill_receipt",
        "page_count": 1,
        "unreadable": False,
        "uncertain": [],
        "fields": _bill_fields(**field_over),
        "evidence": evidence,
    }


def _full_evidence(**over) -> dict:
    base = {
        "issuer": "合成物業管理股份有限公司",
        "payer": "王小明",
        "amount": "合計 19,520",
        "currency": "TWD",
        "date": "帳單日期 2026-08-15",
        "items": [{"name": "租金", "amount": "合計 19,520"}],
        "payment_method": "轉帳",
        "reference_no": "R2026081500042",
    }
    base.update(over)
    return base


# ═══════════════════════════════════════════════════════════════════
# A. schema：每個值欄配一個證據欄，逐表自動產生
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_schema_pairs_every_value_field_with_its_own_evidence_field():
    schema = dx.build_json_schema()
    assert schema["additionalProperties"] is False
    assert "evidence" in schema["required"]
    fields = schema["properties"]["fields"]
    evidence = schema["properties"]["evidence"]

    # 姊妹物件：鍵集與 `fields` 一一對應（⛔ 不混進 `fields` 內部）
    assert evidence["additionalProperties"] is False
    assert evidence["required"] == sorted(evidence["properties"])
    assert set(evidence["properties"]) == set(fields["properties"])
    # `fields` 自己的鍵集／行數不受影響（既有測試依賴這件事）
    assert "evidence" not in fields["properties"]

    # 一般欄：≤40 字、可為 null
    issuer_evidence = evidence["properties"]["issuer"]
    assert issuer_evidence["maxLength"] == 40
    assert "null" in issuer_evidence["type"]

    # string_list（`special_terms`）：索引對齊的片段陣列，逐元素配證據
    special_terms_evidence = evidence["properties"]["special_terms"]
    assert special_terms_evidence["maxItems"] == 8
    assert special_terms_evidence["items"]["maxLength"] == 40

    # object_list（`items`）：逐列一個證據物件，鍵＝該列子欄位名
    items_evidence = evidence["properties"]["items"]
    assert items_evidence["maxItems"] == 10
    row_schema = items_evidence["items"]
    assert row_schema["additionalProperties"] is False
    assert set(row_schema["properties"]) == {"name", "amount"}


@pytest.mark.req(_REQ)
def test_output_token_limit_grows_when_evidence_is_counted_in():
    # 正對照：加了證據預算之後上限比只算值欄位時大（W9-8／點 4）
    value_only = sum(
        dx._spec_char_budget(s) for s in dx._MERGED_FIELDS.values()
    ) * 2 + 256
    assert dx.output_token_limit() > value_only


# ═══════════════════════════════════════════════════════════════════
# B. 新舊形狀共存：沒有 `evidence` 鍵 ⇒ 證據閘整支不動
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_gate_is_a_noop_without_any_evidence_key():
    """釘住「缺 evidence 鍵＝證據閘不啟用」這個判定——舊擷取器／既有測試的假
    擷取器結果沒有這個概念，⛔ 不能被 gate 誤判成「證據給了但是空」而整批 null。
    """
    result = _bill_result(evidence=None)
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"] == result["fields"]
    assert gated["uncertain"] == []
    # 正對照：`validate_extraction` 面對沒有 `evidence` 鍵的原始輸出，回的正是
    # `evidence: None`（不是空 dict、不是缺鍵）——這是上面那個判定的來源。
    raw = {
        "kind": "bill_receipt",
        "unreadable": False,
        "uncertain": [],
        "fields": _bill_fields(),
    }
    assert dx.validate_extraction(raw)["evidence"] is None


@pytest.mark.req(_REQ)
def test_gate_is_also_a_noop_for_empty_evidence_dict():
    # `evidence: {}`（型別對但沒有任何內容）同樣視為未啟用——不是「每一欄都
    # 比對不到」，是擷取器根本沒有回傳這個物件。
    result = _bill_result(evidence={})
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"] == result["fields"]


# ═══════════════════════════════════════════════════════════════════
# C. 證據閘啟用後：逐欄比對
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_gate_nulls_the_field_when_evidence_is_empty():
    result = _bill_result(evidence=_full_evidence(date=""))
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"]["date"] is None
    assert "date" in gated["uncertain"]
    # 正對照：同一份結果，別的欄位（片段沒問題）不受影響
    assert gated["fields"]["payer"] == "王小明"


@pytest.mark.req(_REQ)
def test_gate_keeps_date_when_evidence_contains_it():
    result = _bill_result(evidence=_full_evidence(date="帳單日期 2026-08-15"))
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"]["date"] == "2026-08-15"
    assert "date" not in gated["uncertain"]


@pytest.mark.req(_REQ)
def test_gate_keeps_amount_when_evidence_digits_match():
    result = _bill_result(evidence=_full_evidence(amount="合計 19,520"))
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"]["amount"] == 19520


@pytest.mark.req(_REQ)
def test_gate_nulls_amount_when_evidence_digits_mismatch():
    # 正反對照組：evidence 片段沒變（"合計 19,520"），改的是**值**（18000）——
    # 兩邊數字串對不上 ⇒ null，⛔ 不是「evidence 只要非空就過」。
    result = _bill_result(amount=18000, evidence=_full_evidence(amount="合計 19,520"))
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"]["amount"] is None
    assert "amount" in gated["uncertain"]


@pytest.mark.req(_REQ)
def test_gate_string_field_keeps_or_nulls_by_substring():
    ok = _bill_result(evidence=_full_evidence(issuer="合成物業管理股份有限公司 客服專線"))
    assert dx.apply_evidence_gate(ok)["fields"]["issuer"] == "合成物業管理股份有限公司"

    bad = _bill_result(evidence=_full_evidence(issuer="與開立單位無關的另一段文字"))
    gated_bad = dx.apply_evidence_gate(bad)
    assert gated_bad["fields"]["issuer"] is None
    assert "issuer" in gated_bad["uncertain"]


@pytest.mark.req(_REQ)
def test_gate_object_list_checks_each_row_element_independently():
    # `items` 逐列各自的每個子欄位獨立比對——一列裡 `name` 對得上、`amount`
    # 對不上 ⇒ 只有 `amount` 變 null，`name` 不受牽連（⛔ 不是整列或整欄清空）。
    result = _bill_result(
        items=[{"name": "租金", "amount": 18000}],
        evidence=_full_evidence(items=[{"name": "租金", "amount": "水費 500"}]),
    )
    gated = dx.apply_evidence_gate(result)
    row = gated["fields"]["items"][0]
    assert row["name"] == "租金"
    assert row["amount"] is None
    assert "items" in gated["uncertain"]

    # 正對照：兩個子欄位的片段都對得上 ⇒ 整列保留、`items` 不進 uncertain
    ok_result = _bill_result(
        items=[{"name": "租金", "amount": 18000}],
        evidence=_full_evidence(items=[{"name": "項目：租金", "amount": "合計 18,000"}]),
    )
    ok_gated = dx.apply_evidence_gate(ok_result)
    assert ok_gated["fields"]["items"][0] == {"name": "租金", "amount": 18000}
    assert "items" not in ok_gated["uncertain"]


@pytest.mark.req(_REQ)
def test_gate_string_list_drops_only_the_unmatched_element():
    result = {
        "kind": "contract",
        "page_count": 1,
        "unreadable": False,
        "uncertain": [],
        "fields": {
            "lessor": "甲", "lessee": "乙", "property_address": None,
            "term_start": None, "term_end": None, "rent": None,
            "rent_cycle": None, "deposit": None, "payment_day": None,
            "special_terms": ["禁止轉租", "禁止飼養寵物"],
            "signed": None,
        },
        "evidence": {
            "special_terms": ["特約：禁止轉租", None],  # 第二段沒有證據
        },
    }
    gated = dx.apply_evidence_gate(result)
    assert gated["fields"]["special_terms"] == ["禁止轉租"]
    assert "special_terms" in gated["uncertain"]


# ═══════════════════════════════════════════════════════════════════
# D. 證據**不**進 `build_document_facts`（W9-2 紀律延伸；build_document_facts
#    本身不變，這裡只是釘住「evidence 鍵不影響組句」這個既有不變量）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_evidence_never_leaks_into_facts():
    # ⚠️ 「evidence 內容含值」是通過閘門的**必要條件**（值本身就是 evidence 的
    #    子字串），所以不能拿值字串本身去測「有沒有漏進 facts」——那必然為真、
    #    測不出任何事。要測的是 evidence 裡**值以外**的部分（片段的裝飾文字）
    #    有沒有跟著漏進去。
    result = _bill_result(
        evidence=_full_evidence(
            date="帳單日期標示為 2026-08-15 敬請留意",
            issuer="開立單位欄位寫著 合成物業管理股份有限公司 業者專線",
        )
    )
    gated = dx.apply_evidence_gate(result)
    facts = dx.build_document_facts(gated)
    # 兩欄都因為比對得上而**保留原值**——證明 gate 沒把它們 null 掉
    assert gated["fields"]["date"] == "2026-08-15"
    assert gated["fields"]["issuer"] == "合成物業管理股份有限公司"
    # 但 evidence 片段裡值以外的裝飾文字，⛔ 不得出現在 facts
    assert "帳單日期標示為" not in facts
    assert "敬請留意" not in facts
    assert "開立單位欄位寫著" not in facts
    assert "業者專線" not in facts
