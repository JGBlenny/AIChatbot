#!/usr/bin/env python3
"""跨輪比較工具（R2.5 可重現性｜任務 0.8 的算法本體）。

**為什麼要進 repo**：0.8 的四個數字（E-5 12/104、等價 4/107、平移 13/85 與 2/85）
原本由 /tmp 的一次性腳本算出，腳本消失後**無人能重跑驗證**——
凍結了判準與母體，卻沒凍結算法，等於半套。本工具是那個算法本體。

三種比較模式：

  e5      同碼同輪次的 N 輪 pairwise 不一致（E-5 基線）
          母體＝全輪扣 testcase（noise_manifest.usage_rules.routing_determinism_e5）
          尺＝verdict 複合鍵 (routing_verdict, grounded, answer_verdict)

  equiv   兩臂各 N 輪的逐輪多數決比較（等價驗證）
          尺＝legacy 文字（兩臂皆產得出；UNSTABLE 側不計入不一致，R1.3.4 禁混計）

  shift   對照臂 vs 平移臂（R7.2）
          母體＝**對照臂 N 輪全一致的輪**——系統重跑噪音本身就 12 輪，
          用全母體會把訊號淹掉（0.8 報告 §1 的實測依據）

用法：
  python3 compare_runs.py e5    --runs backtest_e5r1 backtest_e5r2 backtest_e5r3
  python3 compare_runs.py equiv --arm-a backtest_preA1 backtest_preA2 backtest_preA3 \
                                --arm-b backtest_e5r1 backtest_e5r2 backtest_e5r3
  python3 compare_runs.py shift --control backtest_e5r1 backtest_e5r2 backtest_e5r3 \
                                --arm backtest_shm1 backtest_shm2 backtest_shm3

加 --json 輸出機器可讀結果（供關卡報告引用）。
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from scripts.backtest import decision_replay as dr        # noqa: E402


def _dir(tag):
    return os.path.join(dr.CORPUS_DIR, f"out_{tag}_cacheoff")


def load_verdict(tag):
    """verdict 尺：直讀 _turn_results_v2.json。"""
    with open(os.path.join(_dir(tag), "_turn_results_v2.json"), encoding="utf-8") as f:
        return {(k.split("|")[0], int(k.split("|")[1])): v for k, v in json.load(f).items()}


def load_legacy(tag):
    """legacy 文字尺：自逐案 replay 重判（舊檔無快照時唯一可用的尺）。"""
    out = {}
    for p in glob.glob(os.path.join(_dir(tag), "[0-9]*.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        cid = d["turn_results"][0]["case_id"] if d.get("turn_results") else None
        for rp in d["replay"]:
            out[(cid, rp["turn"])] = dr.turn_result_legacy(
                cid, rp["turn"], answer=rp.get("answer"), sources=rp.get("sources"))
    return out


def legacy_key(tr):
    return (tr["legacy_class"], tr["grounded"])


def e5_population(rounds):
    """E-5 母體：全輪扣 testcase 案（noise_manifest.usage_rules.routing_determinism_e5）。"""
    m = dr.load_manifest()
    tc = {c for c, v in m["cases"].items() if "testcase" in (v.get("case_tags") or [])}
    ks = set.intersection(*[set(r) for r in rounds])
    return {k for k in ks if k[0] not in tc}


def pairwise(rounds, ks, keyfn):
    return [sum(1 for k in ks if keyfn(rounds[i][k]) != keyfn(rounds[j][k]))
            for i in range(len(rounds)) for j in range(i + 1, len(rounds))]


def majority(rounds, k, keyfn):
    c, n = collections.Counter(keyfn(r[k]) for r in rounds).most_common(1)[0]
    return c if n * 2 > len(rounds) or n >= 2 else "UNSTABLE"


def cmd_e5(a):
    rounds = [load_verdict(t) for t in a.runs]
    ks = e5_population(rounds)
    pw = pairwise(rounds, ks, dr.composite_key_v2)
    pv = pairwise(rounds, ks, lambda t: t["routing_verdict"])
    pg = pairwise(rounds, ks, lambda t: t["grounded"])
    pa = pairwise(rounds, ks, lambda t: t["answer_verdict"])
    miss = sum(1 for r in rounds for v in r.values() if v["source"] == "missing")
    flip = [k for k in sorted(ks)
            if len({dr.composite_key_v2(r[k]) for r in rounds}) > 1]
    res = {"mode": "e5", "runs": a.runs, "population": len(ks),
           "pairwise": pw, "median": statistics.median(pw),
           "pct": round(100 * statistics.median(pw) / len(ks), 1),
           "by_dimension": {"routing_verdict": pv, "grounded": pg, "answer_verdict": pa},
           "flipped_turns": [f"{c}|{t}" for c, t in flip],
           "snapshot_missing": miss}
    if not a.json:
        print(f"═══ E-5｜{len(a.runs)} 輪｜母體 {len(ks)} 輪 ═══")
        print(f"  複合鍵 pairwise：{pw}  中位 {res['median']}（{res['pct']}%）")
        print(f"    routing_verdict {pv}｜grounded {pg}｜answer_verdict {pa}")
        print(f"  曾翻動的輪：{len(flip)}")
        print(f"  快照缺漏：{miss}")
    return res


def cmd_equiv(a):
    A = [load_legacy(t) for t in a.arm_a]
    B = [load_legacy(t) for t in a.arm_b]
    ks = set.intersection(*[set(r) for r in A + B])
    pwa, pwb = pairwise(A, ks, legacy_key), pairwise(B, ks, legacy_key)
    # UNSTABLE 側不計入「多數決不同」——那是「該側無多數決」，不是「兩側多數決不同」
    diff, uns = [], []
    for k in sorted(ks):
        ma, mb = majority(A, k, legacy_key), majority(B, k, legacy_key)
        if "UNSTABLE" in (ma, mb):
            uns.append(k)
        elif ma != mb:
            diff.append(k)
    base = max(statistics.median(pwa), statistics.median(pwb))
    res = {"mode": "equiv", "ruler": "legacy_text", "population": len(ks),
           "arm_a_pairwise": pwa, "arm_b_pairwise": pwb,
           "majority_diff": len(diff),
           "majority_diff_turns": [f"{c}|{t}" for c, t in diff],
           "unstable": len(uns), "baseline_variance": base,
           "pass": len(diff) <= base}
    if not a.json:
        print(f"═══ 等價｜legacy 文字尺｜{len(ks)} 輪 ═══")
        print("  ⚠ legacy 尺看不見 stay_facet 細分與 verdict，禁與 verdict 尺混計（R1.3.4）")
        print(f"  A 臂輪內：{pwa} 中位 {statistics.median(pwa)}")
        print(f"  B 臂輪內：{pwb} 中位 {statistics.median(pwb)}")
        print(f"  ★ 多數決不同：{len(diff)}／{len(ks)}  {res['majority_diff_turns']}")
        print(f"    UNSTABLE（不計入）：{len(uns)}")
        print(f"  判準 {len(diff)} ≤ 基線變異 {base} ？ "
              f"{'✅ PASS' if res['pass'] else '❌ FAIL'}")
    return res


def cmd_shift(a):
    C = [load_verdict(t) for t in a.control]
    S = [load_verdict(t) for t in a.arm]
    allk = e5_population(C)
    # 母體＝對照臂全一致輪：系統重跑噪音本身就 12 輪，全母體會淹掉平移訊號
    stable = {k for k in allk if len({dr.composite_key_v2(r[k]) for r in C}) == 1}
    ks = stable & set.intersection(*[set(r) for r in S])
    diff, uns = [], []
    for k in sorted(ks):
        ms = majority(S, k, dr.composite_key_v2)
        if ms == "UNSTABLE":
            uns.append(k)
        elif majority(C, k, dr.composite_key_v2) != ms:
            diff.append(k)
    # A 型＝面向⇄非面向（進場受分數支配）；B 型＝其餘（檢索過濾等）
    def is_facet(v):
        return v is not None and ("facet" in v)
    atype = [k for k in diff
             if is_facet(majority(C, k, dr.composite_key_v2)[0])
             != is_facet(majority(S, k, dr.composite_key_v2)[0])]
    pw = pairwise(S, ks, dr.composite_key_v2)
    res = {"mode": "shift", "control": a.control, "arm": a.arm,
           "population_all": len(allk), "population_stable": len(ks),
           "shifted": len(diff), "shifted_turns": [f"{c}|{t}" for c, t in diff],
           "type_a_facet_boundary": len(atype),
           "type_a_turns": [f"{c}|{t}" for c, t in atype],
           "arm_internal_pairwise": pw, "arm_unstable": len(uns)}
    if not a.json:
        print(f"═══ 平移｜母體＝對照臂全一致輪 {len(ks)}／{len(allk)} ═══")
        print(f"  平移臂輪內噪音：{pw} 中位 {statistics.median(pw)}")
        print(f"  ★ 對照 vs 平移，多數決不同：{len(diff)}")
        for c, t in diff:
            mark = " [A型/面向邊界]" if (c, t) in atype else ""
            print(f"      #{c} T{t:<2} {majority(C,(c,t),dr.composite_key_v2)} → "
                  f"{majority(S,(c,t),dr.composite_key_v2)}{mark}")
        print(f"    其中 A 型（面向⇄非面向）：{len(atype)}")
        print(f"  平移臂 UNSTABLE：{len(uns)}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("e5", "equiv", "shift"))
    ap.add_argument("--runs", nargs="+"); ap.add_argument("--arm-a", nargs="+")
    ap.add_argument("--arm-b", nargs="+"); ap.add_argument("--control", nargs="+")
    ap.add_argument("--arm", nargs="+"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = {"e5": cmd_e5, "equiv": cmd_equiv, "shift": cmd_shift}[a.mode](a)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
