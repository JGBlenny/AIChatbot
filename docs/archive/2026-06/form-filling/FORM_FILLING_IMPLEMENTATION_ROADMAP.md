# 表單填寫功能 - 實施路線圖

> 基於確認的方案：表單期間禁用緩存（方案 1）

---

## ✅ 決策確認

**緩存處理方案**：方案 1 - 表單會話期間禁用緩存

**理由**：
- 徹底解決緩存繞過表單邏輯的問題
- 保證表單狀態檢查每次都執行
- 對非表單用戶無影響
- 代碼修改簡單（一個 if 判斷）

---

## 📋 實施步驟（6-10 天）

### Phase 1：資料庫準備（0.5 天）

#### 任務清單

- [ ] **1.1 創建遷移腳本**
  - 文件：`database/migrations/create_form_tables.sql`
  - 內容：已在 `FORM_FILLING_CODE_CHANGES.md` 提供
  - 包含：3 張表 + 測試數據（租屋申請表）

- [ ] **1.2 在開發環境執行遷移**
  ```bash
  psql -h localhost -U your_user -d ai_chatbot \
    -f database/migrations/create_form_tables.sql
  ```

- [ ] **1.3 驗證表已創建**
  ```bash
  psql -h localhost -U your_user -d ai_chatbot -c "\dt form_*"
  # 應該看到：
  # - form_schemas
  # - form_sessions
  # - form_submissions
  ```

- [ ] **1.4 驗證測試數據**
  ```bash
  psql -h localhost -U your_user -d ai_chatbot \
    -c "SELECT form_id, form_name FROM form_schemas;"
  # 應該看到：rental_application | 租屋申請表
  ```

#### 驗收標準
- ✅ 3 張表已創建
- ✅ 測試表單「租屋申請表」已插入
- ✅ 索引已創建
- ✅ 觸發器已創建

---

### Phase 2：服務開發（2-3 天）

#### 任務清單

- [ ] **2.1 完善 FormManager**
  - 文件：`services/form_manager.py`（已有草稿，~600 行）
  - 需要檢查：
    - [ ] 所有方法的錯誤處理
    - [ ] 資料庫連接管理（是否需要改用 asyncpg？）
    - [ ] 日誌輸出格式
  - 修改建議：
    ```python
    # 目前使用 psycopg2（同步），可能需要改成 asyncpg（異步）
    # 以配合現有系統的異步架構

    # 修改前
    conn = psycopg2.connect(**get_db_config())

    # 修改後
    async with app.state.db_pool.acquire() as conn:
        ...
    ```

- [ ] **2.2 完善 FormValidator**
  - 文件：`services/form_validator.py`（已有草稿，~200 行）
  - 需要測試：
    - [ ] 台灣身分證驗證（含檢查碼）
    - [ ] 電話號碼驗證（手機、市話）
    - [ ] Email 驗證
    - [ ] 敏感資料遮罩

- [ ] **2.3 完善 DigressionDetector**
  - 文件：`services/digression_detector.py`（已有草稿，~150 行）
  - 需要測試：
    - [ ] 明確退出關鍵字偵測
    - [ ] 問題關鍵字偵測
    - [ ] 意圖轉移偵測
    - [ ] 語義相似度偵測

- [ ] **2.4 編寫單元測試**
  - 文件：`tests/unit/test_form_manager.py`
  - 文件：`tests/unit/test_form_validator.py`
  - 文件：`tests/unit/test_digression_detector.py`

#### 驗收標準
- ✅ 所有服務類通過單元測試
- ✅ 測試覆蓋率 > 80%
- ✅ 無明顯的性能問題

---

### Phase 3：API 整合（1-2 天）

#### 任務清單

- [ ] **3.1 修改 app.py**
  - 增加 FormManager 初始化
  - 參考：`FORM_FILLING_CODE_CHANGES.md` 第 1 節
  - 代碼量：~5 行

