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

        # 檢查服務是否可用
        self.is_available = self._check_service()

    def _check_service(self) -> bool:
        """檢查語義模型服務是否可用"""
        if use_httpx is None:
            logger.warning("⚠️ httpx 和 requests 都未安裝，無法使用語義模型服務")
            return False

        try:
            if use_httpx:
                with httpx.Client() as client:
                    response = client.get(f"{self.semantic_api_url}/", timeout=2)
            else:
                response = requests.get(f"{self.semantic_api_url}/", timeout=2)

            if response.status_code == 200:
                logger.info(f"✅ 語義模型服務可用: {self.semantic_api_url}")
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
            request_data = {
                "query": query,
                "candidates": [
                    {
                        "id": c.get("id"),
                        "content": c.get("answer", "") + " " + c.get("question_summary", "")
                    }
                    for c in candidates
                ],
                "top_k": top_k
            }

            # 調用語義模型 API
            if use_httpx:
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.semantic_api_url}/rerank",
                        json=request_data,
                        timeout=15
                    )
            else:
                response = requests.post(
                    f"{self.semantic_api_url}/rerank",
                    json=request_data,
                    timeout=15
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