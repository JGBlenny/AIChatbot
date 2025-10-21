"""
LLM 答案優化服務
使用 GPT 模型優化 RAG 檢索結果，生成更自然、更精準的答案
Phase 1 擴展：支援業者參數動態注入
"""
import os
import re
from typing import List, Dict, Optional
from openai import OpenAI
import time


class LLMAnswerOptimizer:
    """LLM 答案優化器"""

    def __init__(self, config: Dict = None):
        """
        初始化 LLM 答案優化器

        Args:
            config: 配置字典
        """
        # 延遲初始化：只有在需要時才檢查 API key
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

        # 從環境變數讀取模型配置（用於降低測試成本）
        default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # 預設配置
        default_config = {
            "model": default_model,
            "temperature": 0.7,
            "max_tokens": 800,
            "enable_optimization": True,
            "optimize_for_confidence": ["high", "medium"],  # 只優化高/中信心度
            "fallback_on_error": True,  # 錯誤時使用原始答案
            # Phase 2 擴展：答案合成功能
            "enable_synthesis": False,  # 是否啟用答案合成（預設關閉，需測試後啟用）
            "synthesis_min_results": 2,  # 最少需要幾個結果才考慮合成
            "synthesis_max_results": 3,  # 最多合成幾個答案
            "synthesis_threshold": 0.7   # 當最高相似度低於此值時，考慮合成
        }

        # 合併用戶配置與預設配置
        if config:
            self.config = {**default_config, **config}
        else:
            self.config = default_config

    def optimize_answer(
        self,
        question: str,
        search_results: List[Dict],
        confidence_level: str,
        intent_info: Dict,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None,
        enable_synthesis_override: Optional[bool] = None
    ) -> Dict:
        """
        優化答案

        Args:
            question: 使用者問題
            search_results: RAG 檢索結果列表
            confidence_level: 信心度等級
            intent_info: 意圖資訊
            vendor_params: 業者參數（Phase 1 擴展）
            vendor_name: 業者名稱（Phase 1 擴展）
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等，Phase 1 SOP 擴展）
            enable_synthesis_override: 覆蓋答案合成配置（None=使用配置，True=強制啟用，False=強制禁用）

        Returns:
            優化結果字典，包含:
            - optimized_answer: 優化後的答案
            - original_answer: 原始答案
            - optimization_applied: 是否使用了優化
            - synthesis_applied: 是否使用了答案合成
            - tokens_used: 使用的 token 數
            - processing_time_ms: 處理時間
        """
        start_time = time.time()

        # 1. 檢查是否需要優化
        if not self._should_optimize(confidence_level, search_results):
            return self._create_fallback_response(search_results, start_time)

        # 2. 準備原始答案
        original_answer = self._create_original_answer(search_results)

        # 3. 判斷是否需要答案合成（Phase 2 擴展）
        # 支援動態覆蓋：如果傳入 enable_synthesis_override，則使用該值
        should_synthesize = self._should_synthesize(
            question,
            search_results,
            enable_synthesis_override
        )

        # 4. 嘗試 LLM 優化（Phase 1 擴展：加入業者參數注入；Phase 2 擴展：答案合成）
        try:
            if should_synthesize:
                # 使用答案合成模式
                optimized_answer, tokens_used = self.synthesize_answer(
                    question=question,
                    search_results=search_results,
                    intent_info=intent_info,
                    vendor_params=vendor_params,
                    vendor_name=vendor_name,
                    vendor_info=vendor_info
                )
                synthesis_applied = True
            else:
                # 使用傳統優化模式
                optimized_answer, tokens_used = self._call_llm(
                    question=question,
                    search_results=search_results,
                    intent_info=intent_info,
                    vendor_params=vendor_params,
                    vendor_name=vendor_name,
                    vendor_info=vendor_info
                )
                synthesis_applied = False

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "optimized_answer": optimized_answer,
                "original_answer": original_answer,
                "optimization_applied": True,
                "synthesis_applied": synthesis_applied,  # 新增：標記是否使用了合成
                "tokens_used": tokens_used,
                "processing_time_ms": processing_time,
                "model": self.config["model"]
            }

        except Exception as e:
            print(f"❌ LLM 優化失敗: {e}")

            if self.config["fallback_on_error"]:
                # 錯誤時使用原始答案
                processing_time = int((time.time() - start_time) * 1000)
                return {
                    "optimized_answer": original_answer,
                    "original_answer": original_answer,
                    "optimization_applied": False,
                    "synthesis_applied": False,
                    "tokens_used": 0,
                    "processing_time_ms": processing_time,
                    "error": str(e)
                }
            else:
                raise

    def _should_optimize(self, confidence_level: str, search_results: List[Dict]) -> bool:
        """判斷是否應該優化"""
        if not self.config["enable_optimization"]:
            return False

        if not search_results:
            return False

        if confidence_level not in self.config["optimize_for_confidence"]:
            return False

        return True

    def _should_synthesize(
        self,
        question: str,
        search_results: List[Dict],
        enable_synthesis_override: Optional[bool] = None
    ) -> bool:
        """
        判斷是否需要答案合成

        觸發條件（全部滿足）：
        1. 啟用合成功能
        2. 至少有指定數量的檢索結果
        3. 問題包含複合需求關鍵字（這類問題通常需要多方面資訊）
        4. 沒有單一高分答案（最高相似度 < 閾值）

        Args:
            question: 用戶問題
            search_results: 檢索結果列表
            enable_synthesis_override: 覆蓋配置（None=使用配置，True=強制啟用，False=強制禁用）

        Returns:
            是否應該合成答案
        """
        # 1. 功能開關（支援動態覆蓋）
        if enable_synthesis_override is not None:
            # 如果傳入覆蓋值，使用覆蓋值
            if not enable_synthesis_override:
                return False
        else:
            # 否則使用配置
            if not self.config.get("enable_synthesis", False):
                return False

        # 2. 結果數量
        min_results = self.config.get("synthesis_min_results", 2)
        if len(search_results) < min_results:
            return False

        # 3. 複合問題關鍵字（這類問題通常需要多方面資訊）
        complex_keywords = ["如何", "怎麼", "流程", "步驟", "需要", "什麼時候", "注意", "準備", "辦理"]
        has_complex_pattern = any(kw in question for kw in complex_keywords)

        # 4. 沒有單一高分答案（表示可能需要組合多個答案）
        threshold = self.config.get("synthesis_threshold", 0.7)
        max_similarity = max(r['similarity'] for r in search_results[:min_results])
        no_perfect_match = max_similarity < threshold

        # 記錄判斷結果（用於調試）
        if has_complex_pattern and no_perfect_match:
            print(f"🔄 答案合成觸發：問題類型={has_complex_pattern}, 最高相似度={max_similarity:.3f} < {threshold}")

        return has_complex_pattern and no_perfect_match

    def _create_original_answer(self, search_results: List[Dict]) -> str:
        """建立原始答案（未優化）"""
        if not search_results:
            return ""

        best_result = search_results[0]
        return f"{best_result['title']}\n\n{best_result['content']}"

    def _create_fallback_response(self, search_results: List[Dict], start_time: float) -> Dict:
        """建立備用回應（不優化）"""
        original_answer = self._create_original_answer(search_results)
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "optimized_answer": original_answer,
            "original_answer": original_answer,
            "optimization_applied": False,
            "tokens_used": 0,
            "processing_time_ms": processing_time
        }

    def inject_vendor_params(
        self,
        content: str,
        vendor_params: Dict,
        vendor_name: str
    ) -> str:
        """
        使用 LLM 根據業者參數動態調整知識內容
        不使用模板變數，而是智能偵測並替換參數

        Args:
            content: 原始知識內容（可能包含通用數值）
            vendor_params: 業者參數字典
            vendor_name: 業者名稱

        Returns:
            調整後的內容
        """
        if not vendor_params:
            return content

        # 建立參數說明
        params_description = "\n".join([
            f"- {key}: {value}" for key, value in vendor_params.items()
        ])

        system_prompt = f"""你是一個專業的內容調整助理。你的任務是根據業者的具體參數，調整知識庫內容中的數值和資訊。

業者名稱：{vendor_name}
業者參數：
{params_description}

調整規則：
1. 仔細識別內容中提到的參數相關資訊（如日期、金額、時間等）
2. 如果內容中的數值與業者參數不符，請替換為業者參數中的值
3. 保持內容的語氣、結構和格式不變
4. 只調整數值，不要改變其他內容
5. 如果內容已經符合業者參數，則不需要修改
6. 業者名稱統一使用 "{vendor_name}"

重要：只輸出調整後的內容，不要加上任何說明或註解。"""

        user_prompt = f"""請根據業者參數調整以下內容：

{content}"""

        try:
            if not self.client:
                raise Exception("OpenAI client not initialized (missing API key)")

            response = self.client.chat.completions.create(
                model=self.config["model"],
                temperature=0.3,  # 使用較低溫度確保準確性
                max_tokens=self.config["max_tokens"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            adjusted_content = response.choices[0].message.content.strip()
            return adjusted_content

        except Exception as e:
            print(f"⚠️  參數注入失敗，使用原始內容: {e}")
            return content

    def synthesize_answer(
        self,
        question: str,
        search_results: List[Dict],
        intent_info: Dict,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> tuple[str, int]:
        """
        合成多個答案為一個完整答案（Phase 2 擴展功能）

        當檢索到的多個答案各有側重時，使用 LLM 將它們合成為一個完整、結構化的答案。
        這可以提升答案的完整性，特別適用於複雜問題。

        Args:
            question: 用戶問題
            search_results: 多個檢索結果
            intent_info: 意圖資訊
            vendor_params: 業者參數（用於動態注入）
            vendor_name: 業者名稱
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等）

        Returns:
            (合成後的答案, 使用的 tokens 數)
        """
        # 準備多個答案的上下文（先進行參數注入）
        max_results = self.config.get("synthesis_max_results", 3)
        answers_to_synthesize = []

        for i, result in enumerate(search_results[:max_results], 1):
            content = result['content']

            # 如果有業者參數，先進行智能參數注入
            if vendor_params and vendor_name:
                content = self.inject_vendor_params(content, vendor_params, vendor_name)

            answers_to_synthesize.append({
                "index": i,
                "title": result['title'],
                "category": result.get('category', 'N/A'),
                "content": content,
                "similarity": result['similarity']
            })

        # 格式化答案列表
        formatted_answers = "\n\n".join([
            f"【答案 {ans['index']}】\n"
            f"標題：{ans['title']}\n"
            f"分類：{ans['category']}\n"
            f"相似度：{ans['similarity']:.2f}\n"
            f"內容：\n{ans['content']}"
            for ans in answers_to_synthesize
        ])

        # 建立合成 Prompt
        system_prompt = self._create_synthesis_system_prompt(intent_info, vendor_name, vendor_info)
        user_prompt = self._create_synthesis_user_prompt(question, formatted_answers, intent_info)

        # 檢查 API key
        if not self.client:
            raise Exception("OpenAI client not initialized (missing API key)")

        # 呼叫 OpenAI API 進行合成
        response = self.client.chat.completions.create(
            model=self.config["model"],
            temperature=0.5,  # 稍低溫度以確保準確性和結構
            max_tokens=self.config["max_tokens"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        synthesized_answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        print(f"✨ 答案合成完成：使用了 {len(answers_to_synthesize)} 個來源，tokens: {tokens_used}")

        return synthesized_answer, tokens_used

    def _create_synthesis_system_prompt(
        self,
        intent_info: Dict,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> str:
        """建立答案合成的系統提示詞"""
        intent_type = intent_info.get('intent_type', 'knowledge')

        base_prompt = """你是一個專業的知識整合助理。你的任務是將多個相關但各有側重的答案，合成為一個完整、準確、結構化的回覆。

合成要求：
1. **完整性**：涵蓋所有重要資訊，不遺漏任何關鍵步驟或細節
2. **準確性**：資訊必須來自提供的答案，不要編造或推測
3. **結構化**：使用清晰的標題、列表、步驟編號，使答案易於閱讀
4. **去重**：如果多個答案提到相同資訊，只保留一次，避免重複
5. **優先級**：優先使用相似度較高的答案內容
6. **語氣**：保持專業、友善、易懂的繁體中文表達
7. **Markdown**：適當使用 Markdown 格式（## 標題、- 列表、**粗體**）"""

        rule_number = 8

        # 如果有業者名稱，加入業者資訊
        if vendor_name:
            base_prompt += f"\n{rule_number}. **業者身份**：你代表 {vendor_name}，請使用該業者的資訊回答"
            rule_number += 1

        # 根據業種類型調整語氣（Phase 1 SOP 擴展）
        if vendor_info:
            business_type = vendor_info.get('business_type', 'property_management')
            if business_type == 'full_service':
                base_prompt += f"\n{rule_number}. **業種特性**：{vendor_name} 是包租型業者，提供全方位服務。語氣應主動告知、確認、承諾。使用「我們會」、「公司將」等主動語句"
                rule_number += 1
            elif business_type == 'property_management':
                base_prompt += f"\n{rule_number}. **業種特性**：{vendor_name} 是代管型業者，協助租客與房東溝通。語氣應協助引導、建議聯繫。使用「請您」、「建議」、「可協助」等引導語句"
                rule_number += 1

        # 根據意圖類型調整提示
        if intent_type == "knowledge":
            base_prompt += f"\n{rule_number}. **知識類型**：這是知識查詢，請提供完整的說明、步驟和注意事項"
        elif intent_type == "data_query":
            base_prompt += f"\n{rule_number}. **資料查詢**：如需查詢具體資料，請說明如何查詢和所需資料"
        elif intent_type == "action":
            base_prompt += f"\n{rule_number}. **操作指引**：請提供具體、可執行的操作步驟"

        base_prompt += "\n\n重要：只輸出合成後的完整答案，不要加上「根據以上資訊」等元資訊。"

        return base_prompt

    def _create_synthesis_user_prompt(self, question: str, formatted_answers: str, intent_info: Dict) -> str:
        """建立答案合成的使用者提示詞"""
        keywords = intent_info.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "無"

        prompt = f"""使用者問題：{question}

意圖類型：{intent_info.get('intent_name', '未知')}
關鍵字：{keywords_str}

以下是多個相關答案，請將它們合成為一個完整的回覆：

{formatted_answers}

請綜合以上答案，生成一個完整、準確、結構化的回覆。確保：
- 涵蓋所有重要資訊
- 使用清晰的結構（標題、列表、步驟）
- 避免重複
- 保持準確性"""

        return prompt

    def _call_llm(
        self,
        question: str,
        search_results: List[Dict],
        intent_info: Dict,
        vendor_params: Optional[Dict] = None,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> tuple[str, int]:
        """
        呼叫 LLM 優化答案

        Args:
            question: 使用者問題
            search_results: 檢索結果
            intent_info: 意圖資訊
            vendor_params: 業者參數（用於動態注入）
            vendor_name: 業者名稱
            vendor_info: 完整業者資訊（包含 business_type, cashflow_model 等）

        Returns:
            (優化後的答案, 使用的 tokens 數)
        """
        # 1. 準備檢索結果上下文（先進行參數注入）
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):  # 最多使用前 3 個結果
            content = result['content']

            # Phase 1 擴展：如果有業者參數，先進行智能參數注入
            if vendor_params and vendor_name:
                content = self.inject_vendor_params(content, vendor_params, vendor_name)

            context_parts.append(
                f"【參考資料 {i}】\n"
                f"標題：{result['title']}\n"
                f"分類：{result.get('category', 'N/A')}\n"
                f"內容：{content}\n"
                f"相似度：{result['similarity']:.2f}"
            )

        context = "\n\n".join(context_parts)

        # 2. 建立優化 Prompt
        system_prompt = self._create_system_prompt(intent_info, vendor_name, vendor_info)
        user_prompt = self._create_user_prompt(question, context, intent_info)

        # 檢查 API key
        if not self.client:
            raise Exception("OpenAI client not initialized (missing API key)")

        # 3. 呼叫 OpenAI API
        response = self.client.chat.completions.create(
            model=self.config["model"],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        optimized_answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return optimized_answer, tokens_used

    def _create_system_prompt(
        self,
        intent_info: Dict,
        vendor_name: Optional[str] = None,
        vendor_info: Optional[Dict] = None
    ) -> str:
        """建立系統提示詞"""
        intent_type = intent_info.get('intent_type', 'knowledge')

        base_prompt = """你是一個專業、友善的客服助理。你的任務是根據知識庫的資訊，用自然、易懂的語言回答使用者的問題。

回答要求：
1. 直接回答問題，不要重複問題內容
2. 使用繁體中文，語氣親切專業
3. 資訊必須來自提供的參考資料，不要編造
4. 如有步驟或流程，請清楚列出
5. 適當使用 Markdown 格式（標題、列表）使答案更易讀
6. 保持簡潔，避免冗長
7. 如果參考資料不足以回答，請誠實說明"""

        rule_number = 8

        # 如果有業者名稱，加入業者資訊
        if vendor_name:
            base_prompt += f"\n{rule_number}. 你代表 {vendor_name}，請使用該業者的資訊回答"
            rule_number += 1

        # 根據業種類型調整語氣（Phase 1 SOP 擴展）
        if vendor_info:
            business_type = vendor_info.get('business_type', 'property_management')
            if business_type == 'full_service':
                base_prompt += f"\n{rule_number}. 【業種特性】{vendor_name} 是包租型業者，你們提供全方位服務。語氣應：主動告知、確認、承諾。使用「我們會」、「公司將」等主動語句"
                rule_number += 1
            elif business_type == 'property_management':
                base_prompt += f"\n{rule_number}. 【業種特性】{vendor_name} 是代管型業者，你們協助租客與房東溝通。語氣應：協助引導、建議聯繫。使用「請您」、「建議」、「可協助」等引導語句"
                rule_number += 1

        # 根據意圖類型調整提示
        if intent_type == "knowledge":
            base_prompt += f"\n{rule_number}. 這是知識查詢問題，請提供清楚的說明和步驟"
        elif intent_type == "data_query":
            base_prompt += f"\n{rule_number}. 這是資料查詢問題，如需查詢具體資料，請說明如何查詢"
        elif intent_type == "action":
            base_prompt += f"\n{rule_number}. 這是操作執行問題，請說明具體操作步驟"

        return base_prompt

    def _create_user_prompt(self, question: str, context: str, intent_info: Dict) -> str:
        """建立使用者提示詞"""
        keywords = intent_info.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "無"

        prompt = f"""使用者問題：{question}

意圖類型：{intent_info.get('intent_name', '未知')}
關鍵字：{keywords_str}

參考資料：
{context}

請根據以上參考資料，用自然、友善的語氣回答使用者的問題。"""

        return prompt

    def get_optimization_stats(self, optimizations: List[Dict]) -> Dict:
        """
        計算優化統計資訊

        Args:
            optimizations: 優化結果列表

        Returns:
            統計資訊字典
        """
        if not optimizations:
            return {
                "total_optimizations": 0,
                "successful_optimizations": 0,
                "total_tokens_used": 0,
                "avg_tokens_per_optimization": 0,
                "avg_processing_time_ms": 0
            }

        total = len(optimizations)
        successful = sum(1 for o in optimizations if o.get('optimization_applied', False))
        total_tokens = sum(o.get('tokens_used', 0) for o in optimizations)
        total_time = sum(o.get('processing_time_ms', 0) for o in optimizations)

        return {
            "total_optimizations": total,
            "successful_optimizations": successful,
            "success_rate": round(successful / total, 3) if total > 0 else 0,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_optimization": round(total_tokens / successful, 1) if successful > 0 else 0,
            "avg_processing_time_ms": round(total_time / total, 1) if total > 0 else 0
        }


# 使用範例
if __name__ == "__main__":
    import asyncio

    async def test_optimizer():
        """測試 LLM 答案優化器"""
        optimizer = LLMAnswerOptimizer()

        # 模擬檢索結果
        search_results = [
            {
                "id": 1,
                "title": "退租流程說明",
                "category": "合約問題",
                "content": """# 退租流程

## 步驟說明

1. **提前通知**：請於退租日前30天以書面方式通知房東
2. **繳清費用**：確認所有租金、水電費已繳清
3. **房屋檢查**：與房東約定時間進行房屋檢查
4. **押金退還**：確認房屋狀況良好後，7個工作天內退還押金

## 注意事項
- 需提前30天通知
- 需繳清所有費用
- 房屋需恢復原狀""",
                "similarity": 0.89
            }
        ]

        intent_info = {
            "intent_name": "退租流程",
            "intent_type": "knowledge",
            "keywords": ["退租", "辦理"]
        }

        # 測試優化
        print("🔄 開始優化答案...")
        result = optimizer.optimize_answer(
            question="請問如何辦理退租手續？",
            search_results=search_results,
            confidence_level="high",
            intent_info=intent_info
        )

        print(f"\n✅ 優化完成")
        print(f"使用優化：{result['optimization_applied']}")
        print(f"Token 使用：{result['tokens_used']}")
        print(f"處理時間：{result['processing_time_ms']}ms")
        print(f"\n{'='*60}")
        print("原始答案：")
        print(result['original_answer'][:200] + "...")
        print(f"\n{'='*60}")
        print("優化後答案：")
        print(result['optimized_answer'])
        print(f"{'='*60}")

    # 執行測試
    asyncio.run(test_optimizer())
