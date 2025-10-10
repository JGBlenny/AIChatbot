"""
知識庫重新分類工具
使用 LLM 自動為現有知識匹配最合適的意圖
"""

import os
import sys
import asyncpg
from typing import List, Dict, Optional
from openai import OpenAI
import asyncio

# 資料庫配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "aichatbot_admin"),
    "user": os.getenv("DB_USER", "aichatbot"),
    "password": os.getenv("DB_PASSWORD", "aichatbot_password")
}


class KnowledgeIntentReclassifier:
    """知識意圖重新分類器"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conn = None
        self.intents = []  # 儲存所有意圖
        self.stats = {
            "total_knowledge": 0,
            "reclassified": 0,
            "unchanged": 0,
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

    async def load_intents(self):
        """載入所有可用意圖"""
        rows = await self.conn.fetch("""
            SELECT id, name, description, keywords
            FROM intents
            WHERE is_enabled = true
            ORDER BY name
        """)

        self.intents = [dict(row) for row in rows]
        print(f"\n📋 載入 {len(self.intents)} 個意圖:")
        for intent in self.intents:
            print(f"   - {intent['id']}. {intent['name']}: {intent['description'][:50] if intent['description'] else 'N/A'}...")

    def classify_intent_with_llm(self, question_summary: str, answer: str, category: str) -> Dict:
        """
        使用 LLM 分類知識的意圖

        Returns:
            {
                'intent_id': int,
                'intent_name': str,
                'confidence': float,
                'reasoning': str
            }
        """
        # 構建意圖列表文本
        intents_text = "\n".join([
            f"- ID {intent['id']}: {intent['name']} - {intent['description'] or '無描述'}"
            for intent in self.intents
        ])

        prompt = f"""你是一個知識庫分類專家。請根據以下知識內容，選擇最合適的意圖（intent）。

可用意圖列表：
{intents_text}

知識內容：
- 問題摘要: {question_summary}
- 回答: {answer[:300]}...
- 分類: {category}

請分析這個知識最適合哪個意圖，並返回 JSON 格式：
{{
    "intent_id": <意圖ID>,
    "intent_name": "<意圖名稱>",
    "confidence": <0-1之間的信心度>,
    "reasoning": "<選擇此意圖的理由>"
}}

注意：
1. 仔細分析問題和答案的核心內容
2. 優先考慮最具體、最相關的意圖
3. 如果不確定，選擇「服務說明」或「一般知識」等通用意圖
4. 信心度應該反映你對分類的確定程度
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一個知識庫分類專家，擅長理解問題意圖並進行準確分類。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = eval(response.choices[0].message.content)

            # 驗證 intent_id 是否有效
            valid_ids = [intent['id'] for intent in self.intents]
            if result['intent_id'] not in valid_ids:
                print(f"   ⚠️  LLM 返回無效的意圖 ID: {result['intent_id']}，使用默認意圖")
                # 使用「服務說明」作為默認
                default_intent = next((i for i in self.intents if i['name'] == '服務說明'), self.intents[0])
                result['intent_id'] = default_intent['id']
                result['intent_name'] = default_intent['name']
                result['confidence'] = 0.5

            return result

        except Exception as e:
            print(f"   ❌ LLM 分類失敗: {e}")
            # 返回默認意圖
            default_intent = next((i for i in self.intents if i['name'] == '服務說明'), self.intents[0])
            return {
                'intent_id': default_intent['id'],
                'intent_name': default_intent['name'],
                'confidence': 0.3,
                'reasoning': f'LLM 分類失敗，使用默認意圖: {e}'
            }

    async def reclassify_knowledge(
        self,
        filter_source_file: Optional[str] = None,
        filter_intent_id: Optional[int] = None,
        batch_size: int = 10,
        dry_run: bool = True
    ):
        """
        重新分類知識庫

        Args:
            filter_source_file: 只處理特定來源檔案的知識（如 "%LINE%"）
            filter_intent_id: 只處理特定意圖 ID 的知識
            batch_size: 批次處理數量（每 N 條顯示一次進度）
            dry_run: 是否為試運行模式（不實際更新資料庫）
        """
        print(f"\n🔄 開始重新分類知識...")
        print(f"   模式: {'試運行（不會修改資料庫）' if dry_run else '正式執行（會更新資料庫）'}")
        print(f"   批次大小: {batch_size}")

        # 構建查詢條件
        where_clauses = []
        params = []
        param_idx = 1

        if filter_source_file:
            where_clauses.append(f"source_file LIKE ${param_idx}")
            params.append(filter_source_file)
            param_idx += 1
            print(f"   篩選來源: {filter_source_file}")

        if filter_intent_id:
            where_clauses.append(f"intent_id = ${param_idx}")
            params.append(filter_intent_id)
            param_idx += 1
            print(f"   篩選意圖 ID: {filter_intent_id}")

        where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # 查詢需要重新分類的知識
        query = f"""
            SELECT id, intent_id, title, question_summary, answer, category, keywords
            FROM knowledge_base
            WHERE {where_clause}
            ORDER BY id
        """

        rows = await self.conn.fetch(query, *params)
        self.stats['total_knowledge'] = len(rows)

        print(f"\n📊 找到 {len(rows)} 條知識需要重新分類\n")

        if len(rows) == 0:
            print("⚠️  沒有符合條件的知識，結束執行")
            return

        # 逐條處理
        for idx, row in enumerate(rows, 1):
            try:
                knowledge_id = row['id']
                old_intent_id = row['intent_id']
                question_summary = row['question_summary'] or row['title'] or '無標題'
                answer = row['answer'] or '無內容'
                category = row['category'] or '未分類'

                # 使用 LLM 分類
                classification = self.classify_intent_with_llm(
                    question_summary=question_summary,
                    answer=answer,
                    category=category
                )

                new_intent_id = classification['intent_id']
                intent_name = classification['intent_name']
                confidence = classification['confidence']
                reasoning = classification['reasoning']

                # 判斷是否需要更新
                if old_intent_id != new_intent_id:
                    status = "🔄 重新分類"
                    self.stats['reclassified'] += 1

                    # 如果不是試運行，更新資料庫
                    if not dry_run:
                        await self.conn.execute("""
                            UPDATE knowledge_base
                            SET intent_id = $1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = $2
                        """, new_intent_id, knowledge_id)
                else:
                    status = "✅ 無需變更"
                    self.stats['unchanged'] += 1

                # 顯示進度
                if idx % batch_size == 0 or idx == len(rows):
                    print(f"[{idx}/{len(rows)}] {status}")
                    print(f"   ID: {knowledge_id}")
                    print(f"   問題: {question_summary[:50]}...")
                    print(f"   舊意圖: {old_intent_id} → 新意圖: {new_intent_id} ({intent_name})")
                    print(f"   信心度: {confidence:.2f}")
                    print(f"   理由: {reasoning[:80]}...")
                    print()

            except Exception as e:
                print(f"   ❌ 處理知識 ID {row['id']} 時出錯: {e}")
                self.stats['errors'] += 1
                continue

        self.print_stats(dry_run)

    def print_stats(self, dry_run: bool):
        """列印統計資訊"""
        print(f"\n{'='*60}")
        print(f"重新分類統計 {'（試運行）' if dry_run else '（正式執行）'}")
        print(f"{'='*60}")
        print(f"總知識數：{self.stats['total_knowledge']}")
        print(f"重新分類：{self.stats['reclassified']}")
        print(f"無需變更：{self.stats['unchanged']}")
        print(f"錯誤：{self.stats['errors']}")
        print(f"{'='*60}\n")


