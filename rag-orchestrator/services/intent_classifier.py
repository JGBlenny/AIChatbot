"""
意圖分類服務
使用 LLM Function Calling 自動識別使用者問題的意圖類型
"""
import os
import yaml
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from .db_utils import get_db_config
from .llm_provider import get_llm_provider, LLMProvider


class IntentClassifier:
    """意圖分類器"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        use_database: bool = True,
        llm_provider: Optional[LLMProvider] = None
    ):
        """
        初始化意圖分類器

        Args:
            config_path: intents.yaml 配置文件路徑（fallback 使用）
            use_database: 是否從資料庫載入意圖（預設 True）
            llm_provider: LLM Provider 實例（可選，默認使用全域 Provider）
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.use_database = use_database
        self.last_reload = None

        # YAML 配置路徑（fallback）
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "intents.yaml"
        self.config_path = config_path

        # 載入意圖配置
        if use_database:
            try:
                self.intents = self._load_intents_from_db_sync()
                print(f"✅ 從資料庫載入 {len(self.intents)} 個意圖")
            except Exception as e:
                print(f"⚠️ 無法從資料庫載入意圖: {type(e).__name__}: {e}")
                print("📂 Fallback 到 YAML 配置")
                self._load_from_yaml()
        else:
            self._load_from_yaml()

        # 預設配置（從 YAML 讀取或使用預設值）
        self.default_config = {
            "confidence_threshold": 0.70,
            "fallback_intent": "unclear",
            "max_intents": 3
        }
        self.classifier_config = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 500
        }

        # 如果 YAML 存在，讀取預設配置
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    if 'default' in yaml_config:
                        self.default_config.update(yaml_config['default'])
                    if 'classifier' in yaml_config:
                        self.classifier_config.update(yaml_config['classifier'])
            except:
                pass

        # 從環境變數覆蓋配置（優先級最高）
        if os.getenv("INTENT_CLASSIFIER_MODEL"):
            self.classifier_config["model"] = os.getenv("INTENT_CLASSIFIER_MODEL")
            print(f"✅ 使用環境變數指定的模型: {self.classifier_config['model']}")

        if os.getenv("INTENT_CLASSIFIER_TEMPERATURE"):
            self.classifier_config["temperature"] = float(os.getenv("INTENT_CLASSIFIER_TEMPERATURE"))

        if os.getenv("INTENT_CLASSIFIER_MAX_TOKENS"):
            self.classifier_config["max_tokens"] = int(os.getenv("INTENT_CLASSIFIER_MAX_TOKENS"))

    def _load_from_yaml(self):
        """從 YAML 載入意圖配置（fallback）"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.intents = config['intents']
        self.default_config = config['default']
        self.classifier_config = config['classifier']
        print(f"✅ 從 YAML 載入 {len(self.intents)} 個意圖")

    def _load_intents_from_db_sync(self) -> List[Dict]:
        """從資料庫載入啟用的意圖（同步版本）"""
        # 建立資料庫連接（使用共用的配置）
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    name,
                    type,
                    description,
                    keywords,
                    confidence_threshold,
                    api_required,
                    api_endpoint,
                    api_action
                FROM intents
                WHERE is_enabled = true
                ORDER BY name
            """)

            rows = cursor.fetchall()

            intents = []
            for row in rows:
                intent = {
                    'name': row['name'],
                    'type': row['type'],
                    'description': row['description'],
                    'keywords': list(row['keywords']) if row['keywords'] else [],
                    'confidence_threshold': float(row['confidence_threshold']),
                    'api_required': row['api_required']
                }

                if row['api_endpoint']:
                    intent['api_endpoint'] = row['api_endpoint']
                if row['api_action']:
                    intent['api_action'] = row['api_action']

                intents.append(intent)

            cursor.close()
            self.last_reload = datetime.now()
            return intents

        finally:
            conn.close()

    def reload_intents(self):
        """重新載入意圖配置（支援動態更新）"""
        if self.use_database:
            try:
                self.intents = self._load_intents_from_db_sync()
                print(f"✅ 重新載入 {len(self.intents)} 個意圖")
                return True
            except Exception as e:
                print(f"❌ 重新載入失敗: {e}")
                return False
        else:
            self._load_from_yaml()
            return True

    def increment_usage_count(self, intent_name: str):
        """增加意圖使用次數"""
        if not self.use_database:
            return

        try:
            # 使用共用的資料庫配置
            db_config = get_db_config()
            conn = psycopg2.connect(**db_config)

            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE intents
                    SET usage_count = usage_count + 1,
                        last_used_at = CURRENT_TIMESTAMP
                    WHERE name = %s
                """, (intent_name,))
                conn.commit()
                cursor.close()
            finally:
                conn.close()
        except Exception as e:
            # 忽略追蹤錯誤，不影響主流程
            pass

    def classify(self, question: str) -> Dict:
        """
        分類使用者問題的意圖

        Args:
            question: 使用者問題

        Returns:
            分類結果，包含:
            - intent_name: 意圖名稱
            - intent_type: 意圖類型 (knowledge/data_query/action/hybrid)
            - confidence: 信心度 (0-1)
            - sub_category: 子類別
            - keywords: 提取的關鍵字
            - requires_api: 是否需要呼叫 API
            - api_endpoint: API 端點 (如果需要)
            - api_action: API 動作 (如果需要)
        """
        # 構建 Function Calling 定義（支援多 Intent + 獨立信心度）
        functions = [
            {
                "name": "classify_intent",
                "description": "分類使用者問題的意圖類型，可返回多個相關意圖，每個意圖都有獨立的信心度評分",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_intent": {
                            "type": "object",
                            "description": "主要意圖及其信心度",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": f"主要意圖名稱，選項: {', '.join([i['name'] for i in self.intents])}",
                                    "enum": [i['name'] for i in self.intents] + ["unclear"]
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "主要意圖的信心度分數 (0-1)，表示你有多確定這是正確的分類",
                                    "minimum": 0,
                                    "maximum": 1
                                }
                            },
                            "required": ["name", "confidence"]
                        },
                        "secondary_intents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "enum": [i['name'] for i in self.intents]
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "此次要意圖的信心度 (0-1)，通常應低於主要意圖",
                                        "minimum": 0,
                                        "maximum": 1
                                    }
                                },
                                "required": ["name", "confidence"]
                            },
                            "description": "次要相關意圖及其信心度（如果問題涉及多個類別）",
                            "maxItems": 2
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "從問題中提取的關鍵字"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "分類理由"
                        }
                    },
                    "required": ["primary_intent", "keywords"]
                }
            }
        ]

        # 構建系統提示
        system_prompt = f"""你是一個專業的意圖分類助手，專門分類 JGB 包租代管客服系統的使用者問題。

