"""unit：C4b e2e harness 的 session isolation invariant（任務 6.2 前置，R3.2）。

⚠️ **本檔零 OpenAI 成本、不起服務**：只驗 harness 自己的隔離語義。
被驗的命題只有一個：

> 每個 run、以及每次 infra retry，都必須是**全新的一條 session**。

若不成立，`attempt 1` 建立的 Face 會話／已收槽位／`asked_count` 會被 `attempt 2` 繼承，
「三次獨立重跑」就退化成「同一條 session 累積狀態後連續跑三遍」——harness false-green。
"""
import pytest

pytestmark = pytest.mark.unit


class _FakeResp:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeLedger:
    """只提供 `_one_run` 用到的兩個方法；內容由 fake `_post` 餵入。"""

    def __init__(self):
        self.calls = []

    def since(self, mark):
        return self.calls[mark:]

    def __len__(self):
        return len(self.calls)


def _spec():
    from tests.support.brain_grounding import BrainGroundingAssertion
    return BrainGroundingAssertion(
        case="harness-probe", execution_face="bill_diagnosis", fixture_bill_id=900003,
        user_turns=("問句", "900003"),
        answer_must_contain=(("7,500",),),
        generic_fallback_markers=("請洽客服",),
        literal_provenance={"7,500": "fixtures 900003.total"},
    )


@pytest.mark.req("conversational-routing-execution:3.2")
def test_each_run_and_each_infra_retry_gets_a_fresh_session(monkeypatch):
    from tests.e2e.conversational import test_c4b_brain_grounding_e2e_req as h

    ledger = _FakeLedger()
    turn1_sessions, turn2_sessions = [], []
    state = {"infra_raised": False}

    def fake_post(client, message, sid, *, trigger_facet_key=None):
        if trigger_facet_key:                      # 第 1 輪
            turn1_sessions.append(sid)
            ledger.calls.append({**h.FROZEN_BRAIN, "has_response_format": True})
            return _FakeResp({"answer": "請問是哪一張帳單？", "intent_type": "conversational"})
        turn2_sessions.append(sid)                 # 第 2 輪
        if not state["infra_raised"]:              # 第一次跑到這裡：模擬 infra 失敗
            state["infra_raised"] = True
            raise TimeoutError("Request timed out")
        ledger.calls.append({**h.FROZEN_SYNTH, "has_response_format": False})
        return _FakeResp({"answer": "金額是 7,500 元。"})

    monkeypatch.setattr(h, "_post", fake_post)
    monkeypatch.setattr(h, "_conversational_rows", lambda sid: 0)
    monkeypatch.setattr(h, "_cleanup", lambda sid: None)
    monkeypatch.setattr(h.time, "sleep", lambda s: None)

    records, retries = h._run_case(client=None, ledger=ledger, spec=_spec())

    assert retries == 1, "模擬的 infra 失敗應觸發且只觸發一次 retry"
    assert len(records) == h.RUNS_PER_CASE and all(r["passed"] for r in records)

    used = turn1_sessions
    assert len(used) == h.RUNS_PER_CASE + 1, \
        f"3 次 run ＋ 1 次 retry 應開 4 條 session，實得 {len(used)}"
    assert len(set(used)) == len(used), f"session 被重用：{used}"
    # retry 的第二次 attempt 不得沿用前一次 attempt 的 session
    assert turn2_sessions[0] != turn2_sessions[1], \
        "infra retry 沿用了失敗那次的 session——不是乾淨重試"


@pytest.mark.req("conversational-routing-execution:3.2")
def test_session_id_allocator_refuses_reuse(monkeypatch):
    """配發器本身即是 machine invariant，不靠呼叫端自律。"""
    from tests.e2e.conversational import test_c4b_brain_grounding_e2e_req as h

    monkeypatch.setattr(h.uuid, "uuid4", lambda: type("U", (), {"hex": "f" * 32})())
    first = h._new_session_id("probe", 1, 0)
    assert first in h._SEEN_SESSIONS
    with pytest.raises(h.SessionReuseError):
        h._new_session_id("probe", 1, 0)      # 同樣的輸入＋同樣的 uuid → 必須被擋


@pytest.mark.req("conversational-routing-execution:3.2")
def test_dirty_session_start_is_refused(monkeypatch):
    """起點不乾淨（已有對話偽會話列）→ 該次量測直接拒收。"""
    from tests.e2e.conversational import test_c4b_brain_grounding_e2e_req as h

    monkeypatch.setattr(h, "_conversational_rows", lambda sid: 1)
    monkeypatch.setattr(h, "_cleanup", lambda sid: None)
    with pytest.raises(AssertionError, match="起點不乾淨"):
        h._one_run(client=None, ledger=_FakeLedger(), spec=_spec(), run_idx=1, attempt=0)
