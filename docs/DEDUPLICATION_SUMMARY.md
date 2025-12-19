# 多意图知识去重功能总结

## 实现位置

文件：`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/vendor_knowledge_retriever.py`

方法：`retrieve_knowledge_hybrid()` (line 413-426)

## 功能说明

### 问题背景

在支持多意图标签后，同一个知识可能在 SQL 查询中返回多条记录（每个意图标签一条）。例如：

```
知识 ID 3041: "那押金會不會變來變去很複雜？"
- primary: 租約變更／轉租 (intent_id: 9)
- secondary: 押金/退款 (intent_id: 15)

SQL 查询返回：
1. (id=3041, intent_id=15, similarity=0.646, boost=1.15x, final_score=0.743)
2. (id=3041, intent_id=9, similarity=0.646, boost=1.0x, final_score=0.646)
```

如果不去重，ID 3041 会在 top_k 结果中占用两个位置。

### 解决方案

在排序后、取 top_k 前，对 `knowledge_id` 去重，只保留每个知识的最高分版本：

```python
# ✅ 去重：對於多意圖知識，只保留最高分版本
seen_ids = set()
unique_candidates = []
duplicates_removed = 0
for candidate in candidates:
    knowledge_id = candidate['id']
    if knowledge_id not in seen_ids:
        seen_ids.add(knowledge_id)
        unique_candidates.append(candidate)
    else:
        duplicates_removed += 1

if duplicates_removed > 0:
    print(f"   ℹ️  去重：移除了 {duplicates_removed} 個重複的知識（多意圖知識的較低分版本）")

# 取 top_k
results = unique_candidates[:top_k]
```

## 工作流程

```
1. SQL 查询返回所有匹配记录（含多意图知识的多条记录）
         ↓
2. 计算每条记录的 intent_boost
         ↓
3. 过滤：只保留 boosted_similarity >= threshold 的记录
         ↓
4. 排序：按 scope_weight → boosted_similarity → priority
         ↓
5. ✅ 去重：对 knowledge_id 去重，保留首次出现的（即最高分的）
         ↓
6. 取 top_k
```

## 实际测试案例

### 测试 1: 查询"押金會不會變來變去？"

**设置**：
```sql
知识 ID 3041 有两个意图：
- primary: 租約變更／轉租 (9)
- secondary: 押金/退款 (15)
```

**用户查询**：
```
问题："押金會不會變來變去？"
LLM分类：押金/退款 (intent_id: 15)
```

**结果**：
```
Found 15 SQL candidates (will rerank and filter):
After semantic boost and filtering: 15 candidates
ℹ️  去重：移除了 1 個重複的知識（多意圖知識的較低分版本）

最终结果：
1. ★ ID 3041 (原始: 0.646, boost: 1.15x [精確匹配（次要意圖）],
              加成後: 0.743, intent: 15)
```

**分析**：
- ID 3041 的两条记录（intent=15 和 intent=9）都被返回
- intent=15 版本获得更高boost（1.15x，匹配 secondary）
- intent=9 版本获得较低boost（语义相似度较低）
- 去重后只保留 intent=15 版本
- **成功移除了 1 个重复**

### 测试 2: 查询"換租客押金怎麼處理？"

**用户查询**：
```
问题："換租客押金怎麼處理？"
LLM分类：租約／合約 (intent_id: 12)
```

**结果**：
```
Found 15 SQL candidates
After semantic boost and filtering: 15 candidates
(无去重信息 - 没有重复的knowledge_id)

最终结果：
1. ID 3197 (boost: 1.20x, score: 0.876)
2. ID 3032 (boost: 1.10x, score: 0.801)
3. ID 3056 (boost: 1.10x, score: 0.801)
...
```

**分析**：
- 没有触发去重，说明结果中没有重复的 knowledge_id
- 系统正常工作

## 优势

### ✅ 确保多样性
- top_k 返回 k 个**不同**的知识
- 避免同一知识占用多个位置

### ✅ 自动选择最佳版本
- 排序确保最高分版本排在前面
- 去重自动保留最高分版本
- 无需手动判断哪个意图标签更相关

### ✅ 保留调试信息
- 最终结果中的 `intent_id` 显示了匹配的意图
- `boost_reason` 解释了为什么选择这个版本

### ✅ 低开销
- 时间复杂度：O(n)，其中 n 是候选数量
- 空间复杂度：O(k)，其中 k 是不同的 knowledge_id 数量

## 日志输出

### 有去重时：
```
ℹ️  去重：移除了 1 個重複的知識（多意圖知識的較低分版本）
```

### 无去重时：
（无输出 - 静默通过）

## 注意事项

1. **去重发生在排序之后**
   - 确保保留的是最高分版本
   - 如果改变排序逻辑，去重结果也会改变

2. **适用范围**
   - 仅在 `retrieve_knowledge_hybrid()` 中实现
   - 其他检索方法（如 `retrieve_knowledge()`）不受影响

3. **调试模式**
   - 去重不受 `return_debug_info` 参数影响
   - 始终执行去重，保证结果一致性

4. **向后兼容**
   - 对于单意图知识（大多数情况），行为不变
   - 只影响有多个意图标签的知识

## 未来优化建议

### 选项 1: SQL 层面去重
在 SQL 查询中使用 `DISTINCT ON` 或窗口函数：
```sql
SELECT DISTINCT ON (kb.id)
    kb.*,
    MAX(boost) OVER (PARTITION BY kb.id) as max_boost
FROM ...
ORDER BY kb.id, max_boost DESC
```

**优点**：减少传输数据量，提高性能

**缺点**：SQL 复杂度增加，boost 计算需要在 SQL 中完成

### 选项 2: 返回所有版本（可选）
添加参数 `include_all_intents=True`，允许返回同一知识的所有版本：
```python
if not include_all_intents:
    # 执行去重
    ...
```

**用例**：调试时查看所有可能的匹配方式

## 相关文档

- [多意图知识评分机制](./MULTI_INTENT_SCORING.md) - 详细说明多意图知识的评分逻辑
- [语义意图匹配](./SEMANTIC_INTENT_MATCHING.md) - Intent boost 的计算方法
