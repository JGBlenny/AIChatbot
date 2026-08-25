"""unit：resolver hop 的 raw output attribution 能否分辨 A/B/C（零成本、不打模型）。

⚠️ 本組**驗的是證據工具**：先證明它分得出來，下一輪付費執行的歸因才有意義。
兩輪 gated validation 都只看到 `delegate_to=None`，而那底下壓著三種不同的問題。
"""
import pytest

from tests.support.resolver_capture import (
    DROP_REASONS,
    build_hop_evidence,
    classify_delegate_drop,
    delegate_related_keys,
)

pytestmark = pytest.mark.unit

ALLOWED = ["billing_anomaly"]


def _norm(scope="switch", delegate=None):
    out = {"action": "ask", "next_question": "q", "scope": scope}
    if delegate:
        out["delegate_facet_key"] = delegate
    return out


@pytest.mark.req("face-exit-before-grounding:1")
def test_A_missing_field():
    """A：模型根本沒輸出 delegate 欄位 → prompt／output contract 不足。"""
    raw = {"content": '{"action":"ask","next_question":"q","scope":"switch","face":""}'}
    ev = classify_delegate_drop(raw, ALLOWED, _norm())
    assert ev["normalization_drop_reason"] == "missing"
    assert ev["raw_scope"] == "switch" and ev["normalized_delegate_facet_key"] is None


@pytest.mark.req("face-exit-before-grounding:1")
def test_B_wrong_key():
    """B：值放到別的鍵（如 face）→ schema／parser contract mismatch。"""
    raw = {"content": '{"action":"ask","scope":"switch","face":"billing_anomaly"}'}
    ev = classify_delegate_drop(raw, ALLOWED, _norm())
    assert ev["normalization_drop_reason"] == "wrong_key"
    assert ev["misplaced_in"] == ["face"] and ev["dropped_value"] == "billing_anomaly"


@pytest.mark.req("face-exit-before-grounding:1")
def test_C_not_allowed():
    """C：有 delegation intent，但值不在白名單 → 被正規化丟掉。"""
    raw = {"content": '{"action":"ask","scope":"switch","delegate_facet_key":"帳單異常"}'}
    ev = classify_delegate_drop(raw, ALLOWED, _norm())
    assert ev["normalization_drop_reason"] == "not_allowed"
    assert ev["dropped_value"] == "帳單異常"


@pytest.mark.req("face-exit-before-grounding:1")
def test_not_string_and_scope_not_switch():
    raw_ns = {"content": '{"action":"ask","scope":"switch","delegate_facet_key":123}'}
    assert classify_delegate_drop(raw_ns, ALLOWED, _norm())["normalization_drop_reason"] \
        == "not_string"
    raw_stay = {"content": '{"action":"ask","scope":"stay","delegate_facet_key":"billing_anomaly"}'}
    assert classify_delegate_drop(raw_stay, ALLOWED, _norm(scope="stay"))[
        "normalization_drop_reason"] == "scope_not_switch"


@pytest.mark.req("face-exit-before-grounding:1")
def test_kept_when_normalization_preserved_it():
    raw = {"content": '{"action":"ask","scope":"switch","delegate_facet_key":"billing_anomaly"}'}
    ev = classify_delegate_drop(raw, ALLOWED, _norm(delegate="billing_anomaly"))
    assert ev["normalization_drop_reason"] == "kept"


@pytest.mark.req("face-exit-before-grounding:1")
def test_unparsable_payload_is_missing_not_crash():
    ev = classify_delegate_drop({"content": "not json at all"}, ALLOWED, _norm())
    assert ev["normalization_drop_reason"] == "missing" and ev["raw_model_payload"] == {}


@pytest.mark.req("face-exit-before-grounding:1")
def test_hop_evidence_has_all_eight_fields():
    raw = {"content": '{"action":"ask","scope":"switch"}'}
    ev = build_hop_evidence("bill_diagnosis", raw, ALLOWED, _norm())
    for field in ("candidate_face", "raw_model_payload", "raw_scope",
                  "raw_delegate_related_keys", "normalized_scope",
                  "normalized_delegate_facet_key", "allowed_delegates",
                  "normalization_drop_reason"):
        assert field in ev, f"缺欄位 {field}"
    assert ev["normalization_drop_reason"] in DROP_REASONS


@pytest.mark.req("face-exit-before-grounding:1")
def test_delegate_related_keys_lists_candidates_for_human_review():
    payload = {"scope": "switch", "face": "x", "delegate_to": "y", "next_question": "q"}
    assert set(delegate_related_keys(payload)) >= {"face", "delegate_to"}
    assert "next_question" not in delegate_related_keys(payload)
