#!/usr/bin/env python3
"""A03 步驟 1–3：integrity ／ label quality（**四類 raw**）／ semantic corpus sufficiency。

判準逐字取自已凍結的 `authorization-A03-protocol.md`，⛔ 未調整：
```text
【2】L1 >= 90%、κ >= 0.70，**直接在四類 raw labels 上算**
     ⛔ 禁止把 INSTANCE vs CONTEXT_DEPENDENT 或 CONTEXT_DEPENDENT vs UNDECIDABLE
        事後合併成 agreement
【3】G1/G2/G3 各 SEMANTICALLY_JUDGEABLE >= 15/20
     I1–I7 explicit 各 >= 8/10          ⛔ 不得 pooled 補足
Layer Q：兩位皆 I 或皆 G → SEMANTICALLY_JUDGEABLE
        任一方 CONTEXT_DEPENDENT 且無 G↔I 實質衝突 → CONTEXT_DEPENDENT
        真正 G vs I 衝突 → LABEL_DISAGREEMENT｜其餘 → UNDECIDABLE
⚠️ CONTEXT_DEPENDENT **刻意不設下限**——只完整報告分布
```
"""
import json
import os
import re
import sys
from collections import Counter

LINE = re.compile(r"^(\d+)\s+(instance|general|context_dependent|undecidable)\s*$")
L1_MIN, K_MIN = 0.90, 0.70
G_MIN, EXPLICIT_MIN = 15, 8


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
    return (Counter(re.findall(r'"name":"([A-Za-z]+)"', blob)),
            set(re.findall(r'"file_path":"([^"]+)"', blob)))


def kappa(la, lb):
    n = len(la)
    po = sum(1 for x, y in zip(la, lb) if x == y) / n
    if len(set(la)) < 2 or len(set(lb)) < 2:
        return None, po, "某標註者只用單一標籤 ⇒ 變異數 0 ⇒ κ 無定義"
    ca, cb = Counter(la), Counter(lb)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if abs(1 - pe) < 1e-12:
        return None, po, "pe = 1 ⇒ κ 無定義"
    return (po - pe) / (1 - pe), po, ""


def layer_q(a, b):
    if a == b and a in ("instance", "general"):
        return "SEMANTICALLY_JUDGEABLE"
    if {a, b} == {"instance", "general"}:
        return "LABEL_DISAGREEMENT"
    if "context_dependent" in (a, b) and "undecidable" not in (a, b):
        return "CONTEXT_DEPENDENT"
    return "UNDECIDABLE"


def main(corpus_path, a_out, b_out):
    corpus = json.load(open(corpus_path, encoding="utf-8"))
    rows = {r["i"]: r for r in corpus["utterances"]}
    n = corpus["n"]
    a, b = extract(a_out), extract(b_out)
    print(f"corpus n={n} digest={corpus['digest']}")

    fail = []
    for name, lab in (("A", a), ("B", b)):
        if len(lab) != n:
            fail.append(f"{name} {len(lab)} ≠ {n}")
        if [i for i in lab if not (1 <= i <= n)] or [i for i in range(1, n + 1) if i not in lab]:
            fail.append(f"{name} 序號不完整")
    for name, path in (("A", a_out), ("B", b_out)):
        t, f = tools(path)
        print(f"  {name} 工具：{dict(t)}｜讀檔數 {len(f)}")
        if {k: v for k, v in t.items() if k != "Read"} or len(f) != 1:
            fail.append(f"{name} 違反 isolation contract")
    if fail:
        print("❌ PROCEDURAL_INVALID：" + "；".join(fail))
        return 1
    print("【1】integrity ✅")

    ids = sorted(a)
    la, lb = [a[i] for i in ids], [b[i] for i in ids]
    k, po, note = kappa(la, lb)
    ok2 = (k is not None and po >= L1_MIN and k >= K_MIN)
    print(f"\n【2】label quality（**四類 raw**，⛔ 未合併任何類別）")
    print(f"   L1 = {po*100:.1f}%（>= 90%） {'✅' if po>=L1_MIN else '❌'}")
    print(f"   κ  = {'UNDEFINED（'+note+'）' if k is None else f'{k:.3f}'}（>= 0.70）"
          f" {'✅' if (k is not None and k>=K_MIN) else '❌'}")
    print(f"   A={dict(Counter(la))}")
    print(f"   B={dict(Counter(lb))}")

    q = {i: layer_q(a[i], b[i]) for i in ids}
    print(f"\n   Layer Q 分布：{dict(Counter(q.values()))}")

    print(f"\n【3】semantic corpus sufficiency（⛔ 不得 pooled）")
    units_g = ["G1", "G2", "G3"]
    units_x = [f"I{i}-explicit" for i in range(1, 8)]
    judge = Counter(rows[i]["unit"] for i in ids if q[i] == "SEMANTICALLY_JUDGEABLE")
    bad = []
    for u in units_g:
        v = judge.get(u, 0); ok = v >= G_MIN
        bad += [] if ok else [u]
        print(f"   {u:16s} judgeable {v:2d}/20 (>= {G_MIN}) {'✅' if ok else '❌'}")
    for u in units_x:
        v = judge.get(u, 0); ok = v >= EXPLICIT_MIN
        bad += [] if ok else [u]
        print(f"   {u:16s} judgeable {v:2d}/10 (>= {EXPLICIT_MIN}) {'✅' if ok else '❌'}")

    print(f"\n   ⚠️ elliptical 四類分布（**刻意不設門檻**，僅完整報告）")
    for i_ in range(1, 8):
        u = f"I{i_}-elliptical"
        c = Counter(q[i] for i in ids if rows[i]["unit"] == u)
        print(f"   {u:16s} {dict(c)}")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a03_labels.json")
    json.dump({"corpus_digest": corpus["digest"], "a": a, "b": b,
               "layer_q": q, "L1": po, "kappa": k, "kappa_note": note},
              open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nlabels → {dest}")

    if not ok2:
        print("❌ **A03-LABELS = INCONCLUSIVE**（整輪停）")
        return 1
    print("✅ A03-LABELS = PASS")
    if bad:
        print(f"❌ **A03-SEMANTIC = INCONCLUSIVE ／ SEMANTIC_CORPUS_INSUFFICIENT**：{bad}")
        return 1
    print("✅ semantic corpus sufficiency 通過 —— 可進入第【4】關（BURN 點）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
