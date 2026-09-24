"""unit：`services/agent/canon/canon_parser.py`（spec knowledge-outline-and-intent-architecture 任務 2.1；需求 2.1, 2.3, 2.5, 2.8, 7.3）。

覆蓋：
- 固定樣本往返決定性（兩次解析逐位元相同 dict／sha；export_json 兩次逐位元相同）。
- content_units 對 provenance_units 切法恆等；一行多句必紅。
- 講法零字元進可引用文字：`phrasing_leaks(doc)` 為空；正對照——把一句講法塞進內容行 ⇒ 必紅。
- 屬性區塊任何壞行 raise CanonFormatError（列號＋原因），⛔ 不落 content_units：每種格式錯各一案。
- traffic 講法 ≤20 字且不含 ≥4 位數字串。
- 鍵清單與正則與 hook `outline_gate.py` 同值（兩邊只准一致）。
- target_user 值域（任務 9.1a）：front matter／細目兩處各一案值域外必紅（含錯字）、`all_users` 必紅（DSP-052，正本禁用）。
- see_also 目標必須是本正本內存在的細目 id，否則必紅；正對照——既有兩份真實正本仍可 parse。
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

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # rag-orchestrator/
CANON_DIR = os.path.join(_RAG, "canon")
#: 版控正本＝**一個目錄九架**（DSP-058／9.6 S3）。⚠️ 舊的 `canon/*.md` 兩份受眾正本已封存到
#: `docs/archive/2026-09/canon-pre-library/`，故這裡 ⛔ 不再 glob `canon/*.md`（那會變成空清單、
#: 底下的參數化案靜默全綠）。
CANON_SHELVES = os.path.join(CANON_DIR, "jgb")

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.1")]

SAMPLE = """---
audience: prospect
version: 2026-09-06.1
reviewers: [owner]
language: zh-TW
budget_tokens: 10000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品基本盤 {#A}
### 系統定位與適用對象 {#prospect/A/positioning}
- phrasings:
  - {text: "你們系統適合我嗎", source: "question_summary:3585", status: approved}
  - {text: "適不適合小房東", source: "koyu:03#12", status: proposed}
- sources: [kb:3585, kb:3602]
- reviewed: {by: owner, at: 2026-09-06}
- see_also: [prospect/G/custom-dev]
- instance_applicability: general
金箍棒把物件、合約、收租集中在一個系統管理。
想知道適不適合，先了解您管幾間。

### 免費試用 {#prospect/A/trial}
- phrasings:
  - {text: "可以先試用嗎", source: "traffic:202609#1", status: approved}
- sources: [kb:3596]
- instance_applicability: general
- target_user: [prospect, property_manager]
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
    assert pos.reviewed_by == "owner" and pos.reviewed_at == "2026-09-06" and pos.see_also == ("prospect/G/custom-dev",)
    assert [p.status for p in pos.phrasings] == ["approved", "proposed"]
    assert pos.content_units == ("金箍棒把物件、合約、收租集中在一個系統管理。", "想知道適不適合，先了解您管幾間。")
    assert pos.target_user == ("prospect",) and pos.business_types == ("system_provider",)  # front matter 預設
    assert fines[1].target_user == ("prospect", "property_manager")  # 細目覆寫
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


# ---------------------------------------------------------------------------
# target_user 值域（任務 9.1a：DSP-053）
# ---------------------------------------------------------------------------

def test_target_user_front_matter_out_of_domain_rejected():
    bad = SAMPLE.replace("target_user: [prospect]", "target_user: [social_housing]")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "target_user 值不在允許集合" in str(ei.value) and "'social_housing'" in str(ei.value)


def test_target_user_front_matter_typo_rejected():
    bad = SAMPLE.replace("target_user: [prospect]", "target_user: [sociaal_housing]")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "target_user 值不在允許集合" in str(ei.value)


def test_target_user_landlord_is_out_of_domain_rejected():
    """DSP-061：`landlord` 不在 `KNOWN_TARGET_USERS` ⇒ front matter 與細目兩處都必紅。

    ⚠️ 正對照＝同一份 SAMPLE 不動時可解析（`test_roundtrip_deterministic` 等），
    否則這條只是因為整份 SAMPLE 壞掉而綠。
    """
    bad_fm = SAMPLE.replace("target_user: [prospect]", "target_user: [landlord]", 1)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad_fm)
    assert "target_user 值不在允許集合" in str(ei.value) and "'landlord'" in str(ei.value)

    bad_fine = SAMPLE.replace(
        "- target_user: [prospect, property_manager]", "- target_user: [prospect, landlord]", 1)
    with pytest.raises(CanonFormatError) as ei2:
        parse_canon_text(bad_fine)
    assert "'landlord'" in str(ei2.value)


