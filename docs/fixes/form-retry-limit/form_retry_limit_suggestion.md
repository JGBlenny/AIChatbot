# 表單重試次數限制改進建議

## 問題描述

目前當使用者在「電費帳單寄送區間」查詢表單中連續輸入無效地址時，系統會持續要求重新輸入，沒有自動退出機制。使用者必須明確輸入「取消」才能結束表單填寫。

### 現有行為
- 使用者輸入「帳單寄送區間」（無效地址）
- 系統提示錯誤，要求重新輸入
- 使用者再次輸入「帳單寄送區間」
- 系統再次提示錯誤，要求重新輸入
- 循環持續，直到使用者手動輸入「取消」

## 改進方案

### 方案 1：使用 metadata 欄位追蹤重試次數

在 `form_manager.py` 中修改：

```python
# 在 _complete_form 方法中（約第 790-820 行）

async def _complete_form(self, session_state: Dict, form_schema: Dict, collected_data: Dict) -> Dict:
    # ... 現有程式碼 ...

    # 檢查 API 是否返回需要用戶重新輸入的錯誤
    if api_result and not api_result.get('success'):
        error_type = api_result.get('error')

        # 特定錯誤類型：需要用戶重新輸入
        if error_type in ['ambiguous_match', 'no_match', 'invalid_input']:
            # 🆕 從 metadata 獲取重試次數
            metadata = session_state.get('metadata', {})
            retry_count = metadata.get('retry_count', 0)
            max_retries = 2  # 最多重試 2 次

            retry_count += 1

            # 🆕 檢查是否超過重試次數
            if retry_count > max_retries:
                # 自動取消表單
                await self.update_session_state(
                    session_id=session_state['session_id'],
                    state=FormState.CANCELLED
                )

                return {
                    "answer": "❌ **多次輸入無效，已自動取消查詢。**\n\n請確認地址資訊後重新查詢。",
                    "form_completed": False,
                    "form_cancelled": True,
                    "auto_cancelled": True,
                    "reason": "exceeded_retry_limit"
                }

            # 🆕 更新重試次數到 metadata
            metadata['retry_count'] = retry_count
            await self.update_session_state(
                session_id=session_state['session_id'],
                state=FormState.COLLECTING,
                metadata=metadata
            )

            # 獲取當前欄位
            current_field_index = session_state['current_field_index']
            current_field = form_schema['fields'][current_field_index]

            # 返回錯誤訊息 + 重新提示（包含重試次數提示）
            error_message = api_result.get('formatted_response', '輸入無效，請重新輸入。')

            # 🆕 加入重試次數提示
            retry_hint = f"\n\n💡 **提示**：第 {retry_count}/{max_retries} 次重試" if retry_count > 1 else ""

            return {
                "answer": f"{error_message}{retry_hint}\n\n---\n\n{current_field['prompt']}\n\n（或輸入「**取消**」結束填寫）",
                "form_completed": False,
                "needs_retry": True,
                "retry_field": current_field['field_name'],
                "retry_count": retry_count
            }
```

### 方案 2：在 collect_field_data 中加入連續錯誤檢測

```python
# 在 collect_field_data 方法中（約第 629 行）

# 驗證資料格式
is_valid, extracted_value, error_message = self.validator.validate_field(
    field_config=current_field,
    user_input=user_message
)

if not is_valid:
    # 🆕 檢查連續驗證失敗次數
    metadata = session_state.get('metadata', {})
    validation_failures = metadata.get('validation_failures', 0)
    max_failures = 3

    validation_failures += 1

    if validation_failures >= max_failures:
        # 自動取消表單
        await self.update_session_state(
            session_id=session_id,
            state=FormState.CANCELLED
        )
        return {
            "answer": "❌ **多次輸入格式錯誤，已自動結束查詢。**\n\n請檢查您的輸入格式後重新開始。",
            "form_cancelled": True,
            "auto_cancelled": True,
            "reason": "validation_failures"
        }

    # 更新失敗次數
    metadata['validation_failures'] = validation_failures
    await self.update_session_state(
        session_id=session_id,
        metadata=metadata
    )

    failure_hint = f"（第 {validation_failures} 次輸入錯誤）" if validation_failures > 1 else ""

    return {
        "answer": f"{error_message} {failure_hint}\n\n{current_field['prompt']}",
        "validation_failed": True,
        "failure_count": validation_failures
    }
```

### 方案 3：智能型退出建議

偵測使用者連續輸入相同的無效內容時，主動提供退出選項：

```python
# 在 collect_field_data 中加入智能檢測

# 檢查是否與上次輸入相同
metadata = session_state.get('metadata', {})
last_input = metadata.get('last_input', '')

if user_message.strip() == last_input:
    # 使用者輸入了相同的內容
    same_input_count = metadata.get('same_input_count', 0) + 1

    if same_input_count >= 2:
        # 主動提供退出建議
        return {
            "answer": (
                "⚠️ **您已連續輸入相同的內容**\n\n"
                "看起來您可能遇到困難。請選擇：\n"
                "• 輸入「**幫助**」→ 查看輸入範例\n"
                "• 輸入「**取消**」→ 結束查詢\n"
                "• 或重新輸入正確的地址"
            ),
            "suggest_exit": True
        }

    metadata['same_input_count'] = same_input_count
else:
    metadata['same_input_count'] = 0

metadata['last_input'] = user_message.strip()
```

## 建議實施優先順序

1. **方案 1**（高優先級）：最直接解決問題，對於 API 查詢失敗的情況設置重試上限
2. **方案 3**（中優先級）：改善使用者體驗，主動偵測困境並提供幫助
3. **方案 2**（低優先級）：作為補充機制，處理其他類型的驗證失敗

## 預期效果

實施後，當使用者連續輸入無效地址 2-3 次後，系統會：
1. 自動結束表單填寫
2. 提供清楚的錯誤說明
3. 建議使用者確認資料後重新開始

這樣可以避免使用者陷入無限循環，提升使用體驗。

## 額外建議

1. **記錄統計資料**：追蹤自動取消的頻率，幫助優化系統
2. **提供範例**：在多次失敗後，顯示正確的地址格式範例
3. **客服引導**：超過重試次數後，提供客服聯絡方式