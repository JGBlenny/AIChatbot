# 测试情境简化实施指南

## ✅ 已完成的改动

### 1. 数据库迁移 ✅

**文件:** `database/migrations-legacy/40-simplify-test-scenarios-for-llm-eval.sql`

**改动内容:**
- ✅ 删除字段：`expected_category`, `expected_keywords`, `expected_intent_id`
- ✅ 简化 `priority` 为 3 档（30/50/80）
- ✅ 新增字段：`expected_answer`, `min_quality_score`
- ✅ 迁移历史数据：`expected_category` → `notes`
- ✅ 重建视图：`v_test_scenario_details`, `v_pending_test_scenarios`

**结果:**
```
总测试情境数: 76
Priority 分布: 50档(中):53个, 80档(高):23个
已删除字段: expected_category, expected_keywords, expected_intent_id
新增字段: expected_answer, min_quality_score
```

### 2. 后端 API 模型 ✅

**文件:** `knowledge-admin/backend/routes_test_scenarios.py`

**改动内容:**
- ✅ 更新 `TestScenarioCreate` 模型
  - 移除：`expected_category`, `expected_intent_id`, `expected_keywords`
  - 新增：`expected_answer`, `min_quality_score`
  - 添加 priority 验证器（只允许 30/50/80）

- ✅ 更新 `TestScenarioUpdate` 模型
  - 移除：`expected_category`, `expected_intent_id`, `expected_keywords`
  - 新增：`expected_answer`, `min_quality_score`

- ✅ 更新 `create_test_scenario` 端点
  - 修改 INSERT 语句
  - 新建测试直接设为 `approved` 状态

- ✅ 更新 `update_test_scenario` 端点
  - 移除已删除字段的更新逻辑
  - 添加新字段的更新逻辑

---

## 🔄 需要完成的改动

### 3. 前端表单和显示逻辑

#### 文件A: `knowledge-admin/frontend/src/views/TestScenariosView.vue`

**需要修改的位置:**

#### (1) 移除表格列显示 (第 88行附近)

```vue
<!-- 删除这一列 -->
<del>
<td>{{ scenario.expected_category || '-' }}</td>
</del>
```

#### (2) 修改表头 (第 75行附近)

```vue
<thead>
  <tr>
    <th width="5%">ID</th>
    <th width="30%">測試問題</th>
    <!-- 删除这一列 -->
    <del><th width="15%">預期分類</th></del>
    <th width="8%">難度</th>
    <th width="8%">狀態</th>
    <th width="10%">知識狀態</th>
    <th width="12%">統計</th>
    <th width="17%">操作</th>
  </tr>
</thead>
```

#### (3) 修改表单 - 移除旧字段 (第 190-215行)

```vue
<form @submit.prevent="saveScenario">
  <div class="form-group">
    <label>測試問題 *</label>
    <textarea
      v-model="formData.test_question"
      required
      rows="3"
      placeholder="輸入要測試的問題..."
    ></textarea>
  </div>

  <!-- 删除这些字段 -->
  <del>
  <div class="form-row">
    <div class="form-group">
      <label>預期分類</label>
      <input
        v-model="formData.expected_category"
        placeholder="例如：帳務問題"
      />
    </div>
    ...
  </div>

  <div class="form-group">
    <label>預期關鍵字（逗號分隔）</label>
    <input
      v-model="formData.expected_keywords"
      placeholder="關鍵字1, 關鍵字2, 關鍵字3"
    />
  </div>
  </del>

  <!-- 修改 Priority 字段 -->
  <div class="form-group">
    <label>優先級</label>
    <select v-model.number="formData.priority" required>
      <option value="30">低優先級（30）- 可延後測試</option>
      <option value="50" selected>中等優先級（50）- 默認</option>
      <option value="80">高優先級（80）- 核心功能</option>
    </select>
    <small class="hint">優先級影響測試執行順序</small>
  </div>

  <!-- 新增字段 -->
  <div class="form-group">
    <label>標準答案（可選）</label>
    <textarea
      v-model="formData.expected_answer"
      rows="4"
      placeholder="提供標準答案用於 LLM 語義對比評估（可選）"
    ></textarea>
    <small class="hint">用於更精確的答案質量評估</small>
  </div>

  <div class="form-group">
    <label>最低質量要求（1-5分）</label>
    <input
      v-model.number="formData.min_quality_score"
      type="number"
      min="1"
      max="5"
      step="0.1"
      placeholder="3.0"
    />
    <small class="hint">LLM 評估分數需達到此標準才算通過（默認 3.0）</small>
  </div>

  <div class="form-actions">
    <button type="button" @click="closeDialog" class="btn-secondary">
      取消
    </button>
    <button type="submit" class="btn-primary">
      {{ editingScenario ? '更新' : '建立' }}
    </button>
  </div>
</form>
```

#### (4) 修改 data() - 更新 formData (第 276-283行)

