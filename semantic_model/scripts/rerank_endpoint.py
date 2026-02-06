"""
添加 /rerank 端點到 API 服務
"""

# 請在 api_server.py 的 /search 端點後添加以下代碼：

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