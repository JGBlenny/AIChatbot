#!/usr/bin/env python3
"""Plan 9.19 (copy of p918_approved.py + HOLD exclusion; generalized copy of p917_s2_approved.py; env P918_WRITE_SHELVES required, P918_SHEET/P918_PLAN_SECTION for derive): owner decision -> approved id list (two independent derivations), and post-write verification.

  python3 p917_s2_approved.py derive <decision.json> [--sheet SHEET] [--out OUT]
  python3 p917_s2_approved.py verify <approved.json> --backup <backup canon dir> [--canon <canon dir>]

decision.json (written from the owner's verbatim reply, which is first recorded in plan §6):
  {"reply": "<業主原文>",
   "rule": "safe" | "all" | "none",      # safe = every non-⚠️ group's pass ids; all = every group's pass ids
   "warn_groups": ["<coarse id>", ...],  # ⚠️ groups the owner named as 過 (their pass ids only)
   "doubt_as_is": ["<fine id>", ...],    # doubt ids the owner named 照原樣過
   "exclude": ["<fine id>", ...]}        # pass ids the owner explicitly withheld (must be pass ids in chosen groups)
derive also requires `reply` to appear verbatim inside plan §6「### S2」 (--plan to override the plan path).

derive: source A = review sheet lines ([pass]/[doubt] + ⚠️ flag); source B = results.json + targets + canon grouping,
        ⚠️ recomputed as doubt/targets > 30%. Writes OUT only when A == B; exits 1 on any defect.
verify: canon reviewed set == backup reviewed set ∪ approved (per id); every other .md byte-identical to backup
        except A/B/C; A/B/C diff = added `- reviewed:` lines on approved ids only; prints endpoint expectation.
"""
import filecmp
import json
import os
import re
import sys

SP = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/chenqinghuang/dev/work/AIChatbot"
CANON = os.path.join(REPO, "rag-orchestrator/canon")
SHEET = os.environ.get("P918_SHEET", "")
RESULTS = os.path.join(SP, "p919-s2-results.json")
TARGETS = os.path.join(SP, "p919-s2-targets.json")
HOLD = set(json.load(open(os.path.join(SP, "p919-s2-hold.json"), encoding="utf-8")))  # owner: delete next plan -> never approved
PLAN = os.path.join(REPO, ".kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.19-abc-fix-and-rereview-20260928.md")
PLAN_SECTION = os.environ.get("P918_PLAN_SECTION", "### S3")
WRITE_SHELVES = os.environ["P918_WRITE_SHELVES"]  # required: shelves this run may write


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def parse_canon(path):
    """{fid: {"grp", "reviewed", "tu"}} in file order."""
    fines, grp, cur = {}, None, None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r"^## .*\{#([^}]+)\}\s*$", line)
            if m:
                grp, cur = m.group(1), None
                continue
            m = re.match(r"^### .*\{#([^}]+)\}\s*$", line)
            if m:
                cur = m.group(1)
                fines[cur] = {"grp": grp, "reviewed": None, "tu": ""}
                continue
            if cur and line.startswith("- reviewed:"):
                fines[cur]["reviewed"] = line
            if cur and line.startswith("- target_user:"):
                fines[cur]["tu"] = line
    return fines


def canon_all(root):
    out = {}
    for s in "ABCDEFGHI":
        out.update(parse_canon(os.path.join(root, "jgb", f"{s}.md")))
    return out


def source_sheet(sheet):
    groups, warn, cur = {}, {}, None
    with open(sheet, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r"^## .*`([^`]+)`（待審.*）( ⚠️)?$", line)
            if m:
                cur = m.group(1)
                groups[cur] = {"pass": set(), "doubt": set()}
                warn[cur] = bool(m.group(2))
                continue
            m = re.match(r"^- \[(pass|doubt|未先審)\] `([^`]+)`", line)
            if m:
                if m.group(1) == "未先審":
                    raise SystemExit(f"❌ sheet has 未先審 fine {m.group(2)}: S2 cannot approve a partial sheet")
                groups[cur][m.group(1)].add(m.group(2))
    return groups, warn


def source_results():
    res, targets, canon = load(RESULTS), set(load(TARGETS)), canon_all(CANON)
    if set(res) != targets:
        raise SystemExit(f"❌ results ids {len(res)} != targets {len(targets)}")
    groups = {}
    for fid in targets:
        if fid in HOLD:  # excluded from approval and from the ⚠️ denominator, same as the sheet
            groups.setdefault(canon[fid]["grp"], {"pass": set(), "doubt": set()})
            continue
        g = groups.setdefault(canon[fid]["grp"], {"pass": set(), "doubt": set()})
        g[res[fid]["verdict"]].add(fid)
    warn = {c: (len(g["pass"]) + len(g["doubt"])) > 0 and len(g["doubt"]) / (len(g["pass"]) + len(g["doubt"])) > 0.30 for c, g in groups.items()}
    return groups, warn


