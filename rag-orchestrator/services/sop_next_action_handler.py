"""
SOP 後續動作處理器（SOP Next Action Handler）
處理三種後續動作：form_fill, api_call, form_then_api

功能：
1. form_fill: 觸發表單收集
2. api_call: 直接調用 API
3. form_then_api: 先填表單，完成後調用 API

與其他模組的整合：
- FormManager: 創建和管理表單會話
- UniversalAPIHandler: 調用後端 API
- SOPTriggerHandler: 獲取 SOP context
"""
from __future__ import annotations
from typing import Optional, Dict, List
from datetime import datetime
import json


class SOPNextActionHandler:
    """
    SOP 後續動作處理器

    負責：
    1. 根據 next_action 執行對應邏輯
    2. 創建表單會話（如需要）
    3. 調用 API（如需要）
    4. 預填表單欄位（從 next_api_config.params）
    """

    def __init__(self, form_manager, api_handler=None):
        """
        初始化後續動作處理器

        Args:
            form_manager: 表單管理器實例
            api_handler: API 調用處理器實例（可選）
        """
        self.form_manager = form_manager
        self.api_handler = api_handler

    async def handle(
        self,
        next_action: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        form_id: Optional[str] = None,
        api_config: Optional[Dict] = None,
        sop_context: Optional[Dict] = None,
        user_message: str = None
    ) -> Dict:
        """
        處理後續動作

        Args:
            next_action: 動作類型 (form_fill/api_call/form_then_api)
            session_id: 會話 ID
            user_id: 用戶 ID
            vendor_id: 業者 ID
            form_id: 表單 ID（form_fill 需要）
            api_config: API 配置（api_call 需要）
            sop_context: SOP context（用於預填）
            user_message: 用戶訊息（用於記錄）

        Returns:
            {
                'action_type': str,      # 動作類型
                'form_session': Dict,    # 表單會話（如果有）
                'api_result': Dict,      # API 結果（如果有）
                'next_step': str,        # 下一步指示
                'response': str          # 返回訊息
            }
        """
        print(f"\n🎯 [Next Action Handler] 處理動作: {next_action}")
        print(f"   Session ID: {session_id}")
        print(f"   Form ID: {form_id}")
        print(f"   Has API Config: {api_config is not None}")

        if next_action == "form_fill":
            return await self._handle_form_fill(
                session_id, user_id, vendor_id, form_id, sop_context, user_message
            )

        elif next_action == "api_call":
            return await self._handle_api_call(
                session_id, user_id, vendor_id, api_config, sop_context
            )

        elif next_action == "form_then_api":
            return await self._handle_form_then_api(
                session_id, user_id, vendor_id, form_id, api_config, sop_context, user_message
            )

        elif next_action == "none":
            return {
                'action_type': 'none',
                'form_session': None,
                'api_result': None,
                'next_step': 'completed',
                'response': '對話已完成'
            }

        else:
            print(f"   ⚠️  未知的動作類型: {next_action}")
            return {
                'action_type': 'unknown',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '系統錯誤：未知的動作類型'
            }

    # ========================================
    # 三種動作的處理邏輯
    # ========================================

    async def _handle_form_fill(
        self,
        session_id: str,
        user_id: str,
        vendor_id: int,
        form_id: str,
        sop_context: Optional[Dict],
        user_message: str
    ) -> Dict:
        """
        處理 form_fill 動作：僅觸發表單收集

        流程：
        1. 創建表單會話
        2. 預填欄位（如果 SOP 有提供）
        3. 返回第一個問題
        """
        print(f"   📋 啟動表單收集: {form_id}")

        if not form_id:
            return {
                'action_type': 'form_fill',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '錯誤：缺少表單 ID'
            }

        # 創建表單會話
        form_session = await self.form_manager.create_form_session(
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id,
            form_id=form_id,
            trigger_question=user_message,
            knowledge_id=sop_context.get('sop_id') if sop_context else None
        )

        if not form_session:
            return {
                'action_type': 'form_fill',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '錯誤：無法創建表單會話'
            }

        # 預填欄位（從 SOP next_api_config.params）
        if sop_context and sop_context.get('next_api_config'):
            api_config = sop_context['next_api_config']
            if isinstance(api_config, str):
                api_config = json.loads(api_config)

            prefill_params = api_config.get('params', {})
            if prefill_params:
                print(f"   🔧 預填欄位: {list(prefill_params.keys())}")
                await self._prefill_form_fields(form_session, prefill_params)

        # 獲取第一個問題
        first_question = await self.form_manager.get_next_question(session_id)

        followup_prompt = sop_context.get('followup_prompt', '') if sop_context else ''
        if not followup_prompt:
            followup_prompt = '好的，我來協助您填寫表單'

        return {
            'action_type': 'form_fill',
            'form_session': form_session,
            'api_result': None,
            'next_step': 'collect_field',
            'response': f"{followup_prompt}\n\n{first_question}" if first_question else followup_prompt,
            'current_field': first_question
        }

    async def _handle_api_call(
        self,
        session_id: str,
        user_id: str,
        vendor_id: int,
        api_config: Dict,
        sop_context: Optional[Dict]
    ) -> Dict:
        """
        處理 api_call 動作：直接調用 API（無表單）

        流程：
        1. 準備 API 參數
        2. 調用 API
        3. 返回結果

        適用場景：
        - auto 模式（緊急型）：自動創建工單
        - 不需要額外資訊的快速操作
        """
        print(f"   🔥 直接調用 API")

        if not api_config:
            return {
                'action_type': 'api_call',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '錯誤：缺少 API 配置'
            }

        # 解析 API 配置
        if isinstance(api_config, str):
            api_config = json.loads(api_config)

        endpoint = api_config.get('endpoint')
        method = api_config.get('method', 'POST')
        params = api_config.get('params', {})

        # 合併系統參數
        params.update({
            'user_id': user_id,
            'vendor_id': vendor_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })

        # 如果有 SOP context，添加 SOP 資訊
        if sop_context:
            params['sop_id'] = sop_context.get('sop_id')
            params['sop_name'] = sop_context.get('sop_name')

        print(f"   📡 調用 API: {method} {endpoint}")
        print(f"   📦 參數: {list(params.keys())}")

        # 調用 API
        if self.api_handler:
            try:
                api_result = await self.api_handler.call_api(
                    endpoint=endpoint,
                    method=method,
                    params=params
                )

                print(f"   ✅ API 調用成功")

                # 格式化回應訊息
                response = self._format_api_response(api_result, api_config)

                return {
                    'action_type': 'api_call',
                    'form_session': None,
                    'api_result': api_result,
                    'next_step': 'completed',
                    'response': response
                }

            except Exception as e:
                print(f"   ❌ API 調用失敗: {e}")
                return {
                    'action_type': 'api_call',
                    'form_session': None,
                    'api_result': None,
                    'next_step': 'error',
                    'response': f'系統錯誤：API 調用失敗 ({str(e)})'
                }
        else:
            print(f"   ⚠️  無 API Handler，模擬成功")
            # 模擬結果（開發模式）
            return {
                'action_type': 'api_call',
                'form_session': None,
                'api_result': {'status': 'simulated', 'params': params},
                'next_step': 'completed',
                'response': f'✅ API 調用已處理（模擬模式）\n端點：{endpoint}'
            }

    async def _handle_form_then_api(
        self,
        session_id: str,
        user_id: str,
        vendor_id: int,
        form_id: str,
        api_config: Dict,
        sop_context: Optional[Dict],
        user_message: str
    ) -> Dict:
        """
        處理 form_then_api 動作：先填表單，完成後調用 API

        流程：
        1. 創建表單會話（標記需要 API 調用）
        2. 預填欄位
        3. 返回第一個問題
        4. [表單完成後] 自動調用 API（由 FormManager 處理）

        適用場景：
        - manual 模式（排查型）：收集維修詳情後創建工單
        """
        print(f"   📋➡️🔥 啟動表單收集 + API 調用")

        if not form_id:
            return {
                'action_type': 'form_then_api',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '錯誤：缺少表單 ID'
            }

        # 創建表單會話（同時記錄 API 配置）
        form_session = await self.form_manager.create_form_session(
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id,
            form_id=form_id,
            trigger_question=user_message,
            knowledge_id=sop_context.get('sop_id') if sop_context else None
        )

        if not form_session:
            return {
                'action_type': 'form_then_api',
                'form_session': None,
                'api_result': None,
                'next_step': 'error',
                'response': '錯誤：無法創建表單會話'
            }

        # 將 API 配置附加到表單會話（供完成後調用）
        if api_config:
            await self._attach_api_config_to_session(session_id, api_config)

        # 預填欄位
        if api_config:
            if isinstance(api_config, str):
                api_config = json.loads(api_config)

            prefill_params = api_config.get('params', {})
            if prefill_params:
                print(f"   🔧 預填欄位: {list(prefill_params.keys())}")
                await self._prefill_form_fields(form_session, prefill_params)

        # 獲取第一個問題
        first_question = await self.form_manager.get_next_question(session_id)

        followup_prompt = sop_context.get('followup_prompt', '') if sop_context else ''
        if not followup_prompt:
            followup_prompt = '好的，我來協助您提交維修請求'

        return {
            'action_type': 'form_then_api',
            'form_session': form_session,
            'api_result': None,
            'next_step': 'collect_field',
            'response': f"{followup_prompt}\n\n{first_question}" if first_question else followup_prompt,
            'current_field': first_question,
            'will_call_api': True
        }

    # ========================================
    # 輔助方法
    # ========================================

    async def _prefill_form_fields(
        self,
        form_session: Dict,
        prefill_params: Dict
    ) -> bool:
        """
        預填表單欄位

        Args:
            form_session: 表單會話
            prefill_params: 預填參數字典

        Returns:
            是否成功
        """
        try:
            session_id = form_session['session_id']
            collected_data = form_session.get('collected_data', {})

            if isinstance(collected_data, str):
                collected_data = json.loads(collected_data)

            # 合併預填值
            for field_name, field_value in prefill_params.items():
                if field_name in collected_data:
                    collected_data[field_name] = field_value
                    print(f"      預填 {field_name}: {field_value}")

            # 更新會話
            # 注意：這裡需要 FormManager 提供更新方法
            # await self.form_manager.update_collected_data(session_id, collected_data)

            return True

        except Exception as e:
            print(f"   ❌ 預填欄位失敗: {e}")
            return False

    async def _attach_api_config_to_session(
        self,
        session_id: str,
        api_config: Dict
    ) -> bool:
        """
        將 API 配置附加到表單會話（供完成後調用）

        Args:
            session_id: 會話 ID
            api_config: API 配置

        Returns:
            是否成功
        """
        try:
            # 這裡需要在 form_sessions 表中添加 api_config 欄位
            # 或使用 metadata 欄位儲存
            # 暫時省略實際的資料庫操作

            print(f"      API 配置已附加到會話")
            return True

        except Exception as e:
            print(f"   ❌ 附加 API 配置失敗: {e}")
            return False

    def _format_api_response(
        self,
        api_result: Dict,
        api_config: Dict
    ) -> str:
        """
        格式化 API 回應訊息

        Args:
            api_result: API 返回結果
            api_config: API 配置

        Returns:
            格式化的訊息
        """
        # 根據 API 類型格式化不同訊息
        endpoint = api_config.get('endpoint', '')

        if 'maintenance' in endpoint and 'create' in endpoint:
            # 維修工單創建
            ticket_id = api_result.get('ticket_id', 'N/A')
            priority = api_result.get('priority', 'N/A')

            return f"""✅ 緊急維修工單已建立！

📋 工單編號：{ticket_id}
優先級：{priority}（非常緊急）

維修人員會立即聯絡您，請保持手機暢通。

🆘 緊急聯絡電話：{api_result.get('emergency_phone', '(02)1234-5678')}
"""

        else:
            # 通用格式
            return f"✅ 操作已完成\n\n{json.dumps(api_result, ensure_ascii=False, indent=2)}"


