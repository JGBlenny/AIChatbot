#!/usr/bin/env python3
"""apply_proposal：把（人審後的）結構提議決定性套成正本 Markdown 草稿＋id 對應表（任務 2.3；9.3⑤ 補「從既有正本重切」模式）。

- 輸入：structure-proposal envelope（取 `payload.synthesis`）或裸提議 JSON；kb 列／草稿（內容來源）；front matter 參數。
- 輸出：`<out-md>`（正本草稿，格式＝design 元件 4；⛔ 不 commit、不入庫，交業主審）＋`<out-idmap>`（`[{old,new,op}]`＋每細目前後對照）。
- 決定性：同輸入兩次逐位元相等（無時間戳；粗目依 id 排序、細目依提議順序、內容句依 merge_of 順序）。
- **未附對應表 ⇒ exit 2**：提議 `id_map` 缺、或有細目的來源不在 id_map ⇒ 拒套。
- 內容句＝來源項目 `content` 依 `provenance_units.split_sentences` 切成一行一句；產出後以 `canon_parser.parse_canon_text` 回讀驗證（失敗 exit 2）。
- 講法不在本步產（步 3）；`sources` 用 `kb:<id>`／`draft:batch#<n>`；`instance_applicability` 取來源項目（缺則 general）。

`--cells <map-v2.json>`（選填，F1）：給了才在 `sources` 既有項目之後，依細目 `merge_of` 各來源項目
衍生的 `helpcenter:<slug>`（排序去重）——不給則輸出與未加此參數前逐位元相同。

`--canon <既有正本>`（任務 9.3⑤，重切模式；與 `--kb-rows` 二擇一；單檔或目錄皆可，`canon_items.parse_canon_auto`
依路徑分派）：內容來源改成既有正本細目，依 `id_map` 每一（舊→新）邊逐條決定屬性去留
（`render_remap` docstring 有完整規則）。

9.6 S4（DSP-058 圖書館正本後）：`--canon` 重切模式的輸出改為**依粗目切九架**寫到 `--out <目錄>`
（架 front matter 六鍵 `SHELF_FRONT_MATTER_KEYS`；`scope` 依序取 `--scopes`／輸入正本自帶的
`scopes`（目錄路徑才有）／`schemas/scopes-jgb.json` 內建預設；粗目標題依序取輸入正本自帶的粗目
標題／提議 `coarses` 自帶標題／`schemas/coarses-jgb.json` 內建預設），同時呼叫 `export_catalog`／
`export_json` 產 `CATALOG.md`／`<--canon-name>.json`；`--version`／`--out-idmap`／`--out-pending-dir`
在此模式下皆有預設值（依序：輸入正本 version／`<out>/id_map.json`／`<out>/pending/`），故最小可只給
`--canon`／`--proposal`／`--out` 三者。每細目**必填** `target_user`（提議自帶，`render_remap` 缺即拒套，
exit 2；`business_types` 沿用來源細目的既有值，⛔ 不重複要求提議填）。`--out-md`（單檔輸出）**只在
`--kb-rows` 模式**適用。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(cand, "services")) and cand not in sys.path:
        sys.path.insert(0, cand)

try:
    from services.agent.canon.canon_parser import (  # noqa: E402
        CanonFormatError, SHELF_FILES, export_catalog, export_json, parse_canon_dir, parse_canon_text,
    )
    from services.agent.provenance_units import split_sentences  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[apply_proposal] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)

#: 九架碼（字母序，來自 SHELF_FILES 白名單），⛔ 不 glob。
_SHELF_CODES: tuple[str, ...] = tuple(f[:-3] for f in SHELF_FILES)
_SCHEMAS_DIR = os.path.join(_HERE, "..", "schemas")


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_aa = _load_sibling("answerability_args")
_ci = _load_sibling("canon_items")


def _fail(msg: str) -> None:
    """拒套：印原因到 stderr、exit 2（⛔ 不寫任何輸出檔）。"""
    print(f"[apply_proposal] {msg}", file=sys.stderr)
    raise SystemExit(2)


_LIST_MARKER_RE = __import__("re").compile(r"^(?:[-*•・]\s+|[-*•・](?=\S)|#{1,6}\s+|>\s+)")


def sentences_of(text: str) -> list:
    """kb `answer` → 一行一句。⚠️ 句首的條列符號（`- `／`* `／`• `）、markdown 標題（`## `）、引用（`> `）一律剝掉：
    正本內容區的行不得以 `- ` 或 `#` 開頭（canon_parser 會當成屬性行／標題行而拒解析），符號本身也不是可引用的內容。"""
    out = []
    for s in split_sentences(text):
        s = _LIST_MARKER_RE.sub("", s.strip()).strip()
        if s:
            out.append(s)
    return out


def source_ref(item_id: str) -> str:
    if item_id.startswith("tmp:kb:"):
        return "kb:" + item_id[len("tmp:kb:"):]
    if item_id.startswith("tmp:draft:"):
        return "draft:batch#" + item_id[len("tmp:draft:"):]
    _fail(f"未知項目 id 形狀：{item_id!r}")


def build_cells_lookups(cells_path: str, drafts_path: str | None = None) -> tuple[dict, dict]:
    """讀 `--cells`（缺口地圖 map-v2.json）→ 兩個查表（F1）：

    (a) `draft_hc`：`draft:batch#<n>` → 該草稿的 `help_center`。真資料的 cell id 是 `C01…`、⛔ 不會以
        `draft:batch#` 開頭（verifier 2026-09-07 P4：舊分支在真資料恆空），正確的鏈是
        **草稿檔第 n 筆（1 起算）的 `cell` 欄 → map-v2 該格的 `help_center`**（`--drafts` 給了才有）；
        cell id 本身即參照的舊分支保留給 fixture。
    (b) `kb_hc`：`kb:<id>` → 每個 `sources` 含該 `kb:<id>` 的 cell 之 `help_center` 聯集（排序去重）。
    """
    doc = _aa._load_json(cells_path)
    cells = doc["cells"] if isinstance(doc, dict) else doc
    draft_hc: dict = {}
    kb_hc: dict = {}
    hc_by_cell: dict = {}
    for c in cells:
        hc = c.get("help_center") or []
        cid = c.get("id", "")
        if isinstance(cid, str):
            hc_by_cell[cid] = sorted(set(hc))
            if cid.startswith("draft:batch#"):
                draft_hc[cid] = sorted(set(draft_hc.get(cid, [])) | set(hc))
        for s in c.get("sources") or []:
            if isinstance(s, str) and s.startswith("kb:"):
                kb_hc.setdefault(s, set())
                kb_hc[s].update(hc)
    if drafts_path:
        ddoc = _aa._load_json(drafts_path)
        items = ddoc.get("knowledge") if isinstance(ddoc, dict) else ddoc
        for n, item in enumerate(items or [], 1):
            cell = item.get("cell") if isinstance(item, dict) else None
            if cell and cell in hc_by_cell:
                key = f"draft:batch#{n}"
                draft_hc[key] = sorted(set(draft_hc.get(key, [])) | set(hc_by_cell[cell]))
    return draft_hc, {k: sorted(v) for k, v in kb_hc.items()}


def helpcenter_slugs_for(srcs: list, draft_hc: dict, kb_hc: dict) -> list:
    """細目來源項目（`tmp:kb:<id>`／`tmp:draft:<n>`）→ 透過 `source_ref` 轉成的參照，
    查兩個表 → 聯集後排序去重的 `helpcenter:<slug>` 清單（無 `--cells` 或查無 ⇒ 空清單）。"""
    slugs: set = set()
    for s in srcs:
        ref = source_ref(s)
        if ref.startswith("draft:batch#"):
            slugs.update(draft_hc.get(ref, []))
        elif ref.startswith("kb:"):
            slugs.update(kb_hc.get(ref, []))
    return sorted(slugs)


def render(proposal: dict, items_by_id: dict, meta_by_id: dict, *, audience: str, version: str, reviewers: list,
           language: str, budget_tokens: int, target_user: list, business_types: list,
           draft_hc: dict | None = None, kb_hc: dict | None = None) -> tuple[str, dict]:
    draft_hc = draft_hc or {}
    kb_hc = kb_hc or {}
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
            hc_slugs = helpcenter_slugs_for(srcs, draft_hc, kb_hc)
            src_refs = [source_ref(s) for s in srcs] + [f"helpcenter:{slug}" for slug in hc_slugs]
            lines.append(f"- sources: [{', '.join(src_refs)}]")
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


# ---------------------------------------------------------------------------
# --canon 重切模式（任務 9.3⑤）
# ---------------------------------------------------------------------------

def _nfkc(s: str) -> str:
    """NFKC＋去空白，與 `canon_parser._nfkc` 同一判準（自成一份，⛔ 不 import 私有符號）。"""
    return "".join(unicodedata.normalize("NFKC", s).split())


def _dedupe_preserve(items) -> list:
    seen: set = set()
    out: list = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _fmt_list(items) -> str:
    return f"[{', '.join(items)}]"


def _fmt_phrasing(p) -> str:
    text = p.text.replace("\\", "\\\\").replace('"', '\\"')
    return f'  - {{text: "{text}", source: "{p.source}", status: {p.status}}}'


def _shelf_coarse_id(code: str) -> str:
    """`render_remap`／`render_expand` 歷來只產「一架一粗目」，粗目 id 固定為 `<架字母>-shelf`
    （計畫 9.10 S5／DSP-070：目錄路徑裸字母 `{#X}` 已停用，⛔ 不再產出；與 `canon_to_library.py`
    同一命名規則，決定性、無需另造 slug 演算法）。"""
    return f"{code}-shelf"


def _target_coarse(canon_doc, code: str, shelf_title: str) -> tuple:
    """重切／擴充輸出第 `code` 架的**唯一**粗目 `(id, 標題)`（計畫 9.10 S5 第三輪、DSP-070 verifier F2）。

    提議只能表達「一架一粗目」（`fines[].coarse_id` 是架字母），而三層正本一架可有多個產品功能粗目。
    ⇒ 輸入正本該架已有**多個**粗目 ⇒ 大聲拒套——照跑會把粗目結構靜默攤平成一個（57→54 實測）；
    恰有**一個**新形態粗目 ⇒ 保留它的 id 與標題（⛔ 不改名成 `<架字母>-shelf`）；
    單檔正本的裸字母粗目、或該架沒有粗目 ⇒ `_shelf_coarse_id(code)`＋架標題。
    """
    of_shelf = [c for c in getattr(canon_doc, "coarses", ()) if c.id.split("-", 1)[0] == code]
    if len(of_shelf) > 1:
        _fail(f"架 {code} 既有 {len(of_shelf)} 個粗目 {[c.id for c in of_shelf]}；提議只能表達一架一粗目，"
              "照跑會把粗目結構攤平 ⇒ 拒套（多粗目的重切／擴充尚未設計）")
    if len(of_shelf) == 1 and "-" in of_shelf[0].id:
        return of_shelf[0].id, of_shelf[0].title
    return _shelf_coarse_id(code), shelf_title


def _load_default_coarse_titles() -> dict:
    """`schemas/coarses-jgb.json` 的九條粗目標題（內建預設，供缺對應碼時兜底）。"""
    doc = _aa._load_json(os.path.join(_SCHEMAS_DIR, "coarses-jgb.json"))
    return {c["id"]: c["title"] for c in doc["coarses"]}


def _load_default_scopes() -> dict:
    """`schemas/scopes-jgb.json` 的九架 scope（內建預設，供缺對應碼時兜底；`_` 開頭鍵為說明，略過）。"""
    doc = _aa._load_json(os.path.join(_SCHEMAS_DIR, "scopes-jgb.json"))
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def render_remap(proposal: dict, canon_doc, *, version: str, scopes_by_code: dict,
                  coarse_titles_by_code: dict, canon_name: str = "jgb") -> tuple:
    """重切模式渲染（任務 9.3⑤；9.6 S4 改依粗目切九架）：內容來源＝`--canon` 既有正本的細目，
    依 `id_map` 決定屬性去留，輸出＝`{碼: 架全文}`（九碼恆備齊，見 `_SHELF_CODES`）。

    每一（舊→新）邊的角色由 `old_to_news`（同一個舊 id 映到幾個新 id）決定，⛔ 不看 op 字面
    （keep／move／merge／split 對「內容永遠整段複製」這件事本身沒有差異；差異在於：
    一個舊細目若映到多個新細目（即被拆分），它的講法一律不掛任何新細目，全數進待審）：

    - 新細目唯一來源、且該來源未被拆分 ⇒ **原樣帶過**（phrasings／sources／reviewed／policy／
      policy_ref／business_types／categories／instance_applicability 全部照抄）。
    - 其餘情況（來源 >1，或唯一來源本身被拆分）⇒ **合併模式**：內容＝各來源 `content_units`
      依序整段串接（不去重）；講法＝非被拆分來源的講法聯集（NFKC 去重，同文留先出現者），
      被拆分來源的講法全數進 `pending-phrasings.json`；sources／business_types／
      categories 聯集去重；`policy` 需全體一致否則 exit 2（policy_ref 取來源序第一個非 None 值）；
      `instance_applicability` 一致則用該值，否則退回 `general`；`reviewed` 一律丟棄
      （內容已變、需重審，fail-closed）。
    - `target_user`：**不沿用來源**，改由提議每一細目**必填**（9.6 S4／DSP-058：圖書館正本無檔級
      預設，且重切本身允許重新指派受眾歸屬）；缺或空 ⇒ 拒套（exit 2）；值域僅 prospect／
      property_manager，不在此域 ⇒ 拒套。
    - `see_also`：目標經 `id_map` 改寫；目標被拆分（映到多個新 id）或找不到對應（已排除／不在
      本次項目集合）⇒ 該筆目標丟棄並記入 `pending-see_also.json`，⛔ 不留舊 id、⛔ 不猜。
    - 拆分來源（`old_to_news[old]` 長度 >1）記一筆 `pending-splits.json`（`{old, children, note}`）。
    - 守門（a）：同一句講法文字（NFKC）掛到兩個不同細目 ⇒ exit 2 並列出兩者（跨架亦然）。
    """
    old_fine_by_bare = {f.id: f for f in canon_doc.fines()}
    id_map = proposal.get("id_map")
    if not id_map:
        _fail("提議未附 id_map（對應表）⇒ 拒套")
    old_to_news: dict = {}
    for row in id_map:
        old = row.get("old")
        if old:
            old_to_news.setdefault(_ci.bare_id(old), set()).add(row["new"])
    mapped_old = {r["old"] for r in id_map if r.get("old") is not None}
    mapped_new = {r["new"] for r in id_map}

    def is_split(bare: str) -> bool:
        return len(old_to_news.get(bare, ())) > 1

    fines_by_coarse: dict = {}
    for f in proposal["fines"]:
        fines_by_coarse.setdefault(f["coarse_id"], []).append(f)

    correspondence: list = []
    pending_splits: list = []
    pending_phrasings: list = []
    pending_see_also: list = []
    split_recorded: set = set()
    phrasing_owner: dict = {}
    shelf_texts: dict = {}

    def remap_see_also(fine_id: str, targets: list) -> list:
        out = []
        for t in targets:
            candidates = old_to_news.get(t, set())
            if len(candidates) == 1:
                out.append(next(iter(candidates)))
            else:
                reason = "target_split" if len(candidates) > 1 else "target_missing"
                pending_see_also.append({"from": fine_id, "target_old": t, "reason": reason})
        return _dedupe_preserve(out)

    target_coarse = {cid: _target_coarse(canon_doc, cid, coarse_titles_by_code[cid]) for cid in _SHELF_CODES}
    for cid in _SHELF_CODES:
        title = coarse_titles_by_code[cid]
        coarse_id, coarse_title = target_coarse[cid]
        lines = ["---", f"coarse: {cid}", f"title: {title}", f"scope: {scopes_by_code[cid]}",
                 f"version: {version}", f"reviewers: {_fmt_list(canon_doc.reviewers)}",
                 f"language: {canon_doc.language}", "---", f"## {coarse_title} {{#{coarse_id}}}"]
        for f in fines_by_coarse.get(cid, []):
            if f["id"].split("/")[0] != canon_name:
                _fail(f"細目 {f['id']} 的 id 前綴與 --canon-name {canon_name!r} 不符 ⇒ 拒套")
            srcs_bare = _dedupe_preserve(
                _ci.bare_id(s) for s in (list(f.get("merge_of") or []) + list(f.get("split_from") or []))
            )
            if not srcs_bare:
                _fail(f"細目 {f['id']} 沒有來源項目（merge_of／split_from 皆空）⇒ 拒套")
            for b in srcs_bare:
                key = _ci.TMP_PREFIX + b
                if key not in mapped_old:
                    _fail(f"細目 {f['id']} 的來源 {key} 不在 id_map ⇒ 拒套")
                if b not in old_fine_by_bare:
                    _fail(f"細目 {f['id']} 的來源 {key} 不在既有正本 ⇒ 拒套")
                if f["id"] not in old_to_news.get(b, set()):
                    _fail(f"細目 {f['id']} 與來源 {key} 的 id_map 不一致 ⇒ 拒套")
            if f["id"] not in mapped_new:
                _fail(f"細目 {f['id']} 不在 id_map.new ⇒ 拒套")

            target_user = f.get("target_user")
            if not target_user:
                _fail(f"細目 {f['id']} 缺必填屬性 target_user（提案需明列）⇒ 拒套")
            bad_tu = sorted(set(target_user) - {"prospect", "property_manager"})
            if bad_tu:
                _fail(f"細目 {f['id']} 的 target_user 含未知值：{bad_tu} ⇒ 拒套")

            old_fines = [old_fine_by_bare[b] for b in srcs_bare]
            split_flags = [is_split(b) for b in srcs_bare]

            content_units: list = []
            for of in old_fines:
                content_units.extend(of.content_units)

            if len(old_fines) == 1 and not split_flags[0]:
                of = old_fines[0]
                phrasings = list(of.phrasings)
                sources = list(of.sources)
                policy = of.policy
                policy_ref = of.policy_ref
                ia = of.instance_applicability
                business_types = of.business_types
                categories = of.categories
                reviewed = (of.reviewed_by, of.reviewed_at)
                see_also_raw = list(of.see_also)
            else:
                phrasings = []
                seen_p: set = set()
                for of, split_flag in zip(old_fines, split_flags):
                    if split_flag:
                        continue
                    for ph in of.phrasings:
                        k = _nfkc(ph.text)
                        if k not in seen_p:
                            seen_p.add(k)
                            phrasings.append(ph)
                sources = _dedupe_preserve(s for of in old_fines for s in of.sources)
                policies = {of.policy for of in old_fines}
                if len(policies) > 1:
                    _fail(f"細目 {f['id']} 合併來源 policy 不一致：{sorted(policies)}（交人裁）")
                policy = next(iter(policies))
                policy_ref = next((of.policy_ref for of in old_fines if of.policy_ref), None)
                ia_set = {of.instance_applicability for of in old_fines}
                ia = next(iter(ia_set)) if len(ia_set) == 1 else "general"
                business_types = tuple(sorted({v for of in old_fines for v in of.business_types}))
                categories = tuple(sorted({v for of in old_fines for v in of.categories}))
                reviewed = (None, None)
                see_also_raw = _dedupe_preserve(v for of in old_fines for v in of.see_also)

            see_also = remap_see_also(f["id"], see_also_raw)

            lines.append(f"### {f['title']} {{#{f['id']}}}")
            if phrasings:
                lines.append("- phrasings:")
                for ph in phrasings:
                    lines.append(_fmt_phrasing(ph))
            if sources:
                lines.append(f"- sources: {_fmt_list(sources)}")
            if reviewed[0]:
                lines.append(f"- reviewed: {{by: {reviewed[0]}, at: {reviewed[1]}}}")
            if see_also:
                lines.append(f"- see_also: {_fmt_list(see_also)}")
            if policy != "answerable":
                lines.append(f"- policy: {policy}")
            if policy_ref:
                lines.append(f"- policy_ref: {policy_ref}")
            lines.append(f"- target_user: {_fmt_list(sorted(target_user))}")
            lines.append(f"- business_types: {_fmt_list(business_types)}")
            if categories:
                lines.append(f"- categories: {_fmt_list(categories)}")
            lines.append(f"- instance_applicability: {ia}")
            lines.extend(content_units)
            lines.append("")

            for ph in phrasings:
                k = _nfkc(ph.text)
                owner = phrasing_owner.get(k)
                if owner and owner != f["id"]:
                    _fail(f"講法重覆掛兩個細目：{ph.text!r}（{owner} 與 {f['id']}）")
                phrasing_owner[k] = f["id"]

            correspondence.append({"new": f["id"], "title": f["title"],
                                   "from": [_ci.TMP_PREFIX + b for b in srcs_bare],
                                   "ops": sorted({r["op"] for r in id_map if r["new"] == f["id"]}),
                                   "units": len(content_units)})

            for b, split_flag in zip(srcs_bare, split_flags):
                if split_flag and b not in split_recorded:
                    split_recorded.add(b)
                    children = sorted(old_to_news[b])
                    pending_splits.append({"old": _ci.TMP_PREFIX + b, "children": children, "note": "待人工分句"})
                    of = old_fine_by_bare[b]
                    for ph in of.phrasings:
                        pending_phrasings.append({"text": ph.text, "source": ph.source, "status": ph.status,
                                                   "from_old": _ci.TMP_PREFIX + b, "candidates": children})

        shelf_texts[cid] = "\n".join(lines).rstrip("\n") + "\n"

    idmap = {"id_map": id_map, "fines": correspondence}
    pending = {"pending-splits": pending_splits, "pending-phrasings": pending_phrasings,
               "pending-see_also": pending_see_also}
    return shelf_texts, idmap, pending


# ---------------------------------------------------------------------------
# --shelf 擴充模式（brief-9.7）：只補一架，其餘八架原樣照抄
# ---------------------------------------------------------------------------

def _helpcenter_slug(draft_id: str) -> str:
    """幫助中心頁 id（如 `help:Landlordonboarding01`）→ `sources`／`pending-content` 用的 slug——
    去掉 `help:` 前綴；沒有此前綴的形狀原樣回傳（不猜、不報錯，呼叫端已知這是草稿 id）。"""
    return draft_id[len("help:"):] if draft_id.startswith("help:") else draft_id


def render_expand(proposal: dict, canon_doc, shelf: str, *, kb_by_id: dict, draft_by_tmpid: dict,
                   version: str, scopes_by_code: dict, coarse_titles_by_code: dict,
                   canon_name: str = "jgb") -> tuple:
    """擴充模式渲染（brief-9.7）：**只重算 `shelf` 架**，其餘八架原樣照抄既有正本原始檔位元組
    （呼叫端用 `canon_doc.source_path` 讀原檔，⛔ 不透過解析結果重新排版——排版任何差異都會讓
    「非 X 架逐位元＝輸入」破功）。回 `(shelf_texts, idmap, pending_content)`；`shelf_texts`
    恆備齊九碼（`_SHELF_CODES`），非 `shelf` 的八碼＝原檔全文。

    `shelf` 內的細目分兩種來源（依 `merge_of`／`split_from` 的 id 前綴判斷，⛔ 不看 `op` 字面——
    與 `render_remap` 同一設計原則：op 是提議者的意圖標記，實際渲染規則由來源形狀決定）：

    - 全部來源是 `tmp:canon:*`（該架既有細目）：規則同 `render_remap`——唯一且未被拆分的來源
      原樣帶過；其餘（來源 >1 或唯一來源本身被拆分）走合併模式（講法聯集去重、`reviewed` 丟棄、
      `policy` 需一致否則拒套）。`target_user` 一律由提議必填驅動。
    - 含 `tmp:kb:*`／`tmp:draft:*`（新材料，op=new 的典型情況；⛔ 不支援與 `tmp:canon:*` 混用，
      混用即拒套——這是尚未定義的語意，寧可拒套也不要猜）：
        - 只有 `tmp:kb:*`：內容＝各列 kb `answer` 依 `split_sentences` 切句、依 `merge_of` 順序
          串接（不去重）；`sources: [kb:<kb_id>…]`；`business_types` 取提議 `business_types`
          （缺 ⇒ 預設 `[system_provider]`）；`target_user` 取提議；不寫 `reviewed`。
        - 含至少一個 `tmp:draft:*`：內容為空（零 `content_units` 合法）；
          `sources: [helpcenter:<slug>…]`；並記一筆 `pending_content`
          （`id`／`title`／來源頁 `source_pages`：`[{id, text}…]`）供人／代理撰寫正文。
      新細目 id 必須 `{canon_name}/{shelf}/<slug>`，且**不得與整座圖書館任何既有 id 相同**
      （撞 ⇒ 拒套，`_fail` 在任何檔案寫出之前呼叫，天然不落檔）。
    """
    if canon_doc.source_path is None:
        _fail("擴充模式需要 canon_doc.source_path（原檔位元組來源）")
    coarse_id, coarse_title = _target_coarse(canon_doc, shelf, coarse_titles_by_code[shelf])
    all_ids = {f.id for f in canon_doc.fines()}
    # ⚠️ 計畫 9.10 S5 第二輪（DSP-070 病灶）：⛔ 不得用 `f.coarse_id == shelf`——粗目 id
    # 自 S1 起恆為 `<架字母>-<slug>`，S5 移除裸字母後永遠不等於架字母，會靜默回空
    # （現行正本實測：`coarse_id == shelf` 命中 0 筆，`_ci.fine_shelf_letter` 命中 63 筆）。
    old_fine_by_bare = {f.id: f for f in canon_doc.fines() if _ci.fine_shelf_letter(f.id) == shelf}
    other_ids = all_ids - set(old_fine_by_bare)

    id_map = proposal.get("id_map")
    if not id_map:
        _fail("提議未附 id_map（對應表）⇒ 拒套")
    old_to_news: dict = {}
    for row in id_map:
        old = row.get("old")
        if old and old.startswith(_ci.TMP_CANON_PREFIX):
            old_to_news.setdefault(_ci.bare_canon_id(old), set()).add(row["new"])
    mapped_old = {r["old"] for r in id_map if r.get("old") is not None}
    mapped_new = {r["new"] for r in id_map}

    def is_split(bare: str) -> bool:
        return len(old_to_news.get(bare, ())) > 1

    fines = [f for f in proposal["fines"] if f.get("coarse_id") == shelf]
    if len(fines) != len(proposal["fines"]):
        bad = sorted({f["id"] for f in proposal["fines"] if f.get("coarse_id") != shelf})
        _fail(f"擴充模式：提議含 coarse_id 不等於 --shelf {shelf!r} 的細目 ⇒ 拒套：{bad}")

    correspondence: list = []
    pending_content: list = []
    pending_splits: list = []
    pending_phrasings: list = []
    pending_see_also: list = []
    split_recorded: set = set()
    lines = ["---", f"coarse: {shelf}", f"title: {coarse_titles_by_code[shelf]}",
             f"scope: {scopes_by_code[shelf]}", f"version: {version}",
             f"reviewers: {_fmt_list(canon_doc.reviewers)}", f"language: {canon_doc.language}", "---",
             f"## {coarse_title} {{#{coarse_id}}}"]

    for f in fines:
        if f["id"].split("/")[0] != canon_name:
            _fail(f"細目 {f['id']} 的 id 前綴與 --canon-name {canon_name!r} 不符 ⇒ 拒套")
        srcs = _dedupe_preserve(list(f.get("merge_of") or []) + list(f.get("split_from") or []))
        if not srcs:
            _fail(f"細目 {f['id']} 沒有來源項目（merge_of／split_from 皆空）⇒ 拒套")
        unknown = [s for s in srcs
                   if not (s.startswith(_ci.TMP_CANON_PREFIX) or s.startswith("tmp:kb:") or s.startswith("tmp:draft:"))]
        if unknown:
            _fail(f"細目 {f['id']} 的來源形狀未知：{unknown} ⇒ 拒套")
        for s in srcs:
            if s not in mapped_old:
                _fail(f"細目 {f['id']} 的來源 {s} 不在 id_map ⇒ 拒套")
        if f["id"] not in mapped_new:
            _fail(f"細目 {f['id']} 不在 id_map.new ⇒ 拒套")

        target_user = f.get("target_user")
        if not target_user:
            _fail(f"細目 {f['id']} 缺必填屬性 target_user（提案需明列）⇒ 拒套")
        bad_tu = sorted(set(target_user) - {"prospect", "property_manager"})
        if bad_tu:
            _fail(f"細目 {f['id']} 的 target_user 含未知值：{bad_tu} ⇒ 拒套")

        canon_srcs = [s for s in srcs if s.startswith(_ci.TMP_CANON_PREFIX)]
        kb_srcs = [s for s in srcs if s.startswith("tmp:kb:")]
        draft_srcs = [s for s in srcs if s.startswith("tmp:draft:")]

        # 既有細目吸收新材料（canon_srcs ＋ kb/draft，三角度提議的常態，2026-09-16 定義）：
        # 既有部分照 render_remap 規則帶過（講法／sources／policy／categories 原樣），再把 kb 列切句**接在既有內容之後**、
        # sources 追加 `kb:`／`helpcenter:`；內容變了 ⇒ `reviewed` 一律丟棄（R2.9：content_sha 變即待審）；
        # 含 draft 來源 ⇒ 另記 pending_content（既有內容仍在，等人補寫該頁段落）。

        if canon_srcs:
            # -------------------- 既有細目：規則同 render_remap --------------------
            bares = _dedupe_preserve(_ci.bare_canon_id(s) for s in canon_srcs)
            for b in bares:
                if b not in old_fine_by_bare:
                    _fail(f"細目 {f['id']} 的來源 {_ci.TMP_CANON_PREFIX}{b} 不在架 {shelf} 既有細目 ⇒ 拒套")
                if f["id"] not in old_to_news.get(b, set()):
                    _fail(f"細目 {f['id']} 與來源 {_ci.TMP_CANON_PREFIX}{b} 的 id_map 不一致 ⇒ 拒套")
            old_fines = [old_fine_by_bare[b] for b in bares]
            split_flags = [is_split(b) for b in bares]
            content_units: list = []
            for of in old_fines:
                content_units.extend(of.content_units)
            if len(old_fines) == 1 and not split_flags[0]:
                of = old_fines[0]
                phrasings = list(of.phrasings)
                sources_out = list(of.sources)
                policy, policy_ref, ia = of.policy, of.policy_ref, of.instance_applicability
                business_types, categories = of.business_types, of.categories
                reviewed = (of.reviewed_by, of.reviewed_at)
                see_also_raw = list(of.see_also)
            else:
                phrasings = []
                seen_p: set = set()
                for of, sf in zip(old_fines, split_flags):
                    if sf:
                        continue
                    for ph in of.phrasings:
                        k = _nfkc(ph.text)
                        if k not in seen_p:
                            seen_p.add(k)
                            phrasings.append(ph)
                sources_out = _dedupe_preserve(s for of in old_fines for s in of.sources)
                policies = {of.policy for of in old_fines}
                if len(policies) > 1:
                    _fail(f"細目 {f['id']} 合併來源 policy 不一致：{sorted(policies)}（交人裁）")
                policy = next(iter(policies))
                policy_ref = next((of.policy_ref for of in old_fines if of.policy_ref), None)
                ia_set = {of.instance_applicability for of in old_fines}
                ia = next(iter(ia_set)) if len(ia_set) == 1 else "general"
                business_types = tuple(sorted({v for of in old_fines for v in of.business_types}))
                categories = tuple(sorted({v for of in old_fines for v in of.categories}))
                reviewed = (None, None)
                see_also_raw = _dedupe_preserve(v for of in old_fines for v in of.see_also)

            if kb_srcs or draft_srcs:
                content_units = list(content_units)
                extra_sources: list = []
                for s in kb_srcs:
                    kb_id = s[len("tmp:kb:"):]
                    row = kb_by_id.get(kb_id)
                    if row is None:
                        _fail(f"細目 {f['id']} 的來源 {s} 不在 --kb-rows 材料 ⇒ 拒套")
                    content_units.extend(sentences_of(row["answer"]))
                    extra_sources.append(f"kb:{kb_id}")
                if draft_srcs:
                    source_pages = []
                    for s in draft_srcs:
                        draft = draft_by_tmpid.get(s)
                        if draft is None:
                            _fail(f"細目 {f['id']} 的來源 {s} 不在 --drafts 材料 ⇒ 拒套")
                        page_id = draft.get("id", s)
                        extra_sources.append(f"helpcenter:{_helpcenter_slug(page_id)}")
                        source_pages.append({"id": page_id, "text": draft.get("text", "")})
                    pending_content.append({"id": f["id"], "title": f["title"], "source_pages": source_pages,
                                            "note": "既有細目吸收幫助中心頁：既有內容保留，該頁段落待補寫"})
                sources_out = _dedupe_preserve(list(sources_out) + extra_sources)
                reviewed = (None, None)

            see_also = []
            for t in see_also_raw:
                cands = old_to_news.get(t, set())
                if cands:
                    if len(cands) == 1:
                        see_also.append(next(iter(cands)))
                    else:
                        pending_see_also.append({"from": f["id"], "target_old": t, "reason": "target_split"})
                elif t in other_ids:
                    see_also.append(t)  # 未被本次擴充觸及的架，id 不變，原樣通行
                else:
                    pending_see_also.append({"from": f["id"], "target_old": t, "reason": "target_missing"})
            see_also = _dedupe_preserve(see_also)

            lines.append(f"### {f['title']} {{#{f['id']}}}")
            if phrasings:
                lines.append("- phrasings:")
                for ph in phrasings:
                    lines.append(_fmt_phrasing(ph))
            if sources_out:
                lines.append(f"- sources: {_fmt_list(sources_out)}")
            if reviewed[0]:
                lines.append(f"- reviewed: {{by: {reviewed[0]}, at: {reviewed[1]}}}")
            if see_also:
                lines.append(f"- see_also: {_fmt_list(see_also)}")
            if policy != "answerable":
                lines.append(f"- policy: {policy}")
            if policy_ref:
                lines.append(f"- policy_ref: {policy_ref}")
            lines.append(f"- target_user: {_fmt_list(sorted(target_user))}")
            lines.append(f"- business_types: {_fmt_list(business_types)}")
            if categories:
                lines.append(f"- categories: {_fmt_list(categories)}")
            lines.append(f"- instance_applicability: {ia}")
            lines.extend(content_units)
            lines.append("")

            # 講法唯一性（本架內／跨架皆是）一律交回讀 `parse_canon_dir` 把關，⛔ 不在此重覆判斷。

            for b, sf in zip(bares, split_flags):
                if sf and b not in split_recorded:
                    split_recorded.add(b)
                    children = sorted(old_to_news[b])
                    pending_splits.append({"old": f"{_ci.TMP_CANON_PREFIX}{b}", "children": children, "note": "待人工分句"})
                    of = old_fine_by_bare[b]
                    for ph in of.phrasings:
                        pending_phrasings.append({"text": ph.text, "source": ph.source, "status": ph.status,
                                                   "from_old": f"{_ci.TMP_CANON_PREFIX}{b}", "candidates": children})

            correspondence.append({"new": f["id"], "title": f["title"],
                                   "from": [f"{_ci.TMP_CANON_PREFIX}{b}" for b in bares],
                                   "ops": sorted({r["op"] for r in id_map if r["new"] == f["id"]}),
                                   "units": len(content_units)})
            continue

        # -------------------- 新細目：來源為 tmp:kb:*／tmp:draft:* --------------------
        if f["id"] in all_ids:
            _fail(f"新細目 {f['id']} 與既有正本 id 撞 ⇒ 拒套")

        # kb 列先渲染（有幾列切幾列、依 merge_of 順序），草稿只追加 sources 與 pending-content——
        # ⛔ 草稿不得把 kb 內容擋掉（2026-09-16 實跑抓到：kb＋draft 同列時 kb 句整個消失、sources 也丟）。
        content_units = []
        kb_ids = []
        for s in kb_srcs:
            kb_id = s[len("tmp:kb:"):]
            row = kb_by_id.get(kb_id)
            if row is None:
                _fail(f"細目 {f['id']} 的來源 {s} 不在 --kb-rows 材料 ⇒ 拒套")
            kb_ids.append(kb_id)
            for sent in sentences_of(row["answer"]):
                content_units.append(sent)
        sources_out = [f"kb:{kid}" for kid in _dedupe_preserve(kb_ids)]
        if draft_srcs:
            source_pages = []
            hc_slugs = []
            for s in draft_srcs:
                draft = draft_by_tmpid.get(s)
                if draft is None:
                    _fail(f"細目 {f['id']} 的來源 {s} 不在 --drafts 材料 ⇒ 拒套")
                page_id = draft.get("id", s)
                slug = _helpcenter_slug(page_id)
                hc_slugs.append(slug)
                source_pages.append({"id": page_id, "text": draft.get("text", "")})
            hc_slugs = _dedupe_preserve(hc_slugs)
            sources_out = _dedupe_preserve(sources_out + [f"helpcenter:{slug}" for slug in hc_slugs])
            pending_content.append({"id": f["id"], "title": f["title"], "source_pages": source_pages,
                                    **({"note": "已有 kb 句，該頁段落待補寫"} if content_units else {})})

        business_types = tuple(f.get("business_types") or ("system_provider",))

        lines.append(f"### {f['title']} {{#{f['id']}}}")
        if sources_out:
            lines.append(f"- sources: {_fmt_list(sources_out)}")
        lines.append(f"- target_user: {_fmt_list(sorted(target_user))}")
        lines.append(f"- business_types: {_fmt_list(business_types)}")
        lines.append("- instance_applicability: general")
        lines.extend(content_units)
        lines.append("")

        correspondence.append({"new": f["id"], "title": f["title"], "from": srcs,
                               "ops": sorted({r["op"] for r in id_map if r["new"] == f["id"]}),
                               "units": len(content_units)})

    shelf_texts: dict = {}
    for code in _SHELF_CODES:
        if code == shelf:
            shelf_texts[code] = "\n".join(lines).rstrip("\n") + "\n"
        else:
            with open(os.path.join(canon_doc.source_path, f"{code}.md"), encoding="utf-8") as fh:
                shelf_texts[code] = fh.read()

    idmap = {"id_map": id_map, "fines": correspondence}
    pending = {"pending-splits": pending_splits, "pending-phrasings": pending_phrasings,
               "pending-see_also": pending_see_also, "pending-content": pending_content}
    return shelf_texts, idmap, pending


def _resolve_scopes_by_code(scopes_arg: str | None, canon_doc) -> dict:
    """優先序：`--scopes` 檔 ＞ 輸入正本自帶的 `scopes`（目錄路徑才有）＞ `schemas/scopes-jgb.json` 內建預設。"""
    override = _load_scopes_file(scopes_arg) if scopes_arg else {}
    from_canon = dict(getattr(canon_doc, "scopes", ()) or ())
    default = _load_default_scopes()
    out = {}
    for code in _SHELF_CODES:
        val = override.get(code) or from_canon.get(code) or default.get(code)
        if not val or not str(val).strip():
            _fail(f"無法決定架 {code} 的 scope（--scopes／輸入正本／內建預設皆缺）")
        out[code] = str(val).strip()
    return out


def _resolve_coarse_titles_by_code(proposal: dict, canon_doc) -> dict:
    """架標題（以架字母為鍵）。優先序：輸入正本自帶的架標題 ＞ 提議 `coarses` 自帶標題 ＞
    `schemas/coarses-jgb.json` 內建預設（九碼恆備齊，供本次提議沒提到的架兜底）。

    ⚠️ 計畫 9.10 S5 第三輪（verifier F1）：目錄正本的架標題在 `shelf_titles`（鍵＝架字母）；
    ⛔ 不得用 `{c.id: c.title for c in coarses}` 查架字母——三層正本粗目 id 是 `A-registration`
    形狀，恆查不到，會靜默退回預設、把業主改過的架名蓋回去。單檔正本的裸字母粗目 id 就是架字母，照舊可用。"""
    from_canon = {c.id: c.title for c in getattr(canon_doc, "coarses", ()) if len(c.id) == 1}
    from_canon.update(dict(getattr(canon_doc, "shelf_titles", ()) or ()))
    from_proposal = {c["id"]: c["title"] for c in proposal.get("coarses", [])}
    default = _load_default_coarse_titles()
    out = {}
    for code in _SHELF_CODES:
        title = from_canon.get(code) or from_proposal.get(code) or default.get(code)
        if not title:
            _fail(f"無法決定架 {code} 的粗目標題（輸入正本／提議／內建預設皆缺）")
        out[code] = title
    return out


def _load_scopes_file(path: str) -> dict:
    doc = _aa._load_json(path)
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--proposal", required=True, help="structure-proposal envelope 或裸提議 JSON")
    p.add_argument("--kb-rows", default=None, help="與 --canon 二擇一")
    p.add_argument("--drafts", default=None)
    p.add_argument("--cells", default=None, help="缺口地圖 map-v2.json（選填；給了才衍生 helpcenter 來源，F1；⛔ 只在 --kb-rows 模式適用）")
    p.add_argument("--canon", default=None,
                   help="既有正本（單檔或目錄）；與 --kb-rows 二擇一。給了 ⇒ 重切模式（任務 9.3⑤，見 render_remap）")
    p.add_argument("--scopes", default=None,
                   help="九架 scope JSON（schemas/scopes-jgb.json 形狀）；⛔ 只在 --canon 時使用；不給則沿用輸入正本自帶 scopes 或內建預設")
    p.add_argument("--out-pending-dir", default=None,
                   help="重切模式待審輸出目錄；⛔ 只在 --canon 時使用；不給預設 <out>/pending/")
    p.add_argument("--canon-name", default="jgb", help="⛔ 只在 --canon 模式使用：驗證細目 id 首段（圖書館正本名恆為 jgb）")
    p.add_argument("--audience", default="prospect",
                   help="⛔ 只在 --kb-rows 模式使用：寫入單檔 audience 欄（值域須 ∈ canon_parser.AUDIENCES，⛔ 不是 jgb——"
                        "圖書館正本名只在目錄路徑成立，單檔仍是舊制單一受眾）")
    p.add_argument("--version", default=None, help="正本版本字串；--canon 模式不給則沿用輸入正本 version，--kb-rows 模式必給")
    p.add_argument("--reviewers", default="owner")
    p.add_argument("--language", default="zh-TW")
    p.add_argument("--budget-tokens", type=int, default=12000)   # 2026-09-07 業主裁：實測 cl100k 10,336 tokens
    p.add_argument("--target-user", default="prospect")
    p.add_argument("--business-types", default="system_provider")
    p.add_argument("--out-md", default=None, help="⛔ 只在 --kb-rows 模式使用（單檔輸出）")
    p.add_argument("--out-idmap", default=None, help="--kb-rows 模式必給；--canon 模式不給則預設 <out>/id_map.json")
    p.add_argument("--out", default=None, help="⛔ 只在 --canon 模式使用（九架輸出目錄）")
    p.add_argument("--shelf", default=None,
                   help="擴充模式（brief-9.7）：只補這一架（九架碼之一）；須同時給 --canon（圖書館目錄）＋--kb-rows，"
                        "選填 --drafts；其餘八架逐位元照抄；任何拒套都不落任何輸出檔")
    a = p.parse_args()

    if a.shelf:
        return _main_expand(a)

    if bool(a.kb_rows) == bool(a.canon):
        print("[apply_proposal] --kb-rows 與 --canon 二擇一（不得同給、不得都不給）", file=sys.stderr)
        return 2

    doc = _aa._load_json(a.proposal)
    proposal = doc["payload"]["synthesis"] if isinstance(doc, dict) and "payload" in doc else doc

    if a.canon:
        if not a.out:
            print("[apply_proposal] --canon（重切模式）須給 --out（九架輸出目錄）", file=sys.stderr)
            return 2
        canon_doc = _ci.load_canon_doc(a.canon)
        version = a.version or canon_doc.version
        scopes_by_code = _resolve_scopes_by_code(a.scopes, canon_doc)
        coarse_titles_by_code = _resolve_coarse_titles_by_code(proposal, canon_doc)
        shelf_texts, idmap, pending = render_remap(
            proposal, canon_doc, version=version, scopes_by_code=scopes_by_code,
            coarse_titles_by_code=coarse_titles_by_code, canon_name=a.canon_name,
        )
        os.makedirs(a.out, exist_ok=True)
        for code in _SHELF_CODES:
            with open(os.path.join(a.out, f"{code}.md"), "w", encoding="utf-8") as fh:
                fh.write(shelf_texts[code])
        try:
            parsed = parse_canon_dir(a.out)
        except CanonFormatError as exc:
            print(f"[apply_proposal] 產出未通過 parse_canon_dir：{exc}", file=sys.stderr)
            return 2
        export_catalog(parsed, os.path.join(a.out, "CATALOG.md"))
        export_json(parsed, os.path.join(a.out, f"{a.canon_name}.json"))

        out_idmap = a.out_idmap or os.path.join(a.out, "id_map.json")
        with open(out_idmap, "w", encoding="utf-8") as fh:
            json.dump({**idmap, "canon_sha256": parsed.canon_sha256}, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")

        out_pending_dir = a.out_pending_dir or os.path.join(a.out, "pending")
        os.makedirs(out_pending_dir, exist_ok=True)
        for name in ("pending-splits", "pending-phrasings", "pending-see_also"):
            with open(os.path.join(out_pending_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
                json.dump(pending[name], fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.write("\n")
        print(f"[apply_proposal] pending splits={len(pending['pending-splits'])} "
              f"phrasings={len(pending['pending-phrasings'])} see_also={len(pending['pending-see_also'])} → {out_pending_dir}")
        print(f"[apply_proposal] ok coarses={len(parsed.coarses)} fines={len(parsed.fines())} "
              f"canon_sha256={parsed.canon_sha256[:12]} → {a.out}")
        return 0

    # ------------------------------------------------------------------
    # --kb-rows 模式（單檔輸出，未經 DSP-058 圖書館重切；仍供全新知識草稿的臨時彙整用）
    # ------------------------------------------------------------------
    if not a.out_md or not a.out_idmap:
        print("[apply_proposal] --kb-rows 模式須給 --out-md 與 --out-idmap", file=sys.stderr)
        return 2
    if not a.version:
        print("[apply_proposal] --kb-rows 模式須給 --version", file=sys.stderr)
        return 2

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

    draft_hc, kb_hc = build_cells_lookups(a.cells, a.drafts) if a.cells else ({}, {})

    md, idmap = render(proposal, items_by_id, meta, audience=a.audience, version=a.version,
                       reviewers=[x.strip() for x in a.reviewers.split(",")], language=a.language,
                       budget_tokens=a.budget_tokens, target_user=[x.strip() for x in a.target_user.split(",")],
                       business_types=[x.strip() for x in a.business_types.split(",")],
                       draft_hc=draft_hc, kb_hc=kb_hc)
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


def _main_expand(a) -> int:
    """`--shelf` 擴充模式的 main 分支（brief-9.7）。**任何拒套都在寫出前發生**：九架先渲染到暫存目錄、
    `parse_canon_dir` 回讀通過（含跨架講法唯一）才整批搬到 `--out`；回讀失敗 ⇒ 暫存目錄整個丟掉，
    `--out` 一個檔都不會出現。"""
    import tempfile
    if a.shelf not in _SHELF_CODES:
        print(f"[apply_proposal] --shelf 須為 {_SHELF_CODES} 之一，得到 {a.shelf!r}", file=sys.stderr)
        return 2
    if not (a.canon and a.kb_rows):
        print("[apply_proposal] 擴充模式（--shelf）須同時給 --canon（圖書館目錄）與 --kb-rows", file=sys.stderr)
        return 2
    if not os.path.isdir(a.canon):
        print(f"[apply_proposal] 擴充模式 --canon 須為圖書館目錄（九架），得到：{a.canon!r}", file=sys.stderr)
        return 2
    if not a.out:
        print("[apply_proposal] 擴充模式須給 --out（九架輸出目錄）", file=sys.stderr)
        return 2
    if os.path.exists(a.out) and os.listdir(a.out):
        print(f"[apply_proposal] 擴充模式 --out 必須是不存在或空目錄（⛔ 不覆蓋）：{a.out!r}", file=sys.stderr)
        return 2

    doc = _aa._load_json(a.proposal)
    proposal = doc["payload"]["synthesis"] if isinstance(doc, dict) and "payload" in doc else doc

    canon_doc = _ci.load_canon_doc(a.canon)
    kb_doc = _aa._load_json(a.kb_rows)
    kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc
    kb_by_id = {str(r["kb_id"]): r for r in kb_rows}
    draft_by_tmpid: dict = {}
    if a.drafts:
        d_doc = _aa._load_json(a.drafts)
        drafts = d_doc["knowledge"] if isinstance(d_doc, dict) else d_doc
        draft_by_tmpid = {f"tmp:draft:{i + 1}": d for i, d in enumerate(drafts)}

    version = a.version or canon_doc.version
    scopes_by_code = _resolve_scopes_by_code(a.scopes, canon_doc)
    coarse_titles_by_code = _resolve_coarse_titles_by_code(proposal, canon_doc)
    shelf_texts, idmap, pending = render_expand(
        proposal, canon_doc, a.shelf, kb_by_id=kb_by_id, draft_by_tmpid=draft_by_tmpid,
        version=version, scopes_by_code=scopes_by_code, coarse_titles_by_code=coarse_titles_by_code,
        canon_name=a.canon_name,
    )

    tmp_dir = tempfile.mkdtemp(prefix="apply_expand_")
    try:
        for code in _SHELF_CODES:
            with open(os.path.join(tmp_dir, f"{code}.md"), "w", encoding="utf-8") as fh:
                fh.write(shelf_texts[code])
        try:
            parsed = parse_canon_dir(tmp_dir)
        except CanonFormatError as exc:
            print(f"[apply_proposal] 擴充產出未通過 parse_canon_dir（未落任何檔）：{exc}", file=sys.stderr)
            return 2
        export_catalog(parsed, os.path.join(tmp_dir, "CATALOG.md"))
        export_json(parsed, os.path.join(tmp_dir, f"{a.canon_name}.json"))
        with open(os.path.join(tmp_dir, "id_map.json"), "w", encoding="utf-8") as fh:
            json.dump({**idmap, "canon_sha256": parsed.canon_sha256}, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        pend_dir = os.path.join(tmp_dir, "pending")
        os.makedirs(pend_dir, exist_ok=True)
        for name in ("pending-splits", "pending-phrasings", "pending-see_also", "pending-content"):
            with open(os.path.join(pend_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
                json.dump(pending[name], fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.write("\n")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        if os.path.isdir(a.out):
            os.rmdir(a.out)
        shutil.move(tmp_dir, a.out)
        tmp_dir = None
    finally:
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"[apply_proposal] expand shelf={a.shelf} pending content={len(pending['pending-content'])} "
          f"splits={len(pending['pending-splits'])} phrasings={len(pending['pending-phrasings'])} "
          f"see_also={len(pending['pending-see_also'])}")
    print(f"[apply_proposal] ok coarses={len(parsed.coarses)} fines={len(parsed.fines())} "
          f"canon_sha256={parsed.canon_sha256[:12]} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