def approve(groups, warn, dec, label):
    errs = []
    for c in dec.get("warn_groups", []):
        if c not in groups:
            errs.append(f"{label}: named group {c} not in sheet")
        elif not warn[c]:
            errs.append(f"{label}: named group {c} is not ⚠️ (rule already covers or excludes it)")
    doubts = {f for g in groups.values() for f in g["doubt"]}
    for f in dec.get("doubt_as_is", []):
        if f not in doubts:
            errs.append(f"{label}: 照原樣過 id {f} is not a doubt fine")
    rule = dec["rule"]
    if rule not in ("safe", "all", "none"):
        errs.append(f"{label}: unknown rule {rule}")
    chosen = {c for c in groups if rule == "all" or (rule == "safe" and not warn[c])} | set(dec.get("warn_groups", []))
    ids = {f for c in chosen if c in groups for f in groups[c]["pass"]}
    for f in dec.get("exclude", []):
        if f not in ids:
            errs.append(f"{label}: exclude id {f} is not a pass id in the chosen groups")
    ids = (ids - set(dec.get("exclude", []))) | set(dec.get("doubt_as_is", []))
    unknown = set(dec) - {"reply", "rule", "warn_groups", "doubt_as_is", "exclude"}
    if unknown:
        errs.append(f"{label}: unknown decision keys {sorted(unknown)}")
    return ids, errs


def cmd_derive(argv):
    dec = load(argv[0])
    sheet = argv[argv.index("--sheet") + 1] if "--sheet" in argv else SHEET
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    if not dec.get("reply"):
        raise SystemExit("❌ decision.json has no owner reply text")
    plan = argv[argv.index("--plan") + 1] if "--plan" in argv else PLAN
    text = open(plan, encoding="utf-8").read()
    if "\n## 6." not in text or "\n" + PLAN_SECTION not in text.split("\n## 6.", 1)[1]:
        raise SystemExit(f"❌ plan §6 has no「{PLAN_SECTION}」record: record the owner's verbatim reply first")
    s2 = text.split("\n## 6.", 1)[1].split("\n" + PLAN_SECTION, 1)[1].split("\n### ", 1)[0]
    if dec["reply"] not in s2:
        raise SystemExit(f"❌ decision reply is not verbatim inside plan §6 {PLAN_SECTION} record")
    a, ea = approve(*source_sheet(sheet), dec, "sheet")
    b, eb = approve(*source_results(), dec, "results")
    errs = ea + eb
    if a != b:
        errs.append(f"sheet-derived {len(a)} != results-derived {len(b)}; only-sheet {sorted(a - b)[:5]} only-results {sorted(b - a)[:5]}")
    canon = canon_all(CANON)
    pre = [f for f in a if canon[f]["reviewed"]]
    if pre:
        errs.append(f"approved ids already reviewed: {pre[:5]}")
    for e in errs:
        print("❌", e)
    if errs:
        return 1
    pm = sum("property_manager" in canon[f]["tu"] for f in a)
    pr = sum("prospect" in canon[f]["tu"] for f in a)
    by = {s: sum(f.split("/")[1] == s for f in a) for s in WRITE_SHELVES}
    print(f"[derive] approved {len(a)} (both sources equal) by shelf {by}; expected endpoint increment pm +{pm}, prospect +{pr}")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(sorted(a), fh, ensure_ascii=False, indent=1)
        print(f"[derive] wrote {out}")
    return 0


