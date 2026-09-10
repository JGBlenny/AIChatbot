"""unit：W9 情境①收尾——⑤ 導流白名單（`ROUTE_NOT_ALLOWED`）改為**受眾範圍制**
（規則鍵 `route_check_audiences`，語義與 U3 的 `sensitive_patterns_audiences` 相同）。

病灶：合成收據歸納的「交易序號為 R2026081500042」被 `_PHONE_RE` 的第二支
`0\\d{1,2}[-\\s]?\\d{3,4}[-\\s]?\\d{4}` 咬到（`081500042`），兩次改寫皆拒 ⇒ 預算耗盡轉人。
這條規則是售前 CTA 守門，對 pm 引資料段的編號沒有意義。

守的事：鍵真的被載入；pm 放行／prospect 照擋／缺值照擋／未知照擋（fail-closed）；
URL 分支同受眾語義；缺鍵＝全受眾＝舊行為（正對照）。一律用出貨規則檔。
"""
from __future__ import annotations

import json

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier

from tests.unit.agent.test_verifier_req import _RULES_PATH

_REQ = "knowledge-outline-and-intent-architecture:W9-scenario-1"
pytestmark = [pytest.mark.unit, pytest.mark.req(_REQ)]

_PHONEISH = "交易序號為 R2026081500042。"
_URLISH = "明細見 https://example.invalid/receipt/1 。"


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


def _verdict(rules: VerifierRules, sentence: str, audience):
    out = AgentOutput.model_validate({
        "kind": "answer",
        "sentences": [{"text": sentence, "kind": "fact",
                       "refs": [f"[{_FIXTURE_NONCE}:t1:kb:9102§0]"]}],
        "fact_class": "other", "handoff_reason": None,
    })
    tool_results = {"t1": ToolResult(ok=True, data=None, text_for_model="",
                                     provenance=[__import__("services.agent.runtime", fromlist=["Provenance"]).Provenance(
                                         source="kb:9102", text=sentence, citable=True)])}  # 引文＝句子本身：覆蓋率必過，只量 ⑤
    resolved, errors = resolve_refs(out, tool_results, _FIXTURE_NONCE)
    return OutputVerifier(rules).verify(out, tool_results, "這張憑證幫我歸納。", None,
                                        resolved=resolved, resolve_errors=errors, audience=audience)


def test_key_is_loaded_from_file(rules):
    assert rules.route_check_audiences == ["prospect"]
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    # 單元 E（第六批）：規則檔多一張 `document_turn_forbid_terms` ⇒ 版本升 1.6.0。
    assert raw["route_check_audiences"] == ["prospect"] and raw["version"] == "1.6.2"


@pytest.mark.parametrize("sentence", [_PHONEISH, _URLISH])
def test_pm_is_not_blocked_by_route_check(rules, sentence):
    assert _verdict(rules, sentence, "property_manager").ok is True


@pytest.mark.parametrize("audience", ["prospect", None, "system_admin", "propspect"])
@pytest.mark.parametrize("sentence", [_PHONEISH, _URLISH])
def test_prospect_missing_and_unknown_are_still_blocked(rules, sentence, audience):
    v = _verdict(rules, sentence, audience)
    assert v.ok is False and v.reason == "ROUTE_NOT_ALLOWED", v


def test_missing_key_means_all_audiences_old_behaviour(rules):
    old = rules.model_copy(update={"route_check_audiences": None})
    v = _verdict(old, _PHONEISH, "property_manager")
    assert v.ok is False and v.reason == "ROUTE_NOT_ALLOWED"


def test_neutral_sentence_passes_for_everyone(rules):
    for aud in ("property_manager", "prospect", None):
        out = AgentOutput.model_validate({
            "kind": "answer",
            "sentences": [{"text": "付款方式為轉帳。", "kind": "fact",
                           "refs": [f"[{_FIXTURE_NONCE}:t1:kb:9102§0]"]}],
            "fact_class": "other", "handoff_reason": None,
        })
        from services.agent.runtime import Provenance
        tool_results = {"t1": ToolResult(ok=True, data=None, text_for_model="",
                                         provenance=[Provenance(source="kb:9102", text="付款方式：轉帳。", citable=True)])}
        resolved, errors = resolve_refs(out, tool_results, _FIXTURE_NONCE)
        assert OutputVerifier(rules).verify(out, tool_results, "x", None, resolved=resolved,
                                            resolve_errors=errors, audience=aud).ok is True
