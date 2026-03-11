"""
API 調用處理器

統一處理知識庫和表單系統中的 API 調用需求：
- 解析 api_config 配置
- 動態參數替換（從 session, form, user_input 等）
- 調用具體的 API 服務
- 錯誤處理和降級策略
- 格式化 API 響應

相關文檔：docs/design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md
"""

import os
import re
from typing import Dict, Any, Optional, Tuple
import logging
from asyncpg.pool import Pool

# 導入具體的 API 服務（根據需要擴展）
from .billing_api import BillingAPIService
from .universal_api_handler import UniversalAPICallHandler

logger = logging.getLogger(__name__)


class APICallHandler:
    """API 調用處理器"""

    def __init__(self, db_pool: Optional[Pool] = None):
        """
        初始化 API 服務

        Args:
            db_pool: 數據庫連接池（可選）
                    - 如果提供，支持動態配置的 API
                    - 如果不提供，僅支持自定義代碼實作的 API
        """
        self.db_pool = db_pool
        self.billing_api = BillingAPIService()

        # 初始化通用 API 處理器（用於動態配置的 API）
        self.universal_handler = UniversalAPICallHandler(db_pool) if db_pool else None

        # API endpoint 映射到具體服務（自定義代碼實作的 API）
        self.api_registry = {
            'billing_inquiry': self.billing_api.get_invoice_status,
            'verify_tenant_identity': self.billing_api.verify_tenant_identity,
            'resend_invoice': self.billing_api.resend_invoice,
            'maintenance_request': self.billing_api.submit_maintenance_request,
            'lookup': self._handle_lookup_api,  # 內部 lookup API 處理器
        }

    async def execute_api_call(
        self,
        api_config: Dict[str, Any],
        session_data: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        user_input: Optional[Dict[str, Any]] = None,
        knowledge_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 API 調用

        Args:
            api_config: API 配置（從 knowledge_base.api_config 或 form_schemas.api_config）
            session_data: 會話數據（包含 user_id, vendor_id, session_id 等）
            form_data: 表單收集的數據
            user_input: 用戶輸入的其他參數
            knowledge_answer: 知識庫答案（用於 combine_with_knowledge）

        Returns:
            {
                'success': True/False,
                'data': API 響應數據,
                'formatted_response': 格式化的回應訊息,
                'error': 錯誤訊息（如果失敗）
            }
        """
        try:
            # 1. 驗證配置
            endpoint = api_config.get('endpoint')
            if not endpoint:
                return self._error_response("API 配置缺少 endpoint")

            # 2. 從數據庫載入 endpoint 配置（如果有 db_pool）
            endpoint_config = None
            if self.db_pool:
                endpoint_config = await self._load_endpoint_config(endpoint)

            # 3. 判斷使用動態處理還是自定義處理
            if endpoint_config and endpoint_config.get('implementation_type') == 'dynamic':
                # 使用動態配置的通用處理器
                logger.info(f"🔄 使用動態處理器調用 API: {endpoint}")

                if not self.universal_handler:
                    return self._error_response("動態 API 處理器未初始化（缺少 db_pool）")

                # 處理 params_from_form 映射（將表單欄位名映射到 API 參數名）
                params_from_form = api_config.get('params_from_form', {})
                if params_from_form and form_data:
                    mapped_form_data = {}
                    for api_param, form_field in params_from_form.items():
                        if form_field in form_data:
                            mapped_form_data[api_param] = form_data[form_field]
                            logger.debug(f"  映射參數: {form_field} → {api_param} = {form_data[form_field]}")
                    # 合併 static_params（如果尚未合併）
                    static_params = api_config.get('static_params', {})
                    for key, value in static_params.items():
                        if key not in mapped_form_data:
                            mapped_form_data[key] = value
                    form_data = mapped_form_data
                    logger.info(f"📝 映射後的表單資料: {form_data}")

                return await self.universal_handler.execute_api_call(
                    endpoint_id=endpoint,
                    session_data=session_data,
                    form_data=form_data,
                    user_input=user_input,
                    knowledge_answer=knowledge_answer
                )

            # 4. 使用自定義代碼實作的處理器
            logger.info(f"⚙️ 使用自定義處理器調用 API: {endpoint}")

            if endpoint not in self.api_registry:
                return self._error_response(f"不支援的 API endpoint: {endpoint}")

            # 5. 身份驗證（如果需要）
            if api_config.get('verify_identity_first'):
                verification_result = await self._verify_identity(
                    api_config, session_data, form_data
                )
                if not verification_result['success']:
                    return verification_result

            # 6. 準備參數
            params = self._prepare_params(
                api_config, session_data, form_data, user_input
            )

            # 確保 vendor_id 在參數中（從 session_data 獲取）
            if 'vendor_id' not in params and session_data and 'vendor_id' in session_data:
                params['vendor_id'] = session_data['vendor_id']

            logger.info(f"🔌 調用 API: {endpoint}, 參數: {params}")

            # 7. 調用 API
            api_function = self.api_registry[endpoint]
            api_result = await api_function(**params)

            # 8. 格式化響應
            formatted_response = self._format_response(
                api_config, api_result, knowledge_answer
            )

            return {
                'success': True,
                'data': api_result,
                'formatted_response': formatted_response
            }

        except Exception as e:
            logger.error(f"❌ API 調用失敗: {e}", exc_info=True)
            return self._error_response(
                f"API 調用失敗: {str(e)}",
                fallback_message=api_config.get('fallback_message'),
                knowledge_answer=knowledge_answer
            )

    async def _verify_identity(
        self,
        api_config: Dict[str, Any],
        session_data: Optional[Dict[str, Any]],
        form_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行身份驗證"""
        verification_params = api_config.get('verification_params', {})

        # 準備驗證參數
        params = {}
        for api_param, source_field in verification_params.items():
            value = self._resolve_param_value(
                source_field, session_data, form_data, {}
            )
            if not value:
                return self._error_response(f"身份驗證參數缺失: {api_param}")
            params[api_param] = value

        logger.info(f"🔐 執行身份驗證，參數: {params}")

        # 調用驗證 API
        verify_result = await self.billing_api.verify_tenant_identity(**params)

        if not verify_result.get('verified'):
            return self._error_response(
                verify_result.get('message', '身份驗證失敗，請確認您的資訊是否正確')
            )

        return {'success': True}

    def _prepare_params(
        self,
        api_config: Dict[str, Any],
        session_data: Optional[Dict[str, Any]],
        form_data: Optional[Dict[str, Any]],
        user_input: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """準備 API 參數"""
        params = {}

        # 方式 1: 從固定的 params 或 static_params 配置取得
        static_params = api_config.get('params', {}) or api_config.get('static_params', {})
        for api_param, param_value in static_params.items():
            resolved_value = self._resolve_param_value(
                param_value, session_data, form_data, user_input
            )
            if resolved_value is not None:
                params[api_param] = resolved_value
            else:
                # 如果無法解析，直接使用原值（支持靜態值）
                params[api_param] = param_value

        # 方式 2: 從 params_from_form 映射取得
        params_from_form = api_config.get('params_from_form', {})
        for api_param, form_field in params_from_form.items():
            # 檢查是否為模板語法
            if isinstance(form_field, str) and '{' in form_field:
                # 使用 _resolve_param_value 解析模板
                resolved_value = self._resolve_param_value(
                    form_field, session_data, form_data, user_input
                )
                if resolved_value is not None:
                    params[api_param] = resolved_value
            elif form_data and form_field in form_data:
                # 直接從 form_data 獲取
                params[api_param] = form_data[form_field]

        return params

    def _resolve_param_value(
        self,
        param_value: Any,
        session_data: Optional[Dict[str, Any]],
        form_data: Optional[Dict[str, Any]],
        user_input: Optional[Dict[str, Any]]
    ) -> Any:
        """
        解析參數值

        支援的語法：
        - {session.user_id} - 從 session 取得
        - {form.field_name} - 從表單取得
        - {user_input.field} - 從用戶輸入取得
        - {vendor.id} - 從業者配置取得
        - 其他 - 直接返回原值
        """
        if not isinstance(param_value, str):
            return param_value

        # 檢查是否為模板語法
        if not ('{' in param_value and '}' in param_value):
            return param_value

        # {session.xxx}
        session_match = re.match(r'\{session\.(\w+)\}', param_value)
        if session_match:
            field = session_match.group(1)
            return session_data.get(field) if session_data else None

        # {form.xxx}
        form_match = re.match(r'\{form\.(\w+)\}', param_value)
        if form_match:
            field = form_match.group(1)
            return form_data.get(field) if form_data else None

        # {user_input.xxx}
        input_match = re.match(r'\{user_input\.(\w+)\}', param_value)
        if input_match:
            field = input_match.group(1)
            return user_input.get(field) if user_input else None

        # {vendor.xxx}
        vendor_match = re.match(r'\{vendor\.(\w+)\}', param_value)
        if vendor_match:
            field = vendor_match.group(1)
            if session_data and field == 'id':
                return session_data.get('vendor_id')

        # 如果無法解析，返回原值
        return param_value

    def _format_response(
        self,
        api_config: Dict[str, Any],
        api_result: Dict[str, Any],
        knowledge_answer: Optional[str]
    ) -> str:
        """格式化 API 響應"""
        combine_with_knowledge = api_config.get('combine_with_knowledge', True)
        response_template = api_config.get('response_template')

        # 格式化 API 結果
        if response_template:
            # 使用自訂模板
            api_response_text = response_template.format(
                api_response=self._format_api_data(api_result)
            )
        else:
            # 使用默認格式
            api_response_text = self._format_api_data(api_result)

        # 是否合併知識答案
        if combine_with_knowledge and knowledge_answer:
            return f"{api_response_text}\n\n---\n\n{knowledge_answer}"
        else:
            return api_response_text

    def _format_api_data(self, api_result) -> str:
        """
        格式化 API 數據為易讀文本

        支援兩種方式：
        1. API 返回 'message' 欄位 → 直接使用
        2. API 只返回原始數據 → 自動格式化
        """
        # 處理字符串結果（例如：ticket ID）
        if isinstance(api_result, str):
            return api_result

        # 處理字典結果
        if isinstance(api_result, dict):
            # 方式 1: 如果 API 結果已經包含格式化的訊息
            if 'message' in api_result:
                return api_result['message']

            # 方式 2: 自動格式化原始數據
            # 檢查是否為錯誤響應
            if not api_result.get('success', True):
                return self._format_error_data(api_result)

            # 正常數據格式化
            return self._format_success_data(api_result)

        # 其他類型直接轉字符串
        return str(api_result)

    def _format_success_data(self, api_result: dict) -> str:
        """格式化成功的 API 數據"""
        # 特殊處理：如果結果已經包含 formatted_response，直接使用
        if 'formatted_response' in api_result:
            return api_result['formatted_response']

        lines = ['✅ **查詢成功**\n']

        # 欄位中文映射（可自訂）
        field_mapping = {
            'invoice_id': '帳單編號',
            'month': '帳單月份',
            'amount': '金額',
            'status': '狀態',
            'sent_date': '發送日期',
            'due_date': '到期日',
            'email': '發送郵箱',
            'ticket_id': '工單編號',
            'order_id': '訂單編號',
        }

        # 需要特殊格式化的欄位
        for key, value in api_result.items():
            if key in ['success', 'verified', 'error', 'formatted_response']:
                continue

            # 使用中文標籤（如果有映射）
            label = field_mapping.get(key, key.replace('_', ' ').title())

            # 特殊格式化
            if key == 'amount':
                formatted_value = f'NT$ {value:,}'
            else:
                formatted_value = value

            lines.append(f'📌 **{label}**: {formatted_value}')

        return '\n'.join(lines)

    def _format_error_data(self, api_result: dict) -> str:
        """格式化錯誤的 API 數據"""
        error_type = api_result.get('error_type', '查詢失敗')

        lines = [f'⚠️ **{error_type}**\n']

        # 添加其他錯誤相關信息
        if 'suggestion' in api_result:
            lines.append(f'💡 {api_result["suggestion"]}')

        if 'next_send_date' in api_result:
            lines.append(f'📅 預計發送日期：{api_result["next_send_date"]}')

        if 'error' in api_result and api_result['error'] not in api_result.get('error_type', ''):
            lines.append(f'\n錯誤代碼：{api_result["error"]}')

        return '\n'.join(lines)

    def _error_response(
        self,
        error_message: str,
        fallback_message: Optional[str] = None,
        knowledge_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """構建錯誤響應"""
        if fallback_message:
            # 使用降級訊息
            formatted_message = fallback_message
            if knowledge_answer and '{knowledge_answer}' in fallback_message:
                formatted_message = fallback_message.replace(
                    '{knowledge_answer}', knowledge_answer
                )
            elif knowledge_answer:
                formatted_message = f"{fallback_message}\n\n{knowledge_answer}"
        else:
            # 默認錯誤訊息
            formatted_message = f"❌ {error_message}"
            if knowledge_answer:
                formatted_message += f"\n\n{knowledge_answer}"

        return {
            'success': False,
            'error': error_message,
            'formatted_response': formatted_message
        }

    async def _handle_lookup_api(
        self,
        category: str,
        key: str,
        vendor_id: int,
        key2: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        內部處理 lookup API 調用（直接查詢數據庫，避免 HTTP 調用）

        Args:
            category: 查詢類別
            key: 查詢鍵
            vendor_id: 業者 ID
            key2: 第二查詢鍵（可選）

        Returns:
            {success: bool, data: dict, formatted_response: str}
        """
        try:
            if not category or not key or not vendor_id:
                return self._error_response(
                    f"缺少必要參數: category={category}, key={key}, vendor_id={vendor_id}"
                )

            # 檢查是否要查詢「全部」
            # 注意：只有當 key2 明確指定為「全部」等關鍵字時才啟用「查詢全部」模式
            # 如果 key2 為 None，表示這是單鍵查詢（如廠商查詢），應該精確查詢 key
            query_all = (
                key2 is not None and  # key2 必須存在
                (
                    key2.strip() == '' or  # key2 只有空白
                    key2.strip() in ['全部', '所有', '全部設施', '所有設施', '全部資料', '所有資料', '全', '所', '*']
                )
            )

            # 組合查詢鍵
            lookup_key = f"{key}_{key2}" if key2 and not query_all else key

            logger.info(f"🔍 內部 Lookup 查詢: category={category}, key={lookup_key}, vendor_id={vendor_id}, query_all={query_all}, key2={key2}")

            # ===== 特殊情況: 查詢「全部」(key 下的所有記錄) =====
            if query_all:
                logger.info(f"📋 查詢全部 | key={key}, category={category}")
                async with self.db_pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT lookup_key, lookup_value, metadata
                        FROM lookup_tables
                        WHERE vendor_id = $1
                          AND category = $2
                          AND lookup_key LIKE $3
                          AND is_active = true
                        ORDER BY lookup_key
                    """, vendor_id, category, f"{key}_%")

                    if not rows:
                        logger.warning(f"⚠️ 查無資料 | key={key}, category={category}")
                        return {
                            'success': False,
                            'error': 'no_data',
                            'formatted_response': f"❌ 查詢失敗\n\n找不到 [{key}] 的任何資料。"
                        }

                    # 格式化所有結果
                    items_formatted = []
                    for idx, row in enumerate(rows, 1):
                        result_value = row['lookup_value']
                        items_formatted.append(f"**{idx}. {result_value.split(chr(10))[0] if result_value else '項目'}**\n\n{result_value}")

                    formatted_response = f"✅ 查詢成功\n\n共找到 {len(rows)} 個設施：\n\n" + "\n\n---\n\n".join(items_formatted)

                    logger.info(f"✅ 查詢全部成功 | 找到 {len(rows)} 筆資料")
                    return {
                        'success': True,
                        'data': {
                            'total': len(rows),
                            'items': [dict(row) for row in rows],
                            'category': category,
                            'key': key
                        },
                        'formatted_response': formatted_response
                    }

            # ===== 正常情況: 精確查詢 =====
            # 查詢數據庫
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT lookup_value, metadata
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND lookup_key = $3
                      AND is_active = true
                """, vendor_id, category, lookup_key)

                if row:
                    # 成功找到
                    logger.info(f"✅ Lookup 查詢成功")
                    result_value = row['lookup_value']
                    metadata = row['metadata'] if row['metadata'] else {}

                    return {
                        'success': True,
                        'data': {
                            'value': result_value,
                            'metadata': metadata,
                            'category': category,
                            'key': lookup_key
                        },
                        'formatted_response': f"✅ 查詢成功\n\n{result_value}"
                    }
                else:
                    # 未找到
                    logger.warning(f"⚠️ Lookup 查詢無結果")
                    return {
                        'success': False,
                        'error': 'no_match',
                        'formatted_response': '❌ 查詢失敗\n\n請確認地址是否正確，或聯繫客服協助查詢。'
                    }

        except Exception as e:
            logger.error(f"❌ Lookup API 調用失敗: {str(e)}")
            return self._error_response(f"查詢失敗: {str(e)}")

    async def _load_endpoint_config(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        從數據庫載入 endpoint 配置

        Args:
            endpoint_id: API endpoint ID

        Returns:
            配置字典，如果不存在返回 None
        """
        if not self.db_pool:
            return None

        try:
            query = """
                SELECT implementation_type, custom_handler_name, is_active
                FROM api_endpoints
                WHERE endpoint_id = $1
            """

            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, endpoint_id)

                if not row:
                    return None

                return dict(row)

        except Exception as e:
            logger.error(f"❌ 載入 endpoint 配置失敗 [{endpoint_id}]: {e}")
            return None


# 全域實例（已棄用，建議直接創建實例並傳遞 db_pool）
_api_call_handler = None


def get_api_call_handler(db_pool: Optional[Pool] = None) -> APICallHandler:
    """
    獲取 API 調用處理器實例

    注意：為了支持動態配置的 API，建議每次都傳遞 db_pool 參數，
    而不是依賴全域單例。

    Args:
        db_pool: 數據庫連接池（可選）

    Returns:
        APICallHandler 實例
    """
    global _api_call_handler

    # 如果提供了 db_pool，創建新實例（不使用單例）
    if db_pool:
        return APICallHandler(db_pool)

    # 否則使用全域單例（向後兼容，但不支持動態 API）
    if _api_call_handler is None:
        _api_call_handler = APICallHandler()
    return _api_call_handler
