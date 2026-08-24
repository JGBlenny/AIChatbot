"""unit：C4b 報告紀律（spec conversational-routing-execution 任務 6.4，R3.2／R9.1）。

6.4 的義務是「C4b 未過而僅 C4a 過時，所有對外表述 SHALL 為
『執行鏈閉環已證實，最終答案能力尚未放行』，SHALL NOT 為『最終答案能力已證實』」。

⚠️ **寫在文件裡的紀律會被下一個人覆蓋，寫成測試的不會。**
本檔把該義務變成機器檢查：掃本 spec 目錄所有 Markdown，出現禁用表述而該行**未**同時
標明它是被禁止的（`SHALL NOT`／`不得`／`❌`／`禁止`／`不可`），即紅。

⚠️ 本檔**不判斷 C4b 是否通過**——它只保證「未通過」這件事不會在文字上被講成通過。
若日後 C4b 真的通過並經業主放行，應**明確刪除或改寫本檔**，而不是讓它默默失效。
"""
import glob
import os

import pytest

pytestmark = pytest.mark.unit

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_SPEC_DIR = os.path.join(_REPO, ".kiro", "specs", "conversational-routing-execution")

#: 禁用表述——出現即須在同一行標明它是被禁止的
FORBIDDEN = (
    "最終答案能力已證實",
    "3/4 cases passed",
    "3/4 案通過",
    "C4b 已通過",
    "C4b 通過上線 gate",
    "production-facing gate OPEN",
)

#: 同一行出現任一項即視為「在陳述禁令」，放行
PROHIBITION_MARKERS = ("SHALL NOT", "不得", "❌", "禁止", "不可")

#: 簽署版報告必須帶的唯一合規表述
COMPLIANT_SENTENCE = "執行鏈閉環已證實"
_REPORT = os.path.join(_SPEC_DIR, "c4b-release-gate-report.md")


def _md_files():
    if not os.path.isdir(_SPEC_DIR):
        pytest.skip(f"spec 目錄未掛載：{_SPEC_DIR}")
    return sorted(glob.glob(os.path.join(_SPEC_DIR, "**", "*.md"), recursive=True))


@pytest.mark.req("conversational-routing-execution:9.1")
def test_no_unqualified_overclaim_in_spec_docs():
    """禁用表述只能以『被禁止』的身分出現，不得作為主張。"""
    offenders = []
    for path in _md_files():
        for lineno, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            for phrase in FORBIDDEN:
                if phrase in line and not any(m in line for m in PROHIBITION_MARKERS):
                    offenders.append(f"{os.path.basename(path)}:{lineno}｜{phrase}｜{line.strip()[:80]}")
    assert not offenders, (
        "出現未標示為禁止的 C4b 過度表述（任務 6.4）：\n  " + "\n  ".join(offenders))


@pytest.mark.req("conversational-routing-execution:9.1")
def test_signed_report_carries_the_compliant_sentence():
    """簽署版報告必須明載唯一合規表述，否則紀律無處可依。"""
    if not os.path.exists(_REPORT):
        pytest.skip("簽署版報告尚未存在")
    text = open(_REPORT, encoding="utf-8").read()
    assert COMPLIANT_SENTENCE in text and "最終答案能力尚未放行" in text, \
        "簽署版報告未載明『執行鏈閉環已證實，最終答案能力尚未放行』"


@pytest.mark.req("conversational-routing-execution:9.1")
def test_release_gate_stays_closed_in_the_ledger():
    """spec.json 的 release_gate 必須仍記錄三項 production-facing 變更被擋著。"""
    import json
    path = os.path.join(_SPEC_DIR, "spec.json")
    if not os.path.exists(path):
        pytest.skip("spec.json 未掛載")
    gate = (json.load(open(path, encoding="utf-8"))
            .get("implementation", {}).get("release_gate", {}))
    assert set(gate.get("blocked_until_released") or []) >= {"4.6", "8", "9"}, \
        f"release_gate 的 blocked_until_released 被鬆綁：{gate}"
