"""
LINE 對話解析器
處理 LINE 聊天記錄文字檔
"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class LineMessage(BaseModel):
    """LINE 訊息"""
    timestamp: datetime
    sender: str
    message: str


class LineConversation(BaseModel):
    """解析後的 LINE 對話"""
    messages: List[LineMessage]
    participants: List[str]
    start_time: datetime
    end_time: datetime
    total_messages: int


class LineParser:
    """LINE 對話解析器"""

    # LINE 訊息格式範例：
    # 2024/01/15 14:30 張三: 你好，請問這個功能怎麼用？
    # 2024/01/15 14:31 客服: 您好！這個功能使用方式如下...

    # 訊息格式正則表達式（支援多種格式）
    PATTERNS = [
        # 格式 1: 2024/01/15 14:30 張三: 訊息內容
        r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})\s+([^:]+):\s*(.+)',
        # 格式 2: [2024-01-15 14:30:00] 張三: 訊息內容
        r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+([^:]+):\s*(.+)',
        # 格式 3: 14:30 張三: 訊息內容（無日期）
        r'(\d{2}:\d{2})\s+([^:]+):\s*(.+)',
    ]

    @classmethod
    def parse_text(cls, text: str, default_date: Optional[str] = None) -> LineConversation:
        """
        解析 LINE 對話文字

        Args:
            text: LINE 對話純文字
            default_date: 預設日期（用於無日期格式），格式：YYYY/MM/DD

        Returns:
            LineConversation: 解析後的對話
        """
        lines = text.strip().split('\n')
        messages: List[LineMessage] = []
        participants = set()

        current_date = default_date or datetime.now().strftime('%Y/%m/%d')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 嘗試匹配各種格式
            parsed = cls._parse_line(line, current_date)
            if parsed:
                messages.append(parsed)
                participants.add(parsed.sender)

        if not messages:
            raise ValueError("無法解析任何訊息，請檢查格式是否正確")

        return LineConversation(
            messages=messages,
            participants=list(participants),
            start_time=messages[0].timestamp,
            end_time=messages[-1].timestamp,
            total_messages=len(messages),
        )

    @classmethod
    def _parse_line(cls, line: str, default_date: str) -> Optional[LineMessage]:
        """解析單行訊息"""
        for pattern in cls.PATTERNS:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()

                # 解析時間戳記
                timestamp_str = groups[0]
                sender = groups[1].strip()
                message = groups[2].strip()

                # 處理不同的時間格式
                try:
                    if '/' in timestamp_str and len(timestamp_str) > 10:
                        # 格式: 2024/01/15 14:30
                        timestamp = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
                    elif '-' in timestamp_str:
                        # 格式: 2024-01-15 14:30:00
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        # 格式: 14:30 (僅時間)
                        time_str = f"{default_date} {timestamp_str}"
                        timestamp = datetime.strptime(time_str, '%Y/%m/%d %H:%M')

                    return LineMessage(
                        timestamp=timestamp,
                        sender=sender,
                        message=message,
                    )
                except ValueError:
                    continue

        return None

    @classmethod
    def to_conversation_dict(cls, line_conv: LineConversation) -> Dict[str, Any]:
        """
        轉換為標準對話格式（用於儲存到資料庫）

        Returns:
            {
                "messages": [...],
                "metadata": {...}
            }
        """
        return {
            "messages": [
                {
                    "timestamp": msg.timestamp.isoformat(),
                    "sender": msg.sender,
                    "message": msg.message,
                }
                for msg in line_conv.messages
            ],
            "metadata": {
                "source": "line",
                "participants": line_conv.participants,
                "start_time": line_conv.start_time.isoformat(),
                "end_time": line_conv.end_time.isoformat(),
                "total_messages": line_conv.total_messages,
                "parsed_at": datetime.now().isoformat(),
            }
        }

    @classmethod
    def format_as_qa(cls, line_conv: LineConversation) -> List[Dict[str, str]]:
        """
        將對話格式化為 Q&A 格式
        假設：參與者中第一個是用戶，其他是客服

        Returns:
            [{"question": "...", "answer": "...", "context": "..."}, ...]
        """
        qa_pairs = []
        participants = line_conv.participants

        # 簡單啟發式：第一個參與者是用戶
        user = participants[0] if participants else "用戶"
        agents = [p for p in participants if p != user]

        current_question = None
        current_answers = []

        for msg in line_conv.messages:
            if msg.sender == user:
                # 用戶訊息 -> 新問題
                if current_question and current_answers:
                    qa_pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answers),
                        "context": f"對話時間：{line_conv.start_time.strftime('%Y-%m-%d %H:%M')}",
                    })

                current_question = msg.message
                current_answers = []
            else:
                # 客服訊息 -> 答案
                if current_question:
                    current_answers.append(msg.message)

        # 處理最後一組 Q&A
        if current_question and current_answers:
            qa_pairs.append({
                "question": current_question,
                "answer": " ".join(current_answers),
                "context": f"對話時間：{line_conv.start_time.strftime('%Y-%m-%d %H:%M')}",
            })

        return qa_pairs


# ========== 使用範例 ==========

if __name__ == "__main__":
    # 測試範例
    sample_text = """
2024/01/15 14:30 客戶: 你好，請問如何使用這個功能？
2024/01/15 14:31 客服: 您好！使用方式很簡單，請按照以下步驟：
2024/01/15 14:31 客服: 1. 打開應用程式
2024/01/15 14:32 客服: 2. 點選右上角的設定按鈕
2024/01/15 14:33 客戶: 好的，我找到了！謝謝
2024/01/15 14:33 客服: 不客氣，還有其他問題嗎？
    """

    parser = LineParser()
    conversation = parser.parse_text(sample_text)

    print("=== 解析結果 ===")
    print(f"參與者: {conversation.participants}")
    print(f"訊息數: {conversation.total_messages}")
    print(f"時間範圍: {conversation.start_time} ~ {conversation.end_time}")

    print("\n=== Q&A 格式 ===")
    qa_pairs = parser.format_as_qa(conversation)
    for i, qa in enumerate(qa_pairs, 1):
        print(f"\nQ{i}: {qa['question']}")
        print(f"A{i}: {qa['answer']}")