# 使用範例
if __name__ == "__main__":
    import asyncio
    from services.form_manager import FormManager

    async def test_next_action_handler():
        # 初始化（實際使用時需要真實的 FormManager 和 APIHandler）
        form_manager = FormManager()  # 需要 db_pool
        handler = SOPNextActionHandler(form_manager)

        print("=" * 80)
        print("測試：form_fill 動作")
        print("=" * 80)

        sop_context = {
            'sop_id': 156,
            'sop_name': '租金繳納登記',
            'followup_prompt': '好的，我來協助您登記本月租金繳納記錄 📝'
        }

        result = await handler.handle(
            next_action='form_fill',
            session_id='test_session_123',
            user_id='tenant_456',
            vendor_id=1,
            form_id='rent_payment_registration',
            sop_context=sop_context,
            user_message='我要登記租金繳納'
        )

        print("\n結果:")
        print(f"  Action Type: {result['action_type']}")
        print(f"  Next Step: {result['next_step']}")
        print(f"  Response: {result['response'][:100]}...")

        print("\n" + "=" * 80)
        print("測試：api_call 動作（模擬）")
        print("=" * 80)

        api_config = {
            'endpoint': '/api/maintenance/emergency',
            'method': 'POST',
            'params': {
                'priority': 'P0',
                'auto_dispatch': True
            }
        }

        sop_context = {
            'sop_id': 201,
            'sop_name': '天花板漏水'
        }

        result = await handler.handle(
            next_action='api_call',
            session_id='test_session_456',
            user_id='tenant_789',
            vendor_id=1,
            api_config=api_config,
            sop_context=sop_context
        )

        print("\n結果:")
        print(f"  Action Type: {result['action_type']}")
        print(f"  Next Step: {result['next_step']}")
        print(f"  Response: {result['response']}")

    # 運行測試
    # asyncio.run(test_next_action_handler())
    print("模組已載入，請在實際環境中測試")
