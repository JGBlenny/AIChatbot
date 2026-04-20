"""
SOP 編排器（SOP Orchestrator）
整合所有 SOP 相關模組，提供統一的處理入口

模組整合：
1. VendorSOPRetriever: SOP 檢索
2. SOPTriggerHandler: 觸發模式處理
3. KeywordMatcher: 關鍵詞匹配
4. SOPNextActionHandler: 後續動作處理
5. FormManager: 表單管理

主要流程：
1. 檢索 SOP → 判斷 trigger_mode → 執行後續動作
2. 檢查 SOP context → 匹配關鍵詞 → 觸發動作
"""
from __future__ import annotations
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import json
import os

from services.vendor_sop_retriever_v2 import VendorSOPRetrieverV2
from services.sop_trigger_handler import SOPTriggerHandler, TriggerMode
from services.keyword_matcher import KeywordMatcher
from services.sop_next_action_handler import SOPNextActionHandler


class SOPOrchestrator:
    """
    SOP 編排器

    負責協調所有 SOP 相關的處理流程：
    1. 第一次用戶提問：檢索 SOP → 處理 trigger_mode
    2. 後續用戶回覆：檢查 context → 匹配關鍵詞 → 觸發動作
    """

    def __init__(
        self,
        form_manager,
        api_handler=None,
        redis_client=None
    ):
        """
        初始化 SOP 編排器

        Args:
            form_manager: 表單管理器
            api_handler: API 處理器
            redis_client: Redis 客戶端
        """
        self.sop_retriever = VendorSOPRetrieverV2()
        self.trigger_handler = SOPTriggerHandler(redis_client)
        self.keyword_matcher = KeywordMatcher()
        self.next_action_handler = SOPNextActionHandler(form_manager, api_handler)

        print("✅ SOP Orchestrator 初始化完成")

    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        intent_id: Optional[int] = None,
        intent_ids: Optional[List[int]] = None,
        precomputed_embedding=None,
        precomputed_rewrites=None
    ) -> Dict:
        """
        處理用戶訊息（主入口）

        流程：
        1. 檢查是否有待處理的 SOP context
        2. 如果有 context：檢查關鍵詞匹配 → 觸發動作
        3. 如果無 context：檢索新 SOP → 處理 trigger_mode

        Args:
            user_message: 用戶訊息
            session_id: 會話 ID
            user_id: 用戶 ID
            vendor_id: 業者 ID
            intent_id: 主要意圖 ID
            intent_ids: 所有相關意圖 IDs

        Returns:
            {
                'has_sop': bool,           # 是否匹配到 SOP
                'sop_item': Dict,          # SOP 項目
                'trigger_result': Dict,    # 觸發處理結果
                'action_result': Dict,     # 動作執行結果
                'response': str,           # 返回訊息
                'next_step': str          # 下一步指示
            }
        """
        print(f"\n{'='*80}")
        print(f"🎯 [SOP Orchestrator] 處理訊息")
        print(f"{'='*80}")
        print(f"用戶訊息: {user_message}")
        print(f"Session ID: {session_id}")
        print(f"Vendor ID: {vendor_id}")
        print(f"Intent ID: {intent_id}")

        # ========================================
        # 步驟 1：檢查是否有待處理的 SOP context
        # ========================================
        sop_context = self.trigger_handler.get_context(session_id)

        if sop_context:
            print(f"\n📖 發現待處理的 SOP Context")
            print(f"   SOP: {sop_context.get('sop_name')}")
            print(f"   狀態: {sop_context.get('state')}")

            # ⚠️ 檢查用戶是否重複問了相同的問題
            # 如果用戶輸入與原始問題高度相似，認為是重新提問，清除舊 context
            original_question = sop_context.get('original_question', '')

            # 情況 1：舊 context 沒有 original_question（升級前的數據）
            if not original_question:
                print(f"   ⚠️  舊 context 無 original_question，清除並重新檢索")
                self.trigger_handler.delete_context(session_id)
                # 繼續到步驟 2，重新檢索 SOP
            # 情況 2：檢測到相似問題
            elif self._is_similar_question(user_message, original_question):
                print(f"   🔄 檢測到相似問題，清除舊 context 並重新檢索")
                print(f"      原始: {original_question}")
                print(f"      當前: {user_message}")
                self.trigger_handler.delete_context(session_id)
                # 繼續到步驟 2，重新檢索 SOP
            # 情況 3：不同問題，檢查關鍵詞匹配
            else:
                # 檢查關鍵詞匹配
                return await self._handle_existing_context(
                    user_message, session_id, user_id, vendor_id, sop_context
                )

        # ========================================
        # 步驟 2：沒有 context，檢索新 SOP
        # ========================================
        print(f"\n🔍 無待處理 Context，檢索新 SOP")

        # ✅ 使用向量相似度檢索 SOP（Intent 作為輔助排序）
        # 修改：提高 top_k 以便 Reranker 有足夠的候選結果進行重排序
        sop_similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.55"))  # 降低閾值，讓更多候選進入 Reranker
        sop_items = await self.sop_retriever.retrieve_sop_by_query(
            vendor_id=vendor_id,
            query=user_message,
            intent_id=intent_id,  # 可選，用於加成排序
            top_k=5,  # 取前 5 個候選，讓 Reranker 進行語義重排序
            similarity_threshold=sop_similarity_threshold,
            precomputed_embedding=precomputed_embedding,
            precomputed_rewrites=precomputed_rewrites
        )

        if not sop_items:
            print(f"   ❌ 無匹配的 SOP（達標）")
            # Debug：撈未達標候選（僅重用已有的預計算資源，不再重跑完整 retrieve）
            debug_candidates = await self.sop_retriever.retrieve_sop_by_query(
                vendor_id=vendor_id,
                query=user_message,
                intent_id=intent_id,
                top_k=5,
                similarity_threshold=0.0,  # 不過濾，全部撈回來看分數
                precomputed_embedding=precomputed_embedding,
                precomputed_rewrites=precomputed_rewrites
            )
            print(f"   📊 Debug: 取得 {len(debug_candidates)} 個未達標候選供 chat-test 顯示")
            return {
                'has_sop': False,
                'sop_item': None,
                'all_sop_candidates': debug_candidates,  # 含未達標分數
                'trigger_result': None,
                'action_result': None,
                'response': None,
                'next_step': 'no_sop_found'
            }

        sop_item = sop_items[0]
        print(f"   ✅ 找到 SOP: {sop_item.get('item_name')}")
        print(f"   📋 共 {len(sop_items)} 個候選結果")

        # 處理新 SOP，並傳遞所有候選結果
        return await self._handle_new_sop(
            sop_item, user_message, session_id, user_id, vendor_id, all_candidates=sop_items
        )

    async def _handle_existing_context(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        sop_context: Dict
    ) -> Dict:
        """
        處理已存在的 SOP context（關鍵詞匹配）

        流程：
        1. 檢查關鍵詞是否匹配
        2. 如果匹配：執行後續動作
        3. 如果不匹配：提示用戶或繼續等待
        """
        state = sop_context.get('state')
        trigger_mode = sop_context.get('trigger_mode')
        trigger_keywords = sop_context.get('trigger_keywords') or []

        # 模式兜底：若 context 中沒有觸發關鍵詞，使用預設值
        if not trigger_keywords:
            if trigger_mode == 'immediate':
                # immediate 模式的確認詞列表
                trigger_keywords = ['確認', '好', '是的', '可以', 'ok', 'yes', '要', '需要', '開始']
            elif trigger_mode == 'manual':
                # manual 模式的預設觸發詞（與 _handle_manual_mode 一致）
                trigger_keywords = ['確認', '需要']

        print(f"\n🔑 檢查關鍵詞匹配")
        print(f"   觸發關鍵詞: {trigger_keywords}")
        print(f"   用戶訊息: {user_message}")

        # 🔧 檢查是否為純粹的否定詞（適用於 immediate 模式）
        negative_keywords = ['不用', '不要', '不需要', '算了', '不必', '免了', '不了', '不']
        user_message_clean = user_message.strip().replace('\n', '').replace(' ', '')

        # 完全匹配或只包含否定詞+標點
        is_pure_negative = user_message_clean in negative_keywords or \
                          any(user_message_clean == kw + punct for kw in negative_keywords for punct in ['', '。', '！', '!', ',', '，'])

        if is_pure_negative and trigger_mode == 'immediate':
            print(f"   ℹ️  檢測到否定詞，取消動作")
            # 刪除 context
            self.trigger_handler.delete_context(session_id)

            # 使用 followup_prompt 或預設禮貌回覆
            followup_prompt = sop_context.get('followup_prompt')
            polite_response = followup_prompt or '好的，如有需要隨時告訴我！'

            return {
                'has_sop': True,
                'sop_item': sop_context,
                'all_sop_candidates': [sop_context],
                'trigger_result': {
                    'matched': False,
                    'cancelled': True,
                    'reason': '用戶拒絕執行'
                },
                'action_result': None,
                'response': polite_response,
                'next_step': 'cancelled'
            }

        # 🔧 immediate 模式：檢查是否為問句（問句不視為確認）
        is_question = False
        if trigger_mode == 'immediate':
            question_indicators = ['？', '?', '嗎', '呢', '什麼', '如何', '怎麼', '怎樣', '為何', '為什麼', '哪裡', '哪里', '誰', '何時']
            is_question = any(indicator in user_message for indicator in question_indicators)
            is_long_message = len(user_message) > 10  # 超過10個字符視為完整問題

            if is_question or is_long_message:
                print(f"   ⚠️  檢測到問句或長訊息，不視為確認")
                print(f"      is_question: {is_question}, is_long_message: {is_long_message}")
                is_match = False
                matched_keyword = None
                match_type = None
            else:
                # 檢查關鍵詞匹配
                is_match, matched_keyword, match_type = self.keyword_matcher.match_any(
                    user_message,
                    trigger_keywords,
                    match_types=["contains", "synonyms"]
                )
        else:
            # manual 模式：正常檢查關鍵詞
            is_match, matched_keyword, match_type = self.keyword_matcher.match_any(
                user_message,
                trigger_keywords,
                match_types=["contains", "synonyms"]
            )

        if is_match:
            print(f"   ✅ 匹配成功: {matched_keyword} ({match_type})")

            # 更新 context 狀態
            self.trigger_handler.update_context_state(
                session_id,
                'TRIGGERED'
            )

            # 執行後續動作
            action_result = await self.next_action_handler.handle(
                next_action=sop_context.get('next_action'),
                session_id=session_id,
                user_id=user_id,
                vendor_id=vendor_id,
                form_id=sop_context.get('next_form_id'),
                api_config=sop_context.get('next_api_config'),
                sop_context=sop_context,
                user_message=user_message
            )

            # 刪除 context（已觸發）
            self.trigger_handler.delete_context(session_id)

            return {
                'has_sop': True,
                'sop_item': sop_context,
                'all_sop_candidates': [sop_context],  # 🆕 添加候選結果（existing context 只有一個）
                'trigger_result': {
                    'matched': True,
                    'keyword': matched_keyword,
                    'match_type': match_type
                },
                'action_result': action_result,
                'response': action_result.get('response'),
                'next_step': action_result.get('next_step')
            }

        else:
            print(f"   ❌ 無匹配關鍵詞")

            # 根據 trigger_mode 提供不同的提示
            trigger_mode = sop_context.get('trigger_mode')

            if trigger_mode == 'manual':
                # manual 模式：不主動提示，保持等待
                return {
                    'has_sop': True,
                    'sop_item': sop_context,
                    'all_sop_candidates': [sop_context],  # 🆕 添加候選結果（existing context 只有一個）
                    'trigger_result': {
                        'matched': False,
                        'reason': '未匹配觸發關鍵詞'
                    },
                    'action_result': None,
                    'response': None,  # 不回應，等待其他處理
                    'next_step': 'waiting_for_keyword'
                }

            elif trigger_mode == 'immediate':
                # immediate 模式：再次詢問
                immediate_prompt = sop_context.get('immediate_prompt')
                return {
                    'has_sop': True,
                    'sop_item': sop_context,
                    'all_sop_candidates': [sop_context],  # 🆕 添加候選結果（existing context 只有一個）
                    'trigger_result': {
                        'matched': False,
                        'reason': '未匹配確認詞'
                    },
                    'action_result': None,
                    'response': f"抱歉，我沒聽懂。{immediate_prompt}",
                    'next_step': 'waiting_for_confirmation'
                }

            else:
                # 其他情況
                return {
                    'has_sop': True,
                    'sop_item': sop_context,
                    'all_sop_candidates': [sop_context],  # 🆕 添加候選結果（existing context 只有一個）
                    'trigger_result': {
                        'matched': False
                    },
                    'action_result': None,
                    'response': None,
                    'next_step': 'waiting'
                }

    async def _handle_new_sop(
        self,
        sop_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        all_candidates: List[Dict] = None  # 🆕 添加所有候選結果參數
    ) -> Dict:
        """
        處理新檢索到的 SOP

        流程：
        1. 使用 SOPTriggerHandler 處理 trigger_mode
        2. 根據處理結果決定下一步：
           - none: 直接結束
           - manual/immediate: 等待關鍵詞
           - auto: 立即執行動作
        """
        # 從資料庫讀取完整的 SOP 資訊（包含 next action 欄位）
        # 注意：這裡需要擴展 VendorSOPRetriever 來獲取這些欄位
        sop_item_full = await self._fetch_sop_with_next_action(sop_item['id'])

        if not sop_item_full:
            # 如果無法獲取完整資訊，使用基本資訊（預設為 none 模式）
            sop_item_full = {
                **sop_item,
                'trigger_mode': 'none',
                'next_action': 'none'
            }
        else:
            # 🔧 保留原始 sop_item 的相似度資訊（從 retrieve_sop_by_query 返回）
            # _fetch_sop_with_next_action 重新查詢時不包含這些欄位，需要手動保留
            sop_item_full['similarity'] = sop_item.get('similarity')
            sop_item_full['boosted_similarity'] = sop_item.get('boosted_similarity')
            sop_item_full['original_similarity'] = sop_item.get('original_similarity')
            sop_item_full['rerank_score'] = sop_item.get('rerank_score')
            sop_item_full['group_name'] = sop_item.get('group_name')
            sop_item_full['category_name'] = sop_item.get('category_name')

        # 處理觸發模式
        trigger_result = self.trigger_handler.handle(
            sop_item=sop_item_full,
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id
        )

        action = trigger_result.get('action')

        # ========================================
        # 根據 action 決定是否立即執行後續動作
        # ========================================

        if action == 'completed':
            # none 模式：直接結束
            return {
                'has_sop': True,
                'sop_item': sop_item_full,
                'all_sop_candidates': all_candidates or [sop_item_full],  # 🆕 添加所有候選結果
                'trigger_result': trigger_result,
                'action_result': None,
                'response': trigger_result.get('response'),
                'next_step': 'completed'
            }

        elif action == 'wait_for_keywords':
            # manual 模式：等待關鍵詞
            return {
                'has_sop': True,
                'sop_item': sop_item_full,
                'all_sop_candidates': all_candidates or [sop_item_full],  # 🆕 添加所有候選結果
                'trigger_result': trigger_result,
                'action_result': None,
                'response': trigger_result.get('response'),
                'next_step': 'waiting_for_keyword'
            }

        elif action == 'wait_for_confirmation':
            # immediate 模式：等待確認
            return {
                'has_sop': True,
                'sop_item': sop_item_full,
                'all_sop_candidates': all_candidates or [sop_item_full],  # 🆕 添加所有候選結果
                'trigger_result': trigger_result,
                'action_result': None,
                'response': trigger_result.get('response'),
                'next_step': 'waiting_for_confirmation'
            }

        elif action == 'execute_immediately':
            # auto 模式：立即執行後續動作（可能是 form_fill/api_call/form_then_api）
            next_action_enum = trigger_result.get('next_action')
            # 轉換 enum 為字符串（如果是 enum 類型）
            if hasattr(next_action_enum, 'value'):
                next_action_str = next_action_enum.value
            else:
                next_action_str = str(next_action_enum) if next_action_enum else 'none'

            action_result = await self.next_action_handler.handle(
                next_action=next_action_str,
                session_id=session_id,
                user_id=user_id,
                vendor_id=vendor_id,
                form_id=trigger_result.get('form_id'),
                api_config=trigger_result.get('api_config'),
                sop_context={'sop_id': sop_item_full['id'], 'sop_name': sop_item_full['item_name']},
                user_message=user_message
            )

            # 組合回應：SOP 內容 + API 結果
            combined_response = trigger_result.get('response', '')
            if action_result.get('response'):
                combined_response += f"\n\n{action_result['response']}"

            return {
                'has_sop': True,
                'sop_item': sop_item_full,
                'all_sop_candidates': all_candidates or [sop_item_full],  # 🆕 添加所有候選結果
                'trigger_result': trigger_result,
                'action_result': action_result,
                'response': combined_response,
                'next_step': 'completed'
            }

        else:
            # 未知 action
            return {
                'has_sop': True,
                'sop_item': sop_item_full,
                'all_sop_candidates': all_candidates or [sop_item_full],  # 🆕 添加所有候選結果
                'trigger_result': trigger_result,
                'action_result': None,
                'response': trigger_result.get('response'),
                'next_step': 'unknown'
            }

    def _is_similar_question(self, question1: str, question2: str, threshold: float = 0.7) -> bool:
        """
        判斷兩個問題是否相似

        使用簡單的字符串相似度算法

        Args:
            question1: 第一個問題
            question2: 第二個問題
            threshold: 相似度閾值（0-1），預設 0.7

        Returns:
            True 如果相似度 >= threshold
        """
        from difflib import SequenceMatcher

        # 移除空白並轉小寫
        q1 = question1.strip().lower()
        q2 = question2.strip().lower()

        # 完全相同
        if q1 == q2:
            return True

        # 計算相似度
        similarity = SequenceMatcher(None, q1, q2).ratio()

        print(f"   📊 問題相似度: {similarity:.2f} (閾值: {threshold})")

        return similarity >= threshold

    async def _fetch_sop_with_next_action(self, sop_id: int) -> Optional[Dict]:
        """
        從資料庫獲取包含 next_action 欄位的完整 SOP 資訊

        Args:
            sop_id: SOP ID

        Returns:
            完整的 SOP 資訊
        """
        try:
            import psycopg2.extras
            from services.db_utils import get_db_config

            conn = psycopg2.connect(**get_db_config())
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    id,
                    category_id,
                    group_id,
                    item_number,
                    item_name,
                    content,
                    priority,
                    trigger_mode,
                    next_action,
                    next_form_id,
                    next_api_config,
                    trigger_keywords,
                    immediate_prompt,
                    followup_prompt
                FROM vendor_sop_items
                WHERE id = %s AND is_active = TRUE
            """, (sop_id,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return dict(row)
            else:
                return None

        except Exception as e:
            print(f"   ❌ 獲取 SOP 完整資訊失敗: {e}")
            return None

    async def handle_knowledge_trigger(
        self,
        knowledge_item: Dict,
        user_message: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        處理知識庫項目的觸發（支援 manual 和 immediate 模式）

        Args:
            knowledge_item: 知識庫項目（已轉換為 SOP 格式）
            user_message: 用戶訊息
            session_id: 會話 ID
            user_id: 用戶 ID
            vendor_id: 業者 ID

        Returns:
            處理結果 {'action': 'triggered'/'wait_for_confirmation', 'response': str}
        """
        print(f"🎯 [Knowledge Trigger] 處理知識庫觸發 ID={knowledge_item.get('id')}, mode={knowledge_item.get('trigger_mode')}")

        # 檢查是否有待處理的 context
        existing_context = self.trigger_handler.get_context(session_id)

        if existing_context:
            # 有待處理的 context，檢查關鍵詞匹配
            print(f"   📖 檢測到待處理 context: knowledge_id={existing_context.get('sop_id')}")

            trigger_keywords = existing_context.get('trigger_keywords', [])
            matched, matched_keyword = self.keyword_matcher.match(user_message, trigger_keywords)

            if matched:
                print(f"   ✅ 關鍵詞匹配成功: {matched_keyword}")
                # 刪除 context
                self.trigger_handler.delete_context(session_id)
                return {
                    'action': 'triggered',
                    'response': '',
                    'matched_keyword': matched_keyword
                }
            else:
                print(f"   ❌ 關鍵詞未匹配，保持等待")
                return {
                    'action': 'wait_for_keywords',
                    'response': '請告訴我您是否需要協助？'
                }
        else:
            # 沒有 context，首次觸發
            result = self.trigger_handler.handle(
                sop_item=knowledge_item,
                user_message=user_message,
                session_id=session_id,
                user_id=user_id,
                vendor_id=vendor_id
            )

            if result.get('action') == 'execute_immediately':
                # auto 模式：直接觸發
                return {
                    'action': 'triggered',
                    'response': result.get('response', '')
                }
            else:
                # manual/immediate 模式：返回等待回應
                return {
                    'action': 'wait_for_confirmation',
                    'response': result.get('response', '')
                }