async def main():
    """主程式"""
    print("="*60)
    print("知識庫意圖重新分類工具")
    print("="*60)

    # 檢查 OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        return

    # 建立分類器
    classifier = KnowledgeIntentReclassifier()

    try:
        # 連接資料庫
        await classifier.connect_db()

        # 載入意圖
        await classifier.load_intents()

        if not classifier.intents:
            print("❌ 錯誤：資料庫中沒有可用的意圖")
            return

        # 詢問用戶配置
        print("\n" + "="*60)
        print("配置選項")
        print("="*60)

        # 是否只處理 LINE 來源
        line_only = input("\n只處理 LINE 提取的知識？(Y/n): ").strip().lower()
        filter_source = "%LINE%" if line_only != 'n' else None

        # 是否只處理特定意圖
        intent_filter = input("\n只處理特定意圖 ID 的知識？（留空表示全部）: ").strip()
        filter_intent_id = int(intent_filter) if intent_filter else None

        # 批次大小
        batch_input = input("\n批次大小（每處理 N 條顯示一次進度，預設 10）: ").strip()
        batch_size = int(batch_input) if batch_input else 10

        # 試運行模式
        dry_run_input = input("\n試運行模式（不會修改資料庫）？(Y/n): ").strip().lower()
        dry_run = dry_run_input != 'n'

        # 確認執行
        print(f"\n{'='*60}")
        print("即將開始重新分類")
        print(f"{'='*60}")
        print(f"來源篩選: {filter_source or '全部'}")
        print(f"意圖篩選: {filter_intent_id or '全部'}")
        print(f"批次大小: {batch_size}")
        print(f"模式: {'試運行' if dry_run else '正式執行（會修改資料庫）'}")
        print(f"{'='*60}")

        if not dry_run:
            confirm = input("\n⚠️  正式執行會修改資料庫！確認繼續？(yes/N): ").strip()
            if confirm.lower() != 'yes':
                print("❌ 已取消執行")
                return

        # 執行重新分類
        await classifier.reclassify_knowledge(
            filter_source_file=filter_source,
            filter_intent_id=filter_intent_id,
            batch_size=batch_size,
            dry_run=dry_run
        )

        print("\n✅ 重新分類完成！")

        if dry_run:
            print("\n💡 提示：這是試運行模式，資料庫未被修改")
            print("   如要正式執行，請重新運行並選擇 '正式執行' 模式")

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 關閉資料庫連接
        await classifier.close_db()


if __name__ == "__main__":
    asyncio.run(main())
