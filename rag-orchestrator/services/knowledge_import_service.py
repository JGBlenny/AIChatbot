"""
知識匯入服務
統一處理各種格式的知識匯入，包括檔案解析、向量生成、資料庫儲存

重構日期：2025-11-21 - 改用統一 Job 系統
"""
import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pandas as pd
import asyncpg
from asyncpg.pool import Pool
import time

# 引入統一 Job 服務
from services.unified_job_service import UnifiedJobService
from services.llm_provider import get_llm_provider, LLMProvider


class KnowledgeImportService(UnifiedJobService):
    """知識匯入服務（已整合到統一 Job 系統）"""

    def __init__(self, db_pool: Pool, llm_provider: Optional[LLMProvider] = None):
        """
        初始化知識匯入服務

        Args:
            db_pool: 資料庫連接池
            llm_provider: LLM Provider（可選，默認使用全域 Provider）
        """
        # 初始化父類（統一 Job 服務）
        super().__init__(db_pool)
        self.llm_provider = llm_provider or get_llm_provider()
        self.embedding_model = "text-embedding-3-small"
        # 知識匯入使用 DOCUMENT_CONVERTER_MODEL（需要大 context 處理長文本）
        # 優先順序：DOCUMENT_CONVERTER_MODEL > KNOWLEDGE_GEN_MODEL > gpt-4o
        self.llm_model = os.getenv("DOCUMENT_CONVERTER_MODEL",
                                   os.getenv("KNOWLEDGE_GEN_MODEL", "gpt-4o"))

        # 質量評估配置
        self.quality_evaluation_enabled = os.getenv("QUALITY_EVALUATION_ENABLED", "true").lower() == "true"
        self.quality_evaluation_threshold = int(os.getenv("QUALITY_EVALUATION_THRESHOLD", "6"))

        # 目標用戶配置緩存（從資料庫動態加載）
        self._target_user_config_cache = None
        self._target_user_cache_time = None

    async def process_import_job(
        self,
        job_id: str,
        file_path: str,
        vendor_id: Optional[int],
        import_mode: str,
        enable_deduplication: bool,
        skip_review: bool = False,
        default_priority: int = 0,
        enable_quality_evaluation: bool = True,
        business_types: Optional[List[str]] = None,
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
            default_priority: 統一優先級（0=未啟用，1=已啟用）
            enable_quality_evaluation: 是否啟用質量評估（預設 True，關閉可加速大量匯入）
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
            # 1. 從資料庫獲取原始檔名（用於來源偵測）
            async with self.db_pool.acquire() as conn:
                job = await conn.fetchrow("""
                    SELECT file_name FROM unified_jobs WHERE job_id = $1
                """, uuid.UUID(job_id))
                original_filename = job['file_name'] if job else Path(file_path).name

            # 2. 更新作業狀態為處理中（uploading 階段由前端處理，後端從 extracting 開始）
            await self.update_status(job_id, "processing", progress={"current": 0, "total": 100, "stage": "extracting"})

            # 3. 偵測檔案類型並選擇解析器
            file_type = self._detect_file_type(file_path)
            print(f"📄 檔案類型: {file_type}")

            # 3. 解析檔案
            await self.update_status(job_id, "processing", progress={"current": 10, "total": 100, "stage": "extracting"})
            knowledge_list = await self._parse_file(file_path, file_type)

            if not knowledge_list:
                raise Exception("未能從檔案中提取任何知識")

            print(f"✅ 解析出 {len(knowledge_list)} 條知識")

            # 3.5 應用業態類型（如果有指定）
            if business_types and len(business_types) > 0:
                print(f"📋 套用業態類型: {business_types}")
                for knowledge in knowledge_list:
                    # 如果Excel沒有提供業態類型，則使用UI選擇的業態類型
                    if not knowledge.get('business_types'):
                        knowledge['business_types'] = business_types
                    # 如果Excel有提供業態類型，則合併（去重）
                    else:
                        combined = set(knowledge['business_types'] + business_types)
                        knowledge['business_types'] = list(combined)

            # 3.5. 偵測匯入來源類型（使用原始檔名）
            source_type, import_source = await self._detect_import_source(original_filename, file_type, knowledge_list)
            print(f"📋 來源類型: {source_type} ({import_source})")

            # ========== 特殊處理：對話記錄 → 等待確認模式 ==========
            if source_type == 'line_chat':
                print(f"💬 偵測到對話記錄，解析測試情境並等待用戶確認")
                await self.update_status(job_id, "processing", progress={"current": 80, "total": 100, "stage": "parsing"})

                # 解析出測試情境列表（但不創建）
                scenarios = await self._parse_chat_scenarios(knowledge_list, file_name=Path(file_path).name)

                # 設置為等待確認狀態
                await self.update_status(
                    job_id,
                    status="awaiting_confirmation",
                    progress={"current": 90, "total": 100},
                    result={
                        "mode": "test_scenarios_preview",
                        "total": len(scenarios),
                        "scenarios": scenarios,
                        "message": "請勾選要創建的測試情境"
                    }
                )

                print(f"✅ 對話記錄解析完成: 共 {len(scenarios)} 個測試情境待確認")
                return {
                    "mode": "test_scenarios_preview",
                    "total": len(scenarios),
                    "scenarios": scenarios
                }

            # 根據來源類型決定處理流程
            is_system_export = (import_source == 'system_export')

            # 4. 預先去重（文字完全相同）- 在 LLM 前執行，節省成本
            if enable_deduplication:
                await self.update_status(job_id, "processing", progress={"current": 20, "total": 100, "stage": "extracting"})
                original_count = len(knowledge_list)
                knowledge_list = await self._deduplicate_exact_match(knowledge_list, skip_review=skip_review, vendor_id=vendor_id)
                text_skipped = original_count - len(knowledge_list)
                print(f"🔍 文字去重: 跳過 {text_skipped} 條完全相同的項目，剩餘 {len(knowledge_list)} 條")

            # 5. 生成問題摘要（使用 LLM）- 只處理去重後的知識
            await self.update_status(job_id, "processing", progress={"current": 35, "total": 100, "stage": "extracting"})
            await self._generate_question_summaries(knowledge_list)

            # 6. 生成向量嵌入 - 只處理去重後的知識
            await self.update_status(job_id, "processing", progress={"current": 55, "total": 100, "stage": "embedding"})
            await self._generate_embeddings(knowledge_list)

            # 7. 語意去重（使用向量相似度）- 二次過濾
            if enable_deduplication:
                await self.update_status(job_id, "processing", progress={"current": 70, "total": 100, "stage": "embedding"})
                semantic_original = len(knowledge_list)
                knowledge_list = await self._deduplicate_by_similarity(knowledge_list, skip_review=skip_review, vendor_id=vendor_id)
                semantic_skipped = semantic_original - len(knowledge_list)
                print(f"🔍 語意去重: 跳過 {semantic_skipped} 條語意相似的項目，剩餘 {len(knowledge_list)} 條")
                print(f"📊 總計跳過: {text_skipped + semantic_skipped} 條（文字: {text_skipped}, 語意: {semantic_skipped}）")

            # 8. 推薦意圖（使用 LLM 或分類器）
            await self.update_status(job_id, "processing", progress={"current": 76, "total": 100, "stage": "embedding"})
            await self._recommend_intents(knowledge_list, enable_quality_evaluation=enable_quality_evaluation)

            # 8.5. 質量評估（自動篩選低質量知識）
            await self.update_status(job_id, "processing", progress={"current": 77, "total": 100, "stage": "embedding"})
            await self._evaluate_quality(knowledge_list, enable_quality_evaluation=enable_quality_evaluation)

            # 9. 建立測試情境建議（需求 2：針對 B2C 知識）
            await self.update_status(job_id, "processing", progress={"current": 78, "total": 100, "stage": "embedding"})
            test_scenario_count = await self._create_test_scenario_suggestions(knowledge_list, vendor_id)

            # 10. 根據 skip_review 參數決定匯入目標
            if skip_review:
                # 直接匯入到正式知識庫
                await self.update_status(job_id, "processing", progress={"current": 85, "total": 100, "stage": "saving"})
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
                await self.update_status(job_id, "processing", progress={"current": 85, "total": 100, "stage": "saving"})
                result = await self._import_to_review_queue(
                    knowledge_list,
                    vendor_id=vendor_id,
                    created_by=user_id,
                    source_type=source_type,
                    import_source=import_source,
                    file_name=Path(file_path).name
                )
                result['test_scenarios_created'] = test_scenario_count

            # 11. 更新作業狀態為完成（使用統一 Job 服務的方法）
            await self.update_status(
                job_id,
                status="completed",
                progress={"current": 100, "total": 100},
                result=result,
                success_records=result.get('imported', 0),
                failed_records=result.get('errors', 0),
                skipped_records=result.get('skipped', 0)
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
            # 更新作業狀態為失敗（使用統一 Job 服務的方法）
            error_message = str(e)
            print(f"\n❌ 匯入失敗: {error_message}")
            await self.update_status(
                job_id,
                status="failed",
                error_message=error_message
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

    async def _detect_import_source(
        self,
        original_filename: str,
        file_type: str,
        knowledge_list: List[Dict]
    ) -> Tuple[str, str]:
        """
        偵測匯入來源類型

        Args:
            original_filename: 原始檔案名稱（非臨時路徑）
            file_type: 檔案類型（excel, csv, json, txt, pdf）
            knowledge_list: 解析後的知識列表

        Returns:
            (source_type, import_source) tuple:
            - source_type: 'ai_generated' | 'spec_import' | 'external_file' | 'line_chat'
            - import_source: 'system_export' | 'external_excel' | 'external_json' | 'spec_docx' | 'spec_pdf' | 'line_chat_txt'
        """
        file_name = original_filename.lower()

        # 1. 檢查是否為系統匯出檔案
        if file_type == 'excel' and knowledge_list:
            # 系統匯出檔案有特定的欄位結構（9 個固定欄位）
            expected_fields = {
                'question_summary', 'answer', 'scope', 'vendor_id',
                'business_types', 'target_user', 'intent_names',
                'keywords', 'priority'
            }
            first_item_fields = set(knowledge_list[0].keys())

            # 如果包含所有預期欄位，判定為系統匯出
            if expected_fields.issubset(first_item_fields):
                print("🔍 偵測到系統匯出檔案（包含 9 個標準欄位）")
                return ('external_file', 'system_export')

        # 2. 檢查是否為對話記錄
        # LINE 對話記錄的主要目的是提取測試情境，而不是提取知識
        if file_type == 'txt' and ('聊天' in file_name or 'chat' in file_name.lower()):
            print("🔍 偵測到對話記錄檔案")
            return ('line_chat', 'line_chat_txt')

        # 3. 檢查是否為規格書
        if file_type == 'pdf' or '規格' in file_name or 'spec' in file_name or 'specification' in file_name:
            if file_type == 'pdf':
                print("🔍 偵測到規格書 PDF 檔案")
                return ('spec_import', 'spec_pdf')
            else:
                print("🔍 偵測到規格書 Word 檔案")
                return ('spec_import', 'spec_docx')

        # 4. 其他外部檔案
        if file_type == 'excel':
            print("🔍 偵測到外部 Excel 檔案")
            return ('external_file', 'external_excel')
        elif file_type == 'json':
            print("🔍 偵測到外部 JSON 檔案")
            return ('external_file', 'external_json')
        elif file_type == 'csv':
            print("🔍 偵測到外部 CSV 檔案")
            return ('external_file', 'external_csv')
        else:
            print(f"🔍 偵測到未知類型檔案（{file_type}），預設為外部檔案")
            return ('external_file', 'external_unknown')

    async def _load_target_user_config(self) -> Dict[str, str]:
        """
        從資料庫加載目標用戶配置

        Returns:
            映射字典 {中文顯示名稱/英文值: 英文值}
            例如: {'租客': 'tenant', 'tenant': 'tenant', '房東': 'landlord', ...}
        """
        # 使用 5 分鐘緩存
        if self._target_user_config_cache is not None:
            if self._target_user_cache_time is not None:
                cache_age = time.time() - self._target_user_cache_time
                if cache_age < 300:  # 5 分鐘內使用緩存
                    return self._target_user_config_cache

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_value, display_name
                    FROM target_user_config
                    WHERE is_active = true
                    ORDER BY id
                """)

                # 建立雙向映射（中文 -> 英文，英文 -> 英文）
                mapping = {}
                for row in rows:
                    user_value = row['user_value']
                    display_name = row['display_name']

                    # 英文值對應自己
                    mapping[user_value.lower()] = user_value

                    # 中文顯示名稱對應英文值
                    if display_name:
                        mapping[display_name.lower()] = user_value

                # 更新緩存
                self._target_user_config_cache = mapping
                self._target_user_cache_time = time.time()

                print(f"✅ 已加載 {len(rows)} 個目標用戶配置")
                return mapping

        except Exception as e:
            print(f"⚠️  加載目標用戶配置失敗: {e}")
            # 返回最小默認配置
            return {
                'tenant': 'tenant',
                '租客': 'tenant',
                'landlord': 'landlord',
                '房東': 'landlord',
                'property_manager': 'property_manager',
                '物業管理師': 'property_manager',
                'system_admin': 'system_admin',
                '系統管理員': 'system_admin',
            }

    async def _normalize_target_user(self, audience: str) -> str:
        """
        將中文或英文 audience 轉換為標準的英文 target_user 值

        從資料庫 target_user_config 表動態加載配置
        支援中文顯示名稱（如「租客」）和英文值（如「tenant」）

        Args:
            audience: 中文或英文的對象描述

        Returns:
            標準化的英文值（從資料庫 target_user_config.user_value 取得）
        """
        if not audience:
            return 'tenant'  # 默認值

        # 從資料庫加載配置（帶緩存）
        mapping = await self._load_target_user_config()

        # 轉換為小寫並去除空白
        key = audience.strip().lower()

        # 查找映射
        if key in mapping:
            return mapping[key]

        # 如果沒有匹配，默認返回 tenant
        print(f"   ⚠️  未知的目標用戶值: {audience}，使用默認值 tenant")
        return 'tenant'

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
        1. 一般格式：第 1 行為標題
           - 欄位: 問題 / question / 問題摘要
           - 欄位: 答案 / answer / 回覆
        2. 租管業格式：第 1 行為業者標籤（物業 | 業者名稱），第 2 行為標題
           - 第 1 行: 物業 | xxx
           - 第 2 行: 問題 | 回答 | ...

        Args:
            file_path: Excel 檔案路徑

        Returns:
            知識列表
        """
        print(f"📖 解析 Excel 檔案: {file_path}")

        # 先讀取第一行，檢查是否為租管業格式
        df_first_row = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=1)

        has_vendor_label = False
        vendor_label = None
        if pd.notna(df_first_row.iloc[0, 0]) and '物業' in str(df_first_row.iloc[0, 0]):
            has_vendor_label = True
            if pd.notna(df_first_row.iloc[0, 1]):
                vendor_label = str(df_first_row.iloc[0, 1]).strip()
            print(f"   🏢 偵測到租管業格式（業者: {vendor_label}）")

        # 根據格式選擇 header 行
        if has_vendor_label:
            df = pd.read_excel(file_path, engine='openpyxl', header=1)  # 第 2 行作為標題
        else:
            df = pd.read_excel(file_path, engine='openpyxl')  # 第 1 行作為標題

        print(f"   讀取 {len(df)} 行資料")
        print(f"   欄位: {list(df.columns)}")

        # 欄位映射（支援多種欄位名稱）
        id_cols = ['id', 'ID', '知識ID', 'knowledge_id']  # ID 欄位（用於更新）
        question_cols = ['問題', 'question', '問題摘要', 'question_summary', 'title', '標題', '租客常問Q', '租客常問Q', '常問問題']
        answer_cols = ['答案', 'answer', '回答', '回覆', 'response', 'content', '內容', '企業希望的標準A', '標準A', '標準答案']
        audience_cols = ['對象', 'audience', '受眾']
        keywords_cols = ['關鍵字', 'keywords', '標籤', 'tags']
        intent_cols = ['意圖', 'intent', 'intent_names', '分類', 'category', '分類別', '分類別 (可自訂分類)']  # 新增：意圖欄位（支援 intent_names）
        subcategory_cols = ['次分類', 'subcategory', '次類別', '次類別 (可自訂分類)']  # 新增：次分類欄位
        business_type_cols = ['業態類型', 'business_type', 'business_types', '業態', '行業類型']  # 新增：業態類型欄位

        # 找到對應的欄位
        id_col = next((col for col in df.columns if col in id_cols), None)  # ID 欄位（可選）
        question_col = next((col for col in df.columns if col in question_cols), None)
        answer_col = next((col for col in df.columns if col in answer_cols), None)
        audience_col = next((col for col in df.columns if col in audience_cols), None)
        keywords_col = next((col for col in df.columns if col in keywords_cols), None)
        intent_col = next((col for col in df.columns if col in intent_cols), None)  # 新增
        subcategory_col = next((col for col in df.columns if col in subcategory_cols), None)  # 新增
        business_type_col = next((col for col in df.columns if col in business_type_cols), None)  # 新增

        # 頻率欄位（租管業格式：可能包含換行符）
        frequency_col = next((col for col in df.columns if '頻率' in col or 'frequency' in col.lower()), None)

        if not answer_col:
            raise Exception(f"找不到答案欄位。支援的欄位名稱: {', '.join(answer_cols)}")

        knowledge_list = []

        for idx, row in df.iterrows():
            # 解析 ID（可選，用於更新現有知識）
            knowledge_id = None
            if id_col and pd.notna(row[id_col]):
                try:
                    knowledge_id = int(row[id_col])
                except (ValueError, TypeError):
                    pass  # ID 無效，視為新增

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

            # 解析對象（轉換為標準英文 target_user）
            audience = 'tenant'  # 預設英文值
            if audience_col and pd.notna(row[audience_col]):
                audience = str(row[audience_col]).strip()
                audience = await self._normalize_target_user(audience)
            else:
                audience = await self._normalize_target_user(audience)

            # 解析關鍵字
            keywords = []
            if keywords_col and pd.notna(row[keywords_col]):
                keywords_str = str(row[keywords_col])
                keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]

            # 解析意圖（如果 Excel 有提供）
            intent = None
            if intent_col and pd.notna(row[intent_col]):
                intent = str(row[intent_col]).strip()

            # 解析次分類（可作為 keywords）
            if subcategory_col and pd.notna(row[subcategory_col]):
                subcategory = str(row[subcategory_col]).strip()
                if subcategory and subcategory not in keywords:
                    keywords.append(subcategory)

            # 解析業態類型（支援逗號分隔多個業態）
            business_types = []
            if business_type_col and pd.notna(row[business_type_col]):
                business_types_str = str(row[business_type_col])
                business_types = [bt.strip() for bt in business_types_str.split(',') if bt.strip()]

            knowledge_list.append({
                'id': knowledge_id,  # ID（用於更新，None 表示新增）
                'question_summary': question,  # 可能為 None，後續用 LLM 生成
                'answer': answer,
                'target_user': audience,  # 使用標準化的英文值
                'keywords': keywords,
                'intent': intent,  # 新增：來自 Excel 的意圖
                'business_types': business_types,  # 新增：來自 Excel 的業態類型
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
        audience_cols = ['對象', 'audience', '受眾', 'target_user']
        keywords_cols = ['關鍵字', 'keywords', '標籤', 'tags']
        intent_id_cols = ['意圖ID', 'intent_id', 'intent', '意圖']

        # 找到對應的欄位
        question_col = next((col for col in df.columns if col in question_cols), None)
        answer_col = next((col for col in df.columns if col in answer_cols), None)
        audience_col = next((col for col in df.columns if col in audience_cols), None)
        keywords_col = next((col for col in df.columns if col in keywords_cols), None)
        intent_id_col = next((col for col in df.columns if col in intent_id_cols), None)

        # 如果找不到標準欄位名稱，嘗試使用位置推測
        # help_datas.csv 格式: title, title.1, content (問題, 答案)
        if not answer_col and len(df.columns) >= 2:
            # 檢查是否為 help_datas.csv 格式（最後一欄通常是答案）
            if 'content' in df.columns:
                question_col = df.columns[0] if len(df.columns) > 1 else None  # 第一欄：問題
                answer_col = 'content'        # 答案欄
                print(f"   偵測到特殊格式 CSV，使用欄位: {question_col}, {answer_col}")

        if not answer_col:
            raise Exception(f"找不到答案欄位。支援的欄位名稱: {', '.join(answer_cols)}\n實際欄位: {list(df.columns)}")

        knowledge_list = []

        for idx, row in df.iterrows():
            try:
                # === 1. 解析問題（支援 JSON 格式） ===
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

                # === 5. 解析對象（轉換為標準英文 target_user） ===
                audience = 'tenant'  # 預設英文值
                if audience_col and pd.notna(row[audience_col]):
                    audience = str(row[audience_col]).strip()
                    audience = await self._normalize_target_user(audience)
                else:
                    audience = await self._normalize_target_user(audience)

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
                    'target_user': audience,  # 使用標準化的英文值
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

        支援智能分段處理：
        - < 50KB: 完整處理
        - 50KB - 200KB: 單次處理（取前 40,000 字元）
        - > 200KB: 分段處理（每段 40,000 字元，重疊 2,000）

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

        # 智能選擇處理策略
        file_size = len(content)
        file_size_kb = file_size / 1024

        print(f"   檔案大小: {file_size_kb:.1f} KB")

        # 策略選擇
        if file_size > 200000:  # 大於 200KB
            print(f"   📊 採用分段處理策略（檔案較大）")
            return await self._parse_txt_with_chunking(file_path, content)

        elif file_size > 50000:  # 50KB - 200KB
            print(f"   📊 採用單次處理策略（取前 40,000 字元）")
            content_to_process = content[:40000]  # gpt-4o 可以處理
            max_tokens = 4000

        else:  # 小於 50KB
            print(f"   📊 採用完整處理策略（檔案較小）")
            content_to_process = content
            max_tokens = 4000

        # 使用 LLM 提取知識（帶重試機制）
        print("🤖 使用 LLM 提取知識...")

        max_retries = 3
        for retry in range(max_retries):
            try:
                llm_result = await self.llm_provider.async_chat_completion(
                    model=self.llm_model,
                    temperature=0,  # 改為 0，確保一致性
                    max_tokens=max_tokens,  # 動態設定
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self._get_extraction_prompt()},
                        {"role": "user", "content": f"請從以下內容提取知識：\n\n{content_to_process}"}
                    ]
                )

                result = json.loads(llm_result['content'])
                knowledge_list = result.get('knowledge_list', [])
                break  # 成功則跳出

            except Exception as e:
                error_str = str(e)
                if 'rate_limit' in error_str.lower() or '429' in error_str:
                    wait_time = 10 * (retry + 1)
                    if retry < max_retries - 1:
                        print(f"   ⚠️ 速率限制，{wait_time}秒後重試 ({retry + 1}/{max_retries})...")
                        import asyncio
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"   ❌ LLM 提取失敗（已重試{max_retries}次）: {e}")
                        raise Exception(f"無法從文字檔案提取知識: {e}")
                else:
                    print(f"   ⚠️ LLM 提取失敗: {e}")
                    raise Exception(f"無法從文字檔案提取知識: {e}")

        try:

            # 調試：顯示 LLM 解析的完整內容
            print(f"\n📋 LLM 解析結果:")
            for idx, k in enumerate(knowledge_list, 1):
                print(f"   {idx}. 問題: {k.get('question_summary', '未提供')}")
                print(f"      答案: {k.get('answer', '未提供')[:50]}...")
                if k.get('warnings'):
                    print(f"      警告: {', '.join(k['warnings'])}")

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

    def _get_extraction_prompt(self) -> str:
        """
        獲取知識提取的 system prompt（統一管理）

        Returns:
            system prompt 內容
        """
        return """你是一個專業的知識庫分析師。
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
      "target_user": "tenant|landlord|property_manager",
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
- target_user 必須使用英文值（tenant=租客, landlord=房東, property_manager=管理師）
- warnings 為選填，沒有警告可省略
"""

    def _deduplicate_knowledge(self, knowledge_list: List[Dict]) -> List[Dict]:
        """
        知識去重（基於 question_summary）

        Args:
            knowledge_list: 知識列表

        Returns:
            去重後的知識列表
        """
        seen_questions = set()
        unique_knowledge = []

        for knowledge in knowledge_list:
            question = knowledge.get('question_summary', '')

            # 基於問題摘要去重
            if question and question not in seen_questions:
                seen_questions.add(question)
                unique_knowledge.append(knowledge)
            else:
                print(f"   ⏭️ 跳過重複問題: {question}")

        return unique_knowledge

    async def _parse_txt_with_chunking(self, file_path: str, content: str) -> List[Dict]:
        """
        分段解析長文本（用於超過 200KB 的對話記錄）

        Args:
            file_path: 檔案路徑
            content: 完整文字內容

        Returns:
            知識列表
        """
        print(f"📄 檔案較大 ({len(content)} 字元)，採用分段處理...")

        # 配置（使用 gpt-4o，上下文限制：128000 tokens）
        # system_prompt ≈ 800 tokens, max_tokens=4000
        # 可用輸入 tokens: 128000 - 800 - 4000 = 123200 tokens
        # 中文 1 字 ≈ 2 tokens，所以: 123200 / 2 ≈ 61600 字元
        # 保守設定為 40000 字元（足夠安全）
        chunk_size = 40000  # 每段 40,000 字元（≈80,000 tokens）
        overlap = 2000      # 重疊 2,000 字元，避免切斷上下文

        # 分段
        chunks = []
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if len(chunk) > 1000:  # 忽略過短的片段
                chunks.append(chunk)

        print(f"   分為 {len(chunks)} 段處理")

        # 逐段提取知識
        all_knowledge = []
        for idx, chunk in enumerate(chunks, 1):
            print(f"   處理第 {idx}/{len(chunks)} 段...")

            # 速率限制重試機制
            max_retries = 3
            for retry in range(max_retries):
                try:
                    llm_result = await self.llm_provider.async_chat_completion(
                        model=self.llm_model,
                        temperature=0,  # 確保一致性
                        max_tokens=4000,  # 提高到 4000
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": self._get_extraction_prompt()},
                            {"role": "user", "content": f"請從以下內容提取知識：\n\n{chunk}"}
                        ]
                    )

                    result = json.loads(llm_result['content'])
                    knowledge_list = result.get('knowledge_list', [])

                    print(f"      提取 {len(knowledge_list)} 個知識")
                    all_knowledge.extend(knowledge_list)

                    # 成功後添加小延遲，避免速率限制
                    if idx < len(chunks):
                        import asyncio
                        await asyncio.sleep(2)

                    break  # 成功則跳出重試循環

                except Exception as e:
                    error_str = str(e)
                    if 'rate_limit' in error_str.lower() or '429' in error_str:
                        # 速率限制錯誤，等待後重試
                        wait_time = 10 * (retry + 1)  # 遞增等待時間
                        if retry < max_retries - 1:
                            print(f"      ⚠️ 速率限制，{wait_time}秒後重試 ({retry + 1}/{max_retries})...")
                            import asyncio
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"      ❌ 第 {idx} 段提取失敗（已重試{max_retries}次）: {e}")
                    else:
                        # 其他錯誤，不重試
                        print(f"      ⚠️ 第 {idx} 段提取失敗: {e}")
                        break

        # 去重（基於 question_summary）
        unique_knowledge = self._deduplicate_knowledge(all_knowledge)

        print(f"✅ 共提取 {len(all_knowledge)} 個知識，去重後 {len(unique_knowledge)} 個")

        # 添加來源資訊
        for knowledge in unique_knowledge:
            knowledge['source_file'] = Path(file_path).name

        return unique_knowledge

    async def _parse_json(self, file_path: str) -> List[Dict]:
        """
        解析 JSON 檔案

        預期格式：
        {
          "knowledge": [
            {
              "question": "問題",
              "answer": "答案",
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

            # 獲取並標準化 target_user
            raw_audience = item.get('audience') or item.get('target_user') or 'tenant'
            normalized_target_user = await self._normalize_target_user(raw_audience)

            knowledge_list.append({
                'question_summary': question,
                'answer': str(answer).strip(),
                'target_user': normalized_target_user,  # 使用標準化的英文值
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

答案：{knowledge['answer'][:200]}

只輸出問題摘要，不要加其他說明。"""

                llm_result = await self.llm_provider.async_chat_completion(
                    model=self.llm_model,
                    temperature=0.3,
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                )

                question_summary = llm_result['content'].strip()
                knowledge['question_summary'] = question_summary

                # 避免 rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"   ⚠️ 生成問題失敗: {e}")
                # 備用方案：保持 question_summary 為 None，後續處理

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
                # 只使用 question_summary（不包含 answer）
                # 根據實測：加入 answer 會降低 9.2% 的檢索匹配度（30 題測試，86.7% 受負面影響）
                # 原因：answer 包含的格式化內容、操作步驟會稀釋語意
                text = knowledge['question_summary']

                embedding = await self.llm_provider.async_embedding(
                    text=text,
                    model=self.embedding_model
                )

                knowledge['embedding'] = embedding

                if idx % 10 == 0:
                    print(f"   進度: {idx}/{len(knowledge_list)}")

                # 避免 rate limit
                await asyncio.sleep(0.05)

            except Exception as e:
                print(f"   ⚠️ 生成向量失敗 (第 {idx} 條): {e}")
                raise Exception(f"向量生成失敗: {e}")

        print(f"   ✅ 向量嵌入生成完成")

    async def _deduplicate_exact_match(self, knowledge_list: List[Dict], skip_review: bool = False, vendor_id: Optional[int] = None) -> List[Dict]:
        """
        去除文字完全相同的知識（精確匹配）
        在 LLM 前執行，節省 OpenAI token 成本

        Args:
            knowledge_list: 知識列表
            skip_review: 是否跳過審核（如果 True，只檢查正式知識庫；如果 False，同時檢查審核佇列）
            vendor_id: 業者 ID（限制檢查範圍在同一業者內）

        Returns:
            去重後的知識列表
        """
        check_scope = "正式知識庫" if skip_review else "正式知識庫 + 審核佇列 + 測試情境"
        vendor_scope = f"業者 {vendor_id}" if vendor_id else "通用知識"
        print(f"🔍 執行文字去重（精確匹配，範圍: {check_scope}，{vendor_scope}）...")

        async with self.db_pool.acquire() as conn:
            unique_list = []

            for knowledge in knowledge_list:
                # 根據 skip_review 決定檢查範圍
                if skip_review:
                    # 跳過審核模式：只檢查正式知識庫（用戶想要直接覆蓋審核佇列中的資料）
                    if vendor_id is not None:
                        exists = await conn.fetchval("""
                            SELECT COUNT(*) FROM knowledge_base
                            WHERE question_summary = $1 AND answer = $2 AND vendor_ids && ARRAY[$3]::int[]
                        """, knowledge.get('question_summary'), knowledge['answer'], vendor_id)
                    else:
                        exists = await conn.fetchval("""
                            SELECT COUNT(*) FROM knowledge_base
                            WHERE question_summary = $1 AND answer = $2 AND array_length(vendor_ids, 1) IS NULL
                        """, knowledge.get('question_summary'), knowledge['answer'])
                else:
                    # 審核模式：檢查正式知識庫、審核佇列和測試情境（避免重複送審）
                    if vendor_id is not None:
                        exists = await conn.fetchval("""
                            SELECT COUNT(*) FROM (
                                SELECT 1 FROM knowledge_base
                                WHERE question_summary = $1 AND answer = $2 AND vendor_ids && ARRAY[$3]::int[]
                                UNION ALL
                                SELECT 1 FROM ai_generated_knowledge_candidates
                                WHERE question = $1 AND generated_answer = $2 AND vendor_id = $3
                                UNION ALL
                                SELECT 1 FROM test_scenarios
                                WHERE test_question = $1 AND vendor_id = $3
                                AND status IN ('approved', 'in_testing')
                            ) AS combined
                        """, knowledge.get('question_summary'), knowledge['answer'], vendor_id)
                    else:
                        exists = await conn.fetchval("""
                            SELECT COUNT(*) FROM (
                                SELECT 1 FROM knowledge_base
                                WHERE question_summary = $1 AND answer = $2 AND array_length(vendor_ids, 1) IS NULL
                                UNION ALL
                                SELECT 1 FROM ai_generated_knowledge_candidates
                                WHERE question = $1 AND generated_answer = $2 AND vendor_id IS NULL
                                UNION ALL
                                SELECT 1 FROM test_scenarios
                                WHERE test_question = $1 AND vendor_id IS NULL
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
        threshold: float = 0.85,
        skip_review: bool = False,
        vendor_id: Optional[int] = None
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
            skip_review: 是否跳過審核（如果 True，只檢查正式知識庫；如果 False，同時檢查審核佇列）

        Returns:
            去重後的知識列表
        """
        check_scope = "正式知識庫" if skip_review else "正式知識庫 + 審核佇列 + 測試情境"
        print(f"🔍 執行語意去重（相似度閾值: {threshold}，範圍: {check_scope}）...")

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

                # 根據 skip_review 決定檢查範圍
                if skip_review:
                    # 跳過審核模式：只檢查正式知識庫
                    is_duplicate = result and result['exists_in_knowledge_base']
                else:
                    # 審核模式：檢查正式知識庫、審核佇列和測試情境
                    is_duplicate = result and (result['exists_in_knowledge_base'] or result['exists_in_review_queue'] or result.get('exists_in_test_scenarios', False))

                if is_duplicate:
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

    async def _recommend_intents(self, knowledge_list: List[Dict], enable_quality_evaluation: bool = True):
        """
        為知識推薦合適的意圖

        使用 LLM 根據問題和答案內容推薦最合適的意圖
        如果 Excel 已經提供意圖，則直接使用，不調用 LLM

        Args:
            knowledge_list: 知識列表（會直接修改）
            enable_quality_evaluation: 是否啟用質量評估（False 時跳過 LLM 推薦，僅處理 Excel 提供的意圖）
        """
        if not enable_quality_evaluation:
            print(f"🎯 意圖推薦: 已關閉質量評估，僅處理 Excel 提供的意圖（跳過 LLM 推薦）")
        else:
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

        # 建立意圖名稱到 ID 的映射（用於 Excel 提供的意圖名稱）
        intent_name_to_id = {intent['name']: intent['id'] for intent in intents}

        # 建立模糊匹配映射（支援部分匹配）
        # 例如：Excel 的「帳務」可以匹配到「帳務查詢」
        intent_fuzzy_match = {}
        for intent in intents:
            # 完整名稱作為 key
            intent_fuzzy_match[intent['name']] = intent['id']
            # 如果名稱包含「/」，分割後的每個部分也可以匹配
            if '/' in intent['name']:
                for part in intent['name'].split('/'):
                    part = part.strip()
                    if part and part not in intent_fuzzy_match:
                        intent_fuzzy_match[part] = intent['id']

        # 2. 處理每條知識
        for idx, knowledge in enumerate(knowledge_list, 1):
            # 如果 Excel 已提供意圖，直接使用
            if knowledge.get('intent'):
                excel_intent = knowledge['intent']

                # 1) 嘗試精確匹配
                matched_id = intent_name_to_id.get(excel_intent)
                match_type = "精確匹配"

                # 2) 如果精確匹配失敗，嘗試模糊匹配（查找包含該關鍵字的意圖）
                if not matched_id:
                    for intent in intents:
                        # 如果資料庫意圖名稱包含 Excel 的分類，或反之
                        if excel_intent in intent['name'] or intent['name'].startswith(excel_intent):
                            matched_id = intent['id']
                            match_type = "模糊匹配"
                            break

                # 3) 如果還是沒有匹配，檢查部分匹配
                if not matched_id and excel_intent in intent_fuzzy_match:
                    matched_id = intent_fuzzy_match[excel_intent]
                    match_type = "部分匹配"

                knowledge['recommended_intent'] = {
                    'intent_id': matched_id,
                    'intent_name': excel_intent,
                    'confidence': 1.0 if matched_id else 0.5,  # 有匹配到 ID 時信心度 100%
                    'reasoning': f'來自 Excel 分類別欄位: {excel_intent}（{match_type}）' if matched_id else f'來自 Excel 分類別欄位: {excel_intent}（未匹配到資料庫意圖）'
                }
                if idx <= 3:  # 只顯示前 3 條
                    match_status = f"{match_type}→ID:{matched_id}" if matched_id else "未匹配"
                    print(f"   ✅ {knowledge['question_summary'][:40]}... → {excel_intent} ({match_status})")
                continue

            # 沒有意圖，需要 LLM 推薦
            # 🛡️ 如果關閉質量評估，跳過 LLM 推薦
            if not enable_quality_evaluation:
                # 設置空的推薦（稍後可在審核時手動設定）
                knowledge['recommended_intent'] = {
                    'intent_id': None,
                    'intent_name': None,
                    'confidence': 0.0,
                    'reasoning': '已關閉質量評估，跳過自動推薦'
                }
                if idx <= 3:
                    print(f"   ⏭️  {knowledge['question_summary'][:40]}... → 跳過 LLM 推薦")
                continue

            # 啟用質量評估時，使用 LLM 推薦意圖
            try:
                prompt = f"""請根據以下問答內容，從意圖清單中選擇最合適的意圖。

問題：{knowledge['question_summary']}
答案：{knowledge['answer'][:200]}


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

                llm_result = await self.llm_provider.async_chat_completion(
                    model=self.llm_model,
                    temperature=0.3,
                    max_tokens=500,  # 意圖推薦只需小量輸出
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                result = json.loads(llm_result['content'])

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

        # 統計推薦結果
        excel_intent_count = sum(1 for k in knowledge_list if k.get('intent'))
        llm_recommended_count = len(knowledge_list) - excel_intent_count

        print(f"   ✅ 意圖推薦完成")
        if excel_intent_count > 0:
            print(f"      來自 Excel: {excel_intent_count} 條")
        if llm_recommended_count > 0:
            print(f"      LLM 推薦: {llm_recommended_count} 條")

    async def _evaluate_quality(self, knowledge_list: List[Dict], enable_quality_evaluation: bool = True):
        """
        評估知識答案的質量

        使用 LLM 評估答案是否有實用價值，避免空泛、循環邏輯或無意義的內容
        評估結果儲存到 knowledge['quality_evaluation']

        Args:
            knowledge_list: 知識列表（會直接修改）
            enable_quality_evaluation: 是否啟用質量評估（預設 True，關閉可加速大量匯入）
        """
        # 檢查是否啟用質量評估（API 參數優先於環境變數）
        if not enable_quality_evaluation or not self.quality_evaluation_enabled:
            reason = "API 參數關閉" if not enable_quality_evaluation else "環境變數停用 (QUALITY_EVALUATION_ENABLED=false)"
            print(f"⏭️  質量評估已停用（{reason}）")
            # 所有知識預設為可接受
            for knowledge in knowledge_list:
                knowledge['quality_evaluation'] = {
                    'quality_score': 8,
                    'is_acceptable': True,
                    'issues': [],
                    'reasoning': f'質量評估已停用（{reason}），預設為可接受'
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

                llm_result = await self.llm_provider.async_chat_completion(
                    model=self.llm_model,
                    temperature=0.3,
                    max_tokens=500,  # 質量評估只需小量輸出
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                result = json.loads(llm_result['content'])

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
                WHERE vendor_ids && ARRAY[$1]::int[]
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

                    # 準備 target_user（knowledge_base 使用陣列，需要轉換）
                    target_user_value = knowledge.get('target_user', 'tenant')
                    target_user_array = [target_user_value] if target_user_value else ['tenant']

                    # 從 recommended_intent 取得意圖 ID
                    intent_id = None
                    recommended_intent = knowledge.get('recommended_intent')
                    if recommended_intent:
                        intent_id = recommended_intent.get('intent_id')

                    if intent_id is None:  # 使用 is None 而不是 not
                        intent_id = default_intent_id

                    # 取得業態類型（如果有）
                    business_types = knowledge.get('business_types', [])

                    # 🔧 UPSERT 邏輯：檢查是否有 ID（用於更新）
                    knowledge_id = knowledge.get('id')

                    if knowledge_id:
                        # 檢查 ID 是否存在
                        exists = await conn.fetchval(
                            "SELECT EXISTS(SELECT 1 FROM knowledge_base WHERE id = $1)",
                            knowledge_id
                        )

                        if exists:
                            # 更新現有知識
                            await conn.execute("""
                                UPDATE knowledge_base SET
                                    vendor_ids = $1,
                                    question_summary = $2,
                                    answer = $3,
                                    keywords = $4,
                                    business_types = $5,
                                    target_user = $6,
                                    source_file = $7,
                                    source_date = $8,
                                    embedding = $9::vector,
                                    scope = $10,
                                    priority = $11,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = $12
                            """,
                                [vendor_id] if vendor_id is not None else [],
                                knowledge['question_summary'],
                                knowledge['answer'],
                                knowledge['keywords'],
                                business_types,
                                target_user_array,
                                knowledge['source_file'],
                                datetime.now().date(),
                                embedding_str,
                                'global' if not vendor_id else 'vendor',
                                default_priority,
                                knowledge_id
                            )

                            # 更新意圖映射
                            if intent_id:
                                await conn.execute("""
                                    INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, confidence, assigned_by)
                                    VALUES ($1, $2, 'primary', 1.0, 'import')
                                    ON CONFLICT (knowledge_id, intent_id)
                                    DO UPDATE SET intent_type = 'primary', confidence = 1.0, updated_at = CURRENT_TIMESTAMP
                                """, knowledge_id, intent_id)

                            print(f"   ✏️  更新知識 ID: {knowledge_id}")
                        else:
                            # ID 不存在，新增（忽略提供的 ID，使用自動生成）
                            new_id = await conn.fetchval("""
                                INSERT INTO knowledge_base (
                                    vendor_ids,
                                    question_summary,
                                    answer,
                                    keywords,
                                    business_types,
                                    target_user,
                                    source_file,
                                    source_date,
                                    embedding,
                                    scope,
                                    priority,
                                    created_at,
                                    updated_at
                                ) VALUES (
                                    $1, $2, $3, $4, $5, $6, $7, $8, $9::vector, $10, $11,
                                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                                )
                                RETURNING id
                            """,
                                [vendor_id] if vendor_id is not None else [],
                                knowledge['question_summary'],
                                knowledge['answer'],
                                knowledge['keywords'],
                                business_types,
                                target_user_array,
                                knowledge['source_file'],
                                datetime.now().date(),
                                embedding_str,
                                'global' if not vendor_id else 'vendor',
                                default_priority
                            )

                            # 插入意圖映射
                            if intent_id:
                                await conn.execute("""
                                    INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, confidence, assigned_by)
                                    VALUES ($1, $2, 'primary', 1.0, 'import')
                                    ON CONFLICT (knowledge_id, intent_id)
                                    DO UPDATE SET intent_type = 'primary', confidence = 1.0, updated_at = CURRENT_TIMESTAMP
                                """, new_id, intent_id)

                            print(f"   ⚠️  ID {knowledge_id} 不存在，新增為新知識 (新 ID: {new_id})")
                    else:
                        # 沒有 ID，新增知識
                        new_id = await conn.fetchval("""
                            INSERT INTO knowledge_base (
                                vendor_ids,
                                question_summary,
                                answer,
                                keywords,
                                business_types,
                                target_user,
                                source_file,
                                source_date,
                                embedding,
                                scope,
                                priority,
                                created_at,
                                updated_at
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9::vector, $10, $11,
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                            RETURNING id
                        """,
                            [vendor_id] if vendor_id is not None else [],
                            knowledge['question_summary'],
                            knowledge['answer'],
                            knowledge['keywords'],
                            business_types,
                            target_user_array,
                            knowledge['source_file'],
                            datetime.now().date(),
                            embedding_str,
                            'global' if not vendor_id else 'vendor',
                            default_priority
                        )

                        # 插入意圖映射
                        if intent_id:
                            await conn.execute("""
                                INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, confidence, assigned_by)
                                VALUES ($1, $2, 'primary', 1.0, 'import')
                                ON CONFLICT (knowledge_id, intent_id)
                                DO UPDATE SET intent_type = 'primary', confidence = 1.0, updated_at = CURRENT_TIMESTAMP
                            """, new_id, intent_id)

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

        B2C 對象包括：tenant（租客）、landlord（房東）（所有外部業務範圍）

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID

        Returns:
            建立的測試情境數量
        """
        print(f"🧪 檢查 B2C 知識並建立測試情境建議...")

        # B2C 對象列表（使用英文標準值）
        b2c_target_users = ['tenant', 'landlord']

        created_count = 0

        async with self.db_pool.acquire() as conn:
            for knowledge in knowledge_list:
                target_user = knowledge.get('target_user', '').lower()

                # 檢查是否為 B2C 對象
                if target_user not in b2c_target_users:
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
                        f"導入的知識"
                    )

                    created_count += 1

                except Exception as e:
                    print(f"   ⚠️ 建立測試情境失敗: {e}")

        if created_count > 0:
            print(f"   ✅ 建立了 {created_count} 個測試情境建議")
        else:
            print(f"   ℹ️ 沒有需要建立測試情境的 B2C 知識")

        return created_count

    async def _parse_chat_scenarios(
        self,
        knowledge_list: List[Dict],
        file_name: str
    ) -> List[Dict]:
        """
        解析對話記錄中的測試情境（不創建到資料庫）

        Args:
            knowledge_list: 從對話中提取的問答列表
            file_name: 來源檔案名稱

        Returns:
            測試情境列表，每個包含 {index, question, difficulty, notes}
        """
        print(f"💬 解析 {len(knowledge_list)} 條對話為測試情境...")

        scenarios = []

        for idx, knowledge in enumerate(knowledge_list):
            question = knowledge.get('question_summary') or knowledge.get('question', '')

            if not question:
                print(f"   ⚠️ 跳過第 {idx} 條：無問題內容")
                continue

            scenarios.append({
                "index": idx,
                "question": question,
                "difficulty": "medium",  # 預設難度
                "notes": f"從對話記錄匯入: {file_name}",
                "selected": True  # 預設全選
            })

        print(f"✅ 解析完成，共 {len(scenarios)} 個測試情境")
        return scenarios

    async def _create_selected_scenarios(
        self,
        scenarios: List[Dict],
        selected_indices: List[int],
        created_by: str
    ) -> Dict:
        """
        創建用戶選中的測試情境

        Args:
            scenarios: 測試情境列表（從 _parse_chat_scenarios 返回）
            selected_indices: 用戶選中的索引列表
            created_by: 建立者

        Returns:
            創建結果統計
        """
        print(f"💬 創建 {len(selected_indices)}/{len(scenarios)} 個選中的測試情境...")

        created = 0
        skipped = 0
        errors = 0
        created_items = []

        async with self.db_pool.acquire() as conn:
            for idx in selected_indices:
                if idx < 0 or idx >= len(scenarios):
                    print(f"   ⚠️ 索引 {idx} 超出範圍，跳過")
                    errors += 1
                    continue

                scenario = scenarios[idx]
                question = scenario['question']

                try:
                    # 檢查是否已存在相同的測試問題
                    existing = await conn.fetchval("""
                        SELECT id FROM test_scenarios
                        WHERE test_question = $1
                        LIMIT 1
                    """, question)

                    if existing:
                        print(f"   ⏭️  跳過重複: {question[:30]}...")
                        skipped += 1
                        continue

                    # 創建測試情境（狀態為 approved，直接可用）
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
                        scenario.get('difficulty', 'medium'),
                        'approved',  # 用戶已確認，直接批准
                        'imported',
                        scenario.get('notes', '')
                    )

                    created += 1
                    created_items.append({
                        "id": test_scenario_id,
                        "question": question
                    })

                except Exception as e:
                    print(f"   ⚠️ 創建測試情境失敗: {e}")
                    errors += 1

        print(f"\n   ✅ 測試情境創建完成:")
        print(f"      新建: {created} 個")
        print(f"      跳過: {skipped} 個（重複）")
        print(f"      失敗: {errors} 個")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "total": len(selected_indices),
            "mode": "test_scenarios_created",
            "items": created_items
        }

    async def _import_chat_as_test_scenarios(
        self,
        knowledge_list: List[Dict],
        vendor_id: Optional[int],
        file_name: str,
        created_by: str
    ) -> Dict:
        """
        將對話記錄匯入為測試情境（模式 A：純測試情境模式）

        對話記錄不創建知識，只創建測試情境供後續測試使用

        Args:
            knowledge_list: 從對話中提取的問答列表
            vendor_id: 業者 ID
            file_name: 來源檔案名稱
            created_by: 建立者

        Returns:
            匯入結果統計
        """
        print(f"💬 將 {len(knowledge_list)} 條對話匯入為測試情境...")

        created = 0
        skipped = 0
        errors = 0
        created_items = []  # 記錄創建的測試情境

        async with self.db_pool.acquire() as conn:
            for idx, knowledge in enumerate(knowledge_list, 1):
                try:
                    question = knowledge.get('question_summary') or knowledge.get('question', '')

                    if not question:
                        print(f"   ⚠️ 跳過第 {idx} 條：無問題內容")
                        skipped += 1
                        continue

                    # 檢查是否已存在相同的測試問題
                    existing = await conn.fetchval("""
                        SELECT id FROM test_scenarios
                        WHERE test_question = $1
                        LIMIT 1
                    """, question)

                    if existing:
                        print(f"   ⏭️  跳過重複: {question[:30]}...")
                        skipped += 1
                        continue

                    # 創建測試情境（test_scenarios 表是全域的，不需要 vendor_id）
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
                        'medium',  # 預設難度
                        'pending_review',  # 待審核狀態，進入審核中心
                        'imported',  # 來源：匯入
                        f"從對話記錄匯入: {file_name}"
                    )

                    created += 1
                    created_items.append({
                        "id": test_scenario_id,
                        "question": question
                    })

                    if idx % 10 == 0:
                        print(f"   進度: {idx}/{len(knowledge_list)}")

                except Exception as e:
                    print(f"   ⚠️ 創建測試情境失敗 (第 {idx} 條): {e}")
                    errors += 1

        print(f"\n   ✅ 測試情境創建完成:")
        print(f"      總共: {len(knowledge_list)} 條對話")
        print(f"      新建: {created} 個測試情境")
        print(f"      跳過: {skipped} 個（重複）")
        if errors > 0:
            print(f"      錯誤: {errors} 個")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "total": len(knowledge_list),
            "mode": "test_scenarios_draft",  # 草稿模式
            "items": created_items,  # 創建的測試情境列表
            "message": "測試情境已創建為草稿狀態，請前往「測試情境管理」頁面審核"
        }

    async def _import_to_review_queue(
        self,
        knowledge_list: List[Dict],
        vendor_id: Optional[int],
        created_by: str,
        source_type: str = 'external_file',
        import_source: str = 'external_unknown',
        file_name: str = 'unknown'
    ) -> Dict:
        """
        將知識匯入到審核佇列（支援多種來源類型）

        知識會先進入 ai_generated_knowledge_candidates 表，
        人工審核通過後才會加入正式的 knowledge_base

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID
            created_by: 建立者
            source_type: 來源類型（'ai_generated', 'spec_import', 'external_file', 'line_chat'）
            import_source: 匯入來源（'system_export', 'external_excel', 'spec_pdf', 'line_chat_txt'等）
            file_name: 來源檔案名稱

        Returns:
            匯入結果統計
        """
        print(f"📋 將 {len(knowledge_list)} 條知識匯入審核佇列...")
        print(f"   來源類型: {source_type}")
        print(f"   匯入來源: {import_source}")

        imported = 0
        auto_rejected = 0
        errors = 0

        async with self.db_pool.acquire() as conn:
            for idx, knowledge in enumerate(knowledge_list, 1):
                try:
                    question = knowledge['question_summary']
                    answer = knowledge['answer']

                    # 1. 條件式創建測試情境（只有對話記錄需要）
                    test_scenario_id = None
                    if source_type == 'line_chat':
                        # 對話記錄 → 創建測試情境
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
                                f"從對話記錄匯入: {file_name}"
                            )
                    # 規格書/外部檔案 → 不創建測試情境（test_scenario_id = NULL）

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

                    reasoning = f"""對象: {knowledge.get('target_user', '')}, 關鍵字: {', '.join(knowledge.get('keywords', []))}

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

                    # 4. 準備新欄位資料
                    keywords = knowledge.get('keywords', [])
                    priority = knowledge.get('priority', 0)
                    scope = knowledge.get('scope', 'global')
                    business_types = knowledge.get('business_types', [])
                    target_user = knowledge.get('target_user')

                    # 5. 建立知識候選記錄（含新欄位）
                    await conn.execute("""
                        INSERT INTO ai_generated_knowledge_candidates (
                            test_scenario_id,
                            source_type,
                            import_source,
                            source_file_name,
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
                            keywords,
                            priority,
                            scope,
                            vendor_id,
                            business_types,
                            target_user,
                            status,
                            created_at,
                            updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7::vector, $8, $9, $10, $11, $12, $13, $14,
                            $15, $16, $17, $18, $19, $20, $21, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """,
                        test_scenario_id,           # $1  - NULL（規格書）或有值（對話記錄）
                        source_type,                # $2  - 'spec_import', 'external_file', 'line_chat'
                        import_source,              # $3  - 'spec_pdf', 'external_excel', 'line_chat_txt'
                        file_name,                  # $4  - 來源檔名
                        question,                   # $5
                        answer,                     # $6
                        embedding_str,              # $7  - 向量嵌入（字串格式）
                        0.85,                       # $8  - 匯入知識固定信心分數 85%
                        f"從檔案匯入: {file_name}",  # $9
                        'knowledge_import',         # $10 - 標記為知識匯入
                        reasoning,                  # $11 - 包含推薦意圖、泛化警告和質量評估
                        [file_name],                # $12 - suggested_sources
                        warnings_list,              # $13 - 泛化警告
                        intent_ids,                 # $14 - 推薦意圖 ID 陣列
                        keywords,                   # $15 - 關鍵字
                        priority,                   # $16 - 優先級
                        scope,                      # $17 - 適用範圍
                        vendor_id,                  # $18 - 廠商 ID
                        business_types,             # $19 - 業務類型
                        target_user,                # $20 - 目標用戶
                        status                      # $21 - 根據質量評估動態設定
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

    # ✅ update_job_status 方法已移除，改用父類 UnifiedJobService 的 update_status() 方法
    # 新的調用方式：
    # await self.update_status(
    #     job_id=job_id,
    #     status=status,
    #     progress=progress,
    #     result=result,
    #     error_message=error,
    #     success_records=result.get('imported'),
    #     failed_records=result.get('errors'),
    #     skipped_records=result.get('skipped')
    # )
