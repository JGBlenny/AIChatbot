# Gap 分析：usage-metering

> 產出：2026-07-06　方法：codebase 實查（grep/讀碼＋DB 實測）　對應 requirements.md R1–R8

## 一、現況資產（比預期好的部分）

| 資產 | 現況 | 對需求的意義 |
|---|---|---|
| **LLM 統一出口** | `services/llm_provider.chat_completion` 是唯一出口——rag-orchestrator 的 services/routers **零繞道**（無直接 `OpenAI()`；唯一例外在 scripts/backtest，屬內部流量本就不計） | R2.3 token 累計只需在**一個函式**裝鉤，不用逐呼叫點改 |
| **usage 已回傳** | `chat_completion` 回傳值已含 `usage.prompt_tokens/completion_tokens/total_tokens`（llm_provider.py:107-110、159-161） | token 原料現成，缺的只是「按請求歸集」 |
| **身分維度齊全** | `VendorChatRequest`（chat.py:3468）已有 vendor_id/mode/target_user/role_id/user_id/session_id | R1 維度不需要改任何請求契約 |
| **內部流量訊號多重** | session 前綴（`backtest_`）＋回測專用旗標 `disable_answer_synthesis`/`skip_sop` 皆在請求上 | R3 識別規則有兩層訊號可用，不只靠前綴 |
| **async DB pool** | `req.app.state.db_pool`（asyncpg），loops.py 已示範用法 | R1.3 fire-and-forget＝`asyncio.create_task`＋pool，無新依賴 |
| **admin API/頁面慣例** | app.py（psycopg2＋`Depends(get_current_user)`）＋Vue tab 體系（BacktestView 剛整修過） | R5/R6 全走既有模式 |
| **稽核掛點** | `make audit` 體系現成，維護準則已定 | R8.4 加條目即可 |

## 二、缺口（要從零建的）

1. **使用事件表**：`conversation_logs` 為空表（0 筆）且 schema 完全不合（無 vendor/mode/target_user/role_id/session_id/token 欄），**建議棄用不改造**——新表 `usage_events`，舊表不動（feedback 端點仍讀它，零風險）。
2. **請求級歸集機制**：token 產生在 `chat_completion`（呼叫棧深處），事件落在請求層——中間沒有任何「本請求」的載體。這是**本 spec 唯一的架構決策點**（見第三節）。
3. **回應出口多**：`/message` 一條路徑有 5+ 個 return（直答/表單/面向/串流/錯誤）——逐出口插記錄必漏。
4. **彙總與報表**：全新，無前例可循的只有「日 rollup 策略」；API/頁面照 backtest 模式抄。
5. **模型單價表**：全新設定資料。

## 三、方案評估（請求級歸集 × 寫入點）

### 方案 A：FastAPI middleware ＋ contextvar 歸集（建議）
- middleware 包住 `/message`：進場建 request 上下文（contextvar），出場（含例外）落事件——**天然覆蓋所有 return 出口與 5xx**（R1.1/R1.2）。
- `chat_completion` 尾端把 usage 累加進 contextvar；串流路徑同（生成器結束時 flush）。
- 業務欄位（processing_path/回應來源）由 chat 流程寫入同一 contextvar（一行 set，不重構出口）。
- 優點：單一 choke point、出口零遺漏、chat.py 侵入極小。風險：串流回應的「完成時點」要在 generator 收尾處理（StreamingResponse 在 middleware return 後才實際吐流）——**設計階段需定案串流事件的落點**〔research 項 1〕。

### 方案 B：逐出口插記錄
- 在 5+ 個 return 前各插一次寫入。
- 優點：直觀。缺點：出口會繼續增加（歷史證明），漏一個＝漏帳；例外路徑蓋不到。**不建議**。

### 方案 C：Nginx/存取日誌事後解析
- 從 web 層日誌抽流量。
- 優點：零程式侵入。缺點：拿不到 token/processing_path/身分細節（POST body），與 R1/R2 不相容。**不建議**（可作為對帳側援）。

### 彙總策略（R4.3）
- 真人流量低頻（單 vendor 日均訊息量預估 <1k），機器流量大但被 `is_internal` 隔離——**查詢時聚合＋事件表索引**（date, vendor_id, is_internal）即可起步；量大再升級物化。設計以 EXPLAIN 實測定案。

## 四、風險與注意

1. **串流路徑的事件完整性**（方案 A 的 research 項）——token 在流結束才齊。
2. **asyncpg pool 壓力**：fire-and-forget task 洪峰時的背壓——需上限或丟棄策略（丟棄記 log，寧漏一筆不拖垮服務，R1.3）。
3. **legacy `/chat` 端點**：另一組舊端點仍存在；生產入口是 `/message`——範圍定案：只計 `/message` 系（設計確認 jgb2 實際打的路徑清單）。
4. **時區**：日粒度歸屬用台北時區還是 UTC——計費爭議點，設計定案〔建議台北，與營運口徑一致〕。
5. **既有 e2e 速度**：計量開啟後跑回測會多寫 N 筆事件——正好是 R8.5 的持續驗證，但索引要撐住迴圈寫入量。

## 五、設計階段 research 清單

1. 串流（SSE）路徑的事件落點與 token 歸集時機（方案 A 核心）。
2. jgb2 前台實際呼叫的端點清單（`/message` 之外有沒有）——決定計量範圍。
3. 事件表索引組合與查詢時聚合的 EXPLAIN 實測（用迴圈流量當測試載荷）。
4. 模型單價表形式（env/設定檔/DB 表）與維護動線。
5. 開放問題 6 條（requirements.md 尾）逐一定案。

## 六、建議實作策略

**extend 為主、新建為輔**：新建 `usage_events` 表＋`services/usage_metering.py`（contextvar 歸集器＋寫入器）；extend `llm_provider`（±5 行）、`chat.py`（middleware 掛載＋path 標記數行）、admin app.py（統計端點）、Vue（報表 tab）、`check_invariants.sh`（計量不變量）。預估規模與帳單診斷案相當（migration 1＋新服務檔 1＋既有檔小改 4＋測試 3 檔）。
