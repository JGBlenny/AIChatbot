"""unit：`RulesetManifest` 與**規則集的版本化**（任務 2.6｜R3.5, R7.2）。

任務 2 的邊界，用一句話講完：

> **問句側 signal 已是 deterministic、版本化、可稽核的 candidate asset，
> 但尚未獲准影響 production routing。**

本檔鎖的就是那個「尚未獲准」：

```text
ruleset digest   ✓
protocol digest  ✓
dataset digest   ✓
holdout not_run  ✗   → 仍不得啟用
```

⚠️ **測得出「PASS 時會放行」≠ production manifest 現在可以寫 PASS。**
真實 status SHALL 一直維持 `not_run`，直到任務 6 的 unseen holdout 裁決。
"""
import pytest

pytestmark = pytest.mark.unit

ACTIVE_PROTOCOL_DIGEST = "4690a258f502d98d"


def _m():
    from services import instance_reference_gate as m
    return m


@pytest.mark.req("routing-disambiguation:3.5")
def test_production_manifest_holdout_is_never_passed():
    """⚠️ 本檔最重要的一條：**production manifest 不得宣稱 passed**。

    任務 6 已於 2026-08-24 裁決 **REFUTED**，故狀態由 `not_run` 轉為 `failed`。
    ⚠️ 兩者在啟用守門上同樣拒絕，但語義不得互換：
    `failed` ＝**已驗且未通過**（本次反證），`not_run` ＝**尚未驗**。
    改回 `not_run` 會抹掉反證；改成 `passed` 則是本 spec 一路在防的事。
    """
    m = _m()
    status = m.current_manifest().holdout.status
    assert status != "passed", "production manifest 宣稱 holdout 已過——與任務 6 的 REFUTED 裁決矛盾"
    assert status == "failed", f"任務 6 已裁決 REFUTED，狀態應為 failed（實得 {status!r}）"


@pytest.mark.req("routing-disambiguation:3.5")
def test_production_manifest_cannot_enable_the_gate_today():
    """即使三重 digest 全部相符，`failed` 仍須擋下——這正是 1.1 特別鎖的那一路。"""
    m = _m()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(m.current_manifest(),
                                active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


@pytest.mark.req("routing-disambiguation:7.2")
def test_ruleset_digest_changes_when_any_pattern_changes():
    """規則集為**版本化資產**：規則一改，digest 就變 → 舊 holdout PASS 隨即失效。"""
    m = _m()
    base = m.ruleset_digest("ie-v1", {"possessive": "我的"}, {"explanation_request": "怎麼算"})
    assert base == m.ruleset_digest("ie-v1", {"possessive": "我的"},
                                    {"explanation_request": "怎麼算"}), "digest 不穩定"
    assert base != m.ruleset_digest("ie-v1", {"possessive": "我的|這張"},
                                    {"explanation_request": "怎麼算"}), "改正向規則 digest 未變"
    assert base != m.ruleset_digest("ie-v1", {"possessive": "我的"},
                                    {"explanation_request": "怎麼算|在哪裡"}), "改反向規則 digest 未變"
    assert base != m.ruleset_digest("ie-v2", {"possessive": "我的"},
                                    {"explanation_request": "怎麼算"}), "改版本 digest 未變"


@pytest.mark.req("routing-disambiguation:7.2")
def test_current_manifest_digest_tracks_the_live_ruleset():
    """manifest 的 digest SHALL 由**當前實際生效的**規則集算出，不得是寫死的字串。"""
    m = _m()
    from services.instance_evidence import (COUNTER_PATTERNS, POSITIVE_PATTERNS,
                                            InstanceEvidenceExtractor)
    expected = m.ruleset_digest(InstanceEvidenceExtractor.RULESET_VERSION,
                                POSITIVE_PATTERNS, COUNTER_PATTERNS)
    assert m.current_manifest().digest == expected


@pytest.mark.req("routing-disambiguation:7.2")
def test_manifest_patterns_are_not_mutable_through_the_manifest():
    """⚠️ `frozen=True` 只凍欄位綁定——pattern 表本身也必須不可變。"""
    m = _m()
    manifest = m.current_manifest()
    with pytest.raises(TypeError):
        manifest.positive_patterns["possessive"] = "任意改"
    with pytest.raises(TypeError):
        manifest.counter_patterns["explanation_request"] = "任意改"


@pytest.mark.req("routing-disambiguation:7.2")
def test_mutating_the_source_dict_does_not_change_a_built_manifest():
    """manifest 保存的是**副本**——外部改了來源 dict 也不得動到既有 manifest。"""
    m = _m()
    src = {"possessive": "我的"}
    manifest = m.RulesetManifest(version="ie-v1", positive_patterns=src, counter_patterns={},
                                 digest="rs-x")
    src["possessive"] = "被改了"
    assert manifest.positive_patterns["possessive"] == "我的"
