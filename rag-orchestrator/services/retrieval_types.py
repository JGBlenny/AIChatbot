"""
Retriever 結果型別契約

統一定義 SOP / 知識庫 retriever 各 pipeline 階段的分數欄位與 metadata。

對應規格：.kiro/specs/retriever-similarity-refactor/
- requirements.md Requirement 1（分數欄位定義）
- design.md 元件 1（RetrievalResult 資料模型）

設計目標：
    將原本被多階段覆寫的 `similarity` 欄位，拆解為各 pipeline 階段獨立記錄的分數，
    最終由 `_finalize_scores` 依公式組合出最終排序分數。各欄位職責單一、不互相覆寫。

欄位語意（pipeline 階段對應）：
    - vector_similarity (Stage 1, _vector_search)：
        query 與 item embedding 的原始 cosine similarity（0.0–1.0）。
        純 keyword fallback 命中項目預設 0.0（代表「向量沒命中、靠 keyword 找到」）。
    - keyword_score (Stage 2, _keyword_search)：
        keyword 配對的 normalized 分數（0.0–1.0）。
        非 keyword 路徑為 None。**不再** cap 在 0.70。
    - keyword_boost (Stage 3, _apply_keyword_boost)：
        命中關鍵字後的加成倍率，未套用為 1.0。
    - rerank_score (Stage 4, _apply_semantic_reranker)：
        SemanticReranker 的分數（0.0–1.0）。未經 rerank 為 None。
    - similarity (Stage 5, _finalize_scores)：
        依公式計算的最終綜合分數，用於排序與 application 端 threshold 過濾。
    - score_source：
        最終 similarity 的計算來源 ("rerank" | "keyword" | "vector")。
    - original_similarity：
        向後相容 alias = vector_similarity（純向量分數）。
        舊版下游消費者讀取此欄位時可拿到純向量分數，行為符合決策 5。
"""
from typing import TypedDict, Optional, List, Any


class RetrievalResult(TypedDict, total=False):
    """
    Retriever 單筆結果的型別契約。

    使用 `total=False` 允許子類 retriever（SOP/KB）在 `_format_result` 中
    依不同來源欄位（item_name vs question_summary、content vs answer）填充，
    避免強制所有欄位都必須提供，但核心分數欄位由 `make_default_result` 確保預設值齊全。

    分數欄位（Stage 對應見模組 docstring）：
        vector_similarity: float
        keyword_score: Optional[float]
        keyword_boost: float
        rerank_score: Optional[float]
        similarity: float
        score_source: str  # "rerank" | "keyword" | "vector"
        original_similarity: float  # alias = vector_similarity

    Metadata：
        keyword_matches: List[str]   # 命中哪些關鍵字
        search_method: str           # "vector" | "keyword_fallback"

    既有欄位（由 _format_result 由 row 填充）：
        id, item_name, content, keywords 等
    """

    # ─── 既有欄位（由 _format_result 由 DB row 填充） ───
    id: int
    item_name: str            # SOP 用 item_name；KB 用 question_summary
    content: str
    keywords: List[str]
    search_method: str        # "vector" | "keyword_fallback"

    # ─── 新增分數欄位 ───
    vector_similarity: float          # Stage 1：原始 cosine（0.0–1.0）
    keyword_score: Optional[float]    # Stage 2：keyword 配對分數
    keyword_boost: float              # Stage 3：boost 倍率，未套用為 1.0
    rerank_score: Optional[float]     # Stage 4：reranker 分數

    # ─── 最終分數 ───
    similarity: float                 # Stage 5：綜合分數，用於排序

    # ─── Debug 輔助 ───
    score_source: str                 # "rerank" | "keyword" | "vector"
    keyword_matches: List[str]        # 命中哪些 keyword

    # ─── 向後相容 alias ───
    # 語意：= vector_similarity（純向量 cosine）
    # 注意：舊版語意為「reranker 前的 similarity」（含 boost）
    # 新版改為純向量分數，符合決策 5（_has_perfect_match 用純向量分數）
    original_similarity: float


def make_default_result() -> RetrievalResult:
    """
    建立 RetrievalResult 預設值工廠。

    用於 `_format_result` 構建單筆結果時提供分數欄位預設值，
    確保即使子類遺漏欄位，pipeline 後續階段（_apply_keyword_boost、
    _finalize_scores）仍能安全讀取。

    預設值對照（符合設計決策）：
        vector_similarity = 0.0         # 無向量結果
        keyword_score     = None        # 未走 keyword path
        keyword_boost     = 1.0         # 未套用 boost
        rerank_score      = None        # 未經 rerank
        similarity        = 0.0         # 待 _finalize_scores 重算
        score_source      = "vector"    # 預設假設為 vector path
        keyword_matches   = []          # 無命中
        original_similarity = 0.0       # alias of vector_similarity

    每次呼叫回傳獨立 dict（不共享 mutable state）。

    Returns:
        RetrievalResult: 含完整分數欄位預設值的 dict
    """
    return {
        'vector_similarity': 0.0,
        'keyword_score': None,
        'keyword_boost': 1.0,
        'rerank_score': None,
        'similarity': 0.0,
        'score_source': 'vector',
        'keyword_matches': [],
        'original_similarity': 0.0,
    }
