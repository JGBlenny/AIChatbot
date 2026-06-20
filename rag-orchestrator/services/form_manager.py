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
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import asyncio
import json
import psycopg2.extras
import asyncpg
from services.db_utils import get_db_cursor
from services.form_validator import FormValidator
from services.digression_detector import DigressionDetector
from services.digression_detector_db import DigressionDetectorDB
from services.api_call_handler import get_api_call_handler
from services.image_recognition_service import ImageRecognitionService
import logging

logger = logging.getLogger(__name__)


class FormState:
    """表單狀態枚舉"""
    COLLECTING = "COLLECTING"  # 收集中
    DIGRESSION = "DIGRESSION"  # 離題中
    REVIEWING = "REVIEWING"    # 審核中
    EDITING = "EDITING"        # 編輯中
    PAUSED = "PAUSED"          # 暫停中（SOP form_then_api 用）
    CONFIRMING = "CONFIRMING"  # 確認中（SOP immediate 模式用）
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

    # 表單串接（form-chaining）：一次對話中連續自動串接的深度上限（R6.1）
    MAX_CHAIN_DEPTH = 3

    # 取消表單的關鍵字（精確比對）。集中於此避免多處硬編漂移。
    # 註：離題偵測器另有更寬的退出語清單（含「不填了/停止」等，子字串比對），
    # 負責 text 等「不跳過離題偵測」欄位；此清單供 select/api_select 等選單型
    # 欄位（跳過離題偵測）與 DIGRESSION 狀態的明確取消使用。
    CANCEL_KEYWORDS = ["取消", "算了", "cancel"]

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

    async def get_next_question(self, session_id: str) -> Optional[str]:
        """獲取當前表單的下一個問題（僅回傳 prompt 文字）"""
        info = await self.get_next_field_info(session_id)
        return info.get('prompt') if info else None

    async def get_next_field_info(self, session_id: str) -> Optional[Dict]:
        """獲取當前表單的下一個欄位資訊（含 field_name、field_type、prompt）"""
        try:
            session_state = await self.get_session_state(session_id)
            if not session_state:
                return None

            form_schema = await self.get_form_schema(
                session_state['form_id'],
                session_state.get('vendor_id')
            )
            if not form_schema:
                return None

            current_index = session_state.get('current_field_index', 0)
            fields = form_schema.get('fields', [])

            if current_index >= len(fields):
                return None

            current_field = fields[current_index]
            return {
                'prompt': current_field.get('prompt', ''),
                'field_name': current_field.get('field_name', ''),
                'field_type': current_field.get('field_type', 'text'),
            }
        except Exception as e:
            print(f"❌ 獲取下一個欄位資訊失敗: {e}")
            return None

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
        collected_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None
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
            if metadata is not None:
                update_fields.append("metadata = %s")
                params.append(json.dumps(metadata))

            # 根據狀態設置完成/取消時間
            if state == FormState.COMPLETED:
                update_fields.append("completed_at = NOW()")
            elif state == FormState.CANCELLED:
                update_fields.append("cancelled_at = NOW()")

            params.append(session_id)

            with get_db_cursor(dict_cursor=True) as cursor:
                # 只更新該 session 的「最新」一列。表單串接（form-chaining）會讓同一
                # session_id 同時存在多列（來源 COMPLETED + 後續 COLLECTING），若用
                # WHERE session_id 會波及已完成的歷史列；以最新 id 鎖定當前進行中的會話。
                cursor.execute(f"""
                    UPDATE form_sessions
                    SET {', '.join(update_fields)}
                    WHERE id = (
                        SELECT id FROM form_sessions
                        WHERE session_id = %s
                        ORDER BY id DESC
                        LIMIT 1
                    )
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
        collected_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        """更新會話狀態（異步）"""
        return await asyncio.to_thread(
            self._update_session_state_sync,
            session_id, state, current_field_index, collected_data, metadata
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
            "current_field_type": first_field.get('field_type', 'text'),
            "progress": f"1/{total_fields}"
        }

    def _present_first_field(self, form_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        組裝表單第一欄的呈現契約（純函式，不碰 DB）。

        抽取自 trigger_form_by_knowledge 既有的第一欄組裝邏輯，供串接
        （_maybe_chain_next_form）與既有知識觸發共用，避免重複。

        Args:
            form_schema: 表單定義（含 form_name / default_intro / fields）

        Returns:
            {
                "prompt": str,                    # 第一欄提示字串（select 含內建 1./2./3. 選項與取消提示）
                "current_field": str,             # 第一欄 field_name
                "current_field_type": str,        # 第一欄 field_type（如 'select'）
                "quick_replies": list[dict] | None,  # select 選項按鈕（text/value/style），非 select 為 None
            }
        """
        first_field = form_schema['fields'][0]

        # 使用表單的 default_intro 作為引導語
        intro_message = form_schema.get('default_intro') or ''

        # 組裝訊息：引導語 + 表單名稱 + 第一欄提示（含選項）+ 取消提示
        prompt = intro_message.strip()
        prompt += f"\n\n📝 **{form_schema['form_name']}**"
        prompt += f"\n\n{first_field['prompt']}"
        prompt += "\n\n（或輸入「**取消**」結束填寫）"

        return {
            "prompt": prompt,
            "current_field": first_field['field_name'],
            "current_field_type": first_field.get('field_type', 'text'),
            "quick_replies": self._build_quick_replies(first_field),
        }

    @staticmethod
    def _cancel_response(pending_question: Optional[str] = None) -> Dict:
        """取消表單的統一回應（訊息 + 旗標），避免多處取消訊息漂移。"""
        resp = {
            "answer": "已取消表單填寫。如需重新申請，請隨時告訴我！",
            "form_cancelled": True,
        }
        if pending_question is not None:
            resp["pending_question"] = pending_question
        return resp

    def _resolve_selected_route(
        self,
        form_schema: Dict[str, Any],
        collected_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        依完成的表單與收集資料，解出「被選中選項」的選項層路由（option-routing）。

        純函式、不碰 DB、全程容錯。回傳 None 表示「該選項無選項層路由」，
        交由呼叫端 fallback 表單層 next_form_id（決策 5 擴充共存 precedence）。

        Args:
            form_schema: 已完成的表單定義（含 fields[].options）
            collected_data: 已收集資料（field_name → 被選 value）

        Returns:
            None 或被選中選項的路由：
            {
                "next_form_id": Optional[str],   # 後續子樹（內部節點）
                "answer_kb": Optional[int],      # 葉答案知識 id
            }
            （僅含實際設定的鍵；兩者皆無 → None）

        解析步驟（design.md 元件 2）：
            1. 取終端 select 欄位：以 fields 最後一欄為主（表單完成＝末欄為終端）；
               若末欄非 select，退取 fields 中最後一個 select 欄位；仍無 → None。
            2. field_name → collected_data[field_name] = 被選 value。
            3. 於該欄位 options 找 value 相符之 option（無相符 → None；int/str 容錯）。
            4. option 含 next_form_id 或 answer_kb → 回該路由；否則 None。
        """
        try:
            fields = form_schema.get('fields') or []
            if not fields:
                return None

            # 1. 取終端 select 欄位：末欄優先，否則退取最後一個 select 欄位
            select_field = None
            last_field = fields[-1]
            if last_field.get('field_type') == 'select':
                select_field = last_field
            else:
                for field in reversed(fields):
                    if field.get('field_type') == 'select':
                        select_field = field
                        break
            if select_field is None:
                return None

            # 2. 被選 value
            field_name = select_field.get('field_name')
            selected_value = collected_data.get(field_name) if field_name else None
            if selected_value is None:
                return None

            # 3. 於 options 找相符 option（沿用 collect_field_data 的 value/label 取值；int/str 容錯）
            matched = None
            for opt in select_field.get('options') or []:
                opt_value = opt.get('value', opt.get('label'))
                if selected_value == opt_value or str(selected_value) == str(opt_value):
                    matched = opt
                    break
            if matched is None:
                return None

            # 4. 組路由（僅含實際設定的鍵）
            route: Dict[str, Any] = {}
            if matched.get('next_form_id'):
                route['next_form_id'] = matched['next_form_id']
            if matched.get('answer_kb') is not None:
                route['answer_kb'] = matched['answer_kb']
            return route or None
        except Exception as e:
            print(f"❌ 解析選項層路由失敗（fallback 表單層）：{e}")
            return None

    async def _resolve_leaf_answer(self, answer_kb: int) -> Optional[str]:
        """
        以既有 branch_answer 取選項葉答案的知識文字（不經檢索，議題 2 async 邊界）。

        重用 ApiCallHandler._handle_branch_answer（choice/mapping 介面）以直接 kb_id 取知識
        answer；任何例外回 None（交由呼叫端 fallback / 容錯）。

        Args:
            answer_kb: 葉答案知識 id（knowledge_base.id）

        Returns:
            知識 answer 文字；解析失敗或無內容回 None。
        """
        try:
            api_handler = get_api_call_handler(self.db_pool)
            result = await api_handler._handle_branch_answer(
                choice="__leaf__", mapping={"__leaf__": answer_kb}
            )
            message = (result or {}).get('message')
            return message or None
        except Exception as e:
            print(f"❌ 葉答案解析失敗（answer_kb={answer_kb}）：{e}")
            return None

    async def _maybe_chain_next_form(
        self,
        source_form_schema: Dict[str, Any],
        session_state: Dict[str, Any],
        collected_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        在表單完成後，判斷是否需串接後續表單（form-chaining / option-routing）。

        純加值、全程容錯：任何例外或防護命中都回傳 None，不影響來源表單的完成。

        路由來源解析順序（決策 5：擴充共存 precedence）：
            1. 選項層路由（_resolve_selected_route）優先（collected_data 存在時）
            2. route.answer_kb → 以 branch_answer 解葉答案（失敗整體回 None，議題 2）
            3. route.next_form_id → 串接該子樹（沿用既有載入/會話/深度/循環/呈現）；
               若同時含 answer_kb，葉答案併入回傳供 _complete_form 合併呈現
            4. route 僅含 answer_kb（無子樹）→ 回葉契約 {"leaf": True, "answer": ...}，分支結束
            5. route 為 None → fallback 表單層 next_form_id（既有主幹串接，R1.2）

        Args:
            source_form_schema: 來源表單定義（含 next_form_id / fields[].options）
            session_state: 來源會話（含 session_id / user_id / vendor_id / metadata）
            collected_data: 來源表單新鮮收集資料（用於解析被選中選項；預設 None 保相容）

        Returns:
            None 表示無串接；否則：
            - 後續子樹呈現契約（含 leaf_answer，選項葉答案合併用，無則 None）：
              {next_form_id, first_field_prompt, current_field, current_field_type,
               quick_replies, chain_depth, leaf_answer}
            - 純葉答案：{"leaf": True, "answer": <知識文字>}
        """
        try:
            # 0. 選項層路由優先；無則 fallback 表單層 next_form_id（決策 5）
            leaf_answer = None
            route = None
            if collected_data is not None:
                route = self._resolve_selected_route(source_form_schema, collected_data)

            if route is not None:
                # 葉答案：以 branch_answer 取知識文字（不經檢索）；失敗整體回 None（議題 2）
                answer_kb = route.get('answer_kb')
                if answer_kb is not None:
                    leaf_answer = await self._resolve_leaf_answer(answer_kb)
                    if leaf_answer is None:
                        return None
                next_form_id = route.get('next_form_id')
                # 純葉答案（無子樹）：分支結束，回葉契約
                if not next_form_id:
                    print(f"選項葉答案（answer_kb={answer_kb}），分支結束")
                    return {"leaf": True, "answer": leaf_answer}
            else:
                # 1. fallback 表單層 next_form_id；無則不串接（R1.2）
                next_form_id = source_form_schema.get('next_form_id')
            if not next_form_id:
                return None

            # 子樹串接任一步失敗時的降級：若選項另帶葉答案，回葉契約以免「答案+子樹」
            # 在子樹載入/防護失敗時連葉答案一起遺失（R6 容錯）；無葉答案則照舊回 None。
            def _degrade_to_leaf():
                if leaf_answer is not None:
                    print("⚠️ 子樹串接未成，降級回選項葉答案（不丟失答案）")
                    return {"leaf": True, "answer": leaf_answer}
                return None

            session_id = session_state.get('session_id')
            user_id = session_state.get('user_id')
            vendor_id = session_state.get('vendor_id')

            # 2. 讀來源會話串接情境
            source_meta = session_state.get('metadata') or {}
            chain_depth = source_meta.get('chain_depth', 0)
            source_form_id = source_form_schema.get('form_id')
            # 已訪集合必含來源 form_id，用於偵測 A→A / A→B→A 循環。
            # 即使既有 metadata 帶了不含來源的部分集合，也補上來源以確保偵測正確。
            chain_visited = list(source_meta.get('chain_visited') or [])
            if source_form_id and source_form_id not in chain_visited:
                chain_visited.append(source_form_id)

            # 3. 防護：深度上限（R6.1）
            if chain_depth + 1 > self.MAX_CHAIN_DEPTH:
                print(f"⛓️ 串接深度達上限（{self.MAX_CHAIN_DEPTH}），不再自動觸發後續表單：{next_form_id}")
                return _degrade_to_leaf()

            # 3b. 防護：循環偵測（R6.2）
            if next_form_id in chain_visited:
                print(f"⛓️ 偵測到串接循環（{next_form_id} 已在已訪集合），中止串接")
                return _degrade_to_leaf()

            # 4. 載入後續表單（_get_form_schema_sync 已過濾 is_active；不存在/未啟用 → None，R1.3）
            next_schema = await asyncio.to_thread(
                self._get_form_schema_sync, next_form_id, vendor_id
            )
            if not next_schema:
                print(f"⚠️ 後續表單不存在或未啟用，跳過串接：{next_form_id}")
                return _degrade_to_leaf()

            # 5. 建立後續 COLLECTING 會話（INSERT 新列，沿用同一 session_id，R2.1/R2.4）
            new_session = await self.create_form_session(
                session_id=session_id,
                user_id=user_id,
                vendor_id=vendor_id,
                form_id=next_form_id,
            )
            if not new_session:
                print(f"⚠️ 建立後續表單會話失敗，跳過串接：{next_form_id}")
                return _degrade_to_leaf()

            # 6. 寫入後續會話 metadata：串接深度 + 已訪集合 + 沿用角色（R2.5）
            new_metadata = {
                "chain_depth": chain_depth + 1,
                "chain_visited": chain_visited + [next_form_id],
            }
            role_id = source_meta.get('role_id')
            if role_id:
                new_metadata['role_id'] = role_id
            await self.update_session_state(session_id=session_id, metadata=new_metadata)

            # 7. 組後續表單第一欄呈現契約
            presented = self._present_first_field(next_schema)
            print(f"⛓️ 串接後續表單：{source_form_id} → {next_form_id}（depth={chain_depth + 1}）")

            return {
                "next_form_id": next_form_id,
                "first_field_prompt": presented["prompt"],
                "current_field": presented["current_field"],
                "current_field_type": presented["current_field_type"],
                "quick_replies": presented["quick_replies"],
                "chain_depth": chain_depth + 1,
                # 選項葉答案（answer_kb + next_form_id 並存時）供 _complete_form 合併呈現；無則 None
                "leaf_answer": leaf_answer,
            }
        except Exception as e:
            print(f"❌ 串接後續表單失敗（不影響來源完成）：{e}")
            # 串接過程例外：若選項已解出葉答案，降級回葉契約不丟失答案；否則 None
            return {"leaf": True, "answer": leaf_answer} if leaf_answer else None

    async def trigger_form_by_knowledge(
        self,
        knowledge_id: int,
        form_id: str,
        session_id: str,
        user_id: str,
        vendor_id: int,
        trigger_question: str = None,
        role_id: str = None
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
            role_id: JGB 角色 ID（B2B 模式用）

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

        # 存 role_id 到 metadata（form_sessions 表沒有 role_id 欄位）
        if role_id and session_state:
            metadata = session_state.get('metadata') or {}
            metadata['role_id'] = role_id
            await self.update_session_state(
                session_id=session_id,
                metadata=metadata
            )
            session_state['metadata'] = metadata

        if not session_state:
            return {
                "answer": "抱歉，創建表單會話失敗，請稍後再試。",
                "form_triggered": False
            }

        # 3. 組合回應（表單引導語 + 表單提示）— 抽取為共用 helper
        total_fields = len(form_schema['fields'])
        presented = self._present_first_field(form_schema)

        return {
            "answer": presented["prompt"],
            "form_triggered": True,
            "form_id": form_id,
            "current_field": presented["current_field"],
            "current_field_type": presented["current_field_type"],
            "quick_replies": presented["quick_replies"],
            "progress": f"1/{total_fields}",
            "triggered_by_knowledge": knowledge_id
        }

    async def collect_field_data(
        self,
        user_message: str,
        session_id: str,
        intent_result: Optional[Dict] = None,
        vendor_id: int = 1,
        language: str = 'zh-TW',
        image_urls: Optional[List[str]] = None,
    ) -> Dict:
        """
        收集欄位資料（核心流程）

        Args:
            user_message: 用戶輸入
            session_id: 會話 ID
            intent_result: 意圖分類結果（用於離題偵測）
            vendor_id: 業者 ID（用於載入專屬配置）
            language: 語言代碼（用於載入對應語言的關鍵字）
            image_urls: 圖片 S3 URL 列表（表單 image 欄位使用）

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
            elif user_message.strip() in self.CANCEL_KEYWORDS:
                # 處理離題後取消，取得待處理的問題
                pending_question = await asyncio.to_thread(self._get_pending_question_sync, session_id)

                await self.update_session_state(
                    session_id=session_id,
                    state=FormState.CANCELLED
                )
                return self._cancel_response(pending_question)

        # 2. 獲取表單定義
        form_schema = await self.get_form_schema(session_state['form_id'])
        if not form_schema:
            return {
                "answer": "找不到表單定義，請重新開始。"
            }

        current_field_index = session_state['current_field_index']
        current_field = form_schema['fields'][current_field_index]

        # 3. 偵測離題（動態欄位類型或自由文字跳過離題偵測，因為輸入可能是姓名、地址、關鍵字等非意圖文字）
        field_type = current_field.get('field_type', 'text')
        validation_type = current_field.get('validation_type', '')
        skip_digression = field_type in ('api_search', 'api_select', 'image', 'select') or validation_type == 'free_text'

        # 3a. 取消關鍵字（僅選單型欄位）：select / api_select 會跳過離題偵測，使用者輸入
        #     「取消」原本會被當成選項值，故在此明確處理，與第一欄提示「輸入取消結束填寫」
        #     一致。其餘欄位（text 走離題偵測；free_text / api_search 維持既有行為）不受影響。
        #     取消後轉 CANCELLED、不進入 _complete_form，故不會自動串接後續表單（R5.1/R5.3）。
        if field_type in ('select', 'api_select') and user_message.strip() in self.CANCEL_KEYWORDS:
            await self.update_session_state(
                session_id=session_id,
                state=FormState.CANCELLED
            )
            return self._cancel_response()

        if not skip_digression:
            has_images = bool(image_urls)
            # 如果���用資料庫版本，傳入 vendor_id 和 language
            if isinstance(self.digression_detector, DigressionDetectorDB):
                is_digression, digression_type, confidence = await self.digression_detector.detect(
                    user_message=user_message,
                    current_field=current_field,
                    form_schema=form_schema,
                    intent_result=intent_result,
                    vendor_id=vendor_id,
                    language=language,
                    has_images=has_images,
                )
            else:
                # 硬編碼版本，不需要 vendor_id 和 language
                is_digression, digression_type, confidence = await self.digression_detector.detect(
                    user_message=user_message,
                    current_field=current_field,
                    form_schema=form_schema,
                    intent_result=intent_result,
                    has_images=has_images,
                )

            if is_digression:
                return await self._handle_digression(
                    user_message=user_message,
                    session_state=session_state,
                    form_schema=form_schema,
                    digression_type=digression_type
                )

        # 4. 動態欄位分派（api_search / api_select / image）
        # field_type 已在 Step 3 取得

        # 為動態欄位處理器提供 form_schema_fields 參考
        session_state['form_schema_fields'] = form_schema.get('fields', [])

        # 4a. image 欄位分派
        if field_type == 'image':
            logger.info(f"[image_field] field_name={current_field.get('field_name')}, has_images={bool(image_urls)}")
            result = await self._handle_image_field(
                current_field=current_field,
                user_message=user_message,
                session_state=session_state,
                image_urls=image_urls,
            )

            if not result['field_completed']:
                return {
                    "answer": result['prompt'],
                    "form_completed": False,
                    "current_field": current_field.get('field_name'),
                    "current_field_type": field_type,
                }

            # 已完成，存入 collected_data
            collected_data = session_state['collected_data']
            collected_data[current_field['field_name']] = result['collected_value']

            # 儲存辨識建議至 metadata（如有）
            if result.get('recognition_result'):
                metadata = session_state.get('metadata', {})
                metadata['recognition_suggestions'] = result['recognition_result']
                session_state['metadata'] = metadata

            next_field_index = current_field_index + 1

            # 檢查是否完成所有欄位
            if next_field_index >= len(form_schema['fields']):
                await self.update_session_state(
                    session_id=session_id,
                    collected_data=collected_data,
                    metadata=session_state.get('metadata', {}),
                )
                skip_review = form_schema.get('skip_review', False)
                if skip_review:
                    session_state = await self.get_session_state(session_id)
                    return await self._complete_form(session_state, form_schema, collected_data)
                else:
                    return await self.show_review_summary(session_id, vendor_id)

            # 更新並提示下一欄位
            await self.update_session_state(
                session_id=session_id,
                current_field_index=next_field_index,
                collected_data=collected_data,
                metadata=session_state.get('metadata', {}),
            )

            next_field = form_schema['fields'][next_field_index]
            total_fields = len(form_schema['fields'])

            # 如果有辨識結果，附加提示
            recognition_hint = ""
            if result.get('recognition_result') and result['recognition_result'].get('is_damage'):
                desc = result['recognition_result'].get('description', '')
                if desc:
                    recognition_hint = f"\n\n📷 圖片辨識：{desc}"

            # 如果下一欄位也是 api_select，先取選項
            next_field_type = next_field.get('field_type', 'text')
            if next_field_type == 'api_select':
                session_state = await self.get_session_state(session_id)
                session_state['form_schema_fields'] = form_schema.get('fields', [])
                select_result = await self._handle_api_select_field(next_field, "", session_state)
                if not select_result['resolved']:
                    prompt_text = select_result['prompt']

                    # 辨識建議匹配：比對 suggested_category 與 api_select 選項 → 自動填入
                    next_field_name = next_field.get('field_name', '')
                    rec_suggestions = session_state.get('metadata', {}).get('recognition_suggestions')
                    if rec_suggestions and next_field_name == 'category_id' and rec_suggestions.get('is_damage'):
                        dynamic_state = session_state.get('metadata', {}).get('dynamic_field_state', {})
                        pending_options = dynamic_state.get('pending_options', [])
                        if pending_options:
                            match = self._match_category_suggestion(
                                recognition_suggestions=rec_suggestions,
                                options=pending_options,
                            )
                            if match:
                                opt = match['matched_option']
                                display_field = next_field.get('display_field') or next_field.get('api_config', {}).get('display_field', 'name')
                                opt_name = opt.get(display_field, opt.get('name', ''))
                                value_field = next_field.get('value_field') or next_field.get('api_config', {}).get('value_field', 'id')
                                auto_value = opt.get(value_field)

                                # 自動填入 category_id
                                collected_data = session_state['collected_data']
                                collected_data[next_field_name] = auto_value
                                metadata = session_state.get('metadata', {})
                                metadata.pop('dynamic_field_state', None)
                                metadata.pop('pending_suggestion', None)

                                # 移動到下下個欄位
                                auto_next_index = next_field_index + 1
                                await self.update_session_state(
                                    session_id=session_id,
                                    current_field_index=auto_next_index,
                                    collected_data=collected_data,
                                    metadata=metadata,
                                )

                                if auto_next_index >= len(form_schema['fields']):
                                    skip_review = form_schema.get('skip_review', False)
                                    if skip_review:
                                        session_state = await self.get_session_state(session_id)
                                        return await self._complete_form(session_state, form_schema, collected_data)
                                    else:
                                        return await self.show_review_summary(session_id, vendor_id)

                                # --- 鏈式自動填入 item_id + broken_reason ---
                                auto_filled_labels = [f"分類：**{opt_name}**"]
                                auto_next_field = form_schema['fields'][auto_next_index]

                                if auto_next_field.get('field_name') == 'item_id' and auto_next_field.get('field_type') == 'api_select':
                                    session_state_fresh = await self.get_session_state(session_id)
                                    session_state_fresh['form_schema_fields'] = form_schema.get('fields', [])
                                    item_select_result = await self._handle_api_select_field(auto_next_field, "", session_state_fresh)

                                    if not item_select_result['resolved']:
                                        item_dynamic = session_state_fresh.get('metadata', {}).get('dynamic_field_state', {})
                                        item_options = item_dynamic.get('pending_options', [])
                                        item_display = auto_next_field.get('display_field') or auto_next_field.get('api_config', {}).get('display_field', 'name')
                                        item_match = self._match_item_suggestion(
                                            recognition_suggestions=rec_suggestions,
                                            options=item_options,
                                            display_field=item_display,
                                        )

                                        if item_match:
                                            item_opt = item_match['matched_option']
                                            item_value_field = auto_next_field.get('value_field') or auto_next_field.get('api_config', {}).get('value_field', 'id')
                                            item_auto_value = item_opt.get(item_value_field, item_opt.get('value'))
                                            item_opt_name = item_opt.get(item_display, item_opt.get('name', ''))

                                            collected_data['item_id'] = item_auto_value
                                            auto_filled_labels.append(f"項目：**{item_opt_name}**")
                                            meta_fresh = session_state_fresh.get('metadata', {})
                                            meta_fresh.pop('dynamic_field_state', None)

                                            auto_next_index += 1

                                            # 嘗試鏈式填入 broken_reason
                                            if auto_next_index < len(form_schema['fields']):
                                                reason_field = form_schema['fields'][auto_next_index]
                                                if reason_field.get('field_name') == 'broken_reason' and reason_field.get('field_type') == 'api_select':
                                                    await self.update_session_state(
                                                        session_id=session_id,
                                                        current_field_index=auto_next_index,
                                                        collected_data=collected_data,
                                                        metadata=meta_fresh,
                                                    )
                                                    session_state_fresh2 = await self.get_session_state(session_id)
                                                    session_state_fresh2['form_schema_fields'] = form_schema.get('fields', [])
                                                    reason_select_result = await self._handle_api_select_field(reason_field, "", session_state_fresh2)

                                                    if not reason_select_result['resolved']:
                                                        reason_dynamic = session_state_fresh2.get('metadata', {}).get('dynamic_field_state', {})
                                                        reason_options = reason_dynamic.get('pending_options', [])
                                                        reason_display = reason_field.get('display_field') or reason_field.get('api_config', {}).get('display_field', 'label')
                                                        reason_match = self._match_reason_suggestion(
                                                            recognition_suggestions=rec_suggestions,
                                                            options=reason_options,
                                                            display_field=reason_display,
                                                        )

                                                        if reason_match:
                                                            reason_opt = reason_match['matched_option']
                                                            reason_value_field = reason_field.get('value_field') or reason_field.get('api_config', {}).get('value_field', 'value')
                                                            reason_auto_value = reason_opt.get(reason_value_field, reason_opt.get('value', reason_opt.get('label')))
                                                            reason_opt_name = reason_opt.get(reason_display, reason_opt.get('label', ''))

                                                            collected_data['broken_reason'] = reason_auto_value
                                                            auto_filled_labels.append(f"原因：**{reason_opt_name}**")
                                                            meta_fresh2 = session_state_fresh2.get('metadata', {})
                                                            meta_fresh2.pop('dynamic_field_state', None)
                                                            auto_next_index += 1

                                                            await self.update_session_state(
                                                                session_id=session_id,
                                                                current_field_index=auto_next_index,
                                                                collected_data=collected_data,
                                                                metadata=meta_fresh2,
                                                            )

                                                            if auto_next_index >= len(form_schema['fields']):
                                                                skip_review = form_schema.get('skip_review', False)
                                                                if skip_review:
                                                                    session_state = await self.get_session_state(session_id)
                                                                    return await self._complete_form(session_state, form_schema, collected_data)
                                                                else:
                                                                    return await self.show_review_summary(session_id, vendor_id)

                                                            final_field = form_schema['fields'][auto_next_index]
                                                            labels_str = "\n- ".join(auto_filled_labels)
                                                            return {
                                                                "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📷 已根據照片自動選擇：\n- {labels_str}\n\n📊 進度：{auto_next_index}/{total_fields}\n\n{final_field['prompt']}",
                                                                "current_field": final_field['field_name'],
                                                                "current_field_type": final_field.get('field_type', 'text'),
                                                                "progress": f"{auto_next_index}/{total_fields}",
                                                            }

                                                        # reason match failed - show reason options
                                                        labels_str = "\n- ".join(auto_filled_labels)
                                                        return {
                                                            "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📷 已根據照片自動選擇：\n- {labels_str}\n\n📊 進度：{auto_next_index}/{total_fields}\n\n{reason_select_result['prompt']}",
                                                            "current_field": reason_field['field_name'],
                                                            "current_field_type": reason_field.get('field_type', 'text'),
                                                            "progress": f"{auto_next_index}/{total_fields}",
                                                        }

                                            # item matched but no reason chain or not broken_reason field
                                            await self.update_session_state(
                                                session_id=session_id,
                                                current_field_index=auto_next_index,
                                                collected_data=collected_data,
                                                metadata=meta_fresh,
                                            )

                                            if auto_next_index >= len(form_schema['fields']):
                                                skip_review = form_schema.get('skip_review', False)
                                                if skip_review:
                                                    session_state = await self.get_session_state(session_id)
                                                    return await self._complete_form(session_state, form_schema, collected_data)
                                                else:
                                                    return await self.show_review_summary(session_id, vendor_id)

                                            next_after_item = form_schema['fields'][auto_next_index]
                                            labels_str = "\n- ".join(auto_filled_labels)
                                            return {
                                                "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📷 已根據照片自動選擇：\n- {labels_str}\n\n📊 進度：{auto_next_index}/{total_fields}\n\n{next_after_item['prompt']}",
                                                "current_field": next_after_item['field_name'],
                                                "current_field_type": next_after_item.get('field_type', 'text'),
                                                "progress": f"{auto_next_index}/{total_fields}",
                                            }

                                        # item match failed - show item options with category already filled
                                        return {
                                            "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📷 已根據照片自動選擇分類：**{opt_name}**\n\n📊 進度：{auto_next_index}/{total_fields}\n\n{item_select_result['prompt']}",
                                            "current_field": auto_next_field['field_name'],
                                            "current_field_type": auto_next_field.get('field_type', 'text'),
                                            "progress": f"{auto_next_index}/{total_fields}",
                                        }

                                # Next field is not item_id api_select, return normally
                                return {
                                    "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📷 已根據照片自動選擇分類：**{opt_name}**\n\n📊 進度：{auto_next_index}/{total_fields}\n\n{auto_next_field['prompt']}",
                                    "current_field": auto_next_field['field_name'],
                                    "current_field_type": auto_next_field.get('field_type', 'text'),
                                    "progress": f"{auto_next_index}/{total_fields}",
                                }

                    return {
                        "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📊 進度：{next_field_index}/{total_fields}\n\n{prompt_text}",
                        "current_field": next_field['field_name'],
                        "current_field_type": next_field.get('field_type', 'text'),
                        "progress": f"{next_field_index}/{total_fields}",
                    }

            return {
                "answer": f"✅ **{current_field['field_label']}** 已記錄！{recognition_hint}\n\n📊 進度：{next_field_index}/{total_fields}\n\n{next_field['prompt']}",
                "current_field": next_field['field_name'],
                "current_field_type": next_field.get('field_type', 'text'),
                "progress": f"{next_field_index}/{total_fields}",
            }

        # 4b. 檢查辨識建議（category_id / broken_note / emergency_status 的自動填入）
        metadata = session_state.get('metadata', {})
        recognition_suggestions = metadata.get('recognition_suggestions')
        if recognition_suggestions and field_type in ('api_select', 'text', 'select'):
            suggestion_result = await self._check_recognition_suggestion(
                current_field=current_field,
                user_message=user_message,
                session_state=session_state,
                recognition_suggestions=recognition_suggestions,
            )
            if suggestion_result is not None:
                return suggestion_result

        if field_type in ('api_search', 'api_select'):
            logger.info(f"[dynamic_field] field_type={field_type}, field_name={current_field.get('field_name')}, user_input={user_message[:50]}")
            if field_type == 'api_search':
                result = await self._handle_api_search_field(current_field, user_message, session_state)
            else:
                result = await self._handle_api_select_field(current_field, user_message, session_state)

            if not result['resolved']:
                # 檢查是否有辨識建議可附加到 api_select 選項列表
                prompt_text = result['prompt']
                metadata = session_state.get('metadata', {})
                recognition_suggestions = metadata.get('recognition_suggestions')
                if recognition_suggestions and field_name == 'category_id':
                    dynamic_state = metadata.get('dynamic_field_state', {})
                    pending_options = dynamic_state.get('pending_options', [])
                    if pending_options:
                        match = self._match_category_suggestion(
                            recognition_suggestions=recognition_suggestions,
                            options=pending_options,
                        )
                        if match:
                            opt = match['matched_option']
                            display_field = current_field.get('display_field') or current_field.get('api_config', {}).get('display_field', 'name')
                            opt_name = opt.get(display_field, opt.get('name', ''))
                            prompt_text = f"📷 根據照片判斷，這可能是「{opt_name}」，輸入「是」確認，或輸入編號選擇其他分類：\n\n{prompt_text}"
                            # 記錄待確認建議
                            metadata['pending_suggestion'] = {
                                'field_name': 'category_id',
                                'type': 'category',
                                'value': opt.get(current_field.get('value_field') or current_field.get('api_config', {}).get('value_field', 'id')),
                            }
                            session_state['metadata'] = metadata
                            await self.update_session_state(
                                session_id=session_state['session_id'],
                                metadata=metadata,
                            )

                return {
                    "answer": prompt_text,
                    "form_completed": False,
                    "current_field": current_field.get('field_name'),
                    "current_field_type": field_type,
                }

            # 已解析，存入 collected_data 並清除 dynamic_field_state
            collected_data = session_state['collected_data']
            collected_data[current_field['field_name']] = result['value']
            metadata = session_state.get('metadata', {})
            metadata.pop('dynamic_field_state', None)

            next_field_index = current_field_index + 1

            # 檢查是否完成所有欄位
            if next_field_index >= len(form_schema['fields']):
                await self.update_session_state(
                    session_id=session_id,
                    collected_data=collected_data,
                    metadata=metadata,
                )
                skip_review = form_schema.get('skip_review', False)
                if skip_review:
                    session_state = await self.get_session_state(session_id)
                    return await self._complete_form(session_state, form_schema, collected_data)
                else:
                    return await self.show_review_summary(session_id, vendor_id)

            # 更新並提示下一欄位
            await self.update_session_state(
                session_id=session_id,
                current_field_index=next_field_index,
                collected_data=collected_data,
                metadata=metadata,
            )

            next_field = form_schema['fields'][next_field_index]
            total_fields = len(form_schema['fields'])

            # 如果下一欄位也是 api_select 且無 depends_on，需要先取選項
            next_field_type = next_field.get('field_type', 'text')
            if next_field_type == 'api_select':
                # 重新取得 session_state（metadata 已更新）
                session_state = await self.get_session_state(session_id)
                session_state['form_schema_fields'] = form_schema.get('fields', [])
                select_result = await self._handle_api_select_field(next_field, "", session_state)
                if not select_result['resolved']:
                    return {
                        "answer": f"✅ **{current_field['field_label']}** 已記錄！\n\n📊 進度：{next_field_index}/{total_fields}\n\n{select_result['prompt']}",
                        "current_field": next_field['field_name'],
                        "current_field_type": next_field.get('field_type', 'text'),
                        "progress": f"{next_field_index}/{total_fields}",
                    }

            return {
                "answer": f"✅ **{current_field['field_label']}** 已記錄！\n\n📊 進度：{next_field_index}/{total_fields}\n\n{next_field['prompt']}",
                "current_field": next_field['field_name'],
                "current_field_type": next_field.get('field_type', 'text'),
                "progress": f"{next_field_index}/{total_fields}",
            }

        # 5. 標準欄位：驗證資料格式
        is_valid, extracted_value, error_message = self.validator.validate_field(
            field_config=current_field,
            user_input=user_message
        )

        if not is_valid:
            return {
                "answer": f"{error_message}\n\n{current_field['prompt']}",
                "validation_failed": True
            }

        # 5b. select 欄位：將 label 或編號轉換為 value
        if field_type == 'select' and current_field.get('options'):
            options = current_field['options']
            resolved_value = None
            stripped = extracted_value.strip()

            # 嘗試用編號選擇
            try:
                idx = int(stripped) - 1
                if 0 <= idx < len(options):
                    resolved_value = options[idx].get('value', options[idx].get('label'))
            except (ValueError, TypeError):
                pass

            # 嘗試用 label 匹配
            if resolved_value is None:
                for opt in options:
                    if stripped == opt.get('label', '') or stripped == str(opt.get('value', '')):
                        resolved_value = opt.get('value', opt.get('label'))
                        break

            if resolved_value is not None:
                extracted_value = resolved_value

        # 6. 儲存資料
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

            # 檢查是否跳過審核步驟（適用於單欄位快速查詢表單）
            skip_review = form_schema.get('skip_review', False)

            if skip_review:
                # 重新獲取最新的 session_state（包含最新的 metadata）
                session_state = await self.get_session_state(session_id)
                # 直接完成表單並執行後續動作
                return await self._complete_form(session_state, form_schema, collected_data)
            else:
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
            "current_field_type": next_field.get('field_type', 'text'),
            "progress": f"{next_field_index}/{total_fields}"
        }

    # ========================================
    # image 欄位處理
    # ========================================

    _SKIP_KEYWORDS = {"跳過", "略過", "skip", "不用"}
    _CONFIRM_KEYWORDS = {"是", "對", "確認", "正確", "ok", "yes", "好", "對的", "沒錯"}

    async def _handle_image_field(
        self,
        current_field: Dict,
        user_message: str,
        session_state: Dict,
        image_urls: Optional[List[str]] = None,
    ) -> Dict:
        """
        處理 image 類型欄位。

        Returns:
            {field_completed, collected_value, prompt, recognition_result}
        """
        # 1. 有 image_urls → 儲存圖片，嘗試辨識
        if image_urls:
            recognition_result = None
            if current_field.get('enable_recognition'):
                try:
                    # 從表單 schema 取得 category_id 的 API 選項名稱及完整分類樹，注入 Vision prompt
                    category_names = await self._fetch_category_names(session_state)
                    categories_tree = await self._fetch_categories_tree(session_state)
                    logger.info(f"[image_field] category_names for prompt: {category_names}, tree_count={len(categories_tree) if categories_tree else 0}")

                    service = ImageRecognitionService()
                    recognition_result = await service.analyze_images(
                        image_urls=image_urls,
                        context=user_message if user_message else None,
                        category_names=category_names,
                        categories_tree=categories_tree,
                        db_pool=self.db_pool,
                    )
                    logger.info(f"[image_field] recognition result: is_damage={recognition_result.get('is_damage')}, suggested_category={recognition_result.get('suggested_category')}, suggested_item={recognition_result.get('suggested_item')}, suggested_reason={recognition_result.get('suggested_reason')}, confidence={recognition_result.get('confidence')}")
                    # 存入 metadata
                    metadata = session_state.get('metadata', {})
                    metadata['recognition_suggestions'] = recognition_result
                    session_state['metadata'] = metadata
                except Exception as e:
                    logger.warning(f"[image_field] 圖片辨識失敗，仍儲存圖片: {e}")

            return {
                "field_completed": True,
                "collected_value": image_urls,
                "recognition_result": recognition_result,
                "prompt": "",
            }

        # 2. 無 image_urls，檢查跳過
        stripped = user_message.strip().lower() if user_message else ""
        if stripped in self._SKIP_KEYWORDS:
            if not current_field.get('required', False):
                return {
                    "field_completed": True,
                    "collected_value": None,
                    "recognition_result": None,
                    "prompt": "",
                }
            else:
                return {
                    "field_completed": False,
                    "collected_value": None,
                    "recognition_result": None,
                    "prompt": "此欄位為必填，請上傳損壞照片。",
                }

        # 3. 無 image_urls 且非跳過 → 提示上傳
        skip_hint = "，或輸入「跳過」" if not current_field.get('required', False) else ""
        return {
            "field_completed": False,
            "collected_value": None,
            "recognition_result": None,
            "prompt": f"請上傳損壞照片{skip_hint}。",
        }

    async def _fetch_category_names(self, session_state: Dict) -> Optional[List[str]]:
        """
        從 JGB 修繕分類 API 取得分類名稱列表，供 Vision prompt 注入。
        讓 GPT-4o 從真實選項中選擇，而非自由生成。
        """
        try:
            form_fields = session_state.get('form_schema_fields', [])
            for field in form_fields:
                if field.get('field_name') == 'category_id':
                    api_config = field.get('api_config', {})
                    endpoint = api_config.get('endpoint')
                    if endpoint:
                        api_handler = get_api_call_handler(self.db_pool)
                        if endpoint in api_handler.api_registry:
                            api_result = await api_handler.api_registry[endpoint](**{})
                            if api_result and api_result.get('success'):
                                data_path = api_config.get('data_path', 'data')
                                items = api_result.get(data_path, [])
                                display_field = api_config.get('display_field', 'name')
                                names = [item.get(display_field, '') for item in items if item.get(display_field)]
                                if names:
                                    logger.info(f"[image_field] 注入 {len(names)} 個分類名稱至 Vision prompt: {names}")
                                    return names
        except Exception as e:
            logger.warning(f"[image_field] 取得分類名稱失敗，Vision 將自由生成: {e}")
        return None

    async def _fetch_categories_tree(self, session_state: Dict) -> Optional[list]:
        """
        從 JGB 修��分類 API 取得完整分類樹（含 items + broken_reasons），
        供 Vision prompt 注入，讓 GPT-4o 精準選擇 item 和 reason。
        """
        try:
            form_fields = session_state.get('form_schema_fields', [])
            for field in form_fields:
                if field.get('field_name') == 'category_id':
                    api_config = field.get('api_config', {})
                    endpoint = api_config.get('endpoint')
                    if endpoint:
                        api_handler = get_api_call_handler(self.db_pool)
                        if endpoint in api_handler.api_registry:
                            api_result = await api_handler.api_registry[endpoint](**{})
                            if api_result and api_result.get('success'):
                                data_path = api_config.get('data_path', 'data')
                                categories = api_result.get(data_path, [])
                                if categories and isinstance(categories, list):
                                    # 確認至少有一個 category 含有 items
                                    has_items = any(cat.get('items') for cat in categories if isinstance(cat, dict))
                                    if has_items:
                                        logger.info(f"[image_field] 注入分類樹 ({len(categories)} 分類) 至 Vision prompt")
                                        return categories
        except Exception as e:
            logger.warning(f"[image_field] 取得分類樹失敗: {e}")
        return None

    # ========================================
    # 辨識建議匹配（供 5.2 使用）
    # ========================================

    def _match_category_suggestion(
        self,
        recognition_suggestions: Dict,
        options: List[Dict],
        display_field: str = "name",
    ) -> Optional[Dict]:
        """
        將辨識建議的 suggested_category 與 api_select 選項比對。

        Returns:
            {matched_option, confirmation_message} 或 None
        """
        confidence = recognition_suggestions.get("confidence", 0)
        if confidence < 0.7:
            return None

        suggested = recognition_suggestions.get("suggested_category", "")
        if not suggested:
            return None

        for opt in options:
            opt_name = opt.get(display_field, opt.get("label", ""))
            if opt_name == suggested:
                return {
                    "matched_option": opt,
                    "confirmation_message": f"根據照片判斷，這可能是「{opt_name}」，是否正確？（輸入「是」確認，或「不是」重新選擇）",
                }
        return None

    def _match_item_suggestion(
        self,
        recognition_suggestions: Dict,
        options: List[Dict],
        display_field: str = "name",
    ) -> Optional[Dict]:
        """
        將辨識建議的 suggested_item 與 item 選項比對。
        支援精確比對和包含比對。
        """
        confidence = recognition_suggestions.get("confidence", 0)
        if confidence < 0.7:
            return None

        suggested = recognition_suggestions.get("suggested_item", "")
        if not suggested:
            return None

        # 精確比對
        for opt in options:
            opt_name = opt.get(display_field, opt.get("label", ""))
            if opt_name == suggested:
                return {"matched_option": opt}

        # 包含比對（模糊）
        for opt in options:
            opt_name = opt.get(display_field, opt.get("label", ""))
            if suggested in opt_name or opt_name in suggested:
                return {"matched_option": opt}

        return None

    def _match_reason_suggestion(
        self,
        recognition_suggestions: Dict,
        options: List[Dict],
        display_field: str = "label",
    ) -> Optional[Dict]:
        """
        將辨識建議的 suggested_reason 與 broken_reason 選項比對。
        broken_reason 選項經 _normalize_options 後為 [{"label": "漏水", "value": "漏水"}, ...]
        """
        confidence = recognition_suggestions.get("confidence", 0)
        if confidence < 0.7:
            return None

        suggested = recognition_suggestions.get("suggested_reason", "")
        if not suggested:
            return None

        # 精確比對
        for opt in options:
            opt_name = opt.get(display_field, opt.get("name", opt.get("value", "")))
            if opt_name == suggested:
                return {"matched_option": opt}

        # 包含比對
        for opt in options:
            opt_name = opt.get(display_field, opt.get("name", opt.get("value", "")))
            if suggested in opt_name or opt_name in suggested:
                return {"matched_option": opt}

        return None

    @staticmethod
    def _build_quick_replies(field: Dict, include_skip: bool = False) -> Optional[list]:
        """根據欄位配置生成 quick_replies 按鈕列表"""
        replies = []
        field_type = field.get('field_type', 'text')

        if field_type == 'select' and field.get('options'):
            for opt in field['options']:
                if isinstance(opt, dict):
                    replies.append({"text": opt.get('label', ''), "value": str(opt.get('value', '')), "style": "default"})
                else:
                    replies.append({"text": str(opt), "value": str(opt), "style": "default"})

        elif field_type == 'api_select':
            # api_select 選項是動態的，在顯示選項時才生成
            pass

        # SOP 確認按鈕
        if not replies:
            return None

        if include_skip and not field.get('required', True):
            replies.append({"text": "跳過", "value": "跳過", "style": "secondary"})

        return replies

    def _get_broken_note_suggestion(self, recognition_suggestions: Dict) -> Optional[Dict]:
        """
        取得 broken_note 預填建議。

        Returns:
            {prefill_value, confirmation_message} 或 None
        """
        description = recognition_suggestions.get("description", "")
        if not description:
            return None

        return {
            "prefill_value": description,
            "confirmation_message": f"AI 描述：{description}\n\n是否使用此描述？可直接輸入修改內容。",
        }

    def _get_emergency_suggestion(self, recognition_suggestions: Dict) -> Optional[Dict]:
        """
        取得 emergency_status 建議。severity=critical → 建議緊急。

        Returns:
            {suggested_value, confirmation_message} 或 None
        """
        severity = recognition_suggestions.get("severity", "")
        if severity == "critical":
            return {
                "suggested_value": 1,  # 緊急
                "confirmation_message": "根據照片判斷損壞情況嚴重，建議選擇「緊急」。是否同意？",
            }
        return None

    async def _check_recognition_suggestion(
        self,
        current_field: Dict,
        user_message: str,
        session_state: Dict,
        recognition_suggestions: Dict,
    ) -> Optional[Dict]:
        """
        檢查當前欄位是否有辨識建議可套用。

        若有建議且用戶尚未回應 → 展示確認訊息
        若用戶已回應確認 → 自動填入
        若用戶拒絕 → 清除建議，回到正常流程

        Returns:
            回應字典，或 None（表示無建議、繼續正常流程）
        """
        metadata = session_state.get('metadata', {})
        field_name = current_field.get('field_name', '')
        pending_suggestion = metadata.get('pending_suggestion')

        # 如果有待確認的建議（用戶正在回應確認/拒絕）
        if pending_suggestion and pending_suggestion.get('field_name') == field_name:
            stripped = user_message.strip().lower()
            if stripped in self._CONFIRM_KEYWORDS:
                # 確認 → 自動填入
                return await self._accept_suggestion(
                    current_field=current_field,
                    session_state=session_state,
                    pending_suggestion=pending_suggestion,
                )
            else:
                # 拒絕 → 清除建議，回到正常流程
                metadata.pop('pending_suggestion', None)
                session_state['metadata'] = metadata
                return None  # 讓正常流程處理

        # 沒有待確認的建議 → 嘗試生成建議
        if field_name == 'category_id':
            # category 欄位：需要 api_select 選項來比對
            # 這裡不攔截，讓 api_select 先取選項，之後在選項展示時附加建議
            return None

        if field_name in ('item_id', 'broken_reason'):
            # item_id 和 broken_reason 的建議在鏈式自動填入中處理
            # 這裡不攔截，讓 api_select 正常取選項
            return None

        if field_name == 'broken_note':
            # 用戶輸入了實際內容 → 直接使用
            stripped_msg = user_message.strip()
            if stripped_msg and stripped_msg not in ('', '跳過', '略過', 'skip'):
                return None  # 讓正常流程直接接受用戶輸入

            # 用戶輸入「跳過」→ 自動用 AI 描述填入（不再詢問確認）
            suggestion = self._get_broken_note_suggestion(recognition_suggestions)
            if suggestion:
                # 直接填入 AI 描述��不需要確認
                return await self._accept_suggestion(
                    current_field=current_field,
                    session_state=session_state,
                    pending_suggestion={
                        'field_name': field_name,
                        'type': 'broken_note',
                        'value': suggestion['prefill_value'],
                    },
                )

        if field_name == 'emergency_status':
            suggestion = self._get_emergency_suggestion(recognition_suggestions)
            if suggestion:
                metadata['pending_suggestion'] = {
                    'field_name': field_name,
                    'type': 'emergency_status',
                    'value': suggestion['suggested_value'],
                }
                session_state['metadata'] = metadata
                await self.update_session_state(
                    session_id=session_state['session_id'],
                    metadata=metadata,
                )
                return {
                    "answer": suggestion['confirmation_message'],
                    "form_completed": False,
                }

        return None

    async def _accept_suggestion(
        self,
        current_field: Dict,
        session_state: Dict,
        pending_suggestion: Dict,
    ) -> Dict:
        """接受辨識建議，自動填入欄位值並推進"""
        metadata = session_state.get('metadata', {})
        collected_data = session_state.get('collected_data', {})
        field_name = current_field.get('field_name', '')
        value = pending_suggestion.get('value')

        # 填入值
        collected_data[field_name] = value

        # 清除待確認建議
        metadata.pop('pending_suggestion', None)

        # 取得 form_schema 以推進欄位
        form_schema = await self.get_form_schema(session_state['form_id'])
        current_field_index = session_state['current_field_index']
        next_field_index = current_field_index + 1

        if next_field_index >= len(form_schema['fields']):
            await self.update_session_state(
                session_id=session_state['session_id'],
                collected_data=collected_data,
                metadata=metadata,
            )
            skip_review = form_schema.get('skip_review', False)
            if skip_review:
                session_state = await self.get_session_state(session_state['session_id'])
                return await self._complete_form(session_state, form_schema, collected_data)
            else:
                return await self.show_review_summary(session_state['session_id'])

        await self.update_session_state(
            session_id=session_state['session_id'],
            current_field_index=next_field_index,
            collected_data=collected_data,
            metadata=metadata,
        )

        next_field = form_schema['fields'][next_field_index]
        total_fields = len(form_schema['fields'])

        return {
            "answer": f"✅ **{current_field['field_label']}** 已自動填入！\n\n📊 進度：{next_field_index}/{total_fields}\n\n{next_field['prompt']}",
            "current_field": next_field['field_name'],
            "current_field_type": next_field.get('field_type', 'text'),
            "progress": f"{next_field_index}/{total_fields}",
        }

    # ========================================
    # 動態欄位處理（api_search / api_select）
    # ========================================

    def _match_user_selection(
        self,
        user_input: str,
        options: List[Dict],
        display_field: str = "name"
    ) -> Optional[Dict]:
        """
        匹配用戶選擇：
        1. 純數字 → 按編號匹配（1-based）
        2. 文字 → 精確匹配 display_field
        3. 都不匹配 → 回傳 None
        """
        stripped = user_input.strip()

        # 按編號匹配
        if stripped.isdigit():
            idx = int(stripped)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            return None

        # 文字精確匹配
        for opt in options:
            if isinstance(opt, dict):
                if opt.get(display_field, "") == stripped or opt.get("label", "") == stripped:
                    return opt
            elif isinstance(opt, str) and opt == stripped:
                return {"label": opt, "value": opt}

        return None

    async def _handle_api_search_field(
        self,
        field: Dict,
        user_input: str,
        session_state: Dict,
    ) -> Dict:
        """
        處理 api_search 欄位的兩階段流程：
        1. searching: 用戶輸入關鍵字 → 呼叫 API → 回傳選項列表
        2. selecting: 用戶輸入編號 → 解析選擇 → 存入 collected_data
        """
        metadata = session_state.get('metadata', {})
        dynamic_state = metadata.get('dynamic_field_state', {})
        phase = dynamic_state.get('phase', 'searching')
        api_config = field.get('api_config', {})

        if phase == 'selecting':
            # 第二階段：用戶選擇
            pending_options = dynamic_state.get('pending_options', [])
            display_field = api_config.get('display_field', 'name')

            selected = self._match_user_selection(user_input, pending_options, display_field)
            if selected is None:
                # 無效選擇，重新顯示
                lines = self._format_options_list(pending_options, api_config)
                return {
                    "resolved": False,
                    "prompt": f"請輸入有效的選項編號：\n\n{lines}",
                }

            # 選擇成功
            value_field = api_config.get('value_field', 'id')
            return {
                "resolved": True,
                "value": selected.get(value_field, selected.get('value')),
            }

        # 第一階段：搜尋
        endpoint = api_config.get('endpoint')
        search_param = api_config.get('search_param', 'keyword')

        # 組裝 API 參數
        params = {}
        extra_params = api_config.get('extra_params', {})
        for k, v in extra_params.items():
            if isinstance(v, str) and v.startswith('{session.'):
                field_name = v[len('{session.'):-1]
                params[k] = metadata.get(field_name, '')
            else:
                params[k] = v
        params[search_param] = user_input

        # 呼叫 API
        logger.info(f"[api_search] endpoint={endpoint}, params={params}")
        try:
            api_handler = get_api_call_handler(self.db_pool)
            api_result = await api_handler.api_registry[endpoint](**params)
            logger.info(f"[api_search] result success={api_result.get('success')}, data_len={len(api_result.get('data', []))}")
        except Exception as e:
            logger.error(f"[api_search] 呼叫 {endpoint} 例外: {e}", exc_info=True)
            return {
                "resolved": False,
                "prompt": f"搜尋失敗，請稍後再試或重新輸入關鍵字。\n\n{field['prompt']}",
            }

        if not api_result.get('success', False):
            logger.warning(f"[api_search] API 回傳失敗: {api_result}")
            return {
                "resolved": False,
                "prompt": f"搜尋失敗，請稍後再試或重新輸入關鍵字。\n\n{field['prompt']}",
            }

        results = api_result.get('data', [])

        if not results:
            return {
                "resolved": False,
                "prompt": f"找不到符合「{user_input}」的結果，請重新輸入關鍵字。\n\n{field['prompt']}",
            }

        # 只有 1 筆結果時自動選取
        if len(results) == 1:
            value_field = api_config.get('value_field', 'id')
            display_field = api_config.get('display_field', 'name')
            selected = results[0]
            logger.info(f"[api_search] 僅 1 筆結果，自動選取: {selected.get(display_field, selected.get('name', ''))}")
            return {
                "resolved": True,
                "value": selected.get(value_field, selected.get('value')),
            }

        # 超過 10 筆截斷
        if len(results) > 10:
            results = results[:10]
            truncated_hint = f"\n\n💡 結果超過 10 筆，僅顯示前 10 筆。請輸入更精確的關鍵字縮小範圍。"
        else:
            truncated_hint = ""

        # 格式化選項列表
        lines = self._format_options_list(results, api_config)

        # 更新 dynamic_field_state 為 selecting
        metadata['dynamic_field_state'] = {
            'field_name': field['field_name'],
            'phase': 'selecting',
            'pending_options': results,
        }
        await self.update_session_state(
            session_id=session_state['session_id'],
            metadata=metadata,
        )

        return {
            "resolved": False,
            "prompt": f"搜尋到以下結果，請輸入編號選擇：\n\n{lines}{truncated_hint}",
        }

    async def _handle_api_select_field(
        self,
        field: Dict,
        user_input: str,
        session_state: Dict,
    ) -> Dict:
        """
        處理 api_select 欄位：
        - 無 depends_on：呼叫 API 取選項
        - 有 depends_on：從 metadata api_cache 中按 options_path 提取子選項
        """
        metadata = session_state.get('metadata', {})
        dynamic_state = metadata.get('dynamic_field_state', {})
        phase = dynamic_state.get('phase', 'fetching')
        collected_data = session_state.get('collected_data', {})

        if phase == 'selecting':
            # 用戶正在選擇
            pending_options = dynamic_state.get('pending_options', [])
            display_field = field.get('display_field') or field.get('api_config', {}).get('display_field', 'name')

            selected = self._match_user_selection(user_input, pending_options, display_field)
            if selected is None:
                lines = self._format_options_list(pending_options, field.get('api_config', {}), display_field=display_field)
                return {
                    "resolved": False,
                    "prompt": f"請輸入有效的選項編號：\n\n{lines}",
                }

            value_field = field.get('value_field') or field.get('api_config', {}).get('value_field', 'id')
            return {
                "resolved": True,
                "value": selected.get(value_field, selected.get('value')),
            }

        # 第一次進入：取得選項
        depends_on = field.get('depends_on')
        options = []

        if depends_on:
            # 級聯：從 api_cache 取子選項
            api_cache = metadata.get('api_cache', {})
            options_path = field.get('options_path', 'items')

            # 找到父欄位的值
            parent_value = collected_data.get(depends_on)

            # 找到父欄位定義以判斷 cache 來源
            cache_key = self._find_cache_key_for_field(depends_on, session_state.get('form_schema_fields', []), metadata)

            if cache_key and cache_key in api_cache:
                cached_data = api_cache[cache_key]['data']
                # 遞迴尋找：先找 depends_on 的父，再找當前
                parent_item = self._find_item_in_cache(cached_data, depends_on, parent_value, collected_data, session_state)
                if parent_item:
                    raw_options = parent_item.get(options_path, [])
                    # 處理字串陣列（如 broken_reasons）
                    options = self._normalize_options(raw_options)
        else:
            # 無依賴：呼叫 API
            api_config = field.get('api_config', {})
            endpoint = api_config.get('endpoint')

            api_handler = get_api_call_handler(self.db_pool)
            api_result = await api_handler.api_registry[endpoint](**{})

            if not api_result.get('success', False):
                return {
                    "resolved": False,
                    "prompt": f"取得選項失敗，請稍後再試。",
                }

            data_path = api_config.get('data_path', 'data')
            raw_data = api_result
            for key in data_path.split('.'):
                raw_data = raw_data.get(key, []) if isinstance(raw_data, dict) else raw_data

            options = raw_data if isinstance(raw_data, list) else []

            # 存入 api_cache
            cache_key = endpoint
            api_cache = metadata.get('api_cache', {})
            api_cache[cache_key] = {
                'data': options,
                'fetched_at': datetime.now().isoformat(),
            }
            metadata['api_cache'] = api_cache

        if not options:
            return {
                "resolved": False,
                "prompt": f"沒有可選的選項，請聯繫客服協助。",
            }

        # 格式化並顯示選項
        display_field = field.get('display_field') or field.get('api_config', {}).get('display_field', 'name')
        lines = self._format_options_list(options, field.get('api_config', {}), display_field=display_field)

        metadata['dynamic_field_state'] = {
            'field_name': field['field_name'],
            'phase': 'selecting',
            'pending_options': options,
        }
        await self.update_session_state(
            session_id=session_state['session_id'],
            metadata=metadata,
        )

        return {
            "resolved": False,
            "prompt": f"{field['prompt']}\n\n{lines}",
        }

    def _format_options_list(
        self,
        options: List,
        api_config: Dict = None,
        display_field: str = "name",
    ) -> str:
        """格式化選項為編號列表"""
        display_template = (api_config or {}).get('display_template')
        lines = []
        for i, opt in enumerate(options, 1):
            if isinstance(opt, dict):
                if display_template:
                    try:
                        label = display_template.format(**opt)
                    except (KeyError, IndexError):
                        label = opt.get(display_field, opt.get('label', str(opt)))
                else:
                    label = opt.get(display_field, opt.get('label', str(opt)))
            else:
                label = str(opt)
            lines.append(f"{i}. {label}")
        return "\n".join(lines)

    def _normalize_options(self, raw_options: list) -> list:
        """將字串陣列轉為統一的 dict 格式"""
        if not raw_options:
            return []
        if isinstance(raw_options[0], str):
            return [{"label": s, "value": s} for s in raw_options]
        return raw_options

    def _find_cache_key_for_field(
        self, field_name: str, form_fields: list, metadata: dict
    ) -> Optional[str]:
        """找到存有此欄位資料的 cache key"""
        api_cache = metadata.get('api_cache', {})
        # 最常見的情況：只有一個 cache key
        if len(api_cache) == 1:
            return list(api_cache.keys())[0]
        # 多個 cache key 時，遍歷 form_fields 找到有 api_config.endpoint 的
        for f in form_fields:
            if f.get('field_name') == field_name and f.get('api_config', {}).get('endpoint'):
                ep = f['api_config']['endpoint']
                if ep in api_cache:
                    return ep
        # fallback
        if api_cache:
            return list(api_cache.keys())[0]
        return None

    def _find_item_in_cache(
        self,
        cached_data: list,
        depends_on: str,
        parent_value: any,
        collected_data: dict,
        session_state: dict,
    ) -> Optional[Dict]:
        """在快取的樹狀結構中，根據已收集的值逐層定位到正確的節點"""
        # 取得表單 fields 定義以追蹤依賴鏈
        form_fields = session_state.get('form_schema_fields', [])

        # 建立依賴鏈：從當前 depends_on 往上追溯
        chain = []
        current_dep = depends_on
        dep_map = {f['field_name']: f for f in form_fields}
        while current_dep and current_dep in dep_map:
            chain.append(current_dep)
            current_dep = dep_map[current_dep].get('depends_on')

        chain.reverse()  # 從根到葉

        # 從根開始逐層定位
        current_level = cached_data
        for dep_field in chain:
            dep_value = collected_data.get(dep_field)
            if dep_value is None:
                logger.warning(f"[cascade] collected_data 缺少欄位 '{dep_field}'，無法定位級聯選項")
                return None
            # 在當前層找到匹配的項目
            found = None
            for item in current_level:
                if isinstance(item, dict) and item.get('id') == dep_value:
                    found = item
                    break
            if found is None:
                logger.warning(f"[cascade] 在快取中找不到 {dep_field}={dep_value} 的項目（共 {len(current_level)} 筆）")
                return None
            # 深入下一層
            dep_field_def = dep_map.get(dep_field, {})
            next_path = None
            # 找下一個依賴此欄位的 field 的 options_path
            for f in form_fields:
                if f.get('depends_on') == dep_field:
                    next_path = f.get('options_path')
                    break
            if next_path and dep_field != depends_on:
                current_level = found.get(next_path, [])
            else:
                # 最後一層，直接回傳
                return found

        # 如果 chain 為空，直接在 cached_data 中找
        for item in cached_data:
            if isinstance(item, dict) and item.get('id') == parent_value:
                return item
        return None

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
            return self._cancel_response()

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

    async def resume_form_filling(self, session_id: str, vendor_id: Optional[int] = None) -> Dict:
        """
        恢復表單填寫

        支持的恢復場景：
        1. DIGRESSION（離題後恢復）
        2. PAUSED（暫停後恢復，用於 SOP form_then_api）
        """
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return {
                "answer": "找不到待恢復的表單會話。"
            }

        current_state = session_state['state']

        # 檢查是否為可恢復的狀態
        if current_state not in [FormState.DIGRESSION, FormState.PAUSED]:
            return {
                "answer": f"該表單會話狀態為 {current_state}，無法恢復。"
            }

        # 更新狀態為 COLLECTING
        await self.update_session_state(
            session_id=session_id,
            state=FormState.COLLECTING
        )

        form_schema = await self.get_form_schema(
            session_state['form_id'],
            vendor_id or session_state.get('vendor_id')
        )
        current_field = form_schema['fields'][session_state['current_field_index']]
        total_fields = len(form_schema['fields'])
        completed = session_state['current_field_index']

        # 根據之前的狀態提供不同的提示
        if current_state == FormState.PAUSED:
            resume_message = "表單已恢復！繼續填寫吧。"
        else:  # DIGRESSION
            resume_message = "好的，繼續填寫！"

        return {
            "answer": f"{resume_message}\n\n📊 進度：{completed}/{total_fields}\n\n{current_field['prompt']}",
            "form_resumed": True,
            "resumed_from": current_state
        }

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
            # 寫入型 API（如 create_repair）不傳 knowledge_answer，避免錯誤時顯示無關內容
            pass_knowledge = knowledge_answer if on_complete_action == 'both' else None
            api_result = await self._execute_form_api(
                api_config=api_config,
                form_data=collected_data,
                session_state=session_state,
                knowledge_answer=pass_knowledge
            )

            # ⚠️ 檢查 API 是否返回需要用戶重新輸入的錯誤
            if api_result and not api_result.get('success'):
                error_type = api_result.get('error')

                # 特定錯誤類型：需要用戶重新輸入（不完成表單）
                if error_type in ['ambiguous_match', 'no_match', 'invalid_input']:
                    # ========== 新增：重試次數限制邏輯 ==========
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

        # 4. 保存表單提交記錄（查詢型表單不存，只有申請型才存）
        submission_id = None
        if on_complete_action != 'call_api':
            submission_id = await self.save_form_submission(
                session_id=session_state['id'],
                form_id=session_state['form_id'],
                user_id=session_state['user_id'],
                vendor_id=session_state['vendor_id'],
                submitted_data=collected_data
            )

        # 5. 格式化完成訊息
        # ⚠️ 如果表單由知識庫觸發，用戶已看過知識內容，不再重複顯示
        triggered_by_knowledge = session_state.get('knowledge_id') is not None
        completion_message = await self._format_completion_message(
            on_complete_action=on_complete_action,
            knowledge_answer=knowledge_answer,
            api_result=api_result,
            triggered_by_knowledge=triggered_by_knowledge
        )

        # 6. 表單串接（form-chaining / option-routing）：完成後依被選中選項或表單層
        #    next_form_id 自動接續。傳入新鮮 collected_data 以解析選項層路由（決策 4）。
        #    純加值——_maybe_chain_next_form 全程容錯，回 None 表示不串接（回應與現況一致）。
        #    來源表單核心完成（COMPLETED 狀態、save_form_submission）已於上方執行，不受串接影響。
        chain = await self._maybe_chain_next_form(
            form_schema, session_state, collected_data=collected_data
        )
        if chain:
            # 6a. 純葉答案（選項 answer_kb，無後續子樹）：分支結束。
            #     葉答案知識**覆寫** completion_message（決策 7，避免雙重回答）。
            if chain.get("leaf"):
                return {
                    "answer": chain["answer"],
                    "form_completed": True,
                    "submission_id": submission_id,
                    "collected_data": collected_data,
                    "api_result": api_result,
                }

            # 6b. 後續子樹：串接 turn 旗標契約（design 元件 4）——對前端為「新表單開始、
            #     等待輸入」，故 form_completed=False、form_triggered=True，
            #     form_id/current_field/quick_replies 指向後續表單。
            #     合併呈現的「頭部」：選項葉答案存在時以其覆寫 completion_message（決策 7），
            #     否則沿用 completion_message（表單層 fallback 行為不變）。
            head = chain.get("leaf_answer") or completion_message
            merged_answer = f"{head}\n\n---\n\n{chain['first_field_prompt']}"
            return {
                "answer": merged_answer,
                "form_completed": False,
                "form_triggered": True,
                "form_id": chain["next_form_id"],
                "current_field": chain["current_field"],
                "current_field_type": chain["current_field_type"],
                "quick_replies": chain["quick_replies"],
                "next_form_id": chain["next_form_id"],
                # 保留既有欄位（來源完成事實）
                "submission_id": submission_id,
                "collected_data": collected_data,
                "api_result": api_result,
            }

        return {
            "answer": completion_message,
            "form_completed": True,
            "submission_id": submission_id,
            "collected_data": collected_data,
            "api_result": api_result  # 返回 API 結果供外部使用
        }

    async def _execute_form_api(
        self,
        api_config: Dict,
        form_data: Dict,
        session_state: Dict,
        knowledge_answer: Optional[str]
    ) -> Dict:
        """執行表單完成後的 API 調用"""
        try:
            # 準備 session 數據
            metadata = session_state.get('metadata') or {}
            session_data = {
                'user_id': session_state.get('user_id'),
                'vendor_id': session_state.get('vendor_id'),
                'session_id': session_state.get('session_id'),
                'role_id': metadata.get('role_id'),
            }

            # 合併 static_params 到 form_data（支援 lookup_generic 的 category 等靜態參數）
            merged_form_data = {**form_data, **api_config.get('static_params', {})}

            # 帶入原始問題（觸發表單時的用戶問題）供 formatter 判斷意圖
            user_input = None
            trigger_question = session_state.get('trigger_question')
            if trigger_question:
                user_input = {"original_question": trigger_question}

            # 調用 API 處理器（傳遞 db_pool 以支持動態配置的 API）
            api_handler = get_api_call_handler(self.db_pool)
            result = await api_handler.execute_api_call(
                api_config=api_config,
                session_data=session_data,
                form_data=merged_form_data,
                user_input=user_input,
                knowledge_answer=knowledge_answer
            )

            return result

        except Exception as e:
            print(f"❌ 表單 API 調用失敗: {e}")
            return {
                'success': False,
                'error': str(e),
                'formatted_response': f"⚠️ 表單已提交，但後續處理時發生錯誤。請稍後再試或聯繫客服。"
            }

    async def _format_completion_message(
        self,
        on_complete_action: str,
        knowledge_answer: Optional[str],
        api_result: Optional[Dict],
        triggered_by_knowledge: bool = False
    ) -> str:
        """格式化表單完成訊息

        Args:
            triggered_by_knowledge: 表單是否由知識庫觸發（用戶已看過知識內容）
        """
        # 情況 1: 只顯示知識答案
        if on_complete_action == 'show_knowledge':
            # ⚠️ 如果表單由知識庫觸發，用戶已看過知識內容，不再重複顯示
            if triggered_by_knowledge:
                return "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快與您聯繫。"
            elif knowledge_answer:
                return f"✅ **表單填寫完成！**\n\n{knowledge_answer}"
            else:
                return "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快處理您的資料。"

        # 情況 2: 只調用 API
        if on_complete_action == 'call_api':
            if api_result and api_result.get('success'):
                return api_result.get('formatted_response', '✅ 操作成功！')
            elif api_result:
                return api_result.get('formatted_response', '❌ 操作失敗，請稍後再試。')
            else:
                return "❌ API 調用失敗，請稍後再試。"

        # 情況 3: 兩者都執行
        if on_complete_action == 'both':
            parts = ["✅ **表單填寫完成！**\n"]

            # API 結果
            if api_result and api_result.get('success'):
                parts.append(api_result.get('formatted_response', ''))
            elif api_result:
                parts.append(api_result.get('formatted_response', '⚠️ 後續處理時發生錯誤。'))

            # 知識答案（如果表單由知識庫觸發，用戶已看過，跳過）
            if knowledge_answer and not triggered_by_knowledge:
                parts.append(f"\n---\n\n{knowledge_answer}")

            return '\n'.join(parts)

        # 默認情況
        return "✅ **表單填寫完成！**\n\n感謝您完成表單！"

    async def pause_form(
        self,
        session_id: str,
        reason: str = "SOP form_then_api",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        暫停表單填寫（用於 SOP form_then_api 場景）

        當 SOP 需要先執行 API，然後再根據結果繼續填表時使用

        Args:
            session_id: 會話 ID
            reason: 暫停原因
            metadata: 附加元數據（如 API 配置、SOP context 等）

        Returns:
            操作結果
        """
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return {
                "answer": "找不到表單會話。",
                "error": True
            }

        # 保存暫停前的狀態和元數據
        pause_metadata = {
            "previous_state": session_state.get('state'),
            "paused_at": datetime.now().isoformat(),
            "reason": reason,
            **(metadata or {})
        }

        # 更新狀態為 PAUSED
        await self.update_session_state(
            session_id=session_id,
            state=FormState.PAUSED,
            metadata=pause_metadata
        )

        return {
            "answer": f"表單填寫已暫停。{reason}",
            "form_paused": True,
            "state": FormState.PAUSED,
            "can_resume": True
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

        return self._cancel_response()

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
