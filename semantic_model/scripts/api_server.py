#!/usr/bin/env python3
"""
語義模型 API 服務 - 生產環境
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Union, Any
import uvicorn
import json
import os
from datetime import datetime
from sentence_transformers import CrossEncoder
import logging

# 設定日誌
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# FastAPI 應用
app = FastAPI(
    title="Semantic Model API",
    description="語義模型服務 - 知識庫智能匹配",
    version="1.0.0"
)

# 全局變數
model = None
knowledge_base = None

# Request/Response 模型
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.1
    vendor_id: Optional[int] = None

class SearchResult(BaseModel):
    knowledge_id: int
    title: str
    content: str
    score: float
    action_type: Optional[str]
    form_id: Optional[Union[int, str]]  # 支援整數或字串

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    search_time: float
    model_version: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    knowledge_base_size: int
    model_name: str

# 啟動時載入模型
@app.on_event("startup")
async def startup_event():
    """啟動時載入模型和知識庫"""
    global model, knowledge_base

    logger.info("正在載入語義模型...")

    # 載入模型
    model_name = os.getenv('MODEL_NAME', 'BAAI/bge-reranker-base')
    try:
        model = CrossEncoder(model_name, max_length=512)
        logger.info(f"✅ 模型載入成功: {model_name}")
    except Exception as e:
        logger.error(f"❌ 模型載入失敗: {e}")
        raise

    # 載入知識庫
    try:
        kb_path = '/app/data/knowledge_base.json'
        with open(kb_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"✅ 載入 {len(knowledge_base)} 個知識點")
    except Exception as e:
        logger.error(f"❌ 知識庫載入失敗: {e}")
        raise

# API 端點
@app.get("/", response_model=HealthResponse)
async def health_check():
    """健康檢查"""
    return HealthResponse(
        status="healthy",
        model_loaded=model is not None,
        knowledge_base_size=len(knowledge_base) if knowledge_base else 0,
        model_name=os.getenv('MODEL_NAME', 'BAAI/bge-reranker-base')
    )

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    語義搜索端點
    """
    if not model or not knowledge_base:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start_time = datetime.now()

    try:
        # 篩選知識庫（可根據 vendor_id 等條件）
        candidates = knowledge_base
        if request.vendor_id:
            candidates = [kb for kb in knowledge_base
                         if kb.get('vendor_id') == request.vendor_id]

        # 批次計算分數
        batch_size = 100
        all_results = []

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i+batch_size]
            pairs = [[request.query, kb['content']] for kb in batch]
            scores = model.predict(pairs)

            for kb, score in zip(batch, scores):
                if score >= request.min_score:
                    all_results.append({
                        'knowledge_id': kb['id'],
                        'title': kb['title'],
                        'content': kb['content'][:200] + "...",
                        'score': float(score),
                        'action_type': kb.get('action_type'),
                        'form_id': kb.get('form_id')  # 現在可以直接傳遞，支援 int 或 str
                    })

        # 排序並返回前 K 個
        all_results.sort(key=lambda x: x['score'], reverse=True)
        top_results = all_results[:request.top_k]

        # 計算搜索時間
        search_time = (datetime.now() - start_time).total_seconds()

        return SearchResponse(
            query=request.query,
            results=top_results,
            search_time=search_time,
            model_version="1.0.0"
        )

    except Exception as e:
        logger.error(f"搜索錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RerankRequest(BaseModel):
    query: str
    candidates: List[Dict[str, Any]]
    top_k: int = 5

class RerankResult(BaseModel):
    id: Any
    score: float
    content: str

class RerankResponse(BaseModel):
    results: List[RerankResult]

@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    """
    重新排序候選結果
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # 準備模型輸入
    pairs = []
    for candidate in request.candidates:
        content = candidate.get("content", "")
        pairs.append([request.query, content])

    # 計算分數
    if pairs:
        scores = model.predict(pairs)

        # 組合結果
        results = []
        for i, (candidate, score) in enumerate(zip(request.candidates, scores)):
            results.append({
                "id": candidate.get("id"),
                "score": float(score),
                "content": candidate.get("content", "")[:200]
            })

        # 按分數排序
        results.sort(key=lambda x: x["score"], reverse=True)

        # 返回前 top_k 個
        return RerankResponse(results=results[:request.top_k])

    return RerankResponse(results=[])

@app.post("/reload")
async def reload_knowledge_base():
    """
    重新載入知識庫（不重啟服務）
    """
    global knowledge_base

    try:
        kb_path = '/app/data/knowledge_base.json'
        with open(kb_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)

        return {
            "status": "success",
            "message": f"重新載入 {len(knowledge_base)} 個知識點"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """
    獲取系統指標
    """
    return {
        "model_loaded": model is not None,
        "knowledge_base_size": len(knowledge_base) if knowledge_base else 0,
        "model_name": os.getenv('MODEL_NAME', 'BAAI/bge-reranker-base'),
        "api_version": "1.0.0",
        "python_version": "3.9"
    }

# 主程式
if __name__ == "__main__":
    port = int(os.getenv('API_PORT', 8000))
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )