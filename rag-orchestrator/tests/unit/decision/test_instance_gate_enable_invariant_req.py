"""unit：InstanceReferenceGate 的**啟用守門** negative control
（spec routing-disambiguation 任務 1.1｜R3.5, R9.2）。

守的是一句話：**規則集未經 matching holdout 驗證者，不得啟用 gate。**

⚠️ 為什麼需要「三重 digest 綁定」而不是「有沒有 holdout 結果」：
design v1.0 原訂 `holdout_result: Optional[str]`，規定「None 時不得啟用」。
但 `holdout_result = "FAILED"` 也是 non-None——照那份契約反而**可以**開旗標。
那是**假的 fail-closed：只防 missing、不防 failed**，
與前案 `startswith("[gate]")` 恆為 False 的分類器是同一種形態
（看似守門、實則恆真）。

故啟用契約為三條**同時**成立：
    status == "passed"
    holdout.ruleset_digest  == manifest.digest          ← 防「舊版 PASS 沿用到改過的規則」
    holdout.protocol_digest == 現行量尺 digest           ← 防「舊尺 PASS 沿用到新尺」

⚠️ 本檔於任務 1.1 建立時**應為紅**（實作尚不存在）——那是它有效的證明。
   import 置於各測試內，使四條路徑**各自**以清楚訊息失敗，
   而非整檔在收集階段 error 而看不出個別攔截。
"""
import pytest

pytestmark = pytest.mark.unit

#: protocol v1 的 digest（robustness-protocol.json，Req.3.5 已凍結）
ACTIVE_PROTOCOL_DIGEST = "4690a258f502d98d"


def _mod():
    """延後匯入：實作尚不存在時，讓每個測試各自紅在自己的斷言上。"""
    from services import instance_reference_gate as m  # noqa: PLC0415
    return m


def _manifest(m, *, status, ruleset_digest="rs-abc", protocol_digest=ACTIVE_PROTOCOL_DIGEST,
              manifest_digest="rs-abc"):
    return m.RulesetManifest(
        version="ie-v1",
        positive_patterns={"possessive": r"我的|我這|這張"},
        counter_patterns={"explanation_request": r"怎麼算|在哪裡"},
        digest=manifest_digest,
        holdout=m.HoldoutRecord(
            status=status,
            ruleset_digest=ruleset_digest,
            protocol_digest=protocol_digest,
            dataset_id="holdout-2026Q3",
            dataset_digest="ds-xyz",
        ),
    )


# ── 四條必須拒絕的路徑 ───────────────────────────────────────
@pytest.mark.req("routing-disambiguation:3.5")
def test_reject_when_holdout_not_run():
    m = _mod()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(_manifest(m, status="not_run"),
                                active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


@pytest.mark.req("routing-disambiguation:3.5")
def test_reject_when_holdout_failed():
    """⚠️ 最關鍵的一條：原設計的 `result != None` 會**放行**這一路。"""
    m = _mod()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(_manifest(m, status="failed"),
                                active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


@pytest.mark.req("routing-disambiguation:3.5")
def test_reject_when_passed_on_a_different_ruleset():
    """規則集改過（digest 不符）→ 舊 PASS 不得沿用。"""
    m = _mod()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(
            _manifest(m, status="passed", ruleset_digest="rs-OLD", manifest_digest="rs-NEW"),
            active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


@pytest.mark.req("routing-disambiguation:9.2")
def test_reject_when_passed_under_a_different_protocol():
    """量尺換版（protocol digest 不符）→ 舊 PASS 不得沿用。"""
    m = _mod()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(
            _manifest(m, status="passed", protocol_digest="OLD-PROTOCOL"),
            active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


# ── 唯一允許的路徑 ──────────────────────────────────────────
@pytest.mark.req("routing-disambiguation:3.5")
def test_allow_only_when_all_three_match():
    m = _mod()
    m.assert_gate_enablable(_manifest(m, status="passed"),
                            active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)


@pytest.mark.req("routing-disambiguation:3.5")
def test_rejection_is_not_downgraded_to_warning():
    """守門 SHALL NOT 降級為 warning——本專案僅三處不 fail-open，此為其一。"""
    m = _mod()
    with pytest.raises(m.GateNotEnablable):
        m.assert_gate_enablable(_manifest(m, status="failed"),
                                active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)
