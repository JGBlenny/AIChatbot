# Product Steering

## 產品定位

**AIChatbot** 是一個基於 RAG (Retrieval-Augmented Generation) 技術的多業者 SaaS AI 客服知識庫系統，專注於租屋管理領域。

## 核心能力

### 1. 對話回合（現役：agentic-MCP 單線）
- **核心是 `AgentRuntime`**（`services/agent/runtime.py`），`/mcp` 只是它的門面之一
- **一回合四段**：程式段 → 九段脈絡注入 → 模型迴圈＋Verifier → 四道出口閘（順序即契約）
- **引用驗證**：`services/agent/verifier.py` 逐句驗引用，擋不住就走轉人固定句
- **知識兩條路**：路 A＝git canon 正本每回合自動注入（⛔ 不碰 `knowledge_base`）；
  路 B＝模型自己呼叫 `kb.search`／`kb.get`
- **向量語義搜尋**: 使用 pgvector；三軸過濾單一來源 `build_visibility_predicate`
- 🔴 **信心度評估與 LLM 答案合成的執行路徑已刪**（2026-09-11 DSP-046），⛔ 別依它們設計新東西。⚠️ 但名為 `disable_answer_synthesis` 的**旗標名**仍殘留：`services/usage_metering.py` 的 `INTERNAL_RULES` 用它當「回測流量」判準之一，`services/agent/shadow.py` 影子請求會帶它——只是標記，不代表有合成功能在跑

### 2. 知識管理系統
- **多元知識來源**:
  - SOP 知識 (vendor_sop_items, vendor_sop_categories, vendor_sop_groups)
  - 通用知識 (knowledge_base)
  - 測試場景 (test_scenarios)
- **知識分類**:
  - `sop_knowledge`: 操作性 SOP 知識
  - `form_fill`: 表單填寫知識
  - `system_config`: 系統配置知識
- **目標用戶隔離**: 支援租客 (tenant)、房東 (landlord)、物業經理 (property_manager)、系統管理員 (system_admin) 角色隔離
- **業態類型過濾**: 支援不同業態 (rental_housing, commercial, etc.) 的知識過濾

### 3. 知識完善迴圈 (Knowledge Completion Loop)
**自動化知識缺口發現與補救流程**:

🔴 **執行面已於 2026-09-11 刪除**：協調器、缺口分析、AI 分類、聚類、知識生成器等
整批不存在，`services/knowledge_completion_loop/` 程式只剩 `embedding_client.py`（另有 `__init__.py`、`create_missing_indexes.sql`）。
**後台頁面與資料表仍在**（`routers/loops.py`、`routers/loop_knowledge.py`），
可以看歷史迴圈、做人工審核，但**沒有任何程式會跑新一輪**。

現行的檢索改善走 `.claude/skills/retrieval-improvement-loop/`（打 `/mcp`，不走這條迴圈）。

### 4. SOP 資料維護（⛔ 對話路徑零讀取）
🔴 **編排器、觸發器、表單狀態機已於 2026-09-11 刪除。**
`vendor_sop_items` 等資料表、後台 CRUD（`routers/platform_sop.py` 15 條路由）、
存檔時的 embedding 計算（`sop_embedding_generator.py`）都還在真的運作——
**但沒有任何對話程式會查它**。維護 SOP 不會改變機器人的回答。

### 5. 測試與驗證
- **測試場景管理** (`test_scenarios`):
  - 來源追蹤: manual, user_question, auto_generated, imported
  - 難度分級: easy, medium, hard
  - 狀態管理: pending_review, approved, rejected, draft
- **批量回測**: 支援批次執行、狀態過濾、限制條數
- **覆蓋率分析**: 多維度測試覆蓋率分析（來源、難度、主題關鍵字）

### 6. 多業者 SaaS 架構
- **業者隔離**: 資料庫層級的 vendor_id 隔離
- **業者配置** (`vendor_configs`): 動態配置系統行為、類別、業態類型
- **審核中心**: 集中管理未釐清問題、待審核知識、測試場景審核

## 價值主張

1. **知識缺口發現**: 原由知識完善迴圈自動執行，**執行面已於 2026-09-11 刪除**（見上 §3）；現行改由 `retrieval-improvement-loop` skill 與回測人工驅動
2. **持續改善**: 迭代式測試與知識補充，持續提升回答準確率
3. **多業者擴展**: SaaS 架構支援快速增加新業者，知識互不干擾
4. **角色隔離**: 確保不同角色（租客、房東、物業）看到適合的知識
5. **透明可控**: 所有 AI 生成內容需人工審核，確保品質與合規性

## 使用場景

### 主要場景
- **租客諮詢**: 租金繳納、裝潢規範、緊急報修、稅務保險
- **房東管理**: 合約管理、租金催收、設施維護、糾紛處理
- **物業運營**: SOP 流程執行、表單填寫、系統配置查詢

### 擴展場景
- **AI 輔助測試題生成**: 使用 OpenAI GPT-4o 批量生成多樣化測試題
- **知識匯入匯出**: 支援 Excel、CSV、JSON 格式的知識批量管理
- **視頻知識**: 支援 S3 儲存的視頻知識檢索與播放
- **文檔轉換**: 支援文檔格式轉換與知識抽取

## 產品原則

1. **測試驅動知識完善**: 所有知識缺口應先有測試案例，再補充知識
2. **人工審核為王**: AI 生成內容僅輔助，最終決策權在人工審核
3. **多元來源整合**: 支援手動錄入、用戶問題提取、AI 自動生成等多元知識來源
4. **持續監控改善**: 透過回測與覆蓋率分析，持續監控系統表現
5. **成本可控**: 追蹤 AI API 成本，支援批量大小、限流控制

---

## 2026-07 現況增補（本節為最新，與上文衝突時以本節與 `docs/architecture/SYSTEM_ARCHITECTURE.md` 為準（`docs/architecture-overview.md` 現為指路檔））

- **對話面向體系（🔴 2026-09-12 更正）**：**16 個 face、六域**（bills 5、contracts 5、accounts 2、repairs 2、iot 1、estates 1）（帳單／合約／修繕／電表／帳號／物件），在註冊時由 `_jgb2_spec(domain, sorted(builders.keys()))` **現算**，⛔ 不是資料驅動、⛔ 不是 21＋。新增 face key **不等於**新增能力：face 只選 builder，資料來源硬編在 `query_<域>`。機械判定用 `services/jgb/*_FACE_BUILDERS`，LLM 只照 facts 組話。
- **資料體系分工（定案）**：`vendor_configs`＝通用單值參數（{{param}} 模板）；`lookup_tables`＝案場級（Excel 匯入＋錨點）；SOP＝b2c 專用（b2b 不走）；jgb API＝個資（role_id+user_id 雙證）。
- **計量與額度**：usage_events 每請求計量（token/成本/內部流量標記）；vendor_quotas 月額度（達限攔截/警示寄信）。
- **品質三層**：unit（make test-unit）／系統回測（迴圈＋多輪模擬＋v3 評審＋金標，按受眾分庫）／不變量稽核（make audit，修一類 bug＝加一條）。驗收鐵則：改引擎行為以系統路徑實跑收案。
- **單一真相源**：`docs/architecture/SYSTEM_ARCHITECTURE.md`（全景）＋ `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §2b（一回合完整流程）；部署走 `docs/deployment-runbook.md`。⚠️ `docs/architecture-overview.md` 已改為指路檔。
