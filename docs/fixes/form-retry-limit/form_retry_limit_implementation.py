# 表單重試次數限制實作方案
# 最多允許重試 2 次，之後自動取消表單

# ============================================================================
# 檔案：rag-orchestrator/services/form_manager.py
# 修改位置：_complete_form 方法（約第 762-855 行）
# ============================================================================

async def _complete_form(
    self,
    session_state: Dict,
    form_schema: Dict,
    collected_data: Dict
) -> Dict:
    """完成表單填寫"""
    # 1. ⭐ 新架構：檢查是否需要調用 API（提前執行，檢查結果）
    on_complete_action = form_schema.get('on_complete_action', 'show_knowledge')
    api_config = form_schema.get('api_config')

    # 從知識庫讀取答案（如果有）
    knowledge_answer = None
    knowledge_id = session_state.get('knowledge_id')
    if knowledge_id:
        knowledge_answer = await asyncio.to_thread(
            self._get_knowledge_answer_sync, knowledge_id
        )

    # 2. 執行 API 調用（如果需要）
    api_result = None
    if on_complete_action in ['call_api', 'both'] and api_config:
        print(f"📞 [表單完成] 調用 API: {api_config.get('endpoint')}")
        api_result = await self._execute_form_api(
            api_config=api_config,
            form_data=collected_data,
            session_state=session_state,
            knowledge_answer=knowledge_answer
        )

        # ⚠️ 檢查 API 是否返回需要用戶重新輸入的錯誤
        if api_result and not api_result.get('success'):
            error_type = api_result.get('error')

            # 特定錯誤類型：需要用戶重新輸入（不完成表單）
            if error_type in ['ambiguous_match', 'no_match', 'invalid_input']:

                # ========== 🆕 新增：重試次數限制邏輯 ==========
                # 從 metadata 獲取重試次數
                metadata = session_state.get('metadata', {})
                retry_count = metadata.get('retry_count', 0)
                MAX_RETRIES = 2  # 最多重試 2 次

                # 增加重試次數
                retry_count += 1

                print(f"🔄 [表單重試] API 錯誤類型: {error_type}, 重試次數: {retry_count}/{MAX_RETRIES}")

                # 檢查是否超過重試次數
                if retry_count >= MAX_RETRIES:
                    # 超過重試次數，自動取消表單
                    await self.update_session_state(
                        session_id=session_state['session_id'],
                        state=FormState.CANCELLED
                    )

                    # 根據錯誤類型提供不同的結束訊息
                    cancel_messages = {
                        'no_match': (
                            "❌ **查詢失敗**\n\n"
                            "已嘗試 2 次，仍無法找到匹配的資料。\n\n"
                            "可能原因：\n"
                            "• 輸入的地址不在服務範圍內\n"
                            "• 地址格式不正確\n"
                            "• 該地址尚未登錄在系統中\n\n"
                            "請確認地址資訊後重新查詢，或聯繫客服協助。"
                        ),
                        'ambiguous_match': (
                            "❌ **查詢中斷**\n\n"
                            "連續 2 次無法精確定位您的地址。\n"
                            "請提供更完整的地址資訊（包含樓層、號碼等細節）後重新查詢。"
                        ),
                        'invalid_input': (
                            "❌ **輸入無效**\n\n"
                            "連續 2 次輸入格式錯誤。\n"
                            "請參考正確格式範例後重新開始。"
                        )
                    }

                    cancel_message = cancel_messages.get(
                        error_type,
                        "❌ **查詢已取消**\n\n已達到最大重試次數。請確認資料後重新開始。"
                    )

                    return {
                        "answer": cancel_message,
                        "form_completed": False,
                        "form_cancelled": True,
                        "auto_cancelled": True,
                        "reason": "exceeded_retry_limit",
                        "retry_count": retry_count,
                        "error_type": error_type
                    }

                # 尚未超過重試次數，更新 metadata 並繼續
                metadata['retry_count'] = retry_count
                await self.update_session_state(
                    session_id=session_state['session_id'],
                    state=FormState.COLLECTING,
                    metadata=metadata
                )

                # 獲取當前欄位（最後一個欄位）
                current_field_index = session_state['current_field_index']
                current_field = form_schema['fields'][current_field_index]

                # 根據重試次數調整提示訊息
                error_message = api_result.get('formatted_response', '輸入無效，請重新輸入。')

                # 加入重試次數提示
                if retry_count == 1:
                    retry_hint = "\n\n💡 **提示**：請確認輸入的地址完整且正確（第 1 次重試）"
                else:  # retry_count == 2
                    retry_hint = "\n\n⚠️ **最後一次機會**：請仔細檢查地址格式（最後一次重試）"

                # 組合錯誤訊息
                combined_message = f"{error_message}{retry_hint}\n\n---\n\n{current_field['prompt']}\n\n（或輸入「**取消**」結束填寫）"

                return {
                    "answer": combined_message,
                    "form_completed": False,
                    "needs_retry": True,
                    "retry_field": current_field['field_name'],
                    "retry_count": retry_count,
                    "max_retries": MAX_RETRIES
                }
                # ========== 重試次數限制邏輯結束 ==========

    # 3. API 成功或無需 API，正常完成表單
    # 更新會話狀態為已完成
    await self.update_session_state(
        session_id=session_state['session_id'],
        state=FormState.COMPLETED,
        collected_data=collected_data
    )

    # 4. 保存表單提交記錄
    submission_id = await self.save_form_submission(
        session_id=session_state['id'],
        form_id=session_state['form_id'],
        user_id=session_state['user_id'],
        vendor_id=session_state['vendor_id'],
        submitted_data=collected_data
    )

    # 5. 格式化完成訊息
    triggered_by_knowledge = session_state.get('knowledge_id') is not None
    completion_message = await self._format_completion_message(
        on_complete_action=on_complete_action,
        knowledge_answer=knowledge_answer,
        api_result=api_result,
        triggered_by_knowledge=triggered_by_knowledge
    )

    return {
        "answer": completion_message,
        "form_completed": True,
        "submission_id": submission_id,
        "collected_data": collected_data,
        "api_result": api_result  # 返回 API 結果供外部使用
    }


