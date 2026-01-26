# SOP Next Action 功能實作文檔

**日期**: 2026-01-24
**狀態**: 核心模組已完成
**版本**: 1.0

---

## 📋 功能概述

SOP Next Action 是一個智能 SOP 管理系統，支援四種觸發模式和三種後續動作，實現從資訊查詢到緊急派工的完整業務流程。

### 四種 SOP 觸發模式

| 模式 | 中文名稱 | 說明 | 使用場景 | 範例 |
|------|---------|------|---------|------|
| **none** | 資訊型 | 純資訊，無後續動作 | 常見問題查詢 | 垃圾收取時間 |
| **manual** | 排查型 | 返回排查步驟，等關鍵詞觸發 | 可自行排查的問題 | 冷氣無法啟動 |
| **immediate** | 行動型 | 立即詢問是否執行 | 主動型業務 | 租金繳納登記 |
| **auto** | 緊急型 | 自動執行，無需確認 | 緊急危險情況 | 天花板漏水 |

### 三種後續動作

| 動作 | 說明 | 適用場景 |
|------|------|---------|
| **form_fill** | 僅填寫表單 | 租金登記、訪客登記 |
| **api_call** | 直接調用 API | 緊急派工 |
| **form_then_api** | 先填表單再調用 API | 維修請求 |

---

## 🗂️ 已完成的模組

### 1. **SOP 觸發模式處理器**
**檔案**: `rag-orchestrator/services/sop_trigger_handler.py`

**功能**:
- 處理四種觸發模式（none/manual/immediate/auto）
- 管理 SOP Context（Redis 儲存）
- 狀態追蹤（MANUAL_WAITING, IMMEDIATE_WAITING, TRIGGERED, EXPIRED）
- TTL 管理（manual: 10分鐘, immediate: 10分鐘）

**核心方法**:
```python
handler = SOPTriggerHandler(redis_client)

# 處理 SOP
result = handler.handle(
    sop_item=sop_item,
    user_message="冷氣無法啟動",
    session_id=session_id,
    user_id=user_id,
    vendor_id=vendor_id
)

# 管理 Context
context = handler.get_context(session_id)
handler.update_context_state(session_id, 'TRIGGERED')
handler.delete_context(session_id)
```

**返回格式**:
```python
{
    'response': str,           # 返回給用戶的訊息
    'action': str,             # 動作類型
    'trigger_mode': str,       # 觸發模式
    'next_action': str,        # 後續動作
    'form_id': str,            # 表單 ID（如果有）
    'api_config': Dict,        # API 配置（如果有）
    'context_saved': bool,     # 是否儲存 context
    'trigger_keywords': List   # 觸發關鍵詞
}
```

---

### 2. **關鍵詞匹配引擎**
**檔案**: `rag-orchestrator/services/keyword_matcher.py`

**功能**:
- 精確匹配（exact）：完全相同
- 包含匹配（contains）：部分包含
- 正則匹配（regex）：正則表達式
- 同義詞匹配（synonyms）：擴展匹配範圍
- 匹配分數計算
- 最佳匹配選擇

**核心方法**:
```python
matcher = KeywordMatcher()

# 基本匹配
is_match, keyword = matcher.match(
    user_message="試過了還是不行",
    keywords=['還是不行', '試過了', '需要維修'],
    match_type="contains"
)

# 多策略匹配
is_match, keyword, match_type = matcher.match_any(
    user_message="沒問題",
    keywords=['好', '是', '要'],
    match_types=["contains", "synonyms"]
)

# 獲取最佳匹配
best_keyword, score = matcher.get_best_match(
    user_message="試過了還是不行",
    keywords=['還是不行', '試過了']
)
```

**同義詞表**:
```python
synonyms = {
    '是': ['好', '要', '可以', '需要', '對', '確認'],
    '還是不行': ['試過了還是不行', '還是沒用', '沒有用'],
    '需要維修': ['要維修', '請幫我修', '需要修理']
}
```

---

### 3. **後續動作處理器**
**檔案**: `rag-orchestrator/services/sop_next_action_handler.py`

**功能**:
- 處理三種後續動作（form_fill, api_call, form_then_api）
- 表單預填欄位（從 next_api_config.params）
- API 調用與結果格式化
- 表單與 API 的協調

**核心方法**:
```python
handler = SOPNextActionHandler(form_manager, api_handler)

# 處理後續動作
result = await handler.handle(
    next_action='form_fill',
    session_id=session_id,
    user_id=user_id,
    vendor_id=vendor_id,
    form_id='rent_payment_registration',
    sop_context=sop_context,
    user_message=user_message
)
```

