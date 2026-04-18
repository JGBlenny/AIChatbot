"""
KB 停用執行腳本

讀取 gap_report.json 中的 deactivated_kb 清單，執行 KB 停用作業。

預設以 --dry-run 模式運行，僅顯示待停用項目的影響範圍；
需明確加上 --execute 旗標才會實際執行 UPDATE knowledge_base SET is_active = false。

使用方式：
  # 預覽待停用項目（預設 dry-run）
  python3 scripts/kb_coverage/apply_deactivations.py \\
      --report scripts/kb_coverage/gap_report.json

  # 實際執行停用
  python3 scripts/kb_coverage/apply_deactivations.py \\
      --report scripts/kb_coverage/gap_report.json --execute
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path setup — allow importing from rag-orchestrator
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator/services"))


# ---------------------------------------------------------------------------
# DB 存取
# ---------------------------------------------------------------------------
def _get_db_connection():
    """建立 PostgreSQL 連線。"""
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )


# ---------------------------------------------------------------------------
# 報告載入
# ---------------------------------------------------------------------------
def load_deactivation_list(report_path: str) -> List[Dict[str, Any]]:
    """從 gap_report.json 載入 deactivated_kb 清單。"""
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    items = report.get("deactivated_kb", [])
    if not isinstance(items, list):
        raise ValueError(f"gap_report.json 的 deactivated_kb 欄位格式錯誤（預期 list，實際 {type(items).__name__}）")

    return items


# ---------------------------------------------------------------------------
# Dry-run 顯示
# ---------------------------------------------------------------------------
def print_dry_run_summary(items: List[Dict[str, Any]]) -> None:
    """以表格格式顯示待停用項目的影響範圍。"""
    print()
    print("=" * 70)
    print("KB 停用預覽（dry-run）")
    print("=" * 70)
    print(f"  待停用筆數: {len(items)}")
    print()

    if not items:
        print("  （無待停用項目）")
        print("=" * 70)
        return

    # 按停用原因分組統計
    reason_counts: Dict[str, int] = {}
    for item in items:
        reason = item.get("reason", "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    print("  停用原因統計:")
    for reason, count in sorted(reason_counts.items()):
        print(f"    {reason}: {count} 筆")
    print()

    # 逐筆明細
    print(f"  {'#':<4} {'KB ID':<8} {'原因':<20} {'question_summary'}")
    print(f"  {'-'*4} {'-'*8} {'-'*20} {'-'*36}")

    for idx, item in enumerate(items, 1):
        kb_id = item.get("kb_id", "?")
        reason = item.get("reason", "unknown")
        question_summary = item.get("question_summary", "（無）")
        detail = item.get("detail", "")
        print(f"  {idx:<4} {str(kb_id):<8} {reason:<20} {question_summary}")
        if detail:
            print(f"       {'':8} {'':20} └ {detail}")

    print()
    print("=" * 70)
    print("  ⚠ 這是 dry-run 模式，尚未執行任何資料庫變更。")
    print("  若要實際停用，請加上 --execute 旗標重新執行。")
    print("=" * 70)


# ---------------------------------------------------------------------------
# 執行停用
# ---------------------------------------------------------------------------
def execute_deactivations(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    實際執行 KB 停用：UPDATE knowledge_base SET is_active = false。

    Returns
    -------
    Dict 包含執行結果摘要
    """
    if not items:
        return {"total": 0, "success": 0, "skipped": 0, "failed": 0, "details": []}

    kb_ids = [item.get("kb_id") for item in items if item.get("kb_id") is not None]

    if not kb_ids:
        return {"total": 0, "success": 0, "skipped": 0, "failed": 0, "details": []}

    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 先查詢哪些 KB 目前仍為 is_active=true
            cur.execute(
                "SELECT id FROM knowledge_base WHERE id = ANY(%s) AND is_active = true",
                (kb_ids,),
            )
            active_ids = {row[0] for row in cur.fetchall()}

            skipped_ids = set(kb_ids) - active_ids
            target_ids = sorted(active_ids)

            if target_ids:
                cur.execute(
                    "UPDATE knowledge_base SET is_active = false, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ANY(%s) AND is_active = true",
                    (target_ids,),
                )
                affected = cur.rowcount
            else:
                affected = 0

        conn.commit()

        result = {
            "total": len(kb_ids),
            "success": affected,
            "skipped": len(skipped_ids),
            "failed": len(kb_ids) - affected - len(skipped_ids),
            "details": [],
        }

        # 建立逐筆明細
        for item in items:
            kb_id = item.get("kb_id")
            if kb_id in active_ids:
                status = "deactivated"
            elif kb_id in skipped_ids:
                status = "skipped (already inactive)"
            else:
                status = "skipped (not found)"
            result["details"].append({
                "kb_id": kb_id,
                "question_summary": item.get("question_summary", ""),
                "reason": item.get("reason", ""),
                "status": status,
            })

        return result

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"停用執行失敗: {e}") from e
    finally:
        conn.close()


