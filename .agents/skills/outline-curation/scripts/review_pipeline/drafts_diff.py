#!/usr/bin/env python3
"""Plan 9.18 S1 (copy of p916_s2_drafts_diff.py): mechanical diff of drafts-<SHELVES> against the backup, checked against the fix log.

Usage:
  python3 p916_s2_drafts_diff.py --base <backup runs dir> --cur <runs dir> \
      --doubt <doubt-ids.json> [--fix-log <fix-log md>] [--list]

Checks (every counter is printed even when 0; any failure exits 1):
  (a) set of changed/deleted items == set of fix-log table rows
  (b) changed fine ids are a subset of the doubt set
  (c) every D/E fine outside the doubt set has 0 changes in any field, phrasings included
  (d) deleted fine ids == fix-log "## 刪除" section
  (e) every fix-log row has verifier verdict 「過」, or its action is 刪句 / 刪細目
  (f) structural differences == 0 (fine id set, coarse list/titles/order, membership/order, top-level keys)
Without --fix-log only (b)(c)(f) and the item list are checked (for positive-control runs).
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

SHELVES = tuple(os.environ.get("P919_DIFF_SHELVES", "ABCI"))  # Plan 9.19 S1


def load(d: str, shelf: str) -> dict:
    with open(os.path.join(d, f"drafts-{shelf}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def fines_of(draft: dict) -> dict:
    return {f["proposed_id"]: f for c in draft["coarses"] for f in c["fines"]}


def item_diff(base: dict, cur: dict) -> set:
    """Return {(fid, field, idx, action)}; idx is always the base-side sentence index ('' for other fields)."""
    items: set = set()
    bf, cf = fines_of(base), fines_of(cur)
    for fid, b in bf.items():
        if fid not in cf:
            items.add((fid, "fine", "", "刪細目"))
            continue
        c = cf[fid]
        for field in sorted(set(b) | set(c)):
            bv, cv = b.get(field), c.get(field)
            if bv == cv:
                continue
            if field == "sentences" and isinstance(bv, list) and isinstance(cv, list):
                sm = difflib.SequenceMatcher(a=bv, b=cv, autojunk=False)
                for op, i1, i2, j1, j2 in sm.get_opcodes():
                    if op == "equal":
                        continue
                    if op == "replace":
                        n = min(i2 - i1, j2 - j1)
                        for k in range(n):
                            items.add((fid, "sentences", str(i1 + k), "改"))
                        for k in range(i1 + n, i2):
                            items.add((fid, "sentences", str(k), "刪句"))
                        for _ in range(j1 + n, j2):
                            items.add((fid, "sentences", str(i1 + n), "新增句"))
                    elif op == "delete":
                        for k in range(i1, i2):
                            items.add((fid, "sentences", str(k), "刪句"))
                    elif op == "insert":
                        items.add((fid, "sentences", str(i1), "新增句"))
            else:
                items.add((fid, field, "", "改"))
    return items


def structural_diff(base: dict, cur: dict, deleted: set) -> list:
    out: list = []
    if sorted(k for k in base if k != "coarses") != sorted(k for k in cur if k != "coarses"):
        out.append(f"top-level keys differ: {sorted(base)} vs {sorted(cur)}")
    for k in base:
        if k != "coarses" and k in cur and base[k] != cur[k]:
            out.append(f"top-level value differs: {k}")
    bt = [c["coarse"] for c in base["coarses"]]
    ct = [c["coarse"] for c in cur["coarses"]]
    if bt != ct:
        out.append(f"coarse list/titles/order differ: {bt} vs {ct}")
    for bc, cc in zip(base["coarses"], cur["coarses"]):
        if {k: v for k, v in bc.items() if k != "fines"} != {k: v for k, v in cc.items() if k != "fines"}:
            out.append(f"coarse-level field differs under {bc['coarse']!r}")
    added = set(fines_of(cur)) - set(fines_of(base))
    for fid in sorted(added):
        out.append(f"added fine id: {fid}")
    cur_members = {c["coarse"]: [f["proposed_id"] for f in c["fines"]] for c in cur["coarses"]}
    for c in base["coarses"]:
        expect = [f["proposed_id"] for f in c["fines"] if f["proposed_id"] not in deleted]
        got = [fid for fid in cur_members.get(c["coarse"], []) if fid not in added]
        if expect != got:
            moved = sorted(set(expect) ^ set(got))
            out.append(f"membership/order differs under {c['coarse']!r}: {moved or 'order only'}")
    return out


_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")


def parse_fix_log(path: str) -> tuple[set, dict, set]:
    rows: set = set()
    verdict: dict = {}
    deleted: set = set()
    section = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            if section == "刪除":
                m = re.match(r"^- `([^`]+)`", line)
                if m:
                    deleted.add(m.group(1))
                continue
            m = _ROW.match(line)
            if m:
                fid, field, idx, action, _basis, v = m.groups()
                key = (fid, field, idx, action)
                if key in rows:
                    raise SystemExit(f"❌ fix log has a duplicate row: {key}")
                rows.add(key)
                verdict[key] = v
    return rows, verdict, deleted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--cur", required=True)
    ap.add_argument("--doubt", required=True, help="JSON list of doubt fine ids (61 + B7 doubt)")
    ap.add_argument("--fix-log")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    with open(a.doubt, encoding="utf-8") as fh:
        doubt = set(json.load(fh))
    if not doubt:
        raise SystemExit("❌ empty doubt set: precondition missing")

    items: set = set()
    all_fids: set = set()
    struct: list = []
    log_rows: set = set()
    log_verdict: dict = {}
    log_deleted: set = set()
    if a.fix_log:
        log_rows, log_verdict, log_deleted = parse_fix_log(a.fix_log)
    for shelf in SHELVES:
        b, c = load(a.base, shelf), load(a.cur, shelf)
        all_fids |= set(fines_of(b))
        items |= item_diff(b, c)
        deleted_here = {i[0] for i in items if i[3] == "刪細目"}
        struct += [f"[{shelf}] {s}" for s in structural_diff(b, c, deleted_here)]

    missing_doubt = sorted(doubt - all_fids)
    changed = {i[0] for i in items}
    deleted = {i[0] for i in items if i[3] == "刪細目"}
    out_of_scope = sorted(changed - doubt)
    protected_changed = sorted(i for i in items if i[0] not in doubt)
    # Plan 9.19: evidence changes on allowed fines are mechanical remaps by p919_edit.py -> checked here, not logged
    ev_items = {i for i in items if i[1] == "evidence" and i[0] in doubt}
    ev_bad = []
    for shelf in SHELVES:
        bf, cf = fines_of(load(a.base, shelf)), fines_of(load(a.cur, shelf))
        for fid in sorted(i[0] for i in ev_items if i[0] in cf and i[0] in bf):
            oob = lambda f: sum(1 for e in f.get("evidence") or [] if not (isinstance(e.get("sentence_index"), int) and 0 <= e["sentence_index"] < len(f["sentences"])))
            if oob(cf[fid]) > oob(bf[fid]):
                ev_bad.append(f"{fid}: out-of-range evidence {oob(bf[fid])} -> {oob(cf[fid])}")
    items = items - ev_items
    print(f"[diff] (g) evidence remaps on allowed fines: {len(ev_items)}; new out-of-range: {len(ev_bad)}")
    for x in ev_bad:
        print(f"[diff]   {x}")

    print(f"[diff] fines in base (shelves {''.join(SHELVES)}): {len(all_fids)}; doubt set: {len(doubt)} (not found in base: {len(missing_doubt)})")
    print(f"[diff] changed/deleted items: {len(items)} in {len(changed)} fines; deleted fines: {len(deleted)}")
    print(f"[diff] (b) changed ids outside doubt set: {len(out_of_scope)}")
    print(f"[diff] (c) items on protected (non-doubt) fines: {len(protected_changed)}")
    print(f"[diff] (f) structural differences: {len(struct)}")
    for s in struct:
        print(f"[diff]   {s}")
    for i in protected_changed:
        print(f"[diff]   protected changed: {i}")
    if a.list:
        for i in sorted(items):
            print("[item]", "｜".join(i))

    fails = bool(missing_doubt) or bool(out_of_scope) or bool(protected_changed) or bool(struct) or bool(ev_bad)
    if a.fix_log:
        extra = sorted(log_rows - items)
        unlogged = sorted(items - log_rows)
        bad_verdict = sorted(k for k in log_rows if log_verdict[k] != "過" and k[3] not in ("刪句", "刪細目"))
        print(f"[diff] (a) fix-log rows: {len(log_rows)}; unlogged diffs: {len(unlogged)}; log rows with no diff: {len(extra)}")
        print(f"[diff] (d) deleted fines: diff {len(deleted)} vs fix-log 刪除 {len(log_deleted)}; equal: {deleted == log_deleted}")
        print(f"[diff] (e) rows not passed and not a deletion: {len(bad_verdict)}")
        for k in unlogged:
            print(f"[diff]   unlogged: {k}")
        for k in extra:
            print(f"[diff]   log-only: {k}")
        for k in bad_verdict:
            print(f"[diff]   verdict: {k} -> {log_verdict[k]!r}")
        fails = fails or bool(extra) or bool(unlogged) or deleted != log_deleted or bool(bad_verdict)
    print("[diff] RESULT:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
