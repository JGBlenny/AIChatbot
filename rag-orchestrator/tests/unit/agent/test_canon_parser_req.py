"""unit：`services/agent/canon/canon_parser.py`（spec knowledge-outline-and-intent-architecture 任務 2.1；需求 2.1, 2.3, 2.5, 2.8, 7.3）。

覆蓋：
- 固定樣本往返決定性（兩次解析逐位元相同 dict／sha；export_json 兩次逐位元相同）。
- content_units 對 provenance_units 切法恆等；一行多句必紅。
- 講法零字元進可引用文字：`phrasing_leaks(doc)` 為空；正對照——把一句講法塞進內容行 ⇒ 必紅。
- 屬性區塊任何壞行 raise CanonFormatError（列號＋原因），⛔ 不落 content_units：每種格式錯各一案。
- traffic 講法 ≤20 字且不含 ≥4 位數字串。
- 鍵清單與正則與 hook `outline_gate.py` 同值（兩邊只准一致）。
"""
from __future__ import annotations

import json
import os
import re

import pytest

from services.agent.canon.canon_parser import (
    ATTR_KEYS, FINE_ID_RE, FRONT_MATTER_KEYS, CanonFormatError, content_text, export_json, parse_canon,
    parse_canon_text, phrasing_leaks, to_dict,
)
from services.agent.provenance_units import split_sentences

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.1")]

SAMPLE = """---
audience: prospect
version: 2026-09-06.1
reviewers: [owner]
language: zh-TW
budget_tokens: 10000
target_user: [landlord]
business_types: [system_provider]
---
## A 產品基本盤 {#A}
### 系統定位與適用對象 {#prospect/A/positioning}
- phrasings:
  - {text: "你們系統適合我嗎", source: "question_summary:3585", status: approved}
  - {text: "適不適合小房東", source: "koyu:03#12", status: proposed}
- sources: [kb:3585, kb:3602]
- reviewed: {by: owner, at: 2026-09-06}
- see_also: [prospect/B/fit-by-scale]
- instance_applicability: general
金箍棒把物件、合約、收租集中在一個系統管理。
想知道適不適合，先了解您管幾間。

### 免費試用 {#prospect/A/trial}
- phrasings:
  - {text: "可以先試用嗎", source: "traffic:202609#1", status: approved}
- sources: [kb:3596]
- instance_applicability: general
- target_user: [landlord, agent]
可先免費試用一個月。
## G 現有不足 {#G}
### 客製開發與計價 {#prospect/G/custom-dev}
- policy: deliberate_no
- policy_ref: DSP-009
- instance_applicability: general
目前不提供客製開發報價。
"""


