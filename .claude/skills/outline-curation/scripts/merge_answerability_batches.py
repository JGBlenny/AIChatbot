#!/usr/bin/env python3
"""合併多批 Workflow Reconcile 回傳（分批 fresh run 取代 resume），輸出單一 run_result 給 finalize_answerability.py。

決定性：labels 依 cell_id 排序；total／agree／agentsUsed 逐批相加；agreementRate＝agree/total；
needs_rubric_revision＝agreementRate < 0.90（與 outline-curation.js 同一門檻）。
批與批的 frozenAt／rubricSha／inputsSha 必須完全一致，否則 exit 2（不同凍結材料不能併成一份試作）。
另附 fineIdAgreementRate（同一格兩位一致判者 fine_id 相同的比率；label 不一致格不計）——只供報告，⛔ 不進門檻。
"""
import argparse, json, sys


def merge(batches: list) -> dict:
    if not batches:
        raise SystemExit("[merge] 沒有批次")
    head = {k: batches[0].get(k) for k in ("step", "frozenAt", "rubricSha", "inputsSha")}
    for i, b in enumerate(batches):
        for k, v in head.items():
            if b.get(k) != v:
                raise SystemExit(f"[merge] 批 {i} 的 {k} 與批 0 不一致，不能合併")
    labels = sorted((e for b in batches for e in b.get("labels", [])), key=lambda e: e["cell_id"])
    ids = [e["cell_id"] for e in labels]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"[merge] cell_id 重複：{sorted({x for x in ids if ids.count(x) > 1})}")
    total = len(labels)
    agree = sum(int(b.get("agree", 0)) for b in batches)
    agents = sum(int(b.get("agentsUsed", 0)) for b in batches)
    rate = agree / total if total else 0.0
    fine_pairs = [e for e in labels if len(e.get("verdicts", [])) >= 2 and e["verdicts"][0]["label"] == e["verdicts"][1]["label"]]
    fine_agree = sum(1 for e in fine_pairs if e["verdicts"][0]["fine_id"] == e["verdicts"][1]["fine_id"])
    return {
        **head,
        "total": total,
        "agree": agree,
        "agreementRate": rate,
        "needs_rubric_revision": rate < 0.90,
        "agentsUsed": agents,
        "labels": labels,
        "batches": len(batches),
        "fineIdAgreement": {"pairs": len(fine_pairs), "agree": fine_agree,
                             "rate": (fine_agree / len(fine_pairs)) if fine_pairs else None},
        "labelCounts": {k: sum(1 for e in labels if e["label"] == k)
                        for k in ("answerable", "partial", "no_source", "deliberate_no")},
        "unresolved": [e["cell_id"] for e in labels if e.get("unresolved")],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("batches", nargs="+", help="各批 Reconcile 回傳 JSON")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    merged = merge([json.load(open(f, encoding="utf-8")) for f in a.batches])
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    print(f"[merge] batches={merged['batches']} total={merged['total']} agree={merged['agree']} "
          f"rate={merged['agreementRate']:.3f} fine_id={merged['fineIdAgreement']} counts={merged['labelCounts']} "
          f"needs_rubric_revision={merged['needs_rubric_revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
