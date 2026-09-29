#!/usr/bin/env python3
"""Plan 9.16 S3: verifier raw output -> results -> review sheet, with three-way reconciliation.

  python3 p916_s3_sheet.py parse                      # p916-s3-raw-<batch>.txt -> p916-s3-results.json (loud on any defect)
  python3 p916_s3_sheet.py sheet <out.md>             # results + canon titles -> review sheet
  python3 p916_s3_sheet.py check <sheet.md> [--raw-dir DIR]   # (1) raw <-> results, (2) sheet <-> results; exit 1 on any mismatch

Raw line format (one per target id): `<id>｜pass[...]` or `<id>｜doubt｜句序 n｜理由｜證據`.
Batches without a raw file are "未先審" (partial sheet); their coarse groups may not be approved as a whole.
"""
import json
import os
import re
import sys

SP = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/chenqinghuang/dev/work/AIChatbot"
CANON_COMMIT = "bdb2327b"
SHELVES = os.environ.get("P919_SHELVES", "ABCI")
PREFIX = "p919-s2"
BATCHES = os.path.join(SP, f"{PREFIX}-batches.json")
RESULTS = os.path.join(SP, f"{PREFIX}-results.json")
TARGETS = os.path.join(SP, f"{PREFIX}-targets.json")
HOLD = set(json.load(open(os.path.join(SP, f"{PREFIX}-hold.json"), encoding="utf-8")))  # owner: delete next plan; never reviewed here


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def canon_layout():
    """[(shelf, coarse_id, coarse_title, [(fid, title)])] in canon order, from the working-tree canon."""
    out = []
    for s in SHELVES:
        cur = None
        with open(os.path.join(REPO, "rag-orchestrator/canon/jgb", f"{s}.md"), encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                m = re.match(r"^## (.*) \{#([^}]+)\}$", line)
                if m:
                    cur = [s, m.group(2), m.group(1), []]
                    out.append(cur)
                    continue
                m = re.match(r"^### (.*) \{#([^}]+)\}$", line)
                if m:
                    cur[3].append((m.group(2), m.group(1)))
    return out


def parse_raw(raw_dir, batches):
    """Return ({id: record}, errors). Only batches with a raw file are parsed."""
    res, errors = {}, []
    for b, groups in batches.items():
        p = os.path.join(raw_dir, f"{PREFIX}-raw-{b}.txt")
        if not os.path.exists(p):
            continue
        expected = [i for g in groups for i in g["ids"]]
        seen = {}
        with open(p, encoding="utf-8") as fh:
            for ln, line in enumerate(fh, 1):
                line = line.strip()
                if not line.startswith("jgb/"):
                    continue
                parts = [x.strip() for x in line.split("｜")]
                fid = parts[0]
                if len(parts) < 2:
                    errors.append(f"{b}:{ln} malformed: {line[:80]}")
                    continue
                if parts[1].startswith("pass"):
                    rec = {"verdict": "pass", "note": "｜".join(parts[1:])[4:].strip()}
                elif parts[1].startswith("doubt"):
                    if len(parts) < 5 or not parts[4]:
                        errors.append(f"{b}:{ln} doubt without evidence: {fid}")
                        continue
                    rec = {"verdict": "doubt", "sentence": parts[2], "reason": parts[3], "evidence": "｜".join(parts[4:])}
                else:
                    errors.append(f"{b}:{ln} unknown verdict: {line[:80]}")
                    continue
                if fid in seen:
                    errors.append(f"{b}:{ln} duplicate id {fid}")
                seen[fid] = dict(rec, batch=b)
        missing = [i for i in expected if i not in seen]
        extra = [i for i in seen if i not in expected]
        if missing:
            errors.append(f"{b}: missing ids {missing}")
        if extra:
            errors.append(f"{b}: ids outside batch {extra}")
        res.update(seen)
    return res, errors


def cmd_parse():
    batches = load(BATCHES)
    res, errors = parse_raw(SP, batches)
    for e in errors:
        print("❌", e)
    if errors:
        return 1
    with open(RESULTS, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    n_pass = sum(1 for r in res.values() if r["verdict"] == "pass")
    print(f"parsed {len(res)} ids: pass {n_pass} / doubt {len(res) - n_pass}")
    return 0


def group_view(results, targets):
    """{coarse_id: {"pass": [...], "doubt": [...], "pending": [...]}} for target fines only, canon order."""
    view = {}
    for shelf, cid, ctitle, fines in canon_layout():
        g = {"shelf": shelf, "title": ctitle, "pass": [], "doubt": [], "pending": [], "hold": [], "titles": {}}
        for fid, t in fines:
            if fid not in targets:
                continue
            g["titles"][fid] = t
            r = results.get(fid)
            if r is None:
                g["pending"].append(fid)
            elif fid in HOLD:
                g["hold"].append(fid)
            else:
                g[r["verdict"]].append(fid)
        if g["titles"]:
            view[cid] = g
    covered = {f for g in view.values() for f in g["titles"]}
    missing = sorted(targets - covered)
    if missing:
        raise SystemExit(f"❌ {len(missing)} targets not found in canon shelves {SHELVES}: {missing[:5]}")
    return view


def warn(g):
    n = len(g["titles"]) - len(g["hold"])  # held fines are out of the review pool
    return n > 0 and len(g["doubt"]) / n > 0.30


def cmd_sheet(out):
    targets = set(load(TARGETS))
    results = load(RESULTS) if os.path.exists(RESULTS) else {}
    view = group_view(results, targets)
    tot_p = sum(len(g["pass"]) for g in view.values())
    tot_d = sum(len(g["doubt"]) for g in view.values())
    tot_u = sum(len(g["pending"]) for g in view.values())
    L = [f"# 審核單：Plan 9.19 S2 A／B／C＋I 修正後重新先審（{len(targets)} 條）", "",
         f"> 審閱的正本版本：commit `{CANON_COMMIT}`。本單由 `scratchpad/p919_s2_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。",
         f"> 合計：pass {tot_p}／doubt {tot_d}／未先審 {tot_u}。",
         "> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。",
         "> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。",
         "> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。", ""]
    for cid, g in view.items():
        n = len(g["titles"])
        flags = (" ⚠️" if warn(g) else "") + (" ⛔ 本組有未先審細目，不可整組回「過」" if g["pending"] else "")
        L.append(f"## {g['title']} `{cid}`（待審 {n} 條：pass {len(g['pass'])}／doubt {len(g['doubt'])}／未先審 {len(g['pending'])}）{flags}")
        L.append("")
        for fid in g["pass"]:
            L.append(f"- [pass] `{fid}` {g['titles'][fid]}")
        for fid in g["doubt"]:
            r = results[fid]
            L.append(f"- [doubt] `{fid}` {g['titles'][fid]} —— {r['sentence']}：{r['reason']}")
        for fid in g["pending"]:
            L.append(f"- [未先審] `{fid}` {g['titles'][fid]}")
        for fid in g["hold"]:
            L.append(f"- [hold] `{fid}` {g['titles'][fid]} —— 業主已裁列下個計畫刪除，⛔ 標已審（先審判定：{results[fid]['verdict']}）")
        L += ["", "回覆：", ""]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"wrote {out}: groups {len(view)}, pass {tot_p} / doubt {tot_d} / pending {tot_u}")
    return 0


def cmd_check(sheet, raw_dir):
    targets = set(load(TARGETS))
    batches = load(BATCHES)
    results = load(RESULTS)
    mism = []
    # (1) raw <-> results
    raw, errors = parse_raw(raw_dir, batches)
    mism += [f"raw-parse: {e}" for e in errors]
    for fid in sorted(set(raw) | set(results)):
        a, b = raw.get(fid, {}).get("verdict"), results.get(fid, {}).get("verdict")
        if a != b:
            mism.append(f"raw<->results {fid}: raw={a} results={b}")
    # (2) sheet <-> results
    view = group_view(results, targets)
    parsed, cur, flag_w, flag_p = {}, None, {}, {}
    with open(sheet, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^## .* `([^`]+)`（.*）(.*)$", line.rstrip("\n"))
            if m:
                cur = m.group(1)
                parsed[cur] = {"pass": [], "doubt": [], "pending": [], "hold": []}
                flag_w[cur] = "⚠️" in m.group(2)
                flag_p[cur] = "未先審細目" in m.group(2)
                continue
            m = re.match(r"^- \[(pass|doubt|未先審|hold)\] `([^`]+)`", line)
            if m and cur:
                parsed[cur]["pending" if m.group(1) == "未先審" else m.group(1)].append(m.group(2))
    sheet_ids = [i for g in parsed.values() for k in g.values() for i in k]
    for fid in sorted(set(sheet_ids) - targets):
        mism.append(f"sheet has non-target id {fid}")
    if len(sheet_ids) != len(set(sheet_ids)):
        mism.append("sheet lists an id more than once")
    for cid in sorted(set(view) | set(parsed)):
        g, p = view.get(cid), parsed.get(cid)
        if g is None or p is None:
            mism.append(f"group {cid} present in only one of sheet/results")
            continue
        for k in ("pass", "doubt", "pending", "hold"):
            for fid in sorted(set(g[k]) ^ set(p[k])):
                mism.append(f"sheet<->results {cid} [{k}] {fid}")
        if flag_w[cid] != warn(g):
            mism.append(f"⚠️ flag wrong for {cid}")
        if flag_p[cid] != bool(g["pending"]):
            mism.append(f"pending flag wrong for {cid}")
    sheet_hold = {f for g in parsed.values() for f in g["hold"]}
    if sheet_hold != (HOLD & set(results)):
        mism.append(f"hold marks: sheet {sorted(sheet_hold)} vs expected {sorted(HOLD & set(results))}")
    if sorted(sheet_ids) != sorted(targets):
        mism.append(f"sheet coverage: sheet ids {len(sheet_ids)} vs targets {len(targets)} (missing {len(targets - set(sheet_ids))})")
    judged = {f for f in results}
    print(f"[check] targets {len(targets)}; judged {len(judged)}; raw-parsed {len(raw)}; sheet ids {len(sheet_ids)}")
    print(f"[check] mismatches: {len(mism)}")
    for x in mism:
        print("[check]  ", x)
    return 1 if mism else 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "parse":
        sys.exit(cmd_parse())
    if cmd == "sheet":
        sys.exit(cmd_sheet(sys.argv[2]))
    if cmd == "check":
        rd = sys.argv[sys.argv.index("--raw-dir") + 1] if "--raw-dir" in sys.argv else SP
        sys.exit(cmd_check(sys.argv[2], rd))
