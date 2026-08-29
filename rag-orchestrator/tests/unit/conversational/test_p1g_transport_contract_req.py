"""unit：P1g——**producer-consumer transport contract**（A03 逼出的 integration false-green）。

## ⚠️ 這一組測試存在的理由

A03 證明：P1f 的 23 條單元測試全過，但 production 上 gate **從來沒看過** applicability 宣告
——因為測試餵的是手寫 `{"generation_metadata": {...}}`，
而 `VendorKnowledgeRetrieverV2` 回傳的列**根本沒有那個欄位**。

```text
nomination ≠ authority｜select=api ≠ capability equivalence
有資料流 ≠ 流到正確語義槽位｜**fixture 有資料 ≠ production 有資料**
```

⇒ 所以本檔的輸入形狀**一律取自 producer 的真實投影**，
⛔ 不得用手寫 dict 當 wiring proof。
"""
import ast
import inspect
import re
import textwrap

import pytest

from services import instance_applicability as ia
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit

#: gate 真正依賴的 transport keys
GATE_REQUIRED_KEYS = {"id", "categories", ia.TRANSPORT_FIELD}


def _producer_row_keys() -> set:
    """從 producer 的**真實 row 組裝程式碼**取出鍵集合（AST，⛔ 非手寫清單）。"""
    # ⚠️ getsource 取方法會帶縮排，必須 dedent 才能 ast.parse（第一版就是這樣紅的）
    tree = ast.parse(textwrap.dedent(
        inspect.getsource(VendorKnowledgeRetrieverV2._format_result)))
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
    return keys


def _producer_source() -> str:
    return inspect.getsource(VendorKnowledgeRetrieverV2)


# ════════════════════════════════════════════════════════════════════
# ① production-shape contract：插頭真的插得到插座
# ════════════════════════════════════════════════════════════════════

def test_producer_row_supplies_every_key_the_gate_needs():
    """**retriever production row keys ⊇ gate required transport keys**。

    ⚠️ 這條就是 A03 缺陷的直接守衛：⛔ 少任何一個鍵即紅。
    """
    keys = _producer_row_keys()
    missing = GATE_REQUIRED_KEYS - keys
    assert not missing, f"producer 未提供 gate 需要的鍵：{missing}"


def test_projection_present_in_every_sql_select():
    """兩處 SQL projection 都必須帶出宣告——⛔ 只改一處會在另一條檢索路徑復發。"""
    src = _producer_source()
    n = len(re.findall(r"instance_applicability'\s*\)?\s*\n?\s*AS knowledge_instance_applicability", src)) \
        or src.count("AS knowledge_instance_applicability")
    assert n >= 2, f"SQL projection 只出現 {n} 次，應為兩處 SELECT 各一"


def test_producer_does_not_normalize_the_value():
    """⛔ retriever **只搬運原值**：值域封閉與 UNKNOWN 語義由契約模組負責。

    ⚠️ 用 AST 精準檢查**那一格的賦值運算式**，⛔ 不做全檔字串比對——
    第一版拿 `"INSTANCE"`／`.lower()` 掃全檔，結果打到自己寫的 SQL 註解
    與 jieba 斷詞（同一個「說明 vs 使用」的錯，本輪第四次）。
    """
    tree = ast.parse(textwrap.dedent(
        inspect.getsource(VendorKnowledgeRetrieverV2._format_result)))
    expr = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == ia.TRANSPORT_FIELD:
                    expr = v
    assert expr is not None, "row 組裝中找不到 transport 欄位"
    # 必須恰為 `row.get("knowledge_instance_applicability")`——無任何包裝／預設值／轉換
    assert isinstance(expr, ast.Call), "transport 欄位不是單純的 row.get(...)"
    assert isinstance(expr.func, ast.Attribute) and expr.func.attr == "get", \
        "transport 欄位被包了其他運算 ⇒ 疑似在 retriever 做 normalization"
    assert len(expr.args) == 1 and not expr.keywords, \
        "row.get 帶了預設值 ⇒ ⛔ retriever 不得代替契約模組決定缺值語義"
    assert isinstance(expr.args[0], ast.Constant) and expr.args[0].value == ia.TRANSPORT_FIELD


# ════════════════════════════════════════════════════════════════════
# ② 三態 transport matrix —— 用 **production shape**（扁平欄位）
# ════════════════════════════════════════════════════════════════════

def _production_row(value):
    """模擬 producer 的扁平投影：⚠️ **沒有** generation_metadata。"""
    row = {k: None for k in _producer_row_keys()}
    row[ia.TRANSPORT_FIELD] = value
    assert "generation_metadata" not in row, "production row 不應有 generation_metadata"
    return row


@pytest.mark.parametrize("declared,expected", [
    ("instance", ia.APPLICABILITY_INSTANCE),
    ("general", ia.APPLICABILITY_GENERAL),
    (None, ia.APPLICABILITY_UNKNOWN),        # ⛔ missing 不得變 general
])
def test_three_state_transport_on_production_shape(declared, expected):
    assert ia.knowledge_instance_applicability(_production_row(declared)) == expected


def test_missing_declaration_never_becomes_general_on_production_shape():
    got = ia.knowledge_instance_applicability(_production_row(None))
    assert got == ia.APPLICABILITY_UNKNOWN
    assert got != ia.APPLICABILITY_GENERAL


# ════════════════════════════════════════════════════════════════════
# ③ mutation：直接打 transport seam
# ════════════════════════════════════════════════════════════════════

def test_mutation_removing_transport_field_breaks_the_contract():
    """把投影欄位從 producer row 拿掉 → contract 必須不成立（⇒ 本檔第一條會紅）。"""
    keys = _producer_row_keys() - {ia.TRANSPORT_FIELD}
    assert GATE_REQUIRED_KEYS - keys, "移除欄位後契約仍成立 ⇒ 這條守衛是空的"


def test_mutation_projection_returning_null_makes_instance_and_general_indistinguishable():
    """投影固定回 null → instance／general 兩種宣告都退化成 UNKNOWN。

    ⚠️ 這證明「key 存在」**不等於**「值有送到」——A03 的 109 筆正是這一格。
    """
    nulled = _production_row(None)
    assert ia.knowledge_instance_applicability(nulled) == ia.APPLICABILITY_UNKNOWN
    real_i = ia.knowledge_instance_applicability(_production_row("instance"))
    real_g = ia.knowledge_instance_applicability(_production_row("general"))
    assert real_i != real_g, "兩種宣告在 production shape 上分不開 ⇒ transport 仍失效"


# ════════════════════════════════════════════════════════════════════
# ④ fixture 紀律：⛔ 不得擁有 production producer 不可能提供的 authority 欄位
# ════════════════════════════════════════════════════════════════════

def test_generation_metadata_is_not_a_production_transport_shape():
    """⚠️ 明文記錄：`generation_metadata` **不在** producer row 內。

    巢狀讀取僅為既有測試與其他來源的**備援**，
    ⛔ 不得再被當作 production wiring 的證明。
    """
    assert "generation_metadata" not in _producer_row_keys()