可用的意圖類型：
{self._format_intents_for_prompt()}

**分類策略：**
1. 識別主要意圖（primary_intent）：問題的核心目的
   - 返回意圖名稱和信心度（0-1）
   - 信心度表示：你有多確定這是正確的分類

2. 識別次要意圖（secondary_intents）：問題可能涉及的其他相關類別
   - 例如「租金如何計算？」可能同時涉及「合約規定」和「帳務查詢」
   - 例如「退租押金如何退還？」可能同時涉及「退租流程」和「帳務查詢」
   - **每個次要意圖都需要獨立的信心度評分**
   - 次要意圖的信心度通常應低於主要意圖

3. 信心度評分標準：
   - 0.9-1.0：非常確定，問題明確屬於此意圖
   - 0.7-0.9：較為確定，問題很可能屬於此意圖
   - 0.5-0.7：不太確定，問題可能屬於此意圖
   - < 0.5：不確定，可能不屬於此意圖

4. 如果問題明確只屬於一個類別，可不填 secondary_intents

5. 如果無法確定或主要意圖信心度低於 0.7，primary_intent.name 返回 "unclear"

**特殊處理規則（重要）：**
6. 對於列表式查詢（如「A、B、C」或「A B C」格式）：
   - 仔細分析每個列表項的業務領域
   - 如果列表項跨越多個意圖範疇，應識別為多意圖
   - 寧可多返回一個次要意圖（信心度 0.45-0.65），也不要遺漏潛在相關意圖

7. 關鍵詞意圖對應參考（優先考慮多意圖）：
   - 「租金」「押金」「繳費」「付款」「金額」 → 可能涉及「帳務查詢」
   - 「租約」「合約」「租期」「條款」「規定」 → 可能涉及「合約規定」
   - 「退租」「解約」「搬遷」「退還」 → 可能涉及「退租流程」
   - 當問題包含 2 個以上上述關鍵詞類別時，通常應返回多個意圖

8. 示例分析：
   - 「租約條款 租金、押金、租期」應識別為：
     主意圖: 合約規定 (0.85) - 因為「條款」「租約」
     次要意圖: 帳務查詢 (0.55) - 因為「租金」「押金」涉及金額查詢

   - 「如何查詢租金和押金？」應識別為：
     主意圖: 帳務查詢 (0.85) - 因為動詞「查詢」
     次要意圖: 合約規定 (0.50) - 因為可能需要了解計算規則

