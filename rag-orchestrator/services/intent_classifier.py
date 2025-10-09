"""
意圖分類服務
使用 OpenAI Function Calling 自動識別使用者問題的意圖類型
"""
import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from openai import OpenAI


class IntentClassifier:
    """意圖分類器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化意圖分類器

        Args:
            config_path: intents.yaml 配置文件路徑
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 載入配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "intents.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.intents = self.config['intents']
        self.default_config = self.config['default']
        self.classifier_config = self.config['classifier']

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
        # 構建 Function Calling 定義
        functions = [
            {
                "name": "classify_intent",
                "description": "分類使用者問題的意圖類型",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent_name": {
                            "type": "string",
                            "description": f"意圖名稱，選項: {', '.join([i['name'] for i in self.intents])}",
                            "enum": [i['name'] for i in self.intents] + ["unclear"]
                        },
                        "confidence": {
                            "type": "number",
                            "description": "信心度分數 (0-1)",
                            "minimum": 0,
                            "maximum": 1
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
                    "required": ["intent_name", "confidence", "keywords"]
                }
            }
        ]

        # 構建系統提示
        system_prompt = f"""你是一個專業的意圖分類助手，專門分類 JGB 包租代管客服系統的使用者問題。

可用的意圖類型：
{self._format_intents_for_prompt()}

請根據使用者問題，判斷最合適的意圖類型。
如果無法確定或信心度低於 0.7，請返回 "unclear"。
"""

        # 呼叫 OpenAI API
        response = self.client.chat.completions.create(
            model=self.classifier_config['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            functions=functions,
            function_call={"name": "classify_intent"},
            temperature=self.classifier_config['temperature'],
            max_tokens=self.classifier_config['max_tokens']
        )

        # 解析結果
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "classify_intent":
            import json
            result = json.loads(function_call.arguments)

            intent_name = result['intent_name']
            confidence = result['confidence']
            keywords = result['keywords']
            reasoning = result.get('reasoning', '')

            # 如果是 unclear，直接返回
            if intent_name == "unclear" or confidence < self.default_config['confidence_threshold']:
                return {
                    "intent_name": "unclear",
                    "intent_type": "unclear",
                    "confidence": confidence,
                    "keywords": keywords,
                    "reasoning": reasoning,
                    "requires_api": False
                }

            # 查找意圖配置
            intent_config = next((i for i in self.intents if i['name'] == intent_name), None)

            if not intent_config:
                return {
                    "intent_name": "unclear",
                    "intent_type": "unclear",
                    "confidence": 0.0,
                    "keywords": keywords,
                    "reasoning": "找不到匹配的意圖配置",
                    "requires_api": False
                }

            # 構建完整結果
            classification = {
                "intent_name": intent_name,
                "intent_type": intent_config['type'],
                "confidence": confidence,
                "sub_category": intent_config.get('description', ''),
                "keywords": keywords,
                "reasoning": reasoning,
                "requires_api": intent_config.get('api_required', False)
            }

            # 如果需要 API，加入 API 資訊
            if classification['requires_api']:
                classification['api_endpoint'] = intent_config.get('api_endpoint')
                classification['api_action'] = intent_config.get('api_action')

                # 處理混合類型
                if intent_config['type'] == 'hybrid':
                    classification['requires_both'] = intent_config.get('requires_both', {})

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