- [ ] **3.2 修改 routers/chat.py**
  - **3.2.1 擴展 VendorChatResponse 模型**（~7 行）
    - 增加 7 個表單相關欄位

  - **3.2.2 新增轉換函數**（~30 行）
    - `convert_form_result_to_response()`

  - **3.2.3 整合表單邏輯**（~40 行修改）
    - 雙點整合：
      - 整合點 A：表單會話檢查 + 緩存跳過
      - 整合點 B：表單觸發檢查

  - 參考：`FORM_FILLING_CODE_CHANGES.md` 第 2 節

- [ ] **3.3 測試重啟服務**
  ```bash
  # Docker 環境
  docker-compose restart rag-orchestrator

  # 查看日誌確認初始化
  docker-compose logs -f rag-orchestrator | grep "表單管理器"
  # 應該看到：✅ 表單管理器已初始化
  ```

#### 驗收標準
- ✅ 服務正常啟動
- ✅ 日誌顯示「✅ 表單管理器已初始化」
- ✅ 現有 API 功能不受影響（回歸測試）

---

### Phase 4：整合測試（1-2 天）

#### 測試案例

- [ ] **4.1 測試案例 1：完整表單流程（無離題）**
  - 觸發表單：「我要申請租房子」
  - 填寫姓名：「王小明」
  - 填寫電話：「0912345678」
  - 填寫身分證：「A123456789」
  - 填寫地址：「台北市大安區復興南路一號」
  - 驗證：表單完成，提交記錄已保存

- [ ] **4.2 測試案例 2：表單填寫中離題**
  - 觸發表單並填寫到第 2 個欄位
  - 用戶離題：「請問租金多少？」
  - 驗證：返回答案 + 「要繼續填表單嗎？」提示
  - 用戶恢復：「繼續」
  - 驗證：返回當前欄位提示

- [ ] **4.3 測試案例 3：緩存跳過驗證（關鍵）**
  - 創建表單會話並填寫到第 2 個欄位
  - 用戶問：「請問租金多少？」（第 1 次）
  - 用戶再問：「請問租金多少？」（第 2 次，相同問題）
  - 驗證：兩次都返回「要繼續填表單嗎？」提示
  - 檢查日誌：應該看到「⏭️  表單會話期間，跳過緩存檢查」

- [ ] **4.4 測試案例 4：表單明確退出**
  - 觸發表單並填寫到第 2 個欄位
  - 用戶輸入：「取消」
  - 驗證：表單取消，返回取消訊息
  - 驗證資料庫：`form_sessions.state = 'CANCELLED'`

- [ ] **4.5 測試案例 5：驗證失敗重試**
  - 觸發表單並填寫姓名
  - 填寫電話（錯誤格式）：「123456」
  - 驗證：返回錯誤訊息「請輸入正確的台灣電話號碼格式」
  - 重試 3 次驗證失敗
  - 驗證：提供選項「1. 繼續嘗試 2. 跳過 3. 取消」

- [ ] **4.6 測試案例 6：會話超時清理**
  - 創建表單會話但不完成
  - 等待 30 分鐘（或修改超時設定為 2 分鐘測試）
  - 運行清理任務：`form_manager.cleanup_expired_sessions()`
  - 驗證：過期會話狀態改為 'CANCELLED'

#### cURL 命令參考

詳見 `FORM_FILLING_CODE_CHANGES.md` 第 4 節

#### 驗收標準
- ✅ 所有測試案例通過
- ✅ 緩存跳過邏輯正確運作（案例 3）
- ✅ 日誌輸出清晰易讀

---

### Phase 5：前端適配（1-2 天）

#### 前端需要處理的新欄位

