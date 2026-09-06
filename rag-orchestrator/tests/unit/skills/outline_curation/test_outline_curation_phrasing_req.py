"""任務 2.2：phrasing_map.py（講法提案＋去識別）與 raw_purge.py（raw/ 保存期限）。

去識別是本任務的個資主面：**每一類都要有正例（必須被遮）與負例（必須不被遮）**——
只驗正例的掃描器等於沒驗，因為「全部都遮掉」也會全綠。
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.2")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SCHEMAS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _load(name):
    path = os.path.join(_SCRIPTS, f"{name}.py")
    if not os.path.exists(path):
        pytest.skip(f"{name}.py 不在掛載路徑")
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# 去識別：十一類（D3 十類；合約號／帳單號在 hook 是同一條 number_label）各一正一負
# ---------------------------------------------------------------------------

DEID_CASES = [
    # (類別, 必須被遮的句子, 必須不被遮的句子)
    ("person_name", "王先生說要換約", "請問老師怎麼收費"),                  # 負例：沒有姓氏錨點，只是稱謂
    ("address", "台北市中山區南京東路三段5號12樓", "台北市的房東多嗎"),      # 負例：有縣市但無路街巷弄＝不是門牌
    ("number_label", "合約編號12345要改", "編號規則說明"),                  # 負例：有「編號」但無 ≥4 位數字
    ("phone", "打 0912345678 給我", "租金 12000 元怎麼算"),                 # 負例：金額不是電話
    ("email", "寄到 a.b@example.com", "帳號設定在哪"),
    ("line_id", "加我 @jgbline123", "LINE 通知怎麼開"),
    ("tax_id", "統編 12345670 開發票", "20260906 之前要繳"),                # 負例：像日期的 8 位數
    ("room", "A棟1203室的租客", "個人房東 約10戶 方案"),                    # 負例：數字＋戶是規模量詞
    ("community", "我住在陽光社區", "整棟大樓都要管理嗎"),                  # 負例：泛稱不是專名
    ("plate", "車牌 ABC-1234", "停車位費用怎麼算"),
    ("amount_date", "繳了 12,000 元在 2026-09-06", "2026-09-06 到期"),      # 負例：只有日期沒有金額
]


@pytest.mark.parametrize("category,positive,negative", DEID_CASES, ids=[c[0] for c in DEID_CASES])
def test_deidentify_positive_and_negative(category, positive, negative):
    pm = _load("phrasing_map")
    out_p, counts_p = pm.deidentify(positive)
    assert counts_p.get(category), f"{category} 正例未被遮：{positive!r} → {out_p!r}（命中 {counts_p}）"
    assert pm.PLACEHOLDER[category] in out_p
    out_n, counts_n = pm.deidentify(negative)
    assert counts_n == {}, f"{category} 負例被誤殺：{negative!r} → {out_n!r}（命中 {counts_n}）"
    assert out_n == negative


def test_placeholder_only_text_is_dropped():
    pm = _load("phrasing_map")
    clean, _ = pm.deidentify("a.b@example.com")
    assert pm.is_only_placeholders(clean)
    assert not pm.is_only_placeholders("怎麼收費")


def test_identifier_regexes_are_the_hook_s_not_a_copy():
    """skill 與 hook 必須是同一把尺：七類 regex 物件同一份，⛔ 不得各自複製一版。"""
    pm = _load("phrasing_map")
    hook = pm._hook
    assert hook.EMAIL_RE is not None and hook.PHONE_RE is not None
    for name in ("EMAIL_RE", "PHONE_RE", "LINE_ID_RE", "TAX_ID_RE", "PLATE_RE", "NUMBER_LABEL_RE", "AMOUNT_DATE_RE"):
        assert hasattr(hook, name), f"hook 缺 {name}——上游改名了，本檔的 import 已失效"
    assert not hasattr(pm, "EMAIL_RE"), "phrasing_map 不得自己再定義一份 EMAIL_RE"


# ---------------------------------------------------------------------------
# 固定 fixture
# ---------------------------------------------------------------------------

FINES = [
    {"id": "prospect/A/positioning", "coarse_id": "A", "title": "系統定位與適用對象",
     "merge_of": ["tmp:kb:1"], "split_from": [], "moved_from": [], "reason": "r", "slug": "positioning"},
    {"id": "prospect/C/rent-collection", "coarse_id": "C", "title": "收租對帳",
     "merge_of": ["tmp:kb:2"], "split_from": [], "moved_from": [], "reason": "r", "slug": "rent-collection"},
    {"id": "prospect/D/trial", "coarse_id": "D", "title": "免費試用",
     "merge_of": ["tmp:draft:1"], "split_from": [], "moved_from": [], "reason": "r", "slug": "trial"},
]

KB_ROWS = {"rows": [
    {"kb_id": 1, "question_summary": "系統定位 適用對象 適不適合我 想了解", "answer": "a",
     "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"]},
    # 15 個詞 ⇒ 超過每細目上限 12
    {"kb_id": 2, "question_summary": "收租對帳 帳單自動 多元金流 金流代收 電子發票 儲值金額 逾期提醒 自動催繳 月結報表 報表匯出 帳單明細 對帳流程 繳費提醒 滯納金額 收據樣式",
     "answer": "b", "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"]},
]}

FROZEN_Q = "凍結題不得進索引"
KOYU = {"articles": {
    "art01": {"title": "t", "phrasings": [
        {"n": 1, "type": "直接", "q": "系統定位是什麼適用對象有哪些"},
        {"n": 2, "type": "操作", "q": "系統定位設定在哪個選單裡面點"},          # ⛔ 操作型不得進
        {"n": 3, "type": "邊界", "q": "系統定位以後會不會改成別的適用對象"},    # ⛔ 邊界型不得進
        {"n": 4, "type": "俗稱", "q": "  凍結題不得進索引  "},                  # 凍結題（前後空白）
        {"n": 5, "type": "口語", "q": "收租對帳"},
        {"n": 6, "type": "情境", "q": "收租 對帳"},                             # NFKC＋去空白後與 #5 同
        {"n": 7, "type": "口語", "q": "有問題寄到 a.b@example.com 給我 收租對帳的事"},
        {"n": 8, "type": "直接", "q": "颱風天要不要收衣服"},                    # 與任何細目都不像 ⇒ unassigned
    ]},
}}

HTML_TMPL = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>{title}</title></head><body><h1>{h1}</h1><p>內文</p></body></html>"""


