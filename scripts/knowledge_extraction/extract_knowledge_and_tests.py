"""
LINE 聊天記錄知識提取與測試情境累積腳本
處理三個 LINE 聊天記錄，提取知識庫並累積測試情境
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Tuple
import pandas as pd
from openai import OpenAI
import time

class LineKnowledgeExtractor:
    """LINE 聊天記錄知識提取器"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

        # 統計資訊
        self.stats = {
            "total_messages": 0,
            "total_qa_pairs": 0,
            "total_test_scenarios": 0,
            "files_processed": 0
        }

    def parse_line_chat(self, file_path: str) -> List[Dict]:
        """
        解析 LINE 聊天記錄

        Returns:
            List of message dicts: {timestamp, user, message}
        """
        print(f"📖 讀取文件: {os.path.basename(file_path)}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # LINE 對話格式：
        # 2023/05/23（二）
        # 下午05:35  張嘉修-Josh  "訊息內容"

        messages = []
        lines = content.split('\n')
        current_date = None

        for line in lines:
            if not line.strip():
                continue

            # 跳過標題和儲存日期
            if line.startswith('[LINE]') or line.startswith('儲存日期'):
                continue

            # 檢查是否為日期行
            date_match = re.match(r'(\d{4}/\d{2}/\d{2})', line)
            if date_match:
                current_date = date_match.group(1)
                continue

            # 檢查是否為訊息行（使用 tab 分隔）
            parts = line.split('\t')
            if len(parts) >= 3:
                time_str = parts[0].strip()
                user = parts[1].strip()
                message = '\t'.join(parts[2:]).strip()

                # 過濾系統訊息和無意義訊息
                if not user or '已新增' in message or '已離開' in message:
                    continue

                # 過濾多媒體訊息
                if message in ['[照片]', '[影片]', '[貼圖]', '[檔案]', '[語音訊息]']:
                    continue

                # 移除引號
                message = message.strip('"')

                if message:  # 只保留有內容的訊息
                    timestamp = f"{current_date} {time_str}" if current_date else time_str
                    messages.append({
                        'timestamp': timestamp,
                        'user': user,
                        'message': message
                    })

        self.stats['total_messages'] += len(messages)
        print(f"   ✅ 解析 {len(messages)} 條有效訊息")
        return messages

    def extract_qa_pairs_and_tests(
        self,
        messages: List[Dict],
        source_file: str,
        batch_size: int = 50
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        使用 LLM 提取問答對和測試情境

        Returns:
            (qa_pairs, test_scenarios)
        """
        print(f"\n🤖 開始 LLM 分析...")

        qa_pairs = []
        test_scenarios = []

        # 將訊息分批處理
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            batch_text = self._format_messages_for_llm(batch)

            print(f"   處理批次 {i//batch_size + 1}/{(len(messages)-1)//batch_size + 1}...")

            # 呼叫 LLM 提取
            extracted = self._call_llm_extract(batch_text, source_file)

            qa_pairs.extend(extracted['qa_pairs'])
            test_scenarios.extend(extracted['test_scenarios'])

            # 避免 API rate limit
            time.sleep(1)

        self.stats['total_qa_pairs'] += len(qa_pairs)
        self.stats['total_test_scenarios'] += len(test_scenarios)

        print(f"   ✅ 提取 {len(qa_pairs)} 個問答對")
        print(f"   ✅ 累積 {len(test_scenarios)} 個測試情境")

        return qa_pairs, test_scenarios

    def _format_messages_for_llm(self, messages: List[Dict]) -> str:
        """格式化訊息供 LLM 分析"""
        formatted = []
        for msg in messages:
            formatted.append(f"[{msg['timestamp']}] {msg['user']}: {msg['message']}")
        return '\n'.join(formatted)

    def _call_llm_extract(self, conversation: str, source_file: str) -> Dict:
        """呼叫 LLM 提取知識和測試情境"""

        system_prompt = """你是一個專業的客服知識庫分析師。分析 LINE 對話記錄，提取：

1. **問答對（QA Pairs）**：提取客服回答的問題和答案
   - 問題要通用化（移除具體租客姓名、房號等）
   - 答案要完整且實用
   - 識別問題類型（帳務/合約/服務/設施）
   - 判斷對象（房東/租客/管理師）

2. **測試情境（Test Scenarios）**：提取可以作為測試的真實問題
   - 保留問題的原始表達方式
   - 記錄預期答案的關鍵要點

請以 JSON 格式輸出：
{
  "qa_pairs": [
    {
      "title": "問題標題",
      "category": "帳務問題|合約問題|服務問題|設施問題",
      "question_summary": "問題摘要",
      "answer": "完整答案",
      "audience": "房東|租客|管理師",
      "keywords": ["關鍵字1", "關鍵字2"]
    }
  ],
  "test_scenarios": [
    {
      "test_question": "測試問題（原始表達）",
      "expected_answer_points": ["答案要點1", "答案要點2"],
      "difficulty": "easy|medium|hard",
      "notes": "備註（簡要說明問題類型和重點）"
    }
  ]
}

注意：
- 只提取清晰、完整的客服問答
- 避免包含私人資訊（姓名、電話、地址等）
- 測試問題要具有代表性
"""

        user_prompt = f"""分析以下 LINE 對話記錄，提取問答對和測試情境：

來源文件：{source_file}

對話內容：
{conversation[:4000]}  # 限制長度避免超出 token 限制

請提取：
1. 清晰的客服問答對
2. 可以作為測試的典型問題
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            result = json.loads(response.choices[0].message.content)

            # 添加來源資訊
            for qa in result.get('qa_pairs', []):
                qa['source_file'] = source_file
                qa['source_date'] = datetime.now().strftime('%Y-%m-%d')

            for test in result.get('test_scenarios', []):
                test['source_file'] = source_file

            return result

        except Exception as e:
            print(f"   ⚠️  LLM 提取失敗: {e}")
            return {'qa_pairs': [], 'test_scenarios': []}

    def process_all_files(self, file_paths: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """處理所有文件"""
        all_qa_pairs = []
        all_test_scenarios = []

        for file_path in file_paths:
            print(f"\n{'='*60}")
            print(f"處理文件: {os.path.basename(file_path)}")
            print(f"{'='*60}")

            # 解析對話
            messages = self.parse_line_chat(file_path)

            # 提取知識和測試
            qa_pairs, test_scenarios = self.extract_qa_pairs_and_tests(
                messages,
                os.path.basename(file_path)
            )

            all_qa_pairs.extend(qa_pairs)
            all_test_scenarios.extend(test_scenarios)

            self.stats['files_processed'] += 1

        return all_qa_pairs, all_test_scenarios

    def save_to_excel(
        self,
        qa_pairs: List[Dict],
        test_scenarios: List[Dict],
        output_dir: str
    ):
        """儲存為 Excel 文件"""
        print(f"\n💾 儲存結果...")

        # 儲存知識庫
        if qa_pairs:
            kb_df = pd.DataFrame(qa_pairs)
            kb_output = os.path.join(output_dir, 'knowledge_base_extracted.xlsx')
            kb_df.to_excel(kb_output, index=False, engine='openpyxl')
            print(f"   ✅ 知識庫已儲存: {kb_output}")
            print(f"      共 {len(qa_pairs)} 條知識")

        # 儲存測試情境
        if test_scenarios:
            test_df = pd.DataFrame(test_scenarios)
            test_output = os.path.join(output_dir, 'test_scenarios.xlsx')
            test_df.to_excel(test_output, index=False, engine='openpyxl')
            print(f"   ✅ 測試情境已儲存: {test_output}")
            print(f"      共 {len(test_scenarios)} 個測試")

    def print_summary(self):
        """列印處理摘要"""
        print(f"\n{'='*60}")
        print("📊 處理摘要")
        print(f"{'='*60}")
        print(f"處理文件數：{self.stats['files_processed']}")
        print(f"總訊息數：{self.stats['total_messages']}")
        print(f"提取問答對：{self.stats['total_qa_pairs']}")
        print(f"累積測試情境：{self.stats['total_test_scenarios']}")
        print(f"{'='*60}\n")


def main():
    """主程式"""
    print("="*60)
    print("LINE 聊天記錄知識提取與測試情境累積")
    print("="*60)

    # 檢查 OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        return

    # 文件路徑
    data_dir = "/Users/lenny/jgb/AIChatbot/data"
    output_dir = "/Users/lenny/jgb/AIChatbot/output"

    files = [
        os.path.join(data_dir, "[LINE] 一方生活x JGB的聊天.txt"),
        os.path.join(data_dir, "[LINE] 富喬 X JGB排除疑難雜症區的聊天.txt"),
        os.path.join(data_dir, "[LINE] 興中資產管理&易聚的聊天.txt")
    ]

    # 檢查文件是否存在
    for f in files:
        if not os.path.exists(f):
            print(f"❌ 文件不存在: {f}")
            return

    # 建立提取器
    extractor = LineKnowledgeExtractor()

    # 處理所有文件
    qa_pairs, test_scenarios = extractor.process_all_files(files)

    # 儲存結果
    extractor.save_to_excel(qa_pairs, test_scenarios, output_dir)

    # 列印摘要
    extractor.print_summary()

    print("✅ 處理完成！")
    print(f"\n下一步：")
    print(f"1. 檢查 {output_dir}/knowledge_base_extracted.xlsx")
    print(f"2. 檢查 {output_dir}/test_scenarios.xlsx")
    print(f"3. 執行知識庫導入腳本")
    print(f"4. 執行回測腳本")


if __name__ == "__main__":
    main()
