"""
KB 批量生成腳本

讀取 gap_report.json 中的 kb_gaps 清單，為每筆缺口呼叫 KnowledgeGenerator
批量生成知識，寫入 loop_generated_knowledge（status=pending）。

功能：
  - 讀取 gap_report.json 的 kb_gaps 清單
  - 為每筆缺口建立符合 KnowledgeGenerator 輸入格式的 gap 結構
  - 生成前檢查 loop_generated_knowledge 是否已有相同 question 的 pending 項目（冪等性）
  - 呼叫 KnowledgeGenerator.generate_knowledge() 批量生成
  - 使用 tenacity 重試處理 API 限流

使用方式：
  python3 scripts/kb_coverage/generate_kb_batch.py \\
      --report scripts/kb_coverage/gap_report.json

  # 指定 batch size（預設 10）
  python3 scripts/kb_coverage/generate_kb_batch.py \\
      --report scripts/kb_coverage/gap_report.json --batch-size 5

  # dry-run 模式（不實際生成，僅顯示待生成清單）
  python3 scripts/kb_coverage/generate_kb_batch.py \\
      --report scripts/kb_coverage/gap_report.json --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Path setup — allow importing from rag-orchestrator
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator/services"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 10
DEFAULT_LOOP_ID = 0  # 批量生成用的佔位 loop_id
DEFAULT_ITERATION = 1
DEFAULT_VENDOR_ID = 1


# ---------------------------------------------------------------------------
# DB 存取
# ---------------------------------------------------------------------------
def _create_db_pool(minconn: int = 1, maxconn: int = 5):
    """建立 PostgreSQL 連線池。"""
    import psycopg2.pool

    return psycopg2.pool.SimpleConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )


def _get_db_connection():
    """建立單一 PostgreSQL 連線（用於冪等性檢查等不需要池的場景）。"""
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
def preflight_check_columns(conn) -> bool:
    """檢查 loop_generated_knowledge 表是否具備必要欄位。

    若缺少 category / is_template / template_vars 欄位，印出警告但不阻擋。
    Returns True 表示通過，False 表示有缺少欄位。
    """
    required_columns = ["category", "scope", "is_template", "template_vars"]
    missing: List[str] = []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'loop_generated_knowledge'
        """)
        existing = {row[0] for row in cur.fetchall()}

    for col in required_columns:
        if col not in existing:
            missing.append(col)

    if missing:
        print(f"[preflight] 警告：loop_generated_knowledge 缺少欄位: {', '.join(missing)}")
        print("[preflight] KnowledgeGenerator._save_to_database 可能會因欄位不存在而失敗。")
        print("[preflight] 請先執行 migration 新增欄位後再重新執行本腳本。")
        return False

    print("[preflight] loop_generated_knowledge 欄位檢查通過")
    return True