def _fixtures(tmp_path):
    struct = tmp_path / "structure-proposal.json"
    struct.write_text(json.dumps({
        "step": "structure", "skill_version": "0.1.0", "inputs_sha": {}, "deterministic": False,
        "raw_outputs_path": None, "cost": {},
        "payload": {"proposals": [], "synthesis": {"angle": "synthesis", "coarses": [], "fines": FINES,
                                                   "id_map": [], "rejected_alternatives": []}},
    }, ensure_ascii=False), encoding="utf-8")

    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps(KB_ROWS, ensure_ascii=False), encoding="utf-8")

    koyu = tmp_path / "koyu.json"
    koyu.write_text(json.dumps(KOYU, ensure_ascii=False), encoding="utf-8")

    # 幫助中心目錄在容器內沒掛 ⇒ 一律自建 tmp 假目錄（扁平、*_zh-Hant.html）
    hc = tmp_path / "helpcenter"
    hc.mkdir(exist_ok=True)
    (hc / "rentflow01_zh-Hant.html").write_text(HTML_TMPL.format(title="收租對帳流程說明", h1="h1"), encoding="utf-8")
    (hc / "positioning02_zh-Hant.html").write_text(HTML_TMPL.format(title="系統定位與適用對象說明", h1="h1"), encoding="utf-8")
    (hc / "noise03_zh-Hant.html").write_text(HTML_TMPL.format(title="", h1="颱風天注意事項"), encoding="utf-8")
    (hc / "ignored_en.html").write_text(HTML_TMPL.format(title="English", h1="English"), encoding="utf-8")

    # 凍結題 manifest（set 的 path 相對 manifest 所在目錄解析）
    (tmp_path / "topics.json").write_text(
        json.dumps({"topics": [{"id": "T1", "phrasings": [{"q": FROZEN_Q}]}]}, ensure_ascii=False), encoding="utf-8")
    manifest = tmp_path / "samples-manifest.json"
    manifest.write_text(json.dumps({"sets": {
        "topics": {"available": True, "path": "topics.json"},
        "traffic": {"available": False, "path": None},
    }}, ensure_ascii=False), encoding="utf-8")

    return str(struct), str(kb), str(hc), str(koyu), str(manifest)