def _hook_module():
    """載入 hook 模組（repo 根 .claude/hooks；容器內掛在 /.claude）。"""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here))))
    for base in (repo, "/"):
        p = os.path.join(base, ".claude", "hooks", "outline_gate.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("outline_gate", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    pytest.skip("outline_gate.py 不在掛載路徑")


# ---------------------------------------------------------------------------
# 往返決定性
# ---------------------------------------------------------------------------

def test_roundtrip_deterministic(tmp_path):
    d1 = parse_canon_text(SAMPLE)
    d2 = parse_canon_text(SAMPLE)
    assert to_dict(d1) == to_dict(d2)
    assert d1.canon_sha256 == d2.canon_sha256 and len(d1.canon_sha256) == 64
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    assert export_json(d1, str(p1)) == export_json(d2, str(p2)) == d1.canon_sha256
    assert p1.read_bytes() == p2.read_bytes()
    assert json.loads(p1.read_text(encoding="utf-8"))["canon_sha256"] == d1.canon_sha256


def test_parse_canon_from_file_and_shape(tmp_path):
    p = tmp_path / "prospect.md"
    p.write_text(SAMPLE, encoding="utf-8")
    doc = parse_canon(str(p))
    assert doc.audience == "prospect" and doc.budget_tokens == 10000 and doc.reviewers == ("owner",)
    assert [c.id for c in doc.coarses] == ["A", "G"]
    fines = doc.fines()
    assert [f.id for f in fines] == ["prospect/A/positioning", "prospect/A/trial", "prospect/G/custom-dev"]
    pos = fines[0]
    assert pos.title == "系統定位與適用對象" and pos.sources == ("kb:3585", "kb:3602")
    assert pos.reviewed_by == "owner" and pos.reviewed_at == "2026-09-06" and pos.see_also == ("prospect/B/fit-by-scale",)
    assert [p.status for p in pos.phrasings] == ["approved", "proposed"]
    assert pos.content_units == ("金箍棒把物件、合約、收租集中在一個系統管理。", "想知道適不適合，先了解您管幾間。")
    assert pos.target_user == ("landlord",) and pos.business_types == ("system_provider",)  # front matter 預設
    assert fines[1].target_user == ("landlord", "agent")  # 細目覆寫
    custom = fines[2]
    assert custom.policy == "deliberate_no" and custom.policy_ref == "DSP-009" and custom.phrasings == ()


def test_content_sha_changes_only_with_content():
    base = parse_canon_text(SAMPLE)
    changed = parse_canon_text(SAMPLE.replace("可先免費試用一個月。", "可先免費試用兩個月。"))
    a = {f.id: f.content_sha256 for f in base.fines()}
    b = {f.id: f.content_sha256 for f in changed.fines()}
    assert a["prospect/A/trial"] != b["prospect/A/trial"]
    assert a["prospect/A/positioning"] == b["prospect/A/positioning"]
    assert base.phrasing_set_sha256 == changed.phrasing_set_sha256  # 講法沒動
    only_status = parse_canon_text(SAMPLE.replace('status: proposed}', 'status: approved}'))
    assert only_status.phrasing_set_sha256 != base.phrasing_set_sha256


# ---------------------------------------------------------------------------
# content_units ＝ provenance_units 切法（恆等）
# ---------------------------------------------------------------------------

def test_content_units_identity_with_provenance_split():
    doc = parse_canon_text(SAMPLE)
    for f in doc.fines():
        for u in f.content_units:
            assert split_sentences(u) == [u]
        joined = "\n".join(f.content_units)
        assert [x for x in split_sentences(joined) if x != "\n"] == list(f.content_units)  # 切法恆等（換行片段除外）


def test_multi_sentence_line_is_rejected():
    bad = SAMPLE.replace("可先免費試用一個月。", "可先免費試用一個月。之後再決定。")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "一行只能一句" in str(ei.value) and ei.value.lineno == 28


# ---------------------------------------------------------------------------
# 講法零字元進可引用文字（注入面）
# ---------------------------------------------------------------------------

def test_phrasings_never_in_content_text_and_positive_control():
    doc = parse_canon_text(SAMPLE)
    assert phrasing_leaks(doc) == []
    text = content_text(doc)
    for f in doc.fines():
        for p in f.phrasings:
            assert p.text not in text
    # 正對照：把一句講法塞進內容行 ⇒ 守門必紅
    injected = SAMPLE.replace("可先免費試用一個月。", "可先免費試用一個月。\n可以先試用嗎")
    doc2 = parse_canon_text(injected)
    assert phrasing_leaks(doc2) == ["prospect/A/trial: 可以先試用嗎"]
    # NFKC：全形／空白變體也抓得到
    assert phrasing_leaks(doc, text="　可以先試用嗎　") == ["prospect/A/trial: 可以先試用嗎"]  # 全形空白變體＝整句相等
    assert phrasing_leaks(doc, text="說明：可以先試用嗎，細節另議") == []  # 短講法被包含在長句裡不算（<10 字）


# ---------------------------------------------------------------------------
# 每種格式錯各一案：屬性區塊壞行一律 raise，⛔ 不落 content_units
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mutate, expect", [
    (lambda s: s.replace("- sources: [kb:3585, kb:3602]", "- score: 0.9"), "不允許的鍵 'score'"),
    (lambda s: s.replace("- sources: [kb:3585, kb:3602]", "- sources: kb:3585"), "sources 須為 [a, b] 清單"),
    (lambda s: s.replace('  - {text: "適不適合小房東", source: "koyu:03#12", status: proposed}', "  - 適不適合小房東"), "phrasings 子項須為"),
    (lambda s: s.replace('status: proposed}', 'status: maybe}'), "status 須為"),
    (lambda s: s.replace("- reviewed: {by: owner, at: 2026-09-06}", "- reviewed: owner"), "reviewed 須為"),
    (lambda s: s.replace("- policy: deliberate_no", "- policy: refuse"), "policy 須為"),
    (lambda s: s.replace("- instance_applicability: general\n目前不提供", "目前不提供"), "缺必填屬性 instance_applicability"),
    (lambda s: s.replace("- sources: [kb:3585, kb:3602]", "- sources: [kb:3585]\n  - {text: \"x\", source: \"y\", status: approved}"), "縮排子項只允許在 phrasings"),
    (lambda s: s.replace("- sources: [kb:3585, kb:3602]", "- sources: [kb:3585]\n- sources: [kb:3602]"), "屬性重複 'sources'"),
    (lambda s: s.replace("想知道適不適合，先了解您管幾間。", "想知道適不適合，先了解您管幾間。\n- see_also: [prospect/B/x]"), "屬性須在內容之前"),
    (lambda s: s.replace("{#prospect/A/trial}", "{#Prospect/A/trial}"), "細目 id 不合法格式"),
    (lambda s: s.replace("{#prospect/A/trial}", "{#tenant/A/trial}"), "受眾 'tenant'"),
    (lambda s: s.replace("{#prospect/A/trial}", "{#prospect/B/trial}"), "粗目碼 'B'"),
    (lambda s: s.replace("{#prospect/A/trial}", "{#prospect/A/positioning}"), "細目 id 重複"),
    (lambda s: s.replace("## G 現有不足 {#G}", "## G 現有不足 {#A}"), "粗目碼重複"),
    (lambda s: s.replace("## A 產品基本盤 {#A}\n", ""), "細目出現在任何粗目之前"),
    (lambda s: s.replace("## G 現有不足 {#G}", "## G 現有不足"), "標題行無法解析"),
    (lambda s: s.replace("budget_tokens: 10000", "budget_tokens: many"), "budget_tokens 須為正整數"),
    (lambda s: s.replace("language: zh-TW\n", ""), "front matter 缺鍵：language"),
    (lambda s: s.replace("audience: prospect", "audience: guest"), "audience 須為"),
    (lambda s: s.replace("audience: prospect", "owner: me\naudience: prospect"), "front matter 不允許的鍵 'owner'"),
    (lambda s: s.split("---\n## A")[0], "front matter 未閉合"),
    (lambda s: s.replace("## A 產品基本盤 {#A}\n", "## A 產品基本盤 {#A}\n這行在細目之外。\n"), "細目之外不得有內容"),
    (lambda s: s.replace('{text: "可以先試用嗎", source: "traffic:202609#1"', '{text: "可以先試用嗎我的合約號是12345678", source: "traffic:202609#1"'), "traffic 講法"),
    (lambda s: s.replace('{text: "可以先試用嗎", source: "traffic:202609#1"', '{text: "可以先試用嗎可以先試用嗎可以先試用嗎可以先試用嗎", source: "traffic:202609#1"'), "traffic 講法超過 20 字"),
])
def test_each_format_error_raises_with_lineno(mutate, expect):
    bad = mutate(SAMPLE)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    msg = str(ei.value)
    assert expect in msg, msg
    assert re.match(r"^第 \d+ 行：", msg)


