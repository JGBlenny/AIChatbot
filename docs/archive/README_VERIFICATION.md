# 知識完善迴圈 - 驗證測試指南

## 🎯 快速開始

### 三種測試規模

```bash
# 1. 快速驗證（50 題）- 驗證系統穩定性
./run_50_verification.sh

# 2. 標準測試（500 題）- 正式測試流程
./run_500_verification.sh

# 3. 全面評估（3000 題）- 大規模測試
./run_3000_verification.sh
```

### 前置準備

```bash
# 設定 OpenAI API Key（必須）
export OPENAI_API_KEY='your-api-key-here'

# 確認 Docker 容器運行
docker ps | grep aichatbot
```

---

## 📋 測試策略

### 階段 1：50 題快速驗證（推薦先執行）

**目標**：驗證核心功能穩定性
- ✅ 測試集固定性（scenario_ids）
- ✅ 立即同步機制
- ✅ 改善幅度可追蹤

**執行**：
```bash
./run_50_verification.sh
```

**預計耗時**：10-15 分鐘

**驗證**：
```bash
# 查詢 Loop ID
LOOP_ID=$(docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
  "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;" | xargs)

# 快速驗證
./quick_verification.sh $LOOP_ID
```

**通過標準**：
```
✅ 測試集固定性：PASS
✅ 立即同步：PASS
✅ 改善幅度可追蹤：PASS
```

---

### 階段 2：500 題標準測試

**目標**：正式測試流程，接近實際使用場景

**執行**：
```bash
./run_500_verification.sh
```

**預計耗時**：60-90 分鐘（第一次迭代）

**特點**：
- 測試題數充足（500 題）
- 知識生成數量合理（約 30-50 個/迭代）
- 審核工作量可控（批量審核約 15 分鐘）

**迭代流程**：

⚠️ **注意**：`run_next_iteration.sh` 目前無法使用（見 `docs/backtest/IMPLEMENTATION_GAPS.md`）

**當前可用的替代流程**：
```bash
# 第一次測試
./run_500_verification.sh              # 建立 Loop #85
# 前端審核知識並通過

# 第二次測試（驗證改善）
./run_500_verification.sh              # 建立 Loop #86（知識庫已有新知識）

# 比較改善幅度
# Loop #85 通過率 vs Loop #86 通過率
```

**未來支援的流程（待實作）**：
```bash
# 第一次迭代
./run_500_verification.sh              # 建立 Loop #13
./quick_verification.sh 13
# 人工審核

# 第二次迭代（同一個 loop）
./run_next_iteration.sh 13             # ⚠️ 待實作
./quick_verification.sh 13             # 顯示改善幅度
```

---

### 階段 3：3000 題全面評估（選擇性）

**目標**：大規模測試，接近完整題庫

**警告**：
- ⚠️ 耗時長（90-120 分鐘/迭代）
- ⚠️ 知識生成多（約 200-300 個/迭代）
- ⚠️ 審核工作重（需批量處理）

**執行**：
```bash
./run_3000_verification.sh             # 會要求確認
```

**建議**：
- 在 50 題和 500 題測試通過後再執行
- 使用批量審核功能處理大量知識
- 考慮分批處理（6×500 比 1×3000 更有效）

---

## 🔄 完整測試流程

### 典型工作流程

```bash
# === 第一階段：50 題驗證（必須） ===
export OPENAI_API_KEY='your-key-here'

# 執行第一次迭代
./run_50_verification.sh
# 輸出：Loop #12 建立

# 驗證結果
./quick_verification.sh 12

# 人工審核（選項 A：前端）
# 開啟 http://localhost:5178
# 進入「知識審核中心」→「迴圈生成知識」
# 使用批量審核功能批准知識

# 或者（選項 B：資料庫直接批准）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE loop_generated_knowledge
SET status = 'approved', reviewed_at = NOW()
WHERE loop_id = 12 AND status = 'pending_review';
"

# 驗證同步
./quick_verification.sh 12
# 預期：同步數量匹配批准數量

# 執行第二次迭代
./run_next_iteration.sh 12

# 驗證改善幅度
./quick_verification.sh 12
# 預期：可追蹤改善幅度，測試集固定

# === 第二階段：500 題測試（建議） ===
./run_500_verification.sh
# 輸出：Loop #13 建立

# 重複上述審核與迭代流程...
./run_next_iteration.sh 13
./run_next_iteration.sh 13
# 直到達標（通過率 ≥ 85%）

# === 第三階段：3000 題評估（選擇性） ===
./run_3000_verification.sh
# 輸出：Loop #14 建立
```

---

## 📊 腳本對照表

| 腳本 | 測試題數 | 用途 | 重複使用 |
|------|---------|------|---------|
| `run_50_verification.sh` | 50 | 快速驗證 | ✅ 可以 |
| `run_500_verification.sh` | 500 | 標準測試 | ✅ 可以 |
| `run_3000_verification.sh` | 3000 | 全面評估 | ✅ 可以 |
| `run_next_iteration.sh <id>` | 同一 loop | 繼續迭代 | ✅ 可以 |
| `quick_verification.sh <id>` | - | 驗證工具 | ✅ 可以 |

### 使用範例

**情境 1：首次測試**
```bash
./run_50_verification.sh      # Loop #12（50 題）
./run_500_verification.sh     # Loop #13（500 題）
```

**情境 2：重新驗證穩定性**
```bash
./run_50_verification.sh      # Loop #14（另一組 50 題）
./run_50_verification.sh      # Loop #15（再一組 50 題）
# 比較 Loop #12, #14, #15 的結果是否一致
```