```javascript
formData: {
  test_question: '',
  // 删除这些
  // expected_category: '',
  // expected_keywords: '',

  difficulty: 'medium',
  priority: 50,  // 默认中等优先级
  notes: '',

  // 新增这些
  expected_answer: '',
  min_quality_score: 3.0
}
```

#### (5) 修改 editScenario 方法 (第 346-356行)

```javascript
editScenario(scenario) {
  this.editingScenario = scenario;
  this.formData = {
    test_question: scenario.test_question,
    // 删除这些
    // expected_category: scenario.expected_category || '',
    // expected_keywords: scenario.expected_keywords?.join(', ') || '',

    difficulty: scenario.difficulty,
    priority: scenario.priority || 50,
    notes: scenario.notes || '',

    // 新增这些
    expected_answer: scenario.expected_answer || '',
    min_quality_score: scenario.min_quality_score || 3.0
  };
}
```

#### (6) 修改 saveScenario 方法 (第 358-384行)

```javascript
async saveScenario() {
  try {
    const data = {
      test_question: this.formData.test_question,
      difficulty: this.formData.difficulty,
      priority: this.formData.priority,
      notes: this.formData.notes,
      expected_answer: this.formData.expected_answer,
      min_quality_score: this.formData.min_quality_score,

      // 删除这些
      // expected_category: this.formData.expected_category,
      // expected_keywords: this.formData.expected_keywords
      //   .split(',')
      //   .map(k => k.trim())
      //   .filter(k => k),
    };

    if (this.editingScenario) {
      await axios.put(`/api/test/scenarios/${this.editingScenario.id}`, data);
      alert('測試情境已更新！');
    } else {
      await axios.post('/api/test/scenarios', data);
      alert('測試情境已建立！');
    }

    this.closeDialog();
    this.loadScenarios();
    this.loadStats();
  } catch (error) {
    console.error('儲存失敗:', error);
    alert('儲存失敗：' + (error.response?.data?.detail || error.message));
  }
}
```

#### (7) 修改 closeDialog 方法 (第 462-473行)

```javascript
closeDialog() {
  this.showCreateDialog = false;
  this.editingScenario = null;
  this.formData = {
    test_question: '',
    difficulty: 'medium',
    priority: 50,
    notes: '',
    expected_answer: '',
    min_quality_score: 3.0
  };
}
```

---

### 4. 修改测试框架默认配置

#### 文件: `scripts/knowledge_extraction/backtest_framework.py`

#### (1) 修改默认 quality_mode (第 28-32行)

```python
def __init__(
    self,
    base_url: str = "http://localhost:8100",
    vendor_id: int = 1,
    quality_mode: str = "detailed",  # ← 改为 detailed（原来是 basic）
    use_database: bool = True
):
```

#### (2) 修改 SELECT 查询 (第 103-110行, 145-152行, 195-202行)

移除已删除的字段：

```python
query = """
    SELECT
        ts.id,
        ts.test_question,
        -- 删除这些
        -- ts.expected_category,
        -- ts.expected_keywords,

        ts.difficulty,
        ts.notes,
        ts.priority,
        ts.total_runs,
        ts.pass_count,
        ts.fail_count,
        ts.avg_score,
        ts.last_run_at,

        -- 新增这些（如果需要）
        ts.expected_answer,
        ts.min_quality_score,

        CASE
            WHEN ts.total_runs = 0 THEN 100
            ...
        END as selection_priority
    FROM test_scenarios ts
    WHERE ts.is_active = TRUE
      AND ts.status = 'approved'
    ...
```

#### (3) 更新 evaluate_answer 说明 (第 420-527行)

在方法开头添加注释：

```python
def evaluate_answer(
    self,
    test_scenario: Dict,
    system_response: Dict
) -> Dict:
    """評估答案（基礎模式）

    注意：此方法僅在 basic/hybrid 模式使用
    如使用 detailed 模式，則完全依賴 LLM 評估

    已移除字段：
    - expected_category (改用 LLM intent_match 評估)
    - expected_keywords (改用 LLM completeness 評估)
    """
    # ... 现有代码保持不变（因为 detailed 模式不会调用此方法）
```

---

### 5. 其他可能需要修改的文件

#### 可选修改（如果使用到这些页面）:

1. **`knowledge-admin/frontend/src/views/BacktestView.vue`**
   - 如果显示了 expected_category/keywords，删除相关显示

2. **`knowledge-admin/frontend/src/views/PendingReviewView.vue`**
   - 同上

3. **`knowledge-admin/frontend/src/components/review/ScenarioReviewTab.vue`**
   - 同上

4. **`rag-orchestrator/services/knowledge_import_service.py`** (第 978-992行, 1048-1064行)
   - 创建测试情境时不再设置 expected_category
   - 直接设置默认 min_quality_score

---

## 📝 测试验证清单

### 数据库验证

