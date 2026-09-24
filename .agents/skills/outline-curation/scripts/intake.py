#!/usr/bin/env python3
"""步 1 intake（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1；9.3⑤ 補「從既有正本重切」來源）。

讀 kb 列／草稿／缺口地圖／既有正本 → `intake.json`。純決定性：不讀 DB、不讀網路、
不讀 `.env`；kb 列由呼叫端先匯出成 JSON 檔傳入。

輸出：inputs_sha（各輸入 sha256）、kb 列摘要（id／question_summary 前 40 字）、
drafts 摘要、gapmap 格數、object_under_test 骨架（materials／frozen_at／approved_by=""）。

重切模式（任務 9.3⑤）：`--canon` 與 `--kb-json` 二擇一，同給／都不給 ⇒ exit 2。給 `--canon` 時
不讀 `--kb-json`，改以既有正本的細目當「kb 列」摘要（id＝`fine.id`、question_summary＝標題前 40 字），
`--exclude <json>`（`{"excluded":[fine.id…],"why":"…"}`）排除的細目不進 kb_rows；
`inputs_sha["kb"]` 在此模式下＝該正本檔 sha256（與 `inputs_sha["canon"]` 相同值），
`inputs_sha["exclude"]` 有給 `--exclude` 才出現。"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, load_schema, make_envelope, sha256_file, sha256_path, validate, write_json  # noqa: E402
import canon_items as canon_items_mod  # noqa: E402
from canon_items import canon_items  # noqa: E402

SKILL_VERSION = "0.1.0"
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "intake.json")


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _truncate(s: str, n: int = 40) -> str:
    return s[:n]


def _materials_relative_to_repo_root(paths: list[str | None]) -> list[str]:
    """材料清單一律相對於 repo 根（F11：⛔ 不相對 cwd——`object_under_test.materials` 若跟著呼叫端 cwd
    漂移，同一份材料在不同 cwd 下跑會被判定成不同物）。找不到 repo 根時退回舊行為（相對 cwd）。"""
    try:
        repo_root = find_repo_root()
    except RuntimeError:
        repo_root = None
    out = []
    for p in paths:
        if not p:
            continue
        if repo_root:
            out.append(os.path.relpath(os.path.abspath(p), repo_root))
        else:
            out.append(os.path.relpath(p) if os.path.isabs(p) else p)
    return out


def build_payload(kb_path: str | None, drafts_path: str | None, gapmap_path: str | None,
                   canon_path: str | None, frozen_at: str, exclude_path: str | None = None,
                   shelf: str | None = None) -> tuple[dict, dict]:
    inputs_sha: dict = {}
    if canon_path and kb_path:
        # 擴充模式（brief-9.7）：既有一架＋新 kb 列＋草稿；`shelf` 由呼叫端驗過（九架碼之一）。
        # kb 列＝該架既有細目（id 形狀 `<fine.id>`）＋外部 kb 列（id 形狀 `<kb_id>`），兩者都只記
        # id＋摘要（intake 不放內容；內容在步 2／apply 由各自來源讀）。
        shelf_doc, shelf_fines = canon_items_mod.shelf_items(canon_path, shelf)
        kb_rows = [{"id": it["id"][len(canon_items_mod.TMP_CANON_PREFIX):], "question_summary": _truncate(it["title"])}
                   for it in shelf_fines]
        kb_rows_raw = _load_json(kb_path)
        kb_rows_raw = kb_rows_raw["rows"] if isinstance(kb_rows_raw, dict) else kb_rows_raw
        if not isinstance(kb_rows_raw, list):
            raise ValueError("--kb-json 內容必須是列表（或 {'rows': [...]}）")
        kb_rows += [
            {"id": str(r.get("kb_id", r.get("id", ""))), "question_summary": _truncate(str(r.get("question_summary", "")))}
            for r in kb_rows_raw
        ]
        inputs_sha["kb"] = sha256_file(kb_path)
        inputs_sha["canon"] = sha256_path(canon_path)
    elif canon_path:
        # 重切模式：既有正本細目當 kb 列來源（9.3⑤）。
        _audience, items, _excluded, _why = canon_items(canon_path, exclude_path)
        kb_rows = [
            {"id": it["id"][len("tmp:kb:"):], "question_summary": _truncate(it["title"])}
            for it in items
        ]
        inputs_sha["kb"] = sha256_path(canon_path)  # 9.6 S4：--canon 可能是目錄（圖書館正本）
        inputs_sha["canon"] = inputs_sha["kb"]
        if exclude_path:
            inputs_sha["exclude"] = sha256_file(exclude_path)
    else:
        kb_rows_raw = _load_json(kb_path)
        if not isinstance(kb_rows_raw, list):
            raise ValueError("--kb-json 內容必須是列表")
        kb_rows = [
            {"id": str(r.get("id", "")), "question_summary": _truncate(str(r.get("question_summary", "")))}
            for r in kb_rows_raw
        ]
        inputs_sha["kb"] = sha256_file(kb_path)
        inputs_sha["canon"] = None

    drafts_raw = _load_json(drafts_path) if drafts_path else []
    if not isinstance(drafts_raw, list):
        raise ValueError("--drafts 內容必須是列表")
    drafts = [
        {"id": str(d.get("id", "")), "summary": _truncate(str(d.get("summary", d.get("question_summary", ""))))}
        for d in drafts_raw
    ]

    gapmap_raw = _load_json(gapmap_path) if gapmap_path else []
    if isinstance(gapmap_raw, list):
        gapmap_cells = len(gapmap_raw)
    elif isinstance(gapmap_raw, dict):
        cells = gapmap_raw.get("cells")
        gapmap_cells = len(cells) if isinstance(cells, list) else len(gapmap_raw)
    else:
        gapmap_cells = 0

    materials = _materials_relative_to_repo_root([kb_path, drafts_path, gapmap_path, canon_path, exclude_path])

    if drafts_path:
        inputs_sha["drafts"] = sha256_file(drafts_path)
    if gapmap_path:
        inputs_sha["gapmap"] = sha256_file(gapmap_path)

    payload = {
        "frozen_at": frozen_at,
        "kb_rows": kb_rows,
        "drafts": drafts,
        "gapmap_cells": gapmap_cells,
        "object_under_test": {
            "materials": materials,
            "frozen_at": frozen_at,
            "approved_by": "",
        },
    }
    return payload, inputs_sha


def main() -> int:
    p = argparse.ArgumentParser(description="步 1 intake：讀 kb 列／草稿／缺口地圖／既有正本 → intake.json")
    p.add_argument("--kb-json", required=False, default=None, help="kb 列 JSON 檔（呼叫端先匯出，⛔ 本腳本不讀 DB）；與 --canon 二擇一")
    p.add_argument("--drafts", required=False, default=None, help="草稿 JSON 檔")
    p.add_argument("--gapmap", required=False, default=None, help="缺口地圖 JSON 檔")
    p.add_argument("--canon", required=False, default=None,
                   help="既有正本 Markdown；與 --kb-json 二擇一。給了 ⇒ 重切模式：正本細目當 kb 列來源")
    p.add_argument("--exclude", required=False, default=None,
                   help="重切模式排除清單 JSON（{'excluded':[fine.id…],'why':'…'}），⛔ 只在給 --canon 時有效")
    p.add_argument("--out", required=True, help="輸出 intake.json 路徑")
    p.add_argument("--frozen-at", required=True, help="ISO 時間戳，⛔ 不用 datetime.now()")
    p.add_argument("--shelf", required=False, default=None,
                   help="擴充模式（brief-9.7）：只補這一架（九架碼之一）；須同時給 --canon（圖書館目錄）＋--kb-json，選填 --drafts")
    args = p.parse_args()

    if args.shelf:
        if args.shelf not in canon_items_mod.SHELF_CODES:
            print(f"[intake] --shelf 須為 {canon_items_mod.SHELF_CODES} 之一，得到 {args.shelf!r}", file=sys.stderr)
            return 2
        if not (args.canon and args.kb_json):
            print("[intake] 擴充模式（--shelf）須同時給 --canon 與 --kb-json", file=sys.stderr)
            return 2
        if args.exclude:
            print("[intake] 擴充模式（--shelf）不支援 --exclude", file=sys.stderr)
            return 2
    else:
        if bool(args.kb_json) == bool(args.canon):
            print("[intake] --kb-json 與 --canon 二擇一（不得同給、不得都不給）", file=sys.stderr)
            return 2
        if args.exclude and not args.canon:
            print("[intake] --exclude 只在給 --canon（重切模式）時有效", file=sys.stderr)
            return 2

    payload, inputs_sha = build_payload(args.kb_json, args.drafts, args.gapmap, args.canon, args.frozen_at, args.exclude,
                                        shelf=args.shelf)
    if args.shelf:
        payload["mode"] = "expand"
        payload["shelf"] = args.shelf
    envelope = make_envelope(
        step="intake",
        skill_version=SKILL_VERSION,
        inputs_sha=inputs_sha,
        deterministic=True,
        payload=payload,
    )
    validate(envelope, load_schema(_SCHEMA_PATH))
    write_json(args.out, envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
