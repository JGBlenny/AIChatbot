"""
SOP 觸發模式處理器（SOP Trigger Handler）
處理四種 SOP 觸發模式：none, manual, immediate, auto

功能：
1. 根據 trigger_mode 決定後續動作
2. 儲存/檢索 SOP context（Redis）
3. 關鍵詞匹配檢測
4. 執行對應的後續動作（form/API）

四種模式：
- none（資訊型）：僅返回 SOP，無後續動作
- manual（排查型）：返回 SOP + 等待關鍵詞觸發
- immediate（行動型）：返回 SOP + 立即詢問
- auto（緊急型）：返回 SOP + 自動執行 API
"""
from __future__ import annotations
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum
import json
import os

# Redis 導入設為可選，允許測試時使用 mock
try:
    import redis
except ImportError:
    redis = None


class TriggerMode(str, Enum):
    """SOP 觸發模式"""
    NONE = "none"          # 資訊型：純資訊，無後續動作
    MANUAL = "manual"      # 排查型：等待關鍵詞觸發
    IMMEDIATE = "immediate"  # 行動型：立即詢問
    AUTO = "auto"          # 緊急型：自動執行


class NextAction(str, Enum):
    """後續動作類型"""
    NONE = "none"                    # 無動作
    FORM_FILL = "form_fill"          # 填寫表單
    API_CALL = "api_call"            # 調用 API
    FORM_THEN_API = "form_then_api"  # 先填表單再調用 API


class SOPContextState(str, Enum):
    """SOP Context 狀態"""
    MANUAL_WAITING = "MANUAL_WAITING"          # 等待 manual 關鍵詞
    IMMEDIATE_WAITING = "IMMEDIATE_WAITING"    # 等待 immediate 確認
    TRIGGERED = "TRIGGERED"                    # 已觸發
    EXPIRED = "EXPIRED"                        # 已過期


