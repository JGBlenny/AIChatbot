# 多意图知识评分机制说明

## 1. 多意图知识的数据结构

### 数据库设计

知识库使用 `knowledge_intent_mapping` 表来实现多对多关系：

```sql
CREATE TABLE knowledge_intent_mapping (
    knowledge_id INTEGER REFERENCES knowledge_base(id),
    intent_id INTEGER REFERENCES intents(id),
    intent_type VARCHAR(20) DEFAULT 'primary',  -- 'primary' 或 'secondary'
    PRIMARY KEY (knowledge_id, intent_id)
);
```

### 示例：多意图知识

```
知识 ID: 3041
问题："那押金會不會變來變去很複雜？"

意图标签：
1. primary: 租約變更／轉租 (intent_id: 9)
2. secondary: 押金/退款 (intent_id: 15)
```

这个知识同时涉及两个主题：租约变更和押金处理。

## 2. SQL 查询行为

### 查询特性

当执行知识检索时，SQL 的 `LEFT JOIN knowledge_intent_mapping` 会：

1. **对于多意图知识，返回多条记录**
   - 每个意图标签对应一条记录
   - 同一个 knowledge_id 会出现多次

2. **每条记录包含不同的 intent_id 和 intent_type**

### 示例查询结果

```
问题："押金會不會變來變去？"
LLM分类结果：押金/退款 (intent_id: 15)

SQL返回（部分示例）：
┌────────┬────────────┬───────┬──────────────┐
│ kb.id  │ intent_id  │ type  │ similarity   │
├────────┼────────────┼───────┼──────────────┤
│ 3041   │ 15         │ sec   │ 0.646        │  ← 匹配 secondary
│ 3041   │ 9          │ pri   │ 0.646        │  ← 同一知识，不同意图
│ 3065   │ 9          │ pri   │ 0.645        │
└────────┴────────────┴───────┴──────────────┘
```

## 3. Intent Boost 计算逻辑

### 当前实现 (vendor_knowledge_retriever.py:367-384)

```python
for row in rows:
    knowledge = dict(row)
    knowledge_intent_id = knowledge.get('intent_id')
    knowledge_intent_type = knowledge.get('intent_type')

    # 使用語義匹配器計算 boost
    if use_semantic_boost and knowledge_intent_id:
        boost, reason = self.intent_matcher.calculate_semantic_boost(
            intent_id,              # LLM分类的意图 (例: 15)
            knowledge_intent_id,    # 当前记录的意图标签
            knowledge_intent_type   # 'primary' 或 'secondary'
        )
```

### Boost 计算规则 (intent_semantic_matcher.py)

```python
def calculate_semantic_boost(query_intent_id, knowledge_intent_id, intent_type):
    # 1. 精确匹配
    if query_intent_id == knowledge_intent_id:
        if intent_type == 'primary':
            return 1.3, "精確匹配（主要意圖）"
        else:  # secondary
            return 1.2, "精確匹配（次要意圖）"

    # 2. 语义相似度计算
    similarity = cosine_similarity(
        query_intent_embedding,
        knowledge_intent_embedding
    )

    # 3. 根据相似度映射 boost
    if similarity >= 0.85:
        return 1.3, f"高度語義相關（相似度: {similarity:.3f}）"
    elif similarity >= 0.70:
        return 1.2, f"強語義相關（相似度: {similarity:.3f}）"
    elif similarity >= 0.55:
        return 1.1, f"中度語義相關（相似度: {similarity:.3f}）"
    elif similarity >= 0.40:
        return 1.05, f"弱語義相關（相似度: {similarity:.3f}）"
    else:
        return 1.0, f"語義不相關（相似度: {similarity:.3f}）"
```

## 4. 多意图知识的评分示例

### 场景 1：查询匹配 secondary 意图

```
用户问题："押金會不會變來變去？"
LLM分类：押金/退款 (intent_id: 15)

知识 3041:
- 语义相似度: 0.646
- 意图标签1: intent_id=15, type=secondary  ← 匹配！
- 意图标签2: intent_id=9, type=primary

SQL返回两条记录：
1. (id=3041, intent_id=15, type=secondary, similarity=0.646)
   → boost = 1.2x (精確匹配-次要意圖)
   → 加成後相似度 = 0.646 × 1.2 = 0.775

2. (id=3041, intent_id=9, type=primary, similarity=0.646)
   → boost = 1.0x~1.2x (根据语义相似度: intent 15 vs intent 9)
   → 加成後相似度 = 0.646 × boost

系统选择：取 boost 更高的那条记录（第1条）
```

### 场景 2：查询匹配 primary 意图

