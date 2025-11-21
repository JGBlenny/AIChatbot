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
        self.llm_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

        # 質量評估配置
        self.quality_evaluation_enabled = os.getenv("QUALITY_EVALUATION_ENABLED", "true").lower() == "true"
        self.quality_evaluation_threshold = int(os.getenv("QUALITY_EVALUATION_THRESHOLD", "6"))

    async def process_import_job(
        self,
        job_id: str,
        file_path: str,
        vendor_id: Optional[int],
        import_mode: str,
        enable_deduplication: bool,
        skip_review: bool = False,
        default_priority: int = 0,
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
            skip_review: 是否跳過審核直接加入知識庫
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

            # 8.5. 質量評估（自動篩選低質量知識）
            await self.update_job_status(job_id, "processing", progress={"current": 77, "total": 100, "stage": "質量評估"})
            await self._evaluate_quality(knowledge_list)

            # 9. 建立測試情境建議（需求 2：針對 B2C 知識）
            await self.update_job_status(job_id, "processing", progress={"current": 78, "total": 100, "stage": "建立測試情境建議"})
            test_scenario_count = await self._create_test_scenario_suggestions(knowledge_list, vendor_id)

            # 10. 根據 skip_review 參數決定匯入目標
            if skip_review:
                # 直接匯入到正式知識庫
                await self.update_job_status(job_id, "processing", progress={"current": 85, "total": 100, "stage": "直接匯入知識庫"})
                result = await self._import_to_database(
                    knowledge_list,
                    vendor_id=vendor_id,
                    import_mode=import_mode,
                    default_priority=default_priority,
                    created_by=user_id
                )
                result['test_scenarios_created'] = test_scenario_count
                result['mode'] = 'direct'
            else:
                # 匯入到審核佇列（需求 3：所有知識都需要審核）
                # 知識會先進入 ai_generated_knowledge_candidates 表
                # 人工審核通過後才會加入正式的 knowledge_base 表
                await self.update_job_status(job_id, "processing", progress={"current": 85, "total": 100, "stage": "匯入審核佇列"})
                result = await self._import_to_review_queue(
                    knowledge_list,
                    vendor_id=vendor_id,
                    created_by=user_id
                )
                result['test_scenarios_created'] = test_scenario_count

            # 11. 更新作業狀態為完成
            await self.update_job_status(
                job_id,
                "completed",
                progress={"current": 100, "total": 100},
                result=result
            )

            print(f"\n{'='*60}")
            if skip_review:
                print(f"✅ 匯入完成（已直接加入正式知識庫）")
            else:
                print(f"✅ 匯入完成（已進入審核佇列）")
            print(f"   匯入知識: {result['imported']} 條")
            print(f"   跳過: {result.get('skipped', 0)} 條")
            print(f"   錯誤: {result.get('errors', 0)} 條")
            if result.get('test_scenarios_created', 0) > 0:
                print(f"   測試情境建議: {result['test_scenarios_created']} 個")
            if not skip_review:
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
            檔案類型（excel, csv, pdf, txt, json）
        """
        suffix = Path(file_path).suffix.lower()

        if suffix in ['.xlsx', '.xls']:
            return 'excel'
        elif suffix == '.csv':
            return 'csv'
        elif suffix == '.pdf':
            return 'pdf'
        elif suffix == '.txt':
            return 'txt'
        elif suffix == '.json':
            return 'json'
        else:
            return 'unknown'

    def _clean_html(self, html_text: str) -> str:
        """
        清理 HTML 標籤，保留文字內容並維持適當格式

        使用 BeautifulSoup 進行智能 HTML 清理：
        - 移除所有 style 屬性
        - 移除 script 和 style 標籤
        - 保留基本段落結構（<p>、<br> 轉換為換行）
        - 保留列表結構（<li> 添加項目符號）
        - 移除所有其他 HTML 標籤
        - 清理多餘空白

        Args:
            html_text: 包含 HTML 標籤的文字

        Returns:
            清理後的純文字
        """
        # 如果不包含 HTML 標籤，直接返回
        if '<' not in html_text or '>' not in html_text:
            return html_text

        try:
            from bs4 import BeautifulSoup

            # 解析 HTML
            soup = BeautifulSoup(html_text, 'lxml')

            # 移除 script 和 style 標籤
            for tag in soup(['script', 'style']):
                tag.decompose()

            # 移除所有 style 屬性
            for tag in soup.find_all(True):
                if 'style' in tag.attrs:
                    del tag.attrs['style']

            # 處理段落和換行
            for p in soup.find_all('p'):
                p.insert_after(soup.new_string('\n\n'))

            for br in soup.find_all('br'):
                br.replace_with(soup.new_string('\n'))

            # 處理列表項目
            for li in soup.find_all('li'):
                li.insert_before(soup.new_string('• '))
                li.insert_after(soup.new_string('\n'))

            # 提取純文字
            text = soup.get_text()

            # 清理多餘空白
            import re
            # 移除每行前後的空白
            lines = [line.strip() for line in text.split('\n')]
            # 移除空行（但保留單個換行）
            text = '\n'.join(lines)
            # 將連續 3 個以上的換行符縮減為 2 個
            text = re.sub(r'\n{3,}', '\n\n', text)

            return text.strip()

        except Exception as e:
            print(f"   ⚠️  HTML 清理失敗: {str(e)}，使用原始文字")
            return html_text

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
        elif file_type == 'csv':
            return await self._parse_csv(file_path)
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

            # HTML 清理（使用 BeautifulSoup）
            answer = self._clean_html(answer)

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

    async def _parse_csv(self, file_path: str) -> List[Dict]:
        """
        解析 CSV 檔案（加強版：支援 JSON 欄位格式）

        支援格式：
        1. 標準 CSV 格式：
           - 欄位: 問題 / question / 問題摘要 / title
           - 欄位: 答案 / answer / 回覆 / content
           - 欄位: 分類 / category (可選)
           - 欄位: 對象 / audience (可選)
           - 欄位: 關鍵字 / keywords (可選)

        2. JSON 欄位格式（如 help_datas.csv）：
           - 欄位值為 JSON 字串，自動提取 zh-TW 語系
           - 例如: {"zh-TW":"物件","en-US":"Property"}

        Args:
            file_path: CSV 檔案路徑

        Returns:
            知識列表
        """
        print(f"📖 解析 CSV 檔案: {file_path}")

        # 讀取 CSV，pandas 會自動處理編碼
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # 如果 UTF-8 失敗，嘗試其他編碼
            df = pd.read_csv(file_path, encoding='utf-8-sig')

        print(f"   讀取 {len(df)} 行資料")
        print(f"   欄位: {list(df.columns)}")

        # 欄位映射（支援多種欄位名稱）
        question_cols = ['問題', 'question', '問題摘要', 'question_summary', 'title', '標題']
        answer_cols = ['答案', 'answer', '回覆', 'response', 'content', '內容']
        category_cols = ['分類', 'category', '類別', 'type']
        audience_cols = ['對象', 'audience', '受眾', 'target_user']
        keywords_cols = ['關鍵字', 'keywords', '標籤', 'tags']
        intent_id_cols = ['意圖ID', 'intent_id', 'intent', '意圖']

        # 找到對應的欄位
        question_col = next((col for col in df.columns if col in question_cols), None)
        answer_col = next((col for col in df.columns if col in answer_cols), None)
        category_col = next((col for col in df.columns if col in category_cols), None)
        audience_col = next((col for col in df.columns if col in audience_cols), None)
        keywords_col = next((col for col in df.columns if col in keywords_cols), None)
        intent_id_col = next((col for col in df.columns if col in intent_id_cols), None)

        # 如果找不到標準欄位名稱，嘗試使用位置推測
        # help_datas.csv 格式: title, title.1, content (分類, 問題, 答案)
        if not answer_col and len(df.columns) >= 3:
            # 檢查是否為 help_datas.csv 格式（第三欄通常是答案）
            if 'content' in df.columns:
                category_col = df.columns[0]  # 第一欄：分類
                question_col = df.columns[1]  # 第二欄：問題
                answer_col = 'content'        # 第三欄：答案
                print(f"   偵測到特殊格式 CSV，使用欄位: {category_col}, {question_col}, {answer_col}")

        if not answer_col:
            raise Exception(f"找不到答案欄位。支援的欄位名稱: {', '.join(answer_cols)}\n實際欄位: {list(df.columns)}")

        knowledge_list = []
        current_category = None

        for idx, row in df.iterrows():
            try:
                # === 1. 解析分類（支援 JSON 格式） ===
                category = None
                if category_col and pd.notna(row[category_col]):
                    cat_value = str(row[category_col]).strip()
                    # 檢查是否為 JSON 格式
                    if cat_value.startswith('{') and cat_value.endswith('}'):
                        try:
                            cat_json = json.loads(cat_value)
                            category = cat_json.get('zh-TW', cat_json.get('zh-tw', cat_value))
                        except json.JSONDecodeError:
                            category = cat_value
                    else:
                        category = cat_value

                    # 過濾掉非分類的描述性文字
                    if category and len(category) < 50:
                        current_category = category

                # === 2. 解析問題（支援 JSON 格式） ===
                question = None
                if question_col and pd.notna(row[question_col]):
                    q_value = str(row[question_col]).strip()
                    # 檢查是否為 JSON 格式
                    if q_value.startswith('{') and q_value.endswith('}'):
                        try:
                            q_json = json.loads(q_value)
                            question = q_json.get('zh-TW', q_json.get('zh-tw'))
                        except json.JSONDecodeError:
                            question = q_value
                    else:
                        question = q_value

                # === 3. 解析答案（支援 JSON 格式） ===
                answer = None
                if pd.notna(row[answer_col]):
                    a_value = str(row[answer_col]).strip()
                    # 檢查是否為 JSON 格式
                    if a_value.startswith('{') and a_value.endswith('}'):
                        try:
                            a_json = json.loads(a_value)
                            answer = a_json.get('zh-TW', a_json.get('zh-tw'))
                        except json.JSONDecodeError:
                            answer = a_value
                    else:
                        answer = a_value

                # 驗證答案有效性
                if not answer or len(answer.strip()) < 10:
                    continue

                answer = answer.strip()

                # === 4. HTML 清理（使用 BeautifulSoup） ===
                answer = self._clean_html(answer)

                # === 5. 解析對象 ===
                audience = '租客'  # 預設
                if audience_col and pd.notna(row[audience_col]):
                    audience = str(row[audience_col]).strip()

                # === 6. 解析關鍵字 ===
                keywords = []
                if keywords_col and pd.notna(row[keywords_col]):
                    keywords_str = str(row[keywords_col])
                    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]

                # === 7. 解析意圖 ID ===
                intent_id = None
                if intent_id_col and pd.notna(row[intent_id_col]):
                    try:
                        intent_id_value = row[intent_id_col]
                        # 處理不同類型的值
                        if isinstance(intent_id_value, (int, float)):
                            intent_id = int(intent_id_value)
                        elif isinstance(intent_id_value, str):
                            intent_id_value = intent_id_value.strip()
                            if intent_id_value.isdigit():
                                intent_id = int(intent_id_value)
                    except (ValueError, TypeError):
                        print(f"   ⚠️  第 {idx + 1} 行意圖 ID 格式錯誤: {row[intent_id_col]}")

                # === 8. 建立知識項目 ===
                knowledge_list.append({
                    'question_summary': question,  # 可能為 None，後續用 LLM 生成
                    'answer': answer,
                    'category': current_category or '一般問題',
                    'audience': audience,
                    'keywords': keywords,
                    'intent_id': intent_id,  # 預設意圖 ID（可能為 None）
                    'source_file': Path(file_path).name
                })

            except Exception as e:
                print(f"   ⚠️  第 {idx + 1} 行解析失敗: {str(e)}")
                continue

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

⚠️ 重要：提取的知識必須是「通用」的、可重複使用的知識。

請遵循以下泛化規則：
1. 移除特定物業/建物名稱（如：三葉寓所 → 該物業/租處/建物）
2. 移除特定房號/單位號碼（如：2B5、5A2 → 該房間/該單位/該租處）
3. 移除特定日期（如：113/12/31 → 到期日/指定日期）
4. 移除個人姓名、電話、聯絡方式等私人資訊
5. **公司名稱泛化**：將特定公司名稱（如：興中資產、XX管理公司）改為「物業管理公司」
6. 保留處理流程、規則、政策、注意事項等通用知識
7. 如果某條知識過於特定（如：僅適用於某個房間的特殊設備），請在 warnings 中註明

泛化範例：
❌ 原文：「三葉寓所-2B5有低電度警報，若預計可用電度歸零將會斷電，煩請管理師再聯繫提醒租客盡快進行電錶儲值。」
✅ 泛化：「當租處出現低電度警報時，若預計可用電度歸零將會斷電，請管理師聯繫租客盡快進行電錶儲值。」
✅ warnings：["原文包含特定物業名稱和房號"]

❌ 原文：「房東需要將管理費支付給興中資產公司。」
✅ 泛化：「房東需要將管理費支付給物業管理公司。」
✅ warnings：["已將特定公司名稱泛化為物業管理公司"]

請以 JSON 格式輸出：
{
  "knowledge_list": [
    {
      "question_summary": "問題摘要（15字以內）",
      "answer": "完整答案（已泛化）",
      "category": "分類（如：帳務問題、設施使用、合約問題等）",
      "audience": "租客|房東|管理師",
      "keywords": ["關鍵字1", "關鍵字2"],
      "warnings": ["警告訊息（如果有特定內容被泛化或無法泛化）"]
    }
  ]
}

注意：
- 只提取清晰、完整、可泛化的知識
- 如果某條資訊過於特定（如：通知某人某事），不要提取
- 問題摘要要簡潔（15字以內）
- 答案要完整且實用
- warnings 為選填，沒有警告可省略
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                temperature=0.3,
                max_tokens=2000,  # 提取知識列表需要較長輸出（多個 Q&A 的 JSON）
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"請從以下內容提取知識：\n\n{content[:4000]}"}
                ]
            )

            result = json.loads(response.choices[0].message.content)
            knowledge_list = result.get('knowledge_list', [])

            # 添加來源資訊並檢查泛化警告
            generalized_count = 0
            for knowledge in knowledge_list:
                knowledge['source_file'] = Path(file_path).name

                # 統計有泛化警告的知識
                if knowledge.get('warnings'):
                    generalized_count += 1
                    print(f"   ⚠️  泛化警告: {knowledge['question_summary'][:30]}... - {knowledge['warnings']}")

            print(f"   ✅ 提取出 {len(knowledge_list)} 個知識項目")
            if generalized_count > 0:
                print(f"   🔄 其中 {generalized_count} 條知識已自動泛化（移除特定物業/房號/日期）")
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
                        AND status IN ('approved', 'in_testing')
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
                    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2::DECIMAL)
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
                    max_tokens=500,  # 意圖推薦只需小量輸出
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

    async def _evaluate_quality(self, knowledge_list: List[Dict]):
        """
        評估知識答案的質量

        使用 LLM 評估答案是否有實用價值，避免空泛、循環邏輯或無意義的內容
        評估結果儲存到 knowledge['quality_evaluation']

        Args:
            knowledge_list: 知識列表（會直接修改）
        """
        # 檢查是否啟用質量評估
        if not self.quality_evaluation_enabled:
            print(f"⏭️  質量評估已停用（QUALITY_EVALUATION_ENABLED=false）")
            # 所有知識預設為可接受
            for knowledge in knowledge_list:
                knowledge['quality_evaluation'] = {
                    'quality_score': 8,
                    'is_acceptable': True,
                    'issues': [],
                    'reasoning': '質量評估已停用，預設為可接受'
                }
            return

        print(f"🔍 評估 {len(knowledge_list)} 條知識的質量（門檻: {self.quality_evaluation_threshold}/10）...")

        for idx, knowledge in enumerate(knowledge_list, 1):
            try:
                prompt = f"""請評估以下問答內容的質量。

問題：{knowledge['question_summary']}
答案：{knowledge['answer']}

評估標準：
1. 具體性：答案是否包含具體的操作步驟、細節或說明？
2. 實用性：答案是否能實際幫助使用者解決問題？
3. 完整性：答案是否完整回答了問題？
4. 非循環性：答案是否避免了循環邏輯（如「需要做X時就做X」）？
5. 深度：答案是否有足夠的深度（不只是重複問題或顯而易見的建議）？

請以 JSON 格式回應：
{{
  "quality_score": 質量分數（1-10，10 為最高）,
  "is_acceptable": 是否可接受（true/false，分數 >= {self.quality_evaluation_threshold} 為可接受）,
  "issues": ["問題1", "問題2"],
  "reasoning": "評估理由（簡短說明）"
}}

評分參考：
- 9-10分：內容詳實、具體、有實用價值，明確說明操作步驟
- 8分：有實用價值，包含必要細節和具體說明
- 6-7分：有一定價值，但過於空泛或缺少關鍵細節
- 4-5分：基本可用，但內容空泛
- 1-3分：無實用價值，有循環邏輯或重複問題，應該拒絕

⚠️ 注意：只有分數 >= {self.quality_evaluation_threshold} 的知識才能進入審核佇列。

只輸出 JSON，不要加其他說明。"""

                response = await self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    temperature=0.3,
                    max_tokens=500,  # 質量評估只需小量輸出
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                result = json.loads(response.choices[0].message.content)

                # 儲存評估結果
                knowledge['quality_evaluation'] = {
                    'quality_score': result.get('quality_score', 5),
                    'is_acceptable': result.get('is_acceptable', True),
                    'issues': result.get('issues', []),
                    'reasoning': result.get('reasoning', '')
                }

                # 顯示低質量的知識
                if not result.get('is_acceptable', True):
                    print(f"   ⚠️  低質量 (分數: {result.get('quality_score', 0)}): {knowledge['question_summary'][:40]}...")
                    print(f"      理由: {result.get('reasoning', '')[:80]}")
                elif idx <= 3:  # 顯示前 3 條的評估
                    print(f"   ✅ {knowledge['question_summary'][:40]}... → 分數: {result.get('quality_score', 0)}/10")

                # 避免 rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"   ⚠️  質量評估失敗 (第 {idx} 條): {e}")
                # 備用方案：預設為可接受
                knowledge['quality_evaluation'] = {
                    'quality_score': 6,
                    'is_acceptable': True,
                    'issues': [],
                    'reasoning': '無法自動評估，預設為可接受'
                }

        # 統計質量分布
        acceptable_count = sum(1 for k in knowledge_list if k.get('quality_evaluation', {}).get('is_acceptable', True))
        rejected_count = len(knowledge_list) - acceptable_count

        print(f"   ✅ 質量評估完成")
        print(f"      可接受: {acceptable_count} 條")
        if rejected_count > 0:
            print(f"      低質量: {rejected_count} 條（將自動標記為已拒絕）")

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
        default_priority: int = 0,
        created_by: str = "admin"
    ) -> Dict:
        """
        匯入知識到資料庫

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID
            import_mode: 匯入模式
            default_priority: 統一優先級（0=未啟用，1=已啟用）
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
                    # 將 embedding 轉換為 PostgreSQL vector 格式
                    embedding = knowledge.get('embedding')
                    embedding_str = None
                    if embedding:
                        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

                    await conn.execute("""
                        INSERT INTO knowledge_base (
                            intent_id,
                            vendor_id,
                            question_summary,
                            answer,
                            keywords,
                            source_file,
                            source_date,
                            embedding,
                            scope,
                            priority,
                            created_at,
                            updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8::vector, $9, $10,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """,
                        knowledge.get('intent_id') or default_intent_id,  # 🔧 優先使用 CSV 中的 intent_id
                        vendor_id,
                        knowledge['question_summary'],
                        knowledge['answer'],
                        knowledge['keywords'],
                        knowledge['source_file'],
                        datetime.now().date(),
                        embedding_str,
                        'global' if not vendor_id else 'vendor',
                        default_priority  # 使用傳入的 default_priority 參數
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
                    category_info = knowledge.get('category', '一般問題')
                    await conn.execute("""
                        INSERT INTO test_scenarios (
                            test_question,
                            difficulty,
                            status,
                            source,
                            notes,
                            created_at
                        ) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                    """,
                        question,
                        'medium',  # 預設難度
                        'pending_review',  # 待審核狀態
                        'imported',
                        f"導入的知識（類別: {category_info}）"
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
        auto_rejected = 0
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
                        category_info = knowledge.get('category', '一般問題')
                        test_scenario_id = await conn.fetchval("""
                            INSERT INTO test_scenarios (
                                test_question,
                                difficulty,
                                status,
                                source,
                                notes,
                                created_at
                            ) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                            RETURNING id
                        """,
                            question,
                            'medium',
                            'pending_review',
                            'imported',
                            f"導入的知識（類別: {category_info}）"
                        )

                    # 2. 準備 generation_reasoning（包含意圖推薦、泛化警告和質量評估）
                    recommended_intent = knowledge.get('recommended_intent', {})
                    warnings_list = knowledge.get('warnings', [])
                    quality_eval = knowledge.get('quality_evaluation', {})

                    # 提取推薦意圖 ID 並建立陣列
                    intent_ids = []
                    if recommended_intent and recommended_intent.get('intent_id') not in [None, '未推薦', 'null']:
                        try:
                            intent_id = int(recommended_intent.get('intent_id'))
                            intent_ids = [intent_id]
                        except (ValueError, TypeError):
                            pass  # 如果轉換失敗，保持空陣列

                    reasoning = f"""分類: {knowledge.get('category')}, 對象: {knowledge.get('audience')}, 關鍵字: {', '.join(knowledge.get('keywords', []))}

【推薦意圖】
意圖 ID: {recommended_intent.get('intent_id', '未推薦')}
意圖名稱: {recommended_intent.get('intent_name', '未推薦')}
信心度: {recommended_intent.get('confidence', 0)}
推薦理由: {recommended_intent.get('reasoning', '無')}"""

                    # 如果有泛化警告，加到 reasoning 中
                    if warnings_list:
                        reasoning += f"\n\n【泛化處理】\n" + "\n".join([f"- {w}" for w in warnings_list])

                    # 決定狀態：根據質量評估結果
                    is_acceptable = quality_eval.get('is_acceptable', True)
                    if is_acceptable:
                        status = 'pending_review'
                    else:
                        status = 'rejected'
                        auto_rejected += 1
                        # 加入質量評估資訊到 reasoning
                        reasoning += f"\n\n【質量評估 - 自動拒絕】\n"
                        reasoning += f"質量分數: {quality_eval.get('quality_score', 0)}/10\n"
                        reasoning += f"拒絕理由: {quality_eval.get('reasoning', '')}\n"
                        if quality_eval.get('issues'):
                            reasoning += f"問題列表: " + ", ".join(quality_eval.get('issues', []))

                    # 3. 將 embedding 轉換為 PostgreSQL vector 格式
                    embedding = knowledge.get('embedding')
                    embedding_str = None
                    if embedding:
                        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

                    # 4. 建立知識候選記錄（含 embedding、warnings 和 intent_ids）
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
                            intent_ids,
                            status,
                            created_at,
                            updated_at
                        ) VALUES ($1, $2, $3, $4::vector, $5, $6, $7, $8, $9, $10, $11, $12, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        test_scenario_id,
                        question,
                        answer,
                        embedding_str,  # 向量嵌入（字串格式）
                        0.85,  # 匯入的知識固定信心分數 85%
                        f"從檔案匯入: {knowledge.get('source_file', 'unknown')}",
                        'knowledge_import',  # 標記為知識匯入來源
                        reasoning,  # 包含推薦意圖、泛化警告和質量評估的詳細資訊
                        [knowledge.get('source_file', 'imported_file')],
                        warnings_list,  # 泛化警告（如果有）
                        intent_ids,  # 推薦意圖 ID 陣列（自動填入）
                        status  # 根據質量評估動態設定的狀態
                    )

                    imported += 1

                    if idx % 10 == 0:
                        print(f"   進度: {idx}/{len(knowledge_list)}")

                except Exception as e:
                    print(f"   ⚠️ 匯入到審核佇列失敗 (第 {idx} 條): {e}")
                    errors += 1

        print(f"\n   ✅ 匯入完成:")
        print(f"      總共: {len(knowledge_list)} 條")
        print(f"      待審核: {imported - auto_rejected} 條")
        if auto_rejected > 0:
            print(f"      自動拒絕: {auto_rejected} 條（質量不足）")
        if errors > 0:
            print(f"      錯誤: {errors} 條")

        return {
            "imported": imported,
            "auto_rejected": auto_rejected,
            "pending_review": imported - auto_rejected,
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
