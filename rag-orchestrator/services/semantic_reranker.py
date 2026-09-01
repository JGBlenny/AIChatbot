"""
語義重排序服務
整合到語義模型 Docker 服務
"""
import os
from typing import List, Dict, Optional
import logging

try:
    import httpx
    use_httpx = True
except ImportError:
    try:
        import requests
        use_httpx = False
    except ImportError:
        # 如果都沒有，稍後會處理
        use_httpx = None

try:  # package import（production 路徑）
    from .retrieval_representation import (
        SURFACE_FIELD,
        SURFACE_SOURCE_FIELD,
        scoring_surface,
    )
except ImportError:  # 直接以 script 執行時的相容路徑
    from retrieval_representation import (  # type: ignore
        SURFACE_FIELD,
        SURFACE_SOURCE_FIELD,
        scoring_surface,
    )

logger = logging.getLogger(__name__)

class SemanticReranker:
    """語義重排序器 - 使用獨立的語義模型服務"""

    def __init__(self):
        """初始化語義重排序器"""
        # 語義模型服務 URL（Docker 內部網路）
        self.semantic_api_url = os.getenv(
            'SEMANTIC_MODEL_API_URL',
            'http://aichatbot-semantic-model:8000'
        )

        #: ⚠️ 2026-09-01：可用性判定改成**可自我復原**。
        #: 舊行為：`__init__` 只探測一次（timeout=2），失敗即 `is_available=False`，
        #: 整個 process 生命週期不再重查 ⇒ semantic-model 一次忙碌（實測推論可達 90 秒、
        #: CPU 600%+）就讓 reranker **永久靜默關閉**，而容器 healthy、
        #: `/api/v1/system/pipeline-health` 也照樣回綠（那支是獨立重探測，
        #: ⛔ 不反映正在服務的物件狀態）。
        #: 實際後果：rerank 佔最終分數 90%（0.1×vector + 0.9×rerank），一停就落到
        #: `max(vector, keyword) × boost` 分支，**純詞面命中得 1.0 壓過正解**。
        #: 2026-09-01 實例：同一題從「請撥打客服專線」變成正確作答，只因 reranker 回來。
        self._recheck_sec = float(os.getenv("RERANKER_RECHECK_INTERVAL", "60"))
        self._probe_timeout = float(os.getenv("RERANKER_PROBE_TIMEOUT", "5"))
        self._last_probe_ts = 0.0
        self._last_probe_ok = False
        self.is_available = self._check_service()

    def available(self) -> bool:
        """目前是否可用（**失敗會在 `RERANKER_RECHECK_INTERVAL` 秒後自動重試**）。

        ⛔ 呼叫端請用本方法，⛔ 不要快取 `is_available` 的布林值——那正是舊行為的病灶。
        成功時不重探（避免每次請求多一次 HTTP）；失敗時才週期性重試。
        """
        import time as _t
        if self._last_probe_ok:
            return True
        if (_t.time() - self._last_probe_ts) >= self._recheck_sec:
            if self._check_service():
                logger.info("✅ 語義模型服務已復原，Reranker 重新啟用")
        return self._last_probe_ok

    def _check_service(self) -> bool:
        """檢查語義模型服務是否可用（同時記錄探測時間與結果，供 `available()` 用）。"""
        import time as _t
        self._last_probe_ts = _t.time()
        self._last_probe_ok = False
        if use_httpx is None:
            logger.warning("⚠️ httpx 和 requests 都未安裝，無法使用語義模型服務")
            return False

        try:
            if use_httpx:
                with httpx.Client() as client:
                    response = client.get(f"{self.semantic_api_url}/",
                                          timeout=self._probe_timeout)
            else:
                response = requests.get(f"{self.semantic_api_url}/",
                                        timeout=self._probe_timeout)

            if response.status_code == 200:
                logger.info(f"✅ 語義模型服務可用: {self.semantic_api_url}")
                self._last_probe_ok = True
                self.is_available = True
                return True
        except Exception as e:
            logger.warning(f"⚠️ 語義模型服務不可用: {e}")
        return False

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        使用語義模型重新排序候選知識

        Args:
            query: 用戶查詢
            candidates: 候選知識列表
            top_k: 返回前K個結果

        Returns:
            重新排序後的知識列表
        """
        if not self.is_available:
            logger.warning("語義模型服務不可用，返回原始順序")
            return candidates[:top_k]

        try:
            # 準備請求數據
            # ⚠️ **scoring surface 在此端解析一次**（D2，2026-08-29）：
            #    舊註解寫「傳原始欄位讓 API server 決定如何組合」——那讓
            #    embedding 端與 reranker 端各自持有一份優先序，兩份實作＝兩個
            #    semantic universe，正是 R8 診斷出的結構性病灶。
            #    現在唯一實作點是 retrieval_representation.scoring_surface()。
            # ⚠️ answer／content／question_summary **仍照舊送**：api_server 對
            #    沒有 scoring_surface 的舊 client 仍需維持原優先序（向後相容），
            #    ⛔ 不可為了「乾淨」把它們拿掉。
            # ⚠️ `scoring_surface_source` 一併送出 ⇒ migration 覆蓋率可被統計。
            payload_candidates = []
            for c in candidates:
                surface, surface_source = scoring_surface(c)
                payload_candidates.append({
                    "id": c.get("id"),
                    "answer": c.get("answer", ""),
                    "content": c.get("content", ""),
                    "question_summary": c.get("question_summary", ""),
                    SURFACE_FIELD: surface,
                    SURFACE_SOURCE_FIELD: surface_source,
                })
            request_data = {
                "query": query,
                "candidates": payload_candidates,
                "top_k": top_k
            }

            # 調用語義模型 API
            # hotfix (.kiro/issues/reranker-returning-zero.md)：
            # timeout 從 15s → 60s。bge-reranker-base CPU 推論大批次（>30 筆）需時 25-30s，
            # 舊的 15s timeout 導致 KB 路徑 100% 失敗。
            # 配合 base_retriever 的 RERANKER_INPUT_LIMIT 限制（預設 20）雙重保險。
            rerank_timeout = int(os.getenv("RERANKER_HTTP_TIMEOUT", "60"))
            if use_httpx:
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.semantic_api_url}/rerank",
                        json=request_data,
                        timeout=rerank_timeout
                    )
            else:
                response = requests.post(
                    f"{self.semantic_api_url}/rerank",
                    json=request_data,
                    timeout=rerank_timeout
                )

            if response.status_code == 200:
                result = response.json()

                # 根據返回的ID順序重新排列候選
                reranked_ids = [r["id"] for r in result.get("results", [])]
                id_to_candidate = {c["id"]: c for c in candidates}

                reranked = []
                for rid in reranked_ids:
                    if rid in id_to_candidate:
                        candidate = id_to_candidate[rid]
                        # 添加語義分數
                        score_info = next((r for r in result["results"] if r["id"] == rid), {})
                        candidate["semantic_score"] = score_info.get("score", 0)
                        reranked.append(candidate)

                logger.info(f"✅ 語義重排序完成，返回 {len(reranked)} 個結果")
                return reranked

        except Exception as e:
            logger.error(f"語義重排序失敗: {e}")

        # 降級返回原始結果
        return candidates[:top_k]

    def search(
        self,
        query: str,
        vendor_id: Optional[int] = None,
        top_k: int = 5
    ) -> Dict:
        """
        直接使用語義模型搜索（掃描全部知識庫）

        Args:
            query: 用戶查詢
            vendor_id: 業者ID（可選）
            top_k: 返回前K個結果

        Returns:
            搜索結果
        """
        if not self.is_available:
            return {"error": "語義模型服務不可用"}

        try:
            # 準備請求
            request_data = {
                "query": query,
                "top_k": top_k,
                "min_score": 0.1
            }

            if vendor_id:
                request_data["vendor_id"] = vendor_id

            # 調用語義模型搜索 API
            if use_httpx:
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.semantic_api_url}/search",
                        json=request_data,
                        timeout=10
                    )
            else:
                response = requests.post(
                    f"{self.semantic_api_url}/search",
                    json=request_data,
                    timeout=10
                )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"語義搜索失敗: {e}")

        return {"error": "搜索失敗"}

# 全局實例
_semantic_reranker = None

def get_semantic_reranker() -> SemanticReranker:
    """獲取語義重排序器實例"""
    global _semantic_reranker
    if _semantic_reranker is None:
        _semantic_reranker = SemanticReranker()
    return _semantic_reranker