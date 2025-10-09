#!/usr/bin/env python3
"""
LINE 對話記錄處理腳本
使用 OpenAI API 分析客服對話，整理成 Excel 格式
"""

import os
import re
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI


class LineConversationParser:
    """LINE 對話解析器"""

    def __init__(self):
        # LINE 對話格式：時間\t發言者\t內容
        self.message_pattern = re.compile(r'^(上午|下午)\d{2}:\d{2}\s+(.+?)\s+(.+)$')
        self.date_pattern = re.compile(r'^\d{4}/\d{2}/\d{2}[（(].*?[）)]$')

    def parse_file(self, file_path: str, max_lines: Optional[int] = None) -> List[Dict]:
        """
        解析 LINE 對話檔案

        Args:
            file_path: txt 檔案路徑
            max_lines: 最多讀取行數（用於測試）

        Returns:
            對話列表
        """
        conversations = []
        current_date = None
        current_conversation = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if max_lines and i >= max_lines:
                    break

                line = line.strip()
                if not line:
                    continue

                # 檢查是否為日期行
                if self.date_pattern.match(line):
                    # 儲存前一個對話段落
                    if current_conversation:
                        conversations.append({
                            'date': current_date,
                            'messages': current_conversation.copy(),
                            'source_file': Path(file_path).name
                        })
                        current_conversation = []

                    current_date = line
                    continue

                # 解析訊息
                match = self.message_pattern.match(line)
                if match:
                    time_period, speaker, content = match.groups()

                    # 過濾系統訊息
                    if '已新增' in content or '已收回訊息' in content or '群組通話' in content:
                        continue

                    # 過濾貼圖、照片等非文字內容
                    if content in ['[貼圖]', '[照片]', '[影片]', '[檔案]', '[聯絡資訊]', '[記事本]']:
                        continue

                    current_conversation.append({
                        'time': time_period + match.group(0).split('\t')[0].split(time_period)[1].split()[0],
                        'speaker': speaker,
                        'content': content
                    })

        # 儲存最後一個對話段落
        if current_conversation:
            conversations.append({
                'date': current_date,
                'messages': current_conversation,
                'source_file': Path(file_path).name
            })

        return conversations


