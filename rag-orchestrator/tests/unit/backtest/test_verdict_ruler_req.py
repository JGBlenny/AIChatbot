"""unit：verdict 量尺（任務 0.6｜R1.3、R1.3.1–3.4）。

契約：
- 路由類別**唯一來源＝決策快照的 `routing_verdict`**，不得由答案文字反推（R1.3）；
- 比較單位＝`(routing_verdict, grounded, answer_verdict)` 複合鍵（R1.3.1）；
- verdict 值域與 design C1 單一枚舉一致，不一致即失敗（R1.3.2）；
- **換尺鐵則（R1.3.3）**：新尺須在已知病灶上判出既有不一致，看不見即不合格；
- 舊檔文字判定須標 `legacy_text`，不得與 verdict 尺混計（R1.3.4）。
"""
import json
import os

import pytest

from scripts.backtest import decision_replay as dr

pytestmark = pytest.mark.unit


# ── R1.3.2：值域與 design C1 枚舉一致 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_verdict_domain_matches_design_enum():
    spec = os.path.join(dr.REPO, ".kiro", "specs", "retrieval-decision-layer", "design.md")
    with open(spec, encoding="utf-8") as f:
        src = f.read()
    for v in dr.ROUTING_VERDICTS:
        assert f'"{v}"' in src, f"值 {v!r} 不在 design.md 的 C1 枚舉——兩套詞彙又分岔了"
    assert dr.verdict_domain_check(src) is True


# ── R1.3：來源是快照，不是文字 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_turn_result_reads_verdict_from_snapshot():
    snap = {"routing_verdict": "stay_facet_ask", "facet_key": "bill_diagnosis"}
    tr = dr.turn_result_v2(case_id="07", turn=4, snapshot=snap,
                           sources=[], answer="請提供帳單編號", noise_tags=[])
    assert tr["routing_verdict"] == "stay_facet_ask"
    assert tr["source"] == "snapshot"
    assert tr["classifier_version"] is None      # verdict 尺不靠文字規則


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_missing_snapshot_is_not_silently_guessed():
    tr = dr.turn_result_v2(case_id="07", turn=4, snapshot=None,
                           sources=[], answer="請提供帳單編號", noise_tags=[])
    assert tr["routing_verdict"] is None, "沒有快照就不得猜——猜了就退回文字反推的老路"
    assert tr["source"] == "missing"


# ── R1.3.1：複合鍵 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_composite_key_includes_grounded_and_answer_verdict():
    a = dr.turn_result_v2("09", 10, {"routing_verdict": "direct_answer"},
                          sources=["一物件多合約 上限10份"], answer="上限 10 份", noise_tags=[])
    b = dr.turn_result_v2("09", 10, {"routing_verdict": "direct_answer"},
                          sources=[], answer="並沒有上限", noise_tags=[])
    assert a["grounded"] is True and b["grounded"] is False
    assert dr.composite_key_v2(a) != dr.composite_key_v2(b), (
        "同 verdict 但知識接地翻轉必須算不一致——這正是舊尺漏計 36% 的那型")


# ── R1.3.4：legacy 尺不得與 verdict 尺混計 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_legacy_and_snapshot_must_not_mix():
    snap_tr = dr.turn_result_v2("01", 1, {"routing_verdict": "direct_answer"},
                                sources=[], answer="x", noise_tags=[])
    legacy_tr = dr.turn_result_legacy("01", 1, answer="查無對應的資料", sources=[], noise_tags=[])
    assert legacy_tr["source"] == "legacy_text"
    assert legacy_tr["classifier_version"].startswith("rc-v1+")
    with pytest.raises(dr.RulerMixError):
        dr.compare_rounds({("01", 1): snap_tr}, {("01", 1): legacy_tr})


