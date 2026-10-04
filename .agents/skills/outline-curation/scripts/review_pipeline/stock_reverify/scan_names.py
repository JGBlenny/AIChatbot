# -*- coding: utf-8 -*-
"""客戶名掃描：詞表逐字取自 review_pipeline/canon_check.py 的 PAT；正對照不中 ⇒ 退出 2。用法：scan_names.py <檔>..."""
import re, sys
src = open("/Users/chenqinghuang/dev/work/AIChatbot/.claude/skills/outline-curation/scripts/review_pipeline/canon_check.py", encoding="utf-8").read()
PAT = re.compile(re.search(r'PAT = re\.compile\(r"(.+?)"\)', src).group(1))
if not PAT.search("合成正對照：喬立的合約") or PAT.search("合成負對照：系統上的設定"):
    print("⛔ 正／負對照失敗——詞表或樣式壞了"); sys.exit(2)
hits = 0
for p in sys.argv[1:]:
    for i, l in enumerate(open(p, encoding="utf-8"), 1):
        for m in PAT.finditer(l):
            hits += 1; print(f"HIT {p}:{i} 樣式 {m.re.pattern[:0]}長度 {len(m.group(0))}")
print(f"掃 {len(sys.argv) - 1} 檔；命中 {hits}（正負對照 ✅）"); sys.exit(1 if hits else 0)