```sql
-- 1. 验证字段已删除
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'test_scenarios'
  AND column_name IN ('expected_category', 'expected_keywords', 'expected_intent_id');
-- 应该返回 0 行

-- 2. 验证新字段存在
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'test_scenarios'
  AND column_name IN ('expected_answer', 'min_quality_score', 'priority');

-- 3. 验证 priority 只有 3 个值
SELECT DISTINCT priority
FROM test_scenarios
ORDER BY priority;
-- 应该只返回 30, 50, 80

-- 4. 验证历史数据迁移
SELECT id, notes
FROM test_scenarios
WHERE notes LIKE '%【遗留数据】%'
LIMIT 5;
```

### API 验证

```bash
# 1. 测试创建新情境
curl -X POST http://localhost:8000/api/test/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "test_question": "测试问题",
    "difficulty": "medium",
    "priority": 50,
    "expected_answer": "这是标准答案",
    "min_quality_score": 3.5
  }'

# 2. 测试 priority 验证
curl -X POST http://localhost:8000/api/test/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "test_question": "测试问题",
    "priority": 60
  }'
# 应该返回错误：priority 必须是 30/50/80

# 3. 测试更新
curl -X PUT http://localhost:8000/api/test/scenarios/1 \
  -H "Content-Type: application/json" \
  -d '{
    "priority": 80,
    "min_quality_score": 4.0
  }'
```

### 前端验证

1. 访问 http://localhost:8087/test-scenarios
2. 点击"新增测试情境"
3. 确认表单：
   - ✅ 没有"预期分类"字段
   - ✅ 没有"预期关键字"字段
   - ✅ Priority 只有 3 个选项（30/50/80）
   - ✅ 有"标准答案"字段
   - ✅ 有"最低质量要求"字段
4. 创建新测试，确认保存成功
5. 编辑现有测试，确认数据正确加载

### 测试框架验证

```bash
# 使用 detailed 模式运行测试
cd /Users/lenny/jgb/AIChatbot
python3 scripts/knowledge_extraction/backtest_framework.py

# 检查输出
# 应该看到：
# ✅ 品質評估模式: detailed
# ✅ LLM 评估分数（relevance, completeness, accuracy）
# ❌ 不应该看到 expected_category 或 expected_keywords 相关的警告
```

---

## 🚀 部署步骤

1. **数据库迁移** ✅ 已完成
   ```bash
   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -f /tmp/40-simplify-test-scenarios-for-llm-eval.sql
   ```

2. **重启后端** ✅ 已完成
   ```bash
   docker-compose restart knowledge-admin-api
   ```

3. **修改前端** 🔄 进行中
   - 按照上面的指南修改 `TestScenariosView.vue`

4. **重启前端**
   ```bash
   docker-compose restart knowledge-admin-web
   ```

5. **测试验证**
   - 运行上面的验证清单

---

## 🔄 回滚方案

如果出现问题，可以执行回滚：

```sql
-- 在 40-simplify-test-scenarios-for-llm-eval.sql 底部有完整的回滚脚本
-- 警告：回滚会丢失 expected_answer 和 min_quality_score 的数据
```

---

## 📊 预期效果

### 测试流程简化

**之前:**
```
创建测试 → 手动填写 expected_category
         → 手动填写 expected_keywords（但实际没人填）
         → 运行测试 → basic 模式评分（依赖缺失的数据）
         → 评分失真
```

**之后:**
```
创建测试 → 只填写测试问题和可选的标准答案
         → 运行测试 → detailed 模式（LLM 评估）
         → 直接测试"准确、完整、有用"
```

### 评估质量提升

| 评估维度 | 之前 (basic) | 之后 (detailed) |
|---------|-------------|----------------|
| **准确性** | ❌ 简单关键字匹配 | ✅ LLM 语义理解 |
| **完整性** | ❌ 依赖缺失的 keywords | ✅ LLM 评估答案完整度 |
| **相关性** | ❌ 模糊分类匹配 | ✅ LLM 意图匹配评估 |
| **数据依赖** | ❌ 76个测试0个有keywords | ✅ 无需人工标注 |

---

## 💡 建议

1. **立即执行**: 前端修改 → 测试验证 → 部署
2. **优先测试**: 先在测试环境验证，确认无误后再部署到生产
3. **监控**: 部署后监控第一次回测的结果，确认 LLM 评估正常工作
4. **文档更新**: 更新团队文档，说明新的测试情境创建流程

---

## ❓ 常见问题

**Q: 历史的 expected_category 数据怎么办？**
A: 已自动迁移到 notes 字段，格式为"【遗留数据】预期分类: XXX"

**Q: 如果我还需要使用 basic 模式怎么办？**
A: backtest_framework.py 的 evaluate_answer 方法仍然保留，可以手动切换回 basic 模式

**Q: 为什么 priority 只有 3 档？**
A: 大部分测试都用默认值50，简化为3档更清晰，避免无意义的微调

**Q: expected_answer 是必填的吗？**
A: 不是，它是可选字段。LLM 评估不依赖它，但提供后可以做语义对比增强评估
