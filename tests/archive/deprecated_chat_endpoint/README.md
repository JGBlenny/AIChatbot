# 已廢棄的 /api/v1/chat 端點測試

**歸檔日期**: 2025-10-21
**原因**: `/api/v1/chat` 端點已被移除

## 歸檔的測試文件

| 文件 | 原始路徑 | 用途 |
|------|---------|------|
| `test_chat_performance.py` | `tests/performance/` | 完整對話流程性能測試 |
| `test_enhanced_detection_api.py` | `tests/deduplication/` | 去重檢測 API 測試 |

## 端點移除詳情

- **移除日期**: 2025-10-21
- **移除原因**: 功能已由更強大的端點替代
- **替代端點**:
  - `/api/v1/message` - 多業者通用端點
  - `/api/v1/chat/stream` - 流式聊天端點

## 遷移建議

如需重新啟用這些測試，請：

1. 複製測試文件
2. 更新端點從 `/api/v1/chat` → `/api/v1/message`
3. 更新請求參數：
   ```python
   # 舊格式
   {
     "question": "...",
     "vendor_id": 1,
     "user_role": "customer",
     "user_id": "..."
   }

   # 新格式
   {
     "message": "...",  # question → message
     "vendor_id": 1,
     "user_role": "customer",
     "user_id": "...",
     "mode": "tenant",  # 新增
     "include_sources": true  # 新增（可選）
   }
   ```
4. 更新響應欄位名稱（參考遷移指南）

## 相關文檔

- [盤查報告](../../../docs/api/CHAT_ENDPOINT_REMOVAL_AUDIT.md)
- [遷移指南](../../../docs/api/CHAT_API_MIGRATION_GUIDE.md)

---

**注意**: 這些測試僅作為參考保留，不應再執行。
