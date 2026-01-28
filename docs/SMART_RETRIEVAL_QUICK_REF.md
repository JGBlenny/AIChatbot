# 智能檢索系統快速參考

## 🎯 核心原則

1. **SOP 和知識庫永遠不混合**
2. **使用 Reranker 分數公平比較**
3. **並行檢索提升效能**
4. **答案合成僅用於知識庫**

---

## 📊 決策邏輯

### 閾值設定

```python
SCORE_GAP_THRESHOLD = 0.15      # 分數差距閾值
SOP_MIN_THRESHOLD = 0.55         # SOP 最低分數
KNOWLEDGE_MIN_THRESHOLD = 0.6    # 知識庫最低分數（代碼中）
```

### 決策流程圖

```
並行檢索
    ↓
提取分數
    ↓
計算差距
    ↓
┌─────────────────────────────────┐
│ SOP > 知識庫 + 0.15？           │
│   ✅ → 選擇 SOP                 │
└─────────────────────────────────┘
    ↓ ❌
┌─────────────────────────────────┐
│ 知識庫 > SOP + 0.15？           │
│   ✅ → 選擇知識庫               │
└─────────────────────────────────┘
    ↓ ❌
┌─────────────────────────────────┐
│ 分數接近 (差距 < 0.15)          │
│   ├─ SOP 有動作？✅ → 選擇 SOP  │
│   └─ 否 → 選擇分數較高者        │
└─────────────────────────────────┘
```

---

## 🔍 API 回應結構

### comparison_metadata 欄位

```json
{
  "sop_score": 0.929,              // SOP 最高分
  "knowledge_score": 0.960,         // 知識庫最高分
  "gap": 0.031,                     // 分數差距
  "sop_candidates": 1,              // SOP 候選數
  "knowledge_candidates": 2,        // 知識庫候選數
  "decision_case": "close_scores_sop_has_action"
}
```

### decision_case 類型

| 類型 | 說明 |
|------|------|
| `sop_significantly_higher` | SOP 顯著更高 |
| `knowledge_significantly_higher` | 知識庫顯著更高 |
| `close_scores_sop_has_action` | 分數接近，SOP 有動作優先 |
| `sop_slightly_higher` | 分數接近，SOP 稍高（無動作） |
| `knowledge_slightly_higher` | 分數接近，知識庫稍高 |
| `only_sop_qualified` | 僅 SOP 達標 |
| `only_knowledge_qualified` | 僅知識庫達標 |
| `both_below_threshold` | 兩者皆未達標 |

---

## 🧪 快速測試

### 使用測試腳本

```bash
/tmp/test_smart_retrieval.sh
```

### 手動測試命令

```bash
# 測試 1: SOP 顯著更高
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租金怎麼繳",
    "vendor_id": 1,
    "user_role": "tenant",
    "user_id": "test",
    "include_debug_info": true
  }'

# 測試 2: 知識庫顯著更高
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "押金是多少",
    "vendor_id": 1,
    "user_role": "tenant",
    "user_id": "test",
    "include_debug_info": true
  }'

# 測試 3: 分數接近 + SOP 有動作
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想要報修",
    "vendor_id": 1,
    "user_role": "tenant",
    "user_id": "test",
    "include_debug_info": true
  }'
```

---

## 🔧 調整參數

### 修改分數差距閾值

**文件**: `rag-orchestrator/routers/chat.py`
**位置**: Line 621

```python
SCORE_GAP_THRESHOLD = 0.15  # 修改這個值
```

**影響**:
- **增大** (如 0.20): SOP 和知識庫更容易被視為「分數接近」
- **縮小** (如 0.05): 需要更接近的分數才會考慮 SOP 優先

### 修改最低閾值

```python
SOP_MIN_THRESHOLD = 0.55          # SOP 最低分數
KNOWLEDGE_MIN_THRESHOLD = 0.6     # 知識庫最低分數
```

---

## 📝 日誌查看

### 關鍵日誌標記

```
🔍 [智能檢索] 同時檢索 SOP 和知識庫
📊 [分數比較]
✅ [決策]
🎯 [最終決策]
```

### 查看即時日誌

```bash
docker-compose logs -f rag-orchestrator | grep -E "(智能檢索|分數比較|決策)"
```

---

## 🐛 常見問題

### Q1: SOP 候選顯示為空

**檢查**: SOP 候選結構是否包含 `item_name` 和 `boosted_similarity`

**文件**: `chat.py` Line 1636-1644

### Q2: comparison_metadata 為 null

**檢查**: 是否傳遞了 `decision` 參數到 `_build_orchestrator_response`

**文件**: `chat.py` Line 2329

### Q3: 前端顯示路徑原始值

**檢查**: 前端映射表是否包含該路徑

**文件**: `ChatTestView.vue` Line 707

---

## 📚 相關文檔

- **完整實施報告**: `SMART_RETRIEVAL_IMPLEMENTATION.md`
- **更新日誌**: `CHANGELOG_2026-01-28.md`
- **Reranker 實施**: `RERANKER_IMPLEMENTATION.md`

---

**最後更新**: 2026-01-28
**狀態**: ✅ 運作正常
