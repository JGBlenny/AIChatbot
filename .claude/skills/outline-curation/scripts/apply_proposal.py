#!/usr/bin/env python3
"""apply_proposal：把（人審後的）結構提議決定性套成正本 Markdown 草稿＋id 對應表（任務 2.3）。

- 輸入：structure-proposal envelope（取 `payload.synthesis`）或裸提議 JSON；kb 列／草稿（內容來源）；front matter 參數。
- 輸出：`<out-md>`（正本草稿，格式＝design 元件 4；⛔ 不 commit、不入庫，交業主審）＋`<out-idmap>`（`[{old,new,op}]`＋每細目前後對照）。
- 決定性：同輸入兩次逐位元相等（無時間戳；粗目依 id 排序、細目依提議順序、內容句依 merge_of 順序）。
- **未附對應表 ⇒ exit 2**：提議 `id_map` 缺、或有細目的來源不在 id_map ⇒ 拒套。
- 內容句＝來源項目 `content` 依 `provenance_units.split_sentences` 切成一行一句；產出後以 `canon_parser.parse_canon_text` 回讀驗證（失敗 exit 2）。
- 講法不在本步產（步 3）；`sources` 用 `kb:<id>`／`draft:batch#<n>`；`instance_applicability` 取來源項目（缺則 general）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(cand, "services")) and cand not in sys.path:
        sys.path.insert(0, cand)

try:
    from services.agent.canon.canon_parser import CanonFormatError, parse_canon_text  # noqa: E402
    from services.agent.provenance_units import split_sentences  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[apply_proposal] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_aa = _load_sibling("answerability_args")


def _fail(msg: str) -> None:
    """拒套：印原因到 stderr、exit 2（⛔ 不寫任何輸出檔）。"""
    print(f"[apply_proposal] {msg}", file=sys.stderr)
    raise SystemExit(2)


def sentences_of(text: str) -> list:
    out = []
    for s in split_sentences(text):
        s = s.strip()
        if s:
            out.append(s)
    return out


def source_ref(item_id: str) -> str:
    if item_id.startswith("tmp:kb:"):
        return "kb:" + item_id[len("tmp:kb:"):]
    if item_id.startswith("tmp:draft:"):
        return "draft:batch#" + item_id[len("tmp:draft:"):]
    _fail(f"未知項目 id 形狀：{item_id!r}")


def render(proposal: dict, items_by_id: dict, meta_by_id: dict, *, audience: str, version: str, reviewers: list,
           language: str, budget_tokens: int, target_user: list, business_types: list) -> tuple[str, dict]:
    id_map = proposal.get("id_map")
    if not id_map:
        _fail("提議未附 id_map（對應表）⇒ 拒套")
    mapped_old = {r["old"] for r in id_map if r.get("old") is not None}
    mapped_new = {r["new"] for r in id_map}

    coarse_titles = {c["id"]: c["title"] for c in proposal["coarses"]}
    fines_by_coarse: dict = {}
    for f in proposal["fines"]:
        fines_by_coarse.setdefault(f["coarse_id"], []).append(f)

    lines = ["---", f"audience: {audience}", f"version: {version}", f"reviewers: [{', '.join(reviewers)}]",
             f"language: {language}", f"budget_tokens: {budget_tokens}",
             f"target_user: [{', '.join(target_user)}]", f"business_types: [{', '.join(business_types)}]", "---"]
    correspondence = []
    for cid in sorted(coarse_titles):
        lines.append(f"## {cid} {coarse_titles[cid]} {{#{cid}}}")
        for f in fines_by_coarse.get(cid, []):
            srcs = list(f.get("merge_of") or []) + [s for s in (f.get("split_from") or []) if s not in (f.get("merge_of") or [])]
            if not srcs:
                _fail(f"細目 {f['id']} 沒有來源項目（merge_of／split_from 皆空）⇒ 拒套")
            for s in srcs:
                if s not in mapped_old:
                    _fail(f"細目 {f['id']} 的來源 {s} 不在 id_map ⇒ 拒套")
                if s not in items_by_id:
                    _fail(f"細目 {f['id']} 的來源 {s} 不在輸入項目 ⇒ 拒套")
            if f["id"] not in mapped_new:
                _fail(f"細目 {f['id']} 不在 id_map.new ⇒ 拒套")
            lines.append(f"### {f['title']} {{#{f['id']}}}")
            lines.append(f"- sources: [{', '.join(source_ref(s) for s in srcs)}]")
            metas = [meta_by_id.get(s, {}) for s in srcs]
            ia = {m.get("instance_applicability") for m in metas if m.get("instance_applicability")}
            lines.append(f"- instance_applicability: {sorted(ia)[0] if len(ia) == 1 else 'general'}")
            units: list = []
            for s in srcs:
                for sent in sentences_of(items_by_id[s]["content"]):
                    if sent not in units:
                        units.append(sent)
            lines.extend(units)
            lines.append("")
            correspondence.append({"new": f["id"], "title": f["title"], "from": srcs, "ops": sorted({r["op"] for r in id_map if r["new"] == f["id"]}),
                                   "units": len(units)})
    md = "\n".join(lines).rstrip("\n") + "\n"
    return md, {"id_map": id_map, "fines": correspondence}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--proposal", required=True, help="structure-proposal envelope 或裸提議 JSON")
    p.add_argument("--kb-rows", required=True)
    p.add_argument("--drafts", default=None)
    p.add_argument("--audience", default="prospect")
    p.add_argument("--version", required=True, help="正本版本字串（如 2026-09-06.1）")
    p.add_argument("--reviewers", default="owner")
    p.add_argument("--language", default="zh-TW")
    p.add_argument("--budget-tokens", type=int, default=10000)
    p.add_argument("--target-user", default="prospect")
    p.add_argument("--business-types", default="system_provider")
    p.add_argument("--out-md", required=True)
    p.add_argument("--out-idmap", required=True)
    a = p.parse_args()

    doc = _aa._load_json(a.proposal)
    proposal = doc["payload"]["synthesis"] if isinstance(doc, dict) and "payload" in doc else doc

    kb_doc = _aa._load_json(a.kb_rows)
    kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc
    items = [_aa.candidate_from_kb_row(r) for r in sorted(kb_rows, key=lambda r: r["kb_id"])]
    meta = {f"tmp:kb:{r['kb_id']}": r for r in kb_rows}
    if a.drafts:
        d_doc = _aa._load_json(a.drafts)
        drafts = d_doc["knowledge"] if isinstance(d_doc, dict) else d_doc
        items += [_aa.candidate_from_draft(d, i + 1) for i, d in enumerate(drafts)]
        meta.update({f"tmp:draft:{i + 1}": d for i, d in enumerate(drafts)})
    items_by_id = {it["id"]: it for it in items}

    md, idmap = render(proposal, items_by_id, meta, audience=a.audience, version=a.version,
                       reviewers=[x.strip() for x in a.reviewers.split(",")], language=a.language,
                       budget_tokens=a.budget_tokens, target_user=[x.strip() for x in a.target_user.split(",")],
                       business_types=[x.strip() for x in a.business_types.split(",")])
    try:
        parsed = parse_canon_text(md)
    except CanonFormatError as exc:
        print(f"[apply_proposal] 產出未通過 canon_parser：{exc}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(a.out_md)) or ".", exist_ok=True)
    with open(a.out_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(a.out_idmap, "w", encoding="utf-8") as fh:
        json.dump({**idmap, "canon_sha256": parsed.canon_sha256}, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"[apply_proposal] ok coarses={len(parsed.coarses)} fines={len(parsed.fines())} canon_sha256={parsed.canon_sha256[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
