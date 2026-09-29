#!/usr/bin/env python3
"""Plan 9.19 S1 (copy of p918_edit.py): edit one fine in drafts-A/B/C/I.json; evidence sentence_index is remapped while keeping the file format byte-stable.

  python3 p916_edit.py --roundtrip                 # prove load+dump is byte-identical (no write)
  python3 p916_edit.py <fine_id> < ops.json        # apply ops to that fine
ops: {"title": str?, "set": {"<i>": str}?, "delete": [i]?, "insert_after": {"<i>": [str]}?,
      "add_sources": [str]?, "remove_sources": [str]?, "evidence": any?}
Sentence indices always refer to the fine's sentences BEFORE this call. Only doubt fines may be edited.
"""
import json
import os
import sys

RUNS = os.environ.get("P919_RUNS", "/Users/chenqinghuang/dev/work/AIChatbot/.claude/skills/outline-curation/runs/outline-20260920")  # override only for scratch pre-runs
SP = os.path.dirname(os.path.abspath(__file__))
TRAIL = {"A": "", "B": "\n", "C": "", "I": "\n"}  # Plan 9.19 S1: measured per shelf


def dump(shelf, d):
    return json.dumps(d, ensure_ascii=False, indent=1) + TRAIL[shelf]


def path(shelf):
    return os.path.join(RUNS, f"drafts-{shelf}.json")


def main():
    if sys.argv[1] == "--roundtrip":
        for s in "ABCI":
            raw = open(path(s), encoding="utf-8").read()
            ok = dump(s, json.loads(raw)) == raw
            print(s, "roundtrip byte-identical:", ok)
            if not ok:
                return 1
        return 0
    fid = sys.argv[1]
    ops = json.load(sys.stdin)
    doubt = set(json.load(open(os.environ["ALLOWED"], encoding="utf-8")))
    if fid not in doubt:
        raise SystemExit(f"❌ {fid} is not in the doubt set; editing it is out of S2 scope")
    shelf = fid.split("/")[1]
    d = json.load(open(path(shelf), encoding="utf-8"))
    hit = [f for c in d["coarses"] for f in c["fines"] if f["proposed_id"] == fid]
    if len(hit) != 1:
        raise SystemExit(f"❌ {fid} found {len(hit)} times")
    f = hit[0]
    old = list(f["sentences"])
    if "evidence" in ops:
        raise SystemExit("❌ the whole-evidence overwrite op is disabled in p919; use evidence_add")
    new = []
    newpos = {}  # old index -> new index (absent = deleted)
    dels = set(ops.get("delete", []))
    sets = {int(k): v for k, v in ops.get("set", {}).items()}
    ins = {int(k): v for k, v in ops.get("insert_after", {}).items()}
    if -1 in ins:  # -1 = before every old sentence
        new.extend(ins[-1])
    for i, s in enumerate(old):
        if i not in dels:
            newpos[i] = len(new)
            new.append(sets.get(i, s))
        new.extend(ins.get(i, []))
    bad = [k for k in list(sets) + list(dels) + [k for k in ins if k != -1] if not 0 <= k < len(old)]
    if bad:
        raise SystemExit(f"❌ index out of range: {bad}")
    ev = []
    for e in f.get("evidence") or []:
        k = e.get("sentence_index")
        if isinstance(k, int) and 0 <= k < len(old):
            if k in newpos:
                ev.append(dict(e, sentence_index=newpos[k]))
            # evidence of a deleted sentence is dropped
        else:
            ev.append(e)  # pre-existing out-of-range entries are kept untouched (not repaired here)
    for e in ops.get("evidence_add", []):  # indices refer to sentences AFTER this call
        if set(e) != {"sentence_index", "source", "quote_or_symbol"}:
            raise SystemExit(f"❌ evidence_add keys must be sentence_index/source/quote_or_symbol: {e}")
        if not 0 <= e["sentence_index"] < len(new):
            raise SystemExit(f"❌ evidence_add index out of range: {e}")
        ev.append(e)
    f["evidence"] = sorted(ev, key=lambda e: (e.get("sentence_index") if isinstance(e.get("sentence_index"), int) else 10**6))
    f["sentences"] = new
    if "title" in ops:
        f["title"] = ops["title"]
    for s in ops.get("remove_sources", []):
        f["sources"].remove(s)
    for s in ops.get("add_sources", []):
        if s not in f["sources"]:
            f["sources"].append(s)
    if "phrasings" in ops:
        f["phrasings"] = ops["phrasings"]
    if not f["sentences"]:
        raise SystemExit("❌ all sentences removed: use the fine-deletion path instead")
    with open(path(shelf), "w", encoding="utf-8") as fh:
        fh.write(dump(shelf, d))
    print(f"{fid}: {len(old)} -> {len(new)} sentences")
    for i, s in enumerate(new):
        print(f"  [{i}] {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
