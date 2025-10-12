"""
知識匯入服務
統一處理各種格式的知識匯入，包括檔案解析、向量生成、資料庫儲存
"""
import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pandas as pd
import asyncpg
from asyncpg.pool import Pool
from openai import AsyncOpenAI
import time


class KnowledgeImportService:
    """知識匯入服務"""

    def __init__(self, db_pool: Pool):
        """
        初始化知識匯入服務

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        self.llm_model = "gpt-4o-mini"

    async def process_import_job(
        self,
        job_id: str,
        file_path: str,
        vendor_id: Optional[int],
        import_mode: str,
        enable_deduplication: bool,
        user_id: str = "admin"
    ) -> Dict:
        """
        處理知識匯入作業（主要入口）

        所有匯入的知識都會先進入審核佇列，
        經過人工審核通過後才會加入正式知識庫。

        Args:
            job_id: 作業 ID
            file_path: 上傳的檔案路徑
            vendor_id: 業者 ID（可選）
            import_mode: 匯入模式（append/replace/merge）
            enable_deduplication: 是否啟用去重
            user_id: 執行者 ID

        Returns:
            匯入結果統計
        """
        print(f"\n{'='*60}")
        print(f"📦 開始處理知識匯入作業")
        print(f"   作業 ID: {job_id}")
        print(f"   檔案: {file_path}")
        print(f"   業者: {vendor_id or '通用知識'}")
        print(f"   模式: {import_mode}")
        print(f"{'='*60}\n")

        try:
            # 1. 更新作業狀態為處理中
            await self.update_job_status(job_id, "processing", progress={"current": 0, "total": 100})

            # 2. 偵測檔案類型並選擇解析器
            file_type = self._detect_file_type(file_path)
            print(f"📄 檔案類型: {file_type}")

            # 3. 解析檔案
            await self.update_job_status(job_id, "processing", progress={"current": 10, "total": 100, "stage": "解析檔案"})
            knowledge_list = await self._parse_file(file_path, file_type)

            if not knowledge_list:
                raise Exception("未能從檔案中提取任何知識")

            print(f"✅ 解析出 {len(knowledge_list)} 條知識")

            # 4. 預先去重（文字完全相同）- 在 LLM 前執行，節省成本
            if enable_deduplication:
                await self.update_job_status(job_id, "processing", progress={"current": 20, "total": 100, "stage": "文字去重"})
                original_count = len(knowledge_list)
                knowledge_list = await self._deduplicate_exact_match(knowledge_list)
                text_skipped = original_count - len(knowledge_list)
                print(f"🔍 文字去重: 跳過 {text_skipped} 條完全相同的項目，剩餘 {len(knowledge_list)} 條")

            # 5. 生成問題摘要（使用 LLM）- 只處理去重後的知識
            await self.update_job_status(job_id, "processing", progress={"current": 35, "total": 100, "stage": "生成問題摘要"})
            await self._generate_question_summaries(knowledge_list)

            # 6. 生成向量嵌入 - 只處理去重後的知識
            await self.update_job_status(job_id, "processing", progress={"current": 55, "total": 100, "stage": "生成向量嵌入"})
            await self._generate_embeddings(knowledge_list)

            # 7. 語意去重（使用向量相似度）- 二次過濾
            if enable_deduplication:
                await self.update_job_status(job_id, "processing", progress={"current": 70, "total": 100, "stage": "語意去重"})
                semantic_original = len(knowledge_list)
                knowledge_list = await self._deduplicate_by_similarity(knowledge_list)
                semantic_skipped = semantic_original - len(knowledge_list)
                print(f"🔍 語意去重: 跳過 {semantic_skipped} 條語意相似的項目，剩餘 {len(knowledge_list)} 條")
                print(f"📊 總計跳過: {text_skipped + semantic_skipped} 條（文字: {text_skipped}, 語意: {semantic_skipped}）")

            # 8. 推薦意圖（使用 LLM 或分類器）
            await self.update_job_status(job_id, "processing", progress={"current": 76, "total": 100, "stage": "推薦意圖"})
            await self._recommend_intents(knowledge_list)

            # 9. 建立測試情境建議（需求 2：針對 B2C 知識）
            await self.update_job_status(job_id, "processing", progress={"current": 78, "total": 100, "stage": "建立測試情境建議"})
            test_scenario_count = await self._create_test_scenario_suggestions(knowledge_list, vendor_id)

            # 10. 匯入到審核佇列（需求 3：所有知識都需要審核）
            # 知識會先進入 ai_generated_knowledge_candidates 表
            # 人工審核通過後才會加入正式的 knowledge_base 表
            await self.update_job_status(job_id, "processing", progress={"current": 85, "total": 100, "stage": "匯入審核佇列"})
            result = await self._import_to_review_queue(
                knowledge_list,
                vendor_id=vendor_id,
                created_by=user_id
            )
            result['test_scenarios_created'] = test_scenario_count

            # 10. 更新作業狀態為完成
            await self.update_job_status(
                job_id,
                "completed",
                progress={"current": 100, "total": 100},
                result=result
            )

            print(f"\n{'='*60}")
            print(f"✅ 匯入完成（已進入審核佇列）")
            print(f"   匯入知識: {result['imported']} 條")
            print(f"   跳過: {result.get('skipped', 0)} 條")
            print(f"   錯誤: {result.get('errors', 0)} 條")
            if result.get('test_scenarios_created', 0) > 0:
                print(f"   測試情境建議: {result['test_scenarios_created']} 個")
            print(f"   ⚠️  所有知識需經人工審核後才會正式加入知識庫")
            print(f"{'='*60}\n")

            return result

        except Exception as e:
            # 更新作業狀態為失敗
            error_message = str(e)
            print(f"\n❌ 匯入失敗: {error_message}")
            await self.update_job_status(
                job_id,
                "failed",
                error=error_message
            )
            raise

    def _detect_file_type(self, file_path: str) -> str:
        """
        偵測檔案類型

        Args:
            file_path: 檔案路徑

        Returns:
            檔案類型（excel, pdf, txt, json）
        """
        suffix = Path(file_path).suffix.lower()

        if suffix in ['.xlsx', '.xls']:
            return 'excel'
        elif suffix == '.pdf':
            return 'pdf'
        elif suffix == '.txt':
            return 'txt'
        elif suffix == '.json':
            return 'json'
        else:
            return 'unknown'

    async def _parse_file(self, file_path: str, file_type: str) -> List[Dict]:
        """
        解析檔案

        Args:
            file_path: 檔案路徑
            file_type: 檔案類型

        Returns:
            知識列表
        """
        if file_type == 'excel':
            return await self._parse_excel(file_path)
        elif file_type == 'txt':
            return await self._parse_txt(file_path)
        elif file_type == 'json':
            return await self._parse_json(file_path)
        elif file_type == 'pdf':
            return await self._parse_pdf(file_path)
        else:
            raise Exception(f"不支援的檔案類型: {file_type}")

    async def _parse_excel(self, file_path: str) -> List[Dict]:
        """
        解析 Excel 檔案

        支援格式：
        - 欄位: 問題 / question / 問題摘要
        - 欄位: 答案 / answer / 回覆
        - 欄位: 分類 / category (可選)
        - 欄位: 對象 / audience (可選)
        - 欄位: 關鍵字 / keywords (可選)

        Args:
            file_path: Excel 檔案路徑

        Returns:
            知識列表
        """
        print(f"📖 解析 Excel 檔案: {file_path}")

        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"   讀取 {len(df)} 行資料")
        print(f"   欄位: {list(df.columns)}")

        # 欄位映射（支援多種欄位名稱）
        question_cols = ['問題', 'question', '問題摘要', 'question_summary', 'title', '標題']
        answer_cols = ['答案', 'answer', '回覆', 'response', 'content', '內容']
        category_cols = ['分類', 'category', '類別', 'type']
        audience_cols = ['對象', 'audience', '受眾']
        keywords_cols = ['關鍵字', 'keywords', '標籤', 'tags']

        # 找到對應的欄位
        question_col = next((col for col in df.columns if col in question_cols), None)
        answer_col = next((col for col in df.columns if col in answer_cols), None)
        category_col = next((col for col in df.columns if col in category_cols), None)
        audience_col = next((col for col in df.columns if col in audience_cols), None)
        keywords_col = next((col for col in df.columns if col in keywords_cols), None)

        if not answer_col:
            raise Exception(f"找不到答案欄位。支援的欄位名稱: {', '.join(answer_cols)}")

        knowledge_list = []
        current_category = None

        for idx, row in df.iterrows():
            # 如果有分類欄位且該行有值，更新當前分類
            if category_col and pd.notna(row[category_col]):
                potential_category = str(row[category_col]).strip()
                # 過濾掉非分類的描述性文字
                if potential_category and len(potential_category) < 50:
                    current_category = potential_category

            # 解析答案（必填）
            answer = row.get(answer_col)
            if pd.isna(answer) or not str(answer).strip() or len(str(answer).strip()) < 10:
                continue

            answer = str(answer).strip()

            # 解析問題（可選，如果沒有會用 LLM 生成）
            question = None
            if question_col and pd.notna(row[question_col]):
                question = str(row[question_col]).strip()

            # 解析對象
            audience = '租客'  # 預設
            if audience_col and pd.notna(row[audience_col]):
                audience = str(row[audience_col]).strip()

            # 解析關鍵字
            keywords = []
            if keywords_col and pd.notna(row[keywords_col]):
                keywords_str = str(row[keywords_col])
                keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]

            knowledge_list.append({
                'question_summary': question,  # 可能為 None，後續用 LLM 生成
                'answer': answer,
                'category': current_category or '一般問題',
                'audience': audience,
                'keywords': keywords,
                'source_file': Path(file_path).name
            })

        print(f"   ✅ 解析出 {len(knowledge_list)} 個有效知識項目")
        return knowledge_list

    async def _parse_txt(self, file_path: str) -> List[Dict]:
        """
        解析純文字檔案（使用 LLM 提取知識）

        Args:
            file_path: 文字檔案路徑

        Returns:
            知識列表
        """
        print(f"📖 解析 TXT 檔案: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if len(content) < 50:
            raise Exception("檔案內容過短，無法提取知識")

        # 使用 LLM 提取知識
        print("🤖 使用 LLM 提取知識...")

        system_prompt = """你是一個專業的知識庫分析師。