def test_bad_attr_line_never_lands_in_content_units():
    """F8 核心：屬性區塊內任何壞行不得靜默落入 content_units。"""
    bad = SAMPLE.replace("- sources: [kb:3585, kb:3602]", "- sources: [kb:3585, kb:3602]\n  - {text: \"漏網講法\", source: \"traffic:x\", status: approved}")
    with pytest.raises(CanonFormatError):
        parse_canon_text(bad)


# ---------------------------------------------------------------------------
# 與 hook 同值
# ---------------------------------------------------------------------------

def test_key_lists_and_regex_match_hook():
    hook = _hook_module()
    assert tuple(hook.FRONT_MATTER_KEYS) == FRONT_MATTER_KEYS
    assert tuple(hook.ATTR_KEYS) == ATTR_KEYS
    assert hook.FINE_ID_RE.pattern == FINE_ID_RE.pattern


def test_hook_structure_check_passes_on_sample(tmp_path):
    hook = _hook_module()
    p = tmp_path / "prospect.md"
    p.write_text(SAMPLE, encoding="utf-8")
    assert hook.check_structure(str(p)) == []


# ---------------------------------------------------------------------------
# verifier 2026-09-06 回歸鎖（REFUTED (a) P2：掉了 `  - ` 前綴的講法子項曾靜默落入 content_units）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_line", [
    '{text: "王先生問A7棟能不能先試用", source: "traffic:202609#7", status: approved}',  # 掉縮排＋破折號的 phrasing 子項
    "sources: [kb:9999]",                                                             # 掉破折號的屬性行
    "policy: deliberate_no",
])
def test_attr_shaped_line_without_dash_is_rejected_not_content(bad_line):
    bad = SAMPLE.replace("- instance_applicability: general\n金箍棒把物件", f"- instance_applicability: general\n{bad_line}\n金箍棒把物件")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "不落內容" in str(ei.value) or "屬性形狀" in str(ei.value)
    # 內容區之後出現同形狀也擋
    bad2 = SAMPLE.replace("想知道適不適合，先了解您管幾間。", f"想知道適不適合，先了解您管幾間。\n{bad_line}")
    with pytest.raises(CanonFormatError):
        parse_canon_text(bad2)


