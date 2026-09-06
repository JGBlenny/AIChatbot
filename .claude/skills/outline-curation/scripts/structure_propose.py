#!/usr/bin/env python3
"""步 2 structure：結構提議（knowledge-outline-and-intent-architecture 任務 2.3）。

形態（業主 2026-09-06 裁）：**⛔ 本步不打模型 API**——3 個角度提議＋1 個合成由主 session 以 Claude Code 子代理（Agent 工具）執行；
本腳本只負責決定性的部分：
  prepare       輸入項目（kb 列＋草稿，白名單投影 id/title/content）＋固定粗目 → 3 份角度 prompt（逐位元穩定）＋schema＋items.json
  validate      子代理回傳的提議 JSON → schema＋事後規則（id_map 覆蓋每一輸入項目、細目 id 合規、coarse ∈ 粗目表）；不合 exit 2
  synth-prompt  三份（已 validate 的）提議 → 合成 prompt
  package       三份提議＋合成 → StepEnvelope（`schemas/structure-proposal.json`，deterministic=false）＋journal；合成不得引入三份都沒有的細目
子代理互不可見：三個角度各自只拿自己的 prompt；合成只拿三份 JSON。原始輸出留 raw/（gitignored）。
提示詞只寫定義不寫例子（業主紀律）。粗目由 `schemas/coarses-<audience>.json` 固定，提議只決定細目與歸屬。
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

ANGLES: tuple[tuple[str, str], ...] = (
    ("user_question_path", "使用者提問路徑：以使用者會怎麼問、一個問題應落在哪一個細目為切分依據；同一個可獨立回答的問題只對應一個細目。"),
    ("content_boundary", "內容邊界：以內容能否獨立成立、彼此不重疊為切分依據；兩段內容若互相依賴才完整，屬同一細目；若各自完整且主題不同，屬不同細目。"),
    ("audience_level", "受眾層級：以受眾在該主題需要的層級（能力／操作／權益）為切分依據；同一受眾同一主題只保留一個層級的細目，其他層級以另見交叉引用。"),
)
OPS = ("keep", "split", "merge", "move", "new")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def proposal_schema(coarse_ids: list, item_ids: list) -> dict:
    return {
        "type": "object",
        "properties": {
            "angle": {"type": "string"},
            "coarses": {"type": "array", "items": {
                "type": "object",
                "properties": {"id": {"type": "string", "enum": list(coarse_ids)}, "title": {"type": "string"}},
                "required": ["id", "title"], "additionalProperties": False}},
            "fines": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "coarse_id": {"type": "string", "enum": list(coarse_ids)},
                    "title": {"type": "string"},
                    "slug": {"type": "string"},
                    "merge_of": {"type": "array", "items": {"type": "string", "enum": list(item_ids)}},
                    "split_from": {"type": "array", "items": {"type": "string", "enum": list(item_ids)}},
                    "moved_from": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
                "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason"],
                "additionalProperties": False}},
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


def synthesis_schema(coarse_ids: list, item_ids: list) -> dict:
    s = proposal_schema(coarse_ids, item_ids)
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


def output_spec_block(audience: str) -> str:
    return "\n".join([
        "## 輸出定義",
        f"fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `{audience}/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；"
        "`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；"
        "`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。",
        "id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old 為 null，表示無來源的新細目（首跑不應出現）。",
        "coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。",
        "同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。",
        "回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。",
    ]) + "\n"


def build_angle_prompt(angle_key: str, angle_def: str, audience: str, coarses: list, items: list, schema: dict) -> str:
    return "\n".join([
        "你是知識大綱的結構提議者。任務：把輸入項目切成細目並歸入固定粗目。",
        f"本次切分依據（角度 {angle_key}）：{angle_def}",
        "只依此角度切分；不評分、不排序、不判斷內容真偽；⛔ 不讀取任何檔案或工具，只依本訊息內容作答。",
        "",
        coarses_block(audience, coarses),
        output_spec_block(audience),
        "## schema",
        json.dumps(schema, ensure_ascii=False),
        "",
        items_block(items),
        f"請輸出角度 {angle_key} 的結構提議（angle 欄填 {angle_key}）。",
    ])


def build_synthesis_prompt(audience: str, coarses: list, items: list, proposals: list, schema: dict) -> str:
    return "\n".join([
        "你是知識大綱結構的合成者。輸入＝同一批項目在三個角度下各自的結構提議。任務：合成一份最終提議。",
        "合成規則：三份提議一致處直接採用；分歧處擇一並把未採用的寫進 rejected_alternatives（alternative 一句描述、reason 一句理由）。",
        "⛔ 不得引入三份提議都沒有的細目 id；⛔ 不得改粗目；⛔ 不讀取任何檔案或工具。",
        "",
        coarses_block(audience, coarses),
        output_spec_block(audience),
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

def validate_proposal(p: dict, audience: str, coarse_ids: set, item_ids: set, coarse_titles: dict | None = None) -> list:
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
        for k in ("merge_of", "split_from"):
            for old in f.get(k, []) or []:
                if old not in item_ids:
                    errs.append(f"細目 {fid} 的 {k} 含未知項目 {old!r}")
        if not (f.get("merge_of") or f.get("split_from")):
            errs.append(f"細目 {fid} 沒有來源項目（merge_of／split_from 皆空）")
    mapped = {r.get("old") for r in p.get("id_map", []) if r.get("old") is not None}
    for r in p.get("id_map", []):
        if r.get("op") not in OPS:
            errs.append(f"id_map op 不合法：{r.get('op')!r}")
        if r.get("new") not in fine_ids:
            errs.append(f"id_map new 指向不存在的細目：{r.get('new')!r}")
        if r.get("op") == "new" and r.get("old") is not None:
            errs.append("id_map op=new 的 old 須為 null")
        if r.get("op") != "new" and r.get("old") is None:
            errs.append(f"id_map op={r.get('op')} 的 old 不得為 null")
        if r.get("old") is not None and r.get("old") not in item_ids:
            errs.append(f"id_map old 未知項目 {r.get('old')!r}")
    missing = sorted(item_ids - mapped)
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

def load_items(kb_rows_path: str, drafts_path: str | None) -> list:
    kb_doc = _aa._load_json(kb_rows_path)
    kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc
    items = [_aa.candidate_from_kb_row(r) for r in sorted(kb_rows, key=lambda r: r["kb_id"])]
    if drafts_path:
        drafts_doc = _aa._load_json(drafts_path)
        drafts = drafts_doc["knowledge"] if isinstance(drafts_doc, dict) else drafts_doc
        items += [_aa.candidate_from_draft(d, i + 1) for i, d in enumerate(drafts)]
    return items


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
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts)
    coarse_ids = [c["id"] for c in coarses]
    item_ids = [it["id"] for it in items]
    schema = proposal_schema(coarse_ids, item_ids)
    os.makedirs(a.out_dir, exist_ok=True)
    _env.write_json(os.path.join(a.out_dir, "items.json"), items)
    _env.write_json(os.path.join(a.out_dir, "schema-proposal.json"), schema)
    _env.write_json(os.path.join(a.out_dir, "schema-synthesis.json"), synthesis_schema(coarse_ids, item_ids))
    manifest = {"audience": audience, "coarses": a.coarses, "kb_rows": a.kb_rows, "drafts": a.drafts, "items": len(items),
                "inputs_sha": {"kb": _env.sha256_file(a.kb_rows), "coarses": _env.sha256_file(a.coarses),
                               **({"drafts": _env.sha256_file(a.drafts)} if a.drafts else {})},
                "prompts": {}}
    for key, definition in ANGLES:
        text = build_angle_prompt(key, definition, audience, coarses, items, schema)
        p = os.path.join(a.out_dir, f"angle-{key}.prompt.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        manifest["prompts"][key] = {"path": p, "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text)}
    _env.write_json(os.path.join(a.out_dir, "manifest.json"), manifest)
    print(f"[structure_propose] prepare ok items={len(items)} prompts={len(ANGLES)} → {a.out_dir}")
    return 0


def cmd_validate(a) -> int:
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts)
    p = load_proposal_file(a.proposal)
    schema_path = os.path.join(a.out_dir, "schema-synthesis.json" if a.synthesis else "schema-proposal.json")
    errs = []
    try:
        _env.validate(p, _aa._load_json(schema_path))
    except Exception as exc:  # noqa: BLE001
        errs.append(f"schema：{exc}")
    errs += validate_proposal(p, audience, {c["id"] for c in coarses}, {it["id"] for it in items}, {c["id"]: c["title"] for c in coarses})
    if errs:
        print("[structure_propose] 提議不合規：\n- " + "\n- ".join(errs), file=sys.stderr)
        return 2
    print(f"[structure_propose] validate ok angle={p.get('angle')} fines={len(p['fines'])} id_map={len(p['id_map'])}")
    return 0


def cmd_synth_prompt(a) -> int:
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts)
    proposals = [load_proposal_file(x) for x in a.proposals]
    if len(proposals) != 3:
        print("[structure_propose] 合成需要恰好 3 份提議", file=sys.stderr)
        return 2
    schema = synthesis_schema([c["id"] for c in coarses], [it["id"] for it in items])
    text = build_synthesis_prompt(audience, coarses, items, proposals, schema)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"[structure_propose] synth-prompt ok chars={len(text)} sha={hashlib.sha256(text.encode()).hexdigest()[:12]}")
    return 0


def cmd_package(a) -> int:
    audience, coarses = _load_coarses(a.coarses)
    items = load_items(a.kb_rows, a.drafts)
    coarse_ids, item_ids = {c["id"] for c in coarses}, {it["id"] for it in items}
    titles = {c["id"]: c["title"] for c in coarses}
    proposals = [load_proposal_file(x) for x in a.proposals]
    synthesis = load_proposal_file(a.synthesis)
    errs = []
    for i, p in enumerate(proposals):
        errs += [f"提議 {i}：{e}" for e in validate_proposal(p, audience, coarse_ids, item_ids, titles)]
    errs += [f"合成：{e}" for e in validate_proposal(synthesis, audience, coarse_ids, item_ids, titles)]
    if not isinstance(synthesis.get("rejected_alternatives"), list):
        errs.append("合成缺 rejected_alternatives")
    extra = synthesis_extra_fines(synthesis, proposals)
    if extra:
        errs.append(f"合成引入三份提議都沒有的細目：{extra}")
    if errs:
        print("[structure_propose] package 拒收：\n- " + "\n- ".join(errs), file=sys.stderr)
        return 2
    journal = {"step": "structure", "run_id": a.run_id, "agents": [{"prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0} for _ in range(4)],
               "wall_s": 0.0, "note": "子代理（Agent 工具）執行；token／usd 由 harness 計、此處不估"}
    os.makedirs(os.path.dirname(os.path.abspath(a.journal)) or ".", exist_ok=True)
    _env.write_json(a.journal, journal)
    inputs_sha = {"kb": _env.sha256_file(a.kb_rows), "coarses": _env.sha256_file(a.coarses)}
    if a.drafts:
        inputs_sha["drafts"] = _env.sha256_file(a.drafts)
    env = _env.make_envelope(step="structure", skill_version=a.skill_version, inputs_sha=inputs_sha, deterministic=False,
                             payload={"proposals": proposals, "synthesis": synthesis}, raw_outputs_path=a.raw_dir,
                             cost={"agents": 4, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0})
    _env.validate(env, _aa._load_json(os.path.join(_HERE, "..", "schemas", "structure-proposal.json")))
    _env.write_json(a.out, env)
    print(f"[structure_propose] package ok fines={len(synthesis['fines'])} rejected_alternatives={len(synthesis['rejected_alternatives'])} → {a.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--kb-rows", required=True)
        sp.add_argument("--drafts", default=None)
        sp.add_argument("--coarses", required=True, help="schemas/coarses-<audience>.json")

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