def test_target_user_fine_out_of_domain_rejected():
    bad = SAMPLE.replace("- target_user: [prospect, property_manager]", "- target_user: [prospect, social_housing]")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "target_user 值不在允許集合" in str(ei.value) and "'social_housing'" in str(ei.value)


def test_target_user_fine_typo_rejected():
    bad = SAMPLE.replace("- target_user: [prospect, property_manager]", "- target_user: [sociaal_housing]")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "target_user 值不在允許集合" in str(ei.value)


def test_target_user_all_users_is_rejected_in_canon():
    """DSP-052：正本 ⛔ 不用 `all_users` 表中立——b2b 分支不放行會變半可見；中立寫空清單。"""
    bad = SAMPLE.replace("- target_user: [prospect, property_manager]", "- target_user: [all_users]", 1)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "all_users" in str(ei.value)
    bad_fm = SAMPLE.replace("target_user: [prospect]", "target_user: [all_users]", 1)
    with pytest.raises(CanonFormatError):
        parse_canon_text(bad_fm)


def test_see_also_dead_id_is_rejected():
    """任務 9.1a：`see_also` 目標不存在 ⇒ 大聲失敗（比照「細目 id 重複」）；正對照＝原 SAMPLE 的 see_also 可過。"""
    parse_canon_text(SAMPLE)  # 正對照：see_also: [prospect/G/custom-dev] 存在，必綠
    bad = SAMPLE.replace("- see_also: [prospect/G/custom-dev]", "- see_also: [prospect/Q/does-not-exist]", 1)
    assert bad != SAMPLE
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "see_also" in str(ei.value)


def test_real_canon_files_are_discovered():
    """正對照的正對照：找不到真實正本＝路徑壞了，⛔ 不得讓下面的案靜默變零。"""
    assert os.path.isdir(CANON_SHELVES), CANON_SHELVES
    shelves = sorted(f for f in os.listdir(CANON_SHELVES) if len(f) == 4 and f.endswith(".md"))
    assert len(shelves) == 9, shelves


def test_real_canon_still_parses_under_9_1a_and_9_6_checks():
    """9.1a 兩條（target_user 值域／see_also 目標存在）＋9.6 S3 兩條（架 title 對齊、
    跨架講法唯一）對**現行版控正本**必須零誤殺。

    計畫 9.10 S1 起粗目 id 可為 `<架字母>-<slug>`（⛔ 不再是裸字母），`[c.id for c in
    doc.coarses] == list("ABCDEFGHI")` 這條斷言假設的是舊形態。改為兩條不假設粗目
    id 形狀的不變量：①九個架字母（由粗目 id 首字母取得）齊全且恰為 A–I；②每個
    粗目 id 首字母＝所在架（parser 本身在 S1 已強制，這裡是外部再核一次，證明
    `parse_canon_dir` 真的把架與粗目綁對）。"""
    from services.agent.canon.canon_parser import parse_canon_dir as _parse_dir

    doc = _parse_dir(CANON_SHELVES)
    assert len(doc.fines()) > 0
    shelf_letters = sorted({c.id[0] for c in doc.coarses})
    assert shelf_letters == list("ABCDEFGHI"), shelf_letters
    for coarse in doc.coarses:
        for fine in coarse.fines:
            assert fine.id.split("/")[1] == coarse.id[0], (fine.id, coarse.id)


# ---------------------------------------------------------------------------
# 圖書館形態（DSP-058；計畫 9.6 S1）：parse_canon_dir／export_catalog
#
# 材料＝合成 fixture `tests/fixtures/canon_jgb/shelves/`（A/B/C 各 2 細目＝6 細目、
# D–I 空架、跨架 see_also、一條共用 [prospect, property_manager]）。
# ⚠️ 白名單是 A.md…I.md **九架全要在**，故「空架」在 fixture 裡有 6 個，H 只是其中之一。
# ⚠️ `expected.json` 由本實作導出 ⇒ 單靠它是套套邏輯；故每一案另有**獨立寫死**的期望值
#    （id 清單、target_user、跨架 see_also、scopes）與**另一條路徑算出的** canon_sha256。
# ---------------------------------------------------------------------------