# 使用範例
if __name__ == "__main__":
    import asyncio
    from services.form_manager import FormManager

    async def test_orchestrator():
        # 初始化（實際使用時需要真實的依賴）
        form_manager = FormManager()  # 需要 db_pool
        orchestrator = SOPOrchestrator(form_manager)

        print("=" * 80)
        print("測試場景 1：資訊型 SOP（垃圾收取時間）")
        print("=" * 80)

        result = await orchestrator.process_message(
            user_message="垃圾什麼時候收？",
            session_id="test_001",
            user_id="tenant_123",
            vendor_id=1,
            intent_id=88  # 垃圾相關查詢
        )

        print("\n處理結果:")
        print(f"  Has SOP: {result['has_sop']}")
        print(f"  Next Step: {result['next_step']}")
        if result['response']:
            print(f"  Response: {result['response'][:100]}...")

        print("\n" + "=" * 80)
        print("測試場景 2：排查型 SOP（冷氣故障）- 第一輪")
        print("=" * 80)

        result = await orchestrator.process_message(
            user_message="冷氣無法啟動",
            session_id="test_002",
            user_id="tenant_456",
            vendor_id=1,
            intent_id=25  # 冷氣維修
        )

        print("\n處理結果:")
        print(f"  Has SOP: {result['has_sop']}")
        print(f"  Next Step: {result['next_step']}")
        if result['response']:
            print(f"  Response: {result['response'][:100]}...")

        print("\n" + "=" * 80)
        print("測試場景 2：排查型 SOP（冷氣故障）- 第二輪（觸發關鍵詞）")
        print("=" * 80)

        result = await orchestrator.process_message(
            user_message="試過了還是不行",
            session_id="test_002",  # 同一個 session
            user_id="tenant_456",
            vendor_id=1
        )

        print("\n處理結果:")
        print(f"  Has SOP: {result['has_sop']}")
        print(f"  Keyword Matched: {result.get('trigger_result', {}).get('matched')}")
        print(f"  Next Step: {result['next_step']}")

    # 運行測試
    # asyncio.run(test_orchestrator())
    print("SOP Orchestrator 模組已載入")
