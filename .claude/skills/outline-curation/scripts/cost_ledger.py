#!/usr/bin/env python3
"""步 6 cost_ledger（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

彙總 Workflow journal（目錄下 *.json）＋ SKILL.md front matter 的 budgets → cost.json。
journal 檔案格式（本任務定義，1.4 對齊）：
    {"step": "structure"|"answerability", "run_id": "...",
     "agents": [{"prompt_tokens": int, "completion_tokens": int, "usd": float}, ...],
     "wall_s": float}

上限判定：每步（依 SKILL.md budgets 的 agents/usd）與整案（total）兩層。
任一層超支 ⇒ 印哪一層、exit 2。並把狀態檔 `cost` 鍵寫成
{"path": ..., "over_budget": bool}。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, make_envelope, sha256_file, update_state, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"

_FRONT_MATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def _parse_front_matter(skill_md_path: str) -> dict:
    """極簡 YAML front matter 解析——只需讀出 budgets 這個巢狀 dict，不引 PyYAML。"""
    with open(skill_md_path, encoding="utf-8") as f:
        text = f.read()
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{skill_md_path} 缺 front matter")
    fm_text = m.group(1)
    return _parse_simple_yaml(fm_text)


def _parse_simple_yaml(text: str) -> dict:
    """支援本 skill front matter 所需的最小子集：純量、巢狀 mapping（2 空白縮排），
    及 `{a: 1, b: 2}` 內嵌 flow mapping（用於 budgets.<step>）。"""
    root: dict = {}
    stack = [(0, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and stack[-1][0] > indent and len(stack) > 1:
            stack.pop()
        parent = stack[-1][1]
        if value == "" :
            new_dict: dict = {}
            parent[key] = new_dict
            stack.append((indent + 2, new_dict))
        elif value.startswith("{") and value.endswith("}"):
            parent[key] = _parse_flow_mapping(value)
        else:
            parent[key] = _coerce_scalar(value)
    return root


def _parse_flow_mapping(value: str) -> dict:
    inner = value.strip()[1:-1]
    out = {}
    for part in inner.split(","):
        if ":" not in part:
            continue
        k, _, v = part.partition(":")
        out[k.strip()] = _coerce_scalar(v.strip())
    return out


def _coerce_scalar(value: str):
    value = value.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def load_journal(journal_dir: str) -> list:
    entries = []
    for path in sorted(glob.glob(os.path.join(journal_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            entries.append(json.load(f))
    return entries


def summarize(entries: list) -> dict:
    by_step: dict = {}
    for entry in entries:
        step = entry.get("step", "unknown")
        agents = entry.get("agents", [])
        acc = by_step.setdefault(step, {"agents": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0})
        acc["agents"] += len(agents)
        acc["prompt_tokens"] += sum(int(a.get("prompt_tokens", 0)) for a in agents)
        acc["completion_tokens"] += sum(int(a.get("completion_tokens", 0)) for a in agents)
        acc["usd"] += sum(float(a.get("usd", 0.0)) for a in agents)
        acc["wall_s"] += float(entry.get("wall_s", 0.0))

    total = {"agents": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0}
    for acc in by_step.values():
        for k in total:
            total[k] += acc[k]
    return {"by_step": by_step, "total": total}


def check_budget(summary: dict, budgets: dict) -> tuple[bool, list]:
    """回 (over_budget, violations)。violations 為印給人看的字串清單。"""
    violations = []
    for step, limits in budgets.items():
        if step == "total":
            continue
        actual = summary["by_step"].get(step, {"agents": 0, "usd": 0.0})
        if "agents" in limits and actual["agents"] > limits["agents"]:
            violations.append(f"step={step} agents={actual['agents']} > 上限 {limits['agents']}")
        if "usd" in limits and actual["usd"] > limits["usd"]:
            violations.append(f"step={step} usd={actual['usd']} > 上限 {limits['usd']}")

    total_limits = budgets.get("total", {})
    total_actual = summary["total"]
    if "agents" in total_limits and total_actual["agents"] > total_limits["agents"]:
        violations.append(f"整案 agents={total_actual['agents']} > 上限 {total_limits['agents']}")
    if "usd" in total_limits and total_actual["usd"] > total_limits["usd"]:
        violations.append(f"整案 usd={total_actual['usd']} > 上限 {total_limits['usd']}")

    return (len(violations) > 0), violations


def main() -> int:
    p = argparse.ArgumentParser(description="彙總 Workflow journal＋provider usage → cost.json")
    p.add_argument("--journal", required=True, help="journal 目錄（.claude/skills/outline-curation/journal/）")
    p.add_argument("--skill", required=True, help="SKILL.md 路徑（讀 budgets）")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    front_matter = _parse_front_matter(args.skill)
    budgets = front_matter.get("budgets", {})
    if not budgets:
        print(f"[cost_ledger] {args.skill} front matter 缺 budgets", file=sys.stderr)
        return 2

    entries = load_journal(args.journal)
    summary = summarize(entries)
    over_budget, violations = check_budget(summary, budgets)

    if over_budget:
        for v in violations:
            print(f"[cost_ledger] 超支：{v}", file=sys.stderr)

    payload = {
        "by_step": summary["by_step"],
        "total": summary["total"],
        "over_budget": over_budget,
    }
    inputs_sha = {"skill": sha256_file(args.skill)}
    envelope = make_envelope(
        step="diff",
        skill_version=SKILL_VERSION,
        inputs_sha=inputs_sha,
        deterministic=True,
        payload=payload,
    )
    write_json(args.out, envelope)

    try:
        repo_root = find_repo_root()
        out_rel = os.path.relpath(os.path.abspath(args.out), repo_root)
        update_state(repo_root, {"cost": {"path": out_rel, "over_budget": over_budget}})
    except RuntimeError as e:
        print(f"[cost_ledger] 警告：找不到 repo 根，跳過狀態檔寫入（{e}）", file=sys.stderr)

    return 2 if over_budget else 0


if __name__ == "__main__":
    raise SystemExit(main())
