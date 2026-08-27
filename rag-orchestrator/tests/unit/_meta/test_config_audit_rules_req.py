"""unit：設定契約掃描器的規則層（knowledge-config-governance 任務 2.1／2.2）。

## 為什麼這檔存在

寫規則的當天，兩條規則就被自己的資料打臉：

```text
C9  立在 `trigger_facet_key` 上 —— 那是 **request 參數**不是欄位 ⇒ 規則永遠不可能正確
C10 只讀 Python registry        —— 漏掉 api_endpoints 表的 dynamic 端點 ⇒ **10 筆裡 8 筆誤報**
```

由此推導出的治理不變量：

> **治理規則本身也必須有 provenance 與 executable coverage。**

⚠️ 一律用**注入的假資料**驗規則，**不讀當下 DB**——否則資料一改測試就紅／綠，
而那紅綠與規則對錯無關。
"""
import pathlib
import re

import pytest

from tools.audit_config import scan

pytestmark = pytest.mark.unit

CONTRACTS = pathlib.Path("/app/database/config_contracts.yaml")
if not CONTRACTS.exists():                     # 本機直跑（非容器）時的備援
    CONTRACTS = pathlib.Path(__file__).resolve().parents[3] / "database" / "config_contracts.yaml"


def _cfg(kid, key, **md):
    md.setdefault("key", key)
    return {"id": kid, "md": md, "target_user": "", "answer": ""}


def _rules(findings):
    return sorted(f["rule"] for f in findings)


# ════════ 合法變體不得被判違規（誤報＝缺陷，R5.1）════════

@pytest.mark.req("knowledge-config-governance:5.1")
def test_role_routed_config_is_not_a_violation():
    """`presales` 那種 role-routed 面向：**無 topic_scope、無 endpoint**，是合法變體。

    ⚠️ 用一條扁平的「全部必填」會把它判成錯——誤報會讓人學會忽略稽核，比沒有稽核更糟。
    """
    configs = [_cfg(1, "presales", persona_role="prospect",
                    grounding_scope={"mode": "b2b", "target_user": "prospect"})]
    assert scan(configs, {"jgb_bills"}) == []


@pytest.mark.req("knowledge-config-governance:5.1")
def test_dynamic_endpoint_from_api_endpoints_table_is_not_a_violation():
    """`lookup_generic` 這類 **dynamic 端點**存在於 api_endpoints 表、不在 Python registry。

    合法 endpoint ＝ **registry ∪ api_endpoints**；只讀其一就是 C10 初版的 8 筆誤報。
    """
    endpoints = {"jgb_bills"} | {"lookup_generic", "demo_form", "trial_form"}
    assert scan([], endpoints, form_endpoints=[("billing_address_form_v2", "lookup_generic")]) == []


@pytest.mark.req("knowledge-config-governance:5.1")
def test_endpoint_missing_from_both_sources_is_caught():
    """真違規必須被抓到——否則上面兩條「不誤報」可以用「永遠不報」來作弊。"""
    out = scan([], {"jgb_bills"}, form_endpoints=[("billing_inquiry_guest", "billing_inquiry")])
    assert _rules(out) == ["C10"] and out[0]["level"] == "L1"


# ════════ 逐條規則 ════════

