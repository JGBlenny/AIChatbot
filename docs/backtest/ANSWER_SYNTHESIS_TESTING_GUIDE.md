# 答案合成功能測試指南

**測試日期：** 2025-10-11
**功能狀態：** ✅ 已整合到 RAG Orchestrator，等待啟用測試

---

## 📍 配置位置

### 1. RAG Orchestrator 配置

**檔案：** `rag-orchestrator/app.py` （第 66-81 行）

已整合環境變數配置：
```python
llm_optimizer_config = {
    "enable_synthesis": os.getenv("ENABLE_ANSWER_SYNTHESIS", "false").lower() == "true",
    "synthesis_threshold": float(os.getenv("SYNTHESIS_THRESHOLD", "0.7")),
    "synthesis_min_results": int(os.getenv("SYNTHESIS_MIN_RESULTS", "2")),
    "synthesis_max_results": int(os.getenv("SYNTHESIS_MAX_RESULTS", "3"))
}
```

### 2. 環境變數配置

**檔案：** `.env` （第 19-24 行）

```bash
# Answer Synthesis Configuration (Phase 3 擴展)
ENABLE_ANSWER_SYNTHESIS=false    # 預設關閉，灰度測試後再啟用
SYNTHESIS_THRESHOLD=0.7           # 觸發閾值
SYNTHESIS_MIN_RESULTS=2           # 最少需要 2 個結果
SYNTHESIS_MAX_RESULTS=3           # 最多合成 3 個答案來源
```

---

## 🚀 啟用答案合成功能

### 方式 1：修改 .env 檔案（推薦）

```bash
# 編輯 .env 檔案
nano .env

# 修改這一行：
ENABLE_ANSWER_SYNTHESIS=false  →  ENABLE_ANSWER_SYNTHESIS=true

# 儲存並重啟 RAG Orchestrator
```

### 方式 2：臨時啟用（用於測試）

```bash
# 設定環境變數並啟動
export ENABLE_ANSWER_SYNTHESIS=true
export SYNTHESIS_THRESHOLD=0.7

# 重啟 RAG Orchestrator
docker-compose restart rag-orchestrator
```

---

## 🧪 測試步驟

### 階段 1：驗證配置已載入

1. **重啟 RAG Orchestrator：**
```bash
docker-compose restart rag-orchestrator
```

2. **查看啟動日誌：**
```bash
docker-compose logs -f rag-orchestrator | grep "答案合成"
```

3. **預期看到：**
```
✅ LLM 答案優化器已初始化 (Phase 3 + 答案合成功能已啟用)
   合成閾值: 0.7
   合成來源數: 2-3
```

**如果看到「答案合成功能停用」，表示配置未生效，檢查：**
- `.env` 檔案中 `ENABLE_ANSWER_SYNTHESIS` 是否為 `true`
- Docker 是否正確載入了環境變數
- 是否需要重建 Docker 容器：`docker-compose up -d --build rag-orchestrator`

---

### 階段 2：使用 Chat API 測試

#### 測試案例 1：應該觸發合成

**問題：** 複合問題 + 低相似度

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租時押金要怎麼退還？需要什麼流程？",
    "vendor_id": 1,
    "mode": "tenant"
  }'
```

**預期行為：**
- 🔄 觸發答案合成
- ✨ 返回結構化、完整的答案
- 📊 答案涵蓋多個來源的資訊

**檢查日誌：**
```bash
docker-compose logs -f rag-orchestrator | grep -E "合成|synthesis"
```

**預期看到：**
```
🔄 答案合成觸發：問題類型=True, 最高相似度=0.65 < 0.7
✨ 答案合成完成：使用了 3 個來源，tokens: 1138
```

---

#### 測試案例 2：不應該觸發合成

**問題：** 單一簡單問題 + 高相似度

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租金是多少？",
    "vendor_id": 1,
    "mode": "tenant"
  }'
```

**預期行為：**
- ❌ 不觸發答案合成（單一答案已足夠）
- ✅ 使用傳統優化模式
- 📝 返回簡潔答案

---

#### 測試案例 3：觸發條件測試

| 測試問題 | 應該觸發？ | 原因 |
|---------|----------|------|
| 「如何辦理退租？需要準備什麼？」 | ✅ 是 | 複合問題 |
| 「退租流程和注意事項是什麼？」 | ✅ 是 | 多面向問題 |
| 「退租需要什麼文件？」 | ✅ 是 | 複合需求 |
| 「租金」 | ❌ 否 | 單一簡單問題 |
| 「繳費日是幾號？」 | ❌ 否 | 單一問題 |

---

### 階段 3：品質評估

#### 人工評估（推薦 50 個測試案例）

**評估表格：**

| 問題 | 觸發合成 | 答案完整性 | 結構清晰度 | 是否重複 | 綜合評分 |
|------|---------|-----------|-----------|---------|---------|
| 問題 1 | ✅/❌ | 1-5 | 1-5 | ✅/❌ | 1-5 |
| 問題 2 | ... | ... | ... | ... | ... |

**評分標準：**
- **完整性 (1-5)：** 答案是否涵蓋所有必要資訊
- **結構清晰度 (1-5)：** 是否使用標題、列表、步驟
- **是否重複：** 是否有重複資訊
- **綜合評分 (1-5)：** 整體品質

**目標：**
- 平均完整性 ≥ 4.0
- 平均結構清晰度 ≥ 4.0
- 無重複率 ≥ 90%
- 綜合評分 ≥ 4.0

---

#### 自動化評估（使用 LLM）

如果你已經實施了 Hybrid 回測模式，可以：

