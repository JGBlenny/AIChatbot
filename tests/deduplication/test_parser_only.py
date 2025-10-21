#!/usr/bin/env python3
"""
LINE 對話解析測試（不需要 API key）
只測試對話解析邏輯，不呼叫 OpenAI API
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional


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


def main():
    """主程式"""

    print("=" * 60)
    print("LINE 對話解析測試（不需要 API）")
    print("=" * 60)

    # 設定參數
    DATA_DIR = Path(__file__).parent.parent / "data"
    MAX_LINES = 300  # 測試模式：只處理前 300 行

    # 找出所有 LINE 對話檔案
    line_files = [f for f in DATA_DIR.glob("*.txt") if "[LINE]" in f.name]

    if not line_files:
        print(f"❌ 在 {DATA_DIR} 找不到 LINE 對話檔案")
        return

    print(f"\n找到 {len(line_files)} 個 LINE 對話檔案：")
    for f in line_files:
        print(f"  - {f.name}")

    # 初始化解析器
    parser = LineConversationParser()

    # 處理每個檔案
    for line_file in line_files:
        print(f"\n{'=' * 60}")
        print(f"處理檔案: {line_file.name}")
        print(f"（測試模式：只讀取前 {MAX_LINES} 行）")
        print(f"{'=' * 60}")

        # 解析對話
        conversations = parser.parse_file(str(line_file), max_lines=MAX_LINES)
        print(f"\n✅ 解析出 {len(conversations)} 個對話段落")

        # 顯示前 5 個對話段落的摘要
        print(f"\n前 5 個對話段落預覽：\n")
        for i, conv in enumerate(conversations[:5], 1):
            print(f"【段落 {i}】")
            print(f"日期: {conv['date']}")
            print(f"訊息數: {len(conv['messages'])}")

            # 顯示對話內容（只顯示前 3 則訊息）
            print(f"對話內容:")
            for j, msg in enumerate(conv['messages'][:3], 1):
                content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                print(f"  {j}. {msg['speaker']}: {content_preview}")

            if len(conv['messages']) > 3:
                print(f"  ... (還有 {len(conv['messages']) - 3} 則訊息)")

            print()

        # 統計資訊
        total_messages = sum(len(conv['messages']) for conv in conversations)
        speakers = set()
        for conv in conversations:
            for msg in conv['messages']:
                speakers.add(msg['speaker'])

        print(f"\n統計資訊：")
        print(f"  - 對話段落數: {len(conversations)}")
        print(f"  - 總訊息數: {total_messages}")
        print(f"  - 平均每段落訊息數: {total_messages / len(conversations):.1f}")
        print(f"  - 發言者數量: {len(speakers)}")
        print(f"  - 發言者列表: {', '.join(list(speakers)[:10])}" +
              (f" ... (還有 {len(speakers) - 10} 位)" if len(speakers) > 10 else ""))

        # 找出包含問答的對話（簡單啟發式判斷）
        qa_candidates = []
        for conv in conversations:
            if len(conv['messages']) >= 2:  # 至少要有 2 則訊息
                # 檢查是否包含問號或常見問題關鍵字
                has_question = False
                has_answer = False

                for msg in conv['messages']:
                    content = msg['content']
                    if '?' in content or '？' in content or '請問' in content or '如何' in content or '怎麼' in content:
                        has_question = True
                    if len(content) > 20:  # 假設回答通常比較長
                        has_answer = True

                if has_question and has_answer:
                    qa_candidates.append(conv)

        print(f"\n可能包含問答的對話段落: {len(qa_candidates)} 個")

        if qa_candidates:
            print(f"\n問答候選範例（前 2 個）：\n")
            for i, conv in enumerate(qa_candidates[:2], 1):
                print(f"【問答候選 {i}】")
                print(f"日期: {conv['date']}")
                for j, msg in enumerate(conv['messages'][:5], 1):
                    content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
                    print(f"  {msg['speaker']}: {content_preview}")
                print()


if __name__ == "__main__":
    main()
