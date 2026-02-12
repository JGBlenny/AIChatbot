"""
直接測試 KnowledgeClassifier.classify_single_knowledge
"""
import os
import sys

sys.path.insert(0, '/app')

from services.knowledge_classifier import KnowledgeClassifier

# 初始化分類器
classifier = KnowledgeClassifier()

# 測試知識 ID 6
knowledge_id = 6
question_summary = "退租時押金要怎麼退還？"
answer = "房屋檢查完成後7個工作天內退還押金。需確認房屋狀況良好，如有損壞、欠繳費用或未恢復原狀會從押金中扣除。"

print("=" * 80)
print(f"測試知識 ID {knowledge_id} 的多意圖分類")
print("=" * 80)
print(f"問題：{question_summary}")
print(f"答案：{answer[:100]}...")
print("=" * 80)

result = classifier.classify_single_knowledge(
    knowledge_id=knowledge_id,
    question_summary=question_summary,
    answer=answer,
    assigned_by='auto'
)

print("\n📊 分類結果:")
print(f"  classified: {result['classified']}")
print(f"  intent_id: {result.get('intent_id')}")
print(f"  intent_name: {result.get('intent_name')}")
print(f"  confidence: {result.get('confidence')}")
print(f"  all_intents: {result.get('all_intents', [])}")
print(f"  secondary_intents: {result.get('secondary_intents', [])}")
print(f"  all_intent_ids: {result.get('all_intent_ids', [])}")

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
