#!/usr/bin/env python3
"""
生成訓練數據：從知識庫生成查詢-文檔配對
"""

import json
import os
import random
from typing import List, Dict, Tuple

class TrainingDataGenerator:
    """訓練數據生成器"""

    def __init__(self):
        self.data_dir = "data"
        self.knowledge_base = self.load_knowledge_base()
        self.patterns = self.define_patterns()

    def load_knowledge_base(self) -> List[Dict]:
        """載入知識庫"""
        kb_file = os.path.join(self.data_dir, "knowledge_base.json")
        if not os.path.exists(kb_file):
            print("❌ 找不到 knowledge_base.json")
            print("請先執行: python extract_knowledge.py")
            return []

        with open(kb_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def define_patterns(self) -> Dict:
        """定義語義模式及其查詢模板"""
        return {
            "time_query": {
                "name": "時間查詢模式",
                "templates": [
                    "{subject}幾號{action}",
                    "{subject}什麼時候{action}",
                    "{subject}何時{action}",
                    "查詢{subject}{action}時間",
                    "{subject}{action}期限",
                    "{subject}{action}週期"
                ],
                "keywords": {
                    "subject": ["電費", "水費", "租金", "管理費", "帳單"],
                    "action": ["寄送", "繳納", "發送", "收取", "到期"]
                }
            },
            "cost_query": {
                "name": "費用計算模式",
                "templates": [
                    "{subject}多少錢",
                    "{subject}怎麼算",
                    "{subject}費用",
                    "{subject}價格",
                    "計算{subject}"
                ],
                "keywords": {
                    "subject": ["電費", "水費", "租金", "管理費", "停車費", "押金"]
                }
            },
            "application": {
                "name": "申請辦理模式",
                "templates": [
                    "申請{subject}",
                    "辦理{subject}",
                    "我要{subject}",
                    "如何{subject}",
                    "怎麼{subject}"
                ],
                "keywords": {
                    "subject": ["退租", "入住", "報修", "停車位", "更換", "續約"]
                }
            },
            "regulation": {
                "name": "規定說明模式",
                "templates": [
                    "{subject}規定",
                    "{subject}須知",
                    "{subject}說明",
                    "{subject}注意事項",
                    "關於{subject}"
                ],
                "keywords": {
                    "subject": ["租屋", "社區", "退租", "入住", "寵物", "裝修"]
                }
            },
            "status_query": {
                "name": "狀態查詢模式",
                "templates": [
                    "可以{action}嗎",
                    "能不能{action}",
                    "是否可以{action}",
                    "有沒有{subject}",
                    "有{subject}嗎"
                ],
                "keywords": {
                    "action": ["養寵物", "裝修", "轉租", "提前退租", "停車"],
                    "subject": ["電梯", "停車位", "管理員", "保全", "公設"]
                }
            }
        }

    def generate_queries_for_knowledge(self, kb_item: Dict) -> List[Dict]:
        """為單個知識點生成多個查詢"""
        queries = []
        title = kb_item.get("title", "")
        content = kb_item.get("content", "")

        # 特定知識點的查詢生成
        if "電費" in title and "寄送" in title:
            # 電費寄送區間特別處理
            specific_queries = [
                "電費幾號寄",
                "電費帳單寄送時間",
                "電費什麼時候寄送",
                "查詢電費寄送區間",
                "電費帳單何時寄送",
                "單月電費幾號寄",
                "雙月電費寄送時間",
                "電費單寄送週期",
                "何時寄電費帳單",
                "電費發送區間"
            ]
            for q in specific_queries:
                queries.append({
                    "query": q,
                    "knowledge_id": kb_item["id"],
                    "knowledge_title": title,
                    "knowledge_content": content,
                    "pattern": "time_query",
                    "is_match": True
                })

        # 通用模式匹配
        for pattern_name, pattern_def in self.patterns.items():
            # 檢查標題是否符合模式
            if self.matches_pattern(title, pattern_name):
                # 生成該模式的查詢
                generated = self.generate_from_template(pattern_def, title)
                for q in generated[:3]:  # 每個模式生成3個查詢
                    queries.append({
                        "query": q,
                        "knowledge_id": kb_item["id"],
                        "knowledge_title": title,
                        "knowledge_content": content,
                        "pattern": pattern_name,
                        "is_match": True
                    })

        return queries

    def matches_pattern(self, title: str, pattern_name: str) -> bool:
        """檢查標題是否符合特定模式"""
        pattern_keywords = {
            "time_query": ["時間", "寄送", "期限", "週期", "幾號"],
            "cost_query": ["費用", "計算", "價格", "收費", "多少"],
            "application": ["申請", "辦理", "表單"],
            "regulation": ["規定", "須知", "說明", "注意"],
            "status_query": ["是否", "可以", "允許"]
        }

        keywords = pattern_keywords.get(pattern_name, [])
        return any(kw in title for kw in keywords)

    def generate_from_template(self, pattern_def: Dict, reference: str = "") -> List[str]:
        """從模板生成查詢"""
        queries = []
        templates = pattern_def.get("templates", [])
        keywords = pattern_def.get("keywords", {})

        for template in templates[:2]:  # 使用前2個模板
            # 簡單替換
            for subject_list in keywords.values():
                if subject_list:
                    subject = random.choice(subject_list)
                    query = template
                    for key in keywords.keys():
                        if f"{{{key}}}" in query:
                            query = query.replace(f"{{{key}}}", random.choice(keywords[key]))
                    queries.append(query)
                    break

        return queries

    def generate_negative_examples(self, positive_examples: List[Dict]) -> List[Dict]:
        """生成負例（不應該匹配的查詢-文檔對）"""
        negative_examples = []

        for pos_example in positive_examples[:len(positive_examples)//2]:
            # 為每個正例生成一個負例
            # 選擇一個不同的知識點
            wrong_kb = random.choice(self.knowledge_base)

            # 確保不是同一個知識點
            if wrong_kb["id"] != pos_example["knowledge_id"]:
                negative_examples.append({
                    "query": pos_example["query"],
                    "knowledge_id": wrong_kb["id"],
                    "knowledge_title": wrong_kb["title"],
                    "knowledge_content": wrong_kb["content"],
                    "pattern": pos_example["pattern"],
                    "is_match": False  # 負例標記
                })

        return negative_examples

    def generate_training_data(self) -> Tuple[List[Dict], List[Dict]]:
        """生成完整的訓練數據集"""
        print("="*60)
        print("開始生成訓練數據")
        print("="*60)

        all_queries = []

        # 為每個知識點生成查詢
        for kb_item in self.knowledge_base:
            queries = self.generate_queries_for_knowledge(kb_item)
            all_queries.extend(queries)
            if queries:
                print(f"✓ {kb_item['title']}: 生成 {len(queries)} 個查詢")

        print(f"\n總計生成 {len(all_queries)} 個正例")

        # 生成負例
        negative_examples = self.generate_negative_examples(all_queries)
        print(f"生成 {len(negative_examples)} 個負例")

        # 合併正負例
        all_training_data = all_queries + negative_examples
        random.shuffle(all_training_data)

        # 分割訓練集和測試集 (8:2)
        split_index = int(len(all_training_data) * 0.8)
        train_data = all_training_data[:split_index]
        test_data = all_training_data[split_index:]

        # 保存訓練數據
        train_file = os.path.join(self.data_dir, "training_data.json")
        with open(train_file, "w", encoding="utf-8") as f:
            json.dump(train_data, f, ensure_ascii=False, indent=2)

        # 保存測試數據
        test_file = os.path.join(self.data_dir, "test_data.json")
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 數據生成完成")
        print(f"訓練集: {len(train_data)} 樣本 -> {train_file}")
        print(f"測試集: {len(test_data)} 樣本 -> {test_file}")

        # 統計資訊
        self.print_statistics(train_data)

        return train_data, test_data

    def print_statistics(self, data: List[Dict]):
        """打印數據統計"""
        print("\n【數據統計】")
        print("-" * 40)

        # 統計正負例
        positive = sum(1 for d in data if d["is_match"])
        negative = sum(1 for d in data if not d["is_match"])
        print(f"正例: {positive}")
        print(f"負例: {negative}")
        print(f"正負比: {positive}/{negative} = {positive/negative:.2f}" if negative > 0 else "")

        # 統計模式分布
        pattern_counts = {}
        for item in data:
            pattern = item.get("pattern", "unknown")
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        print("\n模式分布:")
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(data) * 100
            print(f"  {pattern}: {count} ({percentage:.1f}%)")

        # 範例展示
        print("\n【訓練數據範例】")
        print("-" * 40)
        for example in data[:3]:
            print(f"查詢: {example['query']}")
            print(f"匹配知識: {example['knowledge_title']}")
            print(f"是否匹配: {'✅ 正例' if example['is_match'] else '❌ 負例'}")
            print(f"模式: {example['pattern']}")
            print()

def main():
    """主程序"""
    generator = TrainingDataGenerator()

    if not generator.knowledge_base:
        print("\n❌ 無法載入知識庫，請先執行：")
        print("   python extract_knowledge.py")
        return

    print(f"載入了 {len(generator.knowledge_base)} 個知識點\n")

    # 生成訓練數據
    train_data, test_data = generator.generate_training_data()

    print("\n下一步：")
    print("1. 檢查 data/training_data.json 確認數據品質")
    print("2. 執行 python train.py 開始訓練模型")
    print("3. 訓練完成後執行 python evaluate.py 測試效果")

if __name__ == "__main__":
    main()