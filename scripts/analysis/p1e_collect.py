#!/usr/bin/env python3
"""P1e-1：從盲標代理 transcript 抽出標註，做合議統計（⛔ 不寫 DB）。

合議規則（協議凍結於標註之前，⛔ 不得事後調整）：
```text
兩者皆 instance → instance ｜ 兩者皆 general → general
其餘任何組合    → 保持 UNKNOWN（含一方 undecidable、兩方相反）
```
"""
import json
import os
import re
import sys
from collections import Counter

LABELS = {"instance", "general", "undecidable"}
LINE = re.compile(r"^(\d+)\s+(instance|general|undecidable)\s*$")


def extract(path):
    """回 {id: label}——取 transcript 內**最後一則**含標註行的 assistant 文字。"""
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


def main(task_dir, a_ids, b_ids):
    a, b = {}, {}
    for tid in a_ids:
        a.update(extract(os.path.join(task_dir, f"{tid}.output")))
    for tid in b_ids:
        b.update(extract(os.path.join(task_dir, f"{tid}.output")))
    print(f"標註者 A：{len(a)} 筆｜標註者 B：{len(b)} 筆")
    if not a or not b:
        print("❌ 有一方為空——大聲失敗，不當成「沒有結果」")
        return 1
    ids = sorted(set(a) | set(b))
    consensus, detail = {}, []
    for i in ids:
        la, lb = a.get(i), b.get(i)
        if la == lb and la in ("instance", "general"):
            consensus[i] = la
        detail.append({"id": i, "a": la, "b": lb, "consensus": consensus.get(i)})
    c = Counter(v for v in consensus.values())
    both = [d for d in detail if d["a"] and d["b"]]
    agree = sum(1 for d in both if d["a"] == d["b"])
    print(f"雙方皆有標註：{len(both)} 筆｜逐筆一致：{agree}（{100.0*agree/len(both):.1f}%）")
    print(f"合議 instance：{c.get('instance',0)}｜合議 general：{c.get('general',0)}"
          f"｜保持 UNKNOWN：{len(ids)-len(consensus)}")
    print("── 分歧型態 ──")
    for k, n in Counter((d["a"], d["b"]) for d in both if d["a"] != d["b"]).most_common(8):
        print(f"   A={k[0]:12s} B={k[1]:12s} {n:3d}")
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p1e_labels.json")
    json.dump(detail, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"逐筆 → {dest}")
    return 0


if __name__ == "__main__":
    T = "/private/tmp/claude-501/-Users-lenny-jgb-AIChatbot/0e7aab52-e213-4609-8b02-e195682af4ea/tasks"
    A = ["af7dcf7d3c311e77c", "ad64fb41a8d04b060", "ab12a07c16c72706a"]
    B = ["ad11d68727dbd9e49", "a336292ed2971b6dd", "a5c9a04fdebe482e9"]
    sys.exit(main(T, A, B))
