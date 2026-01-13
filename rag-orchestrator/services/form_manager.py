"""
表單管理服務（Form Manager）
負責表單狀態的完整生命週期管理

功能：
1. 表單會話的創建、更新、查詢
2. 狀態轉移（NORMAL_CHAT → FORM_FILLING → COLLECTING → DIGRESSION）
3. 欄位資料收集與驗證
4. 表單完成與取消

異步包裝說明：
- 所有資料庫操作使用 psycopg2（同步）
- 透過 asyncio.to_thread() 包裝為異步，避免阻塞事件循環
- 使用 db_utils 的 context manager 自動管理連接
"""
from __future__ import annotations
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
import json
import psycopg2.extras
import asyncpg
from services.db_utils import get_db_cursor
from services.form_validator import FormValidator
from services.digression_detector import DigressionDetector
from services.digression_detector_db import DigressionDetectorDB


class FormState:
    """表單狀態枚舉"""
    COLLECTING = "COLLECTING"  # 收集中
    DIGRESSION = "DIGRESSION"  # 離題中
    REVIEWING = "REVIEWING"    # 審核中（新增）
    EDITING = "EDITING"        # 編輯中（新增）
    COMPLETED = "COMPLETED"    # 已完成
    CANCELLED = "CANCELLED"    # 已取消