```bash
# 執行 Hybrid 回測（含 LLM 品質評估）
export ENABLE_ANSWER_SYNTHESIS=true  # 啟用合成
BACKTEST_QUALITY_MODE=hybrid \
BACKTEST_TYPE=smoke \
BACKTEST_SAMPLE_SIZE=10 \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**對比：**
1. 執行一次「無合成」回測（ENABLE_ANSWER_SYNTHESIS=false）
2. 執行一次「有合成」回測（ENABLE_ANSWER_SYNTHESIS=true）
3. 比較完整性、綜合評分的變化

---

### 階段 4：成本監控

#### Token 使用統計

**方式 1：查看日誌**
```bash
docker-compose logs rag-orchestrator | grep "答案合成完成" | awk '{print $NF}'
```

**方式 2：手動記錄**
記錄每次合成的 tokens：
- 合成 2 個來源：~700-800 tokens
- 合成 3 個來源：~1000-1200 tokens

**計算每日成本：**
```
假設：
- 每天 1000 次查詢
- 10% 觸發合成（100 次）
- 平均 900 tokens/次

成本 = 100 × 900 × $0.00000045 (GPT-4o-mini) = $0.04/天 = $1.2/月
```

---

### 階段 5：調整優化

#### 如果觸發太多（> 20%）

**調整閾值：**
```bash
# 提高觸發閾值
SYNTHESIS_THRESHOLD=0.75  # 從 0.7 → 0.75
```

**預期效果：** 只有相似度更低（< 0.75）時才觸發

---

#### 如果觸發太少（< 5%）

**調整閾值：**
```bash
# 降低觸發閾值
SYNTHESIS_THRESHOLD=0.65  # 從 0.7 → 0.65
```

**預期效果：** 更容易觸發合成

---

#### 如果合成品質不佳

**可能原因：**
1. 來源太多（導致冗長） → 減少 `SYNTHESIS_MAX_RESULTS`
2. 來源太少（不夠完整） → 增加 `SYNTHESIS_MAX_RESULTS`
3. LLM prompt 需要調整 → 修改 `llm_answer_optimizer.py` 中的 `_create_synthesis_system_prompt()`

---

## 📊 監控儀表板

### 建議監控指標

| 指標 | 監控方式 | 目標值 |
|------|---------|--------|
| **合成觸發率** | 日誌統計 | 5-15% |
| **平均完整性** | 人工評估 | ≥ 4.0 |
| **平均 tokens** | 日誌統計 | 700-1200 |
| **每日成本** | 計算 | < $0.10 |
| **用戶滿意度** | 反饋統計 | ≥ 4.0 |

---

## ✅ 決策點

### 何時全面啟用？

滿足以下條件即可全面啟用：

1. ✅ **品質指標達標：**
   - 平均完整性 ≥ 4.0
   - 綜合評分 ≥ 4.0

2. ✅ **成本可控：**
   - 每日成本在預算內（< $0.10）

3. ✅ **用戶反饋正面：**
   - 滿意度提升
   - 無負面反饋

4. ✅ **技術穩定：**
   - 無錯誤或異常
   - 觸發率在合理範圍（5-15%）

### 何時停用？

如果出現以下情況，建議暫時停用：

1. ❌ **品質下降：** 答案品質反而變差
2. ❌ **成本過高：** 超出預算 2 倍以上
3. ❌ **用戶投訴：** 收到負面反饋
4. ❌ **系統不穩定：** 頻繁出錯或超時

---

## 🔧 快速操作指令

### 啟用答案合成
```bash
# 修改 .env
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=false/ENABLE_ANSWER_SYNTHESIS=true/' .env

# 重啟服務
docker-compose restart rag-orchestrator

# 驗證配置
docker-compose logs -f rag-orchestrator | grep "答案合成"
```

### 停用答案合成
```bash
# 修改 .env
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=true/ENABLE_ANSWER_SYNTHESIS=false/' .env

# 重啟服務
docker-compose restart rag-orchestrator

# 驗證配置
docker-compose logs -f rag-orchestrator | grep "答案合成"
```

### 測試單一問題
```bash
# 儲存為 test_synthesis.sh
#!/bin/bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$1\", \"vendor_id\": 1, \"mode\": \"tenant\"}" \
  | jq '.answer'

# 使用方式
chmod +x test_synthesis.sh
./test_synthesis.sh "退租時押金要怎麼退還？需要什麼流程？"
```

---

## 📝 測試報告範本

### 灰度測試報告

**測試時間：** 2025-10-XX ~ 2025-10-XX
**測試範圍：** XX 個問題

#### 測試結果

| 指標 | 結果 | 目標 | 達標 |
|------|------|------|------|
| 合成觸發率 | X.X% | 5-15% | ✅/❌ |
| 平均完整性 | X.X/5 | ≥ 4.0 | ✅/❌ |
| 平均綜合評分 | X.X/5 | ≥ 4.0 | ✅/❌ |
| 平均 tokens | XXX | 700-1200 | ✅/❌ |
| 每日成本 | $X.XX | < $0.10 | ✅/❌ |

#### 決策建議

- [ ] 全面啟用
- [ ] 繼續測試（延長 X 週）
- [ ] 調整參數（XXX）
- [ ] 暫時停用

---

## 🎯 總結

### 測試清單

- [ ] 修改 `.env` 啟用答案合成
- [ ] 重啟 RAG Orchestrator
- [ ] 驗證配置已載入
- [ ] 測試觸發條件（3+ 個案例）
- [ ] 人工評估品質（50 個案例）
- [ ] 監控成本
- [ ] 收集用戶反饋
- [ ] 記錄測試結果
- [ ] 做出啟用/停用決策

---

**最後更新：** 2025-10-11
**下一步：** 啟用灰度測試
**預計測試時長：** 1-2 週
