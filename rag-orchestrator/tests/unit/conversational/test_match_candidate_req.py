"""unit:候選確定性比對 `_match_candidate`（conversational-diagnosis 任務 5.2 / R3.5, R2.2, R2.3）。

純函式：依使用者輸入比對候選的序號（1-based）/ id / label（子字串），無法判定回 None。
不依賴 LLM。
"""
import pytest

from services.conversational_engine import _match_candidate

pytestmark = pytest.mark.unit

CANDS = [{"id": 1, "label": "基隆物件"}, {"id": 2, "label": "台北物件"}, {"id": 3, "label": "桃園物件"}]


@pytest.mark.req("conversational-diagnosis:3.5")
def test_match_by_ordinal():
    assert _match_candidate("1", CANDS) == CANDS[0]
    assert _match_candidate("2", CANDS) == CANDS[1]
    assert _match_candidate(" 3 ", CANDS) == CANDS[2]


@pytest.mark.req("conversational-diagnosis:2.3")
def test_match_by_exact_label():
    assert _match_candidate("台北物件", CANDS) == CANDS[1]


@pytest.mark.req("conversational-diagnosis:2.3")
def test_match_by_label_substring():
    assert _match_candidate("基隆", CANDS) == CANDS[0]


@pytest.mark.req("conversational-diagnosis:3.5")
def test_match_by_id_when_not_ordinal():
    cands = [{"id": 10, "label": "A"}, {"id": 20, "label": "B"}]
    assert _match_candidate("20", cands) == cands[1]   # 20 非序號（>長度）→ id 比對


@pytest.mark.req("conversational-diagnosis:3.5")
def test_ordinal_takes_priority_over_id():
    cands = [{"id": 5, "label": "A"}, {"id": 3, "label": "B"}]
    assert _match_candidate("1", cands) == cands[0]    # 序號 1 → 第一筆（id=5），非 id=1


@pytest.mark.req("conversational-diagnosis:2.2")
def test_no_match_returns_none():
    assert _match_candidate("不存在的物件", CANDS) is None
    assert _match_candidate("99", CANDS) is None       # 超出序號且無此 id
    assert _match_candidate("", CANDS) is None
    assert _match_candidate("1", []) is None
