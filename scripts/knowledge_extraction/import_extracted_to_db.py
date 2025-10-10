"""
從提取的 Excel 知識庫匯入資料庫
處理 extract_knowledge_and_tests.py 生成的格式
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


class ExtractedKnowledgeImporter:
    """提取的知識庫匯入器"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conn = None
        self.stats = {
            "total_rows": 0,
            "imported": 0,
            "skipped_duplicate": 0,
            "skipped_invalid": 0,
            "errors": 0
        }

    async def connect_db(self):
        """連接資料庫"""
        try:
            self.conn = await asyncpg.connect(**DB_CONFIG)
            print("✅ 資料庫已連接")
        except Exception as e:
            print(f"❌ 資料庫連接失敗: {e}")
            raise

    async def close_db(self):
        """關閉資料庫連接"""
        if self.conn:
            await self.conn.close()
            print("👋 資料庫連接已關閉")

    def load_excel(self, file_path: str) -> pd.DataFrame:
        """載入提取的 Excel 文件"""
        print(f"\n📖 讀取 Excel 文件: {file_path}")

        df = pd.read_excel(file_path, engine='openpyxl')

        print(f"   ✅ 讀取 {len(df)} 行資料")
        print(f"   欄位: {list(df.columns)}")

        return df

    def validate_row(self, row: pd.Series) -> bool:
        """驗證單行資料是否有效"""
        # 必須有 question_summary 和 answer
        if pd.isna(row.get('question_summary')) or not str(row.get('question_summary')).strip():
            return False

        if pd.isna(row.get('answer')) or not str(row.get('answer')).strip():
            return False

        # 答案長度必須 >= 10
        answer = str(row.get('answer')).strip()
        if len(answer) < 10:
            return False

        return True

    async def check_duplicate(self, question_summary: str, answer: str) -> bool:
        """檢查是否為重複知識"""
        count = await self.conn.fetchval("""
            SELECT COUNT(*) FROM knowledge_base
            WHERE question_summary = $1 OR answer = $2
        """, question_summary, answer)

        return count > 0

    def generate_embedding(self, text: str) -> List[float]:
        """生成向量嵌入"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:2000]  # 限制長度
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"   ⚠️  向量生成失敗: {e}")
            return None

    async def import_to_database(
        self,
        df: pd.DataFrame,
        vendor_id: int = None,
        enable_deduplication: bool = True
    ):
        """
        匯入知識到資料庫

        Args:
            df: 知識庫 DataFrame
            vendor_id: 業者 ID（可選）
            enable_deduplication: 是否啟用去重
        """
        print(f"\n💾 開始匯入到資料庫...")
        print(f"   去重: {'啟用' if enable_deduplication else '停用'}")
        print(f"   業者 ID: {vendor_id if vendor_id else '通用知識'}")

        # 查詢預設意圖 ID（優先使用「服務說明」或任何意圖）
        default_intent_id = await self.conn.fetchval(
            "SELECT id FROM intents WHERE name = '服務說明' OR name = '一般知識' OR name = '其他' LIMIT 1"
        )

        if not default_intent_id:
            # 如果還是找不到，就用第一個意圖
            default_intent_id = await self.conn.fetchval(
                "SELECT id FROM intents ORDER BY id LIMIT 1"
            )

        if not default_intent_id:
            print("⚠️  找不到任何意圖，請先建立意圖")
            return

        print(f"   使用意圖 ID: {default_intent_id}")

        self.stats['total_rows'] = len(df)

        for idx, row in df.iterrows():
            try:
                # 驗證資料
                if not self.validate_row(row):
                    print(f"   [{idx+1}/{len(df)}] ⏩ 跳過無效資料")
                    self.stats['skipped_invalid'] += 1
                    continue

                # 提取欄位
                title = str(row.get('title', '')).strip()
                category = str(row.get('category', '一般問題')).strip()
                question_summary = str(row.get('question_summary')).strip()
                answer = str(row.get('answer')).strip()
                audience = str(row.get('audience', '租客')).strip()

                # 處理關鍵字（可能是字串或列表）
                keywords_val = row.get('keywords', [])
                if isinstance(keywords_val, str):
                    # 嘗試解析字串格式的列表
                    import ast
                    try:
                        keywords = ast.literal_eval(keywords_val)
                    except:
                        keywords = [k.strip() for k in keywords_val.split(',') if k.strip()]
                elif isinstance(keywords_val, list):
                    keywords = keywords_val
                else:
                    keywords = []

                source_file = str(row.get('source_file', 'LINE提取')).strip()

                # 處理日期格式
                source_date_str = str(row.get('source_date', datetime.now().strftime('%Y-%m-%d'))).strip()
                try:
                    source_date = datetime.strptime(source_date_str, '%Y-%m-%d').date()
                except:
                    source_date = datetime.now().date()

                # 去重檢查
                if enable_deduplication:
                    is_duplicate = await self.check_duplicate(question_summary, answer)
                    if is_duplicate:
                        print(f"   [{idx+1}/{len(df)}] ⏩ 已存在: {question_summary[:30]}...")
                        self.stats['skipped_duplicate'] += 1
                        continue

                # 生成向量嵌入
                embedding_text = f"{title} {question_summary} {answer[:200]}"
                embedding = self.generate_embedding(embedding_text)

                if not embedding:
                    print(f"   [{idx+1}/{len(df)}] ❌ 向量生成失敗: {question_summary[:30]}...")
                    self.stats['errors'] += 1
                    continue

                # 將 embedding 轉換為 pgvector 格式字串
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'

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
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::vector, $12, $13,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """,
                    default_intent_id,
                    vendor_id,
                    title or question_summary,  # 如果沒有 title 就用 question_summary
                    category,
                    question_summary,
                    answer,
                    audience,
                    keywords,
                    source_file,
                    source_date,
                    embedding_str,  # 使用字串格式
                    'global' if not vendor_id else 'vendor',
                    0
                )

                print(f"   [{idx+1}/{len(df)}] ✅ 已匯入: {question_summary[:40]}...")
                self.stats['imported'] += 1

            except Exception as e:
                print(f"   [{idx+1}/{len(df)}] ❌ 匯入失敗: {e}")
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
        print(f"跳過（重複）：{self.stats['skipped_duplicate']}")
        print(f"跳過（無效）：{self.stats['skipped_invalid']}")
        print(f"錯誤：{self.stats['errors']}")
        print(f"{'='*60}\n")