import hashlib
import shutil

from services.agent.canon.canon_parser import (
    CANON_NAME, SHELF_DERIVED_OK, SHELF_FILES, SHELF_FRONT_MATTER_KEYS,
    export_catalog, parse_canon_dir,
)

_FIXTURE_ROOT = os.path.join(_RAG, "tests", "fixtures", "canon_jgb")
_FIXTURE_SHELVES = os.path.join(_FIXTURE_ROOT, "shelves")

_EXPECTED_FINE_IDS = [
    "jgb/A/account-registration", "jgb/A/password-reset",
    "jgb/B/team-invite", "jgb/B/landlord-record",
    "jgb/C/estate-import", "jgb/C/community-setup",
]
_EXPECTED_TARGET_USER = {
    "jgb/A/account-registration": ("prospect", "property_manager"),
    "jgb/A/password-reset": ("property_manager",),
    "jgb/B/team-invite": ("property_manager",),
    "jgb/B/landlord-record": ("property_manager",),
    "jgb/C/estate-import": ("prospect",),
    "jgb/C/community-setup": ("prospect",),
}


def _shelves_copy(tmp_path, name="jgb"):
    dst = tmp_path / name
    shutil.copytree(_FIXTURE_SHELVES, dst)
    return dst


def _patch_shelf(dst, shelf, old, new):
    p = dst / shelf
    text = p.read_text(encoding="utf-8")
    assert old in text, f"fixture 已變，{shelf} 找不到 {old!r}"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# --- ① fixture ＝預期 ---------------------------------------------------------

