#!/usr/bin/env python3
"""步 2 structure：結構提議（knowledge-outline-and-intent-architecture 任務 2.3）。

形態（業主 2026-09-06 裁）：**⛔ 本步不打模型 API**——3 個角度提議＋1 個合成由主 session 以 Claude Code 子代理（Agent 工具）執行；
本腳本只負責決定性的部分：
  prepare       輸入項目（kb 列＋草稿，白名單投影 id/title/content）＋固定粗目 → 3 份角度 prompt（逐位元穩定）＋schema＋items.json
  validate      子代理回傳的提議 JSON → schema＋事後規則（id_map 覆蓋每一輸入項目、細目 id 合規、coarse ∈ 粗目表）；不合 exit 2
  synth-prompt  三份（已 validate 的）提議 → 合成 prompt
  package       三份提議＋合成 → StepEnvelope（`schemas/structure-proposal.json`，deterministic=false）＋journal；合成不得引入三份都沒有的細目
子代理互不可見：三個角度各自只拿自己的 prompt；合成只拿三份 JSON。原始輸出留 raw/（gitignored）。
提示詞只寫定義不寫例子（業主紀律）。粗目由 `schemas/coarses-jgb.json` 固定（9.6 S4 起兩受眾共用同一份），提議只決定細目與歸屬。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_aa = _load_sibling("answerability_args")
_env = _load_sibling("_envelope")
_ci = _load_sibling("canon_items")

ANGLES: tuple[tuple[str, str], ...] = (
    ("product_feature", "產品功能面：以產品面向使用者的一件功能或規則（權限 action、幫助中心段）為切分依據；一件可被問的事對應一個細目，⛔ 不猜使用者會怎麼問（問法在步 3 講法處理）。"),
    ("content_boundary", "內容邊界：以內容能否獨立成立、彼此不重疊為切分依據；兩段內容若互相依賴才完整，屬同一細目；若各自完整且主題不同，屬不同細目。"),
    ("audience_level", "受眾層級：以受眾在該主題需要的層級（能力／操作／權益）為切分依據；同一受眾同一主題只保留一個層級的細目，其他層級以另見交叉引用。"),
)
OPS = ("keep", "split", "merge", "move", "new")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def proposal_schema(coarse_ids: list, item_ids: list, *, expand: bool = False) -> dict:
    fine_props = {
        "id": {"type": "string"},
        "coarse_id": {"type": "string", "enum": list(coarse_ids)},
        "title": {"type": "string"},
        "slug": {"type": "string"},
        "merge_of": {"type": "array", "items": {"type": "string", "enum": list(item_ids)}},
        "split_from": {"type": "array", "items": {"type": "string", "enum": list(item_ids)}},
        "moved_from": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}},
    }
    fine_required = ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user"]
    if expand:
        fine_props["op"] = {"type": "string", "enum": list(OPS)}
        fine_required = fine_required + ["op"]
    schema = {
        "type": "object",
        "properties": {
            "angle": {"type": "string"},
            "coarses": {"type": "array", "items": {
                "type": "object",
                "properties": {"id": {"type": "string", "enum": list(coarse_ids)}, "title": {"type": "string"}},
                "required": ["id", "title"], "additionalProperties": False}},
            "fines": {"type": "array", "items": {
                "type": "object", "properties": fine_props, "required": fine_required, "additionalProperties": False}},
            "id_map": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "old": {"anyOf": [{"type": "string", "enum": list(item_ids)}, {"type": "null"}]},
                    "new": {"type": "string"},
                    "op": {"type": "string", "enum": list(OPS)},
                },
                "required": ["old", "new", "op"], "additionalProperties": False}},
        },
        "required": ["angle", "coarses", "fines", "id_map"],
        "additionalProperties": False,
    }
    if expand:
        # 擴充模式：材料明顯屬他架 ⇒ 列此處，不提成細目（見 expand_spec_lines）；⛔ 不需出現在 id_map。
        schema["properties"]["out_of_shelf"] = {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "enum": list(item_ids)},
                "suggested_shelf": {"type": "string"},
                "why": {"type": "string"},
            },
            "required": ["id", "suggested_shelf", "why"], "additionalProperties": False}}
        schema["required"] = list(schema["required"]) + ["out_of_shelf"]
    return schema


def synthesis_schema(coarse_ids: list, item_ids: list, *, expand: bool = False) -> dict:
    s = proposal_schema(coarse_ids, item_ids, expand=expand)
    s["properties"]["rejected_alternatives"] = {"type": "array", "items": {
        "type": "object",
        "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}},
        "required": ["alternative", "reason"], "additionalProperties": False}}
    s["required"] = list(s["required"]) + ["rejected_alternatives"]
    return s


# ---------------------------------------------------------------------------
# prompt（只寫定義，不寫例子）
# ---------------------------------------------------------------------------

def items_block(items: list) -> str:
    lines = [f"## 輸入項目（{len(items)} 筆，原序列舉）"]
    for it in items:
        lines += [f"### {it['id']}", f"標題：{it['title']}", f"內容：{it['content']}", ""]
    return "\n".join(lines) + "\n"


def coarses_block(audience: str, coarses: list) -> str:
    lines = [f"## 粗目（受眾 {audience}，固定，⛔ 不得增刪改）"]
    lines += [f"- {c['id']}：{c['title']}" for c in coarses]
    return "\n".join(lines) + "\n"


def expand_spec_lines(shelf: str) -> list:
    """擴充模式（brief-9.7）專屬輸出定義補充：一次只補一架，其餘架不在本次討論範圍。"""
    return [
        f"⚠️ 本次為擴充模式，**只補一架（{shelf}）**：候選項目分兩種——`tmp:canon:*`（{shelf} 架既有細目）"
        f"與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。",
        f"op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；"
        "新材料成為新細目一律 `op=new`。",
        f"fines：本次每一筆 `coarse_id` 必須等於 `{shelf}`，`id` 必須為 `jgb/{shelf}/<slug>`。",
        "out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；"
        "此類項目不需出現在 id_map。",
    ]


def output_spec_block(audience: str, *, shelf: str | None = None) -> str:
    lines = [
        "## 輸出定義",
        f"fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `{audience}/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；"
        "`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；"
        "`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。",
        ("id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；"
         "op=new 的列 old＝該新材料的項目 id（tmp:kb:*／tmp:draft:*），⛔ 不是 null。"
         if shelf else
         "id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old 為 null，表示無來源的新細目（首跑不應出現）。"),
        "target_user：每一細目必填，值域 prospect／property_manager；兩者共用的細目明列兩者，不得空陣列。",
        "coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。",
        "同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。",
        "歸位判準（跨粗目命題只能歸一處，依下列定義判）：錢怎麼算歸帳務、錢怎麼進來歸帳務底下的收款金流子題；由合約條款決定的歸租約、出現在帳單列上的歸帳務；物件本身的屬性歸社區與物件、由合約驅動的物件狀態歸租約；通知是投遞管道，歸它所通知的那個領域，⛔ 不自成細目。",
        "講法唯一：同一句講法只掛一個細目；同一命題若答案因受眾而異，各受眾各一細目（不同 id），⛔ 不得同時存在中立細目與受眾版細目。",
    ]
    if shelf:
        lines += expand_spec_lines(shelf)
    lines.append("回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。")
    return "\n".join(lines) + "\n"


def build_angle_prompt(angle_key: str, angle_def: str, audience: str, coarses: list, items: list, schema: dict,
                        *, shelf: str | None = None) -> str:
    return "\n".join([
        "你是知識大綱的結構提議者。任務：把輸入項目切成細目並歸入固定粗目。",
        f"本次切分依據（角度 {angle_key}）：{angle_def}",
        "只依此角度切分；不評分、不排序、不判斷內容真偽；⛔ 不讀取任何檔案或工具，只依本訊息內容作答。",
        "",
        coarses_block(audience, coarses),
        output_spec_block(audience, shelf=shelf),
        "## schema",
        json.dumps(schema, ensure_ascii=False),
        "",
        items_block(items),
        f"請輸出角度 {angle_key} 的結構提議（angle 欄填 {angle_key}）。",
    ])


def build_synthesis_prompt(audience: str, coarses: list, items: list, proposals: list, schema: dict,
                            *, shelf: str | None = None) -> str:
    return "\n".join([
        "你是知識大綱結構的合成者。輸入＝同一批項目在三個角度下各自的結構提議。任務：合成一份最終提議。",
        "合成規則：三份提議一致處直接採用；分歧處擇一並把未採用的寫進 rejected_alternatives（alternative 一句描述、reason 一句理由）。",
        "⛔ 不得引入三份提議都沒有的細目 id；⛔ 不得改粗目；⛔ 不讀取任何檔案或工具。",
        "",
        coarses_block(audience, coarses),
        output_spec_block(audience, shelf=shelf),
        "## schema",
        json.dumps(schema, ensure_ascii=False),
        "",
        items_block(items),
        "## 三份角度提議",
        json.dumps(proposals, ensure_ascii=False, indent=1),
        "",
        "請輸出合成提議（angle 欄填 synthesis）。",
    ])


# ---------------------------------------------------------------------------
# 事後驗證
# ---------------------------------------------------------------------------

def validate_proposal(p: dict, audience: str, coarse_ids: set, item_ids: set, coarse_titles: dict | None = None,
                       *, shelf: str | None = None) -> list:
    errs = []
    if not isinstance(p, dict):
        return ["提議不是 JSON 物件"]
    fine_ids = [f.get("id") for f in p.get("fines", [])]
    if not fine_ids:
        errs.append("fines 為空")
    if len(set(fine_ids)) != len(fine_ids):
        errs.append("細目 id 重複")
    for f in p.get("fines", []):
        fid = str(f.get("id", ""))
        parts = fid.split("/")
        if len(parts) != 3 or parts[0] != audience or parts[1] != f.get("coarse_id") or not SLUG_RE.match(parts[2]) or parts[2] != f.get("slug"):
            errs.append(f"細目 id 不合規：{fid!r}（須為 {audience}/<coarse_id>/<slug> 且 slug 同欄）")
        if f.get("coarse_id") not in coarse_ids:
            errs.append(f"細目 {fid} 的 coarse_id 不在粗目表")
        if shelf and f.get("coarse_id") != shelf:
            errs.append(f"擴充模式：細目 {fid} 的 coarse_id {f.get('coarse_id')!r} 不等於 --shelf {shelf!r}")
        for k in ("merge_of", "split_from"):
            for old in f.get(k, []) or []:
                if old not in item_ids:
                    errs.append(f"細目 {fid} 的 {k} 含未知項目 {old!r}")
        if not (f.get("merge_of") or f.get("split_from")):
            errs.append(f"細目 {fid} 沒有來源項目（merge_of／split_from 皆空）")
        tu = f.get("target_user")
        if not tu:
            errs.append(f"細目 {fid} 缺必填屬性 target_user")
        elif set(tu) - {"prospect", "property_manager"}:
            errs.append(f"細目 {fid} 的 target_user 含未知值：{sorted(set(tu) - {'prospect', 'property_manager'})}")
        if shelf and f.get("op") not in OPS:
            errs.append(f"擴充模式：細目 {fid} 缺必填屬性 op（keep／merge／split／new 之一）")
    out_of_shelf_ids: set = set()
    if shelf:
        for o in p.get("out_of_shelf", []) or []:
            oid = o.get("id")
            if oid not in item_ids:
                errs.append(f"out_of_shelf 含未知項目 {oid!r}")
            if not o.get("suggested_shelf"):
                errs.append(f"out_of_shelf 項目 {oid!r} 缺 suggested_shelf")
            if not o.get("why"):
                errs.append(f"out_of_shelf 項目 {oid!r} 缺 why")
            out_of_shelf_ids.add(oid)
    mapped = {r.get("old") for r in p.get("id_map", []) if r.get("old") is not None}
    for r in p.get("id_map", []):
        if r.get("op") not in OPS:
            errs.append(f"id_map op 不合法：{r.get('op')!r}")
        if r.get("new") not in fine_ids:
            errs.append(f"id_map new 指向不存在的細目：{r.get('new')!r}")
        if shelf:
            # 擴充模式（brief-9.7）：`op=new`＝新材料提成新細目，old 必須是材料 id（tmp:kb:*／tmp:draft:*），
            # ⛔ 不是 null——apply 的 render_expand 靠 old 找內容來源。
            if r.get("op") == "new" and not (isinstance(r.get("old"), str)
                                              and (r["old"].startswith("tmp:kb:") or r["old"].startswith("tmp:draft:"))):
                errs.append(f"擴充模式 id_map op=new 的 old 須為材料 id（tmp:kb:*／tmp:draft:*），得到 {r.get('old')!r}")
            if r.get("op") != "new" and r.get("old") is None:
                errs.append(f"id_map op={r.get('op')} 的 old 不得為 null")
        else:
            if r.get("op") == "new" and r.get("old") is not None:
                errs.append("id_map op=new 的 old 須為 null")
            if r.get("op") != "new" and r.get("old") is None:
                errs.append(f"id_map op={r.get('op')} 的 old 不得為 null")
        if r.get("old") is not None and r.get("old") not in item_ids:
            errs.append(f"id_map old 未知項目 {r.get('old')!r}")
    missing = sorted(item_ids - mapped - out_of_shelf_ids)
    if missing:
        errs.append(f"id_map 未覆蓋輸入項目：{missing}")
    got = {c.get("id") for c in p.get("coarses", [])}
    if got != coarse_ids:
        errs.append(f"coarses 與固定粗目表不符：{sorted(got)} vs {sorted(coarse_ids)}")
    if coarse_titles:
        for c in p.get("coarses", []):
            if coarse_titles.get(c.get("id")) != c.get("title"):
                errs.append(f"粗目 {c.get('id')} title 被改：{c.get('title')!r}")
    return errs


def synthesis_extra_fines(synthesis: dict, proposals: list) -> list:
    allowed = {f["id"] for p in proposals for f in p.get("fines", [])}
    return sorted({f.get("id") for f in synthesis.get("fines", [])} - allowed)


# ---------------------------------------------------------------------------
# 載入
# ---------------------------------------------------------------------------

def load_items(kb_rows_path: str | None, drafts_path: str | None,
               canon_path: str | None = None, exclude_path: str | None = None, shelf: str | None = None) -> list:
    """輸入項目清單。`--kb-rows` 與 `--canon`（重切模式，任務 9.3⑤）二擇一——由呼叫端先以
    `check_source_args` 驗過互斥，本函式只依 `canon_path`／`shelf` 是否給定分派。

    擴充模式（`shelf` 給了，brief-9.7）：候選＝該架既有細目（`tmp:canon:*`，`_ci.shelf_items`）
    ＋kb 列（`tmp:kb:*`）＋drafts（`tmp:draft:*`，幫助中心頁形狀 `{id,summary,text?}`，
    ⛔ 與非擴充模式的 batch2 `question`/`answer` 形狀不同，各自一個候選建構函式）；
    `--canon` 與 `--kb-rows` 此模式下皆必給（`check_source_args` 已驗），`--exclude` 不支援。"""
    if shelf:
        _doc, items = _ci.shelf_items(canon_path, shelf)
        kb_doc = _aa._load_json(kb_rows_path)
        kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc
        items += [_aa.candidate_from_kb_row(r) for r in sorted(kb_rows, key=lambda r: r["kb_id"])]
        if drafts_path:
            drafts_doc = _aa._load_json(drafts_path)
            drafts = drafts_doc["knowledge"] if isinstance(drafts_doc, dict) else drafts_doc
            items += [_aa.candidate_from_help_draft(d, i + 1) for i, d in enumerate(drafts)]
        return items
    if canon_path:
        _audience, items, _excluded, _why = _ci.canon_items(canon_path, exclude_path)
    else:
        kb_doc = _aa._load_json(kb_rows_path)
        kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc
        items = [_aa.candidate_from_kb_row(r) for r in sorted(kb_rows, key=lambda r: r["kb_id"])]
    if drafts_path:
        drafts_doc = _aa._load_json(drafts_path)
        drafts = drafts_doc["knowledge"] if isinstance(drafts_doc, dict) else drafts_doc
        items += [_aa.candidate_from_draft(d, i + 1) for i, d in enumerate(drafts)]
    return items


def check_source_args(a) -> None:
    """`--kb-rows` 與 `--canon` 二擇一；`--exclude` 只在重切模式（給了 `--canon`）有效。不合 ⇒ exit 2。

    擴充模式（給了 `--shelf`，brief-9.7）：`--canon`＋`--kb-rows` 須**同時**給（不是二擇一），
    `--shelf` 須是九架碼之一；`--exclude` 不支援此模式（沒有排除既有細目這件事——擴充模式本來
    就只挑一架、其餘架不動）。"""
    shelf = getattr(a, "shelf", None)
    if shelf:
        if shelf not in _ci.SHELF_CODES:
            print(f"[structure_propose] --shelf 須為 {_ci.SHELF_CODES} 之一，得到 {shelf!r}", file=sys.stderr)
            raise SystemExit(2)
        if not (getattr(a, "canon", None) and getattr(a, "kb_rows", None)):
            print("[structure_propose] 擴充模式（--shelf）須同時給 --canon 與 --kb-rows", file=sys.stderr)
            raise SystemExit(2)
        if getattr(a, "exclude", None):
            print("[structure_propose] 擴充模式（--shelf）不支援 --exclude", file=sys.stderr)
            raise SystemExit(2)
        return
    if bool(getattr(a, "kb_rows", None)) == bool(getattr(a, "canon", None)):
        print("[structure_propose] --kb-rows 與 --canon 二擇一（不得同給、不得都不給）", file=sys.stderr)
        raise SystemExit(2)
    if getattr(a, "exclude", None) and not getattr(a, "canon", None):
        print("[structure_propose] --exclude 只在給 --canon（重切模式）時有效", file=sys.stderr)
        raise SystemExit(2)


def source_inputs_sha(a) -> dict:
    """`--kb-rows`／`--canon`（＋選填 `--exclude`）的 sha256，key 一律含 `kb`（重切模式下＝正本檔 sha）。
    擴充模式（`--shelf`）下 `--canon`＋`--kb-rows` 皆給，兩者 sha 都記（`kb` 取 `--kb-rows`，
    `canon` 另記正本目錄 sha）。"""
    sha: dict = {}
    if getattr(a, "shelf", None):
        sha["kb"] = _env.sha256_file(a.kb_rows)
        sha["canon"] = _env.sha256_path(a.canon)
        return sha
    if getattr(a, "canon", None):
        sha["kb"] = _env.sha256_path(a.canon)  # --canon 可能是目錄（圖書館正本）；sha256_path 兩者皆可
        sha["canon"] = sha["kb"]
        if getattr(a, "exclude", None):
            sha["exclude"] = _env.sha256_file(a.exclude)
    else:
        sha["kb"] = _env.sha256_file(a.kb_rows)
    return sha


def _load_coarses(path: str) -> tuple[str, list]:
    d = _aa._load_json(path)
    return d["audience"], d["coarses"]


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def load_proposal_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    return json.loads(_strip_fences(raw))


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_prepare(a) -> int:
    check_source_args(a)
    shelf = getattr(a, "shelf", None)
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts, a.canon, a.exclude, shelf)
    coarse_ids = [c["id"] for c in coarses]
    item_ids = [it["id"] for it in items]
    schema = proposal_schema(coarse_ids, item_ids, expand=bool(shelf))
    os.makedirs(a.out_dir, exist_ok=True)
    _env.write_json(os.path.join(a.out_dir, "items.json"), items)
    _env.write_json(os.path.join(a.out_dir, "schema-proposal.json"), schema)
    _env.write_json(os.path.join(a.out_dir, "schema-synthesis.json"), synthesis_schema(coarse_ids, item_ids, expand=bool(shelf)))
    inputs_sha = {**source_inputs_sha(a), "coarses": _env.sha256_file(a.coarses),
                  **({"drafts": _env.sha256_file(a.drafts)} if a.drafts else {})}
    manifest = {"audience": audience, "coarses": a.coarses, "kb_rows": a.kb_rows, "drafts": a.drafts, "items": len(items),
                "inputs_sha": inputs_sha, "prompts": {}}
    if shelf:
        manifest["mode"] = "expand"
        manifest["shelf"] = shelf
        manifest["canon"] = a.canon
    elif a.canon:
        _excluded_ids, why = _ci.load_exclude(a.exclude)
        manifest["canon"] = a.canon
        manifest["excluded"] = sorted(_excluded_ids)
        manifest["excluded_why"] = why
    for key, definition in ANGLES:
        text = build_angle_prompt(key, definition, audience, coarses, items, schema, shelf=shelf)
        p = os.path.join(a.out_dir, f"angle-{key}.prompt.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        manifest["prompts"][key] = {"path": p, "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text)}
    _env.write_json(os.path.join(a.out_dir, "manifest.json"), manifest)
    print(f"[structure_propose] prepare ok items={len(items)} prompts={len(ANGLES)} → {a.out_dir}")
    return 0


def cmd_validate(a) -> int:
    check_source_args(a)
    shelf = getattr(a, "shelf", None)
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts, a.canon, a.exclude, shelf)
    p = load_proposal_file(a.proposal)
    schema_path = os.path.join(a.out_dir, "schema-synthesis.json" if a.synthesis else "schema-proposal.json")
    errs = []
    try:
        _env.validate(p, _aa._load_json(schema_path))
    except Exception as exc:  # noqa: BLE001
        errs.append(f"schema：{exc}")
    errs += validate_proposal(p, audience, {c["id"] for c in coarses}, {it["id"] for it in items},
                               {c["id"]: c["title"] for c in coarses}, shelf=shelf)
    if errs:
        print("[structure_propose] 提議不合規：\n- " + "\n- ".join(errs), file=sys.stderr)
        return 2
    print(f"[structure_propose] validate ok angle={p.get('angle')} fines={len(p['fines'])} id_map={len(p['id_map'])}")
    return 0


def cmd_synth_prompt(a) -> int:
    check_source_args(a)
    shelf = getattr(a, "shelf", None)
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts, a.canon, a.exclude, shelf)
    proposals = [load_proposal_file(x) for x in a.proposals]
    if len(proposals) != 3:
        print("[structure_propose] 合成需要恰好 3 份提議", file=sys.stderr)
        return 2
    schema = synthesis_schema([c["id"] for c in coarses], [it["id"] for it in items], expand=bool(shelf))
    text = build_synthesis_prompt(audience, coarses, items, proposals, schema, shelf=shelf)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"[structure_propose] synth-prompt ok chars={len(text)} sha={hashlib.sha256(text.encode()).hexdigest()[:12]}")
    return 0


def cmd_package(a) -> int:
    check_source_args(a)
    shelf = getattr(a, "shelf", None)
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts, a.canon, a.exclude, shelf)
    coarse_ids, item_ids = {c["id"] for c in coarses}, {it["id"] for it in items}
    titles = {c["id"]: c["title"] for c in coarses}
    proposals = [load_proposal_file(x) for x in a.proposals]
    synthesis = load_proposal_file(a.synthesis)
    errs = []
    for i, p in enumerate(proposals):
        errs += [f"提議 {i}：{e}" for e in validate_proposal(p, audience, coarse_ids, item_ids, titles, shelf=shelf)]
    errs += [f"合成：{e}" for e in validate_proposal(synthesis, audience, coarse_ids, item_ids, titles, shelf=shelf)]
    if not isinstance(synthesis.get("rejected_alternatives"), list):
        errs.append("合成缺 rejected_alternatives")
    extra = synthesis_extra_fines(synthesis, proposals)
    if extra:
        errs.append(f"合成引入三份提議都沒有的細目：{extra}")
    if errs:
        print("[structure_propose] package 拒收：\n- " + "\n- ".join(errs), file=sys.stderr)
        return 2
    journal = {"step": "structure", "run_id": a.run_id, "agents": [{} for _ in range(4)],
               "wall_s": 0.0, "note": "子代理（Agent 工具）執行"}
    os.makedirs(os.path.dirname(os.path.abspath(a.journal)) or ".", exist_ok=True)
    _env.write_json(a.journal, journal)
    inputs_sha = {**source_inputs_sha(a), "coarses": _env.sha256_file(a.coarses)}
    if a.drafts:
        inputs_sha["drafts"] = _env.sha256_file(a.drafts)
    env = _env.make_envelope(step="structure", skill_version=a.skill_version, inputs_sha=inputs_sha, deterministic=False,
                             payload={"proposals": proposals, "synthesis": synthesis}, raw_outputs_path=a.raw_dir,
                             cost={"agents": 4, "wall_s": 0.0})
    _env.validate(env, _aa._load_json(os.path.join(_HERE, "..", "schemas", "structure-proposal.json")))
    _env.write_json(a.out, env)
    print(f"[structure_propose] package ok fines={len(synthesis['fines'])} rejected_alternatives={len(synthesis['rejected_alternatives'])} → {a.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--kb-rows", default=None, help="與 --canon 二擇一")
        sp.add_argument("--canon", default=None,
                         help="既有正本 Markdown；與 --kb-rows 二擇一（重切模式，任務 9.3⑤）")
        sp.add_argument("--exclude", default=None,
                         help="重切模式排除清單 JSON（{'excluded':[fine.id…],'why':'…'}）；⛔ 只在給 --canon 時有效")
        sp.add_argument("--drafts", default=None)
        sp.add_argument("--coarses", required=True, help="schemas/coarses-jgb.json（9.6 S4 起唯一來源）")
        sp.add_argument("--shelf", default=None,
                         help="擴充模式（brief-9.7）：單一粗目碼（A-I）；給了則 --canon 與 --kb-rows 須同時給")

    s = sub.add_parser("prepare"); common(s); s.add_argument("--out-dir", required=True)
    s = sub.add_parser("validate"); common(s); s.add_argument("--proposal", required=True); s.add_argument("--out-dir", required=True)
    s.add_argument("--synthesis", action="store_true", help="驗合成（含 rejected_alternatives）")
    s = sub.add_parser("synth-prompt"); common(s); s.add_argument("--proposals", nargs=3, required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("package"); common(s); s.add_argument("--proposals", nargs=3, required=True); s.add_argument("--synthesis", required=True)
    s.add_argument("--raw-dir", required=True); s.add_argument("--journal", required=True); s.add_argument("--run-id", required=True)
    s.add_argument("--out", required=True); s.add_argument("--skill-version", default="0.1.0")
    a = p.parse_args()
    return {"prepare": cmd_prepare, "validate": cmd_validate, "synth-prompt": cmd_synth_prompt, "package": cmd_package}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
