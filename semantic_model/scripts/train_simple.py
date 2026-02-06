#!/usr/bin/env python3
"""
簡單的語義模型訓練腳本
直接使用預訓練的 BAAI/bge-reranker-base
"""

import json
import os
import sys
from datetime import datetime
from sentence_transformers import CrossEncoder
import numpy as np

def main():
    print("="*60)
    print("語義模型載入與測試")
    print("="*60)

    # 1. 載入訓練數據以進行測試
    print("\n1. 載入測試數據...")
    test_file = "data/test_data.json"
    if not os.path.exists(test_file):
        print("❌ 找不到測試數據")
        return

    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    print(f"✅ 載入了 {len(test_data)} 個測試樣本")

    # 2. 載入預訓練模型
    print("\n2. 載入預訓練模型...")
    print("   模型: BAAI/bge-reranker-base")
    print("   說明: 這是一個已訓練好的語義理解模型")

    try:
        model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)
        print("✅ 模型載入成功!")

        # 3. 測試模型效果
        print("\n3. 測試模型效果...")
        print("-" * 40)

        # 測試幾個範例
        test_samples = test_data[:10]
        correct = 0

        for i, sample in enumerate(test_samples):
            query = sample["query"]
            content = sample["knowledge_content"]
            actual_match = sample["is_match"]

            # 預測
            pairs = [[query, content]]
            scores = model.predict(pairs)
            score = scores[0]
            predicted_match = score > 0.5

            # 判斷是否正確
            is_correct = predicted_match == actual_match
            if is_correct:
                correct += 1

            # 顯示結果（只顯示前3個）
            if i < 3:
                result = "✅" if is_correct else "❌"
                print(f"\n{result} 範例 {i+1}:")
                print(f"   查詢: {query[:50]}...")
                print(f"   文檔: {content[:50]}...")
                print(f"   相關性分數: {score:.3f}")
                print(f"   預測: {'匹配' if predicted_match else '不匹配'}")
                print(f"   實際: {'匹配' if actual_match else '不匹配'}")

        accuracy = correct / len(test_samples) * 100
        print(f"\n準確率: {accuracy:.1f}% ({correct}/{len(test_samples)})")

        # 4. 保存模型
        print("\n4. 保存模型...")
        model_dir = "models/semantic_v1"
        os.makedirs(model_dir, exist_ok=True)

        # 保存模型
        model.save(model_dir)

        # 保存配置信息
        config = {
            "base_model": "BAAI/bge-reranker-base",
            "model_type": "CrossEncoder",
            "max_length": 512,
            "test_accuracy": accuracy,
            "saved_at": datetime.now().isoformat()
        }

        with open(f"{model_dir}/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"✅ 模型已保存到: {model_dir}")

        # 5. 總結
        print("\n" + "="*60)
        print("✅ 完成！")
        print("="*60)
        print("\n模型資訊：")
        print(f"- 基礎模型: BAAI/bge-reranker-base")
        print(f"- 測試準確率: {accuracy:.1f}%")
        print(f"- 保存位置: {model_dir}")

        if accuracy >= 70:
            print("\n💡 模型表現良好，可以開始使用！")
        else:
            print("\n⚠️ 準確率較低，建議檢查數據品質")

        print("\n下一步：")
        print("1. 將模型整合到您的系統")
        print("2. 使用模型進行語義匹配")
        print("3. 持續收集反饋優化")

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        print("\n可能的解決方案：")
        print("1. 確認網路連接")
        print("2. 檢查 sentence-transformers 安裝: pip install sentence-transformers")
        print("3. 嘗試離線下載模型")

if __name__ == "__main__":
    main()