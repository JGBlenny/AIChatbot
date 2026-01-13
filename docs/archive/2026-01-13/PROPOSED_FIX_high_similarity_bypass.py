# 🔧 建議修正：高相似度繞過意圖過濾
# 文件: rag-orchestrator/services/vendor_knowledge_retriever.py
# 位置: 約第 365-412 行（Python 階段過濾邏輯）

# ========================================
# 修正前代碼 (當前)
# ========================================
"""
candidates = []
filtered_count = 0
for row in rows:
    knowledge = dict(row)
    knowledge_intent_id = knowledge.get('intent_id')
    knowledge_intent_type = knowledge.get('intent_type')

    # 使用語義匹配器計算 boost
    intent_semantic_similarity = None
    if use_semantic_boost and knowledge_intent_id:
        boost, reason, intent_semantic_similarity = self.intent_matcher.calculate_semantic_boost(
            intent_id,
            knowledge_intent_id,
            knowledge_intent_type
        )
    else:
        # 沒有意圖標註或不使用語義加成
        if knowledge_intent_id == intent_id:
            boost = 1.3
            reason = "精確匹配"
            intent_semantic_similarity = 1.0
        elif knowledge_intent_id in all_intent_ids:
            boost = 1.1
            reason = "次要意圖匹配"
            intent_semantic_similarity = 0.8
        else:
            boost = 1.0
            reason = "無意圖匹配"
            intent_semantic_similarity = 0.0

    # 重新計算加成後相似度
    base_similarity = knowledge['base_similarity']
    boosted_similarity = base_similarity * boost

    # ✅ 在 Python 中過濾：只保留加成後 >= similarity_threshold 的結果
    if boosted_similarity < similarity_threshold:
        filtered_count += 1
        continue

    # 更新 boost 和加成後相似度
    knowledge['intent_boost'] = boost
    knowledge['boosted_similarity'] = boosted_similarity
    knowledge['boost_reason'] = reason
    knowledge['intent_semantic_similarity'] = intent_semantic_similarity

    candidates.append(knowledge)
"""

# ========================================
# 修正後代碼 (建議)
# ========================================
"""
# ✅ 配置：高相似度繞過閾值
HIGH_SIMILARITY_BYPASS = 0.9  # 可以移到 __init__ 或配置文件

candidates = []
filtered_count = 0
bypassed_count = 0  # 統計繞過的數量

for row in rows:
    knowledge = dict(row)
    knowledge_intent_id = knowledge.get('intent_id')
    knowledge_intent_type = knowledge.get('intent_type')
    base_similarity = knowledge['base_similarity']

    # 🎯 新增：高相似度繞過邏輯
    if base_similarity >= HIGH_SIMILARITY_BYPASS:
        # 完美匹配：直接通過，不考慮意圖
        boost = 1.0  # 不需要額外加成
        boosted_similarity = base_similarity  # 使用原始相似度
        reason = "完美匹配 (繞過意圖過濾)"
        intent_semantic_similarity = None

        knowledge['intent_boost'] = boost
        knowledge['boosted_similarity'] = boosted_similarity
        knowledge['boost_reason'] = reason
        knowledge['intent_semantic_similarity'] = intent_semantic_similarity

        candidates.append(knowledge)
        bypassed_count += 1
        continue  # 跳過正常的意圖匹配邏輯

    # 原有邏輯：正常的意圖匹配和加成計算
    intent_semantic_similarity = None
    if use_semantic_boost and knowledge_intent_id:
        boost, reason, intent_semantic_similarity = self.intent_matcher.calculate_semantic_boost(
            intent_id,
            knowledge_intent_id,
            knowledge_intent_type
        )
    else:
        # 沒有意圖標註或不使用語義加成
        if knowledge_intent_id == intent_id:
            boost = 1.3
            reason = "精確匹配"
            intent_semantic_similarity = 1.0
        elif knowledge_intent_id in all_intent_ids:
            boost = 1.1
            reason = "次要意圖匹配"
            intent_semantic_similarity = 0.8
        else:
            boost = 1.0
            reason = "無意圖匹配"
            intent_semantic_similarity = 0.0

    # 重新計算加成後相似度
    boosted_similarity = base_similarity * boost

    # ✅ 在 Python 中過濾：只保留加成後 >= similarity_threshold 的結果
    if boosted_similarity < similarity_threshold:
        filtered_count += 1
        continue

    # 更新 boost 和加成後相似度
    knowledge['intent_boost'] = boost
    knowledge['boosted_similarity'] = boosted_similarity
    knowledge['boost_reason'] = reason
    knowledge['intent_semantic_similarity'] = intent_semantic_similarity

    candidates.append(knowledge)

# 🎯 新增：輸出繞過統計
if bypassed_count > 0:
    print(f"   ⭐ 高相似度繞過: {bypassed_count} 個知識 (>= {HIGH_SIMILARITY_BYPASS})")

print(f"   After semantic boost and filtering: {len(candidates)} candidates (filtered out: {filtered_count})")
"""

