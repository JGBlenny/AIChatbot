"""unit：凍結語料重播 harness（spec retrieval-decision-layer 任務 1.1｜R1.1/1.2/1.3/1.4/1.7）。

契約：
- `classify_routing()` 五類別判定為決定性規則，且帶版本戳（規則內容變動必反映在戳上）；
- 前置閘門（容器一致性／語料完整性／快取軌別）任一未過即 abort，**不得降級續跑**；
- FORM 只認結構化證據——凍結語料舊檔沒有該欄位，重判時不得用文字猜。

判定矩陣的輸入句一律取自凍結語料 run2/run3 實際回應（不自造樣本，避免自出考卷）。
"""
import json
import os

import pytest

from scripts.backtest import decision_replay as dr

pytestmark = pytest.mark.unit


# ── 凍結語料實句（run2-head / run3-head 原文擷取）──
S_ASK_ID = "請提供帳單編號（bill_ref），以便查詢該帳單的狀態。"
S_ASK_ID_MULTI = "請提供帳單編號、合約編號或物件名稱，以便查詢帳單的狀態。"
S_FACET_EMPTY = "查無對應的資料，請再確認一下識別資訊（如編號或名稱）是否正確？"
S_FALLBACK = ("我目前沒有找到符合您問題的資訊，但我可以協助您轉給客服處理。"
              "請問您方便提供更詳細的內容嗎？")
S_ANSWER_KB = ("一物件多合約 上限10份\n\n一個物件最多可以綁定 10 份合約"
               "（含制式與上傳的既存合約）。")
S_ANSWER_VALUE = ("帳單「充洋-512」的資訊如下：\n\n- 狀態：已繳費\n- 金額：NT$ 140,047")
# #36：知識答案內含「請提供合約編號」——ASK_ID 的經典誤判陷阱
S_ANSWER_WITH_ASK_PHRASE = (
    "用租客姓名找合約 找某租客的租約 姓名反查合約編號\n\n"
    "智能助手目前無法直接用租客姓名反查合約編號，查詢合約資訊時請提供合約編號或物件名稱。"
    "若手邊只有租客姓名，可先到後台合約列表以租客姓名搜尋，找到對應合約後，"
    "再以該合約編號向助手查詢狀態或細節。")
S_CLARIFY = "請問您是否已經開通新的收款帳戶驗證？"


# ════════════════════════════════════════════════════════════
# R1.3：五類別判定矩陣
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.3")
@pytest.mark.parametrize("answer,expected", [
    (S_ASK_ID, "ASK_ID"),
    (S_ASK_ID_MULTI, "ASK_ID"),
    (S_FACET_EMPTY, "FACET_EMPTY"),
    (S_FALLBACK, "FALLBACK"),
    (S_ANSWER_KB, "ANSWER"),
    (S_ANSWER_VALUE, "ANSWER"),
    (S_CLARIFY, "ANSWER"),                 # 澄清問句歸 ANSWER（另以旗標記錄）
])
def test_classify_routing_matrix(answer, expected):
    cls, ver = dr.classify_routing(answer)
    assert cls == expected
    assert ver.startswith("rc-v1+")


# ── 陷阱①：知識答案裡提到「請提供合約編號」不得誤判 ASK_ID（#36 實句）──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_knowledge_answer_mentioning_ask_phrase_is_answer():
    cls, _ = dr.classify_routing(S_ANSWER_WITH_ASK_PHRASE,
                                 sources=["用租客姓名找合約"])
    assert cls == "ANSWER"
    # 即使來源欄漏空（舊檔），長度門檻仍擋得下
    cls2, _ = dr.classify_routing(S_ANSWER_WITH_ASK_PHRASE, sources=[])
    assert cls2 == "ANSWER"


# ── 陷阱②：短索取句帶 sources 時不算 ASK_ID（面向索取不會帶知識來源）──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_ask_id_requires_no_sources():
    assert dr.classify_routing(S_ASK_ID, sources=[])[0] == "ASK_ID"
    assert dr.classify_routing(S_ASK_ID, sources=["某知識"])[0] == "ANSWER"


# ── FORM 只認結構化證據；純文字不得猜出 FORM ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_form_requires_structured_evidence():
    assert dr.classify_routing("請填寫報修單：品項是什麼？")[0] != "FORM"
    assert dr.classify_routing("請填寫報修單：品項是什麼？",
                               form_triggered=True)[0] == "FORM"


# ── 呼叫失敗的輪不得被塞進五類別（會污染 E-5 不一致率）──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_error_turn_is_not_a_real_class():
    cls, _ = dr.classify_routing("", error="HTTP 500")
    assert cls == dr.CLASS_ERROR
    assert cls not in dr.ROUTING_CLASSES


