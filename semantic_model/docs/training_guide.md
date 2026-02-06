# 真實資料訓練完全指南

## 🎯 理解「真實資料訓練」

### 什麼是真實資料？

**不是**：隨便寫一些測試句子
**而是**：您系統中實際的資料

包含三個部分：
1. **知識庫內容** - 您資料庫中的所有知識點
2. **用戶查詢歷史** - 用戶實際問過的問題（如果有記錄）
3. **正確配對關係** - 哪個查詢應該匹配哪個知識點

## 📊 Step 1: 提取您的知識庫

### 1.1 匯出知識庫資料

```python
# semantic_model/scripts/extract_knowledge.py

import psycopg2
import json

def extract_knowledge_base():
    """從資料庫提取所有知識點"""

    conn = psycopg2.connect(
        host="localhost",
        database="aichatbot",
        user="aichatbot_user",
        password="aichatbot_password"
    )

    cursor = conn.cursor()

    # 提取所有知識點
    cursor.execute("""
        SELECT
            id,
            title,
            content,
            action_type,
            form_id,
            priority
        FROM knowledge_base
        WHERE vendor_id = 1
    """)

    knowledge_points = []
    for row in cursor.fetchall():
        knowledge_points.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "action_type": row[3],
            "form_id": row[4],
            "priority": row[5]
        })

    # 保存為 JSON
    with open("data/knowledge_base.json", "w", encoding="utf-8") as f:
        json.dump(knowledge_points, f, ensure_ascii=False, indent=2)

    print(f"✅ 提取了 {len(knowledge_points)} 個知識點")
    return knowledge_points

if __name__ == "__main__":
    extract_knowledge_base()
```

執行：
```bash
python semantic_model/scripts/extract_knowledge.py
```

### 1.2 分析知識點類型

```python
# analyze_knowledge.py

def analyze_knowledge_types():
    """分析知識點的類型分布"""

    with open("data/knowledge_base.json", "r", encoding="utf-8") as f:
        knowledge = json.load(f)

    # 統計
    stats = {
        "total": len(knowledge),
        "by_action_type": {},
        "has_form": 0,
        "patterns_found": {}
    }

    for kb in knowledge:
        # 統計 action_type
        action = kb["action_type"]
        stats["by_action_type"][action] = stats["by_action_type"].get(action, 0) + 1

        # 統計表單
        if kb["form_id"]:
            stats["has_form"] += 1

        # 識別模式
        title = kb["title"]
        if any(word in title for word in ["時間", "幾號", "何時", "期限"]):
            stats["patterns_found"]["time"] = stats["patterns_found"].get("time", 0) + 1
        if any(word in title for word in ["費用", "價格", "多少錢"]):
            stats["patterns_found"]["cost"] = stats["patterns_found"].get("cost", 0) + 1

    print("知識庫分析結果：")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return stats
```

## 📝 Step 2: 建立訓練數據集

### 2.1 生成查詢-知識配對

