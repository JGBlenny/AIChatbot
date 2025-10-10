"""
意圖建議引擎
使用 OpenAI 分析 unclear 問題，判斷是否屬於業務範圍並建議新增意圖
"""

import os
import json
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import OpenAI


class IntentSuggestionEngine:
    """意圖建議引擎"""

    def __init__(self):
        """初始化引擎"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 資料庫配置
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin')
        }

        # 載入業務範圍配置
        self.business_scope = self._load_active_business_scope()

        # OpenAI 配置
        self.model = "gpt-4o-mini"
        self.temperature = 0.2
        self.max_tokens = 800

    def _load_active_business_scope(self) -> Dict[str, Any]:
        """載入當前啟用的業務範圍配置"""
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    scope_name,
                    scope_type,
                    display_name,
                    business_description,
                    example_questions,
                    example_intents,
                    relevance_prompt
                FROM business_scope_config
                WHERE is_active = true
                LIMIT 1
            """)

            row = cursor.fetchone()
            cursor.close()

            if row:
                return dict(row)
            else:
                # 預設配置
                return {
                    'scope_name': 'external',
                    'scope_type': 'property_management',
                    'display_name': '包租代管業者',
                    'business_description': 'JGB 包租代管服務相關業務',
                    'example_questions': [
                        '退租流程怎麼辦理？',
                        '租約什麼時候到期？',
                        '設備報修要找誰？'
                    ],
                    'example_intents': ['退租流程', '租約查詢', '設備報修'],
                    'relevance_prompt': None
                }

        finally:
            conn.close()

    def reload_business_scope(self):
        """重新載入業務範圍配置"""
        self.business_scope = self._load_active_business_scope()
        print(f"✅ 重新載入業務範圍: {self.business_scope['display_name']}")

    def analyze_unclear_question(
        self,
        question: str,
        user_id: Optional[str] = None,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析 unclear 問題，判斷是否屬於業務範圍並建議新意圖

        Args:
            question: 使用者問題
            user_id: 使用者 ID
            conversation_context: 對話上下文（可選）

        Returns:
            {
                "is_relevant": bool,           # 是否與業務相關
                "relevance_score": float,      # 相關性分數 (0-1)
                "suggested_intent": {          # 建議的意圖（如果相關）
                    "name": str,
                    "type": str,
                    "description": str,
                    "keywords": List[str]
                },
                "reasoning": str,              # OpenAI 推理說明
                "should_record": bool          # 是否應該記錄為建議
            }
        """

        # 構建 OpenAI Function Calling
        functions = [
            {
                "name": "analyze_business_relevance",
                "description": "分析問題是否與業務範圍相關，並建議新意圖",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_relevant": {
                            "type": "boolean",
                            "description": "問題是否與業務範圍相關"
                        },
                        "relevance_score": {
                            "type": "number",
                            "description": "相關性分數 (0-1)，0.7以上視為相關",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "suggested_name": {
                            "type": "string",
                            "description": "建議的意圖名稱（如果相關）"
                        },
                        "suggested_type": {
                            "type": "string",
                            "description": "建議的意圖類型",
                            "enum": ["knowledge", "data_query", "action", "hybrid"]
                        },
                        "suggested_description": {
                            "type": "string",
                            "description": "建議的意圖描述"
                        },
                        "suggested_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "建議的關鍵字列表（3-8個）"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "判斷理由和分析說明"
                        }
                    },
                    "required": ["is_relevant", "relevance_score", "reasoning"]
                }
            }
        ]

        # 構建系統提示
        system_prompt = f"""你是一個專業的意圖分析助手，專門判斷使用者問題是否屬於特定業務範圍。

當前業務範圍：{self.business_scope['display_name']}
業務描述：{self.business_scope['business_description']}

業務範圍內的問題範例：
{chr(10).join([f"- {q}" for q in self.business_scope['example_questions']])}

已存在的意圖範例：
{', '.join(self.business_scope['example_intents'])}

你的任務：
1. 判斷使用者問題是否與上述業務範圍相關
2. 如果相關且找不到匹配的現有意圖，建議創建新意圖
3. 提供相關性分數（0.7以上視為相關）
4. 建議合適的意圖名稱、類型、描述和關鍵字

意圖類型說明：
- knowledge: 知識查詢（流程、規定、使用方法等）
- data_query: 資料查詢（需要查詢資料庫，如租約、帳單等）
- action: 操作請求（需要執行動作，如報修、預約等）
- hybrid: 混合型（同時需要知識和資料/操作）

判斷標準：
- 相關性 ≥ 0.7：屬於業務範圍，建議新增意圖
- 相關性 0.4-0.7：可能相關，但需要更多資訊
- 相關性 < 0.4：不相關，不建議新增
"""

        # 如果有自訂的相關性提示，使用它
        if self.business_scope.get('relevance_prompt'):
            system_prompt = self.business_scope['relevance_prompt']

        # 構建使用者訊息
        user_message = f"問題：{question}"
        if conversation_context:
            user_message += f"\n\n對話上下文：{conversation_context}"

        # 呼叫 OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=functions,
                function_call={"name": "analyze_business_relevance"},
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # 解析結果
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "analyze_business_relevance":
                result = json.loads(function_call.arguments)

                is_relevant = result['is_relevant']
                relevance_score = result['relevance_score']
                reasoning = result['reasoning']

                # 構建回應
                analysis = {
                    "is_relevant": is_relevant,
                    "relevance_score": relevance_score,
                    "reasoning": reasoning,
                    "should_record": is_relevant and relevance_score >= 0.7,
                    "openai_response": result
                }

                # 如果相關，加入建議意圖資訊
                if is_relevant and relevance_score >= 0.7:
                    analysis["suggested_intent"] = {
                        "name": result.get('suggested_name', ''),
                        "type": result.get('suggested_type', 'knowledge'),
                        "description": result.get('suggested_description', ''),
                        "keywords": result.get('suggested_keywords', [])
                    }
                else:
                    analysis["suggested_intent"] = None

                return analysis

        except Exception as e:
            print(f"❌ OpenAI 分析失敗: {e}")
            return {
                "is_relevant": False,
                "relevance_score": 0.0,
                "reasoning": f"分析失敗: {str(e)}",
                "should_record": False,
                "suggested_intent": None,
                "openai_response": None
            }

    def record_suggestion(
        self,
        question: str,
        analysis: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[int]:
        """
        記錄建議意圖到資料庫

        Args:
            question: 觸發的問題
            analysis: analyze_unclear_question 的分析結果
            user_id: 使用者 ID

        Returns:
            建議意圖的 ID，失敗則返回 None
        """

        if not analysis.get('should_record'):
            return None

        suggested = analysis.get('suggested_intent')
        if not suggested:
            return None

        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor()

            # 檢查是否已有相似的建議（相同名稱或問題）
            cursor.execute("""
                SELECT id, frequency
                FROM suggested_intents
                WHERE (suggested_name = %s OR trigger_question = %s)
                  AND status = 'pending'
                LIMIT 1
            """, (suggested['name'], question))

            existing = cursor.fetchone()

            if existing:
                # 更新現有建議的頻率和時間
                suggestion_id, frequency = existing
                cursor.execute("""
                    UPDATE suggested_intents
                    SET frequency = %s,
                        last_suggested_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (frequency + 1, suggestion_id))
                conn.commit()
                cursor.close()
                print(f"✅ 更新建議意圖頻率: {suggested['name']} (ID: {suggestion_id}, 頻率: {frequency + 1})")
                return suggestion_id

            else:
                # 插入新建議
                cursor.execute("""
                    INSERT INTO suggested_intents (
                        suggested_name,
                        suggested_type,
                        suggested_description,
                        suggested_keywords,
                        trigger_question,
                        user_id,
                        relevance_score,
                        reasoning,
                        openai_response,
                        status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                    RETURNING id
                """, (
                    suggested['name'],
                    suggested['type'],
                    suggested['description'],
                    suggested['keywords'],
                    question,
                    user_id,
                    analysis['relevance_score'],
                    analysis['reasoning'],
                    json.dumps(analysis.get('openai_response', {}))
                ))

                suggestion_id = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                print(f"✅ 記錄新建議意圖: {suggested['name']} (ID: {suggestion_id})")
                return suggestion_id

        except Exception as e:
            print(f"❌ 記錄建議失敗: {e}")
            conn.rollback()
            return None

        finally:
            conn.close()

    def get_suggestions(
        self,
        status: Optional[str] = None,
        order_by: str = 'frequency'  # frequency, latest, score
    ) -> List[Dict[str, Any]]:
        """
        取得建議意圖列表

        Args:
            status: 過濾狀態（pending/approved/rejected/merged）
            order_by: 排序方式

        Returns:
            建議意圖列表
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 構建查詢
            query = "SELECT * FROM suggested_intents WHERE 1=1"
            params = []

            if status:
                query += " AND status = %s"
                params.append(status)

            # 排序
            order_mapping = {
                'frequency': 'frequency DESC, last_suggested_at DESC',
                'latest': 'last_suggested_at DESC',
                'score': 'relevance_score DESC, frequency DESC'
            }
            query += f" ORDER BY {order_mapping.get(order_by, 'frequency DESC, last_suggested_at DESC')}"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def approve_suggestion(
        self,
        suggestion_id: int,
        reviewed_by: str = "admin",
        review_note: Optional[str] = None,
        create_intent: bool = True
    ) -> Optional[int]:
        """
        採納建議意圖

        Args:
            suggestion_id: 建議 ID
            reviewed_by: 審核人員
            review_note: 審核備註
            create_intent: 是否自動建立意圖

        Returns:
            建立的意圖 ID，失敗則返回 None
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 取得建議詳情
            cursor.execute("""
                SELECT suggested_name, suggested_type, suggested_description,
                       suggested_keywords
                FROM suggested_intents
                WHERE id = %s AND status = 'pending'
            """, (suggestion_id,))

            suggestion = cursor.fetchone()

            if not suggestion:
                cursor.close()
                print(f"❌ 找不到待審核的建議 ID: {suggestion_id}")
                return None

            intent_id = None

            if create_intent:
                # 建立新意圖
                cursor.execute("""
                    INSERT INTO intents (
                        name, type, description, keywords,
                        confidence_threshold, is_enabled, priority,
                        created_by
                    ) VALUES (%s, %s, %s, %s, 0.75, true, 0, %s)
                    RETURNING id
                """, (
                    suggestion['suggested_name'],
                    suggestion['suggested_type'],
                    suggestion['suggested_description'],
                    suggestion['suggested_keywords'],
                    reviewed_by
                ))

                intent_id = cursor.fetchone()['id']
                print(f"✅ 建立新意圖: {suggestion['suggested_name']} (ID: {intent_id})")

            # 更新建議狀態
            cursor.execute("""
                UPDATE suggested_intents
                SET status = 'approved',
                    reviewed_by = %s,
                    reviewed_at = CURRENT_TIMESTAMP,
                    review_note = %s,
                    approved_intent_id = %s
                WHERE id = %s
            """, (reviewed_by, review_note, intent_id, suggestion_id))

            conn.commit()
            cursor.close()
            print(f"✅ 採納建議 ID: {suggestion_id}")

            return intent_id

        except Exception as e:
            print(f"❌ 採納建議失敗: {e}")
            conn.rollback()
            return None

        finally:
            conn.close()

    def reject_suggestion(
        self,
        suggestion_id: int,
        reviewed_by: str = "admin",
        review_note: Optional[str] = None
    ) -> bool:
        """
        拒絕建議意圖

        Args:
            suggestion_id: 建議 ID
            reviewed_by: 審核人員
            review_note: 審核備註

        Returns:
            是否成功
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE suggested_intents
                SET status = 'rejected',
                    reviewed_by = %s,
                    reviewed_at = CURRENT_TIMESTAMP,
                    review_note = %s
                WHERE id = %s AND status = 'pending'
            """, (reviewed_by, review_note, suggestion_id))

            rows_affected = cursor.rowcount
            conn.commit()
            cursor.close()

            if rows_affected > 0:
                print(f"✅ 拒絕建議 ID: {suggestion_id}")
                return True
            else:
                print(f"❌ 找不到待審核的建議 ID: {suggestion_id}")
                return False

        except Exception as e:
            print(f"❌ 拒絕建議失敗: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def merge_suggestions(
        self,
        suggestion_ids: List[int],
        merged_name: str,
        merged_type: str,
        merged_description: str,
        merged_keywords: List[str],
        reviewed_by: str = "admin",
        create_intent: bool = True
    ) -> Optional[int]:
        """
        合併多個建議為單一意圖

        Args:
            suggestion_ids: 要合併的建議 ID 列表
            merged_name: 合併後的意圖名稱
            merged_type: 合併後的意圖類型
            merged_description: 合併後的描述
            merged_keywords: 合併後的關鍵字
            reviewed_by: 審核人員
            create_intent: 是否建立意圖

        Returns:
            建立的意圖 ID，失敗則返回 None
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor()

            intent_id = None

            if create_intent:
                # 建立合併後的意圖
                cursor.execute("""
                    INSERT INTO intents (
                        name, type, description, keywords,
                        confidence_threshold, is_enabled, priority,
                        created_by
                    ) VALUES (%s, %s, %s, %s, 0.75, true, 0, %s)
                    RETURNING id
                """, (
                    merged_name,
                    merged_type,
                    merged_description,
                    merged_keywords,
                    reviewed_by
                ))

                intent_id = cursor.fetchone()[0]
                print(f"✅ 建立合併意圖: {merged_name} (ID: {intent_id})")

            # 更新所有被合併的建議
            cursor.execute("""
                UPDATE suggested_intents
                SET status = 'merged',
                    reviewed_by = %s,
                    reviewed_at = CURRENT_TIMESTAMP,
                    review_note = '已合併為意圖: ' || %s,
                    approved_intent_id = %s
                WHERE id = ANY(%s) AND status = 'pending'
            """, (reviewed_by, merged_name, intent_id, suggestion_ids))

            conn.commit()
            cursor.close()
            print(f"✅ 合併 {len(suggestion_ids)} 個建議")

            return intent_id

        except Exception as e:
            print(f"❌ 合併建議失敗: {e}")
            conn.rollback()
            return None

        finally:
            conn.close()

    def get_suggestion_stats(self) -> Dict[str, Any]:
        """
        取得建議統計資訊

        Returns:
            統計資訊字典
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 總體統計
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status = 'merged' THEN 1 ELSE 0 END) as merged
                FROM suggested_intents
            """)

            overall = cursor.fetchone()

            # 高頻建議（待審核）
            cursor.execute("""
                SELECT id, suggested_name, suggested_type, frequency,
                       relevance_score, last_suggested_at
                FROM suggested_intents
                WHERE status = 'pending'
                ORDER BY frequency DESC, relevance_score DESC
                LIMIT 5
            """)

            top_suggestions = cursor.fetchall()

            cursor.close()

            return {
                "total": overall['total'],
                "pending": overall['pending'],
                "approved": overall['approved'],
                "rejected": overall['rejected'],
                "merged": overall['merged'],
                "top_suggestions": [dict(row) for row in top_suggestions]
            }

        finally:
            conn.close()


# 單例模式
_suggestion_engine_instance = None


def get_suggestion_engine() -> IntentSuggestionEngine:
    """取得 IntentSuggestionEngine 單例"""
    global _suggestion_engine_instance
    if _suggestion_engine_instance is None:
        _suggestion_engine_instance = IntentSuggestionEngine()
    return _suggestion_engine_instance