# ── 判定順序：FACET_EMPTY／FALLBACK 標記優先於 ASK_ID 形態 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_marker_precedence_over_ask_id_shape():
    assert dr.classify_routing(S_FACET_EMPTY)[0] == "FACET_EMPTY"   # 句中含「編號」
    mixed = "我目前沒有找到符合您問題的資訊，請提供帳單編號。"
    assert dr.classify_routing(mixed)[0] == "FALLBACK"


# ── 空字串／None 一律 ANSWER 以外不臆造（防呆）──
@pytest.mark.req("retrieval-decision-layer:1.3")
@pytest.mark.parametrize("empty", ["", "   ", None])
def test_empty_answer_does_not_crash(empty):
    cls, ver = dr.classify_routing(empty)
    assert cls in dr.ROUTING_CLASSES and ver


# ════════════════════════════════════════════════════════════
# R1.3：版本戳——規則改了戳一定變
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.3")
def test_classifier_version_is_stable_and_content_derived(monkeypatch):
    before = dr.classifier_version()
    assert before == dr.classifier_version()                 # 同輸入穩定
    patched = dict(dr.ROUTING_RULES)
    patched["ask_id_max_len"] = 999
    monkeypatch.setattr(dr, "ROUTING_RULES", patched)
    assert dr.classifier_version() != before                 # 改規則→戳必變


@pytest.mark.req("retrieval-decision-layer:1.3")
def test_classifier_version_ignores_declared_version_only_change(monkeypatch):
    """只改宣告版本、規則內容不動 → 前綴變、雜湊不變（看得出是純升版）。"""
    base_digest = dr.classifier_version().split("+")[1]
    patched = dict(dr.ROUTING_RULES)
    patched["version"] = "rc-v2"
    monkeypatch.setattr(dr, "ROUTING_RULES", patched)
    v = dr.classifier_version()
    assert v.startswith("rc-v2+") and v.split("+")[1] == base_digest


# ── clarify 旗標：澄清問句標記，但不改類別 ──
@pytest.mark.req("retrieval-decision-layer:1.3")
def test_clarify_flag_marks_non_id_questions():
    assert dr.clarify_flag(S_CLARIFY) is True
    assert dr.clarify_flag(S_ASK_ID) is False                # 索取識別不算 clarify
    assert dr.clarify_flag(S_ANSWER_KB) is False
    assert dr.clarify_flag(S_ANSWER_WITH_ASK_PHRASE, ["kb"]) is False


# ════════════════════════════════════════════════════════════
# R1.2：容器一致性閘門——不變量 3 未過即 abort
# ════════════════════════════════════════════════════════════

_AUDIT_OK = """═══ 不變量 2：X ═══
✅ PASS

═══ 不變量 3：服務容器內關鍵檔案與本地一致 ═══
✅ PASS

═══ 不變量 4：Y ═══
⚠️  WARN：無關緊要
"""
_AUDIT_BAD3 = """═══ 不變量 3：服務容器內關鍵檔案與本地一致 ═══
❌ FAIL：routers/chat.py 容器與本地不一致（docker cp + restart，或重建 image）

═══ 不變量 4：Y ═══
✅ PASS
"""
# 不變量 3 過、別的不變量掛：不得因此擋掉評測（R1.2 只綁不變量 3）
_AUDIT_OTHER_FAIL = """═══ 不變量 1：Z ═══
❌ FAIL：與容器一致性無關

═══ 不變量 3：服務容器內關鍵檔案與本地一致 ═══
✅ PASS
"""


class _Res:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


@pytest.mark.req("retrieval-decision-layer:1.2")
def test_invariant3_pass_allows_run(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res(_AUDIT_OK))
    monkeypatch.setattr(dr, "AUDIT_SCRIPT", __file__)   # 存在即可（_run 已被攔）
    assert dr.check_container_consistency()["invariant3"] == "PASS"


@pytest.mark.req("retrieval-decision-layer:1.2")
def test_invariant3_fail_aborts(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res(_AUDIT_BAD3))
    monkeypatch.setattr(dr, "AUDIT_SCRIPT", __file__)   # 存在即可（_run 已被攔）
    with pytest.raises(dr.GateError) as e:
        dr.check_container_consistency()
    assert "重建容器" in str(e.value)


@pytest.mark.req("retrieval-decision-layer:1.2")
def test_other_invariant_failure_does_not_block(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res(_AUDIT_OTHER_FAIL))
    monkeypatch.setattr(dr, "AUDIT_SCRIPT", __file__)   # 存在即可（_run 已被攔）
    assert dr.check_container_consistency()["invariant3"] == "PASS"


