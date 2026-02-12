"""
測試 IntentClassifier 的多意圖分類功能
"""
import os
import sys

# 設定環境變數（使用 Docker compose 的服務名稱）
os.environ['DB_HOST'] = os.getenv('DB_HOST', 'postgres')
os.environ['DB_PORT'] = os.getenv('DB_PORT', '5432')
os.environ['DB_USER'] = os.getenv('DB_USER', 'aichatbot')
os.environ['DB_PASSWORD'] = os.getenv('DB_PASSWORD', 'aichatbot_password')
os.environ['DB_NAME'] = os.getenv('DB_NAME', 'aichatbot_admin')

sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

from services.intent_classifier import IntentClassifier

# 初始化分類器
classifier = IntentClassifier(use_database=True)

# 測試問題
test_questions = [
    "退租時押金要怎麼退還？",
    "我想退租，押金什麼時候會退給我？需要繳清所有費用嗎？",
    "租金如何計算？可以刷卡嗎？",
    "門鎖壞了要報修，費用是從押金扣還是另外收費？"
]

print("=" * 80)
print("測試 IntentClassifier 多意圖分類")
print("=" * 80)

for i, question in enumerate(test_questions, 1):
    print(f"\n{'=' * 80}")
    print(f"測試 {i}: {question}")
    print('-' * 80)

    result = classifier.classify(question)

    print(f"✓ 主要意圖: {result['intent_name']}")
    print(f"✓ 意圖類型: {result['intent_type']}")
    print(f"✓ 信心度: {result['confidence']:.2f}")
    print(f"✓ 關鍵字: {', '.join(result.get('keywords', []))}")
    print(f"✓ 所有意圖: {result.get('all_intents', [])}")
    print(f"✓ 次要意圖: {result.get('secondary_intents', [])}")
    print(f"✓ 意圖 IDs: {result.get('intent_ids', [])}")

    if result.get('reasoning'):
        print(f"✓ 分類理由: {result['reasoning']}")

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