# ========================================
# 使用說明
# ========================================
"""
1. 修改位置:
   - 文件: rag-orchestrator/services/vendor_knowledge_retriever.py
   - 方法: hybrid_retrieve_with_semantic_boost
   - 行數: 約 365-412 行

2. 配置建議:
   - HIGH_SIMILARITY_BYPASS = 0.9  # 推薦值，可調整為 0.85-0.95

3. 測試方法:
   a) 創建意圖錯誤分類的知識
   b) 查詢與知識完全相同的文本
   c) 確認即使意圖不匹配也能找到

4. 監控指標:
   - bypassed_count: 有多少知識通過繞過邏輯
   - 檢索結果質量是否下降
   - 是否出現意圖完全不相關的結果

5. 回滾:
   - 如果出現問題，將 HIGH_SIMILARITY_BYPASS 設為 1.0 (永不繞過)
   - 或直接移除繞過邏輯
"""

# ========================================
# 進階選項：可配置策略
# ========================================
"""
# 可以在 __init__ 或配置文件中添加:

class VendorKnowledgeRetriever:
    def __init__(self, ...):
        # ... 現有代碼 ...

        # 🎯 檢索策略配置
        self.retrieval_config = {
            "enable_high_similarity_bypass": True,    # 是否啟用繞過
            "high_similarity_threshold": 0.9,          # 繞過閾值
            "medium_similarity_threshold": 0.7,        # 中等相似度閾值
            "strict_intent_below_threshold": 0.5,      # 此閾值以下嚴格意圖匹配
        }

# 然後在檢索邏輯中使用:
HIGH_SIMILARITY_BYPASS = self.retrieval_config.get("high_similarity_threshold", 0.9)

if self.retrieval_config.get("enable_high_similarity_bypass", True):
    if base_similarity >= HIGH_SIMILARITY_BYPASS:
        # 繞過邏輯...
"""

# ========================================
# 測試案例代碼
# ========================================
"""
# 測試腳本: test_high_similarity_bypass.py

import asyncio
from services.vendor_knowledge_retriever import VendorKnowledgeRetriever

async def test_high_similarity_bypass():
    retriever = VendorKnowledgeRetriever(...)

    # 測試 1: 完美匹配 + 意圖錯誤分類
    results = await retriever.hybrid_retrieve_with_semantic_boost(
        query="你好，我要續約，新的合約甚麼時候會提供?",
        intent_id=10,  # 租期／到期
        vendor_id=2,
        target_user='tenant',
        top_k=5
    )

    # 驗證知識 1262 是否返回
    knowledge_ids = [r['id'] for r in results]
    assert 1262 in knowledge_ids, "應該找到知識 1262 (即使意圖不匹配)"

    # 檢查是否標記為繞過
    kb_1262 = next(r for r in results if r['id'] == 1262)
    assert "繞過" in kb_1262['boost_reason'], "應該標記為繞過意圖過濾"

    print("✅ 測試通過：高相似度繞過正常運作")

if __name__ == "__main__":
    asyncio.run(test_high_similarity_bypass())
"""