def cmd_verify(argv):
    appr = set(load(argv[0]))
    bk = argv[argv.index("--backup") + 1]
    cn = argv[argv.index("--canon") + 1] if "--canon" in argv else CANON
    cur, old = canon_all(cn), canon_all(bk)
    errs = []
    rc = {f for f, v in cur.items() if v["reviewed"]}
    rb = {f for f, v in old.items() if v["reviewed"]}
    if rc != rb | appr:
        errs.append(f"reviewed set: extra {sorted(rc - (rb | appr))[:5]} missing {sorted((rb | appr) - rc)[:5]}")
    for s in "ABCDEFGHI":
        if s in WRITE_SHELVES:
            continue
        if not filecmp.cmp(os.path.join(cn, "jgb", f"{s}.md"), os.path.join(bk, "jgb", f"{s}.md"), shallow=False):
            errs.append(f"{s}.md differs from backup")
    added = 0
    for s in WRITE_SHELVES:
        a = open(os.path.join(bk, "jgb", f"{s}.md"), encoding="utf-8").read().split("\n")
        b = open(os.path.join(cn, "jgb", f"{s}.md"), encoding="utf-8").read().split("\n")
        i = j = 0
        fid = None
        while j < len(b):
            m = re.match(r"^### .*\{#([^}]+)\}\s*$", b[j])
            if m:
                fid = m.group(1)
            if i < len(a) and a[i] == b[j]:
                i, j = i + 1, j + 1
                continue
            if b[j].startswith("- reviewed:") and fid in appr and j > 0 and b[j - 1].startswith("- sources:"):
                added, j = added + 1, j + 1
                continue
            errs.append(f"{s}.md unexpected change near line {j + 1}: {b[j][:60]!r}")
            break
        if i != len(a):
            errs.append(f"{s}.md lost lines from backup (at {i + 1})")
    if added != len(appr):
        errs.append(f"added reviewed lines {added} != approved {len(appr)}")
    # exports: CATALOG byte-identical; jgb.json differs only in approved fines' reviewed_* and top-level canon_sha256
    for rel in ("jgb/CATALOG.md", "README.md"):
        if not filecmp.cmp(os.path.join(cn, rel), os.path.join(bk, rel), shallow=False):
            errs.append(f"{rel} differs from backup")
    extra = sorted(set(os.listdir(os.path.join(cn, "jgb"))) ^ set(os.listdir(os.path.join(bk, "jgb")))) + sorted(set(os.listdir(cn)) ^ set(os.listdir(bk)))
    if extra:
        errs.append(f"canon file set differs from backup: {extra}")
    ja, jb = load(os.path.join(bk, "jgb.json")), load(os.path.join(cn, "jgb.json"))
    if {k: v for k, v in ja.items() if k not in ("coarses", "canon_sha256")} != {k: v for k, v in jb.items() if k not in ("coarses", "canon_sha256")}:
        errs.append("jgb.json top-level fields other than canon_sha256 changed")
    fa = {f["id"]: f for c in ja["coarses"] for f in c["fines"]}
    fb = {f["id"]: f for c in jb["coarses"] for f in c["fines"]}
    if [c["id"] for c in ja["coarses"]] != [c["id"] for c in jb["coarses"]] or list(fa) != list(fb):
        errs.append("jgb.json coarse/fine order or membership changed")
    strip = lambda c: {k: v for k, v in c.items() if k != "fines"}
    if [strip(c) for c in ja["coarses"]] != [strip(c) for c in jb["coarses"]]:
        errs.append("jgb.json coarse-level fields changed")
    json_changed = 0
    for fid in fa:
        if fid not in fb:
            continue
        x, y = dict(fa[fid]), dict(fb[fid])
        if fid in appr:
            if not y.get("reviewed_at") or y.get("reviewed_by") != "owner":
                errs.append(f"jgb.json {fid} missing reviewed_* after write")
            for k in ("reviewed_at", "reviewed_by"):
                x.pop(k, None), y.pop(k, None)
        if x != y:
            json_changed += 1
            if json_changed <= 5:
                errs.append(f"jgb.json {fid} changed beyond reviewed_*: {sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))}")
    jr = sum(1 for f in fb.values() if f.get("reviewed_at"))
    print(f"[verify] jgb.json reviewed fines {jr}; fines changed beyond reviewed_*: {json_changed}")
    pm = sum("property_manager" in cur[f]["tu"] for f in rc)
    pr = sum("prospect" in cur[f]["tu"] for f in rc)
    print(f"[verify] reviewed backup {len(rb)} -> current {len(rc)}; added lines {added}; approved {len(appr)}")
    print(f"[verify] reviewed fines pm {pm}, prospect {pr}")
    print(f"[verify] mismatches: {len(errs)}")
    for e in errs:
        print("[verify]  ", e)
    return 1 if errs else 0


def cmd_write(argv):
    """write <approved.json> --date YYYY-MM-DD [--canon DIR]: insert `- reviewed:` after `- sources:` of each approved fine."""
    appr = set(load(argv[0]))
    date = argv[argv.index("--date") + 1]
    cn = argv[argv.index("--canon") + 1] if "--canon" in argv else CANON
    line_new = f"- reviewed: {{by: owner, at: {date}}}"
    done = set()
    for s in WRITE_SHELVES:
        p = os.path.join(cn, "jgb", f"{s}.md")
        lines = open(p, encoding="utf-8").read().split("\n")
        out, fid = [], None
        for k, line in enumerate(lines):
            m = re.match(r"^### .*\{#([^}]+)\}\s*$", line)
            if m:
                fid = m.group(1)
            if line.startswith("- reviewed:") and fid in appr:
                raise SystemExit(f"❌ {fid} already has a reviewed line")
            out.append(line)
            if line.startswith("- sources:") and fid in appr:
                if fid in done:
                    raise SystemExit(f"❌ {fid} has two sources lines")
                out.append(line_new)
                done.add(fid)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
    if done != appr:
        raise SystemExit(f"❌ wrote {len(done)} != approved {len(appr)}; not found {sorted(appr - done)[:5]}")
    print(f"[write] added {len(done)} reviewed lines ({line_new})")
    return 0


if __name__ == "__main__":
    cmds = {"derive": cmd_derive, "verify": cmd_verify, "write": cmd_write}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        raise SystemExit(__doc__)
    sys.exit(cmds[sys.argv[1]](sys.argv[2:]))
