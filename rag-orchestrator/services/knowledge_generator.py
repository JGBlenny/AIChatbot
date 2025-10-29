"""
AI 知識生成服務
使用 OpenAI API 為測試情境生成知識庫候選答案
"""
import os
import json
import asyncio
from typing import List, Dict, Optional
import httpx
from difflib import SequenceMatcher


class KnowledgeGenerator:
    """使用 OpenAI 生成知識候選答案"""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 環境變數未設定")

        # 知識生成專用模型（預設 gpt-3.5-turbo，成本較低）
        # 系統其他部分使用 gpt-4o-mini
        self.model = os.getenv("KNOWLEDGE_GEN_MODEL", "gpt-3.5-turbo")
        self.api_url = "https://api.openai.com/v1/chat/completions"

        print(f"✅ KnowledgeGenerator 初始化完成")
        print(f"   使用模型: {self.model}")
        print(f"   （系統預設: gpt-4o-mini，知識生成: {self.model}）")

        # 安全類別白名單（只為這些類別生成知識）
        self.safe_categories = [
            "設施使用",
            "社區規範",
            "常見問題",
            "公共空間",
            "垃圾處理",
            "停車規定"
        ]

        # 限制類別（不自動生成，需人工審核）
        self.restricted_categories = [
            "租金計算",
            "合約條款",
            "退租流程",
            "押金處理",
            "法律諮詢"
        ]

    def is_safe_category(self, category: str) -> bool:
        """檢查類別是否安全（可自動生成）"""
        return category in self.safe_categories

    def is_restricted_category(self, category: str) -> bool:
        """檢查類別是否受限（不建議自動生成）"""
        return category in self.restricted_categories

    async def generate_knowledge_candidates(
        self,
        test_question: str,
        intent_category: str,
        num_candidates: int = 3,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        為測試問題生成知識候選

        Args:
            test_question: 測試問題
            intent_category: 意圖分類（如：租金繳納、寵物飼養）
            num_candidates: 生成候選數量（1-3）
            context: 額外上下文（業務範圍、現有知識摘要等）

        Returns:
            List[Dict]: 候選知識列表（已去重）
        """

        # 檢查類別限制
        if self.is_restricted_category(intent_category):
            print(f"⚠️  類別「{intent_category}」為限制類別，不建議自動生成知識")
            return [{
                "question": test_question,
                "answer": "（此類別不建議自動生成，請人工撰寫）",
                "category": intent_category,
                "confidence_score": 0.0,
                "reasoning": "受限類別，需要人工審核",
                "sources_needed": ["合約條款", "公司政策", "法律條文"],
                "warnings": ["此類別涉及法律、金錢或合約，不建議使用 AI 生成"]
            }]

        # 構建 prompt
        prompt = self._build_generation_prompt(
            test_question,
            intent_category,
            context
        )

        # 呼叫 OpenAI API
        try:
            candidates = await self._call_openai_api(
                prompt=prompt,
                num_candidates=num_candidates
            )

            print(f"🤖 AI 生成了 {len(candidates)} 個原始候選答案")

            # 去重：過濾相似度過高的候選
            deduplicated = self._deduplicate_candidates(candidates)

            if len(deduplicated) < len(candidates):
                print(f"🔄 去重後保留 {len(deduplicated)} 個不同的候選答案（移除了 {len(candidates) - len(deduplicated)} 個重複）")

            print(f"✅ 最終為「{test_question}」提供 {len(deduplicated)} 個候選答案")
            return deduplicated

        except Exception as e:
            print(f"❌ AI 知識生成失敗: {str(e)}")
            raise

    def _get_system_prompt(self) -> str:
        """系統 prompt - 定義 AI 的角色和限制"""
        return """你是一個專業的租屋管理知識專家。你的任務是為租客常見問題生成準確、專業的答案。

【重要原則】
1. **準確性優先**：如果不確定答案，明確說明需要人工審核或確認合約
2. **引用來源**：說明答案應基於什麼來源（法規、合約、公司政策）
3. **風險提示**：標註可能因個案而異的情況
4. **具體實用**：提供具體步驟或明確指引，避免模糊回答
5. **結構化輸出**：嚴格使用 JSON 格式返回

【答案撰寫規範】
- 長度：200-400 字
- 語氣：專業、友善、清晰
- 結構：總述 + 具體說明 + 補充提醒
- 避免：法律術語、模糊表達、未經證實的資訊

【輸出格式】
{
  "answer": "完整答案（2-3 段，清晰易懂）",
  "confidence": 0.8,
  "reasoning": "生成此答案的推理過程",
  "sources": ["租賃契約第5條", "民法第423條"],
  "warnings": ["此答案可能因物件而異，建議確認合約"]
}

【範例輸出】
{
  "answer": "一般來說，租屋處是可以飼養寵物的，但需要遵守以下規定：\\n\\n1. **事前告知**：在簽約前或飼養前，務必告知房東並取得書面同意。\\n2. **遵守社區規範**：不得影響其他住戶安寧，需做好清潔管理。\\n3. **押金規定**：部分房東會要求額外寵物押金，以保障房屋維護。\\n\\n建議您查看租賃合約中的「寵物飼養條款」，或直接聯繫房東確認。如合約未明確規定，可與房東協商並簽署補充協議。",
  "confidence": 0.75,
  "reasoning": "根據一般租屋慣例和常見合約條款推斷。寵物飼養通常需房東同意，但具體規定因合約而異。",
  "sources": ["租賃契約寵物條款", "社區管理規範"],
  "warnings": ["實際規定請以租賃合約為準", "不同房東政策可能不同"]
}"""

    def _build_generation_prompt(
        self,
        question: str,
        category: str,
        context: Optional[Dict]
    ) -> str:
        """構建生成 prompt"""

        prompt = f"""請為以下租屋相關問題生成專業答案：

【問題】
{question}

【分類】
{category}

【業務範圍】
- 租屋管理系統
- 服務對象：租客
- 常見場景：租金、維修、合約、設施使用、社區規範

"""

        # 加入已有知識作為參考（如果有）
        if context and context.get("related_knowledge"):
            related = context["related_knowledge"]
            if len(related) > 0:
                prompt += "\n【相關現有知識（供參考，不要照抄）】\n"
                for k in related[:3]:
                    prompt += f"- Q: {k.get('question', 'N/A')}\n"
                    answer_preview = k.get('answer', '')[:150]
                    prompt += f"  A: {answer_preview}{'...' if len(k.get('answer', '')) > 150 else ''}\n\n"

        # 安全提醒
        if self.is_safe_category(category):
            prompt += "\n【提醒】此類別為安全類別，可以自由生成答案。\n"
        else:
            prompt += "\n【提醒】此類別可能涉及專業知識，請標註不確定之處。\n"

        prompt += "\n請生成答案（JSON 格式）："

        return prompt

    async def _call_openai_api(
        self,
        prompt: str,
        num_candidates: int
    ) -> List[Dict]:
        """呼叫 OpenAI API"""

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            "temperature": float(os.getenv("KNOWLEDGE_GEN_TEMPERATURE", "0.7")),
            "n": num_candidates,  # 生成多個候選
            "max_tokens": int(os.getenv("KNOWLEDGE_GEN_MAX_TOKENS", "800")),
            "response_format": {"type": "json_object"}  # 強制 JSON 輸出（GPT-4 支援）
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API 錯誤: {response.status_code} - {response.text}")

            data = response.json()

            candidates = []
            for choice in data["choices"]:
                content = choice["message"]["content"]

                # 解析 AI 回應
                parsed = self._parse_ai_response(content)

                candidates.append(parsed)

            return candidates

    def _parse_ai_response(self, content: str) -> Dict:
        """解析 AI 回應"""
        try:
            # 嘗試解析 JSON
            data = json.loads(content)

            # 驗證必要欄位
            if "answer" not in data:
                raise ValueError("缺少 answer 欄位")

            # 補充預設值
            return {
                "answer": data["answer"],
                "confidence_score": float(data.get("confidence", 0.7)),
                "reasoning": data.get("reasoning", ""),
                "sources_needed": data.get("sources", []),
                "warnings": data.get("warnings", [])
            }

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  AI 回應解析失敗: {str(e)}")
            print(f"   原始回應: {content[:200]}...")

            # 如果解析失敗，嘗試提取文字
            return {
                "answer": content,
                "confidence_score": 0.5,
                "reasoning": "AI 回應格式非預期，需人工檢查",
                "sources_needed": [],
                "warnings": ["需要人工審核格式和內容"]
            }

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        計算兩段文字的相似度 (0.0 ~ 1.0)

        使用 SequenceMatcher 計算字符層級的相似度

        Args:
            text1: 第一段文字
            text2: 第二段文字

        Returns:
            float: 相似度分數 (0.0 = 完全不同, 1.0 = 完全相同)
        """
        if not text1 or not text2:
            return 0.0

        # 移除多餘空白並轉小寫以提高比較準確性
        t1 = " ".join(text1.lower().split())
        t2 = " ".join(text2.lower().split())

        # 使用 SequenceMatcher 計算相似度
        similarity = SequenceMatcher(None, t1, t2).ratio()

        return similarity

    def _deduplicate_candidates(
        self,
        candidates: List[Dict],
        similarity_threshold: float = 0.80
    ) -> List[Dict]:
        """
        去除相似度過高的候選答案

        策略：
        1. 保留第一個候選
        2. 對於後續候選，只有當其與所有已保留候選的相似度都低於閾值時才保留
        3. 相似度閾值默認 0.80 (80%)

        Args:
            candidates: 候選列表
            similarity_threshold: 相似度閾值，超過此值視為重複

        Returns:
            List[Dict]: 去重後的候選列表
        """
        if len(candidates) <= 1:
            return candidates

        deduplicated = [candidates[0]]  # 保留第一個候選

        for i, candidate in enumerate(candidates[1:], start=1):
            answer = candidate.get("answer", "")

            # 檢查與所有已保留候選的相似度
            is_duplicate = False
            for kept_candidate in deduplicated:
                kept_answer = kept_candidate.get("answer", "")
                similarity = self._calculate_text_similarity(answer, kept_answer)

                if similarity >= similarity_threshold:
                    print(f"   ⚠️  候選 #{i+1} 與候選 #{deduplicated.index(kept_candidate)+1} 相似度過高 ({similarity:.2%})，已移除")
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(candidate)
                print(f"   ✅ 候選 #{i+1} 已保留（與現有候選差異足夠）")

        return deduplicated

    async def batch_generate(
        self,
        test_scenarios: List[Dict],
        max_concurrent: int = 3
    ) -> Dict[int, List[Dict]]:
        """
        批量生成知識候選（用於多個測試情境）

        Args:
            test_scenarios: 測試情境列表 [{"id": 1, "question": "...", "category": "..."}]
            max_concurrent: 最大並發數（避免 API 限流）

        Returns:
            Dict[int, List[Dict]]: {scenario_id: [candidates]}
        """

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(scenario):
            async with semaphore:
                try:
                    candidates = await self.generate_knowledge_candidates(
                        test_question=scenario["question"],
                        intent_category=scenario["category"],
                        num_candidates=2  # 批量時減少候選數
                    )
                    return scenario["id"], candidates
                except Exception as e:
                    print(f"❌ 為情境 #{scenario['id']} 生成失敗: {str(e)}")
                    return scenario["id"], []

        tasks = [generate_with_limit(s) for s in test_scenarios]
        results = await asyncio.gather(*tasks)

        return dict(results)


# 單例模式（可選）
_generator_instance = None


def get_knowledge_generator() -> KnowledgeGenerator:
    """獲取知識生成器實例（單例）"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = KnowledgeGenerator()
    return _generator_instance