```python
# semantic_model/scripts/generate_training_data.py

def generate_query_knowledge_pairs():
    """生成查詢-知識點配對作為訓練數據"""

    # 載入知識庫
    with open("data/knowledge_base.json", "r", encoding="utf-8") as f:
        knowledge_base = json.load(f)

    training_pairs = []

    # 為每個知識點生成可能的查詢
    for kb in knowledge_base:
        # 基於標題生成查詢變化
        title = kb["title"]

        if "電費" in title and "寄送" in title:
            # 電費寄送相關
            queries = [
                "電費幾號寄",
                "電費什麼時候寄送",
                "電費帳單寄送時間",
                "查詢電費寄送區間",
                "單月電費何時寄",
                "雙月電費寄送時間"
            ]
            for q in queries:
                training_pairs.append({
                    "query": q,
                    "knowledge_id": kb["id"],
                    "knowledge_content": kb["content"],
                    "is_match": True,  # 正例
                    "pattern": "time_query"
                })

        elif "租屋" in title and "須知" in title:
            # 租屋規定相關
            queries = [
                "租屋規定",
                "租屋須知",
                "承租注意事項",
                "房客規定"
            ]
            for q in queries:
                training_pairs.append({
                    "query": q,
                    "knowledge_id": kb["id"],
                    "knowledge_content": kb["content"],
                    "is_match": True,
                    "pattern": "regulation"
                })

        # ... 為其他類型生成

    # 生成負例（不應該匹配的）
    negative_pairs = generate_negative_examples(training_pairs, knowledge_base)
    training_pairs.extend(negative_pairs)

    # 保存訓練數據
    with open("data/training_data.json", "w", encoding="utf-8") as f:
        json.dump(training_pairs, f, ensure_ascii=False, indent=2)

    print(f"✅ 生成了 {len(training_pairs)} 個訓練樣本")
    return training_pairs

def generate_negative_examples(positive_pairs, knowledge_base):
    """生成負例：查詢不應該匹配的知識"""

    negative_pairs = []

    for pos in positive_pairs[:100]:  # 取前100個正例
        # 隨機選擇一個不相關的知識點
        wrong_kb = random.choice(knowledge_base)

        # 確保不是正確答案
        if wrong_kb["id"] != pos["knowledge_id"]:
            negative_pairs.append({
                "query": pos["query"],
                "knowledge_id": wrong_kb["id"],
                "knowledge_content": wrong_kb["content"],
                "is_match": False,  # 負例
                "pattern": pos["pattern"]
            })

    return negative_pairs
```

### 2.2 如果有歷史查詢記錄

```python
# extract_historical_queries.py

def extract_user_queries():
    """提取真實的用戶查詢歷史"""

    conn = psycopg2.connect(
        host="localhost",
        database="aichatbot",
        user="aichatbot_user",
        password="aichatbot_password"
    )

    cursor = conn.cursor()

    # 假設您有查詢日誌表
    cursor.execute("""
        SELECT
            user_query,
            matched_knowledge_id,
            user_feedback,
            created_at
        FROM query_logs
        WHERE created_at > NOW() - INTERVAL '30 days'
        ORDER BY created_at DESC
    """)

    real_queries = []
    for row in cursor.fetchall():
        real_queries.append({
            "query": row[0],
            "matched_id": row[1],
            "was_correct": row[2] == 'positive',  # 假設有用戶反饋
            "timestamp": row[3].isoformat()
        })

    print(f"✅ 提取了 {len(real_queries)} 個真實查詢")

    # 這些是最寶貴的訓練數據！
    return real_queries
```

## 🚀 Step 3: 執行訓練

### 3.1 完整訓練腳本

```python
# semantic_model/scripts/train.py

from sentence_transformers import CrossEncoder, InputExample
import json
from sklearn.model_selection import train_test_split

def train_semantic_model():
    """訓練語義理解模型"""

    print("="*60)
    print("開始訓練語義模型")
    print("="*60)

    # 1. 載入訓練數據
    with open("data/training_data.json", "r", encoding="utf-8") as f:
        training_data = json.load(f)

    print(f"載入了 {len(training_data)} 個訓練樣本")

    # 2. 準備訓練格式
    train_examples = []
    for item in training_data:
        # CrossEncoder 需要的格式：(查詢, 文檔) -> 是否相關
        example = InputExample(
            texts=[item["query"], item["knowledge_content"]],
            label=float(item["is_match"])  # True=1.0, False=0.0
        )
        train_examples.append(example)

    # 3. 分割訓練集和驗證集
    train_samples, val_samples = train_test_split(
        train_examples,
        test_size=0.2,
        random_state=42
    )

    print(f"訓練集: {len(train_samples)} 樣本")
    print(f"驗證集: {len(val_samples)} 樣本")

    # 4. 初始化模型
    model = CrossEncoder('BAAI/bge-reranker-base', num_labels=1)

    # 5. 訓練參數
    print("\n訓練配置：")
    print("- 基礎模型: BAAI/bge-reranker-base")
    print("- Epochs: 3")
    print("- Batch Size: 16")
    print("- 預計時間: 30-60分鐘 (GPU) / 2-3小時 (CPU)")

    # 6. 開始訓練
    model.fit(
        train_examples=train_samples,
        dev_examples=val_samples,
        epochs=3,
        batch_size=16,
        warmup_steps=100,
        evaluation_steps=500,
        output_path='models/semantic_v1',
        save_best_model=True
    )

    print("\n✅ 訓練完成！")
    print("模型保存在: models/semantic_v1/")

    return model

if __name__ == "__main__":
    train_semantic_model()
```