@pytest.mark.req("retrieval-decision-layer:1.2")
def test_missing_invariant3_block_aborts(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res("完全沒有不變量區塊"))
    monkeypatch.setattr(dr, "AUDIT_SCRIPT", __file__)   # 存在即可（_run 已被攔）
    with pytest.raises(dr.GateError):
        dr.check_container_consistency()


@pytest.mark.req("retrieval-decision-layer:1.2")
def test_skip_audit_is_recorded_not_silent(monkeypatch):
    def _boom(cmd):
        raise AssertionError("略過時不應真的跑稽核")
    monkeypatch.setattr(dr, "_run", _boom)
    got = dr.check_container_consistency(skip=True)
    assert got["checked"] is False and "不具回歸效力" in got["why"]


# ════════════════════════════════════════════════════════════
# R1.7：快取軌別以容器實測為準
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.7")
@pytest.mark.parametrize("mode,env", [("off", "false"), ("on", "true")])
def test_cache_mode_match(monkeypatch, mode, env):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res(env + "\n"))
    assert dr.check_cache_mode(mode)["observed_cache_enabled"] == env


@pytest.mark.req("retrieval-decision-layer:1.7")
def test_cache_mode_unset_defaults_true(monkeypatch):
    """cache_service 未設 CACHE_ENABLED 時預設啟用——標 off 卻沒設＝說謊，要 abort。"""
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res("\n"))
    assert dr.check_cache_mode("on")["observed_cache_enabled"] == "true"
    with pytest.raises(dr.GateError):
        dr.check_cache_mode("off")


@pytest.mark.req("retrieval-decision-layer:1.7")
def test_cache_mode_mismatch_aborts(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res("true\n"))
    with pytest.raises(dr.GateError) as e:
        dr.check_cache_mode("off")
    assert "快取軌別不符" in str(e.value)


@pytest.mark.req("retrieval-decision-layer:1.7")
def test_cache_probe_failure_aborts(monkeypatch):
    monkeypatch.setattr(dr, "_run", lambda cmd: _Res("", "no such container", 1))
    with pytest.raises(dr.GateError):
        dr.check_cache_mode("off")


# ════════════════════════════════════════════════════════════
# R1.1：凍結語料只讀不改
# ════════════════════════════════════════════════════════════

def _corpus(tmp_path, content=b"x"):
    d = tmp_path / "corpus"
    (d / "run2-head").mkdir(parents=True)
    (d / "run2-head" / "01.json").write_bytes(content)
    return d


@pytest.mark.req("retrieval-decision-layer:1.1")
def test_corpus_integrity_pass(tmp_path):
    d = _corpus(tmp_path)
    manifest = {"corpus_integrity": {"trees": {
        "run2-head": dr.tree_digest(str(d / "run2-head"))}}}
    assert dr.verify_corpus_integrity(manifest, str(d)) is True


@pytest.mark.req("retrieval-decision-layer:1.1")
def test_corpus_modified_aborts(tmp_path):
    d = _corpus(tmp_path)
    manifest = {"corpus_integrity": {"trees": {
        "run2-head": dr.tree_digest(str(d / "run2-head"))}}}
    (d / "run2-head" / "01.json").write_bytes(b"tampered")
    with pytest.raises(dr.GateError) as e:
        dr.verify_corpus_integrity(manifest, str(d))
    assert "只讀不改" in str(e.value)


@pytest.mark.req("retrieval-decision-layer:1.1")
def test_corpus_extra_file_aborts(tmp_path):
    """多一個檔也算被動過（檔數與雜湊都納入樹雜湊）。"""
    d = _corpus(tmp_path)
    manifest = {"corpus_integrity": {"trees": {
        "run2-head": dr.tree_digest(str(d / "run2-head"))}}}
    (d / "run2-head" / "99.json").write_bytes(b"new")
    with pytest.raises(dr.GateError):
        dr.verify_corpus_integrity(manifest, str(d))


@pytest.mark.req("retrieval-decision-layer:1.1")
def test_corpus_missing_dir_aborts(tmp_path):
    manifest = {"corpus_integrity": {"trees": {"run2-head": {"files": 1, "sha256": "x"}}}}
    with pytest.raises(dr.GateError) as e:
        dr.verify_corpus_integrity(manifest, str(tmp_path))
    assert "目錄不存在" in str(e.value)


@pytest.mark.req("retrieval-decision-layer:1.1")
def test_manifest_without_integrity_aborts(tmp_path):
    with pytest.raises(dr.GateError):
        dr.verify_corpus_integrity({}, str(tmp_path))


