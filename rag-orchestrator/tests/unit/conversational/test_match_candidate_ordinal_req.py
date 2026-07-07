"""unit:候選選擇支援中文口語序數（domain-conversational-facets 後續｜候選辨識口語化）。

`_match_candidate` 除純數字/id/label 子字串外，另認中文序數口語：
  第二個 / 第二筆 / 第2個 / 二 / 兩 / 最後一個 / 頭一個 → 對應序號。
越界或無法解析 → None（交插點A 再列候選）。既有純數字/id/label 行為不變。
"""
import pytest

from services.conversational_engine import _match_candidate

pytestmark = pytest.mark.unit

CANDS = [{"id": 11, "label": "基隆A｜2026/06/29"},
         {"id": 22, "label": "基隆B｜2026/06/30"},
         {"id": 33, "label": "基隆C｜2026/07/31"}]


@pytest.mark.parametrize("msg,expect_id", [
    ("第二個", 22), ("第二筆", 22), ("第2個", 22), ("二", 22), ("兩", 22),
    ("第一個", 11), ("頭一個", 11), ("第三筆", 33), ("最後一個", 33), ("最後一筆", 33),
])
@pytest.mark.req("domain-conversational-facets:4.4")
def test_ordinal_selection(msg, expect_id):
    r = _match_candidate(msg, CANDS)
    assert r is not None and r["id"] == expect_id, f"{msg} 應選到 id={expect_id}"


# ── 既有行為不變：純數字 / id / label 子字串 ──
@pytest.mark.req("domain-conversational-facets:4.4")
def test_existing_matching_unchanged():
    assert _match_candidate("2", CANDS)["id"] == 22       # 純序號
    assert _match_candidate("33", CANDS)["id"] == 33      # id 完全比對
    assert _match_candidate("基隆B", CANDS)["id"] == 22   # label 子字串


# ── 越界 / 無法對應 → None ──
@pytest.mark.req("domain-conversational-facets:4.4")
def test_out_of_range_or_unparseable_returns_none():
    assert _match_candidate("第九個", CANDS) is None      # 超過筆數
    assert _match_candidate("我不確定欸", CANDS) is None  # 非選擇語句
