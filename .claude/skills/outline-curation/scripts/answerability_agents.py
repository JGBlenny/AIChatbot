#!/usr/bin/env python3
"""步 4 可答性判者——Claude Code 子代理版（業主 2026-09-06 裁：skill 流程絕大部分用 Claude Code；模型 API 只在真實對話（產品）使用，⛔ 不留 API 判者備援）。

與 `structure_propose.py` 同一套外殼：本腳本只做決定性的部分，LLM 呼叫由主 session 派子代理。
  prepare   slim args（`answerability_args.py --slim`）→ 依 `--cells-per-agent`（預設 5）分組；每組 2 個 slot 的 prompt 檔（內容逐位元相同、
            只有檔名不同 ⇒ 判者互不可見、同尺）；`manifest.json` 記組別、格 id、prompt sha
  collect   讀子代理回傳 JSON（`<out-dir>/verdicts/<group>-s<slot>.json`，每檔＝該組各格 verdict 陣列）→ 事後驗證（label／fine_id enum／
            cell_id ∈ 該組）→ 找出 slot1／slot2 不一致的格 → 產第 3 slot 的 prompt（只含不一致格）；全部齊了就 Reconcile（與 JS／API 版逐條等價，
            門檻 AGREEMENT_THRESHOLD）→ 輸出與 Workflow Reconcile 同形的 result JSON（餵 finalize_answerability.py）
分組的取捨：同組的格共用一份 prompt（rubric＋候選 ≈7k token 只送一次），判者可見同組其他格的問句——這是為了讓子代理數從 110–165 降到 22–33
（8 GB 機器實測 ≥10 個並行子代理會整機重開）；格與格之間本來就不要求隔離，隔離的是同一格的判者之間。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_env = _load_sibling("_envelope")

AGREEMENT_THRESHOLD = 0.80  # 2026-09-06 業主裁（原 0.90）；與 outline-curation.js／merge_answerability_batches.py 同值
LABELS = ["answerable", "partial", "no_source", "deliberate_no"]


def validate_verdict(v, fine_id_enum: list):
    """事後驗證（子代理輸出沒有 schema 強制，這是唯一一道）：不合 ⇒ None（no silent caps：由 Reconcile 記 dropped）。"""
    if not isinstance(v, dict) or v.get("label") not in LABELS or not isinstance(v.get("cell_id"), str):
        return None
    if v.get("fine_id") is not None and v["fine_id"] not in fine_id_enum:
        return None
    if v.get("evidence_unit") is not None and not isinstance(v["evidence_unit"], int):
        return None
    if v.get("confidence") not in ("high", "medium", "low"):
        return None
    return {"cell_id": v["cell_id"], "label": v["label"], "fine_id": v.get("fine_id"), "evidence_unit": v.get("evidence_unit"),
            "confidence": v["confidence"], "provisional": True}


def reconcile(results: list, args: dict, log) -> dict:
    """與 outline-curation.js Reconcile 逐條等價（1.4 定義；門檻 AGREEMENT_THRESHOLD）。"""
    agree = 0
    agents_used = 0
    dropped = 0
    labels = []
    for r in results:
        if not r:
            dropped += 1
            continue
        c, v1, v2, v3 = r["c"], r["v1"], r["v2"], r["v3"]
        verdicts = r["verdicts"]
        agents_used += len(verdicts)
        if not v1 or not v2:
            dropped += 1
            log(f"{c['cellId']} skipped（判者結果缺失，no silent caps）")
            continue
        is_agree = v1["label"] == v2["label"]
        if is_agree:
            agree += 1
            final = v1["label"]
            unresolved = False
        elif v3 and v3["label"] in (v1["label"], v2["label"]):
            final = v3["label"]
            unresolved = False
        else:
            final = "no_source"
            unresolved = True
        winner = next((v for v in verdicts if v["label"] == final), v1)
        entry = {"cell_id": c["cellId"], "label": final, "fine_id": winner["fine_id"], "evidence_unit": winner["evidence_unit"],
                 "confidence": winner["confidence"], "provisional": True, "verdicts": verdicts}
        if unresolved:
            entry["unresolved"] = True
        labels.append(entry)
    if dropped:
        log(f"{dropped} 格因判者結果缺失被跳過（no silent caps）")
    total = len(labels)
    rate = agree / total if total else 0.0
    return {"step": "answerability", "frozenAt": args["frozenAt"], "rubricSha": args["rubricSha"], "inputsSha": args["inputsSha"],
            "total": total, "agree": agree, "agreementRate": rate, "needs_rubric_revision": rate < AGREEMENT_THRESHOLD,
            "agentsUsed": agents_used, "labels": labels, "droppedCells": dropped}


def group_cells(cells: list, per_agent: int) -> list:
    """決定性分組：依 args 內順序切塊；組 id＝G01…。"""
    if per_agent < 1:
        raise ValueError("--cells-per-agent 須 ≥1")
    groups = []
    for i in range(0, len(cells), per_agent):
        chunk = cells[i:i + per_agent]
        groups.append({"group": f"G{len(groups) + 1:02d}", "cell_ids": [c["cellId"] for c in chunk]})
    return groups


def build_group_prompt(args: dict, cells: list) -> str:
    """rubric（promptHead）＋各格待判塊＋候選塊＋輸出說明。每格的 cellBlock 原樣沿用（白名單投影在 Python 端）。"""
    parts = [args["promptHead"]]
    parts.append(f"## 本組待判格（{len(cells)} 格，各自獨立判定，⛔ 不因其他格的判定改變本格）\n\n")
    for c in cells:
        parts.append(c["cellBlock"])
    parts.append(args["candidatesBlock"])
    parts.append("\n".join([
        "## 輸出定義",
        "對本組每一格各輸出一個物件，組成 JSON 陣列（順序同待判格）；只輸出該陣列，不加說明文字、不加 Markdown 圍欄。",
        "cell_id：該格 id。",
        "label：answerable｜partial｜no_source｜deliberate_no（依上方 rubric 判定）。",
        "fine_id：正解候選 id（answerable／partial 時必填、取候選 id；其餘為 null）。",
        "evidence_unit：候選內容第幾句可答該問句或子問題（整數；no_source／deliberate_no 為 null）。",
        "confidence：high｜medium｜low。",
        "provisional：true。",
        "⛔ 不讀取任何檔案或工具，只依本訊息作答。",
    ]))
    return "".join(parts) if False else "\n".join(p.rstrip("\n") for p in parts) + "\n"


def cmd_prepare(a) -> int:
    args = _env_load(a.args)
    for k in ("promptHead", "candidatesBlock", "cells", "fineIdEnum"):
        if k not in args:
            print(f"[answerability_agents] args 缺 {k}：請用 answerability_args.py --slim 產出", file=sys.stderr)
            return 2
    cells = args["cells"]
    if a.cell_ids:
        keep = set(a.cell_ids.split(","))
        cells = [c for c in cells if c["cellId"] in keep]
    groups = group_cells(cells, a.cells_per_agent)
    by_id = {c["cellId"]: c for c in cells}
    os.makedirs(os.path.join(a.out_dir, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(a.out_dir, "verdicts"), exist_ok=True)
    manifest = {"step": "answerability", "frozenAt": args["frozenAt"], "rubricSha": args["rubricSha"], "inputsSha": args["inputsSha"],
                "fineIdEnum": args["fineIdEnum"], "cellsPerAgent": a.cells_per_agent, "groups": []}
    for g in groups:
        text = build_group_prompt(args, [by_id[cid] for cid in g["cell_ids"]])
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        paths = {}
        for slot in (1, 2):
            p = os.path.join(a.out_dir, "prompts", f"{g['group']}-s{slot}.prompt.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            paths[str(slot)] = p
        manifest["groups"].append({**g, "prompt_sha256": sha, "prompts": paths, "chars": len(text)})
    _env.write_json(os.path.join(a.out_dir, "manifest.json"), manifest)
    print(f"[answerability_agents] prepare ok cells={len(cells)} groups={len(groups)} × 2 slots → {a.out_dir}/prompts/")
    return 0


def _env_load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _strip_fences(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def load_verdicts_file(path: str, expected_cells: list, fine_id_enum: list) -> dict:
    """回 {cell_id: verdict|None}；壞的 verdict ⇒ None（no silent caps，由 Reconcile 記 dropped）。"""
    with open(path, encoding="utf-8") as fh:
        raw = _strip_fences(fh.read())
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError:
        return {c: None for c in expected_cells}
    if isinstance(arr, dict):
        arr = [arr]
    out = {c: None for c in expected_cells}
    for v in arr if isinstance(arr, list) else []:
        vv = validate_verdict(v, fine_id_enum)
        if vv and vv["cell_id"] in out and out[vv["cell_id"]] is None:
            out[vv["cell_id"]] = vv
    return out


def cmd_collect(a) -> int:
    m = _env_load(os.path.join(a.out_dir, "manifest.json"))
    enum = m["fineIdEnum"]
    vdir = os.path.join(a.out_dir, "verdicts")
    per_cell: dict = {}
    missing = []
    for g in m["groups"]:
        for slot in (1, 2):
            p = os.path.join(vdir, f"{g['group']}-s{slot}.json")
            if not os.path.exists(p):
                missing.append(os.path.basename(p))
                continue
            got = load_verdicts_file(p, g["cell_ids"], enum)
            for cid, v in got.items():
                per_cell.setdefault(cid, {})[slot] = v
    if missing:
        print(f"[answerability_agents] 尚缺 {len(missing)} 個判者檔：{missing[:6]}{'…' if len(missing) > 6 else ''}", file=sys.stderr)
        return 3

    # 第 3 判者：slot1／slot2 缺或 label 不同的格
    need_third = [cid for g in m["groups"] for cid in g["cell_ids"]
                  if not (per_cell[cid].get(1) and per_cell[cid].get(2) and per_cell[cid][1]["label"] == per_cell[cid][2]["label"])]
    third_path = os.path.join(vdir, "third.json")
    if need_third and not os.path.exists(third_path):
        args = _env_load(a.args)
        by_id = {c["cellId"]: c for c in args["cells"]}
        text = build_group_prompt(args, [by_id[c] for c in need_third])
        p = os.path.join(a.out_dir, "prompts", "third.prompt.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        _env.write_json(os.path.join(a.out_dir, "third-cells.json"), need_third)
        print(f"[answerability_agents] {len(need_third)} 格不一致 ⇒ 第 3 判者 prompt 已產：{p}（回傳存 {third_path}）")
        return 4
    third = load_verdicts_file(third_path, need_third, enum) if need_third else {}

    results = []
    for g in m["groups"]:
        for cid in g["cell_ids"]:
            v1, v2 = per_cell[cid].get(1), per_cell[cid].get(2)
            v3 = third.get(cid)
            verdicts = [v for v in (v1, v2, v3) if v]
            results.append({"c": {"cellId": cid}, "v1": v1, "v2": v2, "v3": v3, "verdicts": verdicts})
    out = reconcile(results, {"frozenAt": m["frozenAt"], "rubricSha": m["rubricSha"], "inputsSha": m["inputsSha"]}, print)
    out["usage"] = {"provider": "claude-code-subagent", "groups": len(m["groups"]), "cellsPerAgent": m["cellsPerAgent"],
                    "agents": len(m["groups"]) * 2 + (1 if need_third else 0), "note": "token 由 harness 計，此處不估"}
    out["usd"] = None
    _env.write_json(a.out, out)
    print(f"[answerability_agents] collect ok total={out['total']} agree={out['agree']} rate={out['agreementRate']:.3f} "
          f"agents={out['agentsUsed']} needs_rubric_revision={out['needs_rubric_revision']} → {a.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare"); s.add_argument("--args", required=True); s.add_argument("--out-dir", required=True)
    s.add_argument("--cells-per-agent", type=int, default=5); s.add_argument("--cell-ids", default=None)
    s = sub.add_parser("collect"); s.add_argument("--args", required=True); s.add_argument("--out-dir", required=True); s.add_argument("--out", required=True)
    a = p.parse_args()
    return {"prepare": cmd_prepare, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