**情境 3：測試不同配置**
```bash
# 修改腳本內的 target_pass_rate（例如改為 0.90）
./run_500_verification.sh     # Loop #16（目標 90%）
```

**情境 4：繼續未完成的 loop**
```bash
# Loop #13 還沒達標（通過率 75%）
./run_next_iteration.sh 13    # 第 3 次迭代
./run_next_iteration.sh 13    # 第 4 次迭代
./quick_verification.sh 13    # 檢查狀態
```

---

## ✅ 驗證檢查清單

### 50 題驗證（必須通過）

- [ ] 執行 `./run_50_verification.sh` 成功
- [ ] 回測完成（50 題）
- [ ] 知識生成（約 5-15 個）
- [ ] scenario_ids 已儲存（`./quick_verification.sh` 驗證）
- [ ] 人工審核完成（批量批准測試）
- [ ] 立即同步成功（同步數 = 批准數）
- [ ] 執行第二次迭代成功（`./run_next_iteration.sh`）
- [ ] 改善幅度可追蹤（通過率變化可量化）
- [ ] `./quick_verification.sh` 輸出全部 PASS

### 500 題測試（建議執行）

- [ ] 執行 `./run_500_verification.sh` 成功
- [ ] 回測完成（500 題）
- [ ] 知識生成（約 30-50 個）
- [ ] 批量審核效率測試（50 個項目 < 20 秒）
- [ ] 執行至少 2 次迭代
- [ ] 通過率持續改善
- [ ] 最終達標（≥ 85%）

### 3000 題評估（選擇性）

- [ ] 系統穩定性確認（50 題 + 500 題已通過）
- [ ] 執行 `./run_3000_verification.sh` 成功
- [ ] 回測完成（3000 題）
- [ ] 大量知識審核測試（200+ 個項目）
- [ ] 效能監控（記憶體、耗時）
- [ ] 達標或確認改善趨勢

---

## 🛠️ 故障排除

### 問題 1：腳本執行失敗

**症狀**：`command not found` 或 `permission denied`

**解決**：
```bash
chmod +x *.sh
```

### 問題 2：OpenAI API Key 錯誤

**症狀**：`❌ 錯誤：未設定 OPENAI_API_KEY`

**解決**：
```bash
export OPENAI_API_KEY='sk-...'
echo $OPENAI_API_KEY  # 驗證已設定
```

### 問題 3：Docker 容器未運行

**症狀**：`Cannot connect to the Docker daemon`

**解決**：
```bash
docker-compose up -d
docker ps | grep aichatbot
```

### 問題 4：資料庫連接失敗

**檢查**：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT 1;"
```

### 問題 5：回測超時

**症狀**：500 或 3000 題測試時出現超時

**解決**：
- 檢查 RAG API 服務狀態
- 增加超時設定
- 考慮分批執行（例如 6×500 代替 1×3000）

### 問題 6：記憶體不足

**症狀**：3000 題測試時記憶體耗盡

**解決**：
- 使用 6×500 策略代替
- 增加 Docker 記憶體限制
- 監控系統資源使用

---

## 📈 效能指標

### 預期耗時（參考值）

| 測試規模 | 回測耗時 | 知識生成 | 人工審核 | 總耗時 |
|---------|---------|---------|---------|--------|
| 50 題   | 5-8 分鐘 | 1-2 分鐘 | 5 分鐘   | 10-15 分鐘 |
| 500 題  | 50-70 分鐘 | 5-10 分鐘 | 15-20 分鐘 | 70-100 分鐘 |
| 3000 題 | 300-400 分鐘 | 20-30 分鐘 | 60-90 分鐘 | 380-520 分鐘 |

### 預期成本（參考值）

| 測試規模 | 第一次迭代 | 單次迭代 | 5 次迭代累計 |
|---------|-----------|---------|-------------|
| 50 題   | $2-3 USD  | $1-2 USD | $5-10 USD   |
| 500 題  | $15-20 USD | $8-12 USD | $50-70 USD  |
| 3000 題 | $80-100 USD | $40-60 USD | $250-350 USD |

---

## 🎓 最佳實踐

### 1. 循序漸進

```
50 題驗證 ✅ → 500 題測試 ✅ → 3000 題評估
```

不要跳過 50 題驗證，它能快速發現問題。

### 2. 使用批量審核

對於 500 題以上的測試，批量審核可節省 75% 時間：
- 單個審核：50 個項目 × 60 秒 = 50 分鐘
- 批量審核：全選 → 批准 = 5-10 分鐘

### 3. 監控改善幅度

每次迭代後執行：
```bash
./quick_verification.sh <loop_id>
```

確認通過率持續改善。

### 4. 記錄測試結果

填寫 `test_verification_log.md`，記錄：
- Loop ID 與配置
- 每次迭代的結果
- 發現的問題
- 最終結論

### 5. 分階段目標

- 50 題：驗證穩定性（目標：所有檢查 PASS）
- 500 題：驗證效果（目標：通過率 ≥ 85%）
- 3000 題：驗證規模化（目標：效能可接受 + 通過率 ≥ 85%）

---

## 📝 下一步

完成驗證測試後：

```bash
# 1. 查看驗證總結
./quick_verification.sh <loop_id>

# 2. 如果全部通過
/kiro:spec-design backtest-knowledge-refinement -y

# 3. 進入設計階段
# 開始詳細的技術設計
```

祝測試順利！🎉