def test_phrasing_leak_check_ignores_inserted_whitespace():
    doc = parse_canon_text(SAMPLE)
    assert phrasing_leaks(doc, text="你們系統 適合我嗎") == ["prospect/A/positioning: 你們系統適合我嗎"]
    assert phrasing_leaks(doc, text="你們系統\u3000適合我　嗎") == ["prospect/A/positioning: 你們系統適合我嗎"]


def test_phrasing_leak_short_topic_terms_are_not_false_positives():
    """短主題詞（<5 字）是內容句的子字串屬正常，不算洩漏；整句相等仍抓。"""
    md = SAMPLE.replace('- phrasings:\n  - {text: "可以先試用嗎", source: "traffic:202609#1", status: approved}',
                        '- phrasings:\n  - {text: "可以先試用嗎", source: "traffic:202609#1", status: approved}\n  - {text: "試用", source: "question_summary:3596", status: proposed}')
    doc = parse_canon_text(md)
    assert phrasing_leaks(doc) == []  # 「試用」是「可先免費試用一個月。」的子字串，不算
    injected = md.replace("可先免費試用一個月。", "可先免費試用一個月。\n試用")
    assert phrasing_leaks(parse_canon_text(injected)) == ["prospect/A/trial: 試用"]  # 整句相等 ⇒ 抓


def test_phrasing_leak_long_sentence_contained_is_flagged():
    """≥10 字的講法（真流量原句形狀）被包在內容行裡也要抓。"""
    md = SAMPLE.replace('{text: "適不適合小房東", source: "koyu:03#12", status: proposed}',
                        '{text: "我管十間套房用你們系統合適嗎", source: "koyu:03#12", status: proposed}')
    doc = parse_canon_text(md)
    assert phrasing_leaks(doc, text="客戶問：我管十間套房用你們系統合適嗎？我們答…") == ["prospect/A/positioning: 我管十間套房用你們系統合適嗎"]
