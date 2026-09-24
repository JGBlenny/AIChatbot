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
import importlib.util
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


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


#: 計畫 9.10 S5 第二輪：`fine_shelf_letter` 與 `apply_proposal.py`／`canon_items.shelf_items`
#: 共用同一份，⛔ 不各自重寫一套（同義同名，見 canon_items.py 的函式 docstring）。
_ci = _load_sibling("canon_items")

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
    p.add_argument("--shelf", default=None,
                   help="圖書館模式（9.7）：--canon 給九架目錄、只掛這一架（A–I）；--out 給輸出目錄（九架＋CATALOG＋jgb.json 重產，"
                        "其他架逐位元照抄）；已有 phrasings 的細目跳過並列進報告 skipped_fines（⛔ 不覆寫人審結果）")
    a = p.parse_args()
    env = json.load(open(a.phrasing_map, encoding="utf-8"))
    payload = env["payload"] if "payload" in env else env
    by_fine = group_phrasings(payload)

    if a.shelf:
        return _main_shelf(a, by_fine)

    with open(a.canon, encoding="utf-8") as fh:
        md = fh.read()
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


def _main_shelf(a, by_fine: dict) -> int:
    """圖書館模式：只掛 `--shelf` 那一架；已有講法的細目跳過（列 `skipped_fines`）；回讀用 `parse_canon_dir`
    （含跨架講法唯一）；任何失敗不落檔（先寫暫存目錄）。"""
    import shutil
    import tempfile
    from services.agent.canon.canon_parser import SHELF_FILES, export_catalog, export_json, parse_canon_dir
    if not os.path.isdir(a.canon):
        _fail(f"--shelf 模式 --canon 須為九架目錄：{a.canon!r}")
    shelf_file = f"{a.shelf}.md"
    if shelf_file not in SHELF_FILES:
        _fail(f"--shelf 須為 A–I，得到 {a.shelf!r}")
    if os.path.exists(a.out) and os.listdir(a.out):
        _fail(f"--out 必須是不存在或空目錄（⛔ 不覆蓋）：{a.out!r}")
    md = open(os.path.join(a.canon, shelf_file), encoding="utf-8").read()
    # 整座圖書館既有講法（任何狀態、任何架）：提案同文者一律不掛、記 `dup_existing`——
    # 講法唯一是 parse_canon_dir 的硬規則（跨架亦然），步 3 提案時看不到既有正本，這裡補這道濾網。
    import unicodedata
    existing_doc = parse_canon_dir(a.canon)
    existing_texts = {unicodedata.normalize("NFKC", p.text).strip(): f.id
                      for f in existing_doc.fines() for p in f.phrasings}
    # 講法若與任一細目的內容句同文 ⇒ 掛上去就是注入面（phrasing_leaks 會擋），先濾、記 `dup_content`。
    # 與 canon_parser.phrasing_leaks 同判準：NFKC＋去空白後，①整句相等 或 ②長度 ≥ LEAK_CONTAINS_MIN_CHARS 且為內容子字串。
    from services.agent.canon.canon_parser import LEAK_CONTAINS_MIN_CHARS
    import re as _re
    def _norm(s: str) -> str:
        return _re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
    content_units_norm = [(_norm(u), f.id) for f in existing_doc.fines() for u in f.content_units]
    content_texts = {u: fid for u, fid in content_units_norm}
    content_hay = "\n".join(u for u, _ in content_units_norm)
    dup_existing: dict = {}
    dup_content: dict = {}
    for fid in list(by_fine):
        kept = []
        for p in by_fine[fid]:
            key = unicodedata.normalize("NFKC", p["text"]).strip()
            nkey = _norm(p["text"])
            if key in existing_texts:
                dup_existing.setdefault(fid, []).append({"text": p["text"], "already_on": existing_texts[key]})
            elif nkey in content_texts or (len(nkey) >= LEAK_CONTAINS_MIN_CHARS and nkey in content_hay):
                dup_content.setdefault(fid, []).append({"text": p["text"], "content_of": content_texts.get(nkey, "substring")})
            else:
                kept.append(p)
        if kept:
            by_fine[fid] = kept
        else:
            del by_fine[fid]
    # 提案內部同文掛多細目（來源被 split 到多個細目時 question_summary 關鍵字會兩邊都掛）：
    # 只留分數最高者（同分取 id 字典序小者），其餘記 `dup_in_proposal` 交人審改掛。
    best: dict = {}
    for fid in sorted(by_fine):
        for p in by_fine[fid]:
            key = unicodedata.normalize("NFKC", p["text"]).strip()
            cur = best.get(key)
            if cur is None or float(p.get("score", 0.0)) > float(cur[1].get("score", 0.0)):
                best[key] = (fid, p)
    dup_in_proposal: dict = {}
    for fid in list(by_fine):
        kept = []
        for p in by_fine[fid]:
            key = unicodedata.normalize("NFKC", p["text"]).strip()
            if best[key][0] == fid:
                kept.append(p)
            else:
                dup_in_proposal.setdefault(fid, []).append({"text": p["text"], "kept_on": best[key][0]})
        if kept:
            by_fine[fid] = kept
        else:
            del by_fine[fid]
    # 已有講法的細目：從 by_fine 拿掉、記報告（attach() 對這種情況是 _fail，這裡先濾）
    lines = md.split("\n")
    has_phr: set = set()
    for i, line in enumerate(lines):
        m = FINE_HEADING_RE.match(line)
        if m and "phrasings" in _existing_attr_keys(lines, i + 1):
            has_phr.add(m.group(2))
    skipped = {fid: by_fine[fid] for fid in list(by_fine) if fid in has_phr}
    for fid in skipped:
        del by_fine[fid]
    # 講法指到別架的細目 ⇒ 不是錯（步 3 是整份提案），只列報告
    shelf_fids = {FINE_HEADING_RE.match(l).group(2) for l in lines if FINE_HEADING_RE.match(l)}
    other = {fid: by_fine[fid] for fid in list(by_fine) if fid not in shelf_fids}
    for fid in other:
        del by_fine[fid]
    new_md, report = attach(md, by_fine)
    tmp = tempfile.mkdtemp(prefix="attach_shelf_")
    try:
        for f in SHELF_FILES:
            src = os.path.join(a.canon, f)
            if f == shelf_file:
                with open(os.path.join(tmp, f), "w", encoding="utf-8") as fh:
                    fh.write(new_md)
            else:
                shutil.copyfile(src, os.path.join(tmp, f))
        try:
            doc = parse_canon_dir(tmp)
        except CanonFormatError as exc:
            _fail(f"掛載後未通過 parse_canon_dir（未落檔）：{exc}")
        leaks = phrasing_leaks(doc)
        if leaks:
            _fail(f"講法出現在內容行（注入面）：{leaks[:5]}")
        export_catalog(doc, os.path.join(tmp, "CATALOG.md"))
        export_json(doc, os.path.join(tmp, "jgb.json"))
        if os.path.isdir(a.out):
            os.rmdir(a.out)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        shutil.move(tmp, a.out)
        tmp = None
    finally:
        if tmp and os.path.isdir(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
    report["skipped_fines"] = {fid: len(v) for fid, v in sorted(skipped.items())}
    report["dup_existing"] = dup_existing
    report["dup_in_proposal"] = dup_in_proposal
    report["dup_content"] = dup_content
    report["other_shelf_fines"] = {fid: len(v) for fid, v in sorted(other.items())}
    report["canon_sha256"] = doc.canon_sha256
    report["phrasing_set_sha256"] = doc.phrasing_set_sha256
    # ⚠️ 計畫 9.10 S5 第二輪（DSP-070 病灶）：⛔ 不得用 `f.coarse_id == a.shelf`——理由與
    # `apply_proposal.render_expand`／`canon_items.shelf_items` 同（見 `_ci.fine_shelf_letter` docstring）。
    report["fines_without_phrasings"] = [
        f.id for f in doc.fines() if _ci.fine_shelf_letter(f.id) == a.shelf and not f.phrasings
    ]
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
    print(f"[attach_phrasings] shelf={a.shelf} fines_with_phrasings={len(report['attached_fines'])} "
          f"phrasings={report['attached_phrasings']} skipped={len(skipped)} other_shelf={len(other)} "
          f"without={len(report['fines_without_phrasings'])} canon_sha256={doc.canon_sha256[:12]} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
