# -*- coding: utf-8 -*-
"""Plan 9.28 抽查 brief：由 aggregate.py --sample-out 的 20 句（[細目 id, 句序]）與 jgb.json 機械產生。
用法：python3 gen_spot.py <sample.json> <HEAD 全碼> <jgb2 匯出路徑> <輸出 brief 路徑>
⛔ 告知批次判定；每句只列所屬細目標題、該句原文、sources。"""
import json, os, sys

REPO = "/Users/chenqinghuang/dev/work/AIChatbot"
sample, HEAD, JGB2, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
SP = os.path.dirname(os.path.abspath(__file__))
canon = json.load(open(REPO + "/rag-orchestrator/canon/jgb.json", encoding="utf-8"))
F = {f["id"]: f for c in canon["coarses"] for f in c["fines"]}
S = json.load(open(sample, encoding="utf-8"))
assert len(S) == 20 and len({tuple(x) for x in S}) == 20
items = []
for fid, n in S:
    f = F[fid]
    items.append(f"### {fid} 句 {n}\n- 所屬細目標題：{f['title']}\n- 句子：{f['content_units'][n - 1]}\n- sources："
                 + "；".join(f"`{s}`" for s in f["sources"]))
t = open(SP + "/spot-template.txt", encoding="utf-8").read()
t = t.replace("{{HEAD}}", HEAD).replace("{{JGB2}}", JGB2).replace("{{BODY}}", "\n\n".join(items))
assert "{{" not in t
open(OUT, "w", encoding="utf-8").write(t)
print("spot brief", len(t))
