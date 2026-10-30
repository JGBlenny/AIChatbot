# API 文檔索引

**最後更新**: 2026-01-20
**維護者**: Claude Code

本文檔提供所有 API 相關文檔的快速索引和導航。

---

## 📚 快速導航

### 🎯 核心必讀文檔

🔴 **2026-09-12：這一節原本的三份「新手必讀」已全部移除。**
它們教的是統一動態 API 執行引擎（`universal_api_handler` / `api_call_handler`），
該機制隨舊 REST 對話鏈於 2026-09-11 刪除，**agentic-MCP 新線沒有對應物**——
工具呼叫改走 `services/agent/tools/registry.py` 的 in-process 註冊表。

設計或新串接先讀 [`docs/architecture/TARGET_ARCHITECTURE.md`](../architecture/TARGET_ARCHITECTURE.md)：目標是呼叫端走專用對話 API，`/mcp` 不是最終入口。

想了解現況，讀這三份：

1. [`docs/architecture/SYSTEM_ARCHITECTURE.md`](../architecture/SYSTEM_ARCHITECTURE.md) — 全景（核心／門面／知識兩條路）
2. [`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../architecture/AGENTIC_MCP_ARCHITECTURE.md) §2b — 一回合的完整流程
3. [`docs/api/mcp-facade.md`](./mcp-facade.md) — `/mcp` 串接契約（header、工具、錯誤碼、額度）

---

## 📋 所有文檔列表

### 📁 本目錄（`docs/api/`）的文件

> ⚠️ 2026-09-04 補上。此前本索引只導向 `../design/` 與 `../guides/api/`，**同目錄一份都沒列**，
> 導致這 14 份 API 契約與參考沒有任何入口。⛔ 新增同目錄檔案時務必回來補這張表。

**交付 jgb2 的對外契約**（本 repo → jgb2 的需求契約）

| 文檔 | 用途 | ⚠️ 注意 |
|------|------|--------|
| [account-api-contract.md](./account-api-contract.md) | 帳號 G/J 對外契約 | 驗證狀態為 2026-07 快照 |
| [billing-api-contract.md](./billing-api-contract.md) | 帳務 G/J 對外契約 | 同上 |
| [estate-api-contract.md](./estate-api-contract.md) | 物件領域契約 | 同上 |
| [g1-g4-api-contract.md](./g1-g4-api-contract.md) | G1–G4 合約欄位擴充 | 逐 gate「✓ 已驗證」是 2026-07-02 當時狀態 |
| [iot-api-contract.md](./iot-api-contract.md) | IoT J/G 契約（台科電＝DAE） | 「jgb2 已修復並部署」為 2026-07-04 當時狀態 |
| [repair-api-contract.md](./repair-api-contract.md) | 修繕租約清單契約 | 含 E1 真 API 上線 gate 的分支落差提醒 |
| [jgb-contracts-api-spec.md](./jgb-contracts-api-spec.md) | 合約查詢 API 完整規格提案（2026-04-20） | 對碼結果（2026-09-10，見檔頭）：提出的端點 `GET /api/external/v1/contracts` 查無實作，已被 `g1-g4-api-contract.md`（`status-overview`）取代；業務判斷邏輯段仍作背景參考 |

> ⛔ 這批是混合體：**欄位與介面定義是雙方仍在遵守的約定**，而逐條「✓ 已驗證」是時點狀態。
> 用前一律對 jgb2 現碼重驗。

**jgb2 規格副本**

| 文檔 | 用途 | ⚠️ 注意 |
|------|------|--------|
| [jgb_external_api_spec.md](./jgb_external_api_spec.md) | jgb2 `external/v1` 端點規格（v1.1） | 🔴 **只列 14 支，jgb2 實有 24 支**——缺 `recharge-accounts` 兩支／`repairs` 三支／`tenants/registration-status`／`meters` 兩支／`roles` members 兩支。完整清單見 `.kiro/specs/agentic-mcp-orchestration/jgb2-source-index.md` §3.4 |

**本 repo 自己的 API**

| 文檔 | 用途 | ⚠️ 注意 |
|------|------|--------|
| [API_REFERENCE_PHASE1.md](./API_REFERENCE_PHASE1.md) | 聊天／快取管理／業者管理核心 API | 「Phase 1」是功能集合命名，文件版本已到 3.1 |
| [API_REFERENCE_KNOWLEDGE_ADMIN.md](./API_REFERENCE_KNOWLEDGE_ADMIN.md) | 知識後台九模塊（端點數隨程式增減，不寫死，查證指令見表下註） | ⛔ **不是** `KNOWLEDGE_ADMIN_API.md` 的超集，兩份重疊至少 4 支（`GET`／`POST` `/api/knowledge`、`PUT`／`DELETE` `/api/knowledge/{id}`） |
| [KNOWLEDGE_ADMIN_API.md](./KNOWLEDGE_ADMIN_API.md) | 知識管理精簡版（約 6 支端點） | 對碼結果（2026-10-18，見檔頭）：`PUT`／`DELETE /api/knowledge/{id}` 存在於 `knowledge-admin/backend/app.py`；登入為 `POST /api/auth/login`（`routes_auth.py`），非 `POST /api/login` |
| [loops_api.md](./loops_api.md) | 知識完善迴圈生命週期 | 產線：`rag-orchestrator/routers/loops.py` |
| [loop_knowledge_api.md](./loop_knowledge_api.md) | 迴圈生成知識的審核端點 | 產線：`rag-orchestrator/routers/loop_knowledge.py` |
| [conversational-api.md](./conversational-api.md) | 對話式回答的對外串接指南 | 已列於 `.claude/MAP.md`〈對話邏輯與路由執行〉 |

> 知識後台端點數查證（2026-10-18 為 66 個裝飾器，含 `routes_*.py`）：`grep -rhoE "@(app|router)[.](get|post|put|delete|patch)[(]" knowledge-admin/backend --include='*.py'`；取其行數即總數。

---

---

## 🔗 相關資源

- **產線程式**：`services/agent/tools/registry.py`（工具註冊表，in-process 呼叫）、
  `services/agent/tools/jgb2.py`（六域 16 face）、`services/agent/tools/kb.py`（知識）、
  `services/jgb/transport.py`（jgb2 轉接：替身 15 端點／真 `external/v1`）
- **資料表**：`api_endpoints`（端點配置）、`usage_events`（每呼叫一列）、`api_keys`
- **測試**：`rag-orchestrator/tests/unit/agent/`、`tests/integration/agent/test_mcp_facade_req.py`

---

🔴 **2026-09-12：本檔刪掉 230 行。**
被刪的是「統一動態 API 執行引擎」那一整套索引——當前有效文檔表、按用途查找、
常見問題 Q1–Q4、推薦閱讀順序、完整性檢查表。它們把
`universal_api_handler.py`／`api_call_handler.py`／`chat.py`／`form_manager.py`
標成「✅ 最新／✅ 有效／完整性 95%」，而這四支已於 2026-09-11 刪除
（DSP-046）。**agentic-MCP 新線沒有「動態配置就能加 API」這個機制**——
加工具要寫程式（`ToolSpec` ＋ registry 註冊 ＋ strict schema）。
⛔ 不留退役標記，要看舊設計請 `git show HEAD:docs/api/README.md`。
