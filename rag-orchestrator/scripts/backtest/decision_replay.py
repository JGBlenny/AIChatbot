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


def verify_corpus_integrity(manifest, corpus_dir=CORPUS_DIR):
    """R1.1：凍結語料只讀不改。任一 run 目錄樹雜湊不符即 abort。"""
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
        "corpus_integrity": verify_corpus_integrity(manifest),
        "container": check_container_consistency(skip=skip_audit),
        "cache": check_cache_mode(cache_mode),
    }
    # 逐字稿在 S3 下是 <年>/<月>/ 分層，必須遞迴收集後**依檔名排序**——案號＝排序序位，
    # 與 replay_harness.py 逐字相同；換排序法會讓案號與 run2/run3 對不上、全部不可比。
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
    meta = {"run_tag": run_tag, "cache_mode": cache_mode,
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
    ap.add_argument("--tag", default="rdl", help="run tag（進 session_id 前綴）")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--reports", default=os.path.join(CORPUS_DIR, "reports"))
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "4")))
    ap.add_argument("--only", default=os.environ.get("ONLY"),
                    help="只跑指定案號，逗號分隔")
    ap.add_argument("--skip-audit", action="store_true",
                    help="略過容器一致性閘門（本輪結論不具回歸效力，會寫進 _run_meta）")
    a = ap.parse_args(argv)
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