# ════════════════════════════════════════════════════════════
# R1.3.3 換尺鐵則：新尺必須看得見已知病灶
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.3")
def test_new_ruler_sees_known_stickiness_flip():
    """#07 T4 黏著：正常輪切到金流面向、黏著輪留在帳單面向索編號。

    舊五類尺兩者皆 ANSWER／ASK_ID 混沌；**新尺必須判為不一致**，
    否則就是換了一把對主病灶同樣全盲的尺（D-24 教訓）。
    """
    normal = dr.turn_result_v2("07", 4, {"routing_verdict": "enter_facet",
                                         "facet_key": "billing_setup_guide"},
                               sources=[], answer="請問您是否已經開通新的收款帳戶驗證？",
                               noise_tags=[])
    sticky = dr.turn_result_v2("07", 4, {"routing_verdict": "stay_facet_ask",
                                         "facet_key": "bill_diagnosis"},
                               sources=[], answer="目前我們專注於帳單操作問題……請提供帳單編號",
                               noise_tags=[])
    assert dr.composite_key_v2(normal) != dr.composite_key_v2(sticky)


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_stay_facet_subdivision_is_load_bearing():
    """面向續輪若不細分 ask/answer，黏著前後皆 stay 而判為一致——鐵則要擋的正是這個。"""
    asking = dr.turn_result_v2("10", 3, {"routing_verdict": "stay_facet_ask"},
                               sources=[], answer="請提供帳單編號（bill_ref）", noise_tags=[])
    answering = dr.turn_result_v2("10", 3, {"routing_verdict": "stay_facet_answer"},
                                  sources=[], answer="對帳的過程主要是確認……", noise_tags=[])
    assert dr.composite_key_v2(asking) != dr.composite_key_v2(answering)
    # 且兩者都必須落在合法值域內
    for tr in (asking, answering):
        assert tr["routing_verdict"] in dr.ROUTING_VERDICTS


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_ruler_gate_rejects_blind_ruler():
    """`assert_ruler_sees_known_defects()` 是換尺的自檢閘門：
    餵一組「病灶在此尺上看不見」的資料，必須 raise。"""
    # 瞎尺的樣子：黏著輪與正常輪被判成同一個合法值（正是 stay_facet 未細分時的下場）
    blind = {("07", 4): [dr.turn_result_v2("07", 4, {"routing_verdict": "stay_facet_ask"},
                                           sources=[], answer="a", noise_tags=[]),
                         dr.turn_result_v2("07", 4, {"routing_verdict": "stay_facet_ask"},
                                           sources=[], answer="b", noise_tags=[])]}
    ok, flat = dr.assert_ruler_sees_known_defects(blind, require_any=False)
    assert flat == [("07", 4)], "全部一致的病灶輪須被列出供報告揭露"
    with pytest.raises(dr.BlindRulerError):
        dr.assert_ruler_sees_known_defects(blind)      # 無任何翻動 → 可疑


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_ruler_gate_passes_when_defect_visible():
    ok = {("07", 4): [dr.turn_result_v2("07", 4, {"routing_verdict": "enter_facet"},
                                        sources=[], answer="a", noise_tags=[]),
                      dr.turn_result_v2("07", 4, {"routing_verdict": "stay_facet_ask"},
                                        sources=[], answer="b", noise_tags=[])],
          ("10", 3): [dr.turn_result_v2("10", 3, {"routing_verdict": "stay_facet_ask"},
                                        sources=[], answer="a", noise_tags=[]),
                      dr.turn_result_v2("10", 3, {"routing_verdict": "direct_answer"},
                                        sources=[], answer="b", noise_tags=[])],
          ("21", 3): [dr.turn_result_v2("21", 3, {"routing_verdict": "direct_answer"},
                                        sources=[], answer="a", noise_tags=[]),
                      dr.turn_result_v2("21", 3, {"routing_verdict": "stay_facet_ask"},
                                        sources=[], answer="b", noise_tags=[])]}
    passed, flat = dr.assert_ruler_sees_known_defects(ok)
    assert passed is True and flat == []


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_unsubdivided_stay_facet_is_rejected_at_domain():
    """`stay_facet` 未細分＝值域外，快照帶進來就當場擋下——
    細分不是建議而是強制（否則 #07 黏著在此尺上不可見）。"""
    with pytest.raises(dr.GateError):
        dr.turn_result_v2("07", 4, {"routing_verdict": "stay_facet"},
                          sources=[], answer="x", noise_tags=[])


# ── R1.3.3 主判準：能力檢查（決定性，不依賴抽樣）──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_ruler_can_represent_all_documented_defects():
    """本尺必須表達得出三個已知病灶的兩種結果差異——這是尺的性質，與抽樣無關。"""
    assert dr.assert_ruler_can_represent_defects() is True


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_capability_check_catches_unsubdivided_ruler(monkeypatch):
    """把 stay_facet_ask 併回 stay（模擬不細分的尺）→ 能力檢查必須擋下。"""
    orig = dr.composite_key_v2
    monkeypatch.setattr(dr, "composite_key_v2",
                        lambda tr: (str(tr["routing_verdict"]).replace("_ask", "")
                                    .replace("_answer", ""),
                                    tr["grounded"], tr["answer_verdict"]))
    # #07 T4：enter_facet vs stay_facet_ask 仍可分；#10 T3 與 #21 T3 亦然 → 需更瞎的尺
    monkeypatch.setattr(dr, "composite_key_v2", lambda tr: ("same", None, None))
    with pytest.raises(dr.BlindRulerError):
        dr.assert_ruler_can_represent_defects()
