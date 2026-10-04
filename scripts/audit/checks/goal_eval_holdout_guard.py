#!/usr/bin/env python3
"""H 留出題守護（目標驗收規格 2026-10-04 §2.4「機械守護」、Plan 9.27）。

H＝凍結檔 `goal-eval-freeze-20261004.json` 的 196 題（holdout 99＋material 97）。
正本 `rag-orchestrator/canon/*.json` 每條細目的 `title`、`phrasings[].text`、`content_units[]`
與 H 任一題：(i) `hash_norm` 整句相同，或 (ii) NFKC、去空白後最長共同子字串 ≥ 8 字 ⇒ 命中；
扣除基準檔（業主逐筆裁定放行的（題 id, 細目 id, 欄位））後仍有命中 ⇒ FAIL。

- 題目原文在 repo 外 `~/jgb-archive/ruler-9.13/questions.json`：讀不到、sha256 與凍結檔不符、
  或任一題 `hash_norm` 對不上 ⇒ 大聲失敗（⛔ 靜默跳過）。
- 輸出只印題 id、細目 id、欄位、共同長度（repo 公開 ⇒ ⛔ 印題目或共同子字串）。
- 只在主機執行（`make audit`、寫入正本前）；⛔ 註冊進容器內 pytest——容器內沒有題目原文。
- 不變量 34（凍結樣本題 ∩ 講法）語義不變；本檢查另守 H 全體。

用法：python3 scripts/audit/checks/goal_eval_holdout_guard.py [--self-test]
      [--questions P] [--canon-glob G] [--freeze P] [--baseline P] [--no-baseline]
退出碼：0 PASS、1 有新命中、2 前置條件失敗或正對照未中（檢查器不可信）。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canon_phrasing_frozen_disjoint import hash_norm  # noqa: E402  唯一雜湊規則

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SPEC_DIR = os.path.join(REPO, ".kiro/specs/knowledge-outline-and-intent-architecture/inputs")
DEFAULT_FREEZE = os.path.join(SPEC_DIR, "goal-eval-freeze-20261004.json")
DEFAULT_BASELINE = os.path.join(SPEC_DIR, "goal-eval-guard-baseline-20261004.json")
DEFAULT_QUESTIONS = os.path.expanduser("~/jgb-archive/ruler-9.13/questions.json")
DEFAULT_CANON_GLOB = os.path.join(REPO, "rag-orchestrator/canon/*.json")
MINLEN = 8


class GuardError(Exception):
    """前置條件失敗——檢查器不可信，退出碼 2。訊息 ⛔ 含題目文字。"""


def norm(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_h(freeze_path: str, questions_path: str) -> dict[str, str]:
    """回傳 {題 id: 原文}，196 題全數對上凍結檔雜湊；任何不符 ⇒ GuardError。"""
    if not os.path.isfile(freeze_path):
        raise GuardError(f"凍結檔不存在：{freeze_path}")
    with open(freeze_path, encoding="utf-8") as f:
        freeze = json.load(f)
    items = freeze.get("items") or []
    if not items:
        raise GuardError("凍結檔 items 為空")
    if not os.path.isfile(questions_path):
        raise GuardError(f"題目原文檔讀不到：{questions_path}（只在主機有；⛔ 在容器內跑本檢查）")
    want = freeze["_meta"]["questions_sha256"]
    got = _sha_file(questions_path)
    if got != want:
        raise GuardError(f"題目原文檔 sha256 不符：凍結 {want[:12]}…，實際 {got[:12]}…")
    with open(questions_path, encoding="utf-8") as f:
        qs = {x["id"]: x["q"] for x in json.load(f)["items"]}
    out = {}
    for it in items:
        q = qs.get(it["id"])
        if q is None:
            raise GuardError(f"題 {it['id']} 不在題目原文檔")
        if hash_norm(q) != it["q_sha256"]:
            raise GuardError(f"題 {it['id']} 的 hash_norm 與凍結檔不符")
        out[it["id"]] = q
    return out


def load_fields(canon_glob: str) -> list[tuple[str, str, str]]:
    """[(細目 id, 欄位 title|phrasing|body, 文字)]；0 檔或 0 欄位 ⇒ GuardError。"""
    paths = sorted(glob.glob(canon_glob))
    if not paths:
        raise GuardError(f"找不到任何正本 JSON（{canon_glob}）")
    fields = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        for c in doc.get("coarses", []):
            for fine in c.get("fines", []):
                fid = fine["id"]
                fields.append((fid, "title", fine.get("title", "")))
                for ph in fine.get("phrasings", []):
                    fields.append((fid, "phrasing", ph.get("text", "")))
                for u in fine.get("content_units", []):
                    fields.append((fid, "body", u))
    if not fields:
        raise GuardError(f"正本 JSON 掃到 0 個欄位（{paths}）")
    return fields


def _lcs_len(a: str, b: str) -> int:
    best, prev = 0, [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def scan(h: dict[str, str], fields: list[tuple[str, str, str]], use_substring: bool = True) -> set[tuple]:
    """回傳 {(題 id, 細目 id, 欄位, 'hash'|共同長度)}。"""
    by_hash = {hash_norm(q): qid for qid, q in h.items()}
    nq = {qid: norm(q) for qid, q in h.items()}
    grams: dict[str, set[str]] = {}
    for qid, t in nq.items():
        for i in range(len(t) - MINLEN + 1):
            grams.setdefault(t[i:i + MINLEN], set()).add(qid)
    hits = set()
    for fid, fld, text in fields:
        qid = by_hash.get(hash_norm(text))
        if qid:
            hits.add((qid, fid, fld, "hash"))
        if not use_substring:
            continue
        t = norm(text)
        cand = set()
        for i in range(len(t) - MINLEN + 1):
            cand |= grams.get(t[i:i + MINLEN], set())
        for qid in cand:
            hits.add((qid, fid, fld, _lcs_len(nq[qid], t)))
    return hits


def load_baseline(path: str | None) -> set[tuple[str, str, str]]:
    if not path or not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {(e["qid"], e["fine_id"], e["field"]) for e in data.get("allowed", [])}


def subtract_baseline(hits: set[tuple], baseline: set[tuple[str, str, str]]) -> set[tuple]:
    return {h for h in hits if (h[0], h[1], h[2]) not in baseline}


def _probe(h: dict[str, str]) -> None:
    """執行期正對照：任一題的 8 字片段嵌進合成句，必須命中；否則掃描器壞了。"""
    qid, t = next(((k, norm(v)) for k, v in sorted(h.items()) if len(norm(v)) >= MINLEN), (None, ""))
    if qid is None:
        raise GuardError("H 沒有任何 ≥8 字的題目，無法做正對照")
    probe = [("<probe>", "body", "前綴文字" + t[:MINLEN] + "後綴文字")]
    if not any(x[0] == qid for x in scan(h, probe)):
        raise GuardError("執行期正對照未命中——掃描器壞了")


def run(freeze: str, questions: str, canon_glob: str, baseline: str | None) -> tuple[int, list[str]]:
    try:
        h = load_h(freeze, questions)
        fields = load_fields(canon_glob)
        _probe(h)
    except GuardError as e:
        return 2, [f"❌ FAIL（前置條件，檢查器不可信）：{e}"]
    allowed = load_baseline(baseline)
    hits = subtract_baseline(scan(h, fields), allowed)
    lines = [f"HIT {qid} × {fid} × {fld} × {L}" for qid, fid, fld, L in sorted(hits, key=lambda x: (x[0], x[1], x[2], str(x[3])))]
    summary = f"H {len(h)} 題 × 正本 {len(fields)} 欄位；基準放行 {len(allowed)} 筆；新命中 {len(hits)} 筆（執行期正對照 ✅）"
    if hits:
        return 1, lines + [f"❌ FAIL：H 留出題出現在正本——{summary}"]
    return 0, [f"✅ PASS：H 留出題守護——{summary}"]


# ---------- self-test（合成資料，⛔ 讀 ~/jgb-archive） ----------

def _mk_env(tmp: str, questions: dict[str, str], fines: list[dict], baseline: list | None = None,
            corrupt_sha: bool = False) -> tuple[str, str, str, str]:
    qp = os.path.join(tmp, "questions.json")
    with open(qp, "w", encoding="utf-8") as f:
        json.dump({"items": [{"id": k, "q": v} for k, v in questions.items()]}, f, ensure_ascii=False)
    fz = os.path.join(tmp, "freeze.json")
    with open(fz, "w", encoding="utf-8") as f:
        json.dump({"_meta": {"questions_sha256": "0" * 64 if corrupt_sha else _sha_file(qp)},
                   "items": [{"id": k, "q_sha256": hash_norm(v)} for k, v in questions.items()]}, f)
    cdir = os.path.join(tmp, "canon")
    os.makedirs(cdir, exist_ok=True)
    with open(os.path.join(cdir, "x.json"), "w", encoding="utf-8") as f:
        json.dump({"coarses": [{"id": "c", "fines": fines}]}, f, ensure_ascii=False)
    bp = os.path.join(tmp, "baseline.json")
    with open(bp, "w", encoding="utf-8") as f:
        json.dump({"allowed": baseline or []}, f)
    return fz, qp, os.path.join(cdir, "*.json"), bp


def _fine(fid, title="無關標題", phr=("無關講法",), body=("無關內文一句。",)):
    return {"id": fid, "title": title, "phrasings": [{"text": p} for p in phr], "content_units": list(body)}


SELF_TEST_Q = {"q1": "請問合約到期之後押金多久會退還給租客呢", "q2": "帳單逾期未繳的滯納金要怎麼設定比較好"}


def self_test() -> int:
    frag1 = norm(SELF_TEST_Q["q1"])[2:2 + MINLEN]   # 8 字片段
    frag2 = norm(SELF_TEST_Q["q2"])[3:3 + MINLEN]
    short = norm(SELF_TEST_Q["q2"])[0:MINLEN - 1]  # 7 字：不得命中
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        def go(sub, fines, baseline=None, **kw):
            d = os.path.join(tmp, sub)
            os.makedirs(d)
            return run(*_mk_env(d, SELF_TEST_Q, fines, baseline, **kw))
        rc, _ = go("clean", [_fine("f0")])
        cases.append(("① 乾淨正本 ⇒ PASS", rc == 0))
        rc, out = go("hash", [_fine("f1", phr=("請問 合約到期之後押金多久會退還給租客呢？",))])
        cases.append(("② 整句（空白、句尾問號差異）種入講法 ⇒ FAIL 且走雜湊路徑", rc == 1 and any("q1 × f1 × phrasing × hash" in x for x in out)))
        rc, out = go("title", [_fine("f2", title="前綴" + frag1 + "後綴")])
        cases.append(("③ 8 字片段種入標題 ⇒ FAIL", rc == 1 and any(x.startswith("HIT q1 × f2 × title × 8") for x in out)))
        rc, out = go("body", [_fine("f3", body=("說明" + frag2 + "結尾。",))])
        cases.append(("④ 8 字片段種入內文 ⇒ FAIL", rc == 1 and any(x.startswith("HIT q2 × f3 × body × 8") for x in out)))
        rc, _ = go("short", [_fine("f4", body=("說明" + short + "結尾。",))])
        cases.append(("⑤ 7 字片段 ⇒ 不命中（門檻 8）", rc == 0))
        rc, _ = go("base", [_fine("f2", title="前綴" + frag1 + "後綴")], baseline=[{"qid": "q1", "fine_id": "f2", "field": "title"}])
        cases.append(("⑥ 基準放行的（題, 細目, 欄位）⇒ PASS", rc == 0))
        rc, _ = go("base2", [_fine("f2", title="前綴" + frag1 + "後綴", body=(frag1 + "。",))], baseline=[{"qid": "q1", "fine_id": "f2", "field": "title"}])
        cases.append(("⑦ 基準只放行標題、同題種入內文 ⇒ 仍 FAIL", rc == 1))
        rc, _ = go("sha", [_fine("f0")], corrupt_sha=True)
        cases.append(("⑧ 題目原文 sha256 不符 ⇒ 2", rc == 2))
        fz, qp, cg, bp = _mk_env(os.path.join(tmp, "base2"), SELF_TEST_Q, [_fine("f0")])
        cases.append(("⑨ 題目原文檔不存在 ⇒ 2", run(fz, qp + ".missing", cg, bp)[0] == 2))
        cases.append(("⑩ 正本 0 檔 ⇒ 2", run(fz, qp, os.path.join(tmp, "nope", "*.json"), bp)[0] == 2))
        all_out = []
        for sub in ("hash", "title", "body"):
            fzx, qpx, cgx, bpx = (os.path.join(tmp, sub, n) for n in ("freeze.json", "questions.json", "canon/*.json", "baseline.json"))
            all_out += run(fzx, qpx, cgx, bpx)[1]
        leak = [x for x in all_out for q in SELF_TEST_Q.values()
                for i in range(len(norm(q)) - MINLEN + 1) if norm(q)[i:i + MINLEN] in norm(x)]
        cases.append(("⑪ 輸出不含任何題目 8 字片段", not leak))
    bad = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(("✅ " if ok else "❌ ") + n)
    print(f"self-test {len(cases) - len(bad)}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze", default=DEFAULT_FREEZE)
    ap.add_argument("--questions", default=DEFAULT_QUESTIONS)
    ap.add_argument("--canon-glob", default=DEFAULT_CANON_GLOB)
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--no-baseline", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    rc, lines = run(a.freeze, a.questions, a.canon_glob, None if a.no_baseline else a.baseline)
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