### 3.2 訓練執行命令

```bash
# CPU 訓練（較慢）
python semantic_model/scripts/train.py

# GPU 訓練（較快，如果有 CUDA）
CUDA_VISIBLE_DEVICES=0 python semantic_model/scripts/train.py
```

## 📊 Step 4: 評估模型效果

### 4.1 測試腳本

```python
# semantic_model/scripts/evaluate.py

def evaluate_model():
    """評估訓練好的模型"""

    # 載入模型
    model = CrossEncoder('models/semantic_v1')

    # 測試集
    test_queries = [
        {"query": "電費幾號寄", "expected_id": 1296},
        {"query": "租屋規定", "expected_id": 1295},
        {"query": "管理費多少", "expected_id": 1297},
        # ... 更多測試
    ]

    # 載入知識庫
    with open("data/knowledge_base.json", "r") as f:
        knowledge_base = json.load(f)

    correct = 0
    total = len(test_queries)

    for test in test_queries:
        # 對所有知識點評分
        scores = []
        for kb in knowledge_base:
            score = model.predict([(test["query"], kb["content"])])[0]
            scores.append((kb["id"], score))

        # 選擇最高分
        best_id = max(scores, key=lambda x: x[1])[0]

        if best_id == test["expected_id"]:
            correct += 1
            print(f"✅ {test['query']} -> 正確")
        else:
            print(f"❌ {test['query']} -> 錯誤 (預期:{test['expected_id']}, 實際:{best_id})")

    accuracy = correct / total * 100
    print(f"\n準確率: {accuracy:.1f}%")

    return accuracy
```

## 🔄 Step 5: 持續優化循環

```python
# semantic_model/scripts/continuous_improvement.py

def improvement_cycle():
    """持續改進循環"""

    while True:
        # 1. 收集一週的新查詢
        new_queries = collect_weekly_queries()

        # 2. 人工標註（或半自動）
        annotated = annotate_queries(new_queries)

        # 3. 加入訓練集
        add_to_training_set(annotated)

        # 4. 每月重新訓練
        if is_month_end():
            retrain_model()

        # 5. A/B 測試新模型
        if new_model_ready():
            run_ab_test()
```

## 💡 實用建議

### 1. 從小開始

不需要一次準備10000個訓練樣本。開始時：
- 100個正例（正確配對）
- 100個負例（錯誤配對）
- 就能看到效果

### 2. 重點優化高頻查詢

```python
# 找出最常見的查詢類型
SELECT query_pattern, COUNT(*) as freq
FROM query_logs
GROUP BY query_pattern
ORDER BY freq DESC
LIMIT 20;
```

優先為這些高頻查詢準備訓練數據。

### 3. 使用真實反饋

如果您的系統有用戶反饋機制：
```python
# 最有價值的訓練數據
SELECT
    query,
    knowledge_id,
    CASE
        WHEN user_feedback = 'helpful' THEN 1.0
        ELSE 0.0
    END as label
FROM query_logs
WHERE user_feedback IS NOT NULL;
```

## 📈 預期效果

| 訓練數據量 | 預期準確率 | 訓練時間(CPU) |
|-----------|----------|-------------|
| 200 樣本   | 70-75%   | 30 分鐘      |
| 1000 樣本  | 80-85%   | 2 小時       |
| 5000 樣本  | 85-90%   | 6 小時       |
| 10000+ 樣本 | 90-95%  | 12 小時      |

## ⚡ 快速開始命令

```bash
# 1. 提取知識庫
python semantic_model/scripts/extract_knowledge.py

# 2. 生成訓練數據
python semantic_model/scripts/generate_training_data.py

# 3. 訓練模型
python semantic_model/scripts/train.py

# 4. 評估效果
python semantic_model/scripts/evaluate.py
```

完成這4步，您就有了一個訓練好的語義模型！