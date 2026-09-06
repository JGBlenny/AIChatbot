#!/usr/bin/env python3
"""attach_phrasings：把步 3 的講法提案（`phrasing-map.json`，全部 `proposed`）決定性掛進正本草稿 Markdown（2.4a 交件前的最後一步）。

- 輸入：正本草稿 `.md`（`apply_proposal.py` 產）＋ `phrasing-map.json`（StepEnvelope；`payload.phrasings[] = {fine_id,text,source,status,score}`）。
- 輸出：新草稿 `.md`——每個有講法的細目在屬性區塊最前面插入 `- phrasings:` 與 `  - {text: "…", source: "…", status: proposed}` 子項
  （順序：score 降冪、同分 text 字典序；每細目上限沿 phrasing-map 的 cap）；沒有講法的細目不加鍵。
- 決定性：同輸入兩次逐位元相同；產出回讀 `canon_parser.parse_canon_text` 驗證（含 `phrasing_leaks` 必須為空——講法不得出現在內容行）。
- ⛔ 只掛 `status == proposed` 的講法；⛔ 不改任何內容句；⛔ 不新增細目；找不到細目的講法列入 stderr 與 `--report`，exit 2（no silent caps）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(cand, "services")) and cand not in sys.path:
        sys.path.insert(0, cand)
try:
    from services.agent.canon.canon_parser import FINE_HEADING_RE, CanonFormatError, parse_canon_text, phrasing_leaks  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[attach_phrasings] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)

ATTR_LINE_RE = re.compile(r"^-\s*[a-zA-Z_]+\s*:")


def _fail(msg: str) -> None:
    print(f"[attach_phrasings] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def group_phrasings(payload: dict) -> dict:
    by: dict = {}
    for p in payload.get("phrasings", []):
        if p.get("status") != "proposed":
            continue
        by.setdefault(p["fine_id"], []).append(p)
    for fid, items in by.items():
        items.sort(key=lambda p: (-float(p.get("score", 0.0)), p["text"], p.get("source", "")))
    return by


def attach(md: str, by_fine: dict) -> tuple[str, dict]:
    lines = md.split("\n")
    out: list = []
    seen: set = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = FINE_HEADING_RE.match(line)
        if m:
            fid = m.group(2)
            items = by_fine.get(fid, [])
            if items:
                seen.add(fid)
                if "phrasings" in _existing_attr_keys(lines, i + 1):
                    _fail(f"細目 {fid} 已有 phrasings 區塊：本工具只掛到沒有講法的草稿（避免覆寫人審結果）")
                out.append("- phrasings:")
                for p in items:
                    out.append(f"  - {{text: {_quote(p['text'])}, source: {_quote(p['source'])}, status: proposed}}")
        i += 1
    missing = sorted(set(by_fine) - seen)
    return "\n".join(out), {"attached_fines": sorted(seen), "attached_phrasings": sum(len(by_fine[f]) for f in seen), "missing_fines": missing}


def _existing_attr_keys(lines: list, start: int) -> set:
    keys = set()
    for j in range(start, len(lines)):
        l = lines[j]
        if not l.strip():
            continue
        m = ATTR_LINE_RE.match(l)
        if m:
            keys.add(l.split(":", 1)[0].lstrip("- ").strip())
            continue
        if l.startswith(" "):
            continue
        break
    return keys


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--canon", required=True, help="正本草稿 .md（apply_proposal 產）")
    p.add_argument("--phrasing-map", required=True, help="步 3 StepEnvelope phrasing-map.json")
    p.add_argument("--out", required=True)
    p.add_argument("--report", default=None, help="掛載報告 JSON（哪些細目掛了幾條、哪些講法找不到細目）")
    a = p.parse_args()
    with open(a.canon, encoding="utf-8") as fh:
        md = fh.read()
    env = json.load(open(a.phrasing_map, encoding="utf-8"))
    payload = env["payload"] if "payload" in env else env
    by_fine = group_phrasings(payload)
    new_md, report = attach(md, by_fine)
    if report["missing_fines"]:
        _fail(f"講法指到草稿沒有的細目：{report['missing_fines']}（結構與講法不同版？）")
    try:
        doc = parse_canon_text(new_md)
    except CanonFormatError as exc:
        _fail(f"掛載後未通過 canon_parser：{exc}")
    leaks = phrasing_leaks(doc)
    if leaks:
        _fail(f"講法出現在內容行（注入面）：{leaks[:5]}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(new_md)
    report["canon_sha256"] = doc.canon_sha256
    report["phrasing_set_sha256"] = doc.phrasing_set_sha256
    report["fines_without_phrasings"] = [f.id for f in doc.fines() if not f.phrasings]
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
    print(f"[attach_phrasings] ok fines_with_phrasings={len(report['attached_fines'])} phrasings={report['attached_phrasings']} "
          f"without={len(report['fines_without_phrasings'])} canon_sha256={doc.canon_sha256[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
