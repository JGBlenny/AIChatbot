#!/usr/bin/env python3
"""
從資料庫提取知識庫內容作為訓練基礎
"""

import psycopg2
import json
import os
from datetime import datetime

def connect_db():
    """連接到資料庫"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "aichatbot"),
            user=os.getenv("DB_USER", "aichatbot_user"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            port=os.getenv("DB_PORT", 5432)
        )
        return conn
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        print("請確認 Docker 容器正在運行：docker ps")
        return None

def extract_knowledge_base(vendor_id=None):
    """提取指定業者的所有知識點（如果不指定則提取全部）"""

    conn = connect_db()
    if not conn:
        return []

    cursor = conn.cursor()

    try:
        # 根據實際的表結構提取知識庫
        if vendor_id:
            cursor.execute("""
                SELECT
                    id,
                    question_summary,
                    answer,
                    action_type,
                    form_id,
                    priority,
                    keywords,
                    scope,
                    created_at,
                    updated_at
                FROM knowledge_base
                WHERE vendor_id = %s AND is_active = true
                ORDER BY id
            """, (vendor_id,))
        else:
            # 提取所有活躍的知識點
            cursor.execute("""
                SELECT
                    id,
                    question_summary,
                    answer,
                    action_type,
                    form_id,
                    priority,
                    keywords,
                    scope,
                    vendor_id,
                    created_at,
                    updated_at
                FROM knowledge_base
                WHERE is_active = true
                ORDER BY id
            """)

        knowledge_points = []
        for row in cursor.fetchall():
            if vendor_id:
                knowledge_points.append({
                    "id": row[0],
                    "title": row[1] or "",  # question_summary 當作 title
                    "content": row[2] or "",  # answer 當作 content
                    "action_type": row[3],
                    "form_id": row[4],
                    "priority": row[5],
                    "keywords": row[6] if row[6] else [],
                    "scope": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "updated_at": row[9].isoformat() if row[9] else None
                })
            else:
                knowledge_points.append({
                    "id": row[0],
                    "title": row[1] or "",
                    "content": row[2] or "",
                    "action_type": row[3],
                    "form_id": row[4],
                    "priority": row[5],
                    "keywords": row[6] if row[6] else [],
                    "scope": row[7],
                    "vendor_id": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None
                })

        # 保存結果
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)

        # 保存知識庫
        kb_file = os.path.join(output_dir, "knowledge_base.json")
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(knowledge_points, f, ensure_ascii=False, indent=2)

        # 統計資訊
        stats = analyze_knowledge(knowledge_points)

        print("="*60)
        print("✅ 知識庫提取完成")
        print("="*60)
        print(f"知識點數量: {len(knowledge_points)}")
        print(f"\n按 action_type 分類:")
        for action_type, count in stats["by_action_type"].items():
            print(f"  {action_type}: {count}")
        print(f"\n包含表單的知識點: {stats['has_form']}")
        print(f"\n檔案位置: {kb_file}")

        return knowledge_points

    except Exception as e:
        print(f"❌ 提取失敗: {e}")
        return []

    finally:
        cursor.close()
        conn.close()

def analyze_knowledge(knowledge_points):
    """分析知識點特徵"""

    stats = {
        "total": len(knowledge_points),
        "by_action_type": {},
        "has_form": 0,
        "patterns_detected": {
            "time": 0,
            "cost": 0,
            "application": 0,
            "regulation": 0,
            "status": 0,
            "troubleshooting": 0,
            "process": 0,
            "contact": 0
        }
    }

    for kb in knowledge_points:
        # 統計 action_type
        action = kb.get("action_type", "unknown")
        if action:
            stats["by_action_type"][action] = stats["by_action_type"].get(action, 0) + 1

        # 統計表單
        if kb.get("form_id"):
            stats["has_form"] += 1

        # 檢測語義模式
        title = kb.get("title", "")
        content = kb.get("content", "")
        keywords = kb.get("keywords", [])

        # 合併所有文本進行分析
        combined = title + " " + content + " " + " ".join(keywords)

        # 時間查詢模式
        if any(word in combined for word in ["時間", "幾號", "何時", "期限", "週期", "寄送", "發送", "繳費", "繳納"]):
            stats["patterns_detected"]["time"] += 1

        # 費用計算模式
        if any(word in combined for word in ["費用", "價格", "多少錢", "計算", "收費", "租金", "押金"]):
            stats["patterns_detected"]["cost"] += 1

        # 申請辦理模式
        if any(word in combined for word in ["申請", "辦理", "填寫", "表單"]):
            stats["patterns_detected"]["application"] += 1

        # 規定說明模式
        if any(word in combined for word in ["規定", "須知", "說明", "注意事項"]):
            stats["patterns_detected"]["regulation"] += 1

        # 狀態查詢模式
        if any(word in combined for word in ["是否", "有沒有", "可以嗎", "能不能"]):
            stats["patterns_detected"]["status"] += 1

        # 問題處理模式（報修）
        if any(word in combined for word in ["故障", "壞了", "維修", "報修", "問題", "修理"]):
            stats["patterns_detected"]["troubleshooting"] += 1

        # 流程步驟模式
        if any(word in combined for word in ["流程", "步驟", "SOP", "程序"]):
            stats["patterns_detected"]["process"] += 1

        # 聯絡資訊模式
        if any(word in combined for word in ["電話", "聯絡", "聯繫", "客服", "負責人", "LINE"]):
            stats["patterns_detected"]["contact"] += 1

    # 保存分析結果
    stats_file = os.path.join("data", "knowledge_analysis.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n語義模式分布:")
    for pattern, count in stats["patterns_detected"].items():
        if count > 0:
            percentage = count / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {pattern}: {count} ({percentage:.1f}%)")

    return stats

def extract_sample_queries():
    """生成範例查詢（用於初始訓練）"""

    # 載入知識庫
    kb_file = os.path.join("data", "knowledge_base.json")
    if not os.path.exists(kb_file):
        print("請先執行 extract_knowledge_base()")
        return

    with open(kb_file, "r", encoding="utf-8") as f:
        knowledge_points = json.load(f)

    sample_queries = []

    for kb in knowledge_points:
        title = kb.get("title", "")
        keywords = kb.get("keywords", [])

        # 根據標題和關鍵字生成可能的查詢
        if "報修" in title or any("報修" in kw for kw in keywords):
            queries = [
                "我要報修",
                "如何報修",
                "設備故障怎麼辦",
                "東西壞了要找誰"
            ]
            for q in queries:
                sample_queries.append({
                    "query": q,
                    "knowledge_id": kb["id"],
                    "pattern": "troubleshooting"
                })

        elif "繳費" in title or "費用" in title:
            queries = [
                "費用怎麼算",
                "要繳多少錢",
                "收費標準",
                "價格計算方式"
            ]
            for q in queries:
                sample_queries.append({
                    "query": q,
                    "knowledge_id": kb["id"],
                    "pattern": "cost_query"
                })

        elif "冷氣" in title:
            queries = [
                "冷氣壞了",
                "冷氣不冷",
                "空調故障"
            ]
            for q in queries:
                sample_queries.append({
                    "query": q,
                    "knowledge_id": kb["id"],
                    "pattern": "troubleshooting"
                })

    # 保存範例查詢
    if sample_queries:
        queries_file = os.path.join("data", "sample_queries.json")
        with open(queries_file, "w", encoding="utf-8") as f:
            json.dump(sample_queries, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 生成了 {len(sample_queries)} 個範例查詢")
        print(f"檔案位置: {queries_file}")

    return sample_queries

if __name__ == "__main__":
    import sys

    # 可選：指定業者ID
    vendor_id = None
    if len(sys.argv) > 1:
        try:
            vendor_id = int(sys.argv[1])
            print(f"提取業者 {vendor_id} 的知識庫...")
        except:
            print("提取所有知識庫...")
    else:
        print("提取所有知識庫...")

    # 提取知識庫
    knowledge = extract_knowledge_base(vendor_id)

    if knowledge:
        # 生成範例查詢
        extract_sample_queries()

        print("\n下一步：")
        print("1. 檢查 data/knowledge_base.json 確認資料正確")
        print("2. 執行 python scripts/generate_training_data.py 生成訓練數據")
        print("3. 執行 python scripts/train.py 開始訓練")