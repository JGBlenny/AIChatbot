"""
調試 IntentClassifier 返回值
"""
import os
import sys
import json

sys.path.insert(0, '/app')

from services.intent_classifier import IntentClassifier

# 初始化分類器
classifier = IntentClassifier(use_database=True)

# 測試問題
question = "退租時押金要怎麼退還？"

print("=" * 80)
print(f"測試問題: {question}")
print("=" * 80)

# 呼叫分類
result = classifier.classify(question)

# 完整輸出
print("\n完整返回結果:")
print(json.dumps(result, ensure_ascii=False, indent=2))

print("\n" + "=" * 80)
print("重點欄位檢查:")
print("=" * 80)
print(f"✓ intent_name: {result.get('intent_name')}")
print(f"✓ all_intents: {result.get('all_intents', 'KEY_NOT_FOUND')}")
print(f"✓ secondary_intents: {result.get('secondary_intents', 'KEY_NOT_FOUND')}")
print(f"✓ intent_ids: {result.get('intent_ids', 'KEY_NOT_FOUND')}")
print(f"✓ confidence: {result.get('confidence')}")

# 檢查 key 是否存在
print("\n欄位是否存在:")
print(f"  'all_intents' in result: {'all_intents' in result}")
print(f"  'secondary_intents' in result: {'secondary_intents' in result}")
print(f"  'intent_ids' in result: {'intent_ids' in result}")
