#!/usr/bin/env python3
"""步 4 answerability 判者 args 組裝（knowledge-outline-and-intent-architecture 任務 1.4｜design 元件 2）。

讀 55 格缺口地圖（`map-v2.json`）＋21 列 prospect kb rows＋18 筆草稿＋rubric →
Workflow `outline-curation.js` `step:'answerability'` 用的 `args` JSON：候選＝程式列舉的
臨時細目集合（kb 依 id 升冪、draft 依原序，⛔ 不經排序不篩選）、每格 judgePrompt（rubric 全文＋
代表問句＋全部候選）、`fineIdEnum`（供 JS 端組 schema enum）。

⛔ 不呼叫 LLM、不跑 Workflow（乾跑由主 session 做）。⛔ 不讀網路、不讀 `.env`。

白名單投影：任何被驗系統的判定／分數欄位（`score`／`similarity`／`top3`／`coverage`／
`cause_state`／`entry_state`／`g0`／`rubric`／`per_question` 等）一律不得進入 judgePrompt 文字
（裁定 10）。已知系統欄位（map-v2 格本身攜帶、kb 列／草稿本身攜帶）允許靜默丟棄；
未列在 `KNOWN_SYSTEM_FIELDS` 的額外欄位一律 raise（正對照見同名測試）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import sha256_file, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"


class ForbiddenFieldError(Exception):
    """cell 或候選帶有未知（非白名單、非已知系統）欄位——⛔ 不得靜默丟棄，必須 raise。"""


# 已知系統欄位：投影時允許靜默丟棄，⛔ 不 raise。未列在此的額外欄位一律 raise。
KNOWN_SYSTEM_FIELDS = {
    # map-v2.json cells[] 除 id/questions/policy/policy_ref 外的既有欄位
    "cell": frozenset({
        "module", "topic", "keywords", "sources", "help_center", "intent",
        "note", "rubric", "g0", "per_question", "cause_state", "entry_state", "coverage",
    }),
    # prospect-kb-rows.json rows[] 除 kb_id/question_summary/answer 外的既有欄位
    "kb_row": frozenset({"business_types", "categories", "outline_approved_by", "target_user"}),
    # batch2 knowledge[] 除 question/answer 外的既有欄位
    "draft": frozenset({"cell", "facet", "target_user", "business_types", "categories", "keywords", "instance_applicability", "g0"}),
}

_CELL_ALLOWED = frozenset({"id", "questions", "policy", "policy_ref"})
_KB_ROW_ALLOWED = frozenset({"kb_id", "question_summary", "answer"})
_DRAFT_ALLOWED = frozenset({"question", "answer"})
_CANDIDATE_ALLOWED = frozenset({"id", "title", "content"})


def _check_no_forbidden(raw: dict, allowed: frozenset, known_extra: frozenset, kind: str) -> None:
    extra = set(raw.keys()) - allowed - known_extra
    if extra:
        raise ForbiddenFieldError(f"{kind} 含未知欄位 {sorted(extra)}——不得進入判者 prompt")


def candidate_from_kb_row(row: dict) -> dict:
    """21 列 prospect kb rows 其中一列 → 候選 {id,title,content}。id=`tmp:kb:<kb_id>`。"""
    _check_no_forbidden(row, _KB_ROW_ALLOWED, KNOWN_SYSTEM_FIELDS["kb_row"], "kb_row")
    return {"id": f"tmp:kb:{row['kb_id']}", "title": row["question_summary"], "content": row["answer"]}


def candidate_from_draft(draft: dict, n: int) -> dict:
    """batch2 草稿其中一筆 → 候選 {id,title,content}。id=`tmp:draft:<n>`（n＝原序，1-indexed）。"""
    _check_no_forbidden(draft, _DRAFT_ALLOWED, KNOWN_SYSTEM_FIELDS["draft"], "draft")
    return {"id": f"tmp:draft:{n}", "title": draft["question"], "content": draft["answer"]}


def project_cell(cell: dict) -> dict:
    """白名單投影：cell 只取 id/questions[0]/policy/policy_ref。其餘已知系統欄位丟棄，未知欄位 raise。"""
    _check_no_forbidden(cell, _CELL_ALLOWED, KNOWN_SYSTEM_FIELDS["cell"], "cell")
    out = {"cellId": cell["id"], "question": cell["questions"][0], "policy": cell.get("policy")}
    if cell.get("policy_ref") is not None:
        out["policyRef"] = cell["policy_ref"]
    return out


def _check_candidate_shape(c: dict) -> None:
    extra = set(c.keys()) - _CANDIDATE_ALLOWED
    if extra:
        raise ForbiddenFieldError(f"candidate 含未知欄位 {sorted(extra)}——不得進入判者 prompt")
    missing = _CANDIDATE_ALLOWED - set(c.keys())
    if missing:
        raise ForbiddenFieldError(f"candidate 缺必要欄位 {sorted(missing)}")


def build_prompt_parts(cell: dict, candidates: list, rubric_text: str) -> dict:
    """把判者 prompt 拆成四段（共用頭／每格待判塊／共用候選塊／每格輸出說明），供 Workflow 端純字串拼接。

    拼接等式（測試守著）：promptHead + cellBlock + candidatesBlock + cellTail == build_judge_prompt(...)。
    理由：55 格時 rubric 與 39 筆候選在每格重複，args 會膨脹到 500 KB；Workflow args 只能經工具參數傳，
    拆段後整份 args 約 20 KB。白名單投影仍在本函式（cellBlock 由 Python 產），JS 只做拼接、⛔ 不碰欄位。
    """
    projected = project_cell(cell)
    for c in candidates:
        _check_candidate_shape(c)

    head = rubric_text.strip() + "\n\n"

    cell_lines = ["## 待判格",
                  f"格 id：{projected['cellId']}",
                  f"代表問句：{projected['question']}",
                  f"policy：{projected['policy']}"]
    if "policyRef" in projected:
        cell_lines.append(f"policy_ref：{projected['policyRef']}")
    cell_block = "\n".join(cell_lines) + "\n\n"

    cand_lines = [f"## 候選（{len(candidates)} 筆，原序列舉，未排序未篩選）"]
    for c in candidates:
        cand_lines.append(f"### {c['id']}")
        cand_lines.append(f"標題：{c['title']}")
        cand_lines.append(f"內容：{c['content']}")
        cand_lines.append("")
    candidates_block = "\n".join(cand_lines) + "\n"

    tail_lines = ["## 輸出欄位說明",
                  f"cell_id：本格 id（{projected['cellId']}）。",
                  "label：answerable｜partial｜no_source｜deliberate_no（依上方 rubric 判定）。",
                  "fine_id：正解候選 id（answerable／partial 時必填、取候選 id；其餘為 null）。",
                  "evidence_unit：候選內容第幾句可答該問句或子問題（no_source／deliberate_no 為 null）。",
                  "confidence：high｜medium｜low。"]
    cell_tail = "\n".join(tail_lines)
    return {"promptHead": head, "cellBlock": cell_block, "candidatesBlock": candidates_block, "cellTail": cell_tail}


def build_judge_prompt(cell: dict, candidates: list, rubric_text: str) -> str:
    """組裝單一格的判者 prompt：rubric 全文＋代表問句＋全部候選（id/title/content，原序，⛔ 不排序不篩選）。

    白名單投影：cell 只取 id/questions[0]/policy/policy_ref；候選只取 id/title/content。
    任何其他鍵（含 score／similarity／top3／coverage／cause_state／entry_state／g0／rubric／
    per_question，已知系統欄位除外）出現 ⇒ raise ForbiddenFieldError。決定性：同輸入兩次逐位元相同。
    實作＝四段拼接（見 build_prompt_parts）。
    """
    parts = build_prompt_parts(cell, candidates, rubric_text)
    return parts["promptHead"] + parts["cellBlock"] + parts["candidatesBlock"] + parts["cellTail"]


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_args(cells_path: str, kb_rows_path: str, drafts_path: str, rubric_path: str,
                frozen_at: str, cell_ids_filter: set | None = None, slim: bool = False) -> dict:
    cells_doc = _load_json(cells_path)
    all_cells = cells_doc["cells"] if isinstance(cells_doc, dict) else cells_doc

    kb_doc = _load_json(kb_rows_path)
    kb_rows = kb_doc["rows"] if isinstance(kb_doc, dict) else kb_doc

    drafts_doc = _load_json(drafts_path)
    drafts = drafts_doc["knowledge"] if isinstance(drafts_doc, dict) else drafts_doc

    with open(rubric_path, encoding="utf-8") as f:
        rubric_text = f.read()

    # 決定性順序：kb 依 kb_id 升冪、draft 依原序（原檔陣列順序）
    kb_sorted = sorted(kb_rows, key=lambda r: r["kb_id"])
    kb_candidates = [candidate_from_kb_row(r) for r in kb_sorted]
    draft_candidates = [candidate_from_draft(d, i + 1) for i, d in enumerate(drafts)]
    candidates = kb_candidates + draft_candidates
    fine_id_enum = [c["id"] for c in candidates]

    if cell_ids_filter:
        selected_cells = [c for c in all_cells if c["id"] in cell_ids_filter]
    else:
        selected_cells = all_cells

    cells_out = []
    prompt_head = None
    candidates_block = None
    for cell in selected_cells:
        parts = build_prompt_parts(cell, candidates, rubric_text)
        prompt_head = parts["promptHead"]
        candidates_block = parts["candidatesBlock"]
        entry = {
            "cellId": cell["id"],
            "question": cell["questions"][0],
            "policy": cell.get("policy"),
            "cellBlock": parts["cellBlock"],
            "cellTail": parts["cellTail"],
        }
        if not slim:
            entry["judgePrompt"] = build_judge_prompt(cell, candidates, rubric_text)
        if cell.get("policy_ref") is not None:
            entry["policyRef"] = cell["policy_ref"]
        cells_out.append(entry)

    inputs_sha = {
        "cells": sha256_file(cells_path),
        "kbRows": sha256_file(kb_rows_path),
        "drafts": sha256_file(drafts_path),
        "rubric": sha256_file(rubric_path),
    }

    return {
        "step": "answerability",
        "frozenAt": frozen_at,
        "rubricSha": inputs_sha["rubric"],
        "inputsSha": inputs_sha,
        "promptHead": prompt_head,
        "candidatesBlock": candidates_block,
        "fineIdEnum": fine_id_enum,
        "cells": cells_out,
        **({} if slim else {"candidates": candidates}),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="步 4 answerability 判者 args 組裝 → Workflow args JSON")
    p.add_argument("--cells", required=True, help="缺口地圖 map-v2.json")
    p.add_argument("--kb-rows", required=True, help="prospect-kb-rows-*.json")
    p.add_argument("--drafts", required=True, help="presales-gapmap-batch2-*.json")
    p.add_argument("--rubric", required=True, help="schemas/answerability-rubric.md")
    p.add_argument("--frozen-at", required=True, help="ISO 時間戳，⛔ 不用 datetime.now()")
    p.add_argument("--out", required=True)
    p.add_argument("--cell-ids", required=False, default=None, help="逗號分隔的格 id 子集，用於乾跑（如 C01,C02）")
    p.add_argument("--slim", action="store_true", help="省略 judgePrompt 與 candidates（Workflow 端以四段拼接；55 格 args 才傳得進工具參數）")
    args = p.parse_args()

    cell_ids_filter = set(x.strip() for x in args.cell_ids.split(",")) if args.cell_ids else None
    payload = build_args(args.cells, args.kb_rows, args.drafts, args.rubric, args.frozen_at, cell_ids_filter, slim=args.slim)
    write_json(args.out, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