def print_execute_summary(result: Dict[str, Any]) -> None:
    """顯示執行結果摘要。"""
    print()
    print("=" * 70)
    print("KB 停用執行結果")
    print("=" * 70)
    print(f"  總筆數:     {result['total']}")
    print(f"  成功停用:   {result['success']}")
    print(f"  略過:       {result['skipped']}（已停用或不存在）")
    if result["failed"] > 0:
        print(f"  失敗:       {result['failed']}")
    print()

    details = result.get("details", [])
    if details:
        print(f"  {'KB ID':<8} {'狀態':<30} {'question_summary'}")
        print(f"  {'-'*8} {'-'*30} {'-'*30}")
        for d in details:
            print(f"  {str(d['kb_id']):<8} {d['status']:<30} {d['question_summary']}")
    print()
    print("=" * 70)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="KB 停用執行腳本 — 讀取 gap_report.json 執行 KB 停用"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="gap_report.json 檔案路徑（預設：腳本所在目錄下的 gap_report.json）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="實際執行停用（預設為 dry-run 模式）",
    )

    args = parser.parse_args()

    # 決定報告路徑
    report_path = args.report or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "gap_report.json"
    )

    if not os.path.isfile(report_path):
        print(f"[ERROR] 找不到報告檔案: {report_path}")
        sys.exit(1)

    # 載入待停用清單
    print(f"[apply_deactivations] 載入報告: {report_path}")
    items = load_deactivation_list(report_path)
    print(f"[apply_deactivations] 待停用項目: {len(items)} 筆")

    if args.execute:
        # 執行模式
        print("[apply_deactivations] 模式: --execute（實際執行停用）")
        result = execute_deactivations(items)
        print_execute_summary(result)
    else:
        # Dry-run 模式（預設）
        print("[apply_deactivations] 模式: dry-run（僅預覽）")
        print_dry_run_summary(items)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Self-test（無 CLI 引數時執行）
    # ------------------------------------------------------------------
    import tempfile

    print("=" * 60)
    print("apply_deactivations.py — self-test")
    print("=" * 60)

    # ----------------------------------------------------------
    # Test 1: load_deactivation_list 正確載入
    # ----------------------------------------------------------
    sample_report = {
        "summary": {},
        "kb_gaps": [],
        "deactivated_kb": [
            {
                "kb_id": 42,
                "question_summary": "押金規定",
                "reason": "quality_poor",
                "detail": "answer 長度不足（30 字 < 50）",
            },
            {
                "kb_id": 99,
                "question_summary": "報修流程說明",
                "reason": "overlap_with_sop",
                "detail": "與 SOP item '報修流程' 重疊 (score=0.912)",
            },
        ],
        "sop_gaps": [],
        "suggest_api_topics": [],
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sample_report, f, ensure_ascii=False, indent=2)
        tmp_path = f.name

    try:
        items = load_deactivation_list(tmp_path)
        assert len(items) == 2, f"應有 2 筆，實際 {len(items)}"
        assert items[0]["kb_id"] == 42
        assert items[1]["kb_id"] == 99
        assert items[0]["reason"] == "quality_poor"
        assert items[1]["reason"] == "overlap_with_sop"
        print("  [PASS] load_deactivation_list 正確載入 2 筆")
    finally:
        os.unlink(tmp_path)

    # ----------------------------------------------------------
    # Test 2: load_deactivation_list 處理空清單
    # ----------------------------------------------------------
    empty_report = {
        "summary": {},
        "kb_gaps": [],
        "deactivated_kb": [],
        "sop_gaps": [],
        "suggest_api_topics": [],
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(empty_report, f, ensure_ascii=False, indent=2)
        tmp_path2 = f.name

    try:
        items_empty = load_deactivation_list(tmp_path2)
        assert len(items_empty) == 0
        print("  [PASS] load_deactivation_list 處理空清單")
    finally:
        os.unlink(tmp_path2)

    # ----------------------------------------------------------
    # Test 3: load_deactivation_list 處理缺少 deactivated_kb 欄位
    # ----------------------------------------------------------
    missing_field_report = {"summary": {}, "kb_gaps": []}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(missing_field_report, f, ensure_ascii=False, indent=2)
        tmp_path3 = f.name

    try:
        items_missing = load_deactivation_list(tmp_path3)
        assert len(items_missing) == 0, "缺少欄位時應回傳空清單"
        print("  [PASS] load_deactivation_list 處理缺少欄位")
    finally:
        os.unlink(tmp_path3)

    # ----------------------------------------------------------
    # Test 4: load_deactivation_list 拒絕錯誤型別
    # ----------------------------------------------------------
    bad_type_report = {"deactivated_kb": "not_a_list"}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(bad_type_report, f, ensure_ascii=False, indent=2)
        tmp_path4 = f.name

    try:
        load_deactivation_list(tmp_path4)
        assert False, "應拋出 ValueError"
    except ValueError as e:
        assert "格式錯誤" in str(e)
        print(f"  [PASS] load_deactivation_list 拒絕錯誤型別: {e}")
    finally:
        os.unlink(tmp_path4)

    # ----------------------------------------------------------
    # Test 5: print_dry_run_summary 不拋出例外
    # ----------------------------------------------------------
    test_items = [
        {"kb_id": 1, "question_summary": "測試問題一", "reason": "quality_poor", "detail": "長度不足"},
        {"kb_id": 2, "question_summary": "測試問題二", "reason": "overlap_with_sop", "detail": "重疊"},
        {"kb_id": 3, "question_summary": "測試問題三", "reason": "quality_poor", "detail": "空洞回答"},
    ]
    try:
        print_dry_run_summary(test_items)
        print("  [PASS] print_dry_run_summary 正常執行（3 筆）")
    except Exception as e:
        assert False, f"print_dry_run_summary 不應拋出例外: {e}"

    # ----------------------------------------------------------
    # Test 6: print_dry_run_summary 處理空清單
    # ----------------------------------------------------------
    try:
        print_dry_run_summary([])
        print("  [PASS] print_dry_run_summary 處理空清單")
    except Exception as e:
        assert False, f"print_dry_run_summary 空清單不應拋出例外: {e}"

    # ----------------------------------------------------------
    # Test 7: print_execute_summary 不拋出例外
    # ----------------------------------------------------------
    test_result = {
        "total": 3,
        "success": 2,
        "skipped": 1,
        "failed": 0,
        "details": [
            {"kb_id": 1, "question_summary": "問題一", "reason": "quality_poor", "status": "deactivated"},
            {"kb_id": 2, "question_summary": "問題二", "reason": "overlap_with_sop", "status": "deactivated"},
            {"kb_id": 3, "question_summary": "問題三", "reason": "quality_poor", "status": "skipped (already inactive)"},
        ],
    }
    try:
        print_execute_summary(test_result)
        print("  [PASS] print_execute_summary 正常執行")
    except Exception as e:
        assert False, f"print_execute_summary 不應拋出例外: {e}"

    # ----------------------------------------------------------
    # Test 8: DeactivatedKB 結構欄位完整
    # ----------------------------------------------------------
    required_fields = {"kb_id", "question_summary", "reason", "detail"}
    for item in sample_report["deactivated_kb"]:
        assert required_fields.issubset(set(item.keys())), \
            f"DeactivatedKB 缺少欄位: {required_fields - set(item.keys())}"
    print("  [PASS] DeactivatedKB 結構欄位完整")

    # ----------------------------------------------------------
    # Test 9: argparse 預設為 dry-run（不帶 --execute）
    # ----------------------------------------------------------
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", default=False)
    test_args = parser.parse_args([])
    assert test_args.execute is False, "預設應為 dry-run（execute=False）"
    print("  [PASS] argparse 預設為 dry-run")

    # ----------------------------------------------------------
    # Test 10: argparse --execute 旗標
    # ----------------------------------------------------------
    test_args2 = parser.parse_args(["--execute"])
    assert test_args2.execute is True
    print("  [PASS] argparse --execute 旗標正確")

    print()
    print("=" * 60)
    print("All apply_deactivations.py self-tests passed!")
    print("=" * 60)
