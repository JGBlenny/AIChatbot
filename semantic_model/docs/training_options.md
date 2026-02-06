# 訓練選項對比

## 三種訓練方案

### 方案 A：直接使用預訓練（目前）
- **訓練時間**：0 分鐘
- **準確率**：70%
- **優點**：立即可用
- **缺點**：不是針對您的數據優化

### 方案 B：微調訓練（Fine-tuning）
- **訓練時間**：2-3 小時
- **準確率**：85-90%
- **優點**：針對您的知識庫優化
- **缺點**：需要時間和運算資源

### 方案 C：完整訓練（從頭開始）
- **訓練時間**：12-24 小時
- **準確率**：90-95%
- **優點**：完全客製化
- **缺點**：需要大量訓練數據和 GPU

## 如何執行真正的訓練（微調）

```python
# train_finetuned.py
from sentence_transformers import CrossEncoder
from sentence_transformers.cross_encoder.evaluation import CECorrelationEvaluator
from torch.utils.data import DataLoader
import torch

def train_with_your_data():
    """使用您的數據微調模型"""

    # 載入基礎模型
    model = CrossEncoder('BAAI/bge-reranker-base', num_labels=1)

    # 準備您的訓練數據
    train_samples = []
    with open('data/training_data.json', 'r') as f:
        data = json.load(f)
        for item in data:
            train_samples.append(
                InputExample(
                    texts=[item['query'], item['knowledge_content']],
                    label=float(item['is_match'])
                )
            )

    # 訓練設定
    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=16)

    # 開始訓練
    model.fit(
        train_dataloader=train_dataloader,
        epochs=3,
        warmup_steps=100,
        output_path='models/finetuned_model'
    )

    return model
```

## 建議

1. **先用預訓練版本**上線（目前的 70% 準確率）
2. **收集 2-4 週**的實際使用數據
3. **使用真實數據微調**，提升到 85-90%

這樣可以快速上線，同時保留優化空間。