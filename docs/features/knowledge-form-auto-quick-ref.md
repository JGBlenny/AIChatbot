# 知識庫表單 Auto 選項 - 快速參考

## 🚀 快速開始

### 1. 執行 Migration
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_knowledge_form_auto_option.sql
```

### 2. 選項說明

| 選項 | 說明 | 使用場景 |
|------|------|----------|
| **always** | 總是觸發表單 | 需要收集資料的知識（如：申請流程） |
| **auto** 🆕 | 自動判斷 | 讓系統根據用戶意圖決定 |
| **never** 🆕 | 永不觸發 | 純資訊類知識（如：營業時間） |
| **conditional** 🆕 | 條件觸發 | 特定關鍵字才觸發 |

## 🤖 Auto 模式邏輯

### 觸發表單的情況 ✅
```
用戶：我要申請退租
用戶：幫我辦理續約
用戶：我想報名活動
```

### 不觸發表單的情況 ❌
```
用戶：租金多少錢？
用戶：什麼時候可以看房？
用戶：有沒有停車位？
```

## 📝 配置範例

### 範例 1：退租知識（Auto 模式）
```json
{
  "question": "退租相關",
  "answer": "退租需提前30天通知...",
  "form_id": "tenant_move_out",
  "trigger_form_condition": "auto"
}
```
- 「退租流程是什麼？」→ 不觸發表單
- 「我要申請退租」→ 觸發表單

### 範例 2：營業時間（Never 模式）
```json
{
  "question": "營業時間",
  "answer": "週一至週五 9:00-18:00",
  "form_id": null,
  "trigger_form_condition": "never"
}
```
永遠只顯示答案，不觸發表單

### 範例 3：特定條件（Conditional 模式）
```json
{
  "question": "維修服務",
  "answer": "提供各類維修服務...",
  "form_id": "repair_request",
  "trigger_form_condition": "conditional",
  "trigger_conditions": {
    "keywords": ["報修", "維修", "故障", "壞了"],
    "exclude": ["費用", "多少錢", "時間"]
  }
}
```
只有包含特定關鍵字時才觸發

## 🔧 後端實作（Python）

```python
# knowledge_manager.py 新增

def should_trigger_form(self, knowledge, user_message):
    """判斷是否應該觸發表單"""

    condition = knowledge.get('trigger_form_condition', 'always')

    # 1. Always 模式
    if condition == 'always':
        return True

    # 2. Never 模式
    if condition == 'never':
        return False

    # 3. Auto 模式
    if condition == 'auto':
        # 動作關鍵字（觸發表單）
        action_words = ['申請', '辦理', '報名', '預約', '登記', '提交']

        # 查詢關鍵字（不觸發）
        query_words = ['多少', '什麼', '哪裡', '何時', '是否', '有沒有']

        # 優先檢查是否為查詢
        for word in query_words:
            if word in user_message:
                return False

        # 檢查是否包含動作詞
        for word in action_words:
            if word in user_message:
                return True

        return False

    # 4. Conditional 模式
    if condition == 'conditional':
        conditions = knowledge.get('trigger_conditions', {})
        keywords = conditions.get('keywords', [])
        exclude = conditions.get('exclude', [])

        # 檢查排除詞
        for word in exclude:
            if word in user_message:
                return False

        # 檢查觸發詞
        for word in keywords:
            if word in user_message:
                return True

        return False

    # 預設不觸發
    return False
```

## 📱 前端實作（Vue）

```vue
<template>
  <el-form-item label="表單觸發模式">
    <el-radio-group v-model="form.trigger_form_condition">
      <el-radio-button label="always">
        <i class="el-icon-circle-check"></i> 總是
      </el-radio-button>
      <el-radio-button label="auto">
        <i class="el-icon-magic-stick"></i> 自動
      </el-radio-button>
      <el-radio-button label="never">
        <i class="el-icon-circle-close"></i> 從不
      </el-radio-button>
      <el-radio-button label="conditional">
        <i class="el-icon-setting"></i> 條件
      </el-radio-button>
    </el-radio-group>

    <div class="mode-hint">
      <span v-if="form.trigger_form_condition === 'always'">
        💡 回答後一定顯示表單
      </span>
      <span v-else-if="form.trigger_form_condition === 'auto'">
        🤖 系統自動判斷用戶是否需要填表
      </span>
      <span v-else-if="form.trigger_form_condition === 'never'">
        📖 只顯示答案，不觸發表單
      </span>
      <span v-else-if="form.trigger_form_condition === 'conditional'">
        ⚙️ 根據自定義條件決定
      </span>
    </div>
  </el-form-item>
</template>
```

## ✅ 測試檢查清單

- [ ] Always 模式正常觸發表單
- [ ] Auto 模式能區分動作詞和查詢詞
- [ ] Never 模式不觸發表單
- [ ] Conditional 模式按條件觸發
- [ ] 向後相容（舊資料仍為 always）

## 🎯 預期效果

1. **減少打擾**：查詢類問題不再彈出表單
2. **提升體驗**：需要時才收集資料
3. **更智能**：系統自動判斷用戶意圖
4. **統一性**：知識庫和 SOP 都有 auto 選項