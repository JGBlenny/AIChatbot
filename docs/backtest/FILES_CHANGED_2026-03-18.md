# 檔案修改摘要 (2026-03-18)

**修復項目**: 表單 Session 隔離
**問題編號**: #BACKTEST-001

---

## 📁 修改的檔案列表

### 1. 後端核心檔案

#### 1.1 `scripts/backtest/backtest_framework_async.py`
**修改行數**: Lines 114-148, 251-265, 645-672
**修改類型**: 功能增強

**主要改動**:
```python
# Line 119: 新增 scenario_id 參數
async def _query_rag_async(
    self,
    question: str,
    timeout: int = None,
    session: aiohttp.ClientSession = None,
    scenario_id: int = None  # ✅ 新增
) -> Dict:

# Lines 136-137: 生成獨立 session_id
unique_session_id = f"backtest_session_{scenario_id}" if scenario_id else "backtest_session"
unique_user_id = f"backtest_user_{scenario_id}" if scenario_id else "backtest_user"

# Line 252: 從 scenario 提取 id
scenario_id = scenario.get('id', None)

# Line 264: 傳遞 scenario_id
system_response = await self._query_rag_async(
    question, timeout, session, scenario_id
)

# Lines 650-672: 優化表單檢測邏輯
action_type = system_response.get('action_type', 'direct_answer')
if action_type in ['form_fill', 'form_then_api']:
    return {
        'passed': True,
        'is_form': True,
        'form_id': form_id,
        'optimization_tips': [...]
    }
```

**檔案路徑**:
- `/Users/lenny/jgb/AIChatbot/scripts/backtest/backtest_framework_async.py`
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/backtest_framework_async.py` (副本)

---

#### 1.2 `rag-orchestrator/run_backtest_db.py`
**修改行數**: Lines 147-148
**修改類型**: Bug 修復

**主要改動**:
```python
# Line 147: 添加 id 欄位
scenarios.append({
    'id': row[0],  # ✅ 新增：讓回測框架能生成獨立 session
    'scenario_id': row[0],  # 保留向後兼容
    'test_question': row[1],
    'difficulty': row[2] or 'medium'
})
```

**原因**: 原本只有 `'scenario_id'`，導致回測框架無法取得 ID 來生成獨立 session

**檔案路徑**:
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/run_backtest_db.py`

---

### 2. 前端檔案

#### 2.1 `knowledge-admin/frontend/src/views/BacktestView.vue`
**修改行數**: Lines 262, 374, 1994-2016
**修改類型**: UI 增強

**主要改動**:

**A. 列表中添加表單標記** (Line 262)
```vue
<div v-if="result.system_answer" class="answer-preview">
  <span v-if="result.is_form" class="form-badge">📝 表單</span>
  {{ result.system_answer.substring(0, 100) }}...
</div>
```

**B. 詳情頁添加表單標記** (Line 374)
```vue
<div class="answer-box">
  <strong>系統回答:</strong>
  <span v-if="selectedResult.is_form" class="form-badge-large">📝 表單類型</span>
  <p>{{ selectedResult.system_answer }}</p>
</div>
```

**C. CSS 樣式** (Lines 1994-2016)
```css
/* 列表中的小標籤 */
.form-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 6px;
  vertical-align: middle;
}

/* 詳情頁的大標籤 */
.form-badge-large {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-left: 10px;
  vertical-align: middle;
}
```

**檔案路徑**:
- `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/BacktestView.vue`

---

### 3. 文檔檔案

#### 3.1 新增文檔

| 檔案 | 說明 |
|------|------|
| `docs/backtest/FORM_SESSION_ISOLATION_FIX.md` | 完整修復文檔 |
| `docs/backtest/CHANGELOG.md` | 系統更新日誌 |
| `docs/backtest/FILES_CHANGED_2026-03-18.md` | 本檔案 |

#### 3.2 更新文檔

| 檔案 | 更新內容 |
|------|----------|
| `docs/backtest/README.md` | 添加新文檔連結 |
| `docs/backtest/ACTUAL_TESTING_STATUS.md` | 添加修復記錄 |

---

## 🔄 部署檢查清單

### 本地檔案同步
- [x] `scripts/backtest/backtest_framework_async.py` → `rag-orchestrator/backtest_framework_async.py`
- [x] 確認兩個檔案內容一致

### 容器更新
- [x] 更新 `aichatbot-rag-orchestrator` 容器
  - [x] `backtest_framework_async.py`
  - [x] `run_backtest_db.py`
- [x] 重啟 `aichatbot-rag-orchestrator`

### 資料庫清理
- [x] 清除舊的 backtest session: `DELETE FROM form_sessions WHERE session_id LIKE 'backtest%'`
- [x] 清空 Redis 緩存: `FLUSHDB`

### 前端更新
- [x] 重新編譯: `npm run build`
- [x] 確認 dist/ 目錄已更新

### 驗證測試
- [x] 執行 10 題測試
- [x] 確認無 session 污染
- [x] 確認表單標記正常顯示

---

## 📊 Git Diff 摘要

### 新增檔案 (3)
```
+ docs/backtest/FORM_SESSION_ISOLATION_FIX.md
+ docs/backtest/CHANGELOG.md
+ docs/backtest/FILES_CHANGED_2026-03-18.md
```

### 修改檔案 (5)
```
M scripts/backtest/backtest_framework_async.py (+35, -10)
M rag-orchestrator/backtest_framework_async.py (+35, -10)
M rag-orchestrator/run_backtest_db.py (+2, -1)
M knowledge-admin/frontend/src/views/BacktestView.vue (+25, -2)
M docs/backtest/README.md (+8, -3)
M docs/backtest/ACTUAL_TESTING_STATUS.md (+52, -3)
```

### 總計
- 檔案新增: 3
- 檔案修改: 6
- 新增行數: +157
- 刪除行數: -29

---

## 🔗 相關連結

- [主要修復文檔](./FORM_SESSION_ISOLATION_FIX.md)
- [系統狀態](./ACTUAL_TESTING_STATUS.md)
- [更新日誌](./CHANGELOG.md)

---

**整理者**: Claude
**日期**: 2026-03-18
**版本**: v2.3
