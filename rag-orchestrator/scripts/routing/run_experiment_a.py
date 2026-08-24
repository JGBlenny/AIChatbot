#!/usr/bin/env python3
"""Experiment A：D1-member-1 / D3-member-1 **首次執行**（paired discrimination）。

⚠️ 讀取的全為**已凍結** artifact：cohort／labels／D1 spec／D3 contract／evaluator rules。
⚠️ 兩 member **同一 evaluator class／model／config／output schema／execution protocol**，
   唯一差異為 provenance source。
⚠️ 必跑 negative control：`fake_evidence = f(similarity, category)` 的 impostor。
"""
import argparse, asyncio, io, json, os, sys
sys.path.insert(0, "/app"); sys.path.insert(0, "/app/services")

E = "/.kiro/specs/routing-authority-model/evidence/"
MODEL = (os.getenv("RELEVANCE_GATE_MODEL") or os.getenv("LLM_MODEL")
         or os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
ENTRY_CLASS = "diagnostic_facet_entry"       # 三個 Face 皆為診斷面向
ENTITY_CLASS = "bill"


def _j(p):
    return json.load(io.open(p, encoding="utf-8"))


def _ask(rules, context, query):
    from services.llm_provider import chat_completion
    r = chat_completion(model=MODEL, temperature=0, max_tokens=200,
                        messages=[{"role": "system", "content": rules},
                                  {"role": "user", "content": f"{context}\n\n問句：{query}"}])
    raw = (r.get("content") or "").strip()
    try:
        s = raw[raw.index("{"):raw.rindex("}") + 1]
        v = json.loads(s).get("applicability", "").strip()
    except Exception:
        v = ""
    return (v if v in ("applicable", "not_applicable", "undecidable") else "undecidable"), raw[:120]


async def main(out):
    cohort = _j(E + "round1-challenge-cohort-frozen.json")
    labels = {r["item_id"]: r for r in _j(E + "round1-blind-labels.json")["labels"]}
    d1_spec = _j(E + "d1-routing-applicability-spec-v1.json")
    d3_ctr = _j(E + "d3-face-responsibility-contract-v1.json")
    d1_rules = io.open(E + "d1-evaluator-rules-v1.txt", encoding="utf-8").read()
    d3_rules = io.open(E + "d3-evaluator-rules-v1.txt", encoding="utf-8").read()
    ec = next(c for c in d1_spec["entry_classes"] if c["entry_class"] == ENTRY_CLASS)
    d1_ctx = ("routing applicability specification（entry class）：\n"
              + json.dumps(ec, ensure_ascii=False, indent=1)
              + f"\n本次 entry 的 entity class：{ENTITY_CLASS}")
    faces = {f["face_key"]: f for f in d3_ctr["faces"]}

    rows = []
    for p in cohort["pairs"]:
        for side in ("a", "b"):
            iid = f'{p["pair_id"]}-{side}'
            q = p[f"question_{side}"]
            fk = p["face_key"]
            d1v, d1raw = _ask(d1_rules, d1_ctx, q)
            d3v, d3raw = _ask(d3_rules,
                              "該面向的 responsibility contract：\n"
                              + json.dumps(faces[fk], ensure_ascii=False, indent=1), q)
            rows.append({"item_id": iid, "pair_id": p["pair_id"], "face_key": fk, "query": q,
                         "label": labels[iid]["judgement"], "label_conf": labels[iid]["confidence"],
                         "d1": d1v, "d1_raw": d1raw, "d3": d3v, "d3_raw": d3raw})

    # ── negative control：impostor（只看 similarity/category，語義一律不看）──
    #    以「同一 Face 的所有句子 category 相同」為前提：impostor 對同 Face 必給同一答案
    imp = {}
    for r in rows:
        imp.setdefault(r["face_key"], "applicable")   # f(category) → 常數
    for r in rows:
        r["impostor"] = imp[r["face_key"]]

    by_pair = {}
    for r in rows:
        by_pair.setdefault(r["pair_id"], []).append(r)
    scored = {k: v for k, v in by_pair.items()
              if len(v) == 2 and "undecidable" not in {x["label"] for x in v}
              and v[0]["label"] != v[1]["label"]}

    def disc(key):
        ok = [k for k, v in scored.items() if v[0][key] != v[1][key]]
        agree = [x for v in scored.values() for x in v if x[key] == x["label"]]
        return {"paired_discrimination": f"{len(ok)}/{len(scored)}",
                "item_agreement": f"{len(agree)}/{len(scored)*2}",
                "failed_pairs": [k for k in scored if k not in ok]}

    out_obj = {"task": "Experiment A — first member execution（paired discrimination）",
               "frozen_inputs": {"cohort_digest": cohort["cohort_digest"],
                                 "labels_digest": _j(E + "round1-blind-labels.json")["labels_digest"],
                                 "d1_spec_digest": d1_spec["spec_digest"],
                                 "d3_contract_digest": d3_ctr["contract_digest"]},
               "model": MODEL, "scored_pairs": len(scored),
               "D1-member-1": disc("d1"), "D3-member-1": disc("d3"),
               "NEGATIVE_CONTROL_impostor": disc("impostor"),
               "impostor_definition": "f(category)：同一 Face 的所有句子給同一答案（不看語義）",
               "rows": rows}
    io.open(out, "w", encoding="utf-8").write(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n")
    print(f"[A] pairs={len(scored)}｜D1 {out_obj['D1-member-1']['paired_discrimination']}"
          f"｜D3 {out_obj['D3-member-1']['paired_discrimination']}"
          f"｜impostor {out_obj['NEGATIVE_CONTROL_impostor']['paired_discrimination']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/app/experiment_a.json")
    asyncio.run(main(ap.parse_args().out))
