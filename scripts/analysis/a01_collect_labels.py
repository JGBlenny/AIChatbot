#!/usr/bin/env python3
"""A01 步驟 3–5：收集盲標、完整性檢查、label-quality precondition（L1／L2）。

⚠️ 本腳本寫於**看到任何 label 之前**（protocol 步驟 2 進行中），
   判準逐字取自已凍結的 `authorization-protocol-frozen.md` §3B，⛔ 未作任何調整。

```text
L1  exact agreement >= 90%
L2  Cohen's kappa   >= 0.70
κ 無定義（任一標註者只用了單一標籤 ⇒ 變異數 0）→ **LABELING_INCONCLUSIVE**
  ⛔ 不得臨場補公式——那本身表示 corpus／process 沒提供足夠雙側判別資訊
judgeable truth：兩者皆 instance／皆 general；任一 undecidable 或兩者分歧 → undecidable
  ⛔ 不得由第三人事後裁決把分歧補成答案
```
"""
import json
import os
import re
import sys
from collections import Counter

LINE = re.compile(r"^(\d+)\s+(instance|general|undecidable)\s*$")
L1_MIN, L2_MIN = 0.90, 0.70


def extract(path):
    """取 transcript 內**最後一則**含最多標註行的 assistant 文字。"""
    best = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
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


def tool_isolation(path, expect_file):
    """回 (tools_used:Counter, files_read:set)——驗 frozen isolation contract。"""
    tools, files = Counter(), set()
    with open(path, encoding="utf-8") as fh:
        blob = fh.read()
    for m in re.finditer(r'"name":"([A-Za-z]+)"', blob):
        tools[m.group(1)] += 1
    for m in re.finditer(r'"file_path":"([^"]+)"', blob):
        files.add(m.group(1))
    return tools, files


def cohens_kappa(a, b, ids):
    """回 (kappa 或 None, po, 說明)。None ＝ mathematically undefined。"""
    la = [a[i] for i in ids]
    lb = [b[i] for i in ids]
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
    n_expect = corpus["n"]
    a, b = extract(a_out), extract(b_out)
    print(f"corpus n={n_expect} digest={corpus['digest']}")
    print(f"標註者 A：{len(a)} 筆｜標註者 B：{len(b)} 筆")

    fail = []
    # ── 步驟 3：完整性 ──
    for name, lab in (("A", a), ("B", b)):
        if len(lab) != n_expect:
            fail.append(f"{name} 標註數 {len(lab)} ≠ {n_expect}")
        bad = [i for i in lab if not (1 <= i <= n_expect)]
        if bad:
            fail.append(f"{name} 出現越界／幻覺序號 {bad[:5]}")
        missing = [i for i in range(1, n_expect + 1) if i not in lab]
        if missing:
            fail.append(f"{name} 漏標 {len(missing)} 筆（例：{missing[:5]}）")
    for name, path in (("A", a_out), ("B", b_out)):
        tools, files = tool_isolation(path, corpus_path)
        other = {t: c for t, c in tools.items() if t != "Read"}
        print(f"  {name} 工具使用：{dict(tools)}｜讀檔：{sorted(files)}")
        if other:
            fail.append(f"{name} 違反 isolation contract：使用了 {other}")
        if len(files) != 1:
            fail.append(f"{name} 讀了 {len(files)} 個檔（應恰為自己的語料檔）")
    if fail:
        print("\n❌ PROCEDURAL_INVALID：")
        for f in fail:
            print(f"   {f}")
        return 1

    # ── 步驟 5：label-quality precondition ──
    ids = sorted(set(a) & set(b))
    kappa, po, note = cohens_kappa(a, b, ids)
    print(f"\nL1 exact agreement = {po*100:.1f}%（門檻 {L1_MIN*100:.0f}%）")
    print(f"L2 Cohen's kappa   = {'UNDEFINED（'+note+'）' if kappa is None else f'{kappa:.3f}'}"
          f"（門檻 {L2_MIN}）")
    print(f"標註分布 A={dict(Counter(a[i] for i in ids))}｜B={dict(Counter(b[i] for i in ids))}")

    truth = {i: a[i] for i in ids
             if a[i] == b[i] and a[i] in ("instance", "general")}
    print(f"judgeable truth：{len(truth)}（instance {sum(1 for v in truth.values() if v=='instance')}"
          f"／general {sum(1 for v in truth.values() if v=='general')}）"
          f"｜undecidable {len(ids)-len(truth)}")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a01_labels.json")
    json.dump({"corpus_digest": corpus["digest"],
               "a": a, "b": b, "truth": truth,
               "L1_agreement": po, "L2_kappa": kappa, "kappa_note": note},
              open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"labels → {dest}")

    if kappa is None or po < L1_MIN or kappa < L2_MIN:
        print("\n❌ **LABELING_INCONCLUSIVE** —— ⛔ 不得進 authorization PASS／FAIL")
        return 1
    print("\n✅ label-quality precondition 通過 —— 可進入步驟 6")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