# ════════════════════════════════════════════════════════════
# R1.4：雜訊標記機器可讀且與登錄簿對得上
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.4")
def test_noise_manifest_shape_and_totals():
    m = dr.load_manifest()
    assert m["totals"]["cases"] == 37 and m["totals"]["turns"] == 107
    # 登錄簿明列的三件全案無效
    for cid in ("01", "05", "12"):
        assert "testcase" in m["cases"][cid]["case_tags"]
    # 客服轉述句 #13～#30
    for i in range(13, 31):
        assert "paraphrased" in m["cases"]["%02d" % i]["case_tags"]
    # 跨案殘留：#03 前兩輪、#21 前兩輪
    assert m["cases"]["03"]["turn_tags"]["1"] == ["carryover"]
    assert m["cases"]["21"]["turn_tags"]["2"] == ["carryover"]
    # 探測腳本重複：#11 前 14 輪為重複、T15–T17 為病灶句
    assert "probe_duplicate" in m["cases"]["11"]["turn_tags"]["14"]
    assert "signal" in m["cases"]["11"]["turn_tags"]["15"]
    # 母體按指標分開定義，不得只有一個「有效輪」數字
    assert set(m["usage_rules"]) >= {"knowledge_coverage", "routing_determinism_e5",
                                     "colloquial_robustness"}


@pytest.mark.req("retrieval-decision-layer:1.4")
def test_noise_manifest_tags_are_all_defined():
    m = dr.load_manifest()
    defined = set(m["tag_definitions"])
    used = set()
    for c in m["cases"].values():
        used |= set(c["case_tags"])
        for tags in c["turn_tags"].values():
            used |= set(tags)
    assert used <= defined, f"未定義的標記：{used - defined}"


@pytest.mark.req("retrieval-decision-layer:1.4")
def test_turn_tags_within_turn_count():
    m = dr.load_manifest()
    for cid, c in m["cases"].items():
        for k in c["turn_tags"]:
            assert 1 <= int(k) <= c["turn_count"], f"#{cid} 輪號 {k} 越界"


@pytest.mark.req("retrieval-decision-layer:1.4")
def test_manifest_matches_frozen_corpus_on_disk():
    """雜訊標記的案號/輪數必須與凍結語料實體對得上（防抄錯輪號）。"""
    m = dr.load_manifest()
    run2 = os.path.join(dr.CORPUS_DIR, "run2-head")
    if not os.path.isdir(run2):
        pytest.skip("凍結語料未取回（依 README 自 S3 取得）")
    for cid, c in m["cases"].items():
        matches = [f for f in os.listdir(run2) if f.startswith(cid + "_")]
        assert matches, f"#{cid} 在凍結語料中找不到對應檔"
        with open(os.path.join(run2, matches[0]), encoding="utf-8") as f:
            assert len(json.load(f)["replay"]) == c["turn_count"]


# ════════════════════════════════════════════════════════════
# 任務 0.4｜D-23：判定字面量須與程式碼實際字串一致（⚠️ 舊鏈隔離 S3 後失去對帳能力）
# 契約：規則表的標記本是從引擎/路由程式碼抄來的字面量，兩條測試釘死兩者一致，
# 有人改引擎一個字就會炸。`services/conversational_engine.py`／`routers/chat.py`
# 已隨舊鏈於 2026-09-10 一起刪除——**對帳的另一邊消失了**，這兩條測試連同移除。
# ⚠️ `dr.ROUTING_RULES["facet_empty_markers"]`／`["fallback_markers"]` 這兩份
# 字面量清單本身**沒有跟著刪**（它們是分析既有歷史語料用的凍結標記，見
# `dr.CORPUS_DIR` 的既有回放語料——那批語料是舊鏈產生的歷史紀錄，內容不會再變），
# 但往後**沒有任何機制**會在有人改動這兩份標記時提醒「有沒有東西可以對」——
# 反正對帳目標已經不存在了，這正是本節要留下的紀錄：對帳能力消失，不是靜默失蹤。
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:1.3")
def test_ask_id_verb_still_appears_in_corpus():
    """索取動詞須在凍結語料實際出現過，避免規則表寫了系統根本不講的話。"""
    run2 = os.path.join(dr.CORPUS_DIR, "run2-head")
    if not os.path.isdir(run2):
        pytest.skip("凍結語料未取回")
    hit = False
    for name in os.listdir(run2):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(run2, name), encoding="utf-8") as f:
            for r in json.load(f).get("replay", []):
                if dr.ROUTING_RULES["ask_id_verb"] in (r.get("answer") or ""):
                    hit = True
                    break
        if hit:
            break
    assert hit, f"{dr.ROUTING_RULES['ask_id_verb']!r} 在凍結語料中零出現——規則表與現實脫節"