```
用户问题："換租客押金怎麼算？"
LLM分类：租約變更／轉租 (intent_id: 9)

知识 3041:
SQL返回两条记录：
1. (id=3041, intent_id=9, type=primary, similarity=0.750)
   → boost = 1.3x (精確匹配-主要意圖)
   → 加成後相似度 = 0.750 × 1.3 = 0.975

2. (id=3041, intent_id=15, type=secondary, similarity=0.750)
   → boost = 1.1x~1.2x (根据语义相似度: intent 9 vs intent 15)
   → 加成後相似度 = 0.750 × boost

系统选择：第1条（primary 匹配的 boost 更高）
```

## 5. 重复记录的处理

### 问题：同一知识出现多次

当前实现中，**同一个知识可能以不同的 intent_id 出现多次**。

### 当前行为（vendor_knowledge_retriever.py:362-400）

```python
candidates = []
for row in rows:  # SQL返回的所有记录（可能包含重复的knowledge_id）
    knowledge = dict(row)
    # 计算boost
    boost, reason = self.intent_matcher.calculate_semantic_boost(...)
    boosted_similarity = base_similarity * boost

    # 过滤
    if boosted_similarity >= similarity_threshold:
        candidates.append(knowledge)

# 排序
candidates.sort(key=lambda x: (-x['scope_weight'], -x['boosted_similarity'], ...))

# 取 top_k
results = candidates[:top_k]
```

### 潜在问题

**同一知识可能占用多个top_k位置**：

```
候选结果（排序后）：
1. ID 3041 (intent=15, boost=1.2, score=0.775)
2. ID 3041 (intent=9, boost=1.1, score=0.711)  ← 重复！
3. ID 2048 (intent=15, boost=1.3, score=0.650)
4. ID 2050 (intent=15, boost=1.1, score=0.620)
5. ID 2051 (intent=9, boost=1.0, score=0.610)

如果 top_k=5，用户实际只看到 4 个不同的知识（3041出现2次）
```

## 6. 建议的优化方案

### 方案 A：去重，保留最高分

```python
# 在排序后、取top_k前，对knowledge_id去重
seen_ids = set()
unique_candidates = []
for candidate in sorted_candidates:
    if candidate['id'] not in seen_ids:
        seen_ids.add(candidate['id'])
        unique_candidates.append(candidate)

results = unique_candidates[:top_k]
```

**优点**：
- 确保 top_k 返回 k 个不同的知识
- 自动选择每个知识的最高分版本

**缺点**：
- 丢失了"为什么这个知识被选中"的信息（可能是因为匹配了secondary意图）

### 方案 B：SQL层面去重（推荐）

修改SQL查询，使用 `DISTINCT ON` 或窗口函数：

```sql
SELECT DISTINCT ON (kb.id)
    kb.id,
    kb.question_summary,
    kim.intent_id,
    kim.intent_type,
    base_similarity,
    -- 预计算最大boost（所有意图中最高的）
    MAX(boost_value) OVER (PARTITION BY kb.id) as max_boost
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
...
ORDER BY kb.id, max_boost DESC
```

### 方案 C：保留当前行为 + 文档说明

如果多意图知识占用多个位置是预期行为（例如：想让用户看到不同角度的匹配理由），则：
1. 在返回结果中保留 `intent_id` 和 `boost_reason`
2. 前端显示时标注"此知识同时匹配多个意图"

## 7. 实际测试结果

### 测试设置

```sql
-- 给知识3041添加第二个意图
INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type)
VALUES (3041, 15, 'secondary');

-- 查询结果
知识 3041:
- primary: 租約變更／轉租 (9)
- secondary: 押金/退款 (15)
```

### 测试查询："押金會不會變來變去？"

```
LLM分类: 押金/退款 (intent_id: 15)

预期：
1. SQL返回 ID 3041 的两条记录（intent_id=15和9）
2. intent_id=15 的记录应该获得更高的boost（1.2x）
3. 最终候选列表可能包含两条 ID 3041

实际观察：
- 需要查看详细日志确认
- 如果信心度过低，可能触发unclear路径，跳过hybrid retrieval
```

## 8. 总结

### 当前多意图评分机制

1. **SQL查询**：返回所有匹配的 (knowledge_id, intent_id) 组合
2. **Boost计算**：每条记录独立计算boost（基于intent匹配度）
3. **排序**：按 scope_weight → boosted_similarity → priority
4. **取top_k**：可能包含重复的knowledge_id

### 关键特性

- ✅ **支持多意图标签**：一个知识可以有多个primary/secondary意图
- ✅ **智能boost**：根据匹配的意图类型（primary/secondary）给予不同加成
- ✅ **语义相似度**：即使不精确匹配，也能通过语义相似度获得boost
- ⚠️ **可能重复**：同一知识可能在top_k中出现多次

### 推荐做法

1. **短期**：使用方案A在Python中去重
2. **中期**：实现方案B，在SQL层面优化
3. **长期**：根据实际使用反馈，决定是否需要保留多次出现的能力
