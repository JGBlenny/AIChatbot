#!/usr/bin/env python3
"""步 4 answerability 收尾（knowledge-outline-and-intent-architecture 任務 1.4｜design 元件 2）。

把 `.claude/workflows/outline-curation.js`（`step:'answerability'`）的回傳 JSON 包成
`StepEnvelope`、通過 `schemas/answerability.json`；同時把原始輸出寫成 journal 檔
（1.3 定義的格式）供 `cost_ledger.py` 彙總；並把狀態檔 `answerability` 鍵寫成
`{"path": ..., "needs_rubric_revision": bool}`（元件 3 Stop hook 讀）。

`needs_rubric_revision=true`：仍寫檔（保留證據），但 exit 2 並印原因——「停下回主 session」
是機制不是叮嚀（design 元件 2 Reconcile／E6）。

⛔ 不呼叫 LLM、不跑 Workflow。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, make_envelope, update_state, validate, load_schema, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "answerability.json")


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_journal_entry(run_result: dict, run_id: str, *, usd: float, prompt_tokens: int,
                         completion_tokens: int, wall_s: float) -> dict:
    """journal 檔格式（1.3 定義）：{"step","run_id","agents":[{prompt_tokens,completion_tokens,usd}],"wall_s"}。

    代理數＝run_result["agentsUsed"]；token／usd 由參數平均分攤給每個代理，未給則 0。
    """
    n = int(run_result.get("agentsUsed", 0))
    if n > 0:
        pt = prompt_tokens // n
        ct = completion_tokens // n
        u = usd / n
        agents = [{"prompt_tokens": pt, "completion_tokens": ct, "usd": u} for _ in range(n)]
        # 餘數併入最後一個代理，讓總和精確對得上輸入參數
        agents[-1]["prompt_tokens"] += prompt_tokens - pt * n
        agents[-1]["completion_tokens"] += completion_tokens - ct * n
        agents[-1]["usd"] += usd - u * n
    else:
        agents = []
    return {"step": "answerability", "run_id": run_id, "agents": agents, "wall_s": wall_s}


def build_envelope(run_result: dict, journal_path: str) -> dict:
    inputs_sha = dict(run_result.get("inputsSha") or {})
    labels = run_result.get("labels", [])
    needs_rubric_revision = bool(run_result.get("needs_rubric_revision", False))
    n_agents = int(run_result.get("agentsUsed", 0))

    payload = {"labels": labels, "needs_rubric_revision": needs_rubric_revision}
    cost = {
        "agents": n_agents,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "usd": 0.0,
        "wall_s": 0.0,
    }
    return make_envelope(
        step="answerability",
        skill_version=SKILL_VERSION,
        inputs_sha=inputs_sha,
        deterministic=False,
        payload=payload,
        raw_outputs_path=journal_path,
        cost=cost,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="把 Workflow answerability 回傳包成 StepEnvelope＋寫 journal")
    p.add_argument("--run-result", required=True, help="Workflow 回傳 JSON 檔路徑")
    p.add_argument("--out", required=True, help="輸出 answerability.json（StepEnvelope）路徑")
    p.add_argument("--journal-dir", required=False,
                    default=os.path.join(".claude", "skills", "outline-curation", "journal"))
    p.add_argument("--run-id", required=False, default=None)
    p.add_argument("--usd", required=False, type=float, default=0.0)
    p.add_argument("--prompt-tokens", required=False, type=int, default=0)
    p.add_argument("--completion-tokens", required=False, type=int, default=0)
    p.add_argument("--wall-s", required=False, type=float, default=0.0)
    args = p.parse_args()

    run_result = _load_json(args.run_result)
    run_id = args.run_id or f"answerability-{run_result.get('frozenAt', 'unknown').replace(':', '').replace('-', '')}"

    journal_entry = build_journal_entry(
        run_result, run_id,
        usd=args.usd, prompt_tokens=args.prompt_tokens,
        completion_tokens=args.completion_tokens, wall_s=args.wall_s,
    )
    os.makedirs(args.journal_dir, exist_ok=True)
    journal_path = os.path.join(args.journal_dir, f"{run_id}.json")
    write_json(journal_path, journal_entry)

    envelope = build_envelope(run_result, journal_path)
    envelope["cost"]["prompt_tokens"] = args.prompt_tokens
    envelope["cost"]["completion_tokens"] = args.completion_tokens
    envelope["cost"]["usd"] = args.usd
    envelope["cost"]["wall_s"] = args.wall_s

    validate(envelope, load_schema(_SCHEMA_PATH))
    write_json(args.out, envelope)

    needs_rubric_revision = envelope["payload"]["needs_rubric_revision"]

    try:
        repo_root = find_repo_root()
        out_rel = os.path.relpath(os.path.abspath(args.out), repo_root)
        update_state(repo_root, {
            "answerability": {
                "path": out_rel,
                "needs_rubric_revision": needs_rubric_revision,
            }
        })
    except RuntimeError as e:
        print(f"[finalize_answerability] 警告：找不到 repo 根，跳過狀態檔寫入（{e}）", file=sys.stderr)

    if needs_rubric_revision:
        print("[finalize_answerability] needs_rubric_revision=true——一致率 <0.90，"
              "回主 session 回修 rubric（新 readiness epoch），⛔ 不進正本、不進地圖", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