**返回格式**:
```python
{
    'action_type': str,      # 動作類型
    'form_session': Dict,    # 表單會話（如果有）
    'api_result': Dict,      # API 結果（如果有）
    'next_step': str,        # 下一步指示
    'response': str,         # 返回訊息
    'will_call_api': bool    # 是否會調用 API
}
```

---

### 4. **SOP 編排器**
**檔案**: `rag-orchestrator/services/sop_orchestrator.py`

**功能**:
- 整合所有 SOP 模組
- 統一處理入口
- 自動流程協調
- Context 與關鍵詞管理

**核心方法**:
```python
orchestrator = SOPOrchestrator(form_manager, api_handler, redis_client)

# 主處理入口
result = await orchestrator.process_message(
    user_message="冷氣無法啟動",
    session_id=session_id,
    user_id=user_id,
    vendor_id=vendor_id,
    intent_id=25  # 冷氣維修
)
```

**處理流程**:
```
1. 檢查是否有待處理的 SOP Context
   ├─ 有 Context → 檢查關鍵詞匹配
   │   ├─ 匹配成功 → 執行後續動作
   │   └─ 匹配失敗 → 提示或繼續等待
   └─ 無 Context → 檢索新 SOP
       └─ 根據 trigger_mode 處理
           ├─ none → 直接返回資訊
           ├─ manual → 儲存 context，等待關鍵詞
           ├─ immediate → 儲存 context，立即詢問
           └─ auto → 立即執行 API
```

**返回格式**:
```python
{
    'has_sop': bool,           # 是否匹配到 SOP
    'sop_item': Dict,          # SOP 項目
    'trigger_result': Dict,    # 觸發處理結果
    'action_result': Dict,     # 動作執行結果
    'response': str,           # 返回訊息
    'next_step': str          # 下一步指示
}
```

---

## 🔗 資料庫 Schema

### vendor_sop_items 表（已擴展）

```sql
-- 新增欄位
ALTER TABLE vendor_sop_items
ADD COLUMN trigger_mode VARCHAR(20) DEFAULT 'none',
ADD COLUMN next_action VARCHAR(50) DEFAULT 'none',
ADD COLUMN next_form_id VARCHAR(100),
ADD COLUMN next_api_config JSONB,
ADD COLUMN trigger_keywords TEXT[],
ADD COLUMN immediate_prompt TEXT,
ADD COLUMN followup_prompt TEXT;

-- 約束
ADD CONSTRAINT check_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto'));

ADD CONSTRAINT check_next_action
CHECK (next_action IN ('none', 'form_fill', 'api_call', 'form_then_api'));

-- 外鍵
ADD CONSTRAINT fk_sop_next_form
FOREIGN KEY (next_form_id)
REFERENCES form_schemas(form_id);
```

---

## 📝 使用範例

### 範例 1：資訊型 SOP（垃圾收取時間）

```python
# 1. 用戶提問
result = await orchestrator.process_message(
    user_message="垃圾什麼時候收？",
    session_id="session_001",
    user_id="tenant_123",
    vendor_id=1,
    intent_id=88  # 垃圾相關查詢
)

# 2. 系統回應
# result['response']:
# 【垃圾收取時間規範】
# • 一般垃圾：每週 一、三、五（晚上 8-9 點）
# • 資源回收：每週 二、四、六（晚上 8-9 點）
# ...

# 3. 對話結束（無後續動作）
# result['next_step']: 'completed'
```

### 範例 2：排查型 SOP（冷氣無法啟動）

```python
# 1. 第一輪：用戶提問
result = await orchestrator.process_message(
    user_message="冷氣無法啟動",
    session_id="session_002",
    user_id="tenant_456",
    vendor_id=1,
    intent_id=25  # 冷氣維修
)

# 2. 系統返回排查步驟
# result['response']:
# 【冷氣無法啟動 - 排查步驟】
# 1. 檢查電源...
# 2. 檢查遙控器...
# ...

# result['next_step']: 'waiting_for_keyword'

# 3. 第二輪：用戶嘗試排查後回覆
result = await orchestrator.process_message(
    user_message="試過了還是不行",
    session_id="session_002",  # 同一個 session
    user_id="tenant_456",
    vendor_id=1
)

# 4. 關鍵詞匹配成功，觸發表單
# result['trigger_result']['matched']: True
# result['response']:
# 好的，我來協助您提交維修請求...
#
# 📋 維修請求表單（第 1/10 題）
# 請問漏水的位置是？

# result['next_step']: 'collect_field'
```

### 範例 3：行動型 SOP（租金繳納登記）

