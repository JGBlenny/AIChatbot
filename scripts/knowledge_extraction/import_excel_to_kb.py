"""
從 Excel 文件匯入知識庫
支援已整理好的客服 QA 資料直接導入
"""

import os
import sys
import pandas as pd
import asyncpg
from datetime import datetime
from typing import List, Dict
from openai import OpenAI

# 資料庫配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "aichatbot_admin"),
    "user": os.getenv("DB_USER", "aichatbot"),
    "password": os.getenv("DB_PASSWORD", "aichatbot_password")
}


class ExcelKnowledgeImporter:
    """Excel 知識庫匯入器"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conn = None
        self.stats = {
            "total_rows": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0
        }

    async def connect_db(self):
        """連接資料庫"""
        self.conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ 資料庫已連接")

    async def close_db(self):
        """關閉資料庫連接"""
        if self.conn:
            await self.conn.close()
            print("👋 資料庫連接已關閉")

    def load_excel(self, file_path: str) -> pd.DataFrame:
        """
        載入 Excel 文件

        Args:
            file_path: Excel 文件路徑

        Returns:
            DataFrame
        """
        print(f"📖 讀取 Excel 文件: {file_path}")

        df = pd.read_excel(file_path, engine='openpyxl')

        print(f"   ✅ 讀取 {len(df)} 行資料")
        print(f"   欄位: {list(df.columns)}")

        return df

    def parse_excel_data(self, df: pd.DataFrame) -> List[Dict]:
        """
        解析 Excel 資料為知識庫格式

        格式：
        - 租客帳號問題：作為分類（category）
        - 回覆：作為答案（answer）
        - 關鍵字：作為關鍵字（keywords）
        - 對象：作為受眾（audience）

        Returns:
            List of knowledge dicts
        """
        print("\n🔄 解析資料...")

        knowledge_list = []
        current_category = None

        for idx, row in df.iterrows():
            self.stats['total_rows'] += 1

            # 解析分類（如果「租客帳號問題」欄位有值，就是新分類）
            category_val = row.get('租客帳號問題')
            if pd.notna(category_val) and category_val and isinstance(category_val, str):
                # 過濾掉非分類的描述性文字
                if not any(x in category_val for x in ['關鍵字', '回覆', '頻率']):
                    current_category = category_val.strip()

            # 解析答案
            answer = row.get('回覆')
            if pd.isna(answer) or not answer or not isinstance(answer, str):
                continue

            answer = str(answer).strip()

            # 跳過空答案或純空白
            if not answer or answer == 'NaN':
                self.stats['skipped'] += 1
                continue

            # 跳過純數字或過短的答案
            if len(answer) < 10:
                self.stats['skipped'] += 1
                continue

            # 解析其他欄位
            audience = row.get('對象')
            if pd.notna(audience):
                audience = str(audience).strip()
            else:
                audience = '租客'  # 預設對象

            keywords_str = row.get('關鍵字')
            if pd.notna(keywords_str) and keywords_str:
                keywords = [k.strip() for k in str(keywords_str).split(',') if k.strip()]
            else:
                keywords = []

            # 建立知識項目
            knowledge = {
                'category': current_category or '一般問題',
                'answer': answer,
                'audience': audience,
                'keywords': keywords,
                'source_file': os.path.basename(file_path) if 'file_path' in locals() else 'Excel',
                'source_date': datetime.now().strftime('%Y-%m-%d')
            }

            knowledge_list.append(knowledge)

        print(f"   ✅ 解析出 {len(knowledge_list)} 個知識項目")
        print(f"   跳過 {self.stats['skipped']} 個無效項目")

        return knowledge_list

    def generate_question_summary(self, answer: str, category: str) -> str:
        """
        使用 LLM 根據答案生成問題摘要

        Args:
            answer: 答案內容
            category: 分類

        Returns:
            問題摘要
        """
        try:
            prompt = f"""請根據以下答案，生成一個簡潔的問題摘要（15字以內）。

分類：{category}
答案：{answer[:200]}

