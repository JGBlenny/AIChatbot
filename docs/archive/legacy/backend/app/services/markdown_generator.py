"""
Markdown 知識庫生成器
將已批准的對話轉換為 Markdown 檔案
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict


class MarkdownGenerator:
    """Markdown 知識庫生成器"""

    def __init__(self, output_dir: str = "../knowledge-base"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_conversations(
        self,
        conversations: List[Dict[str, Any]],
        category: Optional[str] = None
    ) -> Dict[str, str]:
        """
        從對話列表生成 Markdown 檔案

        Args:
            conversations: 對話資料列表
            category: 指定分類（None = 按分類自動分組）

        Returns:
            {
                "產品功能.md": "/path/to/產品功能.md",
                "技術支援.md": "/path/to/技術支援.md",
                ...
            }
        """
        if category:
            # 生成單一分類檔案
            filtered = [c for c in conversations if c.get("primary_category") == category]
            if filtered:
                file_path = self._generate_category_file(category, filtered)
                return {f"{category}.md": str(file_path)}
            return {}
        else:
            # 按分類分組生成多個檔案
            grouped = self._group_by_category(conversations)
            result = {}

            for cat, convs in grouped.items():
                if cat:  # 忽略無分類的
                    file_path = self._generate_category_file(cat, convs)
                    result[f"{cat}.md"] = str(file_path)

            return result

    def _group_by_category(
        self,
        conversations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按分類分組對話"""
        grouped = defaultdict(list)

        for conv in conversations:
            category = conv.get("primary_category", "其他")
            grouped[category].append(conv)

        return dict(grouped)

    def _generate_category_file(
        self,
        category: str,
        conversations: List[Dict[str, Any]]
    ) -> Path:
        """生成單一分類的 Markdown 檔案"""
        # 檔案路徑
        file_path = self.output_dir / f"{category}.md"

        # 收集元數據
        tags = set()
        for conv in conversations:
            tags.update(conv.get("tags", []))

        # 生成 Markdown 內容
        content = self._format_markdown(
            category=category,
            conversations=conversations,
            tags=list(tags)
        )

        # 寫入檔案
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def _format_markdown(
        self,
        category: str,
        conversations: List[Dict[str, Any]],
        tags: List[str]
    ) -> str:
        """格式化 Markdown 內容"""
        lines = []

        # 標題
        lines.append(f"# {category}\n")

        # 元數據
        lines.append("> **元數據**")
        lines.append(f"> - 更新日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> - 資料筆數：{len(conversations)}")
        lines.append(f"> - 來源：LINE 對話整理")
        if tags:
            lines.append(f"> - 標籤：{', '.join(tags)}")
        lines.append("")
        lines.append("---\n")

        # 內容
        for i, conv in enumerate(conversations, 1):
            # 提取清理後的內容
            qa = self._extract_qa(conv)

            if qa:
                # Q&A 格式
                lines.append(f"## {i}. {qa['question']}\n")
                lines.append(qa["answer"])
                lines.append("")

                # 上下文（如有）
                if qa.get("context"):
                    lines.append(f"> **上下文**：{qa['context']}")
                    lines.append("")

                # 標籤
                if conv.get("tags"):
                    lines.append(f"**標籤**：{', '.join(conv['tags'])}")

                # 來源資訊
                lines.append(f"**來源**：對話 ID `{conv.get('id')}`  ")
                if conv.get("quality_score"):
                    lines.append(f"**品質分數**：{conv['quality_score']}/10  ")
                if conv.get("confidence_score"):
                    lines.append(f"**信心度**：{conv['confidence_score']:.2f}  ")

                lines.append("")
                lines.append("---\n")

        return "\n".join(lines)

    def _extract_qa(self, conversation: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """從對話中提取 Q&A"""
        # 優先使用 AI 清理後的內容
        processed = conversation.get("processed_content", {})
        cleaned = processed.get("cleaned", {})

        if cleaned:
            return {
                "question": cleaned.get("question", ""),
                "answer": cleaned.get("answer", ""),
                "context": cleaned.get("context", "")
            }

        # 備用：從原始對話提取
        raw = conversation.get("raw_content", {})
        messages = raw.get("messages", [])

        if not messages:
            return None

        # 簡單提取：第一條為問題，其他為答案
        question = messages[0].get("message", "") if messages else ""
        answers = [m.get("message", "") for m in messages[1:]]
        answer = "\n\n".join(answers)

        return {
            "question": question,
            "answer": answer,
            "context": ""
        }

    def generate_index(self, file_paths: Dict[str, str]) -> Path:
        """
        生成索引檔案（README.md）

        Args:
            file_paths: {分類: 檔案路徑}

        Returns:
            索引檔案路徑
        """
        index_path = self.output_dir / "README.md"

        lines = [
            "# AIChatbot 知識庫\n",
            f"> 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## 📚 分類目錄\n"
        ]

        # 列出所有分類
        for category, path in sorted(file_paths.items()):
            filename = os.path.basename(path)
            lines.append(f"- [{category}](./{filename})")

        lines.append("\n---\n")
        lines.append("## 📖 使用說明\n")
        lines.append("本知識庫由 AIChatbot 後台管理系統自動生成。")
        lines.append("內容來源於 LINE 對話記錄，經過 AI 處理和人工審核。\n")

        lines.append("### 資料格式\n")
        lines.append("每個分類檔案包含：")
        lines.append("- 問題和答案（Q&A 格式）")
        lines.append("- 相關標籤")
        lines.append("- 品質分數和信心度")
        lines.append("- 來源追溯資訊\n")

        lines.append("### 更新頻率\n")
        lines.append("- 建議：每週更新一次")
        lines.append("- 或當有新的已批准對話時手動觸發\n")

        content = "\n".join(lines)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

        return index_path

    def cleanup_old_files(self, keep_categories: List[str]):
        """
        清理不再需要的舊檔案

        Args:
            keep_categories: 要保留的分類列表
        """
        keep_files = {f"{cat}.md" for cat in keep_categories}
        keep_files.add("README.md")
        keep_files.add("_meta.json")

        # 刪除不在保留列表中的 .md 檔案
        for file_path in self.output_dir.glob("*.md"):
            if file_path.name not in keep_files:
                file_path.unlink()
                print(f"已刪除舊檔案: {file_path.name}")


# ========== 使用範例 ==========

if __name__ == "__main__":
    # 測試資料
    test_conversations = [
        {
            "id": "test-001",
            "primary_category": "產品功能",
            "tags": ["登入", "帳戶"],
            "quality_score": 8,
            "confidence_score": 0.92,
            "processed_content": {
                "cleaned": {
                    "question": "如何重設密碼？",
                    "answer": "重設密碼的步驟如下：\n1. 點選右上角『設定』\n2. 選擇『帳戶安全』\n3. 點擊『變更密碼』\n4. 輸入新密碼並確認",
                    "context": "對話時間：2024-01-15 14:30"
                }
            }
        },
        {
            "id": "test-002",
            "primary_category": "產品功能",
            "tags": ["功能", "使用"],
            "quality_score": 9,
            "confidence_score": 0.95,
            "processed_content": {
                "cleaned": {
                    "question": "如何上傳檔案？",
                    "answer": "上傳檔案很簡單：\n1. 點選『上傳』按鈕\n2. 選擇檔案（支援 PDF, JPG, PNG）\n3. 點擊『確認上傳』即可",
                    "context": ""
                }
            }
        },
        {
            "id": "test-003",
            "primary_category": "技術支援",
            "tags": ["錯誤", "排除"],
            "quality_score": 7,
            "confidence_score": 0.85,
            "processed_content": {
                "cleaned": {
                    "question": "無法登入怎麼辦？",
                    "answer": "請嘗試以下方法：\n1. 檢查帳號密碼是否正確\n2. 清除瀏覽器快取\n3. 嘗試重設密碼\n4. 如仍無法解決，請聯繫客服",
                    "context": "常見問題"
                }
            }
        }
    ]

    # 生成 Markdown
    generator = MarkdownGenerator(output_dir="./test_knowledge_base")

    # 生成所有分類檔案
    file_paths = generator.generate_from_conversations(test_conversations)

    print("=== 生成的檔案 ===")
    for category, path in file_paths.items():
        print(f"{category}: {path}")

    # 生成索引
    index_path = generator.generate_index(file_paths)
    print(f"\n索引檔案: {index_path}")

    print("\n✅ Markdown 生成完成！")