```python
# 1. 第一輪：用戶提問
result = await orchestrator.process_message(
    user_message="我要登記租金繳納",
    session_id="session_003",
    user_id="tenant_789",
    vendor_id=1,
    intent_id=45  # 租金相關
)

# 2. 系統返回資訊 + 立即詢問
# result['response']:
# 【租金繳納登記說明】
# 繳納期限：每月 5 日前...
#
# 📋 是否要登記本月租金繳納記錄？

# result['next_step']: 'waiting_for_confirmation'

# 3. 第二輪：用戶確認
result = await orchestrator.process_message(
    user_message="好的",
    session_id="session_003",
    user_id="tenant_789",
    vendor_id=1
)

# 4. 觸發表單
# result['response']:
# 好的，我來協助您登記本月租金繳納記錄 📝
#
# 📋 租金繳納登記（第 1/5 題）
# 請問您的繳款日期是？
```

### 範例 4：緊急型 SOP（天花板漏水）

```python
# 1. 用戶報告緊急情況
result = await orchestrator.process_message(
    user_message="天花板漏水了！",
    session_id="session_004",
    user_id="tenant_012",
    vendor_id=1,
    intent_id=99  # 緊急維修
)

# 2. 系統同時返回 SOP + 自動執行 API
# result['response']:
# 🚨 【緊急處理步驟】
# 1. 收集漏水...
# 2. 關閉電源...
#
# ━━━━━━━━━━━━━━━━━━━━━━
# ⚡ 我已自動為您提交緊急維修請求
#
# 📋 緊急工單資訊
# 工單編號：MT20260124001
# 優先級：P0（非常緊急）
# 預計到達時間：1小時內
#
# 維修人員會立即聯絡您，請保持手機暢通。

# result['action_result']['api_result']:
# {'ticket_id': 'MT20260124001', 'priority': 'P0', ...}

# result['next_step']: 'completed'
```

---

## 🔄 完整流程圖

```
用戶提問
    ↓
檢查 SOP Context
    ├─ 有 Context
    │   ├─ manual mode → 檢查關鍵詞
    │   │   ├─ 匹配 → 執行後續動作
    │   │   └─ 不匹配 → 保持等待
    │   └─ immediate mode → 檢查關鍵詞
    │       ├─ 匹配 → 執行後續動作
    │       └─ 不匹配 → 再次詢問
    └─ 無 Context
        ↓
    檢索新 SOP
        ↓
    處理 trigger_mode
        ├─ none → 返回資訊 → 結束
        ├─ manual → 返回排查 + 儲存 context → 等待關鍵詞
        ├─ immediate → 返回資訊 + 立即詢問 + 儲存 context → 等待確認
        └─ auto → 返回 SOP + 立即執行 API → 結束
```

---

## ✅ 已完成的工作

### 核心模組 (4/4)
- ✅ SOP 觸發模式處理器（4 種模式）
- ✅ 關鍵詞匹配引擎
- ✅ 後續動作處理器（3 種動作）
- ✅ SOP 編排器（整合所有模組）

### 文檔 (2/2)
- ✅ 用戶指南（10 個場景）
- ✅ 實作文檔（本文件）

---

## 📌 待完成的工作

### 必要整合
1. **擴展 VendorSOPRetriever**
   - 在 `retrieve_sop_by_intent()` 中添加 next_action 相關欄位
   - 創建 `_fetch_sop_with_next_action()` 方法

2. **擴展 FormManager**
   - 添加 PAUSED, CONFIRMING 狀態
   - 實作暫存/恢復機制
   - 添加 API 配置附加功能

3. **整合到 RAG Engine**
   - 在主聊天流程中調用 SOPOrchestrator
   - 處理 SOP 與一般對話的優先級
   - 整合離題檢測

### 進階功能
4. **重複報修檢測器**
   - 查詢近期工單
   - 計算相似度
   - 提供工單進度查詢

5. **滿意度調查系統**
   - 監聽工單完成事件
   - 延遲觸發調查
   - AI 情感分析
   - 低分補救流程

### 測試與優化
6. **單元測試**
   - 每個模組的單元測試
   - 整合測試

7. **性能優化**
   - Redis 連接池
   - Context TTL 調優
   - 關鍵詞匹配性能

---

## 🚀 下一步建議

### 立即可做（優先級 P0）
1. 擴展 `VendorSOPRetriever` 讀取完整欄位
2. 在 RAG Engine 中整合 SOPOrchestrator
3. 測試基本流程（4 種模式）

### 短期目標（1-2 週）
4. 擴展 FormManager 支援 PAUSED 狀態
5. 實作表單離題處理增強
6. 添加重複檢測器

### 中期目標（2-4 週）
7. 實作滿意度調查系統
8. 完善異常處理
9. 性能優化與監控

---

## 📞 技術支援

如有問題，請聯繫：
- 開發團隊：dev@example.com
- 文檔位置：`/docs/development/`
- 用戶指南：`/docs/user-guides/MAINTENANCE_FORM_USER_GUIDE.md`

---

**最後更新**: 2026-01-24
**作者**: Claude AI
**版本**: 1.0
