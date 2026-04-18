"""
KB 缺口分析腳本

比對已核准的知識清單與現有 KB/SOP，識別：
  - 尚未覆蓋的知識缺口（kb_gaps）
  - 品質不佳需重新生成的 KB（deactivated_kb）
  - SOP 缺口（sop_gaps）
  - 建議未來串接 API 的子題（suggest_api_topics）

產出：
  - gap_report.json  — 主報告（含三面向覆蓋率統計）
  - sop_gap_report.json — SOP 缺口清單

使用方式：
  python3 scripts/kb_coverage/analyze_gaps.py \\
      --checklists checklist_general.json checklist_industry.json \\
      --output-dir scripts/kb_coverage/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, TypedDict

import numpy as np

# ---------------------------------------------------------------------------
# Path setup — allow importing from rag-orchestrator
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../rag-orchestrator/services"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 閾值常數
# ---------------------------------------------------------------------------
KB_COVERAGE_THRESHOLD = 0.80   # cosine similarity >= 此值視為「已覆蓋」
SOP_OVERLAP_THRESHOLD = 0.85   # cosine similarity >= 此值視為 SOP 重疊
QUALITY_MIN_LENGTH = 50        # answer 長度 < 此值視為品質不佳

# 品質檢查：行話關鍵字
_JARGON_KEYWORDS: List[str] = [
    "SOP", "流程規範", "作業程序", "內部規範", "管理師操作",
    "後台", "backend", "API", "endpoint",
]

# 品質檢查：空洞回答模式
_HOLLOW_ANSWER_PATTERNS: List[str] = [
    "請洽管理師",
    "請聯繫管理師",
    "請洽客服",
    "請聯繫客服",
    "詳情請洽",
]


# ---------------------------------------------------------------------------
# 資料結構（TypedDict）
# ---------------------------------------------------------------------------
class GapSummary(TypedDict):
    total_checklist_items: int
    covered: int
    missing: int
    quality_poor: int
    coverage_rate: float
    by_dimension: Dict[str, Dict[str, Any]]


class KBGapItem(TypedDict):
    checklist_id: str
    question: str
    dimension: str
    category: str
    reason: str  # "missing" | "quality_poor"


class DeactivatedKB(TypedDict):
    kb_id: int
    question_summary: str
    reason: str  # "overlap_with_sop" | "quality_poor"
    detail: str


class SOPGapItem(TypedDict):
    checklist_id: str
    question: str
    dimension: str
    category: str
    reason: str


class SuggestAPIItem(TypedDict):
    checklist_id: str
    question: str
    suggest_api: str


class GapReport(TypedDict):
    summary: GapSummary
    kb_gaps: List[KBGapItem]
    deactivated_kb: List[DeactivatedKB]
    sop_gaps: List[SOPGapItem]
    suggest_api_topics: List[SuggestAPIItem]


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


def load_kb_entries(conn) -> List[Dict[str, Any]]:
    """讀取所有 is_active=true 的 knowledge_base 項目（含 embedding）。"""
    import psycopg2.extras

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, question_summary, answer, embedding::text,
                   scope, category, is_active, keywords
            FROM knowledge_base
            WHERE is_active = true
        """)
        rows = cur.fetchall()

    results = []
    for row in rows:
        entry = dict(row)
        # 解析 embedding 字串為 numpy array
        emb_str = entry.pop("embedding", None)
        if emb_str:
            try:
                # pgvector 格式: '[0.1,0.2,...,0.3]'
                entry["embedding"] = np.array(
                    json.loads(emb_str), dtype=np.float32
                )
            except Exception:
                entry["embedding"] = None
        else:
            entry["embedding"] = None
        results.append(entry)

    return results


def load_sop_items(conn) -> List[Dict[str, Any]]:
    """讀取 vendor_sop_items 的 item_name 欄位。"""
    import psycopg2.extras

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, item_name FROM vendor_sop_items")
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Embedding 生成（使用 EmbeddingClient）
# ---------------------------------------------------------------------------
async def generate_embedding_for_text(
    text: str,
    client=None,
) -> Optional[np.ndarray]:
    """為單筆文字生成 embedding，失敗回傳 None。"""
    from tenacity import retry, stop_after_attempt, wait_exponential

    if client is None:
        from embedding_utils import EmbeddingClient
        client = EmbeddingClient()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def _call():
        return await client.get_embedding(text)

    try:
        emb = await _call()
        if emb is not None:
            return np.array(emb, dtype=np.float32)
        return None
    except Exception as e:
        logger.warning(f"Embedding 生成失敗: {text[:40]}... — {e}")
        return None