class SOPTriggerHandler:
    """
    SOP 觸發模式處理器

    負責：
    1. 根據 trigger_mode 處理不同邏輯
    2. 管理 SOP context（Redis）
    3. 檢測關鍵詞匹配
    4. 準備後續動作參數
    """

    def __init__(self, redis_client = None):
        """
        初始化 SOP 觸發處理器

        Args:
            redis_client: Redis 客戶端（用於 context 儲存），可以是真實的 Redis 或 mock 物件
        """
        self.redis_client = redis_client or self._get_redis_client()

        # 內存存儲（當 Redis 未啟用時使用）
        self._memory_store = {}

        # 配置參數
        self.context_ttl = {
            TriggerMode.MANUAL: int(os.getenv("SOP_MANUAL_TTL", "600")),      # 10 分鐘
            TriggerMode.IMMEDIATE: int(os.getenv("SOP_IMMEDIATE_TTL", "600")),  # 10 分鐘
        }

    def _get_redis_client(self):
        """建立 Redis 連接（如果 redis 模組可用且 CACHE_ENABLED=true）"""
        # 檢查是否啟用緩存
        cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        if not cache_enabled:
            print("ℹ️  CACHE_ENABLED=false，SOP context 將使用內存存儲")
            return None

        if redis is None:
            print("⚠️  Redis 模組未安裝，使用內存存儲（僅限測試）")
            return None

        return redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True
        )

    def _get_context_key(self, session_id: str) -> str:
        """生成 Redis context key"""
        return f"sop_context:{session_id}"

    # ========================================
    # 核心處理方法
    # ========================================

    def handle(
        self,
        sop_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        處理 SOP 觸發邏輯

        Args:
            sop_item: SOP 項目（包含 trigger_mode, next_action 等）
            user_message: 用戶訊息
            session_id: 會話 ID
            user_id: 用戶 ID
            vendor_id: 業者 ID

        Returns:
            {
                'response': str,           # 返回給用戶的訊息
                'action': str,             # 動作類型
                'trigger_mode': str,       # 觸發模式
                'next_action': str,        # 後續動作
                'form_id': str,            # 表單 ID（如果有）
                'api_config': Dict,        # API 配置（如果有）
                'context_saved': bool      # 是否儲存 context
            }
        """
        trigger_mode = sop_item.get('trigger_mode', TriggerMode.NONE)
        next_action = sop_item.get('next_action', NextAction.NONE)

        print(f"\n🔄 [SOP Trigger Handler] 處理模式: {trigger_mode}")
        print(f"   SOP ID: {sop_item.get('id')}")
        print(f"   SOP 名稱: {sop_item.get('item_name')}")
        print(f"   後續動作: {next_action}")

        # 根據 trigger_mode 分發處理
        if trigger_mode == TriggerMode.NONE:
            return self._handle_none_mode(sop_item)

        elif trigger_mode == TriggerMode.MANUAL:
            return self._handle_manual_mode(
                sop_item, user_message, session_id, user_id, vendor_id
            )

        elif trigger_mode == TriggerMode.IMMEDIATE:
            return self._handle_immediate_mode(
                sop_item, user_message, session_id, user_id, vendor_id
            )

        elif trigger_mode == TriggerMode.AUTO:
            return self._handle_auto_mode(
                sop_item, user_message, session_id, user_id, vendor_id
            )

        else:
            # 未知模式，當作 none 處理
            print(f"   ⚠️  未知的觸發模式: {trigger_mode}，當作 none 處理")
            return self._handle_none_mode(sop_item)

    # ========================================
    # 四種模式的處理邏輯
    # ========================================

    def _handle_none_mode(self, sop_item: Dict) -> Dict:
        """
        處理 none 模式（資訊型）

        特點：
        - 僅返回 SOP 內容
        - 不儲存 context
        - 不觸發任何後續動作
        - 對話立即結束
        """
        print(f"   ✅ none 模式：僅返回資訊，無後續動作")

        return {
            'response': sop_item.get('content', ''),
            'action': 'completed',
            'trigger_mode': TriggerMode.NONE,
            'next_action': NextAction.NONE,
            'form_id': None,
            'api_config': None,
            'context_saved': False
        }

    def _handle_manual_mode(
        self,
        sop_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        處理 manual 模式（排查型）

        特點：
        - 返回 SOP 排查步驟
        - 儲存 context（等待關鍵詞）
        - 不主動詢問
        - 租戶說關鍵詞後才觸發
        - 預設觸發詞：['是', '要', '好', '可以', '需要']（可自訂覆蓋）
        """
        print(f"   ✅ manual 模式：返回排查步驟 + 等待關鍵詞")

        # 使用自訂觸發詞（如果有），否則使用預設詞
        trigger_keywords = sop_item.get('trigger_keywords') or ['是', '要']
        print(f"   🔑 觸發關鍵詞: {trigger_keywords}")

        # 儲存 context
        self._save_context(
            session_id=session_id,
            sop_item=sop_item,
            state=SOPContextState.MANUAL_WAITING,
            user_id=user_id,
            vendor_id=vendor_id,
            ttl=self.context_ttl[TriggerMode.MANUAL],
            original_question=user_message  # ← 保存原始問題
        )

        # 🔧 動態組合回應：SOP 內容 + 觸發關鍵詞提示
        response = sop_item.get('content', '')

        # 如果有觸發關鍵詞，自動添加提示
        if trigger_keywords and len(trigger_keywords) > 0:
            keywords_hint = '\n\n💡 **如需進一步協助，請告訴我：**\n'
            for keyword in trigger_keywords:
                keywords_hint += f'• 「{keyword}」\n'
            response += keywords_hint

        return {
            'response': response,
            'action': 'wait_for_keywords',
            'trigger_mode': TriggerMode.MANUAL,
            'next_action': sop_item.get('next_action'),
            'form_id': sop_item.get('next_form_id'),
            'api_config': sop_item.get('next_api_config'),
            'context_saved': True,
            'trigger_keywords': trigger_keywords
        }

    def _handle_immediate_mode(
        self,
        sop_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        處理 immediate 模式（行動型）

        特點：
        - 返回 SOP + 立即詢問
        - 儲存 context（等待確認）
        - 使用通用肯定詞：['是', '要', '好', '可以', '需要']
        - 租戶回覆肯定後觸發
        """
        print(f"   ✅ immediate 模式：返回 SOP + 立即詢問")

        trigger_keywords = sop_item.get('trigger_keywords', ['是', '要'])

        # 使用自訂提示詞（如果有），否則使用系統預設
        immediate_prompt = sop_item.get('immediate_prompt') or '''💡 **需要安排處理嗎？**

• 回覆「要」或「需要」→ 立即填寫表單
• 回覆「不用」→ 繼續為您解答其他問題'''

        print(f"   💬 立即詢問: {immediate_prompt}")
        print(f"   🔑 觸發關鍵詞: {trigger_keywords}")

        # 儲存 context
        self._save_context(
            session_id=session_id,
            sop_item=sop_item,
            state=SOPContextState.IMMEDIATE_WAITING,
            user_id=user_id,
            vendor_id=vendor_id,
            ttl=self.context_ttl[TriggerMode.IMMEDIATE],
            original_question=user_message  # ← 保存原始問題
        )

        # 組合回應：SOP 內容 + 立即詢問
        response = sop_item.get('content', '')
        if immediate_prompt:
            response += f"\n\n{immediate_prompt}"

        return {
            'response': response,
            'action': 'wait_for_confirmation',
            'trigger_mode': TriggerMode.IMMEDIATE,
            'next_action': sop_item.get('next_action'),
            'form_id': sop_item.get('next_form_id'),
            'api_config': sop_item.get('next_api_config'),
            'context_saved': True,
            'trigger_keywords': trigger_keywords,
            'immediate_prompt': immediate_prompt
        }

    def _handle_auto_mode(
        self,
        sop_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        處理 auto 模式（自動執行型）

        特點：
        - 返回 SOP 指引
        - 自動執行後續動作（form_fill / api_call / form_then_api）
        - 不需要用戶確認
        """
        next_action = sop_item.get('next_action', 'none')
        print(f"   ✅ auto 模式：返回 SOP + 自動執行 {next_action}")

        api_config = sop_item.get('next_api_config')
        form_id = sop_item.get('next_form_id')

        if api_config:
            print(f"   🔥 將觸發 API: {api_config.get('endpoint') if api_config else 'None'}")
        if form_id:
            print(f"   📋 將觸發表單: {form_id}")

        # auto 模式不需要儲存 context（立即執行）
        # 但可以短暫儲存用於追蹤
        self._save_context(
            session_id=session_id,
            sop_item=sop_item,
            state=SOPContextState.TRIGGERED,
            user_id=user_id,
            vendor_id=vendor_id,
            ttl=300,  # 5 分鐘（僅用於追蹤）
            original_question=user_message  # ← 保存原始問題
        )

        # 轉換 next_action 字符串為 NextAction enum
        next_action_enum = None
        if next_action == 'form_fill':
            next_action_enum = NextAction.FORM_FILL
        elif next_action == 'api_call':
            next_action_enum = NextAction.API_CALL
        elif next_action == 'form_then_api':
            next_action_enum = NextAction.FORM_THEN_API
        elif next_action == 'none':
            next_action_enum = NextAction.NONE
        else:
            next_action_enum = NextAction.NONE

        return {
            'response': sop_item.get('content', ''),
            'action': 'execute_immediately',
            'trigger_mode': TriggerMode.AUTO,
            'next_action': next_action_enum,
            'form_id': form_id,
            'api_config': api_config,
            'context_saved': True
        }

    # ========================================
    # Context 管理方法
    # ========================================

    def _save_context(
        self,
        session_id: str,
        sop_item: Dict,
        state: SOPContextState,
        user_id: str,
        vendor_id: int,
        ttl: int,
        original_question: str = ''
    ) -> bool:
        """
        儲存 SOP context 到 Redis

        Args:
            session_id: 會話 ID
            sop_item: SOP 項目
            state: Context 狀態
            user_id: 用戶 ID
            vendor_id: 業者 ID
            ttl: 過期時間（秒）
            original_question: 用戶原始問題（用於檢測重複提問）

        Returns:
            是否成功
        """
        try:
            context_key = self._get_context_key(session_id)

            context_data = {
                'sop_id': sop_item.get('id'),
                'sop_name': sop_item.get('item_name'),
                'trigger_mode': sop_item.get('trigger_mode'),
                'next_action': sop_item.get('next_action'),
                'next_form_id': sop_item.get('next_form_id'),
                'next_api_config': sop_item.get('next_api_config'),
                'trigger_keywords': sop_item.get('trigger_keywords', []),
                'immediate_prompt': sop_item.get('immediate_prompt'),
                'followup_prompt': sop_item.get('followup_prompt'),
                'state': state,
                'user_id': user_id,
                'vendor_id': vendor_id,
                'original_question': original_question,  # ← 新增：保存原始問題
                'created_at': datetime.now().isoformat(),
                'ttl': ttl
            }

            # 如果 Redis 被禁用，使用內存存儲
            if self.redis_client is None:
                self._memory_store[context_key] = {
                    'data': context_data,
                    'expires_at': datetime.now().timestamp() + ttl
                }
                print(f"   💾 SOP Context 已儲存到內存: {context_key} (TTL: {ttl}s)")
                return True

            # 儲存到 Redis
            self.redis_client.setex(
                context_key,
                ttl,
                json.dumps(context_data, ensure_ascii=False)
            )

            print(f"   💾 SOP Context 已儲存到 Redis: {context_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            print(f"   ❌ 儲存 SOP Context 失敗: {e}")
            return False

    def get_context(self, session_id: str) -> Optional[Dict]:
        """
        獲取 SOP context

        Args:
            session_id: 會話 ID

        Returns:
            Context 資料或 None
        """
        try:
            context_key = self._get_context_key(session_id)

            # 如果 Redis 被禁用，使用內存存儲
            if self.redis_client is None:
                stored = self._memory_store.get(context_key)
                if stored:
                    # 檢查是否過期
                    if datetime.now().timestamp() > stored['expires_at']:
                        # 已過期，刪除
                        del self._memory_store[context_key]
                        print(f"   ⚠️  SOP Context 已過期: {context_key}")
                        return None

                    context = stored['data']
                    print(f"   📖 讀取內存 SOP Context: {context_key}")
                    print(f"      狀態: {context.get('state')}")
                    return context
                else:
                    print(f"   ⚠️  無內存 SOP Context: {context_key}")
                    return None

            # 從 Redis 讀取
            context_json = self.redis_client.get(context_key)

            if context_json:
                context = json.loads(context_json)
                print(f"   📖 讀取 Redis SOP Context: {context_key}")
                print(f"      狀態: {context.get('state')}")
                return context
            else:
                print(f"   ⚠️  無 Redis SOP Context: {context_key}")
                return None

        except Exception as e:
            print(f"   ❌ 讀取 SOP Context 失敗: {e}")
            return None

    def delete_context(self, session_id: str) -> bool:
        """
        刪除 SOP context

        Args:
            session_id: 會話 ID

        Returns:
            是否成功
        """
        try:
            context_key = self._get_context_key(session_id)

            # 如果 Redis 被禁用，從內存刪除
            if self.redis_client is None:
                if context_key in self._memory_store:
                    del self._memory_store[context_key]
                    print(f"   🗑️  內存 SOP Context 已刪除: {context_key}")
                return True

            # 從 Redis 刪除
            self.redis_client.delete(context_key)
            print(f"   🗑️  Redis SOP Context 已刪除: {context_key}")
            return True
        except Exception as e:
            print(f"   ❌ 刪除 SOP Context 失敗: {e}")
            return False

    def update_context_state(
        self,
        session_id: str,
        new_state: SOPContextState
    ) -> bool:
        """
        更新 Context 狀態

        Args:
            session_id: 會話 ID
            new_state: 新狀態

        Returns:
            是否成功
        """
        try:
            # 如果 Redis 被禁用，跳過更新
            if self.redis_client is None:
                return True

            context = self.get_context(session_id)
            if not context:
                return False

            context['state'] = new_state
            context['updated_at'] = datetime.now().isoformat()

            context_key = self._get_context_key(session_id)
            ttl = context.get('ttl', 600)

            self.redis_client.setex(
                context_key,
                ttl,
                json.dumps(context, ensure_ascii=False)
            )

            print(f"   🔄 SOP Context 狀態已更新: {new_state}")
            return True

        except Exception as e:
            print(f"   ❌ 更新 SOP Context 狀態失敗: {e}")
            return False


# 使用範例
if __name__ == "__main__":
    # 初始化處理器
    handler = SOPTriggerHandler()

    # 測試 SOP 項目
    test_sop_manual = {
        'id': 123,
        'item_name': '冷氣無法啟動',
        'content': '【冷氣無法啟動 - 排查步驟】\n1. 檢查電源...',
        'trigger_mode': 'manual',
        'next_action': 'form_then_api',
        'next_form_id': 'maintenance_request',
        'next_api_config': {'endpoint': '/api/maintenance/create'},
        'trigger_keywords': ['還是不行', '試過了', '需要維修'],
        'followup_prompt': '好的，我來協助您提交維修請求...'
    }

    print("=" * 80)
    print("測試：manual 模式（排查型）")
    print("=" * 80)

    result = handler.handle(
        sop_item=test_sop_manual,
        user_message="冷氣無法啟動",
        session_id="test_session_123",
        user_id="tenant_456",
        vendor_id=1
    )

    print("\n回應結果:")
    print(f"  Response: {result['response'][:100]}...")
    print(f"  Action: {result['action']}")
    print(f"  Context Saved: {result['context_saved']}")
    print(f"  Trigger Keywords: {result.get('trigger_keywords')}")

    # 測試 immediate 模式
    test_sop_immediate = {
        'id': 156,
        'item_name': '租金繳納登記',
        'content': '【租金繳納登記說明】\n繳納期限：每月 5 日前...',
        'trigger_mode': 'immediate',
        'next_action': 'form_fill',
        'next_form_id': 'rent_payment_registration',
        'trigger_keywords': ['是', '要', '好', '可以', '需要'],
        'immediate_prompt': '📋 是否要登記本月租金繳納記錄？'
    }

    print("\n" + "=" * 80)
    print("測試：immediate 模式（行動型）")
    print("=" * 80)

    result = handler.handle(
        sop_item=test_sop_immediate,
        user_message="我要登記租金繳納",
        session_id="test_session_456",
        user_id="tenant_789",
        vendor_id=1
    )

    print("\n回應結果:")
    print(f"  Response: {result['response'][:100]}...")
    print(f"  Action: {result['action']}")
    print(f"  Immediate Prompt: {result.get('immediate_prompt')}")