只輸出問題摘要，不要加其他說明。"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=50,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            question_summary = response.choices[0].message.content.strip()
            return question_summary

        except Exception as e:
            print(f"   ⚠️  LLM 生成問題失敗: {e}")
            # 備用方案：使用分類作為問題
            return f"{category}相關問題"

    async def import_to_database(
        self,
        knowledge_list: List[Dict],
        vendor_id: int = None,
        batch_generate_questions: bool = True
    ):
        """
        匯入知識到資料庫

        Args:
            knowledge_list: 知識列表
            vendor_id: 業者 ID（可選）
            batch_generate_questions: 是否批次生成問題摘要
        """
        print(f"\n💾 開始匯入到資料庫...")

        # 查詢預設意圖 ID
        default_intent_id = await self.conn.fetchval(
            "SELECT id FROM intents WHERE name = '一般知識' OR name = '其他' LIMIT 1"
        )

        if not default_intent_id:
            print("⚠️  找不到預設意圖，請先建立意圖")
            return

        for idx, knowledge in enumerate(knowledge_list, 1):
            try:
                # 生成問題摘要
                if batch_generate_questions:
                    question_summary = self.generate_question_summary(
                        knowledge['answer'],
                        knowledge['category']
                    )
                else:
                    question_summary = knowledge['category']

                # 檢查是否已存在（簡單去重）
                exists = await self.conn.fetchval("""
                    SELECT COUNT(*) FROM knowledge_base
                    WHERE question_summary = $1 AND answer = $2
                """, question_summary, knowledge['answer'])

                if exists > 0:
                    print(f"   [{ idx}/{len(knowledge_list)}] ⏩ 已存在: {question_summary}")
                    self.stats['skipped'] += 1
                    continue

                # 生成向量嵌入（V2 架構：只用 question，keywords 獨立處理）
                # 根據實測：加入 answer 會降低 9.2% 的檢索匹配度（30 題測試，86.7% 受負面影響）
                # 原因：answer 包含的格式化內容、操作步驟會稀釋語意
                text_for_embedding = question_summary

                embedding_response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text_for_embedding
                )
                embedding = embedding_response.data[0].embedding

                # 插入資料庫
                await self.conn.execute("""
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
                        created_at,
                        updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """,
                    default_intent_id,
                    vendor_id,
                    question_summary,  # title
                    knowledge['category'],
                    question_summary,
                    knowledge['answer'],
                    knowledge['audience'],
                    knowledge['keywords'],
                    knowledge['source_file'],
                    knowledge['source_date'],
                    embedding,
                    'global' if not vendor_id else 'vendor',
                    0
                )

                print(f"   [{idx}/{len(knowledge_list)}] ✅ 已匯入: {question_summary}")
                self.stats['imported'] += 1

            except Exception as e:
                print(f"   [{idx}/{len(knowledge_list)}] ❌ 匯入失敗: {e}")
                self.stats['errors'] += 1

        print(f"\n✅ 匯入完成！")
        self.print_stats()

    def print_stats(self):
        """列印統計資訊"""
        print(f"\n{'='*60}")
        print("匯入統計")
        print(f"{'='*60}")
        print(f"總行數：{self.stats['total_rows']}")
        print(f"成功匯入：{self.stats['imported']}")
        print(f"跳過：{self.stats['skipped']}")
        print(f"錯誤：{self.stats['errors']}")
        print(f"{'='*60}\n")


async def main():
    """主程式"""
    print("="*60)
    print("Excel 知識庫匯入工具")
    print("="*60)

    # 檢查 OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        return

    # 文件路徑
    excel_file = "/Users/lenny/jgb/AIChatbot/data/5.3.4_客服_ QA, FB, 來電.xlsx"

    if not os.path.exists(excel_file):
        print(f"❌ 文件不存在: {excel_file}")
        return

    # 建立匯入器
    importer = ExcelKnowledgeImporter()

    try:
        # 連接資料庫
        await importer.connect_db()

        # 載入 Excel
        df = importer.load_excel(excel_file)

        # 解析資料
        knowledge_list = importer.parse_excel_data(df)

        if not knowledge_list:
            print("⚠️  沒有解析出任何知識項目")
            return

        # 詢問是否繼續
        print(f"\n即將匯入 {len(knowledge_list)} 個知識項目")
        print("這將會呼叫 OpenAI API 生成問題摘要和向量嵌入")

        confirm = input("\n確認繼續？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消匯入")
            return

        # 詢問業者 ID
        vendor_id_str = input("\n輸入業者 ID（留空表示通用知識）: ").strip()
        vendor_id = int(vendor_id_str) if vendor_id_str else None

        # 匯入到資料庫
        await importer.import_to_database(
            knowledge_list,
            vendor_id=vendor_id,
            batch_generate_questions=True
        )

        print("\n✅ 全部完成！")

    finally:
        # 關閉資料庫連接
        await importer.close_db()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
