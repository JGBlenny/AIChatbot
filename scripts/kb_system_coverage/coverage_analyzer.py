"""
CoverageAnalyzer — 覆蓋率比對與缺口報告

讀取操作問題清單，對每個問題用 embedding similarity 比對現有
knowledge_base 和 vendor_sop_items，產出覆蓋率報告。

覆蓋狀態判定閥值：
  - >= similarity_threshold (0.6): covered
  - >= partial_threshold (0.4): partial_covered
  - < partial_threshold: uncovered

品質檢查規則（Req 3.4）：
  - 內容 < 50 字 → needs_improvement
  - 內容僅「請洽管理師」→ needs_improvement

建議邏輯（Req 3.5）：
  - needs_improvement → improve_existing
  - SOP 信號（流程/步驟/操作/申請/怎麼做…）→ add_sop
  - 其他 → add_kb
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from .models import (
    CoverageReport,
    GapItem,
    ModuleCoverage,
    RoleCoverage,
    SimilarItem,
    SystemQuestion,
)

# ---------------------------------------------------------------------------
# SOP / KB 信號關鍵字（自 boundary_classifier.py 參考，不直接 import）
# ---------------------------------------------------------------------------

_SOP_SIGNALS: List[str] = [
    "流程", "步驟", "操作", "申請", "辦理", "執行",
    "提交", "填寫", "上傳", "送出", "簽署",
    "表單", "系統操作", "線上申請", "掃碼", "刷卡",
    "怎麼做", "如何操作", "如何申請", "如何辦理", "如何繳費",
    "如何報修", "如何退租", "如何搬入", "如何搬出",
]

_KB_SIGNALS: List[str] = [
    "是什麼", "為什麼", "什麼是", "定義", "規定", "說明",
    "差異", "比較", "區別", "上限", "下限", "條件",
    "權益", "責任", "歸屬", "原則", "標準", "資格",
    "查詢", "多少錢", "金額", "費用", "行情", "明細",
]


class CoverageAnalyzer:
    """比對問題清單與現有 KB/SOP，識別覆蓋缺口。"""

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        partial_threshold: float = 0.4,
    ):
        self.similarity_threshold = similarity_threshold
        self.partial_threshold = partial_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        questions: List[SystemQuestion],
        kb_items: List[dict],
        sop_items: List[dict],
    ) -> CoverageReport:
        """主分析流程：比對問題與 KB/SOP，產出覆蓋率報告。

        Parameters
        ----------
        questions : 操作問題清單
        kb_items : 現有 KB 項目，每筆含 id, question_summary, answer, embedding(optional)
        sop_items : 現有 SOP 項目，每筆含 id, title, content, embedding(optional)
        """
        report = CoverageReport()

        if not questions:
            return report

        # 1. 取得所有問題的 embeddings
        client = self._get_embedding_client()
        question_texts = [q.question for q in questions]
        question_embeddings = await client.get_embeddings_batch(question_texts)

        # 2. 確保 KB/SOP items 都有 embeddings
        kb_embeddings = await self._ensure_embeddings(kb_items, "kb", client)
        sop_embeddings = await self._ensure_embeddings(sop_items, "sop", client)

        # 3. 逐題比對
        report.total_questions = len(questions)

        for i, question in enumerate(questions):
            q_emb = question_embeddings[i]
            if q_emb is None:
                # Embedding 失敗，標記為 uncovered
                self._record_uncovered(report, question, [])
                continue

            # 比對 KB
            best_kb = self._find_best_match(q_emb, kb_items, kb_embeddings, "kb")
            # 比對 SOP
            best_sop = self._find_best_match(q_emb, sop_items, sop_embeddings, "sop")

            # 合併所有相似項
            all_similar = []
            if best_kb:
                all_similar.append(best_kb)
            if best_sop:
                all_similar.append(best_sop)

            # 取最高相似度
            best_similarity = max(
                (s.similarity for s in all_similar), default=0.0
            )
            best_source = max(all_similar, key=lambda s: s.similarity) if all_similar else None

            # 判定覆蓋狀態
            if best_similarity >= self.similarity_threshold:
                # 高相似度：先檢查品質
                content = self._get_content(
                    best_source, kb_items, sop_items
                ) if best_source else ""
                if not self._check_quality(content):
                    self._record_needs_improvement(report, question, all_similar)
                elif best_source and best_source.source_type == "kb":
                    report.covered_by_kb += 1
                    self._update_module_role_stats(report, question, "covered_by_kb")
                else:
                    report.covered_by_sop += 1
                    self._update_module_role_stats(report, question, "covered_by_sop")
            elif best_similarity >= self.partial_threshold:
                self._record_partial(report, question, all_similar)
            else:
                self._record_uncovered(report, question, all_similar)

        return report

    def export_report(self, report: CoverageReport, output_path: Path) -> None:
        """將報告匯出為 JSON 檔案。"""
        data = self._report_to_dict(report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Quality & Recommendation Logic
    # ------------------------------------------------------------------

    def _check_quality(self, content: str) -> bool:
        """檢查內容品質。Returns False if poor quality.

        Rules (Req 3.4):
        - 空內容 → False
        - 內容 < 50 字 → False
        - 內容僅為「請洽管理師」→ False
        """
        if not content:
            return False
        stripped = content.strip()
        if len(stripped) < 50:
            return False
        if stripped == "請洽管理師":
            return False
        return True

    def _recommend(self, gap_type: str, question: SystemQuestion) -> str:
        """依缺口類型與問題特徵判定建議。

        Rules (Req 3.5):
        - needs_improvement → improve_existing
        - SOP 信號分數 > KB 信號分數 → add_sop
        - 其他 → add_kb
        """
        if gap_type == "needs_improvement":
            return "improve_existing"

        text = question.question
        sop_score = sum(1 for kw in _SOP_SIGNALS if kw in text)
        kb_score = sum(1 for kw in _KB_SIGNALS if kw in text)

        if sop_score > kb_score:
            return "add_sop"
        return "add_kb"

    # ------------------------------------------------------------------
    # Cosine Similarity
    # ------------------------------------------------------------------

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """計算兩向量的 cosine similarity。"""
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_embedding_client(self):
        """取得 EmbeddingClient（供 mock 用）。"""
        from services.embedding_utils import EmbeddingClient
        return EmbeddingClient()

    async def _ensure_embeddings(
        self,
        items: List[dict],
        source_type: str,
        client: Any,
    ) -> List[Optional[List[float]]]:
        """確保每個項目都有 embedding。如果沒有，透過 client 生成。"""
        embeddings: List[Optional[List[float]]] = []
        needs_generation: List[int] = []
        texts: List[str] = []

        for i, item in enumerate(items):
            if item.get("embedding") is not None:
                embeddings.append(item["embedding"])
            else:
                embeddings.append(None)
                needs_generation.append(i)
                if source_type == "kb":
                    texts.append(item.get("question_summary", "") + " " + item.get("answer", ""))
                else:
                    texts.append(item.get("title", "") + " " + item.get("content", ""))

        if texts:
            generated = await client.get_embeddings_batch(texts)
            for idx, gen_idx in enumerate(needs_generation):
                if idx < len(generated):
                    embeddings[gen_idx] = generated[idx]

        return embeddings

    def _find_best_match(
        self,
        query_emb: List[float],
        items: List[dict],
        embeddings: List[Optional[List[float]]],
        source_type: str,
    ) -> Optional[SimilarItem]:
        """找出與 query 最相似的項目。"""
        best_sim = 0.0
        best_item: Optional[SimilarItem] = None

        for i, item in enumerate(items):
            emb = embeddings[i]
            if emb is None:
                continue
            sim = self._cosine_similarity(query_emb, emb)
            if sim > best_sim:
                best_sim = sim
                title = item.get("question_summary") or item.get("title", "")
                best_item = SimilarItem(
                    source_type=source_type,
                    source_id=str(item.get("id", "")),
                    title=title,
                    similarity=sim,
                )

        return best_item

    def _get_content(
        self,
        similar: SimilarItem,
        kb_items: List[dict],
        sop_items: List[dict],
    ) -> str:
        """從原始項目取得內容文字。"""
        items = kb_items if similar.source_type == "kb" else sop_items
        for item in items:
            if str(item.get("id", "")) == similar.source_id:
                if similar.source_type == "kb":
                    return item.get("answer", "")
                else:
                    return item.get("content", "")
        return ""

    def _record_uncovered(
        self,
        report: CoverageReport,
        question: SystemQuestion,
        similar: List[SimilarItem],
    ) -> None:
        report.uncovered += 1
        self._update_module_role_stats(report, question, "uncovered")
        report.gaps.append(GapItem(
            topic_id=question.topic_id,
            question=question.question,
            gap_type="uncovered",
            recommendation=self._recommend("uncovered", question),
            query_type=question.query_type,
            priority=question.priority,
            similar_existing=[s for s in similar if s.similarity > 0],
        ))

    def _record_partial(
        self,
        report: CoverageReport,
        question: SystemQuestion,
        similar: List[SimilarItem],
    ) -> None:
        report.partial_covered += 1
        self._update_module_role_stats(report, question, "partial_covered")
        report.gaps.append(GapItem(
            topic_id=question.topic_id,
            question=question.question,
            gap_type="partial",
            recommendation=self._recommend("partial", question),
            query_type=question.query_type,
            priority=question.priority,
            similar_existing=[s for s in similar if s.similarity > 0],
        ))

    def _record_needs_improvement(
        self,
        report: CoverageReport,
        question: SystemQuestion,
        similar: List[SimilarItem],
    ) -> None:
        report.needs_improvement += 1
        self._update_module_role_stats(report, question, "needs_improvement")
        report.gaps.append(GapItem(
            topic_id=question.topic_id,
            question=question.question,
            gap_type="needs_improvement",
            recommendation=self._recommend("needs_improvement", question),
            query_type=question.query_type,
            priority=question.priority,
            similar_existing=[s for s in similar if s.similarity > 0],
        ))

    def _update_module_role_stats(
        self,
        report: CoverageReport,
        question: SystemQuestion,
        status: str,
    ) -> None:
        """更新模組和角色維度的統計。"""
        # Module
        mod_id = question.module_id
        if mod_id not in report.coverage_by_module:
            report.coverage_by_module[mod_id] = ModuleCoverage(
                module_id=mod_id, module_name=mod_id,
            )
        mod = report.coverage_by_module[mod_id]
        mod.total += 1
        setattr(mod, status, getattr(mod, status) + 1)

        # Role (each role in question.roles gets counted)
        for role in question.roles:
            if role not in report.coverage_by_role:
                report.coverage_by_role[role] = RoleCoverage(role=role)
            rc = report.coverage_by_role[role]
            rc.total += 1
            setattr(rc, status, getattr(rc, status) + 1)

    def _report_to_dict(self, report: CoverageReport) -> dict:
        """將 CoverageReport 轉為可序列化的 dict。"""
        module_dict = {}
        for mod_id, mod in report.coverage_by_module.items():
            module_dict[mod_id] = {
                "module_id": mod.module_id,
                "module_name": mod.module_name,
                "total": mod.total,
                "covered_by_kb": mod.covered_by_kb,
                "covered_by_sop": mod.covered_by_sop,
                "uncovered": mod.uncovered,
                "partial_covered": mod.partial_covered,
                "needs_improvement": mod.needs_improvement,
                "coverage_rate": mod.coverage_rate,
            }

        role_dict = {}
        for role_name, rc in report.coverage_by_role.items():
            role_dict[role_name] = {
                "role": rc.role,
                "total": rc.total,
                "covered_by_kb": rc.covered_by_kb,
                "covered_by_sop": rc.covered_by_sop,
                "uncovered": rc.uncovered,
                "partial_covered": rc.partial_covered,
                "needs_improvement": rc.needs_improvement,
                "coverage_rate": rc.coverage_rate,
            }

        gaps_list = []
        for gap in report.gaps:
            gaps_list.append({
                "topic_id": gap.topic_id,
                "question": gap.question,
                "gap_type": gap.gap_type,
                "recommendation": gap.recommendation,
                "query_type": gap.query_type,
                "priority": gap.priority,
                "similar_existing": [
                    {
                        "source_type": s.source_type,
                        "source_id": s.source_id,
                        "title": s.title,
                        "similarity": round(s.similarity, 4),
                    }
                    for s in gap.similar_existing
                ],
            })

        return {
            "total_questions": report.total_questions,
            "covered_by_kb": report.covered_by_kb,
            "covered_by_sop": report.covered_by_sop,
            "uncovered": report.uncovered,
            "partial_covered": report.partial_covered,
            "needs_improvement": report.needs_improvement,
            "coverage_by_module": module_dict,
            "coverage_by_role": role_dict,
            "gaps": gaps_list,
        }
