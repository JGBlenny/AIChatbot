#!/usr/bin/env python3
"""
回測場景生成器 — 從 system_questions_checklist.json 產出回測用 test_scenarios

將 SystemQuestion 清單轉換為 AsyncBacktestFramework 可接受的 test_scenario 格式，
每個場景包含 module_id（在 keywords 中）以供模組分組統計。

場景分為：
- 靜態操作問題（query_type=static）：直接以 KB 回答
- 動態查詢問題（query_type=dynamic）：預期觸發 API call 回答

Usage:
    python scripts/kb_system_coverage/backtest_scenarios.py
    python scripts/kb_system_coverage/backtest_scenarios.py --output /path/to/output.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # AIChatbot/
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import SystemQuestion

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
CHECKLIST_PATH = _SCRIPT_DIR / "system_questions_checklist.json"
DEFAULT_OUTPUT_PATH = _SCRIPT_DIR / "backtest_test_scenarios.json"


# ---------------------------------------------------------------------------
# 場景轉換
# ---------------------------------------------------------------------------

def load_checklist(path: Optional[Path] = None) -> List[SystemQuestion]:
    """從 JSON 載入 system_questions_checklist。"""
    p = path or CHECKLIST_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [SystemQuestion(**q) for q in raw]


def question_to_scenario(q: SystemQuestion, scenario_id: int) -> Dict[str, Any]:
    """將單個 SystemQuestion 轉換為 AsyncBacktestFramework test_scenario 格式。

    回測框架要求的欄位：
    - id: 場景編號
    - test_question: 測試問題文字
    - keywords: 關鍵字清單（包含 module_id 供分組統計）
    - difficulty: 難度等級
    - notes: 備註

    額外 metadata 欄位供分析器使用：
    - module_id, query_type, priority, topic_id, roles, entry_point
    """
    # 將 module_id 加入 keywords（確保分組統計可用）
    keywords = list(q.keywords) if q.keywords else []
    if q.module_id and q.module_id not in keywords:
        keywords.insert(0, q.module_id)

    # 難度依優先級對應
    priority_to_difficulty = {"p0": "hard", "p1": "medium", "p2": "easy"}
    difficulty = priority_to_difficulty.get(q.priority, "medium")

    # 備註組合
    notes_parts = [
        f"模組: {q.module_id}",
        f"類型: {q.query_type}",
        f"角色: {','.join(q.roles)}",
        f"入口: {q.entry_point}",
    ]

    return {
        "id": scenario_id,
        "test_question": q.question,
        "keywords": keywords,
        "difficulty": difficulty,
        "notes": " | ".join(notes_parts),
        # metadata（回測框架會忽略，但分析器會使用）
        "module_id": q.module_id,
        "query_type": q.query_type,
        "priority": q.priority,
        "topic_id": q.topic_id,
        "roles": q.roles,
        "entry_point": q.entry_point,
        "question_category": q.question_category,
    }


def generate_scenarios(
    questions: List[SystemQuestion],
    *,
    filter_modules: Optional[List[str]] = None,
    filter_query_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """批量轉換問題清單為回測場景。

    Parameters
    ----------
    questions : 問題清單
    filter_modules : 只包含指定模組（None = 全部）
    filter_query_types : 只包含指定 query_type（None = 全部）

    Returns
    -------
    回測場景列表
    """
    filtered = questions

    if filter_modules:
        filtered = [q for q in filtered if q.module_id in filter_modules]

    if filter_query_types:
        filtered = [q for q in filtered if q.query_type in filter_query_types]

    scenarios = []
    for idx, q in enumerate(filtered, start=1):
        scenarios.append(question_to_scenario(q, scenario_id=idx))

    return scenarios


def save_scenarios(scenarios: List[Dict[str, Any]], path: Optional[Path] = None) -> Path:
    """將場景列表寫入 JSON 檔案。"""
    p = path or DEFAULT_OUTPUT_PATH
    p.write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI 入口：載入問題清單並輸出回測場景 JSON。"""
    import argparse

    parser = argparse.ArgumentParser(description="產出回測用 test_scenarios")
    parser.add_argument("--input", type=str, default=None, help="問題清單 JSON 路徑")
    parser.add_argument("--output", type=str, default=None, help="輸出場景 JSON 路徑")
    parser.add_argument("--modules", type=str, default=None, help="限定模組（逗號分隔）")
    parser.add_argument("--query-types", type=str, default=None, help="限定 query_type（逗號分隔）")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    output_path = Path(args.output) if args.output else None

    questions = load_checklist(input_path)
    print(f"載入 {len(questions)} 個問題")

    filter_modules = [m.strip() for m in args.modules.split(",")] if args.modules else None
    filter_query_types = [t.strip() for t in args.query_types.split(",")] if args.query_types else None

    scenarios = generate_scenarios(
        questions,
        filter_modules=filter_modules,
        filter_query_types=filter_query_types,
    )
    print(f"產出 {len(scenarios)} 個回測場景")

    out = save_scenarios(scenarios, output_path)
    print(f"已寫入：{out}")


if __name__ == "__main__":
    main()
