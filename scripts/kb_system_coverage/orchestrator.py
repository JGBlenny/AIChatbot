"""
JGB 系統知識覆蓋率 Pipeline Orchestrator

七階段 pipeline 編排：
  P1 Module Mapping     — 從 JGB 程式碼爬梳模組清單
  P2 Question Generation — 各角色操作問題清單生成
  P3 Coverage Analysis   — 覆蓋缺口分析
  P4 Static KB Generation — 靜態系統操作 KB 批量生成
  P5 API KB Building      — 動態查詢 KB 條目建立
  P6 Review Pause         — 暫停等待人工審核
  P7 Backtest Validation  — 回測驗證覆蓋率改善

P4 / P5 平行執行（互不依賴）。
P6 暫停後需另行以 --skip-phases 跳過前段，才會進入 P7。

Usage:
    # 完整 pipeline（P1-P6 後暫停等待審核）
    python scripts/kb_system_coverage/orchestrator.py --vendor-id 1

    # 審核完成後，只跑回測（P7）
    python scripts/kb_system_coverage/orchestrator.py --vendor-id 1 \\
        --skip-phases mapping,questions,coverage,generate_kb,build_api_kb,pause

    # 跳過特定階段
    python scripts/kb_system_coverage/orchestrator.py --vendor-id 1 \\
        --skip-phases mapping,questions

    # 自訂批次大小
    python scripts/kb_system_coverage/orchestrator.py --vendor-id 1 --batch-size 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # AIChatbot/
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import (
    CoverageReport,
    GapItem,
    Module,
    SystemQuestion,
)
from scripts.kb_system_coverage.module_mapper import build_module_inventory
from scripts.kb_system_coverage.question_generator import (
    generate_questions,
    load_inventory,
    save_output,
)
from scripts.kb_system_coverage.coverage_analyzer import CoverageAnalyzer
from scripts.kb_system_coverage.system_kb_generator import SystemKBGenerator
from scripts.kb_system_coverage.api_kb_builder import ApiKBBuilder


# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
ALL_PHASES = [
    "mapping",        # P1: Module Mapping
    "questions",      # P2: Question Generation
    "coverage",       # P3: Coverage Analysis
    "generate_kb",    # P4: Static KB Generation
    "build_api_kb",   # P5: API KB Building
    "pause",          # P6: Review Pause
    "backtest",       # P7: Backtest Validation
]

# 輸出檔案路徑
INVENTORY_PATH = _SCRIPT_DIR / "jgb_module_inventory.json"
QUESTIONS_PATH = _SCRIPT_DIR / "system_questions_checklist.json"
COVERAGE_REPORT_PATH = _SCRIPT_DIR / "coverage_report.json"
STATIC_KB_PATH = _SCRIPT_DIR / "static_kb_candidates.json"
API_KB_PATH = _SCRIPT_DIR / "api_kb_entries.json"


# ---------------------------------------------------------------------------
# 輔助函式：取得 KB / SOP 資料（供 CoverageAnalyzer 使用）
# ---------------------------------------------------------------------------

async def _fetch_kb_items(vendor_id: int) -> List[dict]:
    """從 knowledge_base 取得現有 KB 條目（含 embedding）。

    注意：此函式需要 DB 連線，在純測試環境中會被 mock。
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        import asyncpg
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "aichatbot_admin"),
            user=os.getenv("DB_USER", "aichatbot"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            min_size=1,
            max_size=3,
        )
        try:
            rows = await pool.fetch(
                """SELECT id, question_summary, answer, embedding
                   FROM knowledge_base
                   WHERE vendor_id = $1 AND is_active = true""",
                vendor_id,
            )
            return [dict(r) for r in rows]
        finally:
            await pool.close()
    except Exception as e:
        print(f"  [WARN] 無法載入 KB 資料：{e}")
        return []