從提供的文字內容中提取客服問答知識。

請以 JSON 格式輸出：
{
  "knowledge_list": [
    {
      "question_summary": "問題摘要",
      "answer": "完整答案",
      "category": "分類",
      "audience": "租客|房東|管理師",
      "keywords": ["關鍵字1", "關鍵字2"]
    }
  ]
}

注意：
- 只提取清晰、完整的知識
- 問題摘要要簡潔（15字以內）
- 答案要完整且實用
- 避免包含私人資訊
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"請從以下內容提取知識：\n\n{content[:4000]}"}
                ]
            )

            result = json.loads(response.choices[0].message.content)
            knowledge_list = result.get('knowledge_list', [])

            # 添加來源資訊
            for knowledge in knowledge_list:
                knowledge['source_file'] = Path(file_path).name

            print(f"   ✅ 提取出 {len(knowledge_list)} 個知識項目")
            return knowledge_list

        except Exception as e:
            print(f"   ⚠️ LLM 提取失敗: {e}")
            raise Exception(f"無法從文字檔案提取知識: {e}")

    async def _parse_json(self, file_path: str) -> List[Dict]:
        """
        解析 JSON 檔案

        預期格式：
        {
          "knowledge": [
            {
              "question": "問題",
              "answer": "答案",
              "category": "分類",
              "audience": "對象",
              "keywords": ["關鍵字"]
            }
          ]
        }

        Args:
            file_path: JSON 檔案路徑

        Returns:
            知識列表
        """
        print(f"📖 解析 JSON 檔案: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 支援多種格式
        if 'knowledge' in data:
            raw_list = data['knowledge']
        elif 'knowledge_list' in data:
            raw_list = data['knowledge_list']
        elif isinstance(data, list):
            raw_list = data
        else:
            raise Exception("無法識別 JSON 格式。預期包含 'knowledge' 或 'knowledge_list' 欄位")

        knowledge_list = []
        for item in raw_list:
            # 欄位映射
            question = item.get('question') or item.get('question_summary') or item.get('title')
            answer = item.get('answer') or item.get('response') or item.get('content')

            if not answer or len(str(answer).strip()) < 10:
                continue

            knowledge_list.append({
                'question_summary': question,
                'answer': str(answer).strip(),
                'category': item.get('category', '一般問題'),
                'audience': item.get('audience', '租客'),
                'keywords': item.get('keywords', []),
                'source_file': Path(file_path).name
            })

        print(f"   ✅ 解析出 {len(knowledge_list)} 個知識項目")
        return knowledge_list

    async def _parse_pdf(self, file_path: str) -> List[Dict]:
        """
        解析 PDF 檔案

        Args:
            file_path: PDF 檔案路徑

        Returns:
            知識列表
        """
        # TODO: 實作 PDF 解析（需要安裝 PyPDF2 或 pdfplumber）
        raise Exception("PDF 格式暫不支援，請先轉換為 Excel 或 TXT")

    async def _generate_question_summaries(self, knowledge_list: List[Dict]):
        """
        為沒有問題摘要的知識生成問題

        Args:
            knowledge_list: 知識列表（會直接修改）
        """
        need_generation = [k for k in knowledge_list if not k.get('question_summary')]

        if not need_generation:
            print("✅ 所有知識都已有問題摘要")
            return

        print(f"🤖 為 {len(need_generation)} 條知識生成問題摘要...")

        for knowledge in need_generation:
            try:
                prompt = f"""請根據以下答案，生成一個簡潔的問題摘要（15字以內）。

分類：{knowledge['category']}
答案：{knowledge['answer'][:200]}

只輸出問題摘要，不要加其他說明。"""

                response = await self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    temperature=0.3,
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                )

                question_summary = response.choices[0].message.content.strip()
                knowledge['question_summary'] = question_summary

                # 避免 rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"   ⚠️ 生成問題失敗: {e}")
                # 備用方案
                knowledge['question_summary'] = f"{knowledge['category']}相關問題"

        print(f"   ✅ 問題摘要生成完成")

    async def _generate_embeddings(self, knowledge_list: List[Dict]):
        """
        為知識生成向量嵌入

        Args:
            knowledge_list: 知識列表（會直接修改）
        """
        print(f"🔮 為 {len(knowledge_list)} 條知識生成向量嵌入...")

        for idx, knowledge in enumerate(knowledge_list, 1):
            try:
                # 組合文字（問題 + 答案前段）
                text = f"{knowledge['question_summary']} {knowledge['answer'][:200]}"

                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )

                knowledge['embedding'] = response.data[0].embedding

                if idx % 10 == 0:
                    print(f"   進度: {idx}/{len(knowledge_list)}")

                # 避免 rate limit
                await asyncio.sleep(0.05)

            except Exception as e:
                print(f"   ⚠️ 生成向量失敗 (第 {idx} 條): {e}")
                raise Exception(f"向量生成失敗: {e}")

        print(f"   ✅ 向量嵌入生成完成")

    async def _deduplicate_exact_match(self, knowledge_list: List[Dict]) -> List[Dict]:
        """
        去除文字完全相同的知識（精確匹配）
        在 LLM 前執行，節省 OpenAI token 成本

        Args:
            knowledge_list: 知識列表

        Returns:
            去重後的知識列表
        """
        print(f"🔍 執行文字去重（精確匹配）...")

        async with self.db_pool.acquire() as conn:
            unique_list = []

            for knowledge in knowledge_list:
                # 檢查是否已存在相同的問題和答案（同時檢查正式知識庫、審核佇列和測試情境）
                exists = await conn.fetchval("""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM knowledge_base
                        WHERE question_summary = $1 AND answer = $2
                        UNION ALL
                        SELECT 1 FROM ai_generated_knowledge_candidates
                        WHERE question = $1 AND generated_answer = $2
                        UNION ALL
                        SELECT 1 FROM test_scenarios
                        WHERE test_question = $1
                    ) AS combined
                """, knowledge.get('question_summary'), knowledge['answer'])

                if exists == 0:
                    unique_list.append(knowledge)
                else:
                    print(f"   跳過重複: {knowledge.get('question_summary', '無問題')[:50]}...")

        return unique_list

    async def _deduplicate_by_similarity(
        self,
        knowledge_list: List[Dict],
        threshold: float = 0.85
    ) -> List[Dict]:
        """
        使用向量相似度去重（語意去重）
        檢查知識庫、審核佇列和測試情境中是否已有語意相似的知識

        重用 unclear_questions 的相似度機制：
        - 閾值：0.85（與 unclear_questions 一致）
        - 使用資料庫函數 check_knowledge_exists_by_similarity()

        Args:
            knowledge_list: 知識列表（必須已有 embedding）
            threshold: 相似度閾值（預設 0.85）

        Returns:
            去重後的知識列表
        """
        print(f"🔍 執行語意去重（相似度閾值: {threshold}）...")

        unique_list = []

        async with self.db_pool.acquire() as conn:
            for idx, knowledge in enumerate(knowledge_list, 1):
                embedding = knowledge.get('embedding')

                if not embedding:
                    print(f"   ⚠️  知識缺少 embedding，跳過語意檢查: {knowledge.get('question_summary', '無問題')[:50]}")
                    unique_list.append(knowledge)
                    continue

                # 將 embedding 轉換為 PostgreSQL vector 格式
                vector_str = '[' + ','.join(str(x) for x in embedding) + ']'

                # 使用資料庫函數檢查是否已存在相似知識
                result = await conn.fetchrow("""
                    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2)
                """, vector_str, threshold)

                if result and (result['exists_in_knowledge_base'] or result['exists_in_review_queue'] or result.get('exists_in_test_scenarios', False)):
                    # 找到相似知識，跳過
                    source = result['source_table']
                    matched_q = result['matched_question']
                    sim_score = result['similarity_score']

                    print(f"   跳過語意相似 (相似度: {sim_score:.4f}, 來源: {source})")
                    print(f"      新問題: {knowledge['question_summary'][:50]}...")
                    print(f"      相似問題: {matched_q[:50]}...")
                else:
                    # 沒有找到相似知識，保留
                    unique_list.append(knowledge)

                # 每處理 10 條顯示進度
                if idx % 10 == 0:
                    print(f"   進度: {idx}/{len(knowledge_list)}")

        return unique_list

    async def _recommend_intents(self, knowledge_list: List[Dict]):
        """
        為知識推薦合適的意圖

        使用 LLM 根據問題和答案內容推薦最合適的意圖
        推薦結果儲存到 knowledge['recommended_intent']

        Args:
            knowledge_list: 知識列表（會直接修改）
        """
        print(f"🎯 為 {len(knowledge_list)} 條知識推薦意圖...")

        # 1. 取得所有可用的意圖
        async with self.db_pool.acquire() as conn:
            intents = await conn.fetch("""
                SELECT id, name, description
                FROM intents
                ORDER BY id
            """)

        if not intents:
            print("   ⚠️  找不到任何意圖，跳過推薦")
            return

        # 建立意圖清單文字
        intent_list = "\n".join([
            f"- {intent['id']}: {intent['name']} ({intent['description']})"
            for intent in intents
        ])

        # 2. 為每條知識推薦意圖
        for idx, knowledge in enumerate(knowledge_list, 1):
            try:
                prompt = f"""請根據以下問答內容，從意圖清單中選擇最合適的意圖。

問題：{knowledge['question_summary']}
答案：{knowledge['answer'][:200]}
分類：{knowledge.get('category', '未分類')}

可用的意圖清單：
{intent_list}

請以 JSON 格式回應：
{{
  "intent_id": 推薦的意圖 ID（數字）,
  "intent_name": 意圖名稱,
  "confidence": 信心度（0.0-1.0）,
  "reasoning": 推薦理由（簡短說明）
}}

只輸出 JSON，不要加其他說明。"""

                response = await self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                result = json.loads(response.choices[0].message.content)

                # 儲存推薦結果
                knowledge['recommended_intent'] = {
                    'intent_id': result.get('intent_id'),
                    'intent_name': result.get('intent_name'),
                    'confidence': result.get('confidence', 0.8),
                    'reasoning': result.get('reasoning', '')
                }

                if idx <= 3:  # 只顯示前 3 條的推薦
                    print(f"   ✅ {knowledge['question_summary'][:40]}... → {result.get('intent_name')} (信心度: {result.get('confidence', 0):.2f})")

                # 避免 rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"   ⚠️  意圖推薦失敗 (第 {idx} 條): {e}")
                # 備用方案：使用預設意圖
                knowledge['recommended_intent'] = {
                    'intent_id': 4,  # 服務說明
                    'intent_name': '服務說明',
                    'confidence': 0.5,
                    'reasoning': '無法自動推薦，使用預設意圖'
                }

        print(f"   ✅ 意圖推薦完成")

    async def _clear_vendor_knowledge(self, vendor_id: int):
        """
        清除業者的現有知識（用於 replace 模式）

        Args:
            vendor_id: 業者 ID
        """
        print(f"🗑️  清除業者 {vendor_id} 的現有知識...")

        async with self.db_pool.acquire() as conn:
            deleted_count = await conn.fetchval("""
                DELETE FROM knowledge_base
                WHERE vendor_id = $1
                RETURNING COUNT(*)
            """, vendor_id)

            print(f"   ✅ 已刪除 {deleted_count or 0} 條舊知識")

    async def _import_to_database(
        self,
        knowledge_list: List[Dict],
        vendor_id: Optional[int],
        import_mode: str,
        created_by: str
    ) -> Dict:
        """
        匯入知識到資料庫

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID
            import_mode: 匯入模式
            created_by: 建立者

        Returns:
            匯入結果統計
        """
        print(f"💾 匯入 {len(knowledge_list)} 條知識到資料庫...")

        imported = 0
        skipped = 0
        errors = 0

        async with self.db_pool.acquire() as conn:
            # 取得預設意圖 ID
            default_intent_id = await conn.fetchval("""
                SELECT id FROM intents
                WHERE name IN ('一般知識', '其他', 'general')
                ORDER BY id
                LIMIT 1
            """)

            if not default_intent_id:
                print("⚠️ 找不到預設意圖，使用第一個意圖")
                default_intent_id = await conn.fetchval("SELECT id FROM intents ORDER BY id LIMIT 1")

            for idx, knowledge in enumerate(knowledge_list, 1):
                try:
                    await conn.execute("""
                        INSERT INTO knowledge_base (
                            intent_id,
                            vendor_id,
                            title,
                            category,
                            question_summary,
                            answer,
                            audience,
                            keywords,
                            source_file,
                            source_date,
                            embedding,
                            scope,
                            priority,
                            created_by,
                            created_at,
                            updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """,
                        default_intent_id,
                        vendor_id,
                        knowledge['question_summary'],  # title
                        knowledge['category'],
                        knowledge['question_summary'],
                        knowledge['answer'],
                        knowledge['audience'],
                        knowledge['keywords'],
                        knowledge['source_file'],
                        datetime.now().date(),
                        knowledge['embedding'],
                        'global' if not vendor_id else 'vendor',
                        0,  # priority
                        created_by
                    )

                    imported += 1

                    if idx % 10 == 0:
                        print(f"   進度: {idx}/{len(knowledge_list)}")

                except Exception as e:
                    print(f"   ⚠️ 匯入失敗 (第 {idx} 條): {e}")
                    errors += 1

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "total": len(knowledge_list)
        }

    async def _create_test_scenario_suggestions(
        self,
        knowledge_list: List[Dict],
        vendor_id: Optional[int]
    ) -> int:
        """
        為 B2C 對象的知識建立測試情境建議（需求 2）

        B2C 對象包括：租客、房東（所有外部業務範圍）

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID

        Returns:
            建立的測試情境數量
        """
        print(f"🧪 檢查 B2C 知識並建立測試情境建議...")

        # B2C 對象列表
        b2c_audiences = ['租客', '房東', 'tenant', 'landlord']

        created_count = 0

        async with self.db_pool.acquire() as conn:
            for knowledge in knowledge_list:
                audience = knowledge.get('audience', '').lower()

                # 檢查是否為 B2C 對象
                if not any(b2c in audience.lower() for b2c in b2c_audiences):
                    continue

                question = knowledge['question_summary']

                # 檢查是否已存在相似的測試情境
                exists = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM test_scenarios
                    WHERE test_question = $1
                """, question)

                if exists > 0:
                    continue

                # 建立測試情境建議
                try:
                    await conn.execute("""
                        INSERT INTO test_scenarios (
                            test_question,
                            expected_category,
                            difficulty,
                            status,
                            source,
                            created_at
                        ) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                    """,
                        question,
                        knowledge.get('category', '一般問題'),
                        'medium',  # 預設難度
                        'pending_review',  # 待審核狀態
                        'imported'
                    )

                    created_count += 1

                except Exception as e:
                    print(f"   ⚠️ 建立測試情境失敗: {e}")

        if created_count > 0:
            print(f"   ✅ 建立了 {created_count} 個測試情境建議")
        else:
            print(f"   ℹ️ 沒有需要建立測試情境的 B2C 知識")

        return created_count

    async def _import_to_review_queue(
        self,
        knowledge_list: List[Dict],
        vendor_id: Optional[int],
        created_by: str
    ) -> Dict:
        """
        將知識匯入到審核佇列（需求 3：混合模式）

        知識會先進入 ai_generated_knowledge_candidates 表，
        人工審核通過後才會加入正式的 knowledge_base

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID
            created_by: 建立者

        Returns:
            匯入結果統計
        """
        print(f"📋 將 {len(knowledge_list)} 條知識匯入審核佇列...")

        imported = 0
        errors = 0

        async with self.db_pool.acquire() as conn:
            for idx, knowledge in enumerate(knowledge_list, 1):
                try:
                    question = knowledge['question_summary']
                    answer = knowledge['answer']

                    # 1. 先檢查或建立對應的測試情境
                    test_scenario_id = await conn.fetchval("""
                        SELECT id FROM test_scenarios
                        WHERE test_question = $1
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, question)

                    # 如果沒有測試情境，先建立一個
                    if not test_scenario_id:
                        test_scenario_id = await conn.fetchval("""
                            INSERT INTO test_scenarios (
                                test_question,
                                expected_category,
                                difficulty,
                                status,
                                source,
                                created_at
                            ) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                            RETURNING id
                        """,
                            question,
                            knowledge.get('category', '一般問題'),
                            'medium',
                            'pending_review',
                            'imported'
                        )

                    # 2. 準備 generation_reasoning（包含意圖推薦）
                    recommended_intent = knowledge.get('recommended_intent', {})
                    reasoning = f"""分類: {knowledge.get('category')}, 對象: {knowledge.get('audience')}, 關鍵字: {', '.join(knowledge.get('keywords', []))}

【推薦意圖】
意圖 ID: {recommended_intent.get('intent_id', '未推薦')}
意圖名稱: {recommended_intent.get('intent_name', '未推薦')}
信心度: {recommended_intent.get('confidence', 0)}
推薦理由: {recommended_intent.get('reasoning', '無')}"""

                    # 3. 將 embedding 轉換為 PostgreSQL vector 格式
                    embedding = knowledge.get('embedding')
                    embedding_str = None
                    if embedding:
                        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

                    # 4. 建立知識候選記錄（含 embedding）
                    await conn.execute("""
                        INSERT INTO ai_generated_knowledge_candidates (
                            test_scenario_id,
                            question,
                            generated_answer,
                            question_embedding,
                            confidence_score,
                            generation_prompt,
                            ai_model,
                            generation_reasoning,
                            suggested_sources,
                            warnings,
                            status,
                            created_at,
                            updated_at
                        ) VALUES ($1, $2, $3, $4::vector, $5, $6, $7, $8, $9, $10, $11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        test_scenario_id,
                        question,
                        answer,
                        embedding_str,  # 向量嵌入（字串格式）
                        0.95,  # 匯入的知識給予較高的信心分數
                        f"從檔案匯入: {knowledge.get('source_file', 'unknown')}",
                        'knowledge_import',  # 標記為知識匯入來源
                        reasoning,  # 包含推薦意圖的詳細資訊
                        [knowledge.get('source_file', 'imported_file')],
                        [],  # 無警告
                        'pending_review'  # 待審核狀態
                    )

                    imported += 1

                    if idx % 10 == 0:
                        print(f"   進度: {idx}/{len(knowledge_list)}")

                except Exception as e:
                    print(f"   ⚠️ 匯入到審核佇列失敗 (第 {idx} 條): {e}")
                    errors += 1

        return {
            "imported": imported,
            "skipped": 0,
            "errors": errors,
            "total": len(knowledge_list),
            "mode": "review_queue"
        }

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[Dict] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """
        更新作業狀態

        注意：job 記錄必須在呼叫此方法前已存在（由上傳端點建立）

        Args:
            job_id: 作業 ID
            status: 狀態（processing/completed/failed）
            progress: 進度資訊
            result: 結果統計
            error: 錯誤訊息
        """
        async with self.db_pool.acquire() as conn:
            import uuid
            # 更新作業狀態（假設 job 記錄已存在）
            # 先進行基本更新
            updated = await conn.fetchval("""
                UPDATE knowledge_import_jobs
                SET status = $1::varchar,
                    progress = $2::jsonb,
                    result = $3::jsonb,
                    error_message = $4,
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CASE WHEN $1::varchar IN ('completed', 'failed')
                                        THEN CURRENT_TIMESTAMP
                                        ELSE completed_at
                                   END
                WHERE job_id = $5
                RETURNING job_id
            """, status, json.dumps(progress) if progress else None,
                json.dumps(result) if result else None, error, uuid.UUID(job_id))

            if not updated:
                raise Exception(f"Job {job_id} not found in database")

            # 如果有 result 且狀態是 completed，更新計數欄位
            if result and status == 'completed':
                await conn.execute("""
                    UPDATE knowledge_import_jobs
                    SET imported_count = ($1::jsonb->>'imported')::integer,
                        skipped_count = ($1::jsonb->>'skipped')::integer,
                        error_count = ($1::jsonb->>'errors')::integer
                    WHERE job_id = $2
                """, json.dumps(result), uuid.UUID(job_id))