def test_parse_canon_dir_matches_expected_json():
    doc = parse_canon_dir(_FIXTURE_SHELVES)
    with open(os.path.join(_FIXTURE_ROOT, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    # 走 JSON 一趟再比：`to_dict` 的 tuple 在 JSON 是 list，逐位元比對的是導出結果而非記憶體型別。
    assert json.loads(json.dumps(to_dict(doc), ensure_ascii=False, sort_keys=True)) == expected

    # 獨立寫死的期望值（⛔ 不靠 expected.json）
    assert doc.name == CANON_NAME and doc.audience == CANON_NAME
    assert doc.budget_tokens == 0 and doc.target_user == () and doc.business_types == ()
    # 計畫 9.10 S1 起粗目 id 恆為 `<架字母>-<slug>`（⛔ 不再是裸字母，S5／DSP-070 停用）：
    # fixture 九架各一個粗目，slug 見 tests/fixtures/canon_jgb/shelves/*.md。
    assert [c.id for c in doc.coarses] == [
        "A-account", "B-team", "C-community", "D-lease", "E-billing",
        "F-repair", "G-device", "H-help", "I-plan",
    ]
    assert [f.id for f in doc.fines()] == _EXPECTED_FINE_IDS
    assert {f.id: f.target_user for f in doc.fines()} == _EXPECTED_TARGET_USER
    assert all(f.business_types == ("system_provider",) for f in doc.fines())
    # 跨架 see_also：A 指到 C、C 指回 A（單檔路徑做不到）
    sa = {f.id: f.see_also for f in doc.fines() if f.see_also}
    assert sa == {
        "jgb/A/account-registration": ("jgb/C/estate-import",),
        "jgb/C/estate-import": ("jgb/A/account-registration",),
    }
    assert [cid for cid, _scope in doc.scopes] == list("ABCDEFGHI")
    assert all(scope.strip() for _cid, scope in doc.scopes)
    # 空架：H 有粗目、零細目（正對照：A 有 2 條）
    by_id = {c.id: c for c in doc.coarses}
    assert by_id["H-help"].fines == () and len(by_id["A-account"].fines) == 2

    # canon_sha256 由**另一條路徑**重算：九架全文 sha 依字母序串接再 sha
    digest = hashlib.sha256("\n".join(
        hashlib.sha256(open(os.path.join(_FIXTURE_SHELVES, f), "rb").read()).hexdigest()
        for f in SHELF_FILES
    ).encode("utf-8")).hexdigest()
    assert doc.canon_sha256 == digest


def test_parse_canon_dir_is_deterministic():
    assert to_dict(parse_canon_dir(_FIXTURE_SHELVES)) == to_dict(parse_canon_dir(_FIXTURE_SHELVES))


def test_shelf_sha_changes_when_any_shelf_changes(tmp_path):
    """正對照：動任何一架一個字，canon_sha256 就變（證明它真的涵蓋九架、不是只看 A）。"""
    base = parse_canon_dir(_FIXTURE_SHELVES).canon_sha256
    dst = _shelves_copy(tmp_path)
    assert parse_canon_dir(str(dst)).canon_sha256 == base
    _patch_shelf(dst, "I.md", "方案與導入 {#I-plan}", "方案與導入  {#I-plan}")
    assert parse_canon_dir(str(dst)).canon_sha256 != base


# --- ② 細目兩屬性必填（含正對照）--------------------------------------------

@pytest.mark.parametrize("old, new, expect", [
    ("- target_user: [property_manager]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "缺必填屬性 target_user"),
    ("- target_user: [property_manager]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "- target_user: []\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "缺必填屬性 target_user"),
    ("- target_user: [property_manager]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "- target_user: [all_users]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "target_user 值不在允許集合"),
    ("- target_user: [property_manager]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "- target_user: [property_manager]\n- instance_applicability: general\n忘記密碼",
     "缺必填屬性 business_types"),
    ("- target_user: [property_manager]\n- business_types: [system_provider]\n- instance_applicability: general\n忘記密碼",
     "- target_user: [property_manager]\n- business_types: [b2c_vendor]\n- instance_applicability: general\n忘記密碼",
     "須含 'system_provider'"),
])
def test_shelf_fine_required_attrs(tmp_path, old, new, expect):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", old, new)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    msg = str(ei.value)
    assert expect in msg, msg
    assert "A.md" in msg and "jgb/A/password-reset" in msg or "target_user 值不在" in msg, msg


def test_shelf_fine_required_attrs_positive_control():
    """正對照：同一份 fixture 未動時六條細目全部通過（證明上面五案的紅不是整個 fixture 壞掉）。"""
    assert len(parse_canon_dir(_FIXTURE_SHELVES).fines()) == 6


def test_single_file_path_keeps_file_level_defaults():
    """正對照（相容性）：單檔路徑**不**套必填規則——細目不寫兩屬性仍繼承檔級預設。"""
    doc = parse_canon_text(SAMPLE)
    assert doc.fines()[0].target_user == ("prospect",) and doc.fines()[0].business_types == ("system_provider",)


# --- ③④ 粗目碼與一檔一粗目 ---------------------------------------------------

def test_shelf_coarse_key_must_match_filename(tmp_path):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "B.md", "coarse: B", "coarse: C")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "與檔名字母 'B' 不符" in str(ei.value), str(ei.value)


def test_shelf_heading_code_must_match_filename(tmp_path):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "B.md", "{#B-team}", "{#C-team}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "不符" in str(ei.value) and "B.md" in str(ei.value), str(ei.value)


def test_shelf_duplicate_coarse_id_within_file_is_rejected(tmp_path):
    """一架內兩個粗目同 id（`_parse_body` 的檔內 seen_coarse，計畫 9.10 S1 允許一架多粗目後
    仍不得同 id 重複）。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "H.md", "## 幫助中心 {#H-help}", "## 幫助中心 {#H-help}\n## 另一個粗目 {#H-help}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "H.md" in str(ei.value) and "粗目碼重複" in str(ei.value), str(ei.value)


def test_shelf_zero_coarse_is_rejected(tmp_path):
    """計畫 9.10 S1 不變量①：每架至少一個粗目（負對照）。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "H.md", "## 幫助中心 {#H-help}\n", "")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "架至少須有一個粗目" in str(ei.value), str(ei.value)


# --- 計畫 9.10 S1：一架多粗目（新形態）--------------------------------------

def test_shelf_multi_coarse_new_shape_parses(tmp_path):
    """正對照＋新形狀：一架兩個 `<字母>-<slug>` 粗目，細目各自歸位正確。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(
        dst, "A.md",
        "## 帳號與身分 {#A-account}\n### 怎麼註冊帳號 {#jgb/A/account-registration}",
        "## 註冊帳號 {#A-account-registration}\n### 怎麼註冊帳號 {#jgb/A/account-registration}",
    )
    _patch_shelf(
        dst, "A.md",
        "### 忘記密碼怎麼辦 {#jgb/A/password-reset}",
        "## 登入 {#A-login}\n### 忘記密碼怎麼辦 {#jgb/A/password-reset}",
    )
    doc = parse_canon_dir(str(dst))
    by_id = {c.id: c for c in doc.coarses}
    assert set(by_id) >= {"A-account-registration", "A-login"}
    assert [f.id for f in by_id["A-account-registration"].fines] == ["jgb/A/account-registration"]
    assert [f.id for f in by_id["A-login"].fines] == ["jgb/A/password-reset"]
    assert dict(doc.shelf_titles)["A"] == "帳號與身分"


def test_shelf_coarse_id_first_letter_must_match_shelf(tmp_path):
    """負對照①：粗目 id 首字母≠架字母。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "## 帳號與身分 {#A-account}", "## 帳號與身分 {#B-account}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "首字母與檔名字母 'A' 不符" in str(ei.value), str(ei.value)


def test_shelf_coarse_id_unique_across_shelves(tmp_path):
    """負對照②：粗目 id 跨架重複——A 架合法宣告 `A-shared`，B 架撞同一個 id（B 檔的第一個粗目，
    未及檢查自己的首字母就先被跨架重複攔下，證明檢查順序真的是③先於②）。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "## 帳號與身分 {#A-account}", "## 帳號與身分 {#A-shared}")
    _patch_shelf(dst, "B.md", "## 團隊、人員與大房東 {#B-team}", "## 團隊、人員與大房東 {#A-shared}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "粗目 id 跨架重複 'A-shared'（首見於 A.md）" in str(ei.value), str(ei.value)


def test_fine_id_middle_segment_must_match_shelf_letter(tmp_path):
    """負對照④：細目 id 中段≠架字母（`{#jgb/B/...}` 寫在 A.md）。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "{#jgb/A/account-registration}", "{#jgb/B/account-registration}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "細目 id 中段 'B' 與所在架 'A' 不符" in str(ei.value), str(ei.value)


def test_malformed_coarse_slug_is_rejected(tmp_path):
    """負對照⑤：粗目 id 大小寫或 slug 不合法 ⇒ SHELF_COARSE_HEADING_RE 不匹配、也不是裸字母
    形態 ⇒ 整行落入「標題行無法解析」。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "## 帳號與身分 {#A-account}", "## 帳號與身分 {#a-account}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "標題行無法解析" in str(ei.value), str(ei.value)


def test_new_shape_shelf_skips_fm_title_equality_check(tmp_path):
    """新形態下 fm title 不必等於任何 `## 標題`（唯一來源是 front matter）——計畫 9.10 S5／
    DSP-070 後這是**唯一**形態，不再需要「新舊分流」的前提，⛔ 無任何 fm-title 相等檢查。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(
        dst, "A.md",
        "## 帳號與身分 {#A-account}\n### 怎麼註冊帳號 {#jgb/A/account-registration}",
        "## 註冊帳號 {#A-account-registration}\n### 怎麼註冊帳號 {#jgb/A/account-registration}",
    )
    _patch_shelf(dst, "A.md", "title: 帳號與身分", "title: 帳號與身分（改名不必等於任何 ## 標題）")
    doc = parse_canon_dir(str(dst))
    assert dict(doc.shelf_titles)["A"] == "帳號與身分（改名不必等於任何 ## 標題）"


# --- 計畫 9.10 S5／DSP-070：目錄路徑裸字母粗目整條移除 -----------------------

def test_shelf_bare_coarse_id_is_rejected_with_disabled_message(tmp_path):
    """驗收第一條（負對照）：裸字母架檔送 `parse_canon_dir` ⇒ 解析失敗，訊息逐字含停用聲明。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "## 帳號與身分 {#A-account}", "## 帳號與身分 {#A}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "粗目 id 須為 `<架字母>-<slug>`，裸字母形態已於 DSP-067／S5 停用" in str(ei.value), str(ei.value)


def test_generic_heading_hint_shows_new_shape_example():
    """泛用「標題行無法解析」提示的 `{#X}` 範例已改成新形狀，⛔ 不再示範被停用的寫法。"""
    bad = SAMPLE.replace("## G 現有不足 {#G}", "## G 現有不足")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_text(bad)
    assert "{#<架字母>-<slug>}" in str(ei.value), str(ei.value)


def test_export_functions_reject_bare_coarse_id_defense_in_depth(tmp_path):
    """拒絕負對照（三條之二）：`export_json`／`export_catalog` 各自對裸字母粗目 raise，
    訊息點名該粗目 id（計畫 9.10 S5 item 7c，防線二——`parse_canon_dir` 本身已在解析階段
    擋住裸字母，正常情況下走不到這裡；這裡用單檔路徑 `parse_canon_text` 造出一份裸字母
    coarse 的 doc，再手動標成目錄路徑（`dataclasses.replace(..., library=True)`）模擬
    「萬一裸字母繞過 parser」的情境）。

    正對照：單檔路徑（`library=False`，即 `parse_canon_text` 的原生輸出）完全不受影響，
    `export_json` 對 SAMPLE 仍成功——單檔路徑的裸字母是既有、未變的合法形態。
    mutation：拿掉 `_reject_bare_coarse_ids` 的呼叫，本測試前兩個 `pytest.raises` 區塊即紅。
    """
    import dataclasses

    bare_doc = parse_canon_text(SAMPLE)  # SAMPLE 的粗目 "A"／"G" 皆為裸字母
    assert any(len(c.id) == 1 for c in bare_doc.coarses)

    library_shaped = dataclasses.replace(bare_doc, library=True)
    with pytest.raises(CanonFormatError, match="裸字母"):
        export_json(library_shaped, str(tmp_path / "x.json"))
    with pytest.raises(CanonFormatError, match="裸字母"):
        from services.agent.canon.canon_parser import export_catalog as _export_catalog
        _export_catalog(library_shaped, str(tmp_path / "x.md"))

    # 正對照：單檔路徑（library=False）完全不受影響
    out = str(tmp_path / "single_file.json")
    assert export_json(bare_doc, out) == bare_doc.canon_sha256


def test_load_canon_or_die_rejects_synthetic_bare_nine_shelf_dir(tmp_path):
    """拒絕負對照（三條之三）：合成裸字母九架目錄送 `load_canon_or_die` ⇒ raise
    （經 `parse_canon_dir` 本身的偵測擋住，`load_canon_or_die` 不需要另一層檢查）。
    """
    import shutil

    from services.agent.canon.canon_assembler import load_canon_or_die

    base = tmp_path / "canon_root"
    shelf_dir = base / CANON_NAME
    shutil.copytree(_FIXTURE_SHELVES, shelf_dir)
    _patch_shelf(shelf_dir, "A.md", "## 帳號與身分 {#A-account}", "## 帳號與身分 {#A}")
    # `load_canon_or_die` 先要求 jgb.json／CATALOG.md 存在才會走到解析——用既有 fixture 的
    # 衍生物佔位即可（同源比對會先被裸字母的 parse 失敗擋下，不會走到那一步）。
    (base / f"{CANON_NAME}.json").write_text("{}", encoding="utf-8")
    (shelf_dir / "CATALOG.md").write_text("", encoding="utf-8")
    with pytest.raises(Exception) as ei:
        load_canon_or_die(str(base))
    assert "裸字母" in str(ei.value) or "DSP-067" in str(ei.value), str(ei.value)


# --- ⑤ 白名單外 .md（正對照：README.md 不 raise）------------------------------

def test_extra_md_outside_whitelist_is_rejected(tmp_path):
    dst = _shelves_copy(tmp_path)
    (dst / "Z.md").write_text("---\n---\n", encoding="utf-8")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "白名單外的 .md" in str(ei.value) and "Z.md" in str(ei.value), str(ei.value)


@pytest.mark.parametrize("name", SHELF_DERIVED_OK)
def test_derived_md_is_allowed(tmp_path, name):
    """正對照：衍生物（CATALOG.md／README.md）與九架共存時仍解析成功、且**不被當正本讀**。"""
    dst = _shelves_copy(tmp_path)
    (dst / name).write_text("這是衍生物，⛔ 不是正本。\n", encoding="utf-8")
    doc = parse_canon_dir(str(dst))
    assert [f.id for f in doc.fines()] == _EXPECTED_FINE_IDS


def test_missing_shelf_is_rejected(tmp_path):
    dst = _shelves_copy(tmp_path)
    os.remove(dst / "H.md")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "缺架 H.md" in str(ei.value), str(ei.value)


# --- ⑥ 符號連結 --------------------------------------------------------------

def test_symlinked_shelf_is_rejected(tmp_path):
    dst = _shelves_copy(tmp_path)
    outside = tmp_path / "outside.md"
    shutil.copyfile(dst / "H.md", outside)
    os.remove(dst / "H.md")
    os.symlink(outside, dst / "H.md")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "符號連結" in str(ei.value), str(ei.value)


def test_symlinked_shelf_pointing_inside_is_also_rejected(tmp_path):
    """⛔ 連指向目錄內部的連結也拒——白名單的意義是「這九個檔就是全部內容」。"""
    dst = _shelves_copy(tmp_path)
    os.remove(dst / "H.md")
    os.symlink(dst / "I.md", dst / "H.md")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "符號連結" in str(ei.value), str(ei.value)


# --- ⑦ 細目 id 首段 ----------------------------------------------------------

def test_fine_id_prefix_must_be_canon_name(tmp_path):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "{#jgb/A/password-reset}", "{#prospect/A/password-reset}")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "首段 'prospect' 與正本名 'jgb' 不符" in str(ei.value), str(ei.value)


def test_cross_shelf_see_also_dead_id_is_rejected(tmp_path):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "A.md", "- see_also: [jgb/C/estate-import]", "- see_also: [jgb/C/no-such-thing]")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "see_also 目標不存在" in str(ei.value), str(ei.value)


# --- ⑧ export_catalog 決定性 --------------------------------------------------

def test_export_catalog_is_byte_deterministic(tmp_path):
    doc = parse_canon_dir(_FIXTURE_SHELVES)
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    export_catalog(doc, str(a))
    export_catalog(parse_canon_dir(_FIXTURE_SHELVES), str(b))
    assert a.read_bytes() == b.read_bytes() and len(a.read_bytes()) > 100

    text = a.read_text(encoding="utf-8")
    assert "## A 帳號與身分 {#A}" in text
    assert "scope: 註冊、登入" in text
    assert "### A-account 帳號與身分 {#A-account}" in text
    # 每細目一行：id｜title｜target_user=…｜approved 講法（⛔ 不含 content_units）
    assert "jgb/A/account-registration｜怎麼註冊帳號｜target_user=prospect,property_manager｜怎麼註冊帳號" in text
    assert "註冊後系統會寄出驗證碼通知。" not in text, "CATALOG ⛔ 不得含內容句"
    assert "註冊要多久" not in text, "CATALOG 只含 approved 講法"
    # 行數＝9 架 ×(標題＋scope＋粗目行) ＋ 6 細目（計畫 9.10 S5：裸字母移除後每架恆有一行
    # `### <粗目 id> <粗目標題> {#<粗目 id>}`，不再與架標題合併成一行）＋ 8 個架間空行
    assert len([ln for ln in text.split("\n") if ln]) == 9 * 3 + 6


# --- ⑧b scope 缺／空（正對照：有 scope 通過）----------------------------------

@pytest.mark.parametrize("old, new, expect", [
    ("scope: 社區建檔、物件新增與批次匯入、刊登與銷售；⛔ 物件上的租約歸 D、抄表歸 E\n", "", "缺鍵：scope"),
    ("scope: 社區建檔、物件新增與批次匯入、刊登與銷售；⛔ 物件上的租約歸 D、抄表歸 E", "scope:   ", "scope 缺值"),
])
def test_shelf_scope_required(tmp_path, old, new, expect):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "C.md", old, new)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert expect in str(ei.value) and "C.md" in str(ei.value), str(ei.value)


@pytest.mark.parametrize("extra", ["budget_tokens: 12000", "audience: prospect"])
def test_shelf_front_matter_is_exactly_six_keys(tmp_path, extra):
    dst = _shelves_copy(tmp_path)
    _patch_shelf(dst, "C.md", "coarse: C", f"{extra}\ncoarse: C")
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert "不允許的鍵" in str(ei.value), str(ei.value)


@pytest.mark.parametrize("key", ["version", "reviewers", "language"])
def test_shelves_must_agree_on_version_reviewers_language(tmp_path, key):
    dst = _shelves_copy(tmp_path)
    repl = {"version": ("version: 2026-09-15.0", "version: 2026-09-16.0"),
            "reviewers": ("reviewers: [owner]", "reviewers: [someone]"),
            "language": ("language: zh-TW", "language: en-US")}[key]
    _patch_shelf(dst, "E.md", *repl)
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    assert f"{key} 與前面各架不一致" in str(ei.value), str(ei.value)


def test_missing_dir_fails_loudly(tmp_path):
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(tmp_path / "no-such-dir"))
    assert "不存在" in str(ei.value), str(ei.value)


# --- 導出相容性：單檔導出 ⛔ 不得多出 9.6 的新欄位 ------------------------------

def test_single_file_export_has_no_library_only_keys():
    """單檔導出逐位元相容：`name`／`scopes`／`library` 都不得出現（版控 JSON 靠這條不變）。"""
    d = to_dict(parse_canon_text(SAMPLE))
    assert "name" not in d and "scopes" not in d and "library" not in d
    # 正對照：目錄路徑有 name／scopes
    lib = to_dict(parse_canon_dir(_FIXTURE_SHELVES))
    assert lib["name"] == CANON_NAME and len(lib["scopes"]) == 9 and "library" not in lib


# --- ⑨ 9.6 S3：跨架講法唯一（含正對照）----------------------------------------
# ⚠️ 「架 title 對齊」（fm title 與架內 `## 標題` 相等）檢查已於計畫 9.10 S5／DSP-070
# 隨裸字母整條移除——新形態下架內本就沒有與架同名的 `##`，架標題唯一來源是 `shelf_titles`；
# 正對照見上方 test_new_shape_shelf_skips_fm_title_equality_check。


def test_phrasing_must_be_unique_across_shelves(tmp_path):
    """同一句 approved 講法掛在**兩架**的兩個細目 ⇒ raise（單檔路徑看不到這種重複）。"""
    dst = _shelves_copy(tmp_path)
    _patch_shelf(
        dst, "C.md",
        '  - {text: "批次匯入物件", source: "question_summary:3700", status: approved}',
        '  - {text: "批次匯入物件", source: "question_summary:3700", status: approved}\n'
        '  - {text: "怎麼註冊帳號", source: "question_summary:3585", status: proposed}',
    )
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(dst))
    msg = str(ei.value)
    assert "講法跨細目重複" in msg
    assert "jgb/A/account-registration" in msg and "jgb/C/estate-import" in msg, msg


def test_phrasing_uniqueness_positive_controls(tmp_path):
    """兩個正對照：① 未動的 fixture 通過（⛔ 不是恆紅）；② `retired` 同句 ⛔ 不算重複。"""
    assert len(parse_canon_dir(_FIXTURE_SHELVES).fines()) == 6
    dst = _shelves_copy(tmp_path)
    _patch_shelf(
        dst, "C.md",
        '  - {text: "批次匯入物件", source: "question_summary:3700", status: approved}',
        '  - {text: "批次匯入物件", source: "question_summary:3700", status: approved}\n'
        '  - {text: "怎麼註冊帳號", source: "question_summary:3585", status: retired}',
    )
    assert len(parse_canon_dir(str(dst)).fines()) == 6


# --- hook 同值（新常數）-------------------------------------------------------

def test_shelf_constants_match_hook():
    hook = _hook_module()
    assert hook.CANON_NAME == CANON_NAME
    assert tuple(hook.SHELF_FRONT_MATTER_KEYS) == SHELF_FRONT_MATTER_KEYS
    assert hook.FINE_ID_RE.pattern == FINE_ID_RE.pattern


def test_fine_without_sources_is_rejected(tmp_path):
    """定義 D6（2026-09-19）：每條細目每句都要可對回權威 ⇒ `sources` 必填非空，缺 ⇒ 大聲失敗。

    正對照＝同一份 fixture 目錄不動時 `parse_canon_dir` 通過；否則本條只是因 fixture 壞掉而綠。
    """
    import shutil
    from pathlib import Path
    from services.agent.canon.canon_parser import parse_canon_dir

    src = Path(__file__).resolve().parents[2] / "fixtures" / "canon_jgb" / "shelves"
    good = tmp_path / "good"
    shutil.copytree(src, good)
    doc = parse_canon_dir(str(good))
    assert doc.fines(), "正對照：fixture 目錄應可解析且有細目"

    bad = tmp_path / "bad"
    shutil.copytree(src, bad)
    stripped = False
    for shelf in sorted(bad.glob("[A-I].md")):
        text = shelf.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith("- sources:"):
                del lines[i]
                stripped = True
                break
        if stripped:
            shelf.write_text("".join(lines), encoding="utf-8")
            break
    assert stripped, "fixture 應至少有一條 `- sources:` 可移除"
    with pytest.raises(CanonFormatError) as ei:
        parse_canon_dir(str(bad))
    assert "sources" in str(ei.value)
