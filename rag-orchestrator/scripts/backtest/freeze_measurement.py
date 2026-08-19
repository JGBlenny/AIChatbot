#!/usr/bin/env python3
"""量測前凍結（R2.5／D-16）：把判準、母體分母、雜訊標記、尺版本鎖成一份快照。

**為什麼需要**：反證盤查發現「及格線與分母留在被驗證方手上」是本 spec 的系統性缺陷之一
——「低於預先聲明的上限」而該數值全 spec 從未出現、基線由實作方量、雜訊標記由實作方寫
且未凍結。**基線量得越吵，及格門越寬。** 此工具把四件事在量測前釘死，
量測後任一項變更即為換尺，須重跑前後兩側。

用法：
    python3 freeze_measurement.py --label v0-remeasure --note "0.8 新尺重測基線"
    python3 freeze_measurement.py --verify frozen/v0-remeasure.json   # 事後核對有無漂移

輸出：`docs/backtest/corpus-20260810/frozen/<label>.json`（進版控）。
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from scripts.backtest import decision_replay as dr        # noqa: E402

FROZEN_DIR = os.path.join(dr.CORPUS_DIR, "frozen")


def _sha(obj):
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def _file_sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def snapshot():
    """四件事的當下狀態（R2.5 明列項）。"""
    manifest = dr.load_manifest()
    exp_path = os.path.join(dr.CORPUS_DIR, "expected_answers.json")
    exp = None
    if os.path.exists(exp_path):
        with open(exp_path, encoding="utf-8") as f:
            exp = json.load(f)
    return {
        # ① 判準與及格線——未核定者顯式標 null，不得留白讓人事後填
        "criteria": {
            "e5_upper_bound": None,          # R8.2：待業主於 0.8 後核定
            "r72_shift_upper_bound": None,   # R7.2：同上
            "equivalence_rule": "逐輪多數決複合鍵不一致率 ≤ 同側重跑變異中位數",
            "answer_population_rule": "母體內任一 unjudged 即 FAIL；母體外揭露佔比",
        },
        # ② 統計母體與分母
        "population": {
            "routing_determinism_turns": manifest["totals"]["routing_determinism_turns"],
            "knowledge_coverage_turns": manifest["totals"]["knowledge_coverage_turns"],
            "total_turns": manifest["totals"]["turns"],
            "answer_population": (len(exp["entries"]) if exp else None),
        },
        # ③ 雜訊標記
        "noise_manifest": {"version": manifest.get("manifest_version"),
                           "sha": _file_sha(os.path.join(dr.CORPUS_DIR, "noise_manifest.json"))},
        # ④ 尺的版本（含模型/規則的選擇方式——EXP-7 揭露的漏洞：只寫「深度≤3」
        #    未凍結選法，若當初凍結深度 2 則判準結論會翻）
        "ruler": {
            "verdict_domain": list(dr.ROUTING_VERDICTS),
            "composite_key": ["routing_verdict", "grounded", "answer_verdict"],
            "legacy_classifier_version": dr.classifier_version(),
            "selection_rule": "verdict 直讀決策快照，無模型擬合、無可調參數",
            "known_defect_pairs": {f"{k[0]}|{k[1]}": [a, b]
                                   for k, (a, b) in dr.DOCUMENTED_DEFECT_PAIRS.items()},
        },
        "expected_answers": {"sha": (dr.expected_answers_hash(exp) if exp else None),
                             "breakdown": (dr.expected_answers_breakdown(exp) if exp else None)},
    }


def freeze(label, note):
    os.makedirs(FROZEN_DIR, exist_ok=True)
    snap = snapshot()
    doc = {"label": label, "note": note, "frozen_snapshot": snap, "sha": _sha(snap)}
    path = os.path.join(FROZEN_DIR, f"{label}.json")
    if os.path.exists(path):
        print(f"💥 {label} 已存在——凍結不得覆寫（要重凍請換 label 並說明理由）", file=sys.stderr)
        return 2
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 已凍結 {label}（sha {doc['sha']}）→ {path}")
    for k, v in snap["population"].items():
        print(f"   母體 {k}: {v}")
    print(f"   及格線: {snap['criteria']['e5_upper_bound']}"
          f"（None＝待業主核定，量測後不得由實作方自填）")
    return 0


def verify(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    now = snapshot()
    if _sha(now) == doc["sha"]:
        print(f"✅ 與 {doc['label']} 凍結時一致（sha {doc['sha']}）")
        return 0
    print(f"💥 已漂移——凍結後有東西被改動，本輪量測結果不可與凍結時比較（R2.5）")
    old, new = doc["frozen_snapshot"], now
    for sec in old:
        if old[sec] != new.get(sec):
            print(f"  [{sec}]\n    凍結: {json.dumps(old[sec], ensure_ascii=False)[:200]}"
                  f"\n    現在: {json.dumps(new.get(sec), ensure_ascii=False)[:200]}")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label"); ap.add_argument("--note", default="")
    ap.add_argument("--verify")
    a = ap.parse_args()
    if a.verify:
        return verify(a.verify)
    if not a.label:
        ap.error("需要 --label 或 --verify")
    return freeze(a.label, a.note)


if __name__ == "__main__":
    sys.exit(main())