# ============================================================================
# 額外建議：在成功收集資料時重置重試計數器
# 修改位置：collect_field_data 方法（約第 636 行）
# ============================================================================

# 在成功儲存資料後（第 636-638 行附近）
# 5. 儲存資料
collected_data = session_state['collected_data']
collected_data[current_field['field_name']] = extracted_value
next_field_index = current_field_index + 1

# 🆕 重置重試計數器（成功收集資料）
metadata = session_state.get('metadata', {})
if 'retry_count' in metadata:
    metadata['retry_count'] = 0
    await self.update_session_state(
        session_id=session_id,
        metadata=metadata
    )

# ============================================================================
# 測試案例
# ============================================================================

"""
測試場景 1：連續輸入無效地址
----------------------------------------
使用者：電費帳單寄送區間
系統：請提供完整的物件地址

使用者：帳單寄送區間
系統：❌ 未找到匹配記錄...
     💡 提示：請確認輸入的地址完整且正確（第 1 次重試）
     請提供完整的物件地址

使用者：帳單寄送區間
系統：❌ 查詢失敗
     已嘗試 2 次，仍無法找到匹配的資料。
     [自動取消表單]

測試場景 2：第一次重試後輸入正確地址
----------------------------------------
使用者：電費帳單寄送區間
系統：請提供完整的物件地址

使用者：錯誤地址
系統：❌ 未找到匹配記錄...
     💡 提示：請確認輸入的地址完整且正確（第 1 次重試）

使用者：台北市大安區師大路86巷1號4樓
系統：✅ 查詢成功
     寄送區間：單月

測試場景 3：使用者主動取消
----------------------------------------
使用者：電費帳單寄送區間
系統：請提供完整的物件地址

使用者：取消
系統：已取消表單填寫。
"""