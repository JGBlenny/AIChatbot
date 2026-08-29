#!/usr/bin/env python3
"""A02 步驟 3–5：integrity ＋ label quality ＋ **per-stratum corpus sufficiency**。

判準逐字取自已凍結的 `authorization-A02-protocol.md`，⛔ 未作任何調整：
```text
L1 exact agreement >= 90%｜L2 Cohen's kappa >= 0.70｜κ 無定義 → LABELING_INCONCLUSIVE
每個 stratum judgeable >= 15/20，否則 CORPUS_INSUFFICIENT
  「有效」＝ authoring integrity 通過 AND 兩位一致 AND label ∈ {instance, general}
  ⛔ 不得以 general 合併 45 掩蓋某 stratum 只剩 8
```
"""
import json
import os
import re
import sys
from collections import Counter

LINE = re.compile(r"^(\d+)\s+(instance|general|undecidable)\s*$")
L1_MIN, L2_MIN, STRATUM_MIN = 0.90, 0.70, 15
STRATA = ["G1", "G2", "G3", "I1", "I2", "I3", "I4", "I5", "I6", "I7"]


def extract(path):
    best = {}
    for raw in open(path, encoding="utf-8"):
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        texts = []

        def walk(o):
            if isinstance(o, dict):
                if o.get("type") == "text" and isinstance(o.get("text"), str):
                    texts.append(o["text"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(rec)
        for t in texts:
            got = {}
            for line in t.splitlines():
                m = LINE.match(line.strip())
                if m:
                    got[int(m.group(1))] = m.group(2)
            if len(got) > len(best):
                best = got
    return best


def tools(path):
    blob = open(path, encoding="utf-8").read()
    return Counter(re.findall(r'"name":"([A-Za-z]+)"', blob)), set(re.findall(r'"file_path":"([^"]+)"', blob))


def kappa(a, b, ids):
    la, lb = [a[i] for i in ids], [b[i] for i in ids]
    n = len(ids)
    po = sum(1 for x, y in zip(la, lb) if x == y) / n
    if len(set(la)) < 2 or len(set(lb)) < 2:
        return None, po, "某標註者只用了單一標籤 ⇒ 變異數 0 ⇒ κ 無定義"
    ca, cb = Counter(la), Counter(lb)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if abs(1 - pe) < 1e-12:
        return None, po, "pe = 1 ⇒ κ 無定義"
    return (po - pe) / (1 - pe), po, ""


def main(corpus_path, a_out, b_out):
    corpus = json.load(open(corpus_path, encoding="utf-8"))
    rows = {r["i"]: r for r in corpus["utterances"]}
    n_expect = corpus["n"]
    a, b = extract(a_out), extract(b_out)
    print(f"corpus n={n_expect} digest={corpus['digest']}")
    print(f"標註者 A：{len(a)}｜B：{len(b)}")

    fail = []
    for name, lab in (("A", a), ("B", b)):
        if len(lab) != n_expect:
            fail.append(f"{name} 標註數 {len(lab)} ≠ {n_expect}")
        if [i for i in lab if not (1 <= i <= n_expect)]:
            fail.append(f"{name} 有越界／幻覺序號")
        if [i for i in range(1, n_expect + 1) if i not in lab]:
            fail.append(f"{name} 有漏標")
    for name, path in (("A", a_out), ("B", b_out)):
        t, f = tools(path)
        print(f"  {name} 工具：{dict(t)}｜讀檔數：{len(f)}")
        if {k: v for k, v in t.items() if k != "Read"}:
            fail.append(f"{name} 違反 isolation contract")
        if len(f) != 1:
            fail.append(f"{name} 讀了 {len(f)} 個檔")
    if fail:
        print("\n❌ PROCEDURAL_INVALID：" + "；".join(fail))
        return 1
    print("① integrity ✅")

    ids = sorted(set(a) & set(b))
    k, po, note = kappa(a, b, ids)
    print(f"\n② label quality")
    print(f"   L1 exact agreement = {po*100:.1f}%（>= {L1_MIN*100:.0f}%）"
          f" {'✅' if po>=L1_MIN else '❌'}")
    print(f"   L2 Cohen's kappa   = {'UNDEFINED（'+note+'）' if k is None else f'{k:.3f}'}"
          f"（>= {L2_MIN}） {'✅' if (k is not None and k>=L2_MIN) else '❌'}")
    print(f"   分布 A={dict(Counter(a[i] for i in ids))}｜B={dict(Counter(b[i] for i in ids))}")

    truth = {i: a[i] for i in ids if a[i] == b[i] and a[i] in ("instance", "general")}
    print(f"\n③ corpus sufficiency（**每 stratum** judgeable >= {STRATUM_MIN}／20）")
    per = Counter(rows[i]["stratum"] for i in truth)
    insufficient = []
    for s in STRATA:
        n = per.get(s, 0)
        ok = n >= STRATUM_MIN
        if not ok:
            insufficient.append(s)
        print(f"   {s}: {n:2d}/20 {'✅' if ok else '❌'}")
    print(f"   總 judgeable {len(truth)}（instance {sum(1 for v in truth.values() if v=='instance')}"
          f"／general {sum(1 for v in truth.values() if v=='general')}）")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a02_labels.json")
    json.dump({"corpus_digest": corpus["digest"], "a": a, "b": b, "truth": truth,
               "L1": po, "kappa": k, "kappa_note": note,
               "per_stratum_judgeable": dict(per)},
              open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nlabels → {dest}")

    if k is None or po < L1_MIN or k < L2_MIN:
        print("❌ **LABELING_INCONCLUSIVE**")
        return 1
    if insufficient:
        print(f"❌ **CORPUS_INSUFFICIENT**（不足的 stratum：{insufficient}）")
        return 1
    print("✅ label quality ＋ corpus sufficiency 全過 —— 可進入步驟 7（跑 frozen implementation）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