async def _fetch_sop_items(vendor_id: int) -> List[dict]:
    """從 vendor_sop_items 取得現有 SOP 條目（含 embedding）。"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        import asyncpg
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "aichatbot_admin"),
            user=os.getenv("DB_USER", "aichatbot"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            min_size=1,
            max_size=3,
        )
        try:
            rows = await pool.fetch(
                """SELECT id, title, content, embedding
                   FROM vendor_sop_items
                   WHERE vendor_id = $1 AND is_active = true""",
                vendor_id,
            )
            return [dict(r) for r in rows]
        finally:
            await pool.close()
    except Exception as e:
        print(f"  [WARN] 無法載入 SOP 資料：{e}")
        return []


# ---------------------------------------------------------------------------
# Pipeline 主流程
# ---------------------------------------------------------------------------

async def run_pipeline(
    vendor_id: int,
    skip_phases: Optional[List[str]] = None,
    batch_size: int = 5,
) -> Dict:
    """執行 JGB 系統知識覆蓋率 pipeline。

    Parameters
    ----------
    vendor_id : 業者 ID
    skip_phases : 要跳過的階段名稱列表
    batch_size : KB 生成批次大小

    Returns
    -------
    包含各階段結果的 dict，status 為 "completed" 或 "waiting_for_review"
    """
    skip = set(skip_phases or [])
    results: Dict = {}

    # 中間資料：各階段間傳遞
    modules: List[Module] = []
    questions: List[SystemQuestion] = []
    report: Optional[CoverageReport] = None

    print("=" * 60)
    print("JGB 系統知識覆蓋率 Pipeline")
    print(f"  vendor_id: {vendor_id}")
    print(f"  skip_phases: {skip or '(none)'}")
    print(f"  batch_size: {batch_size}")
    print(f"  時間: {datetime.now().isoformat()}")
    print("=" * 60)

    # ==================================================================
    # Phase 1: Module Mapping
    # ==================================================================
    if "mapping" not in skip:
        print("\n📦 Phase 1: Module Mapping — 模組盤點")
        modules = build_module_inventory()
        # 保存結果
        INVENTORY_PATH.write_text(
            json.dumps(
                [asdict(m) for m in modules],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        results["module_count"] = len(modules)
        print(f"  完成：{len(modules)} 個模組")
    else:
        print("\n⏭️  Phase 1: 跳過（mapping）")
        # 從檔案載入既有結果
        if INVENTORY_PATH.exists():
            modules = load_inventory(INVENTORY_PATH)
            print(f"  載入既有模組清單：{len(modules)} 個模組")

    # ==================================================================
    # Phase 2: Question Generation
    # ==================================================================
    if "questions" not in skip:
        print("\n❓ Phase 2: Question Generation — 問題清單生成")
        if not modules:
            print("  [WARN] 無模組清單，跳過問題生成")
        else:
            questions = await generate_questions(modules)
            save_output(questions, QUESTIONS_PATH)
            results["question_count"] = len(questions)
            print(f"  完成：{len(questions)} 個問題")
    else:
        print("\n⏭️  Phase 2: 跳過（questions）")
        # 從檔案載入既有結果
        if QUESTIONS_PATH.exists():
            raw = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
            questions = [SystemQuestion(**q) for q in raw]
            print(f"  載入既有問題清單：{len(questions)} 個問題")

    # ==================================================================
    # Phase 3: Coverage Analysis
    # ==================================================================
    if "coverage" not in skip:
        print("\n🔍 Phase 3: Coverage Analysis — 覆蓋缺口分析")
        if not questions:
            print("  [WARN] 無問題清單，跳過覆蓋分析")
        else:
            # 取得現有 KB 與 SOP
            kb_items = await _fetch_kb_items(vendor_id)
            sop_items = await _fetch_sop_items(vendor_id)
            print(f"  KB: {len(kb_items)} 筆, SOP: {len(sop_items)} 筆")

            analyzer = CoverageAnalyzer()
            report = await analyzer.analyze(questions, kb_items, sop_items)
            analyzer.export_report(report, COVERAGE_REPORT_PATH)

            results["total_questions"] = report.total_questions
            results["covered_by_kb"] = report.covered_by_kb
            results["covered_by_sop"] = report.covered_by_sop
            results["uncovered"] = report.uncovered
            results["partial_covered"] = report.partial_covered
            results["gap_count"] = len(report.gaps)
            print(f"  覆蓋率：KB {report.covered_by_kb}/{report.total_questions}, "
                  f"SOP {report.covered_by_sop}/{report.total_questions}")
            print(f"  缺口：{len(report.gaps)} 筆")
    else:
        print("\n⏭️  Phase 3: 跳過（coverage）")
        # 從檔案載入既有結果
        if COVERAGE_REPORT_PATH.exists():
            raw = json.loads(COVERAGE_REPORT_PATH.read_text(encoding="utf-8"))
            gaps = [GapItem(**g) for g in raw.get("gaps", [])]
            report = CoverageReport(
                total_questions=raw.get("total_questions", 0),
                gaps=gaps,
            )
            print(f"  載入既有覆蓋報告：{len(gaps)} 個缺口")

    # ==================================================================
    # Phase 4+5: Static KB Generation + API KB Building（平行）
    # ==================================================================
    run_p4 = "generate_kb" not in skip
    run_p5 = "build_api_kb" not in skip

    if run_p4 or run_p5:
        gaps = report.gaps if report else []
        if not gaps:
            print("\n  [WARN] 無覆蓋缺口，跳過 P4/P5")
        else:
            tasks = []

            # P4: 靜態 KB 生成
            if run_p4:
                print("\n📝 Phase 4: Static KB Generation — 靜態 KB 批量生成")

                async def _run_p4():
                    generator = SystemKBGenerator(batch_size=batch_size)
                    candidates = await generator.generate_batch(
                        gaps=gaps,
                        module_inventory=modules,
                    )
                    generator.export_candidates(candidates, STATIC_KB_PATH)
                    return candidates

                tasks.append(("p4", _run_p4()))
            else:
                print("\n⏭️  Phase 4: 跳過（generate_kb）")

            # P5: 動態 KB 建立
            if run_p5:
                print("\n🔗 Phase 5: API KB Building — 動態查詢 KB 條目建立")

                async def _run_p5():
                    builder = ApiKBBuilder()
                    kb_entries, api_entries = builder.build(gaps)
                    builder.export(kb_entries, api_entries, API_KB_PATH)
                    return kb_entries, api_entries

                tasks.append(("p5", _run_p5()))
            else:
                print("\n⏭️  Phase 5: 跳過（build_api_kb）")

            # 平行執行
            task_results = await asyncio.gather(
                *[t[1] for t in tasks], return_exceptions=True
            )

            for (label, _), result in zip(tasks, task_results):
                if isinstance(result, Exception):
                    print(f"  [ERROR] {label} 失敗：{result}")
                    continue
                if label == "p4":
                    results["static_kb_count"] = len(result)
                    print(f"  P4 完成：{len(result)} 筆靜態 KB 候選")
                elif label == "p5":
                    kb_entries, api_entries = result
                    results["api_kb_count"] = len(kb_entries)
                    results["api_endpoint_count"] = len(api_entries)
                    print(f"  P5 完成：{len(kb_entries)} 筆 API KB, "
                          f"{len(api_entries)} 筆端點設定")
    else:
        print("\n⏭️  Phase 4: 跳過（generate_kb）")
        print("⏭️  Phase 5: 跳過（build_api_kb）")

    # ==================================================================
    # Phase 6: Review Pause — 暫停等待人工審核
    # ==================================================================
    if "pause" not in skip:
        print("\n" + "=" * 60)
        print("⏸️  Phase 6: 等待人工審核")
        print(f"  靜態 KB 候選：{results.get('static_kb_count', 0)} 筆")
        print(f"  API KB 條目：{results.get('api_kb_count', 0)} 筆")
        print(f"  請至審核介面確認後，執行以下命令進行回測：")
        print()
        print(f"  python scripts/kb_system_coverage/orchestrator.py \\")
        print(f"    --vendor-id {vendor_id} \\")
        print(f"    --skip-phases mapping,questions,coverage,generate_kb,build_api_kb,pause")
        print("=" * 60)
        results["status"] = "waiting_for_review"
        return results

    # ==================================================================
    # Phase 7: Backtest Validation — 回測驗證
    # ==================================================================
    if "backtest" not in skip:
        print("\n🧪 Phase 7: Backtest Validation — 回測驗證")
        # TODO: 待 task 7.2 實作回測場景後整合
        print("  [TODO] 回測驗證尚未實作（待 task 7.2）")
        results["backtest"] = {"status": "not_implemented"}
    else:
        print("\n⏭️  Phase 7: 跳過（backtest）")

    # ==================================================================
    # 最終報告
    # ==================================================================
    print("\n" + "=" * 60)
    print("📊 Pipeline 完成")
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    print("=" * 60)

    results["status"] = "completed"
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令列參數。"""
    parser = argparse.ArgumentParser(
        description="JGB 系統知識覆蓋率 Pipeline Orchestrator",
    )
    parser.add_argument(
        "--vendor-id", type=int, required=True,
        help="業者 ID",
    )
    parser.add_argument(
        "--skip-phases", type=str, default="",
        help="要跳過的階段（逗號分隔），可用值：" + ", ".join(ALL_PHASES),
    )
    parser.add_argument(
        "--batch-size", type=int, default=5,
        help="KB 生成批次大小（預設 5）",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()

    skip_phases = [x.strip() for x in args.skip_phases.split(",") if x.strip()]

    asyncio.run(run_pipeline(
        vendor_id=args.vendor_id,
        skip_phases=skip_phases or None,
        batch_size=args.batch_size,
    ))
