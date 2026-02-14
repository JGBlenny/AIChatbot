# 回測結果知識庫優化指南

## 📋 問題：如何根據回測結果優化知識庫？

當回測失敗時，系統現在會明確告訴你**哪些知識條目**需要優化。

---

## ✅ 解決方案：知識來源追蹤

### **回測框架改進（v1.4.0）**

回測結果現在包含：

| 欄位 | 說明 | 範例 |
|------|------|------|
| `knowledge_sources` | 知識來源摘要 | `[178] 租客的租金計算方式是什麼？; [173] 為什麼要以迄月日數...` |
| `source_ids` | 知識庫 IDs（逗號分隔）| `178,173,146` |
| `source_count` | 來源數量 | `3` |
| `knowledge_links` | 🆕 知識庫直接鏈接（換行分隔）| `http://localhost:8080/#/knowledge?search=178` |
| `batch_url` | 🆕 批量查詢鏈接 | `http://localhost:8080/#/knowledge?ids=178,173,146` |

---

## 🔍 使用方式

### **1. 執行回測**

```bash
python3 scripts/knowledge_extraction/backtest_framework.py
```

### **2. 查看控制台輸出**

```
[1/10] 測試問題: 租金如何計算？...
   ✅ PASS (分數: 0.87)
   📚 知識來源 (3 個):
      1. [ID 178] 租客的租金計算方式是什麼？
      2. [ID 173] 為什麼要以迄月日數來計算首月租金？
      3. [ID 146] 如何處理開啟前的負數租金？
   🔗 直接鏈接:
      1. http://localhost:8080/#/knowledge?search=178
      2. http://localhost:8080/#/knowledge?search=173
      3. http://localhost:8080/#/knowledge?search=146
   📦 批量查詢: http://localhost:8080/#/knowledge?ids=178,173,146
   ✅ 測試通過，但仍有優化空間:
   ✅ 多意圖匹配: 預期「帳務問題」在次要意圖中找到
```

**🆕 直接導航到知識庫（v1.5.0）**：
- 點擊 🔗 直接鏈接，可快速訪問特定知識條目
- 點擊 📦 批量查詢，可一次查看所有相關知識

### **3. 失敗案例 - 知道該改什麼**

如果測試失敗：

```
[5/10] 測試問題: 忘記密碼怎麼辦？...
   ❌ FAIL (分數: 0.27)
   📚 知識來源 (1 個):
      1. [ID 223] 重設密碼流程
   意圖分類不匹配: 預期「帳號問題」但識別為「unclear」
   💡 建議: 新增「帳號問題」意圖以提升準確性
```

**你現在知道**：
- 系統找到了 ID 223 的知識
- 但這個知識沒有被正確分類到「帳號問題」意圖
- **行動**：去資料庫將 ID 223 關聯到「帳號問題」意圖

---

## 📊 查看詳細結果

### **方法 1：Excel 檔案**

打開 `output/backtest/backtest_results.xlsx`：

| test_question | passed | knowledge_sources | source_ids | batch_url | optimization_tips |
|--------------|--------|-------------------|------------|-----------|-------------------|
| 租金如何計算？ | TRUE | [178] 租客的租金... | 178,173,146 | http://localhost:8080/#/knowledge?ids=178,173,146 | ✅ 測試通過... |
| 忘記密碼怎麼辦？ | FALSE | [223] 重設密碼流程 | 223 | http://localhost:8080/#/knowledge?ids=223 | 意圖分類不匹配... |

**💡 快速訪問**：Excel 中的 `batch_url` 欄位可以直接點擊打開，快速跳轉到相關知識條目。

### **方法 2：摘要報告**

查看 `output/backtest/backtest_results_summary.txt`：

```
============================================================
失敗案例
============================================================

問題：忘記密碼怎麼辦？
預期分類：帳號問題
實際意圖：unclear
分數：0.27
知識來源：[223] 重設密碼流程
來源IDs：223
知識庫鏈接：
http://localhost:8080/#/knowledge?search=223
批量查詢：http://localhost:8080/#/knowledge?ids=223
優化建議：
意圖分類不匹配: 預期「帳號問題」但識別為「unclear」
   💡 建議: 新增「帳號問題」意圖以提升準確性
------------------------------------------------------------
```

**💡 快速訪問**：複製摘要報告中的 URL 到瀏覽器，即可直接查看需要優化的知識條目。

---

## 🛠️ 優化流程

### **步驟 1：找出失敗案例的知識 IDs**

從回測結果中找到 `source_ids` 欄位：
```
source_ids: 223
```