class ConversationAnalyzer:
    """使用 OpenAI API 分析對話"""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def analyze_conversation(self, conversation: Dict) -> Optional[Dict]:
        """
        分析單個對話段落

        Returns:
            {
                'date': 日期,
                'staff': 建檔人員,
                'category': 問題類別,
                'audience': 對象角色,
                'frequency': 頻率,
                'response': 標準回覆,
                'keywords': 關鍵字
            }
        """
        # 組合對話內容
        messages_text = "\n".join([
            f"{msg['speaker']}: {msg['content']}"
            for msg in conversation['messages']
        ])

        # 如果對話太短或不包含實質問答，跳過
        if len(conversation['messages']) < 2:
            return None

        # 建立 prompt
        prompt = f"""請分析以下 JGB 包租代管系統的客服對話記錄，提取關鍵資訊。

對話內容：
{messages_text}

請以 JSON 格式回覆，包含以下欄位：
{{
    "is_qa": true/false,  // 是否為有價值的問答（需包含問題和解答）
    "category": "合約問題/物件問題/帳務問題/IOT設備問題/帳號問題/操作問題/其他",
    "audience": "房東/租客/管理師/業者/其他",
    "question_summary": "問題摘要（20字內）",
    "standard_response": "標準回覆內容（完整且專業的回答，可供未來客服參考）",
    "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]  // 3-5個關鍵字
}}

注意事項：
1. 只有包含明確問題和解答的對話才設定 is_qa=true
2. 純聊天、貼圖、確認訊息等設定 is_qa=false
3. 標準回覆要完整、專業，可作為未來類似問題的參考答案
4. 關鍵字要能幫助未來搜尋，包含功能名稱、問題類型等

只回傳 JSON，不要其他說明文字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是 JGB 包租代管系統的客服知識庫整理專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # 只保留有價值的問答
            if not result.get('is_qa', False):
                return None

            return {
                'date': conversation['date'],
                'staff': '系統自動整理',
                'category': result.get('category', '其他'),
                'audience': result.get('audience', '其他'),
                'frequency': '',  # 需要後續統計
                'response': result.get('standard_response', ''),
                'keywords': ', '.join(result.get('keywords', [])),
                'question_summary': result.get('question_summary', ''),
                'source_file': conversation['source_file']
            }

        except Exception as e:
            print(f"❌ 分析失敗: {str(e)}")
            return None


def main():
    """主程式"""

    print("=" * 60)
    print("LINE 對話記錄分析工具（測試版）")
    print("=" * 60)

    # 設定參數
    DATA_DIR = Path(__file__).parent.parent / "data"
    OUTPUT_DIR = DATA_DIR
    MAX_LINES = 200  # 測試模式：只處理前 200 行

    # OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 錯誤：請設定環境變數 OPENAI_API_KEY")
        print("   方法：export OPENAI_API_KEY='your-api-key'")
        return

    # 找出所有 LINE 對話檔案
    line_files = [f for f in DATA_DIR.glob("*.txt") if "[LINE]" in f.name]

    if not line_files:
        print(f"❌ 在 {DATA_DIR} 找不到 LINE 對話檔案")
        return

    print(f"\n找到 {len(line_files)} 個 LINE 對話檔案：")
    for f in line_files:
        print(f"  - {f.name}")

    # 初始化
    parser = LineConversationParser()
    analyzer = ConversationAnalyzer(api_key)

    all_results = []

    # 處理每個檔案
    for line_file in line_files:
        print(f"\n處理檔案: {line_file.name}")
        print(f"（測試模式：只讀取前 {MAX_LINES} 行）")

        # 解析對話
        conversations = parser.parse_file(str(line_file), max_lines=MAX_LINES)
        print(f"  解析出 {len(conversations)} 個對話段落")

        # 分析對話
        for i, conv in enumerate(conversations, 1):
            print(f"  分析中... {i}/{len(conversations)}", end="\r")

            result = analyzer.analyze_conversation(conv)
            if result:
                all_results.append(result)

        print(f"\n  ✅ 提取出 {len([r for r in all_results if r['source_file'] == line_file.name])} 個有效問答")

    # 輸出結果
    if not all_results:
        print("\n⚠️  沒有提取到有效的問答內容")
        return

    print(f"\n總計提取 {len(all_results)} 個有效問答")

    # 轉換為 DataFrame
    df = pd.DataFrame(all_results)

    # 調整欄位順序
    columns_order = ['date', 'staff', 'category', 'audience', 'question_summary',
                     'response', 'keywords', 'frequency', 'source_file']
    df = df[columns_order]

    # 重新命名欄位為中文
    df.columns = ['日期', '建檔人員', '租客帳號問題', '對象', '問題摘要',
                  '回覆', '關鍵字', '頻率', '來源檔案']

    # 儲存為 Excel
    output_file = OUTPUT_DIR / "客服QA整理_測試結果.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')

    print(f"\n✅ 結果已儲存至: {output_file}")

    # 顯示統計資訊
    print("\n" + "=" * 60)
    print("統計資訊")
    print("=" * 60)
    print(f"\n問題類別分佈：")
    print(df['租客帳號問題'].value_counts())
    print(f"\n對象分佈：")
    print(df['對象'].value_counts())

    # 顯示範例
    print("\n" + "=" * 60)
    print("前 3 筆結果預覽")
    print("=" * 60)
    for i, row in df.head(3).iterrows():
        print(f"\n第 {i+1} 筆：")
        print(f"  類別: {row['租客帳號問題']}")
        print(f"  對象: {row['對象']}")
        print(f"  問題: {row['問題摘要']}")
        print(f"  關鍵字: {row['關鍵字']}")
        print(f"  回覆: {row['回覆'][:100]}...")


if __name__ == "__main__":
    main()