class FormManager:
    """
    表單管理器

    管理表單會話的完整生命週期：
    - 創建表單會話
    - 收集欄位資料
    - 偵測並處理離題
    - 恢復表單填寫
    - 完成或取消表單
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        初始化表單管理器

        Args:
            db_pool: 資料庫連接池（可選）
                    - 如果提供，使用 DigressionDetectorDB（資料庫配置版本）
                    - 如果不提供，使用 DigressionDetector（硬編碼版本）
        """
        self.validator = FormValidator()
        self.db_pool = db_pool

        # 根據是否提供 db_pool 選擇離題偵測器
        if db_pool:
            self.digression_detector = DigressionDetectorDB(db_pool)
            print("✅ 使用資料庫配置版本的離題偵測器（DigressionDetectorDB）")
        else:
            self.digression_detector = DigressionDetector()
            print("✅ 使用硬編碼版本的離題偵測器（DigressionDetector）")

    # ========================================
    # 資料庫操作方法（同步 + 異步包裝）
    # ========================================

    def _get_form_schema_sync(self, form_id: str, vendor_id: Optional[int] = None) -> Optional[Dict]:
        """獲取表單定義（同步）"""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                if vendor_id is not None:
                    # 支援 vendor 過濾
                    cursor.execute("""
                        SELECT * FROM form_schemas
                        WHERE form_id = %s
                          AND (vendor_id = %s OR vendor_id IS NULL)
                          AND is_active = true
                        ORDER BY vendor_id DESC NULLS LAST
                        LIMIT 1
                    """, (form_id, vendor_id))
                else:
                    # 向後兼容：不過濾 vendor
                    cursor.execute("""
                        SELECT * FROM form_schemas
                        WHERE form_id = %s AND is_active = true
                    """, (form_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ 獲取表單定義失敗: {e}")
            return None

    async def get_form_schema(self, form_id: str, vendor_id: Optional[int] = None) -> Optional[Dict]:
        """獲取表單定義（異步）"""
        return await asyncio.to_thread(self._get_form_schema_sync, form_id, vendor_id)

    def _find_form_by_intent_sync(self, intent_name: str, vendor_id: int) -> Optional[Dict]:
        """根據意圖名稱查找匹配的表單（同步）"""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                # 使用 JSONB 查詢觸發意圖列表
                cursor.execute("""
                    SELECT * FROM form_schemas
                    WHERE is_active = true
                      AND (vendor_id = %s OR vendor_id IS NULL)
                      AND trigger_intents @> %s::jsonb
                    ORDER BY vendor_id DESC NULLS LAST
                    LIMIT 1
                """, (vendor_id, json.dumps([intent_name])))

                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ 查找表單失敗: {e}")
            return None

    async def find_form_by_intent(self, intent_name: str, vendor_id: int) -> Optional[Dict]:
        """根據意圖名稱查找匹配的表單（異步）"""
        return await asyncio.to_thread(self._find_form_by_intent_sync, intent_name, vendor_id)

    def _get_session_state_sync(self, session_id: str) -> Optional[Dict]:
        """獲取會話狀態（同步）"""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT * FROM form_sessions
                    WHERE session_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (session_id,))

                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ 獲取會話狀態失敗: {e}")
            return None

    async def get_session_state(self, session_id: str) -> Optional[Dict]:
        """獲取會話狀態（異步）"""
        return await asyncio.to_thread(self._get_session_state_sync, session_id)

    def _create_form_session_sync(
        self,
        session_id: str,
        user_id: str,
        vendor_id: int,
        form_id: str,
        trigger_question: str = None,
        knowledge_id: int = None
    ) -> Optional[Dict]:
        """創建新的表單會話（同步）"""
        try:
            # 先獲取表單定義
            form_schema = self._get_form_schema_sync(form_id, vendor_id)
            if not form_schema:
                print(f"❌ 表單定義不存在: {form_id}")
                return None

            # 初始化空的 collected_data
            collected_data = {field['field_name']: None for field in form_schema['fields']}

            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute("""
                    INSERT INTO form_sessions (
                        session_id, user_id, vendor_id, form_id,
                        state, current_field_index, collected_data, trigger_question, knowledge_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    session_id, user_id, vendor_id, form_id,
                    FormState.COLLECTING, 0,
                    json.dumps(collected_data),
                    trigger_question,
                    knowledge_id
                ))

                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ 創建表單會話失敗: {e}")
            return None

    async def create_form_session(
        self,
        session_id: str,
        user_id: str,
        vendor_id: int,
        form_id: str,
        trigger_question: str = None,
        knowledge_id: int = None
    ) -> Optional[Dict]:
        """創建新的表單會話（異步）"""
        return await asyncio.to_thread(
            self._create_form_session_sync,
            session_id, user_id, vendor_id, form_id, trigger_question, knowledge_id
        )

    def _update_session_state_sync(
        self,
        session_id: str,
        state: Optional[str] = None,
        current_field_index: Optional[int] = None,
        collected_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """更新會話狀態（同步）"""
        try:
            # 構建動態更新語句
            update_fields = ["last_activity_at = NOW()"]
            params = []

            if state is not None:
                update_fields.append("state = %s")
                params.append(state)
            if current_field_index is not None:
                update_fields.append("current_field_index = %s")
                params.append(current_field_index)
            if collected_data is not None:
                update_fields.append("collected_data = %s")
                params.append(json.dumps(collected_data))

            # 根據狀態設置完成/取消時間
            if state == FormState.COMPLETED:
                update_fields.append("completed_at = NOW()")
            elif state == FormState.CANCELLED:
                update_fields.append("cancelled_at = NOW()")

            params.append(session_id)

            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute(f"""
                    UPDATE form_sessions
                    SET {', '.join(update_fields)}
                    WHERE session_id = %s
                    RETURNING *
                """, tuple(params))

                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ 更新會話狀態失敗: {e}")
            return None

    async def update_session_state(
        self,
        session_id: str,
        state: Optional[str] = None,
        current_field_index: Optional[int] = None,
        collected_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """更新會話狀態（異步）"""
        return await asyncio.to_thread(
            self._update_session_state_sync,
            session_id, state, current_field_index, collected_data
        )

    def _save_form_submission_sync(
        self,
        session_id: int,
        form_id: str,
        user_id: str,
        vendor_id: int,
        submitted_data: Dict
    ) -> Optional[int]:
        """保存表單提交記錄（同步）"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO form_submissions (
                        form_session_id, form_id, user_id, vendor_id, submitted_data
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, form_id, user_id, vendor_id, json.dumps(submitted_data)))

                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"❌ 保存表單提交失敗: {e}")
            return None

    async def save_form_submission(
        self,
        session_id: int,
        form_id: str,
        user_id: str,
        vendor_id: int,
        submitted_data: Dict
    ) -> Optional[int]:
        """保存表單提交記錄（異步）"""
        return await asyncio.to_thread(
            self._save_form_submission_sync,
            session_id, form_id, user_id, vendor_id, submitted_data
        )

    def _save_pending_question_sync(self, session_id: str, question: str) -> bool:
        """保存待處理的問題到資料庫（同步）"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE form_sessions
                    SET pending_question = %s
                    WHERE session_id = %s
                """, (question, session_id))
                return True
        except Exception as e:
            print(f"❌ 保存待處理問題失敗: {e}")
            return False

    def _get_pending_question_sync(self, session_id: str) -> Optional[str]:
        """從資料庫取得待處理的問題（同步）"""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT pending_question
                    FROM form_sessions
                    WHERE session_id = %s
                """, (session_id,))
                result = cursor.fetchone()
                return result['pending_question'] if result else None
        except Exception as e:
            print(f"❌ 取得待處理問題失敗: {e}")
            return None

    def _get_knowledge_answer_sync(self, knowledge_id: int) -> Optional[str]:
        """從資料庫取得知識答案（同步）"""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT answer
                    FROM knowledge_base
                    WHERE id = %s
                """, (knowledge_id,))
                result = cursor.fetchone()
                return result['answer'] if result else None
        except Exception as e:
            print(f"❌ 取得知識答案失敗: {e}")
            return None

    # ========================================
    # 業務邏輯方法
    # ========================================

    async def trigger_form_filling(
        self,
        intent_name: str,
        session_id: str,
        user_id: str,
        vendor_id: int
    ) -> Dict:
        """
        觸發表單填寫流程

        Args:
            intent_name: 觸發的意圖名稱
            session_id: 會話 ID
            user_id: 用戶 ID
            vendor_id: 業者 ID

        Returns:
            回應字典
        """
        # 1. 查找匹配的表單
        form_schema = await self.find_form_by_intent(intent_name, vendor_id)

        if not form_schema:
            return {
                "answer": "抱歉，目前沒有適合的表單可以協助您。",
                "form_triggered": False
            }

        # 2. 創建表單會話
        session_state = await self.create_form_session(
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id,
            form_id=form_schema['form_id']
        )

        if not session_state:
            return {
                "answer": "抱歉，創建表單會話失敗，請稍後再試。",
                "form_triggered": False
            }

        # 3. 返回第一個欄位的提示
        first_field = form_schema['fields'][0]
        total_fields = len(form_schema['fields'])

        return {
            "answer": f"好的，我來協助您填寫**{form_schema['form_name']}**。\n\n{first_field['prompt']}",
            "form_triggered": True,
            "form_id": form_schema['form_id'],
            "current_field": first_field['field_name'],
            "progress": f"1/{total_fields}"
        }

    async def trigger_form_by_knowledge(
        self,
        knowledge_id: int,
        form_id: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        trigger_question: str = None
    ) -> Dict:
        """
        通過知識觸發表單（新架構）

        Args:
            knowledge_id: 知識ID（用於記錄觸發來源）
            form_id: 表單ID
            session_id: 會話ID
            user_id: 用戶ID
            vendor_id: 業者ID
            trigger_question: 觸發表單的用戶問題

        Returns:
            表單回應字典
        """
        # 1. 取得表單定義
        form_schema = await asyncio.to_thread(self._get_form_schema_sync, form_id, vendor_id)

        if not form_schema:
            return {
                "answer": f"抱歉，找不到表單 {form_id}，請聯繫管理員。",
                "form_triggered": False
            }

        # 2. 檢查是否已存在會話，避免重複創建
        existing_session = await self.get_session_state(session_id)
        if existing_session and existing_session['state'] in ['COLLECTING', 'DIGRESSION']:
            # 已有進行中的表單會話，不重複創建
            print(f"⚠️ 會話 {session_id} 已存在進行中的表單，跳過創建")
            session_state = existing_session
        else:
            # 創建新的表單會話
            session_state = await self.create_form_session(
                session_id=session_id,
                user_id=user_id,
                vendor_id=vendor_id,
                form_id=form_id,
                trigger_question=trigger_question,
                knowledge_id=knowledge_id
            )

        if not session_state:
            return {
                "answer": "抱歉，創建表單會話失敗，請稍後再試。",
                "form_triggered": False
            }

        # 3. 組合回應（表單引導語 + 表單提示）
        first_field = form_schema['fields'][0]
        total_fields = len(form_schema['fields'])

        # 使用表單的 default_intro 作為引導語
        intro_message = form_schema.get('default_intro', '')

        # 組裝訊息
        response = intro_message.strip()
        response += f"\n\n📝 **{form_schema['form_name']}**"
        response += f"\n\n{first_field['prompt']}"
        response += "\n\n（或輸入「**取消**」結束填寫）"

        return {
            "answer": response,
            "form_triggered": True,
            "form_id": form_id,
            "current_field": first_field['field_name'],
            "progress": f"1/{total_fields}",
            "triggered_by_knowledge": knowledge_id
        }

    async def collect_field_data(
        self,
        user_message: str,
        session_id: str,
        intent_result: Optional[Dict] = None,
        vendor_id: int = 1,
        language: str = 'zh-TW'
    ) -> Dict:
        """
        收集欄位資料（核心流程）

        Args:
            user_message: 用戶輸入
            session_id: 會話 ID
            intent_result: 意圖分類結果（用於離題偵測）
            vendor_id: 業者 ID（用於載入專屬配置）
            language: 語言代碼（用於載入對應語言的關鍵字）

        Returns:
            回應字典
        """
        # 1. 獲取當前會話狀態
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return {
                "answer": "找不到表單會話，請重新開始。"
            }

        # 1.5. 檢查是否為恢復表單（用戶說"繼續"）
        if session_state['state'] == FormState.DIGRESSION:
            if user_message.strip() in ["繼續", "继续", "continue"]:
                return await self.resume_form_filling(session_id)
            elif user_message.strip() in ["回答", "回答問題", "answer"]:
                # 處理離題後回答問題（取消表單）
                pending_question = await asyncio.to_thread(self._get_pending_question_sync, session_id)

                # 取消表單會話
                await self.update_session_state(
                    session_id=session_id,
                    state=FormState.CANCELLED
                )

                if pending_question:
                    return {
                        "answer": "",  # 空答案，讓主流程來回答
                        "answer_pending_question": True,  # 標記需要回答待處理的問題
                        "pending_question": pending_question,  # 返回待處理的問題
                        "form_cancelled": True  # 表單已取消
                    }
                else:
                    return {
                        "answer": "找不到您的問題記錄。"
                    }
            elif user_message.strip() in ["取消", "算了", "cancel"]:
                # 處理離題後取消，取得待處理的問題
                pending_question = await asyncio.to_thread(self._get_pending_question_sync, session_id)

                await self.update_session_state(
                    session_id=session_id,
                    state=FormState.CANCELLED
                )
                return {
                    "answer": "已取消表單填寫。",
                    "form_cancelled": True,
                    "pending_question": pending_question  # 返回待處理的問題
                }

        # 2. 獲取表單定義
        form_schema = await self.get_form_schema(session_state['form_id'])
        if not form_schema:
            return {
                "answer": "找不到表單定義，請重新開始。"
            }

        current_field_index = session_state['current_field_index']
        current_field = form_schema['fields'][current_field_index]

        # 3. 偵測離題
        # 如果使用資料庫版本，傳入 vendor_id 和 language
        if isinstance(self.digression_detector, DigressionDetectorDB):
            is_digression, digression_type, confidence = await self.digression_detector.detect(
                user_message=user_message,
                current_field=current_field,
                form_schema=form_schema,
                intent_result=intent_result,
                vendor_id=vendor_id,
                language=language
            )
        else:
            # 硬編碼版本，不需要 vendor_id 和 language
            is_digression, digression_type, confidence = await self.digression_detector.detect(
                user_message=user_message,
                current_field=current_field,
                form_schema=form_schema,
                intent_result=intent_result
            )

        if is_digression:
            return await self._handle_digression(
                user_message=user_message,
                session_state=session_state,
                form_schema=form_schema,
                digression_type=digression_type
            )

        # 4. 驗證資料格式
        is_valid, extracted_value, error_message = self.validator.validate_field(
            field_config=current_field,
            user_input=user_message
        )

        if not is_valid:
            return {
                "answer": f"{error_message}\n\n{current_field['prompt']}",
                "validation_failed": True
            }

        # 5. 儲存資料
        collected_data = session_state['collected_data']
        collected_data[current_field['field_name']] = extracted_value
        next_field_index = current_field_index + 1

        # 6. 檢查是否完成所有欄位
        if next_field_index >= len(form_schema['fields']):
            # 更新collected_data
            await self.update_session_state(
                session_id=session_id,
                collected_data=collected_data
            )
            # 進入審核模式（而非直接完成表單）
            return await self.show_review_summary(session_id, vendor_id)

        # 7. 更新會話狀態並提示下一個欄位
        await self.update_session_state(
            session_id=session_id,
            current_field_index=next_field_index,
            collected_data=collected_data
        )

        next_field = form_schema['fields'][next_field_index]
        total_fields = len(form_schema['fields'])

        return {
            "answer": f"✅ **{current_field['field_label']}** 已記錄！\n\n📊 進度：{next_field_index}/{total_fields}\n\n{next_field['prompt']}",
            "current_field": next_field['field_name'],
            "progress": f"{next_field_index}/{total_fields}"
        }

    async def _handle_digression(
        self,
        user_message: str,
        session_state: Dict,
        form_schema: Dict,
        digression_type: str
    ) -> Dict:
        """處理離題情況"""
        if digression_type == "explicit_exit":
            # 明確退出
            await self.update_session_state(
                session_id=session_state['session_id'],
                state=FormState.CANCELLED
            )
            return {
                "answer": "已取消表單填寫。如需重新申請，請隨時告訴我！",
                "form_cancelled": True
            }

        elif digression_type == "question":
            # 用戶問問題（需要整合到主對話流程）
            # 保存待處理的問題到資料庫
            await asyncio.to_thread(self._save_pending_question_sync, session_state['session_id'], user_message)

            await self.update_session_state(
                session_id=session_state['session_id'],
                state=FormState.DIGRESSION
            )
            return {
                "answer": f"💡 您的**{form_schema['form_name']}**還未完成，需要繼續填寫嗎？\n• 輸入「**繼續**」恢復填寫\n• 輸入「**回答**」回答您的問題\n• 輸入「**取消**」結束",
                "allow_resume": True,
                "pending_question": user_message
            }

        else:  # irrelevant_response
            current_field = form_schema['fields'][session_state['current_field_index']]
            return {
                "answer": f"抱歉，我沒聽懂您的回覆。\n\n{current_field['prompt']}\n\n（或輸入「**取消**」結束填寫）"
            }

    async def resume_form_filling(self, session_id: str) -> Dict:
        """恢復表單填寫"""
        session_state = await self.get_session_state(session_id)
        if not session_state or session_state['state'] != FormState.DIGRESSION:
            return {
                "answer": "找不到待恢復的表單會話。"
            }

        # 更新狀態為 COLLECTING
        await self.update_session_state(
            session_id=session_id,
            state=FormState.COLLECTING
        )

        form_schema = await self.get_form_schema(session_state['form_id'])
        current_field = form_schema['fields'][session_state['current_field_index']]
        total_fields = len(form_schema['fields'])
        completed = session_state['current_field_index']

        return {
            "answer": f"好的，繼續填寫！\n\n📊 進度：{completed}/{total_fields}\n\n{current_field['prompt']}",
            "form_resumed": True
        }

    async def _complete_form(
        self,
        session_state: Dict,
        form_schema: Dict,
        collected_data: Dict
    ) -> Dict:
        """完成表單填寫"""
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

        # 3. 取得完成訊息（如果有 knowledge_id，從知識庫讀取答案）
        completion_message = "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快處理您的資料。"

        knowledge_id = session_state.get('knowledge_id')
        if knowledge_id:
            # 從知識庫讀取答案
            knowledge_answer = await asyncio.to_thread(self._get_knowledge_answer_sync, knowledge_id)
            if knowledge_answer:
                completion_message = f"✅ **表單填寫完成！**\n\n{knowledge_answer}"

        return {
            "answer": completion_message,
            "form_completed": True,
            "submission_id": submission_id,
            "collected_data": collected_data
        }

    async def cancel_form(self, session_id: str) -> Dict:
        """取消表單填寫"""
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return {
                "answer": "找不到表單會話。"
            }

        # 更新狀態為已取消
        await self.update_session_state(
            session_id=session_id,
            state=FormState.CANCELLED
        )

        return {
            "answer": "已取消表單填寫。如需重新申請，請隨時告訴我！",
            "form_cancelled": True
        }

    # ========================================================================
    # 表單審核與編輯功能（新增）
    # ========================================================================

    async def show_review_summary(
        self,
        session_id: str,
        vendor_id: int
    ) -> Dict:
        """顯示表單審核摘要，讓用戶確認或修改"""
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return {"answer": "找不到表單會話", "error": True}

        form_schema = await self.get_form_schema(
            session_state['form_id'],
            vendor_id
        )

        collected_data = session_state.get('collected_data', {})

        # 格式化摘要
        summary = self._format_review_summary(form_schema, collected_data)

        # 更新狀態為 REVIEWING
        await self.update_session_state(
            session_id=session_id,
            state=FormState.REVIEWING
        )

        return {
            "answer": summary,
            "state": "REVIEWING",
            "allow_confirm": True,
            "allow_edit": True,
            "form_id": session_state['form_id']
        }

    def _format_review_summary(
        self,
        form_schema: Dict,
        collected_data: Dict,
        changed_field: str = None
    ) -> str:
        """格式化審核摘要"""
        lines = [
            "✅ **所有欄位已填寫完成！**",
            "",
            "【您的資料】",
            "━" * 30
        ]

        # Emoji 映射
        emoji_map = {
            "name": "📝", "full_name": "📝", "姓名": "📝",
            "address": "📍", "地址": "📍",
            "phone": "📞", "電話": "📞", "聯絡電話": "📞",
            "email": "📧",
            "date": "📅", "日期": "📅"
        }

        for idx, field in enumerate(form_schema['fields'], 1):
            field_name = field['field_name']
            field_label = field['field_label']
            value = collected_data.get(field_name, '')

            # 選擇 emoji
            emoji = "▪️"
            for key, icon in emoji_map.items():
                if key in field_name.lower() or key in field_label:
                    emoji = icon
                    break

            # 如果是剛修改的欄位，加上標記
            if field_name == changed_field:
                lines.append(f"{idx}. {emoji} **{field_label}**：{value}  ✨ ← 已更新")
            else:
                lines.append(f"{idx}. {emoji} **{field_label}**：{value}")

        lines.extend([
            "━" * 30,
            "",
            "**資料是否正確？**",
            "• 輸入「**確認**」→ 提交表單",
            "• 輸入「**編號**」→ 修改欄位（例如：2）",
            "• 輸入「**取消**」→ 放棄填寫"
        ])

        return "\n".join(lines)

    async def handle_edit_request(
        self,
        session_id: str,
        user_input: str,
        vendor_id: int
    ) -> Dict:
        """處理編輯請求（支援編號或欄位名稱）"""
        session_state = await self.get_session_state(session_id)
        form_schema = await self.get_form_schema(
            session_state['form_id'],
            vendor_id
        )

        # 嘗試解析為數字
        try:
            field_number = int(user_input.strip())
            if 1 <= field_number <= len(form_schema['fields']):
                field_index = field_number - 1
                return await self._start_editing_field(
                    session_id,
                    field_index,
                    form_schema
                )
            else:
                return {
                    "answer": f"❌ 編號無效，請輸入 1-{len(form_schema['fields'])} 之間的數字",
                    "error": True
                }
        except ValueError:
            # 無法解析為數字，返回提示
            return {
                "answer": "❌ 請輸入有效的欄位編號（數字）",
                "error": True
            }

    async def _start_editing_field(
        self,
        session_id: str,
        field_index: int,
        form_schema: Dict
    ) -> Dict:
        """開始編輯特定欄位"""
        field = form_schema['fields'][field_index]

        # 更新狀態：設置為編輯模式，並記錄正在編輯的欄位
        await self.update_session_state(
            session_id=session_id,
            state=FormState.EDITING,
            current_field_index=field_index
        )

        return {
            "answer": f"請重新輸入「**{field['field_label']}**」\n\n{field.get('prompt', '')}",
            "state": "EDITING",
            "editing_field": field['field_name'],
            "field_label": field['field_label']
        }

    async def collect_edited_field(
        self,
        session_id: str,
        user_message: str,
        vendor_id: int
    ) -> Dict:
        """收集編輯後的欄位值"""
        session_state = await self.get_session_state(session_id)
        form_schema = await self.get_form_schema(
            session_state['form_id'],
            vendor_id
        )

        current_field = form_schema['fields'][session_state['current_field_index']]

        # 驗證欄位
        is_valid, extracted_value, error_message = self.validator.validate_field(
            field_config=current_field,
            user_input=user_message
        )

        if not is_valid:
            return {
                "answer": f"❌ {error_message}\n\n請重新輸入「**{current_field['field_label']}**」",
                "validation_failed": True,
                "state": "EDITING"
            }

        # 更新欄位值
        collected_data = session_state.get('collected_data', {})
        collected_data[current_field['field_name']] = extracted_value

        await self.update_session_state(
            session_id=session_id,
            collected_data=collected_data,
            state=FormState.REVIEWING  # 回到審核模式
        )

        # 顯示更新後的摘要，標記修改的欄位
        summary = self._format_review_summary(
            form_schema,
            collected_data,
            changed_field=current_field['field_name']
        )

        return {
            "answer": f"✅ 已更新「**{current_field['field_label']}**」\n\n{summary}",
            "state": "REVIEWING",
            "field_updated": True
        }

    # ========================================================================

    def _cleanup_expired_sessions_sync(self, timeout_minutes: int = 30) -> int:
        """清理過期的表單會話（同步）"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE form_sessions
                    SET state = %s, cancelled_at = NOW()
                    WHERE state IN (%s, %s)
                      AND last_activity_at < NOW() - INTERVAL '%s minutes'
                """, (
                    FormState.CANCELLED,
                    FormState.COLLECTING,
                    FormState.DIGRESSION,
                    timeout_minutes
                ))

                rows_affected = cursor.rowcount
                print(f"🧹 清理了 {rows_affected} 個過期的表單會話")
                return rows_affected
        except Exception as e:
            print(f"❌ 清理過期會話失敗: {e}")
            return 0

    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """清理過期的表單會話（異步）"""
        return await asyncio.to_thread(
            self._cleanup_expired_sessions_sync,
            timeout_minutes
        )