async def batch_generate_embeddings(
    texts: List[str],
    client=None,
    concurrency: int = 5,
) -> List[Optional[np.ndarray]]:
    """批量生成 embeddings，控制並發數。"""
    if client is None:
        from embedding_utils import EmbeddingClient
        client = EmbeddingClient()

    semaphore = asyncio.Semaphore(concurrency)
    results: List[Optional[np.ndarray]] = [None] * len(texts)

    async def _worker(idx: int, text: str):
        async with semaphore:
            results[idx] = await generate_embedding_for_text(text, client)

    tasks = [_worker(i, t) for i, t in enumerate(texts)]
    await asyncio.gather(*tasks)
    return results


# ---------------------------------------------------------------------------
# Cosine Similarity
# ---------------------------------------------------------------------------
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """計算兩向量的 cosine similarity。"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_best_match(
    query_emb: np.ndarray,
    candidates: List[Dict[str, Any]],
    emb_key: str = "embedding",
) -> tuple[float, Optional[Dict[str, Any]]]:
    """在候選清單中找到與 query_emb 最相似的項目。"""
    best_score = 0.0
    best_item = None
    for cand in candidates:
        cand_emb = cand.get(emb_key)
        if cand_emb is None:
            continue
        score = cosine_similarity(query_emb, cand_emb)
        if score > best_score:
            best_score = score
            best_item = cand
    return best_score, best_item


# ---------------------------------------------------------------------------
# 品質檢查
# ---------------------------------------------------------------------------
def check_kb_quality(kb_entry: Dict[str, Any]) -> Optional[str]:
    """
    檢查 KB 項目品質，回傳失敗原因或 None（品質合格）。

    檢查項目：
      1. answer 長度 < 50 字
      2. 僅含「請洽管理師」類空洞回答
      3. 含行話（面向客服人員的術語）
    """
    answer = kb_entry.get("answer") or ""

    # 1. 長度不足
    if len(answer.strip()) < QUALITY_MIN_LENGTH:
        return f"answer 長度不足（{len(answer.strip())} 字 < {QUALITY_MIN_LENGTH}）"

    # 2. 空洞回答
    answer_stripped = answer.strip()
    for pattern in _HOLLOW_ANSWER_PATTERNS:
        if pattern in answer_stripped:
            # 如果整段回答扣除這個 pattern 後所剩無幾，才判定為空洞
            remaining = answer_stripped.replace(pattern, "").strip()
            # 去除標點後若 < 20 字，視為空洞
            remaining_clean = remaining.replace("，", "").replace("。", "").replace("、", "").strip()
            if len(remaining_clean) < 20:
                return f"空洞回答（僅含「{pattern}」）"

    # 3. 行話
    for jargon in _JARGON_KEYWORDS:
        if jargon in answer:
            return f"含行話「{jargon}」"

    return None


# ---------------------------------------------------------------------------
# SOP 缺口偵測
# ---------------------------------------------------------------------------
def is_operational_topic(question: str) -> bool:
    """判斷問題是否屬於操作流程性質（可能應歸 SOP）。"""
    from boundary_classifier import classify_knowledge_type
    return classify_knowledge_type(question) == "sop"


# ---------------------------------------------------------------------------
# 清單載入與驗證
# ---------------------------------------------------------------------------
def load_checklist(filepath: str) -> Dict[str, Any]:
    """載入並驗證清單 JSON 檔案。"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("status") != "approved":
        raise ValueError(
            f"清單 {filepath} 的 status 為 '{data.get('status')}'，"
            f"必須為 'approved' 才能進行缺口分析。"
            f"請先人工審閱清單並將 status 改為 'approved'。"
        )

    return data


