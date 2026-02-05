# 知識庫表單自動選擇功能 - 改進方案

## 📋 現況分析

### 目前狀態

1. **SOP** (`vendor_sop_items`) 已支援 4 種 `trigger_mode`：
   - `none` - 不觸發
   - `manual` - 手動觸發（關鍵字）
   - `immediate` - 立即觸發
   - **`auto`** - 自動選擇 ✅

2. **知識庫** (`knowledge_base`) 只有：
   - `form_id` - 關聯的表單 ID
   - `trigger_form_condition` - 目前只有 `always` ❌

### 問題
知識庫缺少 **auto（自動）** 選項，無法實現智能表單選擇。

## 🎯 改進方案

### 1. 資料庫更新

```sql
-- 新增 CHECK 約束，支援多種觸發條件
ALTER TABLE knowledge_base
DROP COLUMN IF EXISTS trigger_form_condition;

ALTER TABLE knowledge_base
ADD COLUMN trigger_form_condition VARCHAR(20) DEFAULT 'always'
CHECK (trigger_form_condition IN ('always', 'auto', 'never', 'conditional'));

COMMENT ON COLUMN knowledge_base.trigger_form_condition IS
'表單觸發條件：
- always: 總是觸發表單
- auto: 自動判斷是否需要表單
- never: 永不觸發表單
- conditional: 根據條件觸發';
```

### 2. 觸發邏輯設計

#### `auto` 模式的判斷邏輯

```python
def should_trigger_form(knowledge, user_question):
    """
    自動判斷是否需要觸發表單

    觸發表單的情況：
    1. 問題中包含「申請」、「辦理」、「報名」等動作詞
    2. 知識內容提到需要收集資料
    3. 問題明顯需要個人資訊

    不觸發表單的情況：
    1. 純粹詢問資訊（如：費用多少？）
    2. 查詢類問題（如：什麼時候？）
    3. 確認類問題（如：是否可以？）
    """

    # 動作關鍵字
    action_keywords = ['申請', '辦理', '報名', '預約', '登記', '提交']

    # 查詢關鍵字（不需要表單）
    query_keywords = ['多少', '什麼', '哪裡', '何時', '是否', '有沒有']

    # 檢查是否為查詢性質
    if any(keyword in user_question for keyword in query_keywords):
        return False

    # 檢查是否包含動作關鍵字
    if any(keyword in user_question for keyword in action_keywords):
        return True

    # 默認不觸發
    return False
```

### 3. UI 介面更新

#### 知識庫編輯頁面

```html
<el-form-item label="表單觸發">
  <el-select v-model="knowledge.trigger_form_condition">
    <el-option label="總是觸發" value="always">
      <span>
        <i class="el-icon-circle-check"></i>
        總是觸發 - 回答後一定顯示表單
      </span>
    </el-option>

    <el-option label="自動判斷" value="auto">
      <span>
        <i class="el-icon-magic-stick"></i>
        自動判斷 - 根據用戶意圖智能決定
      </span>
    </el-option>

    <el-option label="永不觸發" value="never">
      <span>
        <i class="el-icon-circle-close"></i>
        永不觸發 - 只顯示答案
      </span>
    </el-option>

    <el-option label="條件觸發" value="conditional">
      <span>
        <i class="el-icon-setting"></i>
        條件觸發 - 根據自定義條件
      </span>
    </el-option>
  </el-select>
</el-form-item>

<!-- 當選擇 conditional 時顯示 -->
<el-form-item v-if="knowledge.trigger_form_condition === 'conditional'"
              label="觸發條件">
  <el-input
    type="textarea"
    v-model="knowledge.trigger_conditions"
    placeholder="輸入觸發條件，如：包含特定關鍵字"
  />
</el-form-item>
```

## 📊 使用案例

### 案例 1：租金查詢（不需要表單）
- 問題：「租金多少錢？」
- `auto` 模式：不觸發表單
- 原因：純查詢性質

### 案例 2：申請退租（需要表單）
- 問題：「我要申請退租」
- `auto` 模式：觸發表單
- 原因：包含「申請」動作詞

### 案例 3：了解退租流程（不需要表單）
- 問題：「退租流程是什麼？」
- `auto` 模式：不觸發表單
- 原因：詢問資訊，非執行動作

## 🛠️ 實作步驟

### 第一階段：資料庫
1. 執行 migration 新增 CHECK 約束
2. 更新現有資料的預設值

### 第二階段：後端
1. 修改 `knowledge_manager.py` 加入 auto 判斷邏輯
2. 更新 API 端點支援新欄位

### 第三階段：前端
1. 更新知識庫編輯介面
2. 加入選項說明和提示

## 📈 預期效益

1. **更智能**：系統自動判斷何時需要表單
2. **更靈活**：支援多種觸發模式
3. **更友善**：減少不必要的表單打擾
4. **統一性**：知識庫與 SOP 都有 auto 選項

## ⚠️ 注意事項

1. **向後相容**：保留 `always` 作為預設值
2. **測試覆蓋**：需要測試各種問句的判斷結果
3. **可調整性**：auto 邏輯應該可以配置和調整

## 📝 Migration SQL

```sql
-- add_knowledge_trigger_auto_option.sql
BEGIN;

-- 1. 新增 trigger_form_condition 的條件約束
ALTER TABLE knowledge_base
ALTER COLUMN trigger_form_condition TYPE VARCHAR(20),
ALTER COLUMN trigger_form_condition SET DEFAULT 'always';

-- 2. 新增 CHECK 約束
ALTER TABLE knowledge_base
ADD CONSTRAINT check_trigger_form_condition
CHECK (trigger_form_condition IN ('always', 'auto', 'never', 'conditional'));

-- 3. 新增條件欄位（用於 conditional 模式）
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_conditions JSONB;

COMMENT ON COLUMN knowledge_base.trigger_conditions IS
'自定義觸發條件（僅 conditional 模式使用）';

-- 4. 更新現有資料
UPDATE knowledge_base
SET trigger_form_condition = 'always'
WHERE trigger_form_condition IS NULL;

COMMIT;

-- 驗證
SELECT
    COUNT(*) as total,
    trigger_form_condition,
    COUNT(*) as count
FROM knowledge_base
GROUP BY trigger_form_condition;
```