def _run(tmp_path, min_score=0.12, cap=12, out_name="phrasing-map.json", raw_name="raw"):
    pm = _load("phrasing_map")
    struct, kb, hc, koyu, manifest = _fixtures(tmp_path)
    raw_dir = str(tmp_path / raw_name)
    payload, raw = pm.build(struct, kb, hc, koyu, manifest, raw_dir, "2026-09-06T00:00:00Z",
                            min_score=min_score, cap=cap)
    pm.write_raw(raw_dir, raw)
    return pm, payload, raw, raw_dir


def _texts(payload, fine_id=None):
    return [p["text"] for p in payload["phrasings"] if fine_id is None or p["fine_id"] == fine_id]


# ---------------------------------------------------------------------------
# 掛載、排除、上限、去重
# ---------------------------------------------------------------------------

def test_question_summary_attaches_by_kb_id_not_by_score(tmp_path):
    _, payload, _, _ = _run(tmp_path)
    got = [p for p in payload["phrasings"] if p["source"] == "question_summary:1"]
    assert got, "question_summary 未掛上"
    assert {p["fine_id"] for p in got} == {"prospect/A/positioning"}, "應掛在 merge_of 含 tmp:kb:1 的細目"
    assert {p["text"] for p in got} == {"系統定位", "適用對象", "適不適合我", "想了解"}
    assert all(p["status"] == "proposed" for p in payload["phrasings"])


def test_frozen_questions_are_dropped_and_counted(tmp_path):
    _, payload, raw, _ = _run(tmp_path)
    assert FROZEN_Q not in _texts(payload)
    assert payload["counts"]["dropped_frozen"] >= 1
    assert payload["counts"]["frozen_questions"] == 1, "正對照：manifest 真的被讀到（不是 0 題空跑）"
    assert any(FROZEN_Q in c["text"] for c in raw["dropped_frozen"])


def test_koyu_operation_and_boundary_types_are_excluded(tmp_path):
    _, payload, raw, _ = _run(tmp_path)
    all_sources = {p["source"] for p in payload["phrasings"]} | {u["source"] for u in payload["unassigned"]}
    assert "koyu:art01#2" not in all_sources, "操作型不得進索引"
    assert "koyu:art01#3" not in all_sources, "邊界型不得進索引"
    assert "koyu:art01#1" in all_sources, "正對照：同一篇的直接型必須進得來"
    assert payload["counts"]["koyu_excluded_by_type"] == {"操作": 1, "邊界": 1}
    assert not any(c["source"] in ("koyu:art01#2", "koyu:art01#3") for c in raw["candidates"]), \
        "操作／邊界在列舉階段就排除，連 raw/ 也不落"


def test_min_term_chars_drops_two_char_topic_words(tmp_path):
    """2 字主題詞（「合約」）不成講法：MIN_TERM_CHARS=3。"""
    m = _load("phrasing_map")
    assert m.MIN_TERM_CHARS == 3


def test_cap_12_per_fine(tmp_path):
    _, payload, _, _ = _run(tmp_path)
    for fid in {p["fine_id"] for p in payload["phrasings"]}:
        assert len(_texts(payload, fid)) <= 12
    assert len(_texts(payload, "prospect/C/rent-collection")) == 12, "15 個詞應被砍到 12"
    assert payload["counts"]["dropped_over_cap"] >= 3


def test_nfkc_whitespace_dedupe(tmp_path):
    # 門檻放低，讓 koyu#5「收租對帳」與 #6「收租 對帳」都掛上同一細目，去重才有東西可去
    _, payload, _, _ = _run(tmp_path, min_score=0.05)
    norm = _load("phrasing_map").norm
    for fid in {p["fine_id"] for p in payload["phrasings"]}:
        keys = [norm(t) for t in _texts(payload, fid)]
        assert len(keys) == len(set(keys)), f"{fid} 有 NFKC＋去空白後重複的講法"
    assert payload["counts"]["dropped_duplicate"] >= 1, "正對照：fixture 內確實有一組只差空白的講法"