# ---------------------------------------------------------------------------
# 讀取 gap_report
# ---------------------------------------------------------------------------
def load_gap_report(filepath: str) -> Dict[str, Any]:
    """載入 gap_report.json。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 冪等性檢查：查詢已有的 pending questions
# ---------------------------------------------------------------------------
def get_existing_pending_questions(conn) -> Set[str]:
    """查詢 loop_generated_knowledge 中 status=pending 的 question 集合。"""
    import psycopg2.extras

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT question
            FROM loop_generated_knowledge
            WHERE status = 'pending'
        """)
        return {row["question"] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# 將 kb_gaps 轉換為 KnowledgeGenerator 輸入格式
# ---------------------------------------------------------------------------
def _dimension_to_scope(dimension: str) -> str:
    """將 dimension 映射為 scope。"""
    if dimension == "vendor":
        return "vendor"
    return "global"


def build_generator_gaps(
    kb_gaps: List[Dict[str, Any]],
    existing_pending: Set[str],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """將 gap_report 的 kb_gaps 轉換為 KnowledgeGenerator 所需的 gaps 格式。

    同時執行冪等性過濾：跳過已有 pending 項目的 question。

    Returns:
        (gaps_to_generate, skipped_gaps)
    """
    gaps_to_generate: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for idx, gap in enumerate(kb_gaps):
        question = gap.get("question", "")

        # 冪等性：跳過已有 pending 的 question
        if question in existing_pending:
            skipped.append(gap)
            continue

        scope = _dimension_to_scope(gap.get("dimension", "general"))

        generator_gap: Dict[str, Any] = {
            "gap_id": idx + 1,  # 自動編號（KnowledgeGenerator 需要 gap_id）
            "question": question,
            "failure_reason": gap.get("reason", "missing"),
            "priority": "p0" if gap.get("reason") == "missing" else "p1",
            "suggested_action_type": "direct_answer",
            "intent_name": gap.get("category", "未知"),
            # 新增欄位（task 4.1 擴充）
            "dimension": gap.get("dimension", "general"),
            "scope": scope,
            "category": gap.get("category", ""),
        }
        gaps_to_generate.append(generator_gap)

    return gaps_to_generate, skipped


# ---------------------------------------------------------------------------
# 建立 action_type_judgments（全部為 direct_answer）
# ---------------------------------------------------------------------------
def build_action_type_judgments(gaps: List[Dict[str, Any]]) -> Dict[int, Dict]:
    """為所有 gaps 建立 action_type_judgments，全部設定為 direct_answer。"""
    return {
        gap["gap_id"]: {"action_type": "direct_answer"}
        for gap in gaps
    }


# ---------------------------------------------------------------------------
# 主要生成流程
# ---------------------------------------------------------------------------
async def generate_kb_batch(
    report_path: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    loop_id: int = DEFAULT_LOOP_ID,
    vendor_id: int = DEFAULT_VENDOR_ID,
) -> Dict[str, Any]:
    """
    批量生成 KB 的主流程。

    Parameters
    ----------
    report_path : str
        gap_report.json 的檔案路徑
    batch_size : int
        每批次生成的筆數（控制 KnowledgeGenerator 的並發量）
    dry_run : bool
        若為 True，不實際呼叫 API，僅顯示待生成清單
    loop_id : int
        用於 loop_generated_knowledge 的 loop_id
    vendor_id : int
        業者 ID

    Returns
    -------
    Dict 包含生成摘要
    """
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    # --- 1. 載入 gap_report ---
    print(f"[generate_kb_batch] 載入: {report_path}")
    report = load_gap_report(report_path)
    kb_gaps = report.get("kb_gaps", [])
    print(f"[generate_kb_batch] kb_gaps 總數: {len(kb_gaps)}")

    if not kb_gaps:
        print("[generate_kb_batch] 無 kb_gaps，結束")
        return {"total": 0, "generated": 0, "skipped": 0, "failed": 0}

    # --- 2. 冪等性檢查 ---
    if dry_run:
        existing_pending: Set[str] = set()
        print("[generate_kb_batch] dry-run 模式，跳過冪等性檢查")
    else:
        print("[generate_kb_batch] 檢查既有 pending 項目...")
        conn = _get_db_connection()
        try:
            # Preflight: 檢查欄位
            preflight_check_columns(conn)
            existing_pending = get_existing_pending_questions(conn)
        finally:
            conn.close()
        print(f"  既有 pending 項目: {len(existing_pending)} 筆")

    # --- 3. 轉換為 KnowledgeGenerator 格式 ---
    gaps_to_generate, skipped_gaps = build_generator_gaps(kb_gaps, existing_pending)
    print(f"[generate_kb_batch] 待生成: {len(gaps_to_generate)} 筆, "
          f"跳過（冪等）: {len(skipped_gaps)} 筆")

    if not gaps_to_generate:
        print("[generate_kb_batch] 所有缺口已有 pending 項目，結束")
        return {
            "total": len(kb_gaps),
            "generated": 0,
            "skipped": len(skipped_gaps),
            "failed": 0,
        }

    # --- dry-run 模式：僅列印 ---
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — 待生成缺口清單")
        print("=" * 60)
        for i, gap in enumerate(gaps_to_generate, 1):
            print(f"  {i:3d}. [{gap['dimension']}/{gap['category']}] {gap['question']}")
            print(f"       scope={gap['scope']}, reason={gap['failure_reason']}")
        print("=" * 60)
        print(f"  共 {len(gaps_to_generate)} 筆待生成")
        if skipped_gaps:
            print(f"\n  跳過（已有 pending）: {len(skipped_gaps)} 筆")
            for gap in skipped_gaps[:5]:
                print(f"    - {gap.get('question', '')[:60]}")
            if len(skipped_gaps) > 5:
                print(f"    ... 及其他 {len(skipped_gaps) - 5} 筆")
        return {
            "total": len(kb_gaps),
            "generated": 0,
            "skipped": len(skipped_gaps),
            "failed": 0,
            "dry_run": True,
        }

    # --- 4. 建立 KnowledgeGenerator ---
    from knowledge_completion_loop.knowledge_generator import KnowledgeGeneratorClient

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("[generate_kb_batch] 錯誤：未設定 OPENAI_API_KEY 環境變數")
        sys.exit(1)

    db_pool = _create_db_pool(minconn=1, maxconn=5)
    cost_tracker = None  # 可選：若有 CostTracker 可在此初始化

    generator = KnowledgeGeneratorClient(
        openai_api_key=openai_api_key,
        db_pool=db_pool,
        model=os.getenv("KB_GEN_MODEL", "gpt-4o-mini"),
        cost_tracker=cost_tracker,
    )

    # --- 5. 分批生成 ---
    total_generated = 0
    total_failed = 0
    all_results: List[Dict] = []

    # tenacity 重試裝飾器：處理 API 限流
    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    async def _generate_batch(batch_gaps, batch_judgments):
        return await generator.generate_knowledge(
            loop_id=loop_id,
            gaps=batch_gaps,
            action_type_judgments=batch_judgments,
            iteration=DEFAULT_ITERATION,
            vendor_id=vendor_id,
        )

    num_batches = (len(gaps_to_generate) + batch_size - 1) // batch_size
    print(f"\n[generate_kb_batch] 開始生成（{num_batches} 批次, 每批 {batch_size} 筆）\n")

    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(gaps_to_generate))
        batch_gaps = gaps_to_generate[start:end]
        batch_judgments = build_action_type_judgments(batch_gaps)

        batch_label = f"[batch {batch_idx + 1}/{num_batches}]"
        print(f"{batch_label} 生成 {len(batch_gaps)} 筆 (#{start + 1}–#{end})...")

        t0 = time.time()
        try:
            results = await _generate_batch(batch_gaps, batch_judgments)
            elapsed = time.time() - t0
            generated_count = len(results)
            failed_count = len(batch_gaps) - generated_count
            total_generated += generated_count
            total_failed += failed_count
            all_results.extend(results)

            print(f"{batch_label} 完成: 成功 {generated_count}, "
                  f"失敗/攔截 {failed_count}, "
                  f"耗時 {elapsed:.1f}s")

        except Exception as e:
            elapsed = time.time() - t0
            total_failed += len(batch_gaps)
            print(f"{batch_label} 失敗（重試後仍出錯）: {e} ({elapsed:.1f}s)")
            logger.exception("Batch generation failed after retries")

    # --- 6. 列印摘要 ---
    print("\n" + "=" * 60)
    print("KB 批量生成結果摘要")
    print("=" * 60)
    print(f"  gap_report kb_gaps 總數:  {len(kb_gaps)}")
    print(f"  跳過（冪等）:             {len(skipped_gaps)}")
    print(f"  實際送出生成:             {len(gaps_to_generate)}")
    print(f"  成功生成:                 {total_generated}")
    print(f"  失敗/攔截:                {total_failed}")

    # 按 dimension 分組統計
    dim_stats: Dict[str, Dict[str, int]] = {}
    for result in all_results:
        # result 從 _save_to_database 回來，可能沒有 dimension
        # 嘗試從原始 gaps 反查
        gap_id = result.get("gap_id")
        original = next(
            (g for g in gaps_to_generate if g.get("gap_id") == gap_id),
            None,
        )
        dim = original["dimension"] if original else "unknown"
        if dim not in dim_stats:
            dim_stats[dim] = {"generated": 0}
        dim_stats[dim]["generated"] += 1

    if dim_stats:
        print("\n  按面向統計:")
        for dim, stats in sorted(dim_stats.items()):
            print(f"    [{dim}] 生成 {stats['generated']} 筆")

    print("=" * 60)

    # 清理
    try:
        db_pool.closeall()
    except Exception:
        pass

    return {
        "total": len(kb_gaps),
        "generated": total_generated,
        "skipped": len(skipped_gaps),
        "failed": total_failed,
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="KB 批量生成腳本 — 讀取 gap_report.json 並呼叫 KnowledgeGenerator"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="gap_report.json 檔案路徑（預設：腳本同目錄的 gap_report.json）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"每批次生成筆數（預設 {DEFAULT_BATCH_SIZE}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅顯示待生成清單，不實際呼叫 API",
    )
    parser.add_argument(
        "--loop-id",
        type=int,
        default=DEFAULT_LOOP_ID,
        help=f"loop_generated_knowledge 的 loop_id（預設 {DEFAULT_LOOP_ID}）",
    )
    parser.add_argument(
        "--vendor-id",
        type=int,
        default=DEFAULT_VENDOR_ID,
        help=f"業者 ID（預設 {DEFAULT_VENDOR_ID}）",
    )
    args = parser.parse_args()

    report_path = args.report or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "gap_report.json"
    )

    if not os.path.exists(report_path):
        print(f"[generate_kb_batch] 錯誤：找不到 {report_path}")
        sys.exit(1)

    asyncio.run(
        generate_kb_batch(
            report_path=report_path,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            loop_id=args.loop_id,
            vendor_id=args.vendor_id,
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        main()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Self-test（無 CLI 引數時執行）
    # ------------------------------------------------------------------
    import tempfile

    print("=" * 60)
    print("generate_kb_batch.py — self-test")
    print("=" * 60)

    # ----------------------------------------------------------
    # Test 1: load_gap_report 正確載入
    # ----------------------------------------------------------
    sample_report = {
        "summary": {
            "total_checklist_items": 10,
            "covered": 6,
            "missing": 3,
            "quality_poor": 1,
            "coverage_rate": 0.6,
            "by_dimension": {},
        },
        "kb_gaps": [
            {
                "checklist_id": "general-01-01",
                "question": "什麼是定期租賃契約？",
                "dimension": "general",
                "category": "租賃契約與法規",
                "reason": "missing",
            },
            {
                "checklist_id": "industry-02-01",
                "question": "包租業與代管業有什麼差別？",
                "dimension": "industry",
                "category": "包租代管制度",
                "reason": "missing",
            },
            {
                "checklist_id": "general-03-01",
                "question": "押金最多可以收幾個月？",
                "dimension": "general",
                "category": "押金規定",
                "reason": "quality_poor",
            },
        ],
        "deactivated_kb": [],
        "sop_gaps": [],
        "suggest_api_topics": [],
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sample_report, f, ensure_ascii=False, indent=2)
        tmp_report_path = f.name

    try:
        loaded = load_gap_report(tmp_report_path)
        assert "kb_gaps" in loaded
        assert len(loaded["kb_gaps"]) == 3
        print("  [PASS] load_gap_report 正確載入")
    finally:
        os.unlink(tmp_report_path)

    # ----------------------------------------------------------
    # Test 2: _dimension_to_scope 映射正確
    # ----------------------------------------------------------
    assert _dimension_to_scope("general") == "global"
    assert _dimension_to_scope("industry") == "global"
    assert _dimension_to_scope("vendor") == "vendor"
    assert _dimension_to_scope("unknown") == "global"
    print("  [PASS] _dimension_to_scope 映射正確")

    # ----------------------------------------------------------
    # Test 3: build_generator_gaps 基本轉換
    # ----------------------------------------------------------
    gaps, skipped = build_generator_gaps(
        sample_report["kb_gaps"],
        existing_pending=set(),
    )
    assert len(gaps) == 3, f"應有 3 筆，實際 {len(gaps)}"
    assert len(skipped) == 0
    # 檢查格式
    g = gaps[0]
    assert "gap_id" in g
    assert "question" in g
    assert "failure_reason" in g
    assert "priority" in g
    assert "suggested_action_type" in g
    assert "intent_name" in g
    assert "dimension" in g
    assert "scope" in g
    assert "category" in g
    assert g["suggested_action_type"] == "direct_answer"
    assert g["scope"] == "global"  # general → global
    print("  [PASS] build_generator_gaps 基本轉換正確")

    # ----------------------------------------------------------
    # Test 4: build_generator_gaps 冪等性過濾
    # ----------------------------------------------------------
    existing = {"什麼是定期租賃契約？", "押金最多可以收幾個月？"}
    gaps2, skipped2 = build_generator_gaps(
        sample_report["kb_gaps"],
        existing_pending=existing,
    )
    assert len(gaps2) == 1, f"應跳過 2 筆，僅生成 1 筆，實際 {len(gaps2)}"
    assert len(skipped2) == 2
    assert gaps2[0]["question"] == "包租業與代管業有什麼差別？"
    print("  [PASS] build_generator_gaps 冪等性過濾正確")

    # ----------------------------------------------------------
    # Test 5: build_generator_gaps gap_id 自動編號
    # ----------------------------------------------------------
    gaps3, _ = build_generator_gaps(sample_report["kb_gaps"], set())
    ids = [g["gap_id"] for g in gaps3]
    assert ids == [1, 2, 3], f"gap_id 應為 [1,2,3]，實際 {ids}"
    print("  [PASS] build_generator_gaps gap_id 自動編號")

    # ----------------------------------------------------------
    # Test 6: build_generator_gaps priority 對應 reason
    # ----------------------------------------------------------
    gaps4, _ = build_generator_gaps(sample_report["kb_gaps"], set())
    # missing → p0, quality_poor → p1
    assert gaps4[0]["priority"] == "p0"  # reason=missing
    assert gaps4[2]["priority"] == "p1"  # reason=quality_poor
    print("  [PASS] build_generator_gaps priority 對應 reason")

    # ----------------------------------------------------------
    # Test 7: build_generator_gaps scope 對應 dimension
    # ----------------------------------------------------------
    vendor_gaps_input = [
        {
            "checklist_id": "vendor-01-01",
            "question": "公司電話是什麼？",
            "dimension": "vendor",
            "category": "聯絡資訊",
            "reason": "missing",
        }
    ]
    gaps5, _ = build_generator_gaps(vendor_gaps_input, set())
    assert gaps5[0]["scope"] == "vendor"
    assert gaps5[0]["dimension"] == "vendor"
    print("  [PASS] build_generator_gaps vendor scope 正確")

    # ----------------------------------------------------------
    # Test 8: build_action_type_judgments 全部 direct_answer
    # ----------------------------------------------------------
    judgments = build_action_type_judgments(gaps3)
    assert len(judgments) == 3
    for gid, j in judgments.items():
        assert j["action_type"] == "direct_answer", \
            f"gap_id={gid} 應為 direct_answer，實際 {j['action_type']}"
    print("  [PASS] build_action_type_judgments 全部 direct_answer")

    # ----------------------------------------------------------
    # Test 9: build_generator_gaps 空 kb_gaps
    # ----------------------------------------------------------
    gaps6, skipped6 = build_generator_gaps([], set())
    assert len(gaps6) == 0
    assert len(skipped6) == 0
    print("  [PASS] build_generator_gaps 空輸入處理")

    # ----------------------------------------------------------
    # Test 10: build_generator_gaps intent_name 使用 category
    # ----------------------------------------------------------
    assert gaps3[0]["intent_name"] == "租賃契約與法規"
    assert gaps3[1]["intent_name"] == "包租代管制度"
    print("  [PASS] build_generator_gaps intent_name 使用 category")

    # ----------------------------------------------------------
    # Test 11: build_generator_gaps 缺少 dimension 時預設 general
    # ----------------------------------------------------------
    no_dim_gaps = [
        {
            "checklist_id": "x-01",
            "question": "test",
            "category": "test_cat",
            "reason": "missing",
        }
    ]
    gaps7, _ = build_generator_gaps(no_dim_gaps, set())
    assert gaps7[0]["dimension"] == "general"
    assert gaps7[0]["scope"] == "global"
    print("  [PASS] build_generator_gaps 缺少 dimension 時預設 general")

    # ----------------------------------------------------------
    # Test 12: build_action_type_judgments 空輸入
    # ----------------------------------------------------------
    assert build_action_type_judgments([]) == {}
    print("  [PASS] build_action_type_judgments 空輸入")

    # ----------------------------------------------------------
    # Test 13: dry-run generate_kb_batch
    # ----------------------------------------------------------
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sample_report, f, ensure_ascii=False, indent=2)
        tmp_path = f.name

    try:
        result = asyncio.run(generate_kb_batch(
            report_path=tmp_path,
            batch_size=5,
            dry_run=True,
        ))
        assert result["dry_run"] is True
        assert result["total"] == 3
        assert result["generated"] == 0
        assert result["skipped"] == 0
        print("  [PASS] generate_kb_batch dry-run 正確")
    finally:
        os.unlink(tmp_path)

    # ----------------------------------------------------------
    # Test 14: 空 kb_gaps 的 generate_kb_batch
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
        result2 = asyncio.run(generate_kb_batch(
            report_path=tmp_path2,
            dry_run=True,
        ))
        assert result2["total"] == 0
        assert result2["generated"] == 0
        print("  [PASS] generate_kb_batch 空 kb_gaps 處理")
    finally:
        os.unlink(tmp_path2)

    # ----------------------------------------------------------
    # Test 15: build_generator_gaps 全部被跳過
    # ----------------------------------------------------------
    all_existing = {gap["question"] for gap in sample_report["kb_gaps"]}
    gaps8, skipped8 = build_generator_gaps(sample_report["kb_gaps"], all_existing)
    assert len(gaps8) == 0
    assert len(skipped8) == 3
    print("  [PASS] build_generator_gaps 全部被冪等性跳過")

    # ----------------------------------------------------------
    # Test 16: build_generator_gaps failure_reason 映射
    # ----------------------------------------------------------
    gaps9, _ = build_generator_gaps(sample_report["kb_gaps"], set())
    assert gaps9[0]["failure_reason"] == "missing"
    assert gaps9[2]["failure_reason"] == "quality_poor"
    print("  [PASS] build_generator_gaps failure_reason 映射正確")

    # ----------------------------------------------------------
    # Test 17: DEFAULT 常數合理
    # ----------------------------------------------------------
    assert DEFAULT_BATCH_SIZE > 0
    assert DEFAULT_LOOP_ID >= 0
    assert DEFAULT_ITERATION >= 1
    assert DEFAULT_VENDOR_ID >= 1
    print("  [PASS] DEFAULT 常數合理")

    # ----------------------------------------------------------
    # Test 18: build_generator_gaps 缺少 category 時預設空字串
    # ----------------------------------------------------------
    no_cat_gaps = [
        {
            "checklist_id": "x-02",
            "question": "test2",
            "dimension": "general",
            "reason": "missing",
        }
    ]
    gaps10, _ = build_generator_gaps(no_cat_gaps, set())
    assert gaps10[0]["category"] == ""
    assert gaps10[0]["intent_name"] == "未知"  # intent_name 預設 "未知"
    print("  [PASS] build_generator_gaps 缺少 category 預設處理正確")

    # ----------------------------------------------------------
    # Test 19: build_generator_gaps 保留 checklist_id 無關
    # ----------------------------------------------------------
    # generator gap 不需要 checklist_id（由 gap_id 取代）
    assert "checklist_id" not in gaps3[0]
    print("  [PASS] build_generator_gaps 不含 checklist_id")

    # ----------------------------------------------------------
    # Test 20: load_gap_report 處理大量缺口
    # ----------------------------------------------------------
    large_report = {
        "summary": {},
        "kb_gaps": [
            {
                "checklist_id": f"g-{i:03d}",
                "question": f"問題 {i}",
                "dimension": "general",
                "category": "測試",
                "reason": "missing",
            }
            for i in range(200)
        ],
        "deactivated_kb": [],
        "sop_gaps": [],
        "suggest_api_topics": [],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(large_report, f, ensure_ascii=False, indent=2)
        tmp_large = f.name

    try:
        loaded_large = load_gap_report(tmp_large)
        assert len(loaded_large["kb_gaps"]) == 200
        gaps_large, _ = build_generator_gaps(loaded_large["kb_gaps"], set())
        assert len(gaps_large) == 200
        print("  [PASS] 200 筆缺口批次轉換正確")
    finally:
        os.unlink(tmp_large)

    print("=" * 60)
    print("All generate_kb_batch.py self-tests passed!")
    print("=" * 60)
