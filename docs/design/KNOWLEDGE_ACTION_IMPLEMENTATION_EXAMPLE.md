# 知識庫動作系統 - 實作範例

> 本文件提供完整的程式碼實作範例

**相關文檔**：
- [完整設計文檔](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [快速參考](./KNOWLEDGE_ACTION_QUICK_REFERENCE.md)

---

## 📋 目錄

1. [API 服務實作](#api-服務實作)
2. [FormManager 擴展](#formmanager-擴展)
3. [Chat 處理邏輯](#chat-處理邏輯)
4. [輔助函數](#輔助函數)
5. [完整範例](#完整範例)

---

## API 服務實作

### services/billing_api.py

```python
"""
帳單查詢 API 服務
整合 JGB 主系統的帳單查詢功能
"""
import httpx
import os
from typing import Optional, Dict, Literal
from datetime import datetime

class BillingAPIService:
    """帳單 API 服務"""

    def __init__(self):
        self.base_url = os.getenv("JGB_BILLING_API_URL", "http://localhost:8080/api/billing")
        self.timeout = 10.0
        self.api_key = os.getenv("JGB_BILLING_API_KEY", "")

    async def get_invoice_status(
        self,
        user_id: str,
        month: Optional[str] = None,
        requester_id: Optional[str] = None,
        requester_role: Literal['tenant', 'landlord', 'customer_service'] = 'tenant'
    ) -> Dict:
        """
        查詢帳單狀態

        Args:
            user_id: 租客 ID
            month: 查詢月份（格式：2026-01），None 則查詢最新一期
            requester_id: 請求者 ID（用於權限驗證）
            requester_role: 請求者角色

        Returns:
            {
                "status": "success" | "error",
                "data": {...} or None,
                "error_code": str (如有錯誤),
                "message": str
            }
        """
        try:
            # 構建請求
            url = f"{self.base_url}/users/{user_id}/invoices"
            params = {}
            if month:
                params['month'] = month
            else:
                params['latest'] = 'true'

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Requester-ID": requester_id or user_id,
                "X-Requester-Role": requester_role
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "message": "查詢成功"
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error_code": "INVOICE_NOT_FOUND",
                    "message": "查無帳單記錄（可能尚未生成）"
                }
            elif e.response.status_code == 403:
                return {
                    "status": "error",
                    "error_code": "PERMISSION_DENIED",
                    "message": "無權限查詢此帳單"
                }
            else:
                return {
                    "status": "error",
                    "error_code": "API_ERROR",
                    "message": f"API 錯誤：{e.response.status_code}"
                }

        except httpx.TimeoutException:
            return {
                "status": "error",
                "error_code": "TIMEOUT",
                "message": "查詢超時，請稍後再試"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_code": "UNKNOWN_ERROR",
                "message": f"系統錯誤：{str(e)}"
            }

    async def verify_tenant_identity(
        self,
        tenant_id: str,
        id_last_4: str
    ) -> Dict:
        """
        驗證租客身份

        Args:
            tenant_id: 租客 ID
            id_last_4: 身份證後 4 碼

        Returns:
            {"success": bool, "message": str}
        """
        try:
            url = f"{self.base_url}/auth/verify"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "tenant_id": tenant_id,
                "id_last_4": id_last_4
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()

                return {
                    "success": True,
                    "message": "身份驗證通過"
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {
                    "success": False,
                    "message": "身份驗證失敗，請確認資料是否正確"
                }
            else:
                return {
                    "success": False,
                    "message": f"驗證失敗：{e.response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"驗證錯誤：{str(e)}"
            }

    async def resend_invoice(
        self,
        invoice_id: str,
        channel: Literal['email', 'sms'] = 'email',
        requester_role: str = 'tenant'
    ) -> Dict:
        """
        重新寄送帳單

        Args:
            invoice_id: 帳單 ID
            channel: 寄送管道（email/sms）
            requester_role: 請求者角色

        Returns:
            {"success": bool, "message": str}
        """
        try:
            url = f"{self.base_url}/invoices/{invoice_id}/resend"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "channel": channel,
                "requester_role": requester_role
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()

                return {
                    "success": True,
                    "message": f"已重新寄送至 {channel}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"重新寄送失敗：{str(e)}"
            }


# === 輔助函數 ===

def extract_month_from_question(question: str) -> Optional[str]:
    """
    從問題中提取月份

    Examples:
        "我1月的帳單" → "2026-01"
        "2025年12月的帳單" → "2025-12"
        "上個月的帳單" → "2025-12" (假設現在是2026-01)
    """
    import re
    from datetime import datetime, timedelta

    # 模式1：「1月」、「01月」
    match = re.search(r'(\d{1,2})月', question)
    if match:
        month_num = int(match.group(1))
        current_year = datetime.now().year
        return f"{current_year}-{month_num:02d}"

    # 模式2：「2025年12月」
    match = re.search(r'(\d{4})年(\d{1,2})月', question)
    if match:
        year = match.group(1)
        month = int(match.group(2))
        return f"{year}-{month:02d}"

    # 模式3：「上個月」
    if '上個月' in question or '上月' in question:
        last_month = datetime.now() - timedelta(days=30)
        return last_month.strftime("%Y-%m")

    # 未提取到 → 返回 None（稍後詢問用戶）
    return None
```

---

## FormManager 擴展

### services/form_manager.py (修改部分)

```python
async def _complete_form(
    self,
    session_state: Dict,
    form_schema: Dict,
    collected_data: Dict
) -> Dict:
    """
    完成表單填寫

    ✨ 新增：支援表單完成後調用 API
    """
    # 1. 更新會話狀態為已完成
    await self.update_session_state(
        session_id=session_state['session_id'],
        state=FormState.COMPLETED,
        collected_data=collected_data
    )

    # 2. 保存表單提交記錄
    submission_id = await self.save_form_submission(
        session_id=session_state['id'],
        form_id=session_state['form_id'],
        user_id=session_state['user_id'],
        vendor_id=session_state['vendor_id'],
        submitted_data=collected_data
    )

    # ✨ 3. 檢查是否需要調用 API
    on_complete_action = form_schema.get('on_complete_action', 'show_knowledge')
    api_config = form_schema.get('api_config')

    if on_complete_action in ['call_api', 'both'] and api_config:
        print(f"📡 表單完成後調用 API：{api_config.get('endpoint')}")

        # 調用 API
        api_result = await self._execute_form_api(
            api_config=api_config,
            collected_data=collected_data,
            session_state=session_state
        )

        # 結合 API 結果與知識庫答案
        completion_message = await self._format_completion_message(
            knowledge_id=session_state.get('knowledge_id'),
            api_result=api_result,
            api_config=api_config
        )

        return {
            "answer": completion_message,
            "form_completed": True,
            "submission_id": submission_id,
            "collected_data": collected_data,
            "api_result": api_result
        }

    else:
        # 原有邏輯：只顯示知識庫答案
        completion_message = "✅ **表單填寫完成！**\n\n感謝您完成表單！"

        knowledge_id = session_state.get('knowledge_id')
        if knowledge_id:
            knowledge_answer = await asyncio.to_thread(
                self._get_knowledge_answer_sync,
                knowledge_id
            )
            if knowledge_answer:
                completion_message = f"✅ **表單填寫完成！**\n\n{knowledge_answer}"

        return {
            "answer": completion_message,
            "form_completed": True,
            "submission_id": submission_id,
            "collected_data": collected_data
        }


async def _execute_form_api(
    self,
    api_config: Dict,
    collected_data: Dict,
    session_state: Dict
) -> Dict:
    """
    執行表單完成後的 API 調用

    Args:
        api_config: API 配置
        collected_data: 表單收集的資料
        session_state: 會話狀態

    Returns:
        API 執行結果
    """
    from services.billing_api import BillingAPIService

    endpoint = api_config.get('endpoint')
    param_mapping = api_config.get('param_mapping', {})

    # 1. 如果需要先驗證身份
    if api_config.get('verify_identity_first'):
        print(f"🔐 執行身份驗證...")
        verify_config = api_config.get('verification_params', {})
        verify_result = await self._verify_user_identity(
            collected_data=collected_data,
            verify_config=verify_config
        )

        if not verify_result['success']:
            return {
                "status": "error",
                "error_code": "IDENTITY_VERIFICATION_FAILED",
                "message": verify_result['message']
            }

        print(f"✅ 身份驗證通過")

    # 2. 映射表單資料到 API 參數
    api_params = {}
    for api_param_name, form_field_name in param_mapping.items():
        # 支援從 session 取值（如 session.user_id）
        if form_field_name.startswith('session.'):
            field_key = form_field_name.replace('session.', '')
            api_params[api_param_name] = session_state.get(field_key)
        else:
            api_params[api_param_name] = collected_data.get(form_field_name)

    # 3. 調用對應的 API
    try:
        if endpoint == 'billing_inquiry':
            billing_service = BillingAPIService()
            result = await billing_service.get_invoice_status(
                user_id=api_params.get('user_id'),
                month=api_params.get('month'),
                requester_role='tenant'
            )
            return result

        elif endpoint == 'repair_submit':
            # TODO: 實作報修 API
            return {
                "status": "success",
                "data": {
                    "ticket_id": "R-2026-001",
                    "estimated_time": "24小時內"
                }
            }

        else:
            return {
                "status": "error",
                "error_code": "UNKNOWN_ENDPOINT",
                "message": f"未知的 API 端點: {endpoint}"
            }

    except Exception as e:
        print(f"❌ API 調用失敗: {e}")
        return {
            "status": "error",
            "error_code": "API_CALL_FAILED",
            "message": f"API 調用失敗: {str(e)}"
        }


async def _verify_user_identity(
    self,
    collected_data: Dict,
    verify_config: Dict
) -> Dict:
    """
    驗證用戶身份

    Args:
        collected_data: 表單收集的資料
        verify_config: 驗證配置

    Returns:
        {"success": bool, "message": str}
    """
    from services.billing_api import BillingAPIService

    tenant_id = collected_data.get(verify_config.get('tenant_id'))
    id_last_4 = collected_data.get(verify_config.get('id_last_4'))

    if not tenant_id or not id_last_4:
        return {
            "success": False,
            "message": "缺少驗證所需資料"
        }

    # 調用身份驗證 API
    billing_service = BillingAPIService()
    result = await billing_service.verify_tenant_identity(tenant_id, id_last_4)

    return result


async def _format_completion_message(
    self,
    knowledge_id: Optional[int],
    api_result: Dict,
    api_config: Dict
) -> str:
    """
    格式化完成訊息（結合知識庫答案與 API 結果）

    Args:
        knowledge_id: 知識 ID
        api_result: API 結果
        api_config: API 配置

    Returns:
        格式化後的訊息
    """
    # 1. 獲取知識庫答案
    knowledge_answer = ""
    if knowledge_id:
        knowledge_answer = await asyncio.to_thread(
            self._get_knowledge_answer_sync,
            knowledge_id
        )

    # 2. 根據 API 結果格式化
    if api_result['status'] == 'success':
        # 使用配置的成功模板
        response_template = api_config.get(
            'response_template',
            '✅ **表單填寫完成！**\n\n{api_response}\n\n{knowledge_answer}'
        )

        # 格式化 API 回應
        api_response_text = self._format_api_response(api_result['data'])

        return response_template.format(
            api_response=api_response_text,
            knowledge_answer=knowledge_answer
        )
    else:
        # API 失敗，使用降級訊息
        fallback_message = api_config.get(
            'fallback_message',
            '✅ 表單已提交\n\n{knowledge_answer}\n\n⚠️ 但目前無法查詢結果：{error}'
        )

        return fallback_message.format(
            knowledge_answer=knowledge_answer,
            error=api_result.get('message', '未知錯誤')
        )


def _format_api_response(self, api_data: Dict) -> str:
    """格式化 API 回應為友好的文字"""
    # 根據不同的 API 類型格式化
    if 'invoice_id' in api_data:
        # 帳單查詢結果
        delivery = api_data.get('delivery_status', {})
        return f"""查詢結果：

📄 帳單編號：{api_data.get('invoice_id')}
💰 金額：${api_data.get('amount', 0):,}
📅 到期日：{api_data.get('due_date')}

{self._format_delivery_status(delivery)}"""

    elif 'ticket_id' in api_data:
        # 報修結果
        return f"""🔧 報修單號：{api_data.get('ticket_id')}
📅 預計處理時間：{api_data.get('estimated_time')}"""

    # 其他類型...
    return str(api_data)


def _format_delivery_status(self, delivery: Dict) -> str:
    """格式化寄送狀態"""
    if delivery.get('email_sent'):
        status = "✅ 已寄送"
        sent_at = delivery.get('sent_at', 'N/A')
        email = self._mask_email(delivery.get('email', ''))

        return f"""寄送狀態：{status}
寄送時間：{sent_at}
寄送信箱：{email}

建議檢查：
1️⃣ 郵件垃圾信件夾
2️⃣ 搜尋寄件者「JGB租屋平台」"""
    else:
        return "📧 尚未寄送"


def _mask_email(self, email: str) -> str:
    """Email 遮罩"""
    if not email or '@' not in email:
        return email
    local, domain = email.split('@')
    if len(local) <= 3:
        masked_local = local[0] + '***'
    else:
        masked_local = local[:2] + '***' + local[-1]
    return f"{masked_local}@{domain}"
```

---

## Chat 處理邏輯

### routers/chat.py (修改部分)

```python
async def _build_knowledge_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    knowledge_list: list,
    resolver,
    vendor_info: dict,
    cache_service
) -> VendorChatResponse:
    """使用知識庫結果構建優化回應"""

    if not knowledge_list:
        return await _handle_no_knowledge_found(...)

    best_knowledge = knowledge_list[0]
    action_type = best_knowledge.get('action_type', 'direct_answer')

    print(f"🎯 知識 {best_knowledge['id']} 的 action_type: {action_type}")

    # === 決策樹 ===

    if action_type == 'direct_answer':
        # 場景 A：純知識問答
        print(f"📖 使用純知識問答模式")
        # 使用現有的知識庫回答邏輯
        # ... (現有代碼)
        pass

    elif action_type == 'form_fill':
        # 場景 B：觸發表單
        form_id = best_knowledge.get('form_id')
        if not form_id:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=form_fill but no form_id")

        print(f"📝 觸發表單：{form_id}")
        # 使用現有的表單觸發邏輯
        # ... (現有代碼)
        pass

    elif action_type == 'api_call':
        # 場景 C/F：直接調用 API
        api_config = best_knowledge.get('api_config')
        if not api_config:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=api_call but no api_config")

        print(f"📡 調用 API：{api_config.get('endpoint')}")

        # 檢查參數是否齊全
        params_check = await _check_api_params(api_config, request)

        if not params_check['all_ready']:
            # 缺少參數 → 詢問用戶
            print(f"⚠️ 缺少參數：{params_check['missing']}")
            return _ask_missing_params(
                params_check['missing'],
                request,
                intent_result
            )

        # 參數齊全 → 調用 API
        api_result = await _call_api(
            api_config,
            params_check['params'],
            request
        )

        # 格式化回應
        combine_knowledge = api_config.get('combine_with_knowledge', True)
        if combine_knowledge and best_knowledge.get('answer'):
            return _format_api_with_knowledge(
                api_result,
                best_knowledge,
                api_config,
                request,
                intent_result
            )
        else:
            return _format_api_only(
                api_result,
                api_config,
                request,
                intent_result
            )

    elif action_type == 'form_then_api':
        # 場景 D/E：先表單後 API
        form_id = best_knowledge.get('form_id')
        if not form_id:
            raise ValueError(f"Knowledge {best_knowledge['id']} has action_type=form_then_api but no form_id")

        print(f"📝➡️📡 表單後調用 API：{form_id}")

        # 觸發表單（表單完成後會自動調用 API）
        # 使用現有的表單觸發邏輯
        # ... (現有代碼)
        pass

    else:
        raise ValueError(f"Unknown action_type: {action_type}")


async def _check_api_params(
    api_config: Dict,
    request: VendorChatRequest
) -> Dict:
    """
    檢查 API 參數是否齊全

    Returns:
        {
            "all_ready": bool,
            "params": dict,
            "missing": list
        }
    """
    params_config = api_config.get('params', {})
    params = {}
    missing = []

    for param_name, param_source in params_config.items():
        if param_source.startswith('{') and param_source.endswith('}'):
            # 從變數取值
            source = param_source[1:-1]  # 去掉 {}

            if source.startswith('session.'):
                # 從 session 取值
                key = source.replace('session.', '')
                value = getattr(request, key, None)
                if value:
                    params[param_name] = value
                else:
                    missing.append(param_name)

            elif source.startswith('form.'):
                # 從表單取值（這裡應該不會發生，因為 form 的由表單系統處理）
                missing.append(param_name)

            elif source.startswith('user_input.'):
                # 需要用戶輸入
                missing.append(param_name)
        else:
            # 固定值
            params[param_name] = param_source

    return {
        "all_ready": len(missing) == 0,
        "params": params,
        "missing": missing
    }


async def _call_api(
    api_config: Dict,
    params: Dict,
    request: VendorChatRequest
) -> Dict:
    """調用 API"""
    from services.billing_api import BillingAPIService

    endpoint = api_config.get('endpoint')

    try:
        if endpoint == 'billing_inquiry':
            billing_service = BillingAPIService()
            result = await billing_service.get_invoice_status(
                user_id=params.get('user_id'),
                month=params.get('month'),
                requester_id=request.user_id,
                requester_role='tenant'
            )
            return result
        else:
            return {
                "status": "error",
                "error_code": "UNKNOWN_ENDPOINT",
                "message": f"未知的 API 端點: {endpoint}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error_code": "API_CALL_FAILED",
            "message": f"API 調用失敗: {str(e)}"
        }


def _format_api_with_knowledge(
    api_result: Dict,
    knowledge: Dict,
    api_config: Dict,
    request: VendorChatRequest,
    intent_result: dict
) -> VendorChatResponse:
    """格式化 API 結果 + 知識答案"""

    if api_result['status'] == 'success':
        # 成功：使用模板格式化
        template = api_config.get(
            'response_template',
            '{api_response}\n\n{knowledge_answer}'
        )

        # 格式化 API 回應（簡化版）
        api_response_text = str(api_result['data'])

        final_answer = template.format(
            api_response=api_response_text,
            knowledge_answer=knowledge['answer']
        )
    else:
        # 失敗：使用降級訊息
        fallback = api_config.get(
            'fallback_message',
            '目前無法查詢。\n\n{knowledge_answer}'
        )
        final_answer = fallback.format(
            knowledge_answer=knowledge['answer']
        )

    return VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        confidence=intent_result['confidence'],
        vendor_id=request.vendor_id,
        mode=request.mode,
        timestamp=datetime.utcnow().isoformat()
    )


def _format_api_only(
    api_result: Dict,
    api_config: Dict,
    request: VendorChatRequest,
    intent_result: dict
) -> VendorChatResponse:
    """只格式化 API 結果（不結合知識答案）"""

    if api_result['status'] == 'success':
        template = api_config.get(
            'response_template',
            '{api_response}'
        )
        final_answer = template.format(
            api_response=str(api_result['data'])
        )
    else:
        fallback = api_config.get(
            'fallback_message',
            '目前無法查詢，請稍後再試。'
        )
        final_answer = fallback

    return VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        confidence=intent_result['confidence'],
        vendor_id=request.vendor_id,
        mode=request.mode,
        timestamp=datetime.utcnow().isoformat()
    )


def _ask_missing_params(
    missing_params: list,
    request: VendorChatRequest,
    intent_result: dict
) -> VendorChatResponse:
    """詢問缺少的參數"""

    # 簡化版：只詢問第一個缺少的參數
    param = missing_params[0]

    prompts = {
        'month': '請問查詢哪個月份的帳單？（例如：2026-01）',
        'user_id': '請提供您的租客編號：',
        'phone': '請提供您的聯絡電話：'
    }

    prompt = prompts.get(param, f'請提供 {param}：')

    return VendorChatResponse(
        answer=prompt,
        intent_name=intent_result['intent_name'],
        confidence=intent_result['confidence'],
        vendor_id=request.vendor_id,
        mode=request.mode,
        timestamp=datetime.utcnow().isoformat()
    )
```

---

## 輔助函數

### 格式化帳單資訊

```python
def format_invoice_info(invoice_data: Dict) -> str:
    """格式化帳單資訊為友好文字"""

    delivery = invoice_data.get('delivery_status', {})

    result = f"""📄 **帳單詳情**

帳單編號：{invoice_data.get('invoice_id', 'N/A')}
金額：${invoice_data.get('amount', 0):,}
到期日：{format_date(invoice_data.get('due_date'))}

"""

    # 寄送狀態
    if delivery.get('email_sent'):
        result += f"""✅ **寄送狀態：已寄送**
寄送時間：{format_datetime(delivery.get('sent_at'))}
寄送信箱：{mask_email(delivery.get('email', ''))}

"""

        if delivery.get('email_opened'):
            result += "📧 郵件已開啟\n"
        else:
            result += "📧 郵件尚未開啟（建議檢查垃圾郵件夾）\n"

    elif delivery.get('email_bounced'):
        result += f"""⚠️ **寄送狀態：退信**
原因：{delivery.get('bounce_reason', '未知')}
系統信箱：{mask_email(delivery.get('email', ''))}

請更新您的聯絡信箱。
"""

    else:
        result += f"""⏳ **寄送狀態：尚未寄送**
預計寄送：{format_date(invoice_data.get('scheduled_send_date'))}
"""

    return result


def format_date(date_str: str) -> str:
    """格式化日期：2026-01-15 → 01/15"""
    if not date_str:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%m/%d")
    except:
        return date_str


def format_datetime(dt_str: str) -> str:
    """格式化時間：2026-01-10T10:00:00Z → 01/10 10:00"""
    if not dt_str:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%m/%d %H:%M")
    except:
        return dt_str


def mask_email(email: str) -> str:
    """遮罩 Email：wang@example.com → wang_***@example.com"""
    if not email or '@' not in email:
        return email

    local, domain = email.split('@')
    if len(local) <= 3:
        masked_local = local[0] + '***'
    else:
        masked_local = local[:2] + '***' + local[-1]

    return f"{masked_local}@{domain}"
```

---

## 完整範例

### 範例：帳單查詢完整流程

```python
# === 1. 資料庫配置 ===

# 知識庫
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    api_config,
    scope
) VALUES (
    '帳單寄送狀態查詢（未登入）',
    '如仍未收到，建議檢查垃圾郵件或聯繫客服 {{service_hotline}}。',
    'form_then_api',
    'billing_inquiry_guest',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "verification_code"
        },
        "param_mapping": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true,
        "response_template": "✅ 身份驗證通過！\n\n{api_response}\n\n{knowledge_answer}"
    }'::jsonb,
    'global'
);

# 表單
INSERT INTO form_schemas (
    form_id,
    form_name,
    fields,
    on_complete_action,
    api_config
) VALUES (
    'billing_inquiry_guest',
    '帳單查詢（訪客）',
    '[
        {
            "name": "tenant_id",
            "label": "租客編號（合約上的編號）",
            "type": "text",
            "required": true
        },
        {
            "name": "verification_code",
            "label": "身份證後4碼",
            "type": "text",
            "required": true
        },
        {
            "name": "inquiry_month",
            "label": "查詢月份（例如：2026-01）",
            "type": "text",
            "required": true
        }
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "verification_code"
        },
        "param_mapping": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true
    }'::jsonb
);


# === 2. 使用流程 ===

# 第一輪：觸發表單
POST /api/v1/message
{
  "message": "我的帳單怎麼沒收到",
  "vendor_id": 1,
  "session_id": "test_session"
}

# 回應：
{
  "answer": "為了保護您的隱私，需要驗證身份。\n\n請提供租客編號（合約上的編號）：",
  "form_triggered": true,
  "form_id": "billing_inquiry_guest"
}

# 第二輪：填寫租客編號
POST /api/v1/message
{
  "message": "T12345",
  "vendor_id": 1,
  "session_id": "test_session"
}

# 回應：
{
  "answer": "請提供身份證後4碼："
}

# 第三輪：填寫身份證
POST /api/v1/message
{
  "message": "1234",
  "vendor_id": 1,
  "session_id": "test_session"
}

# 回應：
{
  "answer": "請提供查詢月份（例如：2026-01）："
}

# 第四輪：填寫月份（表單完成）
POST /api/v1/message
{
  "message": "2026-01",
  "vendor_id": 1,
  "session_id": "test_session"
}

# 回應（表單完成 → 驗證身份 → 調用 API）：
{
  "answer": "✅ 身份驗證通過！\n\n📄 **帳單詳情**\n\n帳單編號：INV-2026-01-001\n金額：$15,000\n到期日：01/05\n\n✅ **寄送狀態：已寄送**\n寄送時間：01/01 10:00\n寄送信箱：user_***@example.com\n\n📧 郵件尚未開啟（建議檢查垃圾郵件夾）\n\n如仍未收到，建議檢查垃圾郵件或聯繫客服 02-1234-5678。",
  "form_completed": true,
  "api_result": {...}
}
```

---

## 環境變數配置

```.env
# 帳單 API 配置
JGB_BILLING_API_URL=http://jgb-main-api:8080/api/billing
JGB_BILLING_API_KEY=your_api_key_here

# 其他 API 配置
JGB_REPAIR_API_URL=http://jgb-main-api:8080/api/repair
```

---

## 測試範例

```python
# tests/test_billing_inquiry.py

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_billing_inquiry_complete_flow():
    """測試完整的帳單查詢流程（未登入用戶）"""

    session_id = "test_session_001"

    # 1. 觸發查詢（應該觸發表單）
    response = client.post("/api/v1/message", json={
        "message": "我的帳單怎麼沒收到",
        "vendor_id": 1,
        "session_id": session_id
    })

    assert response.status_code == 200
    data = response.json()
    assert "租客編號" in data['answer']
    assert data.get('form_triggered') == True

    # 2. 填寫租客編號
    response = client.post("/api/v1/message", json={
        "message": "T12345",
        "vendor_id": 1,
        "session_id": session_id
    })

    assert "身份證後4碼" in response.json()['answer']

    # 3. 填寫身份證
    response = client.post("/api/v1/message", json={
        "message": "1234",
        "vendor_id": 1,
        "session_id": session_id
    })

    assert "月份" in response.json()['answer']

    # 4. 填寫月份（表單完成，應該調用 API）
    response = client.post("/api/v1/message", json={
        "message": "2026-01",
        "vendor_id": 1,
        "session_id": session_id
    })

    data = response.json()
    assert response.status_code == 200
    assert data.get('form_completed') == True
    assert "帳單編號" in data['answer'] or "無法查詢" in data['answer']
```

---

**文檔結束**

如有問題或需要補充，請參考：
- [完整設計文檔](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [快速參考](./KNOWLEDGE_ACTION_QUICK_REFERENCE.md)