# ---------------------------------------------------------------------------
# 主分析流程
# ---------------------------------------------------------------------------
async def analyze_gaps(
    checklist_paths: List[str],
    output_dir: str,
    dry_run: bool = False,
) -> GapReport:
    """
    執行缺口分析主流程。

    Parameters
    ----------
    checklist_paths : List[str]
        已核准清單 JSON 的檔案路徑
    output_dir : str
        報告輸出目錄
    dry_run : bool
        若為 True，不連線 DB，使用空資料（測試用）

    Returns
    -------
    GapReport
    """
    from embedding_utils import EmbeddingClient

    # --- 1. 載入所有清單 ---
    all_items: List[Dict[str, Any]] = []
    for path in checklist_paths:
        print(f"[analyze_gaps] 載入清單: {path}")
        checklist = load_checklist(path)
        dimension = checklist.get("dimension", "unknown")
        for item in checklist.get("items", []):
            item["_dimension"] = dimension
            all_items.append(item)
    print(f"[analyze_gaps] 清單子題總數: {len(all_items)}")

    # --- 2. 載入現有 KB 與 SOP ---
    if dry_run:
        kb_entries: List[Dict[str, Any]] = []
        sop_items: List[Dict[str, Any]] = []
    else:
        conn = _get_db_connection()
        try:
            print("[analyze_gaps] 載入現有 KB...")
            kb_entries = load_kb_entries(conn)
            print(f"  現有 KB: {len(kb_entries)} 筆（is_active=true）")

            print("[analyze_gaps] 載入 SOP items...")
            sop_items = load_sop_items(conn)
            print(f"  SOP items: {len(sop_items)} 筆")
        finally:
            conn.close()

    # --- 3. 為清單子題生成 embeddings ---
    print("[analyze_gaps] 生成清單子題 embeddings...")
    embedding_client = EmbeddingClient()
    checklist_texts = [item.get("question", "") for item in all_items]

    embeddings = await batch_generate_embeddings(
        checklist_texts, embedding_client, concurrency=5,
    )

    emb_success = sum(1 for e in embeddings if e is not None)
    print(f"  Embedding 成功: {emb_success}/{len(all_items)}")

    # --- 4. 為 SOP items 生成 embeddings ---
    if sop_items:
        print("[analyze_gaps] 生成 SOP item_name embeddings...")
        sop_texts = [s.get("item_name", "") for s in sop_items]
        sop_embeddings = await batch_generate_embeddings(
            sop_texts, embedding_client, concurrency=5,
        )
        for i, emb in enumerate(sop_embeddings):
            sop_items[i]["embedding"] = emb
        sop_emb_success = sum(1 for e in sop_embeddings if e is not None)
        print(f"  SOP embedding 成功: {sop_emb_success}/{len(sop_items)}")

    # --- 5. 逐筆比對 ---
    print("[analyze_gaps] 執行缺口比對...")

    kb_gaps: List[KBGapItem] = []
    deactivated_kb: List[DeactivatedKB] = []
    sop_gaps: List[SOPGapItem] = []
    suggest_api_topics: List[SuggestAPIItem] = []

    # 追蹤已標記品質不佳的 KB ID（避免重複）
    flagged_kb_ids: set = set()
    # 追蹤各面向統計
    dim_stats: Dict[str, Dict[str, int]] = {}

    for idx, item in enumerate(all_items):
        item_id = item.get("id", f"unknown-{idx}")
        question = item.get("question", "")
        dimension = item.get("_dimension", item.get("dimension", "unknown"))
        category = item.get("category", "")
        suggest_api = item.get("suggest_api")

        # 初始化面向統計
        if dimension not in dim_stats:
            dim_stats[dimension] = {
                "total": 0, "covered": 0, "missing": 0, "quality_poor": 0,
            }
        dim_stats[dimension]["total"] += 1

        # 收集 suggest_api 子題
        if suggest_api:
            suggest_api_topics.append(SuggestAPIItem(
                checklist_id=item_id,
                question=question,
                suggest_api=suggest_api,
            ))

        query_emb = embeddings[idx]

        # 若 embedding 生成失敗，標記為 missing（unknown）
        if query_emb is None:
            kb_gaps.append(KBGapItem(
                checklist_id=item_id,
                question=question,
                dimension=dimension,
                category=category,
                reason="missing",
            ))
            dim_stats[dimension]["missing"] += 1
            continue

        # --- 5a. 與現有 KB 比對 ---
        best_kb_score, best_kb = find_best_match(query_emb, kb_entries)
        is_covered = best_kb_score >= KB_COVERAGE_THRESHOLD

        if is_covered and best_kb is not None:
            # 檢查匹配到的 KB 品質
            quality_issue = check_kb_quality(best_kb)
            if quality_issue:
                # 品質不佳 → 列入 deactivated_kb + kb_gaps
                kb_id = best_kb.get("id", 0)
                if kb_id not in flagged_kb_ids:
                    flagged_kb_ids.add(kb_id)
                    deactivated_kb.append(DeactivatedKB(
                        kb_id=kb_id,
                        question_summary=best_kb.get("question_summary", ""),
                        reason="quality_poor",
                        detail=quality_issue,
                    ))
                kb_gaps.append(KBGapItem(
                    checklist_id=item_id,
                    question=question,
                    dimension=dimension,
                    category=category,
                    reason="quality_poor",
                ))
                dim_stats[dimension]["quality_poor"] += 1
            else:
                dim_stats[dimension]["covered"] += 1

            # --- 5b. 檢查 SOP 重疊（已覆蓋的 KB 也要檢查） ---
            if sop_items:
                sop_score, sop_match = find_best_match(query_emb, sop_items)
                if sop_score >= SOP_OVERLAP_THRESHOLD and sop_match and best_kb is not None:
                    # 純重疊：KB 與 SOP 說一樣的事 → 建議停用 KB
                    kb_id = best_kb.get("id", 0)
                    if kb_id not in flagged_kb_ids:
                        flagged_kb_ids.add(kb_id)
                        deactivated_kb.append(DeactivatedKB(
                            kb_id=kb_id,
                            question_summary=best_kb.get("question_summary", ""),
                            reason="overlap_with_sop",
                            detail=f"與 SOP item '{sop_match.get('item_name', '')}' 重疊 (score={sop_score:.3f})",
                        ))
        else:
            # 未覆蓋
            kb_gaps.append(KBGapItem(
                checklist_id=item_id,
                question=question,
                dimension=dimension,
                category=category,
                reason="missing",
            ))
            dim_stats[dimension]["missing"] += 1

            # --- 5c. 檢查是否屬於操作流程但 SOP 未涵蓋 ---
            if is_operational_topic(question):
                # 檢查 SOP 是否已涵蓋
                sop_covered = False
                if sop_items:
                    sop_score, _ = find_best_match(query_emb, sop_items)
                    sop_covered = sop_score >= SOP_OVERLAP_THRESHOLD

                if not sop_covered:
                    sop_gaps.append(SOPGapItem(
                        checklist_id=item_id,
                        question=question,
                        dimension=dimension,
                        category=category,
                        reason="operational_topic_not_in_sop",
                    ))

    # --- 6. 額外掃描現有 KB 品質 ---
    print("[analyze_gaps] 掃描現有 KB 品質...")
    for kb in kb_entries:
        kb_id = kb.get("id", 0)
        if kb_id in flagged_kb_ids:
            continue
        quality_issue = check_kb_quality(kb)
        if quality_issue:
            flagged_kb_ids.add(kb_id)
            deactivated_kb.append(DeactivatedKB(
                kb_id=kb_id,
                question_summary=kb.get("question_summary", ""),
                reason="quality_poor",
                detail=quality_issue,
            ))

    # --- 7. 彙整統計 ---
    total = sum(d["total"] for d in dim_stats.values())
    covered = sum(d["covered"] for d in dim_stats.values())
    missing = sum(d["missing"] for d in dim_stats.values())
    quality_poor = sum(d["quality_poor"] for d in dim_stats.values())

    by_dimension: Dict[str, Dict[str, Any]] = {}
    for dim, stats in dim_stats.items():
        dim_total = stats["total"]
        dim_covered = stats["covered"]
        by_dimension[dim] = {
            "total": dim_total,
            "covered": dim_covered,
            "missing": stats["missing"],
            "quality_poor": stats["quality_poor"],
            "coverage_rate": round(dim_covered / dim_total, 4) if dim_total > 0 else 0.0,
        }

    summary = GapSummary(
        total_checklist_items=total,
        covered=covered,
        missing=missing,
        quality_poor=quality_poor,
        coverage_rate=round(covered / total, 4) if total > 0 else 0.0,
        by_dimension=by_dimension,
    )

    report = GapReport(
        summary=summary,
        kb_gaps=kb_gaps,
        deactivated_kb=deactivated_kb,
        sop_gaps=sop_gaps,
        suggest_api_topics=suggest_api_topics,
    )

    # --- 8. 寫入報告 ---
    os.makedirs(output_dir, exist_ok=True)

    gap_report_path = os.path.join(output_dir, "gap_report.json")
    with open(gap_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[analyze_gaps] 寫入: {gap_report_path}")

    # SOP 缺口報告
    sop_report = {
        "total_sop_gaps": len(sop_gaps),
        "items": sop_gaps,
    }
    sop_report_path = os.path.join(output_dir, "sop_gap_report.json")
    with open(sop_report_path, "w", encoding="utf-8") as f:
        json.dump(sop_report, f, ensure_ascii=False, indent=2)
    print(f"[analyze_gaps] 寫入: {sop_report_path}")

    # --- 9. 列印摘要 ---
    print("\n" + "=" * 60)
    print("缺口分析結果摘要")
    print("=" * 60)
    print(f"  清單子題總數:     {total}")
    print(f"  已覆蓋:           {covered} ({summary['coverage_rate']:.1%})")
    print(f"  缺口（missing）:  {missing}")
    print(f"  品質不佳:         {quality_poor}")
    print(f"  KB 缺口清單:      {len(kb_gaps)} 筆")
    print(f"  建議停用 KB:      {len(deactivated_kb)} 筆")
    print(f"  SOP 缺口:         {len(sop_gaps)} 筆")
    print(f"  建議 API 子題:    {len(suggest_api_topics)} 筆")
    print()
    for dim, stats in by_dimension.items():
        print(f"  [{dim}] {stats['covered']}/{stats['total']} "
              f"({stats['coverage_rate']:.1%})")
    print("=" * 60)

    return report


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="KB 缺口分析腳本 — 比對知識清單與現有 KB/SOP"
    )
    parser.add_argument(
        "--checklists",
        nargs="+",
        required=True,
        help="已核准清單 JSON 檔案路徑（可多個）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="報告輸出目錄（預設：腳本所在目錄）",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(__file__))

    asyncio.run(analyze_gaps(args.checklists, output_dir))


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
    print("analyze_gaps.py — self-test")
    print("=" * 60)

    # ----------------------------------------------------------
    # Test 1: GapReport 資料結構完整性
    # ----------------------------------------------------------
    sample_report = GapReport(
        summary=GapSummary(
            total_checklist_items=10,
            covered=6,
            missing=3,
            quality_poor=1,
            coverage_rate=0.6,
            by_dimension={
                "general": {"total": 7, "covered": 5, "missing": 2, "quality_poor": 0, "coverage_rate": 0.7143},
                "industry": {"total": 3, "covered": 1, "missing": 1, "quality_poor": 1, "coverage_rate": 0.3333},
            },
        ),
        kb_gaps=[
            KBGapItem(checklist_id="general-01-01", question="q1", dimension="general", category="cat1", reason="missing"),
        ],
        deactivated_kb=[
            DeactivatedKB(kb_id=1, question_summary="qs1", reason="quality_poor", detail="answer 長度不足"),
        ],
        sop_gaps=[
            SOPGapItem(checklist_id="general-02-01", question="q2", dimension="general", category="cat2", reason="operational_topic_not_in_sop"),
        ],
        suggest_api_topics=[
            SuggestAPIItem(checklist_id="industry-02-01", question="q3", suggest_api="管理費金額查詢"),
        ],
    )
    assert "summary" in sample_report
    assert "kb_gaps" in sample_report
    assert "deactivated_kb" in sample_report
    assert "sop_gaps" in sample_report
    assert "suggest_api_topics" in sample_report
    assert sample_report["summary"]["total_checklist_items"] == 10
    print("  [PASS] GapReport 資料結構完整")

    # ----------------------------------------------------------
    # Test 2: cosine_similarity 計算正確
    # ----------------------------------------------------------
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-6, "相同向量應為 1.0"

    c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert abs(cosine_similarity(a, c) - 0.0) < 1e-6, "正交向量應為 0.0"

    d = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    assert abs(cosine_similarity(a, d) - (-1.0)) < 1e-6, "反向向量應為 -1.0"

    # 零向量
    z = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, z) == 0.0, "零向量應回傳 0.0"
    print("  [PASS] cosine_similarity 計算正確")

    # ----------------------------------------------------------
    # Test 3: find_best_match 找到最佳匹配
    # ----------------------------------------------------------
    candidates = [
        {"id": 1, "embedding": np.array([1.0, 0.0, 0.0], dtype=np.float32)},
        {"id": 2, "embedding": np.array([0.0, 1.0, 0.0], dtype=np.float32)},
        {"id": 3, "embedding": np.array([0.7, 0.7, 0.0], dtype=np.float32)},
    ]
    query = np.array([0.8, 0.6, 0.0], dtype=np.float32)
    score, best = find_best_match(query, candidates)
    assert best is not None
    assert best["id"] == 3, f"應匹配 id=3，實際 id={best['id']}"
    assert score > 0.9, f"分數應 > 0.9，實際 {score:.4f}"
    print("  [PASS] find_best_match 正確匹配")

    # ----------------------------------------------------------
    # Test 4: find_best_match 處理空候選
    # ----------------------------------------------------------
    score_empty, best_empty = find_best_match(query, [])
    assert score_empty == 0.0
    assert best_empty is None
    print("  [PASS] find_best_match 處理空候選")

    # ----------------------------------------------------------
    # Test 5: find_best_match 處理 None embedding
    # ----------------------------------------------------------
    none_candidates = [
        {"id": 1, "embedding": None},
        {"id": 2, "embedding": None},
    ]
    score_none, best_none = find_best_match(query, none_candidates)
    assert score_none == 0.0
    assert best_none is None
    print("  [PASS] find_best_match 處理 None embedding")

    # ----------------------------------------------------------
    # Test 6: check_kb_quality — 長度不足
    # ----------------------------------------------------------
    short_kb = {"answer": "請洽管理師"}
    result = check_kb_quality(short_kb)
    assert result is not None
    assert "長度不足" in result
    print(f"  [PASS] check_kb_quality 偵測長度不足: {result}")

    # ----------------------------------------------------------
    # Test 7: check_kb_quality — 空洞回答
    # ----------------------------------------------------------
    hollow_kb = {"answer": "關於您的問題，請洽管理師。" + "　" * 30}
    result2 = check_kb_quality(hollow_kb)
    assert result2 is not None
    # 可能是長度不足或空洞回答
    assert "長度不足" in result2 or "空洞" in result2 or "請洽管理師" in result2
    print(f"  [PASS] check_kb_quality 偵測空洞/過短回答: {result2}")

    # 額外測試：長度足夠但仍空洞（扣除 pattern 和標點後 < 20 字）
    hollow_kb2 = {"answer": "這個問題，請洽管理師。" + "。" * 50}
    assert len(hollow_kb2["answer"].strip()) >= QUALITY_MIN_LENGTH, "測試前提：長度需 >= 50"
    result2b = check_kb_quality(hollow_kb2)
    assert result2b is not None
    assert "空洞" in result2b or "請洽管理師" in result2b
    print(f"  [PASS] check_kb_quality 偵測空洞回答（長度足夠）: {result2b}")

    # ----------------------------------------------------------
    # Test 8: check_kb_quality — 含行話
    # ----------------------------------------------------------
    jargon_kb = {"answer": "根據我們的 SOP 作業程序，管理師需要先在後台系統確認租客身份，然後依照流程規範進行處理，這是為了確保服務品質。" * 2}
    result3 = check_kb_quality(jargon_kb)
    assert result3 is not None
    assert "行話" in result3
    print(f"  [PASS] check_kb_quality 偵測行話: {result3}")

    # ----------------------------------------------------------
    # Test 9: check_kb_quality — 合格
    # ----------------------------------------------------------
    good_kb = {"answer": "押金（又稱保證金）是租賃契約中租客預先支付給房東的款項，用來保障房東在租約期間可能產生的損害或欠繳租金。依據《租賃住宅市場發展及管理條例》規定，押金不得超過兩個月租金。租約終止後，房東應在合理期限內返還押金，扣除損壞修繕費用及未繳清費用後退還餘額。"}
    result4 = check_kb_quality(good_kb)
    assert result4 is None, f"合格 KB 應回傳 None，實際: {result4}"
    print("  [PASS] check_kb_quality 合格 KB 通過")

    # ----------------------------------------------------------
    # Test 10: check_kb_quality — 空 answer
    # ----------------------------------------------------------
    empty_kb: Dict[str, Any] = {"answer": ""}
    result5 = check_kb_quality(empty_kb)
    assert result5 is not None
    print(f"  [PASS] check_kb_quality 空 answer: {result5}")

    # ----------------------------------------------------------
    # Test 11: check_kb_quality — None answer
    # ----------------------------------------------------------
    none_kb: Dict[str, Any] = {"answer": None}
    result6 = check_kb_quality(none_kb)
    assert result6 is not None
    print(f"  [PASS] check_kb_quality None answer: {result6}")

    # ----------------------------------------------------------
    # Test 12: load_checklist 拒絕非 approved
    # ----------------------------------------------------------
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({"status": "draft", "dimension": "general", "categories": [], "items": []}, f)
        draft_path = f.name

    try:
        load_checklist(draft_path)
        assert False, "應拒絕 status=draft"
    except ValueError as e:
        assert "approved" in str(e)
        print(f"  [PASS] load_checklist 拒絕非 approved: {e}")
    finally:
        os.unlink(draft_path)

    # ----------------------------------------------------------
    # Test 13: load_checklist 接受 approved
    # ----------------------------------------------------------
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({
            "status": "approved",
            "dimension": "general",
            "categories": [],
            "items": [{"id": "g-01-01", "question": "test"}],
        }, f)
        approved_path = f.name

    try:
        data = load_checklist(approved_path)
        assert data["status"] == "approved"
        assert len(data["items"]) == 1
        print("  [PASS] load_checklist 接受 approved")
    finally:
        os.unlink(approved_path)

    # ----------------------------------------------------------
    # Test 14: 閾值常數正確
    # ----------------------------------------------------------
    assert KB_COVERAGE_THRESHOLD == 0.80, f"KB 閾值應為 0.80，實際 {KB_COVERAGE_THRESHOLD}"
    assert SOP_OVERLAP_THRESHOLD == 0.85, f"SOP 閾值應為 0.85，實際 {SOP_OVERLAP_THRESHOLD}"
    assert QUALITY_MIN_LENGTH == 50, f"品質最低字數應為 50，實際 {QUALITY_MIN_LENGTH}"
    print("  [PASS] 閾值常數正確")

    # ----------------------------------------------------------
    # Test 15: GapReport 包含所有必要欄位
    # ----------------------------------------------------------
    required_keys = {"summary", "kb_gaps", "deactivated_kb", "sop_gaps", "suggest_api_topics"}
    assert required_keys == set(sample_report.keys()), \
        f"GapReport keys 不符: {set(sample_report.keys())} != {required_keys}"
    print("  [PASS] GapReport 包含所有必要欄位")

    # ----------------------------------------------------------
    # Test 16: GapSummary 包含 by_dimension
    # ----------------------------------------------------------
    assert "by_dimension" in sample_report["summary"]
    assert "general" in sample_report["summary"]["by_dimension"]
    assert "coverage_rate" in sample_report["summary"]["by_dimension"]["general"]
    print("  [PASS] GapSummary 包含 by_dimension 面向統計")

    # ----------------------------------------------------------
    # Test 17: SuggestAPIItem 結構正確
    # ----------------------------------------------------------
    api_item = sample_report["suggest_api_topics"][0]
    assert "checklist_id" in api_item
    assert "question" in api_item
    assert "suggest_api" in api_item
    print("  [PASS] SuggestAPIItem 結構正確")

    # ----------------------------------------------------------
    # Test 18: _JARGON_KEYWORDS 與 _HOLLOW_ANSWER_PATTERNS 非空
    # ----------------------------------------------------------
    assert len(_JARGON_KEYWORDS) >= 5, f"行話關鍵字應至少 5 個，實際 {len(_JARGON_KEYWORDS)}"
    assert len(_HOLLOW_ANSWER_PATTERNS) >= 3, f"空洞回答模式應至少 3 個，實際 {len(_HOLLOW_ANSWER_PATTERNS)}"
    print("  [PASS] 品質檢查常數非空")

    # ----------------------------------------------------------
    # Test 19: DeactivatedKB 結構正確
    # ----------------------------------------------------------
    deact = sample_report["deactivated_kb"][0]
    assert "kb_id" in deact
    assert "question_summary" in deact
    assert "reason" in deact
    assert "detail" in deact
    assert deact["reason"] in ("quality_poor", "overlap_with_sop")
    print("  [PASS] DeactivatedKB 結構正確")

    # ----------------------------------------------------------
    # Test 20: SOPGapItem 結構正確
    # ----------------------------------------------------------
    sop_gap = sample_report["sop_gaps"][0]
    assert "checklist_id" in sop_gap
    assert "question" in sop_gap
    assert "dimension" in sop_gap
    assert "category" in sop_gap
    assert "reason" in sop_gap
    print("  [PASS] SOPGapItem 結構正確")

    print("=" * 60)
    print("All analyze_gaps.py self-tests passed!")
    print("=" * 60)