```typescript
interface VendorChatResponse {
  // ... 現有欄位 ...

  // 新增：表單相關欄位
  form_triggered?: boolean;      // 是否觸發表單
  form_completed?: boolean;      // 表單是否完成
  form_cancelled?: boolean;      // 表單是否取消
  form_id?: string;              // 表單 ID
  current_field?: string;        // 當前欄位名稱
  progress?: string;             // 進度（如 "2/5"）
  allow_resume?: boolean;        // 是否允許恢復
}
```

#### 前端任務清單

- [ ] **5.1 檢測表單觸發**
  ```javascript
  if (response.form_triggered) {
    // 顯示表單模式 UI
    showFormMode();
    showProgress(response.progress); // 顯示進度條
  }
  ```

- [ ] **5.2 顯示進度條**
  ```javascript
  // 當 progress = "2/5" 時
  const [current, total] = response.progress.split('/');
  progressBar.style.width = `${(current / total) * 100}%`;
  ```

- [ ] **5.3 處理離題提示**
  ```javascript
  if (response.allow_resume) {
    // 顯示「繼續填寫」或「取消」按鈕
    showResumeButtons();
  }
  ```

- [ ] **5.4 表單完成處理**
  ```javascript
  if (response.form_completed) {
    // 顯示完成動畫
    // 清除表單狀態
    exitFormMode();
  }
  ```

#### 驗收標準
- ✅ 表單觸發時顯示表單模式 UI
- ✅ 進度條正確顯示
- ✅ 離題時顯示恢復提示
- ✅ 完成時有明確的反饋

---

### Phase 6：部署（1 天）

#### Staging 環境部署

- [ ] **6.1 備份資料庫**
  ```bash
  pg_dump -h staging_host -U user -d ai_chatbot > backup_$(date +%Y%m%d).sql
  ```

- [ ] **6.2 執行遷移**
  ```bash
  psql -h staging_host -U user -d ai_chatbot \
    -f database/migrations/create_form_tables.sql
  ```

- [ ] **6.3 部署新代碼**
  ```bash
  git checkout main
  git pull origin main
  docker-compose -f docker-compose.staging.yml up -d --build rag-orchestrator
  ```

- [ ] **6.4 驗證部署**
  - 檢查日誌
  - 運行測試案例 1-6
  - 監控錯誤率

#### Production 環境部署

- [ ] **6.5 準備回滾計畫**
  - Git commit hash 記錄
  - 資料庫回滾腳本準備

- [ ] **6.6 執行遷移（先）**
  ```bash
  # 在維護時段執行
  psql -h production_host -U user -d ai_chatbot \
    -f database/migrations/create_form_tables.sql
  ```

- [ ] **6.7 部署新代碼（後）**
  ```bash
  docker-compose -f docker-compose.prod.yml up -d --build rag-orchestrator
  ```

- [ ] **6.8 監控**
  - 錯誤率監控（Sentry / Grafana）
  - 響應時間監控
  - 表單完成率監控

#### 驗收標準
- ✅ Staging 環境測試通過
- ✅ Production 部署無錯誤
- ✅ 監控指標正常

---

## 📊 監控指標

### 建議配置的監控指標

| 指標 | 計算方式 | 目標值 | 監控工具 |
|------|---------|--------|---------|
| **表單完成率** | 完成數 / 開始數 | > 70% | 自定義 SQL 查詢 |
| **平均填寫時間** | AVG(completed_at - started_at) | < 5 分鐘 | PostgreSQL 查詢 |
| **離題率** | 離題次數 / 總對話輪次 | < 20% | 日誌分析 |
| **驗證失敗率** | 驗證失敗 / 總提交 | < 10% | 日誌分析 |
| **恢復率** | 離題後恢復 / 離題總次數 | > 50% | 自定義 SQL 查詢 |
| **會話超時率** | 超時取消 / 總開始數 | < 15% | 定時任務日誌 |

### 監控 SQL 示例

