#!/usr/bin/env python3
"""建立 **30 個 reviewed_active responsibility 的 canonical embeddings**（C2-SCORE，業主裁定 2026-08-30）。

⚠️ 這是 sealed Registry V2 的 **derived runtime artifact**，⛔ 不是 authority source
   ——⛔ 不得回寫 registry-v2.json。

## 角色鎖死

```text
row／alias embeddings          → nomination ／ recall
canonical responsibility embeddings → **final semantic vector component**（collapse ＋ top20 之後）
⛔ C2-v1 ⛔ 不新增「canonical vector recall arm」——否則同時改 recall architecture，因果變髒。
```

## 重建條件（任一成立即必須重建）

```text
① canonical text 改      → canonical_text_digest 變
② Registry authority epoch 改 → registry_v2_digest 變
③ embedding model／版本改 → embedding_model_id 變
```

用法（容器內）：python3 tools/build_canonical_embeddings.py [--out DIR]
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.embedding_utils import generate_embedding  # noqa: E402

DEFAULT_REGISTRY = "/spec/registry-v2.json"
MODEL_INFO_URL = os.getenv("EMBEDDING_INFO_URL", "http://embedding-api:5000/")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def model_id() -> str:
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(MODEL_INFO_URL)
        r.raise_for_status()
        d = r.json()
    return f"{d.get('model')}@{d.get('version')}"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--out", default="/spec/derived")
    args = ap.parse_args()

    with open(args.registry, "rb") as f:
        raw = f.read()
    reg = json.loads(raw)
    reg_digest = hashlib.sha256(raw).hexdigest()
    if reg.get("seal_status") != "sealed":
        print("❌ registry 未 sealed——⛔ 不得對未封存的 authority 建 derived artifact")
        return 1

    active = [r for r in reg["responsibilities"] if r["status"] == "reviewed_active"]
    # ⚠️ 大聲失敗：canonical 未閉合就 ⛔ 不得建 index（否則會產生半套 semantic surface）
    missing = [r["responsibility_id"] for r in active
               if not r.get("canonical_responsibility")
               or (r.get("canonical_review") or {}).get("verdict") != "APPROVED"]
    if missing:
        print(f"❌ 這些 active responsibility 的 canonical 尚未 APPROVED：{missing}")
        return 1
    hist = [r for r in reg["responsibilities"] if r["status"] != "reviewed_active"]

    mid = await model_id()
    entries, dim = [], None
    for r in sorted(active, key=lambda x: x["responsibility_id"]):
        text = r["canonical_responsibility"]
        emb = await generate_embedding(text)
        if not emb:
            print(f"❌ {r['responsibility_id']} embedding 生成失敗——⛔ 不得以零向量或略過帶過")
            return 1
        if dim is None:
            dim = len(emb)
        elif len(emb) != dim:
            print(f"❌ {r['responsibility_id']} 維度不一致：{len(emb)} ≠ {dim}")
            return 1
        entries.append({"responsibility_id": r["responsibility_id"],
                        "canonical_text_digest": sha(text),
                        "embedding_checksum": sha(",".join(f"{x:.8f}" for x in emb)),
                        "embedding": emb})

    os.makedirs(args.out, exist_ok=True)
    index = {
        "_doc": "C2-SCORE canonical responsibility embeddings（derived runtime artifact）。",
        "_authority": "⛔ NONE——authority 在 registry-v2.json；本檔是它的 derived index，"
                      "⛔ 不得回寫 registry。",
        "_role": "collapse ＋ top20 **之後**的 responsibility semantic vector component；"
                 "⛔ 不參與 recall（C2-v1 ⛔ 不新增 canonical vector recall arm）。",
        "registry_v2_digest": reg_digest,
        "embedding_model_id": mid,
        "embedding_dimension": dim,
        "count": len(entries),
        "excluded": {"reviewed_historical": [r["responsibility_id"] for r in hist],
                     "_why": "⛔ historical 與 16 個 unresolved rows 一律不建 embedding"},
        "_rebuild_triggers": ["canonical text 改（canonical_text_digest）",
                             "registry authority epoch 改（registry_v2_digest）",
                             "embedding model／版本改（embedding_model_id）"],
        "entries": entries,
    }
    path = os.path.join(args.out, "canonical-embeddings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
        f.write("\n")
    manifest = {k: v for k, v in index.items() if k != "entries"}
    manifest["entries"] = [{k: v for k, v in e.items() if k != "embedding"} for e in entries]
    manifest["embeddings_file_digest"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    mpath = os.path.join(args.out, "canonical-embeddings-manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"✅ {len(entries)} 筆／dim={dim}／model={mid}")
    print(f"   {path}")
    print(f"   {mpath}")
    print(f"   EMBEDDINGS_FILE_DIGEST={manifest['embeddings_file_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