def test_below_threshold_goes_to_unassigned_not_forced_onto_a_fine(tmp_path):
    _, payload, _, _ = _run(tmp_path)
    un = {u["source"] for u in payload["unassigned"]}
    assert "koyu:art01#8" in un, "與任何細目都不像的候選應進待審，⛔ 不得硬掛"
    assert "koyu:art01#8" not in {p["source"] for p in payload["phrasings"]}
    for u in payload["unassigned"]:
        assert u["score"] < 0.12


def test_high_threshold_pushes_everything_scored_to_unassigned(tmp_path):
    """正對照：門檻拉到 1.01 後，靠分數掛的一筆都不該留下（by_kb_id 的不受影響）。"""
    _, payload, _, _ = _run(tmp_path, min_score=1.01)
    assert all(p["source"].startswith("question_summary:") for p in payload["phrasings"])
    assert payload["counts"]["unassigned"] > 0


def test_helpcenter_title_and_file_count(tmp_path):
    _, payload, _, _ = _run(tmp_path)
    assert payload["helpcenter_files"] == 3, "只數 *_zh-Hant.html，⛔ 不數 _en.html"
    srcs = {p["source"] for p in payload["phrasings"]} | {u["source"] for u in payload["unassigned"]}
    assert "helpcenter:rentflow01" in srcs
    assert "helpcenter:noise03" in srcs, "<title> 空時退回 <h1>"
    assert "helpcenter:ignored" not in srcs


# ---------------------------------------------------------------------------
# raw/ 與去識別的先後：原句只落 raw/，out 一個字元都不能有
# ---------------------------------------------------------------------------

def test_raw_holds_pre_deid_text_while_out_has_none(tmp_path):
    pm, payload, _, raw_dir = _run(tmp_path)
    out = tmp_path / "out.json"
    env = pm._env.make_envelope(step="phrasing", skill_version="0.1.0", inputs_sha={}, deterministic=True,
                                payload=payload, raw_outputs_path=raw_dir)
    pm._env.write_json(str(out), env)

    raw_text = (tmp_path / "raw" / "candidates-raw.json").read_text(encoding="utf-8")
    assert "a.b@example.com" in raw_text, "正對照：原句確實有進 raw/（否則下一行的『沒有』毫無意義）"
    assert "a.b@example.com" not in out.read_text(encoding="utf-8")
    assert any("〈EMAIL〉" in p["text"] for p in payload["phrasings"] + payload["unassigned"])
    assert payload["redaction_counts"].get("email") == 1


def test_raw_dir_under_runs_is_refused(tmp_path):
    pm = _load("phrasing_map")
    with pytest.raises(ValueError):
        pm.write_raw(str(tmp_path / "runs" / "phrasing-20260906"), {"candidates": [], "dropped_frozen": [],
                                                                    "dropped_deidentified": []})


# ---------------------------------------------------------------------------
# envelope／schema／逐位元決定性
# ---------------------------------------------------------------------------

