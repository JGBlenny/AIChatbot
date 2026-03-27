# Deprecated Scripts（已棄用的腳本）

本目錄包含依賴未實作功能的腳本，暫時無法使用。

## 已棄用的腳本

### `run_next_iteration.sh`
**移除原因**：依賴尚未實作的前端 API 整合與非同步執行架構

**原始功能**：
- 執行知識完善迴圈的下一次迭代
- 檢查審核狀態並觸發新的迴圈

**無法使用的原因**：
- 需要前端 API 路由層 (`routers/loops.py`) 支援迴圈管理
- 需要非同步執行管理器 (`AsyncExecutionManager`) 處理長時間任務
- 需要完整的迴圈狀態機實作

**替代方案**：
目前請使用基礎回測腳本：
```bash
# 50 題驗證回測
./run_50_verification.sh

# 500 題標準回測
./run_500_verification.sh

# 3000 題完整回測
./run_3000_verification.sh
```

**恢復時機**：
當實作以下任務後可恢復使用：
- 任務 3：非同步執行管理器實作
- 任務 5：迴圈管理 API 路由層實作

---

### `quick_verification.sh`
**移除原因**：依賴尚未實作的驗證效果回測功能

**原始功能**：
- 快速驗證知識改善效果
- 只測試失敗案例 + 抽樣通過案例
- 縮短驗證時間

**無法使用的原因**：
- 需要 `LoopCoordinator.validate_loop()` 方法支援驗證回測
- 需要前端 API 端點 `POST /loops/{loop_id}/validate`
- 需要 regression 檢測機制

**替代方案**：
目前請使用完整迭代回測（測試所有固定測試集）：
```bash
# 執行完整迭代以驗證知識改善效果
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

**恢復時機**：
當實作以下任務後可恢復使用：
- 任務 4.2：實作驗證回測主流程
- 任務 4.3：實作 regression 檢測邏輯
- 任務 5.5：實作驗證回測端點

---

## 可用的替代腳本

請使用根目錄下的以下腳本：

1. **`run_50_verification.sh`** - 快速驗證（50 題）
   - 適用於快速測試知識庫變更
   - 執行時間約 10-15 分鐘

2. **`run_500_verification.sh`** - 標準驗證（500 題）
   - 適用於標準測試覆蓋率
   - 執行時間約 60-90 分鐘

3. **`run_3000_verification.sh`** - 完整驗證（3000 題）
   - 適用於全面評估知識庫品質
   - 執行時間約 90-120 分鐘

---

## 相關文檔

- [任務清單](../../.kiro/specs/backtest-knowledge-refinement/tasks.md) - 查看實作進度
- [設計文檔](../../.kiro/specs/backtest-knowledge-refinement/design.md) - 了解系統架構
- [QUICK_REFERENCE.md](../../docs/backtest/QUICK_REFERENCE.md) - 回測系統快速參考

---

*最後更新：2026-03-27*
*狀態：等待前端 API 整合完成後恢復*