async def main():
    """主程式"""
    print("="*60)
    print("LINE 提取知識庫匯入工具")
    print("="*60)

    # 檢查 OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        return

    # 文件路徑
    excel_file = "/Users/lenny/jgb/AIChatbot/output/knowledge_base_extracted.xlsx"

    if not os.path.exists(excel_file):
        print(f"❌ 文件不存在: {excel_file}")
        print(f"\n請先執行提取腳本：")
        print(f"python3 scripts/knowledge_extraction/extract_knowledge_and_tests.py")
        return

    # 建立匯入器
    importer = ExtractedKnowledgeImporter()

    try:
        # 連接資料庫
        await importer.connect_db()

        # 載入 Excel
        df = importer.load_excel(excel_file)

        if df.empty:
            print("⚠️  Excel 文件為空")
            return

        # 詢問是否繼續
        print(f"\n即將匯入 {len(df)} 個知識項目")
        print("這將會呼叫 OpenAI API 生成向量嵌入")
        print(f"預估成本: ${len(df) * 0.00002:.4f} USD")

        confirm = input("\n確認繼續？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消匯入")
            return

        # 詢問業者 ID
        vendor_id_str = input("\n輸入業者 ID（留空表示通用知識）: ").strip()
        vendor_id = int(vendor_id_str) if vendor_id_str else None

        # 詢問是否啟用去重
        enable_dedup = input("\n啟用智能去重？(Y/n): ").strip().lower()
        enable_deduplication = enable_dedup != 'n'

        # 匯入到資料庫
        await importer.import_to_database(
            df,
            vendor_id=vendor_id,
            enable_deduplication=enable_deduplication
        )

        print("\n✅ 全部完成！")
        print(f"\n下一步：執行回測驗證")
        print(f"python3 scripts/knowledge_extraction/backtest_framework.py")

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 關閉資料庫連接
        await importer.close_db()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