@pytest.mark.req("knowledge-config-governance:2.1")
def test_c1_row_without_config_or_target_user():
    out = scan([{"id": 9, "md": None, "target_user": "", "answer": ""}], set())
    assert _rules(out) == ["C1"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c1_row_with_only_target_user_is_ok():
    """只有 target_user 也能組出設定（loader 用它當 persona_role）——不得判違規。"""
    assert scan([{"id": 9, "md": None, "target_user": "prospect", "answer": ""}], set()) == []


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c2_duplicate_key():
    out = scan([_cfg(1, "dup"), _cfg(2, "dup")], set())
    assert _rules(out) == ["C2"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c3_category_mode_without_category():
    out = scan([_cfg(1, "a", topic_scope={"mode": "category", "category": "  "})], set())
    assert _rules(out) == ["C3"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c4_duplicate_category():
    cs = [_cfg(1, "a", topic_scope={"mode": "category", "category": "帳單異常"}),
          _cfg(2, "b", topic_scope={"mode": "category", "category": "帳單異常"})]
    assert _rules(scan(cs, set())) == ["C4"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c5_delegate_target_not_in_registry():
    cs = [_cfg(1, "a", responsibility={"delegates": [{"target": "ghost", "when": "x"}]},
               answer_rules="delegate_facet_key")]
    assert _rules(scan(cs, set())) == ["C5"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c6_delegate_without_when():
    cs = [_cfg(1, "a", responsibility={"delegates": [{"target": "b"}]},
               answer_rules="delegate_facet_key"),
          _cfg(2, "b")]
    assert _rules(scan(cs, set())) == ["C6"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c7_delegates_declared_but_output_shape_missing():
    """v3 實證：模型只產出 persona **宣告形狀內**的欄位——規則沒宣告該鍵，委派永不發生。"""
    cs = [_cfg(1, "a", responsibility={"delegates": [{"target": "b", "when": "x"}]}), _cfg(2, "b")]
    out = scan(cs, set())
    assert _rules(out) == ["C7"] and out[0]["level"] == "L2"


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c7_satisfied_by_answer_text_not_only_answer_rules():
    """宣告可能寫在 persona 規則的 answer 全文裡（migration 第 (2) 段就是改那裡）。"""
    cs = [{"id": 1, "target_user": "", "answer": "…輸出 JSON…delegate_facet_key…",
           "md": {"key": "a", "responsibility": {"delegates": [{"target": "b", "when": "x"}]}}},
          _cfg(2, "b")]
    assert scan(cs, set()) == []


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c8_grounding_endpoint_unknown():
    cs = [_cfg(1, "a", grounding_scope={"endpoint": "jgb_ghost"})]
    assert _rules(scan(cs, {"jgb_bills"})) == ["C8"]


@pytest.mark.req("knowledge-config-governance:2.1")
def test_c9_knowledge_endpoint_unknown():
    assert _rules(scan([], {"jgb_bills"}, kb_endpoints=[("4321", "gone")])) == ["C9"]


# ════════ 2.2 契約檔 ↔ 掃描器一致性 ════════

@pytest.mark.req("knowledge-config-governance:1.1")
def test_every_contract_rule_is_implemented_or_declared_not_implemented():
    """**防的是**：契約寫了一條漂亮的規則，但沒有人在跑它。

    ⚠️ 刻意用 regex 解析而非 import yaml——稽核與其測試都不得引入新相依（R2.3 精神）。
    """
    text = CONTRACTS.read_text(encoding="utf-8")
    declared = set(re.findall(r"^\s*- id:\s*(\w+)", text, re.M))
    src = pathlib.Path(scan.__code__.co_filename).read_text(encoding="utf-8")
    implemented = set(re.findall(r'check\(findings,\s*"L\d",\s*"(\w+)"', src))
    not_impl = set(re.findall(r"^\s*disposition:.*$", text, re.M))

    # L3 依定義不由掃描器判定（R2.2／R3.3）——契約需明寫 disposition
    l3 = set(re.findall(r"- id:\s*(\w+)\s*\n\s*level:\s*L3", text))
    assert l3, "契約中應有 L3 規則（語義歸屬只提案）——找不到代表解析壞了"
    assert len(not_impl) >= len(l3), "每條 L3 規則都必須寫明 disposition（只提案，人裁）"

    missing = declared - implemented - l3
    assert not missing, f"契約宣告了但掃描器沒實作：{sorted(missing)}——看起來受治理，實際沒人在驗"
    extra = implemented - declared
    assert not extra, f"掃描器在跑但契約沒宣告：{sorted(extra)}——規則缺 provenance"
