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

        from services.business_scope_utils import get_allowed_audiences_for_scope
        business_scope = "external" if request.user_role == "customer" else "internal"
        allowed_audiences = get_allowed_audiences_for_scope(business_scope)

        # 1.5 層級2優先：檢查是否為參數型問題（Vendor Configs 整合）
        param_category = vendor_config_service.is_param_question(request.question)
        if param_category:
            param_answer = await vendor_config_service.create_param_answer(
                vendor_id=request.vendor_id,
                question=request.question,
                param_category=param_category
            )

            if param_answer:
                # 參數型問題直接回答
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

                # 完成事件
                processing_time = int((time.time() - start_time) * 1000)
                yield await generate_sse_event("answer_complete", {
                    "processing_time_ms": processing_time
                })
                yield await generate_sse_event("metadata", {
                    "source": "vendor_config",
                    "confidence_score": 1.0,
                    "confidence_level": "high",
                    "processing_time_ms": processing_time
                })
                yield await generate_sse_event("done", {
                    "message": "處理完成（參數型答案）",
                    "success": True
                })
                return

        # 2. 並行執行意圖分類和檢索（Phase 2 優化）
        intent_task = asyncio.to_thread(intent_classifier.classify, request.question)
        search_task = rag_engine.search(
            query=request.question,
            limit=5,
            similarity_threshold=0.60,
            allowed_audiences=allowed_audiences
        )

        intent_result, search_results = await asyncio.gather(intent_task, search_task)

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

        # 5. 信心度評估
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
                llm_optimizer
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
                add_warning=True
            ):
                yield chunk

        else:
            # 低信心度：unclear
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
    add_warning: bool = False
):
    """
    流式輸出優化後的答案

    根據信心度使用不同的策略（Phase 1 條件式優化）:
    - 極高信心度: 快速路徑（逐字輸出預存答案）
    - 高信心度: 模板格式化（逐字輸出格式化答案）
    - 其他: LLM streaming（OpenAI streaming API）
    """
    confidence_score = evaluation['confidence_score']
    confidence_level = evaluation['confidence_level']

    # 檢查是否使用快速路徑
    from services.answer_formatter import AnswerFormatter
    formatter = AnswerFormatter()

    if confidence_score >= 0.75 and formatter.is_content_complete(search_results[0]):
        # 快速路徑：逐字輸出預存答案
        print(f"⚡ [Streaming] 快速路徑觸發 (信心度: {confidence_score:.3f})")
        result = formatter.format_simple_answer(search_results)
        answer = result['answer']

        # 模擬逐字輸出（提升用戶體驗）
        words = answer.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield await generate_sse_event("answer_chunk", {"chunk": chunk})
            await asyncio.sleep(0.02)  # 20ms 延遲，模擬打字效果

    elif 0.55 <= confidence_score < 0.75 and confidence_level in ['high', 'medium']:
        # 模板格式化：逐字輸出
        print(f"📋 [Streaming] 模板格式化觸發 (信心度: {confidence_score:.3f}, 級別: {confidence_level})")
        result = formatter.format_with_template(
            question,
            search_results,
            intent_type=intent_result.get('intent_type')
        )
        answer = result['answer']

        # 逐字輸出
        words = answer.split()
        print(f"📤 [Streaming] 準備輸出 {len(words)} 個詞塊，預計耗時 {len(words) * 20}ms")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield await generate_sse_event("answer_chunk", {"chunk": chunk})
            await asyncio.sleep(0.02)

    else:
        # 完整 LLM 優化 - 使用 OpenAI Streaming API
        print(f"🤖 [Streaming] LLM 串流觸發 (信心度: {confidence_score:.3f}, 級別: {confidence_level})")
        import os
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 準備 prompt
        content = search_results[0].get('content', '') if search_results else ''
        prompt = f"""請根據以下知識回答用戶問題。

用戶問題: {question}

相關知識:
{content}

請提供清晰、準確的答案。"""

        # 使用 streaming API
        stream = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "你是一個專業的客服助手。"},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            temperature=0.7,
            max_tokens=800
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield await generate_sse_event("answer_chunk", {
                    "chunk": chunk.choices[0].delta.content
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
