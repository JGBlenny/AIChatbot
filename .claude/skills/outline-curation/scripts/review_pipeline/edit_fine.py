#!/usr/bin/env python3
"""Plan 9.19 S1 (copy of p918_edit.py): edit one fine in drafts-A/B/C/I.json; evidence sentence_index is remapped while keeping the file format byte-stable.

  python3 p916_edit.py --roundtrip                 # prove load+dump is byte-identical (no write)
  python3 p916_edit.py <fine_id> < ops.json        # apply ops to that fine
ops: {"title": str?, "set": {"<i>": str}?, "delete": [i]?, "insert_after": {"<i>": [str]}?,
      "add_sources": [str]?, "remove_sources": [str]?, "evidence": any?}
Sentence indices always refer to the fine's sentences BEFORE this call. Only doubt fines may be edited.
Plan 9.30 whole-fine ops (each must be the only key): {"remove_fine": true} (fine must also be in env REMOVE=<json>);
  {"rewrite_fine": {title, sentences, phrasings, sources, evidence, not_supported_greps, open_questions}} (all 7 required;
  proposed_id/askable/unit_ids/target_user/business_types/instance_applicability are refused).
"""
import json
import os
import sys

RUNS = os.environ.get("P919_RUNS", "/Users/chenqinghuang/dev/work/AIChatbot/.claude/skills/outline-curation/runs/outline-20260920")  # override only for scratch pre-runs
SP = os.path.dirname(os.path.abspath(__file__))
TRAIL = {"A": "", "B": "\n", "C": "", "D": "\n", "E": "", "F": "", "G": "", "I": "\n"}  # Plan 9.19 S1 + 9.29 (D–G): measured per shelf; H is not byte-stable, never edit it


def dump(shelf, d):
    return json.dumps(d, ensure_ascii=False, indent=1) + TRAIL[shelf]


def path(shelf):
    return os.path.join(RUNS, f"drafts-{shelf}.json")


REWRITE_KEYS = {"title", "sentences", "phrasings", "sources", "evidence", "not_supported_greps", "open_questions"}
FROZEN_KEYS = {"proposed_id", "askable", "unit_ids", "target_user", "business_types", "instance_applicability"}


def whole_fine(shelf, d, fid, f, ops):
    """Plan 9.30: {"remove_fine": true} (fid must also be in env REMOVE) or {"rewrite_fine": {7 keys}}."""
    if len(ops) != 1:
        raise SystemExit(f"❌ remove_fine/rewrite_fine must be the only op key: {sorted(ops)}")
    if "remove_fine" in ops:
        if ops["remove_fine"] is not True:
            raise SystemExit("❌ remove_fine must be true")
        remove = set(json.load(open(os.environ["REMOVE"], encoding="utf-8")))
        if fid not in remove:
            raise SystemExit(f"❌ {fid} is not in the REMOVE set; removing it is out of scope")
        for c in d["coarses"]:
            c["fines"] = [x for x in c["fines"] if x["proposed_id"] != fid]
        with open(path(shelf), "w", encoding="utf-8") as fh:
            fh.write(dump(shelf, d))
        print(f"{fid}: removed")
        return 0
    rw = ops["rewrite_fine"]
    if not isinstance(rw, dict):
        raise SystemExit("❌ rewrite_fine must be an object")
    frozen = sorted(set(rw) & FROZEN_KEYS)
    if frozen:
        raise SystemExit(f"❌ rewrite_fine may not change {frozen}; those need the owner")
    if set(rw) != REWRITE_KEYS:
        raise SystemExit(f"❌ rewrite_fine keys must be exactly {sorted(REWRITE_KEYS)}: missing {sorted(REWRITE_KEYS - set(rw))}, extra {sorted(set(rw) - REWRITE_KEYS)}")
    if not isinstance(rw["title"], str) or not rw["title"].strip():
        raise SystemExit("❌ rewrite_fine.title must be a non-empty string")
    for k in ("sentences", "phrasings", "sources"):
        if not isinstance(rw[k], list) or not rw[k] or not all(isinstance(x, str) and x.strip() for x in rw[k]):
            raise SystemExit(f"❌ rewrite_fine.{k} must be a non-empty list of non-empty strings")
    for k in ("evidence", "not_supported_greps", "open_questions"):
        if not isinstance(rw[k], list):
            raise SystemExit(f"❌ rewrite_fine.{k} must be a list (give [] when empty)")
    n = len(rw["sentences"])
    for e in rw["evidence"]:
        if set(e) != {"sentence_index", "source", "quote_or_symbol"}:
            raise SystemExit(f"❌ evidence keys must be sentence_index/source/quote_or_symbol: {e}")
        if not isinstance(e["sentence_index"], int) or not 0 <= e["sentence_index"] < n:
            raise SystemExit(f"❌ evidence sentence_index out of range 0..{n - 1}: {e}")
    missing = sorted(set(range(n)) - {e["sentence_index"] for e in rw["evidence"]})
    if missing:
        raise SystemExit(f"❌ sentences without evidence: {missing}")
    for k in REWRITE_KEYS:
        f[k] = rw[k]
    f["evidence"] = sorted(f["evidence"], key=lambda e: e["sentence_index"])
    with open(path(shelf), "w", encoding="utf-8") as fh:
        fh.write(dump(shelf, d))
    print(f"{fid}: rewritten, {n} sentences")
    for i, s in enumerate(f["sentences"]):
        print(f"  [{i}] {s}")
    return 0


def main():
    if sys.argv[1] == "--roundtrip":
        for s in "ABCDEFGI":
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
    if "remove_fine" in ops or "rewrite_fine" in ops:  # Plan 9.30: whole-fine ops never mix with sentence ops
        return whole_fine(shelf, d, fid, f, ops)
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
