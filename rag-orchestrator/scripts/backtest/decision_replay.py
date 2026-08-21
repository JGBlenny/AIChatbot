#!/usr/bin/env python3
"""凍結語料重播 harness（spec retrieval-decision-layer 任務 1.1｜R1.1–1.7）。

源自 `docs/backtest/corpus-20260810/replay_harness.py`，補上四道「結論可信」的前置：

1. **容器一致性閘門**（R1.2）：開跑前跑 `make audit`，不變量 3（服務容器內關鍵檔與本地
   一致）未過即 abort。20260810 第一輪重播整批結論被舊 image 污染，就是漏了這道。
2. **語料完整性閘門**（R1.1）：凍結語料只讀不改——對 run 目錄重算樹雜湊，與
   `noise_manifest.json` 記錄值不符即 abort。
3. **快取軌別實測**（R1.7）：`--cache-mode on/off` 不是只寫進報告的標籤，開跑前直接讀
   容器的 `CACHE_ENABLED` 核對，不符即 abort（標籤說謊比沒標籤更傷）。
4. **路由類別版本化判定**（R1.3）：`classify_routing()` 規則表版本＋內容雜湊雙戳，
   規則改了而忘了升版也看得出來，跨輪比較才有意義。

跑法（在**主機**上跑，打本機 rag-orchestrator）：
    python3 rag-orchestrator/scripts/backtest/decision_replay.py --cache-mode off --tag rdl_p0
    ONLY=7,18 python3 ... --cache-mode off        # 只跑指定案

輸入：`docs/backtest/corpus-20260810/reports/*.md`（S3 逐字稿，需先取回）。
輸出：`<outdir>/<NN>_<file>.json` 逐案結果 ＋ `<outdir>/_run_meta.json` 執行元資料。
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
CORPUS_DIR = os.path.join(REPO, "docs", "backtest", "corpus-20260810")
MANIFEST_PATH = os.path.join(CORPUS_DIR, "noise_manifest.json")
AUDIT_SCRIPT = os.path.join(REPO, "scripts", "audit", "check_invariants.sh")
SERVICE_CONTAINER = "aichatbot-rag-orchestrator"
API = os.environ.get("DECISION_REPLAY_API", "http://localhost:8100/api/v1/message")


class GateError(RuntimeError):
    """前置閘門未過——一律 abort，不得降級續跑（結論不具效力）。"""


# ════════════════════════════════════════════════════════════════════
# 路由類別判定（R1.3）——規則版本化，跨輪可比
# ════════════════════════════════════════════════════════════════════

# 判定用字面量全部收在此表：規則＝資料，改表即改規則，雜湊自動反映（見 classifier_version）
ROUTING_RULES = {
    "version": "rc-v1",
    # 面向查無的引擎通用句（services/conversational_engine.py 字面量）
    "facet_empty_markers": ["查無對應的資料"],
    # 無知識兜底（routers/chat.py `_handle_no_knowledge_found` 模板）
    "fallback_markers": ["我目前沒有找到符合您問題的資訊"],
    # 面向索取識別資訊：句中出現「請提供」＋識別詞
    "ask_id_verb": "請提供",
    "ask_id_terms": ["編號", "bill_ref", "名稱", "ID"],
    # 索取句為短句且不帶知識來源；用來與「知識答案裡剛好提到請提供編號」區分
    #（凍結語料實例：#36 姓名反查合約——長答案＋帶 sources，不得誤判成 ASK_ID）
    "ask_id_max_len": 120,
    "ask_id_requires_no_sources": True,
}

# ════════════════════════════════════════════════════════════════════
# verdict 量尺（任務 0.6｜R1.3）——**唯一來源＝決策快照**，不從文字反推
#
# 舊五類尺（下方 ROUTING_CLASSES／classify_routing）自此降級為 `legacy_text`，
# 僅供本 spec 立案前產生、無決策快照的舊檔重判，且 SHALL NOT 與 verdict 尺混計（R1.3.4）。
# 換尺的理由（D-04）：五類看不見「同類別但知識接地翻轉」——同一句「我可以擁有多少個
# 物件？」一輪答『上限 10 份』（有來源）、一輪答『並沒有上限』（無來源、與知識庫矛盾），
# 兩者皆記 ANSWER，實測漏計 36% 的不穩定輪。
# ════════════════════════════════════════════════════════════════════

# 單一枚舉：與 design.md C1 的 RoutingDecision.routing_verdict 逐字相同（R1.3.2 自動核對）
ROUTING_VERDICTS = (
    "direct_answer", "enter_facet",
    "stay_facet_ask", "stay_facet_answer", "exit_facet",
    "degrade_knowledge", "degrade_honest", "form", "fallback",
)
# 已知病灶的換尺自檢錨點（R1.3.3）：這三個初翻點在任何新尺上都必須判為不一致
KNOWN_DEFECT_TURNS = (("07", 4), ("10", 3), ("21", 3))


class RulerMixError(RuntimeError):
    """verdict 尺與 legacy_text 尺混計——R1.3.4 明令禁止。"""


class BlindRulerError(RuntimeError):
    """換尺鐵則（R1.3.3）未過：新尺在已知病灶上判不出既有不一致。"""


def verdict_domain_check(design_src: str) -> bool:
    """R1.3.2：本模組值域必須與 design.md C1 枚舉逐字一致，否則兩套詞彙又分岔。"""
    missing = [v for v in ROUTING_VERDICTS if f'"{v}"' not in design_src]
    if missing:
        raise GateError(f"verdict 值域與 design C1 不一致，缺：{missing}")
    return True


def grounded_flag(sources):
    """本輪答案有無知識來源支撐（正交於 verdict）。None＝該 run 未記錄，無從判斷。"""
    if sources is None:
        return None
    return bool(sources)


def turn_result_v2(case_id, turn, snapshot, *, sources=None, answer=None,
                   noise_tags=None, answer_verdict="unjudged"):
    """verdict 尺的 TurnResult（R1.3／3.1）。

    `snapshot` 為該輪的 `usage_events.decision_snapshot`；**沒有快照就不猜**
    （回 routing_verdict=None、source='missing'）——猜了就退回文字反推的老路。
    """
    v = (snapshot or {}).get("routing_verdict")
    if v is not None and v not in ROUTING_VERDICTS:
        raise GateError(f"快照帶了值域外的 routing_verdict：{v!r}")
    return {"case_id": case_id, "turn": turn,
            "routing_verdict": v,
            "grounded": grounded_flag(sources),
            "answer_verdict": answer_verdict,
            "source": "snapshot" if v is not None else "missing",
            "classifier_version": None,
            "noise_tags": list(noise_tags or []),
            "facet_key": (snapshot or {}).get("facet_key"),
            "incomplete": bool((snapshot or {}).get("incomplete"))}


def turn_result_legacy(case_id, turn, *, answer, sources=None, noise_tags=None):
    """舊檔重判（R1.3.4）：標 legacy_text＋版本戳，不得與 verdict 尺混計。"""
    cls, ver = classify_routing(answer, sources=sources)
    return {"case_id": case_id, "turn": turn,
            "routing_verdict": None, "legacy_class": cls,
            "grounded": grounded_flag(sources),
            "answer_verdict": "unjudged",
            "source": "legacy_text", "classifier_version": ver,
            "noise_tags": list(noise_tags or []), "facet_key": None, "incomplete": False}


def composite_key_v2(tr):
    """R1.3.1 的唯一合法比較單位。單用 routing_verdict 視為缺陷。"""
    return (tr["routing_verdict"], tr["grounded"], tr["answer_verdict"])


def compare_rounds(a, b):
    """兩輪次的逐輪複合鍵比較，回不一致的鍵清單。混尺即 raise（R1.3.4）。"""
    for k in set(a) & set(b):
        srcs = {a[k]["source"], b[k]["source"]}
        if "legacy_text" in srcs and srcs != {"legacy_text"}:
            raise RulerMixError(
                f"{k} 兩側尺別不同（{srcs}）——legacy_text 與 verdict 尺不得混計")
    return [k for k in sorted(set(a) & set(b))
            if composite_key_v2(a[k]) != composite_key_v2(b[k])]


# 已知病灶的**文獻記載結果對**（來源：e5-attribution-report.md 實驗①的 10 樣本 census）。
# 換尺能力檢查用這個，不用抽樣——抽樣會把「尺瞎了」和「這兩個樣本剛好沒翻」混為一談。
DOCUMENTED_DEFECT_PAIRS = {
    # #07 T4 黏著：正常輪切到金流面向 vs 黏著輪留在帳單面向索編號（9:1）
    ("07", 4): ({"routing_verdict": "enter_facet"}, {"routing_verdict": "stay_facet_ask"}),
    # #10 T3 對帳被扣住索編號 vs 正常直答（9:1）
    ("10", 3): ({"routing_verdict": "stay_facet_ask"}, {"routing_verdict": "direct_answer"}),
    # #21 T3 一次編輯未發送帳單：直答 vs 被面向索編號（8:2）
    ("21", 3): ({"routing_verdict": "direct_answer"}, {"routing_verdict": "stay_facet_ask"}),
}


def assert_ruler_can_represent_defects():
    """**換尺鐵則·能力檢查（R1.3.3 主判準）**——決定性，不依賴抽樣。

    對每個已知病灶，把文獻記載的兩種結果餵進本尺，複合鍵**必須不同**。
    這是尺的性質（表達力），與某次重播剛好抽到什麼無關。

    存在理由（D-24 教訓）：修訂過程中曾以 `stay_facet` 不細分的尺取代舊尺，
    結果 #07 型黏著前後皆 stay 而判為一致——**換了一把同樣瞎的尺**。
    """
    blind = []
    for k, (s1, s2) in DOCUMENTED_DEFECT_PAIRS.items():
        t1 = turn_result_v2(k[0], k[1], s1, sources=[], noise_tags=[])
        t2 = turn_result_v2(k[0], k[1], s2, sources=[], noise_tags=[])
        if composite_key_v2(t1) == composite_key_v2(t2):
            blind.append(k)
    if blind:
        raise BlindRulerError(
            "換尺鐵則未過：本尺無法區分已知病灶的兩種結果 → 對主病灶全盲，退回重設計。"
            f"表達不出的輪：{blind}")
    return True


def assert_ruler_sees_known_defects(samples, require_any=True):
    """**換尺鐵則·現場檢查（R1.3.3 輔助）**——以實跑樣本佐證，非主判準。

    `samples`：{(case_id, turn): [TurnResult, ...]}。
    已知病灶的翻動率介於 1/10～2/10，樣本少時全部不翻屬正常抽樣結果，
    故判準為「**至少一個**病灶輪呈現不一致」；全部一致才是可疑訊號。
    回傳 (passed, 未翻動的輪清單) 供報告揭露。
    """
    flipped, flat = [], []
    for k in KNOWN_DEFECT_TURNS:
        rs = samples.get(k)
        if not rs or len(rs) < 2:
            continue
        (flipped if len({composite_key_v2(t) for t in rs}) > 1 else flat).append(k)
    if require_any and not flipped and flat:
        raise BlindRulerError(
            f"現場檢查：{len(flat)} 個已知病灶輪在 {len(samples.get(flat[0], []))} 個樣本上"
            f"全部一致，且無任何病灶輪翻動——樣本不足或尺有問題，需加樣本重驗。輪：{flat}")
    return True, flat


# ════════════════════════════════════════════════════════════════════
# 期望答案表與 answer_verdict（任務 0.7｜R5.4.1／5.4.2）
#
# 「0 胡編 0 錯誤資訊」原本只是驗收口號——全 spec 沒有任何量測機制，而 `grounded`
# 只證明「有來源」，**有來源仍可能答錯**。此表把它變成可量測：
#   母體＝表涵蓋的輪；母體內任一輪 unjudged 即 FAIL（禁止「沒判＝沒問題」）；
#   母體外不罰，但**必須揭露筆數與佔比**（不得讓分母悄悄縮小）。
# 表本身納入 R2.5 的量測前凍結（雜湊可查）。
# ════════════════════════════════════════════════════════════════════

# `not_applicable`：本輪的答案真偽在本環境不可判——目前唯一來源是 env_limited
# （prod 編號在 preview 查無屬**正確行為**，noise_manifest 明訂 grounding 不列入判定）。
# 沒有這個值就只能判 incorrect，那是假陰性；它與 unjudged 的差別是
# **unjudged＝還沒判（母體內即 FAIL）、not_applicable＝判過且結論是「此環境不適用」**。
ANSWER_VERDICTS = ("correct", "incorrect", "unsupported", "not_applicable", "unjudged")
_EXPECTED_CONFIDENCE = ("explicit", "derivable")


class UnjudgedError(RuntimeError):
    """母體內存在未判定的輪——R5.4.2 明令 FAIL。"""


def load_expected_answers(path=None):
    path = path or os.path.join(CORPUS_DIR, "expected_answers.json")
    with open(path, encoding="utf-8") as f:
        t = json.load(f)
    validate_expected_answers(t)
    return t


def validate_expected_answers(table):
    """結構驗證：鍵格式、期望答案與判定要點非空、confidence 值域。"""
    bad = []
    for k, e in (table.get("entries") or {}).items():
        parts = k.split("|")
        if len(parts) != 2 or not parts[1].isdigit():
            bad.append(f"{k}：鍵格式須為 '<case_id>|<turn>'")
            continue
        if not (e.get("expected_answer") or "").strip():
            bad.append(f"{k}：expected_answer 為空（期望答案須逐字引用，不得留白）")
        if not (e.get("key_points") or []):
            bad.append(f"{k}：key_points 為空（無判定要點則此列無法用於判 correct/incorrect）")
        if e.get("confidence") not in _EXPECTED_CONFIDENCE:
            bad.append(f"{k}：confidence 須為 {_EXPECTED_CONFIDENCE}，得到 {e.get('confidence')!r}")
    if bad:
        raise GateError("期望答案表結構不合格：\n  " + "\n  ".join(bad))
    return True


def in_answer_population(table, case_id, turn):
    return f"{case_id}|{turn}" in (table.get("entries") or {})


def expected_answers_breakdown(table):
    """explicit / derivable 分開統計——derivable 有主觀成分，報告須分列。"""
    b = {"explicit": 0, "derivable": 0}
    for e in (table.get("entries") or {}).values():
        b[e["confidence"]] = b.get(e["confidence"], 0) + 1
    b["total"] = b["explicit"] + b["derivable"]
    return b


def expected_answers_hash(table):
    """R2.5：表入量測前凍結，雜湊隨內容變動。"""
    body = json.dumps(table.get("entries") or {}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def env_limited_turns(table):
    """表上標 env_limited 的輪（prod 編號在 preview 查無屬正確行為）。"""
    return {k for k, e in (table.get("entries") or {}).items() if e.get("env_limited")}


def assert_answer_population_judged(table, turn_results):
    """R5.4.2 驗收：母體內全判、母體外揭露。

    `turn_results`：{(case_id, turn): TurnResult}。
    回傳報告 dict；母體內有 unjudged 即 raise UnjudgedError。
    """
    inside, judged, unjudged_keys, outside, na = 0, 0, [], 0, 0
    for (cid, t), tr in turn_results.items():
        av = tr.get("answer_verdict", "unjudged")
        if av not in ANSWER_VERDICTS:
            raise GateError(f"{cid}|{t}：answer_verdict 越界 {av!r}")
        if in_answer_population(table, cid, t):
            inside += 1
            if av == "unjudged":
                unjudged_keys.append(f"{cid}|{t}")
            elif av == "not_applicable":
                na += 1                    # 判過，但此環境不適用（env_limited）
            else:
                judged += 1
        else:
            outside += 1
    total = inside + outside
    rep = {"in_population": inside, "judged": judged, "not_applicable": na,
           "outside_population": outside,
           "outside_ratio": (outside / total) if total else 0.0,
           "table_hash": expected_answers_hash(table),
           "breakdown": expected_answers_breakdown(table)}
    # env_limited 的輪若被判 incorrect＝假陰性（在 preview 查無本來就對）
    _env = env_limited_turns(table)
    _false_neg = [f"{c}|{t}" for (c, t), tr in turn_results.items()
                  if f"{c}|{t}" in _env and tr.get("answer_verdict") == "incorrect"]
    if _false_neg:
        raise GateError(
            "env_limited 輪被判 incorrect（假陰性）——prod 編號在 preview 查無屬正確行為，"
            f"應判 not_applicable：{'、'.join(sorted(_false_neg))}")
    rep["env_limited_in_population"] = len(_env)
    if unjudged_keys:
        raise UnjudgedError(
            "母體內尚有未判定的輪（禁止以『沒判＝沒問題』通過，R5.4.2）："
            + "、".join(sorted(unjudged_keys)))
    return rep


ROUTING_CLASSES = ("ANSWER", "ASK_ID", "FACET_EMPTY", "FORM", "FALLBACK")
# 呼叫失敗的輪：不屬五類別，另立標記——把錯誤輪塞進任一真類別會污染 E-5 不一致率。
CLASS_ERROR = "ERROR"


def classifier_version() -> str:
    """規則表版本戳＝宣告版本＋規則內容雜湊。

    只升版不改內容、或改內容不升版，兩種都會被下游看見（跨輪比較的前提是規則同一）。
    """
    body = json.dumps({k: v for k, v in ROUTING_RULES.items() if k != "version"},
                      ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]
    return f"{ROUTING_RULES['version']}+{digest}"


def classify_routing(answer, *, sources=None, form_triggered=False, error=None):
    """把一輪回應歸入路由類別，回 (class, classifier_version)。

    判定順序固定（前者優先）：ERROR → FORM → FACET_EMPTY → FALLBACK → ASK_ID → ANSWER。

    - FORM 只認結構化證據（`form_triggered`/`form_id`）。**凍結語料 run2/run3 的歸檔
      JSON 未記這些欄位**，故對舊檔重判時 FORM 永不成立——這是已知盲點，不以文字猜測
      補足（猜錯會讓 E-5 歸因指向錯的方向）；新跑的 run 由本 harness 完整記錄。
    - ASK_ID 要求「短句＋無知識來源」，避免把「知識答案裡提到請提供編號」誤判成面向索取。
    """
    ver = classifier_version()
    if error:
        return CLASS_ERROR, ver
    text = (answer or "").strip()
    if form_triggered:
        return "FORM", ver
    for m in ROUTING_RULES["facet_empty_markers"]:
        if m in text:
            return "FACET_EMPTY", ver
    for m in ROUTING_RULES["fallback_markers"]:
        if m in text:
            return "FALLBACK", ver
    if ROUTING_RULES["ask_id_verb"] in text \
            and any(t in text for t in ROUTING_RULES["ask_id_terms"]) \
            and len(text) <= ROUTING_RULES["ask_id_max_len"] \
            and not (ROUTING_RULES["ask_id_requires_no_sources"] and sources):
        return "ASK_ID", ver
    return "ANSWER", ver


def clarify_flag(answer, sources=None):
    """診斷旗標（非類別）：面向在問澄清但不是索取識別碼（如「請問您希望改成多少？」）。

    R1.3 的類別集固定為五類，這類輪次歸 ANSWER；但它們是 E-3 黏著的主要現場，
    丟掉可惜，故另立旗標隨 TurnResult 落地，不參與類別統計。
    """
    text = (answer or "").strip()
    if sources or not text.endswith(("？", "?")):
        return False
    cls, _ = classify_routing(text, sources=sources)
    return cls == "ANSWER"


# ════════════════════════════════════════════════════════════════════
# 前置閘門
# ════════════════════════════════════════════════════════════════════

def tree_digest(root):
    """對目錄做決定性樹雜湊（與 noise_manifest 產生時同一演算法）。"""
    h = hashlib.sha256()
    n = 0
    for dirpath, _, names in os.walk(root):
        for name in sorted(names):
            fp = os.path.join(dirpath, name)
            rel = os.path.relpath(fp, root)
            with open(fp, "rb") as f:
                fh = hashlib.sha256(f.read()).hexdigest()
            h.update(rel.encode() + b"\0" + fh.encode() + b"\n")
            n += 1
    return {"files": n, "sha256": h.hexdigest()}


def load_manifest(path=MANIFEST_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify_external_anchor(manifest, corpus_dir=CORPUS_DIR, allow_offline=True):
    """R1.8／D-21：完整性錨點須為**本流程無法改寫的外部事實**。

    舊做法只比對 `noise_manifest.json` 內由本程式算出的樹雜湊——同時改語料與重算雜湊
    即可通過（自簽自證）；而 corpus README 白紙黑字寫「開跑前必驗 SHA-256，不符即 abort」，
    程式卻從未讀 `tarball_sha256`、從未觸及 S3。此函式補上該實比對。

    回傳 dict 記錄實際做了什麼（進 `_run_meta.json`，供關卡報告判斷結論效力）：
      verified=True   已對 S3 物件的 SHA-256 實比對
      verified=False  外部錨點不可達 → **明示降級**，該輪標「完整性未經外部錨點驗證」
    不符（非不可達，是真的對不上）一律 raise，不得降級。
    """
    ci = (manifest.get("corpus_integrity") or {})
    want = ci.get("tarball_sha256")
    s3 = ci.get("tarball_s3")
    if not want or not s3:
        return {"verified": False, "why": "manifest 未記 tarball_sha256／tarball_s3"}
    local = os.path.join(corpus_dir, os.path.basename(s3))
    if not os.path.exists(local):
        r = _run(["aws", "s3", "cp", s3, local])
        if r.returncode != 0:
            if allow_offline:
                return {"verified": False, "anchor": s3,
                        "why": f"S3 錨點不可達（{r.stderr.strip()[:120]}）——"
                               f"本輪結論標記「完整性未經外部錨點驗證」"}
            raise GateError(f"S3 錨點不可達且不允許降級：{r.stderr.strip()[:200]}")
    h = hashlib.sha256()
    with open(local, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != want:
        raise GateError(f"凍結語料 tarball SHA-256 不符（R1.1 只讀不改）：\n"
                        f"  期望 {want}\n  實得 {got}\n  來源 {s3}")
    return {"verified": True, "anchor": s3, "sha256": got}


def verify_corpus_integrity(manifest, corpus_dir=CORPUS_DIR):
    """R1.1：凍結語料只讀不改。任一 run 目錄樹雜湊不符即 abort。

    ⚠ 本函式只是**本機一致性**檢查（自簽自證，擋不住「同時改語料與雜湊」）；
    真正的錨點是 `verify_external_anchor()`。兩者都跑，缺一不可。
    """
    expected = (manifest.get("corpus_integrity") or {}).get("trees") or {}
    if not expected:
        raise GateError("noise_manifest.json 缺 corpus_integrity.trees，無從驗凍結語料")
    bad = []
    for sub, exp in expected.items():
        root = os.path.join(corpus_dir, sub)
        if not os.path.isdir(root):
            bad.append(f"{sub}：目錄不存在（依 README 自 S3 取回）")
            continue
        got = tree_digest(root)
        if got != exp:
            bad.append(f"{sub}：{got} != 記錄值 {exp}")
    if bad:
        raise GateError("凍結語料完整性未過（只讀不改，R1.1）：\n  " + "\n  ".join(bad))
    return True


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def parse_invariant3(audit_stdout):
    """從 `make audit` 輸出切出不變量 3 區塊，回 (passed, 區塊原文)。"""
    blocks = re.split(r"═══ (不變量 \d+[^═]*) ═══", audit_stdout)
    # blocks = [前言, 標題1, 內容1, 標題2, 內容2, ...]
    for i in range(1, len(blocks) - 1, 2):
        if blocks[i].startswith("不變量 3"):
            body = blocks[i + 1]
            return ("❌" not in body), body.strip()
    return False, "audit 輸出中找不到不變量 3 區塊"


def check_container_consistency(skip=False):
    """R1.2：不變量 3 未過 → 拒絕開跑。"""
    if skip:
        return {"checked": False,
                "why": "--skip-audit 明示略過（本輪結論不具回歸效力）"}
    if not os.path.exists(AUDIT_SCRIPT):
        raise GateError(f"找不到稽核腳本 {AUDIT_SCRIPT}")
    res = _run(["bash", AUDIT_SCRIPT])
    passed, body = parse_invariant3(res.stdout)
    if not passed:
        raise GateError("容器一致性（make audit 不變量 3）未過，先重建容器再跑：\n"
                        + body)
    return {"checked": True, "invariant3": "PASS", "detail": body}


def check_cache_mode(expected):
    """R1.7：快取軌別以容器實際 env 為準，不以參數自稱為準。"""
    res = _run(["docker", "exec", SERVICE_CONTAINER, "printenv", "CACHE_ENABLED"])
    if res.returncode != 0:
        raise GateError(f"讀不到 {SERVICE_CONTAINER} 的 CACHE_ENABLED"
                        f"（容器沒起來？）：{res.stderr.strip()}")
    # cache_service.py：未設時預設 true
    observed = (res.stdout.strip() or "true").lower()
    want = "true" if expected == "on" else "false"
    if observed != want:
        raise GateError(
            f"快取軌別不符：要求 --cache-mode {expected}（CACHE_ENABLED={want}），"
            f"容器實測 CACHE_ENABLED={observed}。\n"
            f"  改法：調整 docker-compose.prod.yml 的 CACHE_ENABLED 後重啟 "
            f"{SERVICE_CONTAINER}，再重跑。")
    return {"requested": expected, "observed_cache_enabled": observed}


# ════════════════════════════════════════════════════════════════════
# 重播（payload 形狀與 replay_harness.py 逐欄一致——換了就與 run2/run3 不可比）
# ════════════════════════════════════════════════════════════════════

def parse_report(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    def field(label):
        m = re.search(r"- %s：(.*)" % label, text)
        return m.group(1).strip() if m else ""

    role = re.search(r"role_id:\s*([0-9-]+)", text)
    desc = ""
    m = re.search(r"## 問題描述\n+(.*?)\n+## ", text, re.S)
    if m:
        desc = m.group(1).strip()
    turns = []
    body = text.split("## 對話逐字稿", 1)[1] if "## 對話逐字稿" in text else ""
    parts = re.split(r"\*\*(使用者|智能助手)：\*\*", body)
    i = 1
    while i < len(parts):
        speaker = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        turns.append({"speaker": speaker, "text": content})
        i += 2
    return {"file": os.path.basename(path), "time": field("回報時間"),
            "user_id": field("回報人 user_id"), "role_name": field("團隊/角色"),
            "role_id": role.group(1) if role else None, "page": field("頁面"),
            "orig_session": field("session_id"), "desc": desc, "turns": turns}


def ask(message, session_id, role_id, user_id):
    payload = {"message": message, "mode": "b2b",
               "target_user": "property_manager", "session_id": session_id}
    if role_id and role_id != "-":
        payload["role_id"] = str(role_id)
    if user_id:
        payload["user_id"] = str(user_id)
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": "HTTP %s" % e.code, "body": e.read().decode()[:500],
                "elapsed": round(time.time() - t0, 1)}
    except Exception as e:
        return {"error": repr(e), "elapsed": round(time.time() - t0, 1)}
    return {
        "answer": data.get("answer") or data.get("message") or "",
        "intent": data.get("intent_name"),
        "confidence": data.get("confidence"),
        "sources": [s.get("question_summary") or s.get("question")
                    for s in (data.get("sources") or [])][:3],
        # 新增（舊 harness 未記）：FORM 類別的結構化證據，文字猜不出來
        "form_triggered": bool(data.get("form_triggered")),
        "form_id": data.get("form_id"),
        "action_type": data.get("action_type"),
        "elapsed": round(time.time() - t0, 1),
    }


def turn_result(case_id, turn, res, noise_tags):
    cls, ver = classify_routing(res.get("answer"), sources=res.get("sources"),
                                form_triggered=res.get("form_triggered"),
                                error=res.get("error"))
    return {"case_id": case_id, "turn": turn, "routing_class": cls,
            "classifier_version": ver, "noise_tags": noise_tags,
            "clarify_question": clarify_flag(res.get("answer"), res.get("sources")),
            "structured_form_evidence": "form_triggered" in res}


def collect_verdicts(run_tag, cases_meta, since_iso=None):
    """重播後自 usage_events 取回決策快照，依 session_id＋輪序對齊（R1.3、C6 重寫）。

    **不改請求 payload**——payload 與凍結語料逐欄一致，可比性不變；對齊只靠
    session_id 與同 session 內的時間序。取不到快照的輪回 None（由 turn_result_v2
    標 source='missing'），**不猜**。

    `since_iso`：session_id 由 tag 衍生，**重用同一個 tag 會撈到前一輪的舊列**
    （實測踩過：前一輪留下未細分的 stay_facet，讓本輪在值域檢查當場 abort）。
    以本次執行起始時間過濾，不改請求 payload、不動 session_id 格式。
    """
    out = {}
    for case_id, sid, n_turns in cases_meta:
        r = _run(["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
                  "-d", "aichatbot_admin", "-tA", "-c",
                  f"SELECT coalesce(decision_snapshot::text,'') FROM usage_events "
                  f"WHERE session_id = '{sid}'"
                  + (f" AND ts >= '{since_iso}'" if since_iso else "")
                  + " ORDER BY ts"])
        if r.returncode != 0:
            print(f"⚠️ 取快照失敗（{sid}）：{r.stderr.strip()[:100]}")
            continue
        rows = [ln for ln in r.stdout.splitlines() if ln.strip() != ""]
        for i in range(1, n_turns + 1):
            snap = None
            if i <= len(rows):
                try:
                    snap = json.loads(rows[i - 1]) if rows[i - 1] else None
                except json.JSONDecodeError:
                    snap = None
            out[(case_id, i)] = snap
    return out


def build_turn_results(results, verdicts, manifest):
    """把重播結果與快照併成 verdict 尺的 TurnResult（複合鍵可比）。"""
    trs = {}
    for out in results:
        case_id = out["turn_results"][0]["case_id"] if out.get("turn_results") else None
        if case_id is None:
            continue
        tags = ((manifest.get("cases") or {}).get(case_id) or {})
        for rp in out["replay"]:
            k = (case_id, rp["turn"])
            trs[k] = turn_result_v2(
                case_id, rp["turn"], verdicts.get(k),
                sources=rp.get("sources"), answer=rp.get("answer"),
                noise_tags=list(tags.get("case_tags") or [])
                + list((tags.get("turn_tags") or {}).get(str(rp["turn"]), [])))
    return trs


def replay_case(args):
    idx, rec, run_tag, outdir, manifest = args
    case_id = "%02d" % idx
    case = (manifest.get("cases") or {}).get(case_id, {})
    turn_tags = case.get("turn_tags") or {}
    case_tags = case.get("case_tags") or []
    user_turns = [t["text"] for t in rec["turns"] if t["speaker"] == "使用者"]
    sid = "%s_%02d_%s" % (run_tag, idx, rec["file"][:15])
    out = dict(rec)
    out["replay_session"] = sid
    out["case_tags"] = case_tags
    out["replay"] = []
    out["turn_results"] = []
    for n, msg in enumerate(user_turns, 1):
        res = ask(msg, sid, rec["role_id"], rec["user_id"])
        out["replay"].append({"turn": n, "user": msg, **res})
        tags = list(case_tags) + list(turn_tags.get(str(n), []))
        out["turn_results"].append(turn_result(case_id, n, res, tags))
        print("  [%s/T%d] %-10s %s" % (case_id, n, out["turn_results"][-1]["routing_class"],
                                       msg[:26].replace("\n", " ")), flush=True)
    with open(os.path.join(outdir, "%s_%s.json" % (case_id, rec["file"][:-3])),
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def run_corpus(cache_mode, run_tag, outdir, reports_dir, workers=4, only=None,
               skip_audit=False):
    """R1.7 雙軌重播。前置閘門任一未過即 abort（不降級續跑）。"""
    manifest = load_manifest()
    gates = {
        "corpus_integrity": verify_corpus_integrity(manifest),      # 本機樹雜湊（自簽）
        "external_anchor": verify_external_anchor(manifest),        # S3 SHA-256（外部事實）
        "container": check_container_consistency(skip=skip_audit),
        "cache": check_cache_mode(cache_mode),
    }
    if not gates["external_anchor"].get("verified"):
        print("⚠️  完整性未經外部錨點驗證：%s" % gates["external_anchor"].get("why"))
    # 逐字稿在 S3 下是 <年>/<月>/ 分層，必須遞迴收集後**依檔名排序**——案號＝排序序位，
    # 與 replay_harness.py 逐字相同；換排序法會讓案號與 run2/run3 對不上、全部不可比。
    _run_started = _run(["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
                         "-d", "aichatbot_admin", "-tA", "-c", "SELECT now()"]).stdout.strip()
    files = []
    for root, _, names in os.walk(reports_dir):
        files.extend(os.path.join(root, n) for n in names if n.endswith(".md"))
    files.sort(key=os.path.basename)
    if not files:
        raise GateError(f"{reports_dir} 內沒有逐字稿（依 README 自 S3 取回）")
    cases = [(i, parse_report(p)) for i, p in enumerate(files, 1)]
    if only:
        cases = [c for c in cases if c[0] in only]
    os.makedirs(outdir, exist_ok=True)
    print("replaying %d cases (%d user turns), cache=%s, classifier=%s"
          % (len(cases), sum(len([t for t in r["turns"] if t["speaker"] == "使用者"])
                             for _, r in cases), cache_mode, classifier_version()))
    jobs = [(i, r, run_tag, outdir, manifest) for i, r in cases]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(replay_case, jobs))
    # D-22：`_run_meta.json` 原本全 repo 無消費者，「本輪結論不具回歸效力」只是寫給人看的
    # 良心話。此處把效力判定固化成欄位，關卡報告產生器據此拒絕收錄（`evidence_grade`）。
    _degraded = []
    if not gates["container"].get("checked"):
        _degraded.append("容器一致性未驗（--skip-audit）")
    if not gates["external_anchor"].get("verified"):
        _degraded.append("完整性未經外部錨點驗證")
    # verdict 尺（任務 0.6）：自快照取回並落檔，供跨輪以複合鍵比較
    _cases_meta = [(("%02d" % i), "%s_%02d_%s" % (run_tag, i, r["file"][:15]),
                    len([t for t in r["turns"] if t["speaker"] == "使用者"]))
                   for i, r in cases]
    _verdicts = collect_verdicts(run_tag, _cases_meta, since_iso=_run_started or None)
    _trs = build_turn_results(results, _verdicts, manifest)
    with open(os.path.join(outdir, "_turn_results_v2.json"), "w", encoding="utf-8") as f:
        json.dump({f"{k[0]}|{k[1]}": v for k, v in sorted(_trs.items())},
                  f, ensure_ascii=False, indent=2)
    _missing = sum(1 for v in _trs.values() if v["source"] == "missing")
    _cov = 1 - (_missing / len(_trs)) if _trs else 0
    print("verdict 尺：%d 輪，快照覆蓋 %.1f%%（missing %d）"
          % (len(_trs), _cov * 100, _missing))

    meta = {"run_tag": run_tag, "cache_mode": cache_mode,
            "evidence_grade": "invalid_for_regression" if _degraded else "valid",
            "degraded_reasons": _degraded,
            "verdict_ruler": {"turns": len(_trs), "snapshot_coverage": round(_cov, 4),
                              "missing": _missing},
            "classifier_version": classifier_version(),
            "manifest_version": manifest.get("manifest_version"),
            "gates": gates, "cases": len(results),
            "turns": sum(len(r["turn_results"]) for r in results),
            "api": API}
    with open(os.path.join(outdir, "_run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("done ->", outdir)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="凍結語料決策層重播（R1）")
    ap.add_argument("--cache-mode", choices=("on", "off"), required=True,
                    help="快取軌別；開跑前以容器 CACHE_ENABLED 實測核對")
    # 預設須為 usage_metering.INTERNAL_RULES 認得的內部前綴，否則自己的重播會被算成
    # 「非內部事件」而污染快照覆蓋率母體（任務 0.1 驗收④）。
    ap.add_argument("--tag", default="backtest_rdl", help="run tag（進 session_id 前綴；須為內部前綴）")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--reports", default=os.path.join(CORPUS_DIR, "reports"))
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "4")))
    ap.add_argument("--only", default=os.environ.get("ONLY"),
                    help="只跑指定案號，逗號分隔")
    ap.add_argument("--skip-audit", action="store_true",
                    help="略過容器一致性閘門（本輪結論不具回歸效力，會寫進 _run_meta）")
    a = ap.parse_args(argv)
    _INTERNAL_PREFIXES = ("backtest_", "loop_", "kcl_", "smoke_", "verify_", "probe_",
                          "demo_", "fp_", "fp2_", "reg_", "dev_")
    if not a.tag.startswith(_INTERNAL_PREFIXES):
        print("💥 --tag 必須以內部流量前綴開頭（%s），否則重播會污染計量母體；"
              "現值：%s" % ("/".join(_INTERNAL_PREFIXES[:3]) + "…", a.tag), file=sys.stderr)
        return 2
    outdir = a.outdir or os.path.join(CORPUS_DIR, "out_%s_cache%s" % (a.tag, a.cache_mode))
    only = {int(x) for x in a.only.split(",")} if a.only else None
    try:
        run_corpus(a.cache_mode, a.tag, outdir, a.reports, a.workers, only, a.skip_audit)
    except GateError as e:
        print("💥 前置閘門未過，拒絕開跑：\n%s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