```sql
-- 表單完成率（過去 7 天）
SELECT
  COUNT(CASE WHEN state = 'COMPLETED' THEN 1 END) * 100.0 / COUNT(*) AS completion_rate
FROM form_sessions
WHERE started_at >= NOW() - INTERVAL '7 days';

-- 平均填寫時間
SELECT
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) / 60) AS avg_minutes
FROM form_sessions
WHERE state = 'COMPLETED';

-- 離題率
SELECT
  SUM(digression_count) * 100.0 / COUNT(*) AS digression_rate
FROM form_sessions;
```

---

## ⚠️ 風險與緩解

### 風險 1：FormManager 使用同步資料庫（psycopg2）

**問題**：現有系統使用 asyncpg（異步），FormManager 草稿使用 psycopg2（同步）

**影響**：可能阻塞事件循環，降低性能

**緩解方案**：
- **選項 A**：使用 `asyncio.to_thread()` 包裝同步調用（快速方案）
  ```python
  session_state = await asyncio.to_thread(
      form_manager.get_session_state,
      session_id
  )
  ```

- **選項 B**：重寫 FormManager 使用 asyncpg（更好但耗時）
  ```python
  async def get_session_state(self, session_id: str):
      async with self.db_pool.acquire() as conn:
          result = await conn.fetchrow(...)
  ```

**推薦**：Phase 2 時使用選項 A，Phase 3 後根據性能測試決定是否採用選項 B

---

### 風險 2：緩存跳過邏輯實施錯誤

**問題**：如果整合點 A 的邏輯順序錯誤，可能仍會被緩存繞過

**緩解方案**：
- 嚴格按照 `FORM_FILLING_CODE_CHANGES.md` 的順序實施
- 必須在緩存檢查**之前**檢查表單會話
- 使用測試案例 3 驗證

---

### 風險 3：前端未正確處理表單狀態

**問題**：前端不顯示進度條或恢復按鈕

**緩解方案**：
- 提供明確的前端整合文檔
- 後端返回的欄位都是 Optional，不會導致解析錯誤
- 可以先部署後端，前端逐步適配

---

## 📚 相關文檔索引

| 文檔 | 用途 |
|------|------|
| `FORM_FILLING_DIALOG_DESIGN.md` | 完整架構設計和理論 |
| `FORM_FILLING_INTEGRATION_PLAN.md` | 整合方案對比 |
| `FORM_FILLING_CONFLICT_ANALYSIS.md` | ⭐ 衝突深度分析 |
| `FORM_FILLING_CODE_CHANGES.md` | ⭐ 具體代碼修改示例 |
| `FORM_FILLING_IMPLEMENTATION_ROADMAP.md` | ⭐ 本文檔（實施路線圖）|

---

## ✅ 檢查清單（總覽）

### 開發階段
- [ ] Phase 1: 資料庫準備（0.5 天）
- [ ] Phase 2: 服務開發（2-3 天）
- [ ] Phase 3: API 整合（1-2 天）
- [ ] Phase 4: 整合測試（1-2 天）
- [ ] Phase 5: 前端適配（1-2 天）
- [ ] Phase 6: 部署（1 天）

### 關鍵驗證點
- [ ] 緩存跳過邏輯正確（測試案例 3）
- [ ] 離題恢復流程正常（測試案例 2）
- [ ] 表單完成率 > 70%
- [ ] 無性能退化（響應時間監控）

---

## 🎯 下一步行動

### 立即可做（不需要我協助）
1. 審閱本路線圖，確認可行性
2. 評估團隊資源和時程
3. 決定是否要我協助 Phase 1（創建遷移腳本）

### 需要我協助時
1. Phase 1：創建並測試遷移腳本
2. Phase 2：完善服務代碼（處理 async/sync 問題）
3. Phase 3：協助整合代碼到 chat.py
4. Phase 4：編寫測試案例腳本
5. 任何實施過程中遇到的問題

---

**預計總時間**：6-10 天（視團隊規模和測試深度）

準備好開始了嗎？ 🚀
