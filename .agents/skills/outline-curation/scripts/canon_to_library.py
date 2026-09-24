#!/usr/bin/env python3
"""canon_to_library：把兩份受眾正本切成「一目錄＋九架」圖書館正本（DSP-058；計畫 9.6 S1 出貨）。

輸入：`--prospect <md>`／`--pm <md>`（兩份**舊**受眾正本，用 `canon_parser.parse_canon` 解析）
      ＋`--scopes <json>`（九條歸位判準，鍵 `A`…`I`；來源＝計畫 9.6 附錄 A）。
輸出：`<out>/A.md … I.md`（每粗目一架，H 空架亦產）、`<out>/CATALOG.md`（`export_catalog`）、
      `<out>/jgb.json`（`export_json`），以及可選 `--id-map-out`（`remap_ids.py` 吃得下的裸陣列）。

逐細目的搬法（⛔ 不補值、⛔ 不重寫內容）：
- id：`<aud>/X/slug` → `jgb/X/slug`（`op` 一律 `keep`：只換前綴，粗目碼與 slug 不動）。
- `target_user`／`business_types`：寫**該細目在舊檔的實際值**——舊檔 53 條全部沒有自帶，
  故實際值＝檔級預設（prospect ⇒ `[prospect]`、pm ⇒ `[property_manager]`）。
  這一步是 DSP-058 的重點：圖書館形態沒有檔級預設，隔離只認**明列**成員。
- `see_also`：同步 remap（跨架合法）。
- 其餘屬性（phrasings 含 status、sources、reviewed、policy、policy_ref、categories、
  instance_applicability）與 content_units **逐字原樣**。

決定性：同輸入兩次逐位元相同（屬性順序固定＝`canon_parser.ATTR_KEYS` 的順序；細目順序＝
prospect 原序在前、pm 原序在後；⛔ 無時間戳、⛔ 無隨機）。

停點（exit 2，大聲失敗、⛔ 不部分寫檔）：
- 同架同 slug 碰撞（主 session 2026-09-15 已盤為 0，仍要有檢查）；
- 兩份正本的 `version`／`reviewers`／`language` 不一致而未以 `--version` 指定；
- 粗目碼在兩份正本的標題不一致；
- `--scopes` 缺任一架或該架 scope 為空；
- 產出回讀 `parse_canon_dir` 失敗。

⚠️ 本腳本 **只寫 `--out` 指定的目錄**，⛔ 不碰 `rag-orchestrator/canon/`（那是 S2 的事）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for _cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(_cand, "services")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from services.agent.canon.canon_parser import (  # noqa: E402
        CANON_NAME, SHELF_FILES, SHELF_FRONT_MATTER_KEYS, CanonFormatError,
        export_catalog, export_json, parse_canon, parse_canon_dir,
    )
except ImportError as exc:  # pragma: no cover — 只在沒掛到 rag-orchestrator 時發生
    print(f"[canon_to_library] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行",
          file=sys.stderr)
    raise SystemExit(2)

#: 屬性寫出順序（固定）——決定性的來源之一。⛔ 不依 dict 插入序。
ATTR_ORDER = (
    "phrasings", "sources", "reviewed", "see_also", "policy", "policy_ref",
    "target_user", "business_types", "categories", "instance_applicability",
)
#: 粗目標題在舊正本是 `## A 帳號與身分 {#A}`（標題自帶粗目碼）。架 front matter 的 `title`
#: 一律去掉這個前綴；架內 `## 標題 {#<X>-shelf}`（計畫 9.10 S5／DSP-070：目錄路徑裸字母
#: `{#X}` 已停用，⛔ 不再產出）改由 `_shelf_coarse_id` 補上固定 slug。
_TITLE_CODE_PREFIX_RE = re.compile(r'^([A-Z])\s+')


def _shelf_coarse_id(code: str) -> str:
    """本腳本歷來只產「一架一粗目」，粗目 id 固定為 `<架字母>-shelf`（決定性、無需另造 slug 演算法）。"""
    return f"{code}-shelf"


def _fail(msg: str) -> None:
    print(f"[canon_to_library] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _strip_code_prefix(title: str, code: str) -> str:
    m = _TITLE_CODE_PREFIX_RE.match(title)
    return title[m.end():] if m and m.group(1) == code else title


def _fmt_list(values) -> str:
    return "[" + ", ".join(values) + "]"


def _fmt_phrasing(p) -> str:
    text = p.text.replace("\\", "\\\\").replace('"', '\\"')
    return f'  - {{text: "{text}", source: "{p.source}", status: {p.status}}}'


def _remap(fid: str) -> str:
    _aud, code, slug = fid.split("/")
    return f"{CANON_NAME}/{code}/{slug}"


def _fine_block(fine, id_map: dict) -> list:
    """一個細目的行（⛔ 不含結尾空行；屬性順序固定）。"""
    out = [f"### {fine.title} {{#{id_map[fine.id]}}}"]
    for key in ATTR_ORDER:
        if key == "phrasings":
            if fine.phrasings:
                out.append("- phrasings:")
                out.extend(_fmt_phrasing(p) for p in fine.phrasings)
        elif key == "sources":
            if fine.sources:
                out.append(f"- sources: {_fmt_list(fine.sources)}")
        elif key == "reviewed":
            if fine.reviewed_by is not None:
                out.append(f"- reviewed: {{by: {fine.reviewed_by}, at: {fine.reviewed_at}}}")
        elif key == "see_also":
            if fine.see_also:
                out.append(f"- see_also: {_fmt_list(id_map[t] for t in fine.see_also)}")
        elif key == "policy":
            # 一律明寫（parser 預設 answerable；明寫讓架檔自己說得清楚，回讀值不變）
            out.append(f"- policy: {fine.policy}")
        elif key == "policy_ref":
            if fine.policy_ref is not None:
                out.append(f"- policy_ref: {fine.policy_ref}")
        elif key == "target_user":
            out.append(f"- target_user: {_fmt_list(fine.target_user)}")
        elif key == "business_types":
            out.append(f"- business_types: {_fmt_list(fine.business_types)}")
        elif key == "categories":
            if fine.categories:
                out.append(f"- categories: {_fmt_list(fine.categories)}")
        elif key == "instance_applicability":
            out.append(f"- instance_applicability: {fine.instance_applicability}")
    out.extend(fine.content_units)
    return out


def _shelf_text(code: str, title: str, scope: str, version: str, reviewers, language: str, fines, id_map: dict) -> str:
    lines = [
        "---",
        f"coarse: {code}",
        f"title: {title}",
        f"scope: {scope}",
        f"version: {version}",
        f"reviewers: {_fmt_list(reviewers)}",
        f"language: {language}",
        "---",
        f"## {title} {{#{_shelf_coarse_id(code)}}}",
    ]
    for fine in fines:
        lines.append("")
        lines.extend(_fine_block(fine, id_map))
    return "\n".join(lines) + "\n"


def _load_scopes(path: str) -> dict:
    if not os.path.isfile(path):
        _fail(f"--scopes 檔案不存在：{path}")
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        _fail(f"--scopes（{path}）須為物件，鍵 A…I")
    scopes = {}
    for fname in SHELF_FILES:
        code = fname[:-3]
        val = raw.get(code)
        if not isinstance(val, str) or not val.strip():
            _fail(f"--scopes 缺架 {code} 或其 scope 為空（九架都要有歸位判準）")
        scopes[code] = val.strip()
    return scopes


def build(prospect_md: str, pm_md: str, scopes: dict, version: str = "") -> tuple:
    """回 (shelf_texts: dict[code]=text, id_map: list[dict])。⛔ 不寫檔（寫檔在 main）。"""
    docs = []
    for path in (prospect_md, pm_md):
        if not os.path.isfile(path):
            _fail(f"正本不存在：{path}")
        try:
            docs.append(parse_canon(path))
        except CanonFormatError as exc:
            _fail(f"{path} 解析失敗：{exc}")

    for key in ("reviewers", "language"):
        vals = {getattr(d, key) for d in docs}
        if len(vals) != 1:
            _fail(f"兩份正本的 {key} 不一致：{sorted(str(v) for v in vals)}（⛔ 不自行合併，請先對齊正本）")
    if not version:
        versions = {d.version for d in docs}
        if len(versions) != 1:
            _fail(f"兩份正本的 version 不一致：{sorted(versions)}——請以 --version 明確指定")
        version = versions.pop()

    titles: dict = {}
    by_code: dict = {code[:-3]: [] for code in SHELF_FILES}
    slug_owner: dict = {}
    collisions: list = []
    id_map: list = []
    id_index: dict = {}

    for doc in docs:
        for coarse in doc.coarses:
            if coarse.id not in by_code:
                _fail(f"{doc.source_path}：粗目碼 {coarse.id!r} 不在九架白名單 {SHELF_FILES}")
            title = _strip_code_prefix(coarse.title, coarse.id)
            if titles.setdefault(coarse.id, title) != title:
                _fail(f"粗目 {coarse.id} 在兩份正本標題不一致："
                      f"{titles[coarse.id]!r} vs {title!r}（⛔ 不自行擇一）")
            for fine in coarse.fines:
                _aud, code, slug = fine.id.split("/")
                prev = slug_owner.get((code, slug))
                if prev is not None:
                    collisions.append(f"{code}/{slug}：{prev} 與 {fine.id}")
                    continue
                slug_owner[(code, slug)] = fine.id
                new_id = _remap(fine.id)
                id_index[fine.id] = new_id
                id_map.append({"old": fine.id, "new": new_id, "op": "keep"})
                by_code[code].append(fine)

    if collisions:
        _fail("同架同 slug 碰撞（⛔ 不自動改名）：\n  - " + "\n  - ".join(collisions))

    # see_also 目標一律在 id_map 內（舊 parser 已驗過檔內存在性；跨檔引用不存在則此處大聲失敗）
    for fine in (f for fines in by_code.values() for f in fines):
        for target in fine.see_also:
            if target not in id_index:
                _fail(f"細目 {fine.id} 的 see_also 目標 {target!r} 不在任何一份輸入正本內")

    missing_titles = [c for c in (f[:-3] for f in SHELF_FILES) if c not in titles]
    if missing_titles:
        _fail(f"兩份正本都沒有粗目 {missing_titles}——⛔ 不自行造標題，請先補進正本")

    shelf_texts = {}
    for fname in SHELF_FILES:
        code = fname[:-3]
        shelf_texts[code] = _shelf_text(
            code, titles[code], scopes[code], version, docs[0].reviewers, docs[0].language,
            by_code[code], id_index,
        )
    return shelf_texts, id_map


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="舊受眾正本 → 圖書館正本（一目錄＋九架）")
    ap.add_argument("--prospect", required=True, help="舊 prospect 正本 .md")
    ap.add_argument("--pm", required=True, help="舊 property_manager 正本 .md")
    ap.add_argument("--scopes", required=True, help="九條 scope 的 JSON（鍵 A…I）")
    ap.add_argument("--out", required=True, help="輸出目錄（⛔ 不是 rag-orchestrator/canon/）")
    ap.add_argument("--id-map-out", default="", help="id_map.json 輸出路徑（remap_ids.py 可讀的裸陣列）")
    ap.add_argument("--version", default="", help="架 front matter 的 version（預設＝兩份正本的一致值）")
    args = ap.parse_args(argv)

    scopes = _load_scopes(args.scopes)
    shelf_texts, id_map = build(args.prospect, args.pm, scopes, args.version)

    os.makedirs(args.out, exist_ok=True)
    for code, text in sorted(shelf_texts.items()):
        with open(os.path.join(args.out, f"{code}.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    # 回讀驗證（⛔ 不宣稱成功而不回讀）：產出必須過 parse_canon_dir 的全部規則。
    try:
        doc = parse_canon_dir(args.out)
    except CanonFormatError as exc:
        _fail(f"產出未通過 parse_canon_dir：{exc}")

    export_catalog(doc, os.path.join(args.out, "CATALOG.md"))
    export_json(doc, os.path.join(args.out, f"{CANON_NAME}.json"))

    if args.id_map_out:
        with open(args.id_map_out, "w", encoding="utf-8") as fh:
            json.dump(id_map, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")

    fines = doc.fines()
    empty = [c.id for c in doc.coarses if not c.fines]
    print(f"[canon_to_library] out={args.out} 架={len(doc.coarses)} 細目={len(fines)} "
          f"空架={','.join(empty) or '無'} canon_sha256={doc.canon_sha256}")
    print(f"[canon_to_library] front matter 六鍵={SHELF_FRONT_MATTER_KEYS} id_map={len(id_map)} 筆（全 keep）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
