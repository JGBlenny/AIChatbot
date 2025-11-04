"""
Streaming Chat API
提供 Server-Sent Events (SSE) 流式輸出
Phase 3: 用戶體驗優化 - 即時反饋
"""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
import json
import asyncio
import time

router = APIRouter()


class ChatStreamRequest(BaseModel):
    """流式聊天請求"""
    question: str = Field(..., min_length=1, max_length=1000)
    vendor_id: int = Field(..., ge=1)
    user_role: str = Field(..., description="customer 或 staff")
    user_id: Optional[str] = None
    context: Optional[Dict] = None


async def generate_sse_event(event_type: str, data: dict) -> str:
    """生成 SSE 格式的事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chat_stream_generator(
    request: ChatStreamRequest,
    app_state
):
    """
    流式聊天生成器

    輸出事件類型:
    - start: 開始處理
    - intent: 意圖分類完成
    - search: 檢索完成
    - confidence: 信心度評估完成
    - answer_chunk: 答案片段（逐字輸出）
    - answer_complete: 答案完成
    - metadata: 處理元數據
    - done: 全部完成
    """
    start_time = time.time()

    try:
        # 1. 發送開始事件
        yield await generate_sse_event("start", {
            "message": "開始處理問題...",
            "question": request.question
        })

        # 獲取服務實例
        intent_classifier = app_state.intent_classifier
        rag_engine = app_state.rag_engine
        confidence_evaluator = app_state.confidence_evaluator
        llm_optimizer = app_state.llm_answer_optimizer
        vendor_config_service = app_state.vendor_config_service

        # 2. 並行執行意圖分類和檢索（Phase 2 優化 + Vendor SOP 整合）
        # NOTE: 移除了早期參數檢查，改為在找不到知識庫/SOP結果時才使用參數答案
        import os
        intent_task = asyncio.to_thread(intent_classifier.classify, request.question)
        fallback_similarity_threshold = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", "0.55"))
        rag_top_k = int(os.getenv("RAG_TOP_K", "5"))
        search_task = rag_engine.search(
            query=request.question,
            limit=rag_top_k,
            similarity_threshold=fallback_similarity_threshold,
            vendor_id=request.vendor_id
        )

        intent_result, search_results = await asyncio.gather(intent_task, search_task)

        # 2.5. 如果有明確意圖，也檢索 Vendor SOP（使用共用模組）
        intent_ids = intent_result.get('intent_ids', [])
        print(f"🔍 Intent IDs: {intent_ids}, Vendor ID: {request.vendor_id}")
        print(f"🔑 Question Keywords: {intent_result.get('keywords', [])}")
        print(f"📊 Search Results: {len(search_results)} items")
        if search_results:
            print(f"   First Result Keywords: {search_results[0].get('keywords', [])}")

        sop_items = []
        if intent_ids and request.vendor_id:
            try:
                # 使用共用模組的 SOP 檢索函數
                from routers.chat_shared import retrieve_sop_async, convert_sop_to_search_results

                # 檢索 SOP（異步版本）
                sop_items = await retrieve_sop_async(
                    vendor_id=request.vendor_id,
                    intent_ids=intent_ids,
                    top_k=rag_top_k
                )

                # 如果找到 SOP，轉換為標準格式並優先使用
                if sop_items:
                    # 使用共用函數轉換格式（自動設定 similarity=1.0）
                    sop_search_results = convert_sop_to_search_results(sop_items)

                    # 合併：SOP 在前，一般知識在後
                    search_results = sop_search_results + search_results[:2]
                    print(f"✨ 合併後共 {len(search_results)} 個結果（{len(sop_search_results)} SOP + {min(2, len(search_results) - len(sop_search_results))} 知識庫）")
            except Exception as e:
                print(f"⚠️  Vendor SOP 檢索失敗: {e}，使用一般知識庫結果")

        # 3. 發送意圖分類結果
        yield await generate_sse_event("intent", {
            "intent_type": intent_result['intent_type'],
            "intent_name": intent_result.get('intent_name', 'unknown'),
            "confidence": intent_result.get('confidence', 0)
        })

        # 4. 發送檢索結果
        yield await generate_sse_event("search", {
            "doc_count": len(search_results),
            "has_results": len(search_results) > 0
        })

        # 5. 信心度評估（SOP 檢索時強制使用高信心度）
        from routers.chat_shared import has_sop_results

        has_sop = has_sop_results(search_results)

        if has_sop:
            # SOP 精準匹配，強制使用高信心度（與 chat.py 統一）
            evaluation = {
                'confidence_score': 0.95,
                'confidence_level': 'high',
                'decision': 'direct_answer'
            }
            print(f"📋 [SOP] 強制使用高信心度（similarity=1.0）")
        else:
            # 正常信心度評估
            evaluation = confidence_evaluator.evaluate(
                search_results=search_results,
                question_keywords=intent_result['keywords']
            )

        yield await generate_sse_event("confidence", {
            "score": evaluation['confidence_score'],
            "level": evaluation['confidence_level'],
            "decision": evaluation['decision']
        })

        # 6. 根據決策生成答案（使用 streaming）
        if evaluation['decision'] == 'direct_answer' and search_results:
            # 高信心度：使用條件式優化（Phase 1）
            async for chunk in stream_optimized_answer(
                request.question,
                search_results,
                evaluation,
                intent_result,
                llm_optimizer,
                vendor_id=request.vendor_id
            ):
                yield chunk

        elif evaluation['decision'] == 'needs_enhancement' and search_results:
            # 中等信心度
            async for chunk in stream_optimized_answer(
                request.question,
                search_results,
                evaluation,
                intent_result,
                llm_optimizer,
                vendor_id=request.vendor_id,
                add_warning=True
            ):
                yield chunk

        else:
            # 低信心度或無結果：嘗試參數答案，否則返回 unclear
            from routers.chat_shared import check_param_question
            param_category, param_answer = await check_param_question(
                vendor_config_service=vendor_config_service,
                question=request.question,
                vendor_id=request.vendor_id
            )

            if param_answer:
                # 使用參數型答案
                print(f"   ℹ️  知識庫/SOP無結果，使用參數型答案（category={param_category}）")
                yield await generate_sse_event("config_param", {
                    "category": param_category,
                    "config_used": param_answer.get('config_used', {})
                })

                # 流式輸出答案
                answer = param_answer['answer']
                words = answer.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield await generate_sse_event("answer_chunk", {"chunk": chunk})
                    await asyncio.sleep(0.02)
            else:
                # unclear 答案
                yield await generate_sse_event("answer_chunk", {
                    "chunk": "抱歉，我對這個問題不太確定如何回答。\n\n"
                })
                yield await generate_sse_event("answer_chunk", {
                    "chunk": "您的問題已經記錄下來，我們會盡快處理。\n"
                })
                yield await generate_sse_event("answer_chunk", {
                    "chunk": "如需立即協助，請聯繫客服人員。"
                })

        # 7. 發送完成事件
        processing_time = int((time.time() - start_time) * 1000)
        yield await generate_sse_event("answer_complete", {
            "processing_time_ms": processing_time
        })

        # 8. 發送元數據
        yield await generate_sse_event("metadata", {
            "confidence_score": evaluation['confidence_score'],
            "confidence_level": evaluation['confidence_level'],
            "intent_type": intent_result['intent_type'],
            "doc_count": len(search_results),
            "processing_time_ms": processing_time
        })

        # 9. 發送完成標記
        yield await generate_sse_event("done", {
            "message": "處理完成",
            "success": True
        })

    except Exception as e:
        # 錯誤處理
        yield await generate_sse_event("error", {
            "message": str(e),
            "type": type(e).__name__
        })
        yield await generate_sse_event("done", {
            "message": "處理失敗",
            "success": False
        })


async def stream_optimized_answer(
    question: str,
    search_results: list,
    evaluation: dict,
    intent_result: dict,
    llm_optimizer,
    vendor_id: int = None,
    add_warning: bool = False
):
    """
    流式輸出優化後的答案

    Phase 3 擴展：整合答案合成功能
    - 使用 llm_optimizer.optimize_answer() 統一處理所有優化策略
    - 支援答案合成（自動合併多個 SOP 項目）
    - 條件式優化（快速路徑、模板、LLM）由 optimizer 內部決定

    Phase 4 擴展：業態語氣調整
    - 根據 vendor_id 取得業者的 business_types
    - 將 vendor_info 傳遞給優化器以應用語氣調整
    """
    confidence_score = evaluation['confidence_score']
    confidence_level = evaluation['confidence_level']

    # 取得業者資訊（包含 business_types，用於語氣調整）
    vendor_info = None
    vendor_name = None
    if vendor_id:
        try:
            from services.vendor_parameter_resolver import VendorParameterResolver
            param_resolver = VendorParameterResolver()
            vendor_info = param_resolver.get_vendor_info(vendor_id)
            if vendor_info:
                vendor_name = vendor_info.get('name')
                # 確保 business_type 欄位存在（從 business_types 陣列取第一個）
                if 'business_types' in vendor_info and vendor_info['business_types']:
                    vendor_info['business_type'] = vendor_info['business_types'][0]
                print(f"📋 業者資訊: {vendor_name}, 業態: {vendor_info.get('business_type', 'N/A')}")
        except Exception as e:
            print(f"⚠️  取得業者資訊失敗: {e}")

    try:
        # 使用 llm_optimizer 進行答案優化（包含答案合成和語氣調整）
        # 在 asyncio 線程池中執行同步方法
        optimization_result = await asyncio.to_thread(
            llm_optimizer.optimize_answer,
            question=question,
            search_results=search_results,
            confidence_level=confidence_level,
            intent_info=intent_result,
            confidence_score=confidence_score,
            vendor_name=vendor_name,
            vendor_info=vendor_info
        )

        # 取得優化後的答案
        answer = optimization_result['optimized_answer']
        synthesis_applied = optimization_result.get('synthesis_applied', False)
        optimization_method = optimization_result.get('optimization_method', 'unknown')

        # 記錄優化結果
        if synthesis_applied:
            print(f"🔄 [Streaming] 答案合成已應用 ({len(search_results)} 個來源)")
        else:
            print(f"📤 [Streaming] 優化方法: {optimization_method} (信心度: {confidence_score:.3f})")

        # 發送合成狀態事件（如果有合成）
        if synthesis_applied:
            yield await generate_sse_event("synthesis", {
                "applied": True,
                "source_count": len(search_results),
                "method": optimization_method
            })

        # 流式輸出答案（逐字輸出以提升用戶體驗）
        words = answer.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield await generate_sse_event("answer_chunk", {"chunk": chunk})

            # 根據優化方法調整輸出速度
            if optimization_method == "fast_path":
                await asyncio.sleep(0.015)  # 快速路徑：15ms
            elif optimization_method == "template":
                await asyncio.sleep(0.02)   # 模板：20ms
            else:
                await asyncio.sleep(0.025)  # LLM/合成：25ms（模擬 LLM 生成）

    except Exception as e:
        # 優化失敗時的降級處理
        print(f"❌ [Streaming] 答案優化失敗: {e}")

        # 使用第一個搜尋結果作為降級答案
        if search_results:
            answer = search_results[0].get('content', '抱歉，無法生成答案。')
            words = answer.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield await generate_sse_event("answer_chunk", {"chunk": chunk})
                await asyncio.sleep(0.02)
        else:
            yield await generate_sse_event("answer_chunk", {
                "chunk": "抱歉，無法生成答案。"
            })

    # 如果需要添加警告
    if add_warning:
        yield await generate_sse_event("answer_chunk", {
            "chunk": f"\n\n⚠️ 注意：此答案信心度為中等（{confidence_score:.2f}），建議您聯繫客服人員進一步確認。"
        })


@router.post("/chat/stream")
async def chat_stream(request: ChatStreamRequest, req: Request):
    """
    流式聊天 API (SSE)

    返回 Server-Sent Events 流，包含以下事件:
    - start: 開始處理
    - intent: 意圖分類
    - search: 檢索結果
    - confidence: 信心度評估
    - answer_chunk: 答案片段（逐字輸出）
    - answer_complete: 答案完成
    - metadata: 處理元數據
    - done: 全部完成

    客戶端範例:
    ```javascript
    const eventSource = new EventSource('/api/v1/chat/stream');

    eventSource.addEventListener('answer_chunk', (event) => {
        const data = JSON.parse(event.data);
        answerDiv.textContent += data.chunk;
    });

    eventSource.addEventListener('done', (event) => {
        eventSource.close();
    });
    ```
    """
    return StreamingResponse(
        chat_stream_generator(request, req.app.state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 緩衝
        }
    )


# 測試端點
@router.get("/chat/stream/test")
async def test_stream():
    """測試 SSE 連接"""
    async def generate():
        for i in range(5):
            yield f"data: {{\"message\": \"測試訊息 {i+1}\"}}\n\n"
            await asyncio.sleep(0.5)
        yield "data: {\"message\": \"完成\"}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