請仔細分析問題的語義，為每個意圖提供精確的信心度評分。
"""

        # 呼叫 LLM API
        llm_result = self.llm_provider.chat_completion(
            model=self.classifier_config['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=self.classifier_config['temperature'],
            max_tokens=self.classifier_config['max_tokens'],
            functions=functions,
            function_call={"name": "classify_intent"}
        )

        # 從 raw_response 取得原始回應(用於 function calling)
        response = llm_result['raw_response']

        # 解析結果
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "classify_intent":
            import json
            result = json.loads(function_call.arguments)

            # 解析主要意圖（新格式：對象包含 name 和 confidence）
            primary_intent_obj = result['primary_intent']
            primary_intent_name = primary_intent_obj['name']
            primary_confidence = primary_intent_obj['confidence']

            # 解析次要意圖（新格式：對象數組，每個包含 name 和 confidence）
            secondary_intents_objs = result.get('secondary_intents', [])

            keywords = result['keywords']
            reasoning = result.get('reasoning', '')

            # 如果 AI 返回 unclear，直接返回
            if primary_intent_name == "unclear":
                print(f"⚠️ AI classified as unclear: {question[:50]}...")
                return {
                    "intent_name": "unclear",
                    "intent_type": "unclear",
                    "confidence": primary_confidence,
                    "keywords": keywords,
                    "reasoning": reasoning,
                    "requires_api": False,
                    "all_intents": [],
                    "all_intents_with_confidence": [],
                    "secondary_intents": [],
                    "intent_ids": []
                }

            # 查找主要意圖配置
            intent_config = next((i for i in self.intents if i['name'] == primary_intent_name), None)

            if not intent_config:
                print(f"⚠️ Intent config not found: {primary_intent_name}")
                return {
                    "intent_name": "unclear",
                    "intent_type": "unclear",
                    "confidence": 0.0,
                    "keywords": keywords,
                    "reasoning": "找不到匹配的意圖配置",
                    "requires_api": False,
                    "all_intents": [],
                    "all_intents_with_confidence": [],
                    "secondary_intents": [],
                    "intent_ids": []
                }

            # 【方案 B 改進 1】：使用意圖獨立閾值檢查主要意圖
            primary_threshold = intent_config.get('confidence_threshold', self.default_config['confidence_threshold'])
            primary_passed = primary_confidence >= primary_threshold

            if not primary_passed:
                print(f"⚠️ Primary intent failed threshold: {primary_intent_name} "
                      f"(confidence={primary_confidence:.3f} < threshold={primary_threshold:.3f})")

            # 【方案 B 改進 2+3】：過濾次要意圖 + 嘗試降級機制
            valid_secondary_intents = []
            for sec_intent in secondary_intents_objs:
                sec_config = next((i for i in self.intents if i['name'] == sec_intent['name']), None)
                if not sec_config:
                    continue

                sec_threshold = sec_config.get('confidence_threshold', self.default_config['confidence_threshold'])
                sec_confidence = sec_intent['confidence']

                # 只保留通過閾值的次要意圖
                if sec_confidence >= sec_threshold:
                    valid_secondary_intents.append({
                        'name': sec_intent['name'],
                        'confidence': sec_confidence,
                        'threshold': sec_threshold,
                        'config': sec_config
                    })
                else:
                    print(f"   ❌ Filtered secondary intent: {sec_intent['name']} "
                          f"(confidence={sec_confidence:.3f} < threshold={sec_threshold:.3f})")

            # 【方案 B 改進 3】：次要意圖降級機制
            # 如果主意圖未通過閾值，但有次要意圖通過，則將最高分的次要意圖升級為主意圖
            if not primary_passed and valid_secondary_intents:
                # 按信心度排序，取最高分
                best_secondary = max(valid_secondary_intents, key=lambda x: x['confidence'])
                print(f"✅ Promoting secondary to primary: {best_secondary['name']} "
                      f"(confidence={best_secondary['confidence']:.3f} >= threshold={best_secondary['threshold']:.3f})")

                # 將原主意圖降為次要（如果它還有一定信心度）
                original_primary_valid = primary_confidence >= (primary_threshold * 0.8)  # 放寬 20% 作為次要意圖
                if original_primary_valid:
                    print(f"   → Demoting original primary to secondary: {primary_intent_name} "
                          f"(confidence={primary_confidence:.3f})")

                # 重新分配
                promoted_intent_config = best_secondary['config']
                valid_secondary_intents.remove(best_secondary)

                # 如果原主意圖還有效，加回次要意圖列表
                if original_primary_valid:
                    valid_secondary_intents.insert(0, {
                        'name': primary_intent_name,
                        'confidence': primary_confidence,
                        'threshold': primary_threshold,
                        'config': intent_config
                    })

                # 更新主意圖
                primary_intent_name = best_secondary['name']
                primary_confidence = best_secondary['confidence']
                intent_config = promoted_intent_config

            # 如果主意圖仍未通過閾值且沒有有效次要意圖，返回 unclear
            elif not primary_passed:
                print(f"❌ No valid intents found → unclear")
                return {
                    "intent_name": "unclear",
                    "intent_type": "unclear",
                    "confidence": primary_confidence,
                    "keywords": keywords,
                    "reasoning": f"主要意圖信心度不足 ({primary_confidence:.3f} < {primary_threshold:.3f})",
                    "requires_api": False,
                    "all_intents": [],
                    "all_intents_with_confidence": [],
                    "secondary_intents": [],
                    "intent_ids": []
                }

            # 收集所有相關意圖（主要 + 已過濾的次要）
            valid_secondary_names = [s['name'] for s in valid_secondary_intents]
            all_intent_names = [primary_intent_name] + valid_secondary_names
            all_intent_ids = []

            # 構建完整的意圖信心度列表（包含主意圖和副意圖）
            all_intents_with_confidence = [
                {
                    "name": primary_intent_name,
                    "confidence": primary_confidence,
                    "type": "primary"
                }
            ]

            # 添加已過濾的次要意圖及其信心度
            for sec_intent in valid_secondary_intents:
                all_intents_with_confidence.append({
                    "name": sec_intent['name'],
                    "confidence": sec_intent['confidence'],
                    "type": "secondary"
                })

            # 從資料庫查詢所有意圖的 ID（保持順序）
            if self.use_database:
                try:
                    # 使用共用的資料庫配置
                    db_config = get_db_config()
                    conn = psycopg2.connect(**db_config)
                    cursor = conn.cursor()
                    # 逐個查詢以保持順序
                    for intent_name in all_intent_names:
                        cursor.execute("""
                            SELECT id FROM intents
                            WHERE name = %s AND is_enabled = true
                        """, (intent_name,))
                        db_result = cursor.fetchone()
                        if db_result:
                            all_intent_ids.append(db_result[0])
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"⚠️ 無法查詢 intent IDs: {e}")

            # 構建完整結果
            classification = {
                "intent_name": primary_intent_name,
                "intent_type": intent_config['type'],
                "confidence": primary_confidence,
                "sub_category": intent_config.get('description', ''),
                "keywords": keywords,
                "reasoning": reasoning,
                "requires_api": intent_config.get('api_required', False),
                # 多 Intent 支援（向後兼容）- 現在只包含已過濾的次要意圖
                "all_intents": all_intent_names,
                "secondary_intents": valid_secondary_names,
                "intent_ids": all_intent_ids,
                # 新增：完整的意圖信心度資訊
                "all_intents_with_confidence": all_intents_with_confidence
            }

            # 如果需要 API，加入 API 資訊
            if classification['requires_api']:
                classification['api_endpoint'] = intent_config.get('api_endpoint')
                classification['api_action'] = intent_config.get('api_action')

                # 處理混合類型
                if intent_config['type'] == 'hybrid':
                    classification['requires_both'] = intent_config.get('requires_both', {})

            # 增加使用次數
            if self.use_database and primary_intent_name != "unclear":
                self.increment_usage_count(primary_intent_name)

            return classification

        # 如果 API 呼叫失敗
        return {
            "intent_name": "unclear",
            "intent_type": "unclear",
            "confidence": 0.0,
            "keywords": [],
            "reasoning": "API 呼叫失敗",
            "requires_api": False
        }

    def _format_intents_for_prompt(self) -> str:
        """格式化意圖列表為 prompt"""
        lines = []
        for intent in self.intents:
            keywords_str = ", ".join(intent['keywords'][:5])  # 只顯示前 5 個關鍵字
            lines.append(f"- {intent['name']} ({intent['type']}): {intent['description']}")
            lines.append(f"  關鍵字: {keywords_str}")
        return "\n".join(lines)

    def get_intent_config(self, intent_name: str) -> Optional[Dict]:
        """
        取得特定意圖的配置

        Args:
            intent_name: 意圖名稱

        Returns:
            意圖配置字典，如果找不到則返回 None
        """
        return next((i for i in self.intents if i['name'] == intent_name), None)

    def list_intents(self) -> List[Dict]:
        """
        列出所有可用的意圖

        Returns:
            意圖列表
        """
        return self.intents


# 使用範例
if __name__ == "__main__":
    # 測試意圖分類
    classifier = IntentClassifier()

    test_questions = [
        "我想退租，需要怎麼辦理？",
        "我的租約什麼時候到期？",
        "門鎖壞了，要怎麼報修？",
        "這個月的帳單多少錢？",
        "IOT 門鎖要怎麼使用？"
    ]

    for question in test_questions:
        print(f"\n問題: {question}")
        result = classifier.classify(question)
        print(f"意圖: {result['intent_name']} ({result['intent_type']})")
        print(f"信心度: {result['confidence']:.2f}")
        print(f"關鍵字: {', '.join(result['keywords'])}")
        if result['requires_api']:
            print(f"API: {result.get('api_endpoint')}.{result.get('api_action')}")
