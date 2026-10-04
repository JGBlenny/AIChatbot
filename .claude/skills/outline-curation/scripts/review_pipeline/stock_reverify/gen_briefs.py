# -*- coding: utf-8 -*-
"""Plan 9.28：由 jgb.json＋batches.json＋decoys.py 機械產生 24 份批次 brief 與誘餌清單。
用法：python3 gen_briefs.py <HEAD 全碼> <jgb2 匯出路徑> <輸出目錄>
每批混入 1 條誘餌（位置由種子 20261011＋批號決定）；誘餌 id＝<shelf>/<來源 slug>-d<批號>。"""
import hashlib, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decoys import DECOYS

REPO = "/Users/chenqinghuang/dev/work/AIChatbot"
HEAD, JGB2, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SP = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
canon = json.load(open(REPO + "/rag-orchestrator/canon/jgb.json", encoding="utf-8"))
F = {f["id"]: f for c in canon["coarses"] for f in c["fines"]}
batches = json.load(open(SP + "/batches.json", encoding="utf-8"))
assert len(batches) == len(DECOYS) == 24, (len(batches), len(DECOYS))
sha = lambda units: hashlib.sha256("\n".join(units).encode("utf-8")).hexdigest()
TEMPLATE = open(SP + "/brief-template.txt", encoding="utf-8").read()


def block(fid, title, units, sources, csha):
    lines = [f"### {fid}", f"- content_sha256: `{csha}`", f"- 標題：{title}", "- 句子："]
    lines += [f"  {i}. {u}" for i, u in enumerate(units, 1)]
    lines += ["- sources：" + "；".join(f"`{s}`" for s in sources)]
    return "\n".join(lines)


manifest = []
TITLES = {f["title"] for f in F.values()}
for bi, (b, (src, n, old, new, slug, dtitle)) in enumerate(zip(batches, DECOYS), 1):
    f = F[src]
    units = list(f["content_units"])
    assert units[n - 1].count(old) == 1, (src, n)
    units[n - 1] = units[n - 1].replace(old, new)
    did = src.rsplit("/", 1)[0] + "/" + slug
    assert did not in F, did
    assert dtitle not in TITLES, dtitle
    decoy = {"id": did, "title": dtitle, "units": units, "sources": f["sources"], "sha": sha(units),
             "from": src, "n": n}
    items = [(x, F[x]["title"], F[x]["content_units"], F[x]["sources"], F[x]["content_sha256"]) for x in b["fines"]]
    for x, _, u, _, s in items:
        assert sha(u) == s, x
    pos = random.Random(20261011 + bi).randrange(len(items) + 1)
    items.insert(pos, (did, decoy["title"], units, decoy["sources"], decoy["sha"]))
    body = "\n\n".join(block(*it) for it in items)
    ids = [it[0] for it in items]
    brief = (TEMPLATE.replace("{{BATCH}}", b["batch"]).replace("{{HEAD}}", HEAD).replace("{{JGB2}}", JGB2)
             .replace("{{N}}", str(len(items))).replace("{{S}}", str(sum(len(it[2]) for it in items)))
             .replace("{{IDS}}", "\n".join(ids)).replace("{{BODY}}", body))
    assert "{{" not in brief
    open(f"{OUT}/brief-{b['batch']}.txt", "w", encoding="utf-8").write(brief)
    manifest.append({"batch": b["batch"], "decoy_id": did, "from": src, "sentence": n, "old": old, "new": new,
                     "decoy_sha": decoy["sha"], "decoy_title": dtitle, "fines": b["fines"], "position": pos})
json.dump(manifest, open(f"{OUT}/decoy-manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("briefs", len(manifest), "max chars", max(os.path.getsize(f"{OUT}/brief-{m['batch']}.txt") for m in manifest))