### **步驟 2：查詢這些知識的詳細資訊**

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT id, title, intent_id, keywords
FROM knowledge_base
WHERE id IN (223);
"
```

結果：
```
 id  |     title      | intent_id |    keywords
-----+----------------+-----------+-----------------
 223 | 重設密碼流程   |           | {密碼,重設}
```

### **步驟 3：根據優化建議修改**

**建議說「新增帳號問題意圖」**：

```bash
# 1. 確認「帳號問題」意圖 ID
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT id FROM intents WHERE name = '帳號問題';
"
# 結果: id = 14

# 2. 更新知識的 intent_id
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE knowledge_base
SET intent_id = 14
WHERE id = 223;
"

# 3. 重新載入意圖配置
curl -X POST http://localhost:8100/api/v1/intents/reload
```

### **步驟 4：重新回測驗證**

```bash
python3 scripts/knowledge_extraction/backtest_framework.py
```

應該會看到：
```
[5/10] 測試問題: 忘記密碼怎麼辦？...
   ✅ PASS (分數: 0.90)
   📚 知識來源 (1 個):
      1. [ID 223] 重設密碼流程
```

---

## 📈 常見優化場景

### **場景 1：意圖分類錯誤**

**症狀**：
```
意圖分類不匹配: 預期「合約規定」但識別為「unclear」
知識來源：[ID 45] 租約期限說明
```

**解決**：
1. 將 ID 45 關聯到「合約規定」意圖
2. 或新增「合約規定」意圖（如不存在）

---

### **場景 2：答案缺少關鍵字**

**症狀**：
```
答案缺少關鍵字: 押金, 退還
知識來源：[ID 12] 退租流程
```

**解決**：
1. 查看 ID 12 的內容
2. 補充「押金退還」相關說明
3. 或新增專門的「押金退還」知識條目

---

### **場景 3：信心度過低**

**症狀**：
```
信心度過低 (0.45)
知識來源：[ID 88] 繳費方式說明
```

**解決**：
1. 檢查 ID 88 的內容是否完整
2. 優化關鍵字（更貼近常見問法）
3. 確保知識與意圖正確關聯

---

## 🎯 最佳實踐

### ✅ **DO（推薦做法）**

1. **定期回測**
   ```bash
   # 每次更新知識後執行
   python3 scripts/knowledge_extraction/backtest_framework.py
   ```

2. **優先處理失敗案例**
   - 從 Excel 篩選 `passed = FALSE`
   - 按 `score` 排序，從最低分開始修

3. **追蹤優化效果**
   - 記錄修改前的分數
   - 修改後重測，確認改進

4. **使用知識 IDs 精準定位**
   - 不要猜測要改哪個知識
   - 直接用 `source_ids` 查詢

### ❌ **DON'T（避免做法）**

1. ❌ 不要只看優化建議，要看知識來源
2. ❌ 不要盲目新增知識（可能重複）
3. ❌ 不要修改測試預期（除非預期本身錯誤）
4. ❌ 不要忽略 `PASS` 但分數低的案例

---

## 📝 快速查詢命令

```bash
# 1. 查詢特定知識詳情
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT id, title, intent_id, keywords, scope
FROM knowledge_base
WHERE id = 223;
"

# 2. 更新知識的意圖
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE knowledge_base
SET intent_id = 14
WHERE id = 223;
"

# 3. 查詢某意圖下的所有知識
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT id, title
FROM knowledge_base
WHERE intent_id = 14;
"

# 4. 重新載入配置
curl -X POST http://localhost:8100/api/v1/intents/reload
```

---

## 🆕 更新日誌

### v1.5.0 (2025-10-11)

- ✅ 新增 `knowledge_links` 欄位（知識庫直接鏈接）
- ✅ 新增 `batch_url` 欄位（批量查詢鏈接）
- ✅ 控制台顯示可點擊的知識庫 URL
- ✅ 摘要報告包含知識庫直接鏈接
- ✅ 支援從回測結果直接導航到知識管理界面

### v1.4.0 (2025-10-11)

- ✅ 新增 `knowledge_sources` 欄位（知識來源摘要）
- ✅ 新增 `source_ids` 欄位（知識 IDs）
- ✅ 新增 `source_count` 欄位（來源數量）
- ✅ 控制台即時顯示知識來源
- ✅ 摘要報告包含知識來源資訊

### v1.3.0 (2025-10-11)

- 支援多 Intent 評估
- 模糊匹配意圖名稱
- 差異化加成策略

---

**維護者**: Claude Code
**最後更新**: 2025-10-11
**相關文檔**:
- [回測優化指南](../BACKTEST_OPTIMIZATION_GUIDE.md)
- [多 Intent 分類系統](./MULTI_INTENT_CLASSIFICATION.md)
