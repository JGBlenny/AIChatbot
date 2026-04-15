# 實作缺陷記錄

## 1. Loop 迭代續接功能缺失

### 問題描述
**狀態**: ❌ 未實作
**優先級**: P1 - 高
**發現時間**: 2026-03-27

### 詳細說明

當前 `LoopCoordinator` 無法載入已存在的 loop 並繼續執行下一次迭代。

**當前支援的場景**：
```python
# ✅ 支援：同一個 session 內連續執行
coordinator = LoopCoordinator(...)
await coordinator.start_loop(config)  # 建立 Loop #84
await coordinator.execute_iteration()  # 迭代 1
await coordinator.execute_iteration()  # 迭代 2
```

**不支援的場景**：
```python
# ❌ 不支援：載入已存在的 loop 繼續執行
coordinator = LoopCoordinator(...)
coordinator.loop_id = 84  # 手動設定
await coordinator.execute_iteration()  # 錯誤：UNINITIALIZED 狀態
```

### 錯誤訊息
```
models.InvalidStateError: 無法從狀態 'UNINITIALIZED' 轉換至 'execute_iteration'
```

### 影響範圍

1. **無法執行跨 session 的迭代**：
   - 使用者審核完知識後，無法從命令列執行下一次迭代
   - 必須透過前端 API（如果已實作）或重新執行整個流程

2. **腳本 `run_next_iteration.sh` 無法使用**：
   - 該腳本設計用於執行現有 loop 的下一次迭代
   - 但因為 coordinator 狀態機限制而無法運作

3. **改善幅度驗證困難**：
   - 無法在同一個 loop 內執行多次迭代並比較改善幅度
   - 需要建立多個 loop 來間接驗證

### 根本原因

`LoopCoordinator.__init__()` 初始化時：
- `self.loop_id = None`
- `self.current_status = LoopStatus.UNINITIALIZED`

執行 `execute_iteration()` 時檢查狀態：
```python
# coordinator.py:801
if self.current_status == LoopStatus.UNINITIALIZED:
    raise InvalidStateError(
        f"無法從狀態 '{self.current_status.value}' 轉換至 'execute_iteration'"
    )
```

手動設定 `loop_id` 和 `current_status` 無法通過所有驗證。

### 建議解決方案

#### 方案 1：新增 `load_loop()` 方法（推薦）

```python
async def load_loop(self, loop_id: int) -> Dict:
    """
    載入已存在的 loop 並初始化協調器狀態

    Args:
        loop_id: 要載入的 loop ID

    Returns:
        Loop 的當前狀態資訊
    """
    conn = self.db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # 查詢 loop 資訊
            cur.execute("""
                SELECT loop_name, vendor_id, status, current_iteration,
                       current_pass_rate, config
                FROM knowledge_completion_loops
                WHERE id = %s
            """, (loop_id,))

            row = cur.fetchone()
            if not row:
                raise ValueError(f"Loop #{loop_id} 不存在")

            loop_name, vendor_id, status, current_iteration, \
                current_pass_rate, config = row

            # 設定協調器狀態
            self.loop_id = loop_id
            self.loop_name = loop_name
            self.vendor_id = vendor_id
            self.current_status = LoopStatus(status)

            # 初始化 cost_tracker
            self.cost_tracker = OpenAICostTracker(
                loop_id=loop_id,
                db_pool=self.db_pool
            )
            self.knowledge_generator.cost_tracker = self.cost_tracker

            return {
                "loop_id": loop_id,
                "loop_name": loop_name,
                "status": status,
                "current_iteration": current_iteration,
                "current_pass_rate": current_pass_rate
            }
    finally:
        self.db_pool.putconn(conn)
```

#### 方案 2：允許 `execute_iteration()` 自動載入

修改 `execute_iteration()` 檢查邏輯：
```python
async def execute_iteration(self) -> Dict:
    # 如果 loop_id 已設定但狀態為 UNINITIALIZED，嘗試載入
    if self.loop_id is not None and self.current_status == LoopStatus.UNINITIALIZED:
        await self.load_loop(self.loop_id)

    # 原有邏輯...
```

### 暫時替代方案

**當前可用的驗證流程**：

```bash
# 1. 第一次測試
./scripts/testing/run_50_verification.sh        # 建立 Loop #84，迭代 1

# 2. 前端審核知識

# 3. 第二次測試（建立新 loop）
./scripts/testing/run_50_verification.sh        # 建立 Loop #85，迭代 1

# 4. 手動比較改善幅度
# Loop #84 通過率 vs Loop #85 通過率
```

**優點**：
- 無需修改程式碼即可驗證成效
- 建立獨立的 loop 方便對比

**缺點**：
- 無法在同一個 loop 內追蹤改善幅度
- `quick_verification.sh` 的改善分析功能無法使用
- 測試集可能不同（如果未固定 scenario_ids）

### 相關文件

- 腳本：`run_next_iteration.sh`（待實作此功能後才可用）
- 驗證腳本：`quick_verification.sh`（改善幅度分析需要此功能）
- Coordinator：`rag-orchestrator/services/knowledge_completion_loop/coordinator.py`

### 實作優先級

**P1 - 高優先級**，因為：
1. 影響正常的迭代工作流程
2. 需求文檔中明確要求支援多次迭代
3. 前端審核後需要能繼續執行下一次迭代
4. 改善幅度追蹤是核心功能之一

### 驗收標準

實作完成後應通過以下測試：

```bash
# 1. 執行第一次迭代
./scripts/testing/run_50_verification.sh
# → 建立 Loop #84

# 2. 前端審核完成

# 3. 執行第二次迭代
./run_next_iteration.sh 84
# → ✅ 成功執行迭代 2

# 4. 驗證改善幅度
./quick_verification.sh 84
# → 顯示：迭代 1 (50%) vs 迭代 2 (60%) [改善 +10%]
```

---

## 2. 資料庫架構不匹配

### 問題描述
**狀態**: ⚠️ 部分實作
**優先級**: P2 - 中
**發現時間**: 2026-03-27

### 詳細說明

Requirements.md 規劃的資料庫欄位與實際架構不完全匹配：

**缺少的欄位**：
- `knowledge_completion_loops.scenario_ids` - 固定測試集
- `knowledge_completion_loops.max_iterations` - 在 config JSONB 中
- `knowledge_gap_analysis.gap_type` - 實際為 `failure_reason`
- `knowledge_gap_analysis.cluster_id` - 未實作聚類功能

**影響**：
- `quick_verification.sh` 需要適配實際架構
- 測試集固定性驗證功能部分失效
- 聚類分析功能未實作

### 建議

1. 評估是否需要嚴格按 requirements.md 實作所有欄位
2. 或調整 requirements.md 以反映實際實作狀況
3. 統一命名慣例（`gap_type` vs `failure_reason`）

---

## 總結

| 缺陷 | 優先級 | 狀態 | 影響 |
|------|--------|------|------|
| Loop 迭代續接功能 | P1 | ❌ 未實作 | 阻礙正常工作流程 |
| 資料庫架構不匹配 | P2 | ⚠️ 部分 | 部分功能受限 |