def _cli(tmp_path, out_path, raw_name):
    struct, kb, hc, koyu, manifest = _fixtures(tmp_path)
    cmd = [sys.executable, os.path.join(_SCRIPTS, "phrasing_map.py"),
           "--structure", struct, "--kb-rows", kb, "--helpcenter-dir", hc, "--koyu", koyu,
           "--frozen-manifest", manifest, "--raw-dir", str(tmp_path / raw_name),
           "--frozen-at", "2026-09-06T00:00:00Z", "--out", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


def test_envelope_passes_schema(tmp_path):
    pm = _load("phrasing_map")
    out = tmp_path / "phrasing-map.json"
    _cli(tmp_path, str(out), "raw1")
    env = json.loads(out.read_text(encoding="utf-8"))
    assert env["step"] == "phrasing" and env["deterministic"] is True
    assert set(env["inputs_sha"]) == {"structure", "kb_rows", "koyu", "frozen_manifest", "helpcenter_dir"}
    schema = pm._env.load_schema(os.path.join(_SCHEMAS, "phrasing-map.json"))
    pm._env.validate(env, schema)
    assert env["payload"]["similar_pairs"] == [], "步 3 的相似對由 similar_items.py 填"


def test_byte_identical_on_rerun(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _cli(tmp_path, str(a), "raw1")          # 同一組輸入（含同一個 --raw-dir）跑兩次
    _cli(tmp_path, str(b), "raw1")
    assert a.read_bytes() == b.read_bytes()


# ---------------------------------------------------------------------------
# raw_purge.py
# ---------------------------------------------------------------------------

def test_raw_purge_dry_run_then_apply(tmp_path):
    rp = _load("raw_purge")
    import datetime
    raw = tmp_path / "raw"
    (raw / "phrasing-20260101").mkdir(parents=True)
    (raw / "phrasing-20260101" / "candidates-raw.json").write_text("{}", encoding="utf-8")
    (raw / "phrasing-2026-09-06").mkdir()
    (raw / "trial-20260906.json").write_text("{}", encoding="utf-8")
    (raw / "no-date-here.json").write_text("{}", encoding="utf-8")

    today = datetime.date(2026, 9, 6)
    doomed, kept = rp.plan(str(raw), today, days=90)
    doomed_names = {os.path.basename(p) for p, _, _ in doomed}
    kept_names = {os.path.basename(p) for p, _, _ in kept}
    assert doomed_names == {"phrasing-20260101"}
    assert {"phrasing-2026-09-06", "trial-20260906.json", "no-date-here.json"} <= kept_names
    assert (raw / "phrasing-20260101").exists(), "乾跑 ⛔ 不得刪任何東西"

    assert rp.apply_plan(doomed) == 1
    assert not (raw / "phrasing-20260101").exists()
    assert (raw / "no-date-here.json").exists(), "名稱無日期者永遠不動"
    assert (raw / "phrasing-2026-09-06").exists()


def test_raw_purge_parse_date_in_name():
    rp = _load("raw_purge")
    import datetime
    assert rp.parse_date_in_name("phrasing-20260906") == datetime.date(2026, 9, 6)
    assert rp.parse_date_in_name("phrasing-2026-09-06") == datetime.date(2026, 9, 6)
    assert rp.parse_date_in_name("structure-proposal.json") is None
    assert rp.parse_date_in_name("run-20261332") is None, "非法月日 ⇒ 不當日期（⛔ 不猜）"



# ---------------------------------------------------------------------------
# verifier 2026-09-06 回歸鎖（REFUTED (a) P2：全形數字／全形 ＠／號碼中間空白曾原樣進 --out）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dirty, category", [
    ("聯絡０９１２３４５６７８", "phone"),          # 全形數字
    ("寫信到 abc＠example.com", "email"),          # 全形 ＠
    ("請撥 0912 345 678 找我", "phone"),           # 號碼中間空白
    ("請撥 0912-345-678 找我", "phone"),           # 號碼中間連字號
])
def test_deidentify_sees_through_fullwidth_and_spaced_numbers(dirty, category):
    m = _load("phrasing_map")
    out, counts = m.deidentify(dirty)
    assert counts.get(category, 0) >= 1, (out, counts)
    assert "0912" not in out and "０９１２" not in out and "example.com" not in out and "＠" not in out


def test_norm_folds_trailing_punctuation_for_frozen_match():
    m = _load("phrasing_map")
    assert m.norm("簽約邀請有時效嗎？") == m.norm("簽約邀請有時效嗎") == m.norm("簽約邀請有時效嗎 ?")
    assert m.norm("A。B。") != m.norm("AB")  # 只折句尾，不折句中


# ---------------------------------------------------------------------------
# F12（completeness audit）：--koyu 選填，換受眾無問法正本時可省略
# ---------------------------------------------------------------------------

def test_koyu_optional_when_omitted_source_is_skipped(tmp_path):
    struct, kb, hc, koyu, manifest = _fixtures(tmp_path)
    out = tmp_path / "phrasing-map-no-koyu.json"
    cmd = [sys.executable, os.path.join(_SCRIPTS, "phrasing_map.py"),
           "--structure", struct, "--kb-rows", kb, "--helpcenter-dir", hc,
           "--frozen-manifest", manifest, "--raw-dir", str(tmp_path / "raw-no-koyu"),
           "--frozen-at", "2026-09-06T00:00:00Z", "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    env = json.loads(out.read_text(encoding="utf-8"))
    assert env["inputs_sha"]["koyu"] is None
    payload = env["payload"]
    assert payload["counts"]["candidates_koyu"] == 0
    assert payload["counts"]["koyu_excluded_by_type"] == {}
    assert not any(str(p["source"]).startswith("koyu:") for p in payload["phrasings"])
    assert not any(str(u["source"]).startswith("koyu:") for u in payload["unassigned"])
