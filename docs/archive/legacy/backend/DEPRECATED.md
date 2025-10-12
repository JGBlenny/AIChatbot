# 此目錄已廢棄 (DEPRECATED)

**廢棄日期**: 2025-10-13
**原因**: 已被 `rag-orchestrator` 取代

## 歷史背景

此目錄包含早期版本的 FastAPI 應用程式，當時系統架構如下：

```
/backend/
  ├── app/
  │   ├── main.py           # 舊版主應用
  │   ├── api/              # 舊版 API 路由
  │   │   ├── conversations.py
  │   │   ├── processing.py
  │   │   └── knowledge.py
  │   ├── services/         # 舊版服務層
  │   │   ├── line_parser.py
  │   │   ├── openai_service.py
  │   │   └── markdown_generator.py
  │   └── models/           # 舊版數據模型
  └── tests/
```

## 為何廢棄

在 2024 年 Q4，系統進行了重大架構重構：

1. **服務拆分**: 將單體應用拆分為多個微服務
   - `rag-orchestrator`: 核心 RAG 服務（取代此 backend）
   - `knowledge-admin`: 知識庫管理後台
   - `embedding-service`: 向量嵌入服務

2. **功能增強**:
   - 新增多業者支援 (Multi-Vendor)
   - 新增意圖分類系統
   - 新增回測框架
   - 新增 B2B/B2C 業務隔離

3. **技術升級**:
   - 引入 pgvector 向量數據庫
   - 引入 Redis 快取層
   - 更完善的錯誤處理
   - 更好的可擴展性

## 新架構位置

| 舊位置 | 新位置 | 說明 |
|--------|--------|------|
| `backend/app/main.py` | `rag-orchestrator/app.py` | 主應用 |
| `backend/app/api/` | `rag-orchestrator/routers/` | API 路由 |
| `backend/app/services/` | `rag-orchestrator/services/` | 服務層 |
| `backend/app/models/` | `rag-orchestrator/models/` | 數據模型 |

## 保留原因

此目錄被保留在 archive 中，而非直接刪除，原因：

1. **歷史參考**: 可能需要查看舊版實現方式
2. **測試程式**: 包含一些測試程式碼可能有參考價值
3. **遷移追蹤**: 保留遷移軌跡，方便未來審計

## 相關文件

- 新系統文檔: `/docs/architecture/SYSTEM_ARCHITECTURE.md`
- 遷移指南: （尚未創建）
- API 文檔: `/docs/api/API_REFERENCE_PHASE1.md`

---

**注意**: 此目錄中的代碼已不再維護，請勿使用於生產環境。
