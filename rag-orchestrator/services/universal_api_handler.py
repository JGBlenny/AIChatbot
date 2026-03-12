"""
通用 API 調用處理器
支持動態配置的 API 調用，不需要為每個 API 寫函數

核心功能：
1. 從數據庫載入 API 配置
2. 動態替換 URL 和參數中的變量
3. 執行 HTTP 請求
4. 格式化響應
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from asyncpg.pool import Pool

logger = logging.getLogger(__name__)


class UniversalAPICallHandler:
    """通用 API 調用處理器"""

    def __init__(self, db_pool: Pool):
        """
        初始化

        Args:
            db_pool: 數據庫連接池
        """
        self.db_pool = db_pool
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def execute_api_call(
        self,
        endpoint_id: str,
        session_data: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        user_input: Optional[Dict[str, Any]] = None,
        knowledge_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 API 調用（動態）

        Args:
            endpoint_id: API endpoint ID
            session_data: 會話數據（user_id, vendor_id 等）
            form_data: 表單數據
            user_input: 用戶輸入
            knowledge_answer: 知識庫答案（用於合併）

        Returns:
            {
                'success': True/False,
                'data': 原始 API 響應,
                'formatted_response': 格式化後的回應,
                'error': 錯誤訊息（如果失敗）
            }
        """
        try:
            # 1. 從數據庫載入配置
            config = await self._load_endpoint_config(endpoint_id)

            if not config:
                return self._error_response(f'未找到 API 配置: {endpoint_id}')

            if not config.get('is_active'):
                return self._error_response(f'API 已停用: {endpoint_id}')

            # 2. 檢查實作類型
            implementation_type = config.get('implementation_type', 'dynamic')

            if implementation_type != 'dynamic':
                return self._error_response(
                    f'此 API 使用自定義處理器: {config.get("custom_handler_name")}'
                )

            # 3. 準備上下文數據
            context = {
                'session': session_data or {},
                'form': form_data or {},
                'input': user_input or {}
            }

            # 4. 執行動態 API 調用
            result = await self._execute_dynamic_api(config, context)

            # 5. 格式化響應（成功和失敗都需要格式化）
            formatted = self._format_response(
                config,
                result.get('data', {}) if result.get('success') else result,
                knowledge_answer
            )
            result['formatted_response'] = formatted

            return result

        except Exception as e:
            logger.error(f"❌ API 調用失敗 [{endpoint_id}]: {str(e)}")
            return self._error_response(f'系統錯誤: {str(e)}')

    async def _load_endpoint_config(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """從數據庫載入 API 配置"""
        query = """
            SELECT
                endpoint_id, endpoint_name, implementation_type,
                api_url, http_method, request_headers, request_body_template,
                request_timeout, param_mappings, response_format_type,
                response_template, custom_handler_name, is_active
            FROM api_endpoints
            WHERE endpoint_id = $1
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, endpoint_id)

            if not row:
                return None

            config = dict(row)

            # 解析 JSONB 欄位
            for field in ['request_headers', 'request_body_template', 'param_mappings']:
                if isinstance(config.get(field), str):
                    try:
                        config[field] = json.loads(config[field])
                    except:
                        config[field] = {} if field == 'request_headers' else []

            return config

    async def _execute_dynamic_api(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行動態 API 調用

        Args:
            config: API 配置
            context: 上下文數據 {session: {...}, form: {...}, input: {...}}

        Returns:
            {success: bool, data: dict, error: str}
        """
        try:
            # 1. 準備 URL
            url = config.get('api_url')
            if not url:
                return self._error_response('API 配置缺少 api_url')

            url = self._replace_variables(url, context)
            logger.info(f"🔌 動態 API URL: {url}")

            # 2. 準備參數
            params = self._build_params(config.get('param_mappings', []), context)
            logger.info(f"🔌 API 參數: {params}")

            # 3. 準備請求頭
            headers = config.get('request_headers', {})
            headers = {
                k: self._replace_variables(str(v), context)
                for k, v in headers.items()
            }

            # 4. 準備請求體（POST/PUT）
            body = None
            if config.get('request_body_template'):
                body = self._build_request_body(
                    config['request_body_template'],
                    context
                )

            # 5. 執行 HTTP 請求
            method = config.get('http_method', 'GET').upper()
            timeout = config.get('request_timeout', 30)

            logger.info(f"🔌 調用 API: {method} {url}")

            if method == 'GET':
                response = await self.http_client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'POST':
                response = await self.http_client.post(
                    url,
                    json=body or params,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'PUT':
                response = await self.http_client.put(
                    url,
                    json=body or params,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'DELETE':
                response = await self.http_client.delete(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
            else:
                return self._error_response(f'不支持的 HTTP 方法: {method}')

            # 6. 處理響應
            response.raise_for_status()

            # 嘗試解析 JSON
            try:
                result_data = response.json()
            except:
                result_data = {'text': response.text}

            # ⚠️ 檢查 API 響應內容中的 success 字段
            # 有些 API（如 Lookup）會在 JSON 中返回自己的 success 狀態
            if isinstance(result_data, dict) and 'success' in result_data:
                # 如果 API 本身返回失敗，直接傳遞該狀態
                if not result_data.get('success'):
                    logger.warning(f"⚠️ API 返回業務失敗: {config.get('endpoint_id')}")
                    return result_data  # 直接返回原始結果（包含 error, suggestions 等）

            logger.info(f"✅ API 調用成功: {config.get('endpoint_id')}")

            return {
                'success': True,
                'data': result_data,
                'status_code': response.status_code
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP 錯誤: {e.response.status_code} - {e.response.text}")
            return self._error_response(
                f'API 返回錯誤: HTTP {e.response.status_code}'
            )
        except httpx.TimeoutException:
            logger.error(f"❌ API 調用超時")
            return self._error_response('API 調用超時')
        except Exception as e:
            logger.error(f"❌ API 調用失敗: {str(e)}")
            return self._error_response(f'調用失敗: {str(e)}')

    def _build_params(
        self,
        param_mappings: List[Dict],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根據配置構建參數

        param_mappings 示例:
        [
            {
                "param_name": "user_id",
                "source": "session",
                "source_key": "user_id",
                "required": true
            }
        ]
        """
        params = {}

        for mapping in param_mappings:
            param_name = mapping.get('param_name')
            source = mapping.get('source')  # 'session', 'form', 'input', 'static'
            source_key = mapping.get('source_key')

            value = None

            if source == 'session':
                value = context.get('session', {}).get(source_key)
            elif source == 'form':
                value = context.get('form', {}).get(source_key)
            elif source == 'input':
                value = context.get('input', {}).get(source_key)
            elif source == 'static':
                value = mapping.get('static_value')

            # 檢查必要參數
            if value is None or value == '':
                if mapping.get('required'):
                    # 嘗試使用預設值
                    value = mapping.get('default')
                    if value is None:
                        logger.warning(f"⚠️ 缺少必要參數: {param_name}")
                        continue
                else:
                    value = mapping.get('default')

            if value is not None:
                params[param_name] = value

        return params

    def _build_request_body(
        self,
        body_template: Dict,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """構建請求體"""
        # 遞歸替換模板中的變量
        def replace_in_dict(obj):
            if isinstance(obj, dict):
                return {k: replace_in_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_in_dict(item) for item in obj]
            elif isinstance(obj, str):
                return self._replace_variables(obj, context)
            else:
                return obj

        return replace_in_dict(body_template)

    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """
        替換字符串中的變量

        支持格式:
        - {session.user_id}
        - {form.start_date}
        - {input.query}
        """
        if not isinstance(text, str):
            return text

        def replacer(match):
            var_path = match.group(1)  # 例如: session.user_id
            parts = var_path.split('.')

            if len(parts) < 2:
                return match.group(0)  # 保持原樣

            source = parts[0]  # session, form, input
            key_path = parts[1:]  # user_id 或 nested.key

            # 從上下文獲取值
            value = context.get(source, {})
            for key in key_path:
                if isinstance(value, dict):
                    value = value.get(key, '')
                else:
                    return ''

            return str(value) if value is not None else ''

        # 替換 {xxx.yyy} 格式
        pattern = r'\{([^}]+)\}'
        result = re.sub(pattern, replacer, text)

        return result

    def _format_response(
        self,
        config: Dict[str, Any],
        api_result: Dict[str, Any],
        knowledge_answer: Optional[str] = None
    ) -> str:
        """
        格式化 API 響應

        支持三種格式:
        1. template: 使用模板
        2. raw: 直接返回 JSON
        3. custom: 自定義格式化（暫不支持）
        """
        # 檢查 API 是否成功
        if not api_result.get('success', True):
            # API 失敗時的處理
            error_type = api_result.get('error', 'unknown')
            error_msg = api_result.get('message', '查詢失敗')
            suggestions = api_result.get('suggestions', [])

            # 處理模糊匹配（地址不完整）
            if error_type == 'ambiguous_match' and suggestions:
                suggestion_text = "\n\n**找到以下可能的地址，請選擇或提供完整地址：**\n"
                for i, sug in enumerate(suggestions, 1):
                    # 顯示地址和對應的寄送區間
                    value_info = f"（{sug.get('value', '未知')}）" if sug.get('value') else ""
                    suggestion_text += f"{i}. {sug['key']} {value_info}\n"
                return f"⚠️ {error_msg}{suggestion_text}\n💡 請提供完整的地址（包含樓層）以獲得準確結果。"

            # 處理一般的找不到匹配
            elif suggestions:
                suggestion_text = "\n\n**建議的地址：**\n"
                for i, sug in enumerate(suggestions[:3], 1):
                    score_info = f"(相似度: {sug['score']*100:.0f}%)" if sug.get('score') else ""
                    suggestion_text += f"{i}. {sug['key']} {score_info}\n"
                return f"❌ {error_msg}{suggestion_text}\n請重新輸入正確的地址。"
            else:
                return f"❌ {error_msg}\n\n請確認地址是否正確，或聯繫客服協助查詢。"

        format_type = config.get('response_format_type', 'template')

        if format_type == 'raw':
            formatted = json.dumps(api_result, ensure_ascii=False, indent=2)
        elif format_type == 'template':
            template = config.get('response_template', '')
            if template:
                formatted = self._apply_template(template, api_result)
            else:
                formatted = json.dumps(api_result, ensure_ascii=False, indent=2)
        else:
            formatted = str(api_result)

        # 合併知識答案（如果需要）
        if knowledge_answer:
            formatted = f"{knowledge_answer}\n\n---\n\n{formatted}"

        return formatted

    def _apply_template(self, template: str, data: Dict) -> str:
        """
        應用響應模板

        模板示例:
        "用戶名: {name}\nEmail: {email}\n地址: {address.city}"

        特殊處理:
        - {formatted_value}: 如果 value 是 dict/JSON，格式化顯示為清單
        """
        def replacer(match):
            key_path = match.group(1)  # 例如: address.city 或 formatted_value

            # 特殊處理 formatted_value
            if key_path == 'formatted_value':
                value = data.get('value')
                if isinstance(value, dict):
                    # 格式化為清單顯示
                    lines = []
                    for k, v in value.items():
                        if v and str(v).strip():  # 只顯示非空值
                            lines.append(f"- **{k}**：{v}")
                    return '\n'.join(lines) if lines else str(value)
                else:
                    return str(value) if value is not None else ''

            # 一般的 key path 處理
            keys = key_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                elif isinstance(value, list) and key.isdigit():
                    idx = int(key)
                    value = value[idx] if idx < len(value) else ''
                else:
                    return ''

            return str(value) if value is not None else ''

        pattern = r'\{([^}]+)\}'
        result = re.sub(pattern, replacer, template)

        return result

    def _error_response(self, error: str) -> Dict[str, Any]:
        """構建錯誤響應"""
        return {
            'success': False,
            'error': error,
            'data': None,
            'formatted_response': f"❌ {error}"
        }

    async def close(self):
        """關閉 HTTP 客戶端"""
        await self.http_client.aclose()
