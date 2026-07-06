# Research：usage-metering

> 產出：2026-07-06　方法：codebase／jgb2 原始碼實查　所有結論附出處

## 摘要

輕量 discovery（Extension 型功能）：五個 research 項全數定案，六個開放問題全數裁決。最重要發現：**jgb2 生產端只用非串流的 `/rag-api/v1/message`**，SSE 事件落點從「核心風險」降為「次要路徑的一致性處理」。

## Research Log

### 1. jgb2 實際呼叫面（計量範圍定案）
- `jgb2/src/components/HelpSystem/composables/useChat.ts:10`：`CHATBOT_API_URL = 'https://chatai.jgbsmart.com/rag-api/v1/message'`——唯一入口。
- `:55-71`：`fetch` POST＋`response.json()`——**非串流**；body 帶 `message/mode:'b2b'/session_id/user_id/role_id`（user_id 生產有帶 ✓）。
- **定案**：計量範圍＝`/api/v1/message`（含其 stream 分支以防未來啟用）；legacy `/chat` 不計（無生產呼叫者）。

### 2. LLM token 歸集點
- `services/llm_provider.py:107-110,159-161`：`chat_completion` 回傳已含 `usage`。
- rag-orchestrator services/routers **無任何直接 `OpenAI()`**（grep 實證）——統一出口成立。
- 對話引擎經 `llm_answer_optimizer` → `chat_completion`（conversational_engine.py:413/509/527）✓。
- embedding 呼叫走自建 embedding-api（本地模型，零邊際成本）——**不計 token**，僅計 OpenAI 系呼叫。

### 3. 串流路徑（次要，仍要蓋）
- `chat.py`：串流有多個包裝器（`stream_response_wrapper:1129`、`stream_synthesis_response:1222`、`generate_answer_stream:1401`）；`StreamingResponse` 在 middleware return 後才實際吐流。
- **定案**：contextvar 歸集＋**雙落點單寫入**——非串流：middleware 出場寫；串流：generator `finally` 寫。同一 `finalize()`，以 request 級 uuid 冪等（重覆呼叫只寫一次）。

### 4. 彙總策略
- 量級：真人流量低頻（jgb2 站內客服）；機器流量大但 `is_internal` 隔離。
- **定案**：查詢時聚合＋複合索引 `(date_tpe, vendor_id, is_internal)` 起步；tasks 內含以迴圈流量為載荷的 EXPLAIN 驗證項；超標升級物化視圖（介面不變）。

### 5. 開放問題裁決

| # | 問題 | 裁決 | 理由 |
|---|---|---|---|
| 1 | 問題原文 | **不存原文**——只存 `message_len`＋分類特徵（processing_path/intent） | 個資最小化；內容分析已有 unclear_questions 管道 |
| 2 | 彙總實作 | 查詢時聚合（見 §4） | 量級不需要物化 |
| 3 | 模型單價表 | JSON 設定檔（env `LLM_PRICING_PATH` 指路徑，內建預設表）；缺模型→記 token、成本留空 | 改價=改檔重啟，無 UI 維護成本；升級 DB 表留待計費 spec |
| 4 | per-user 明細 | ~~不提供~~ → **提供**（2026-07-06 使用者改判）：/api/usage/users Top N＋頁面使用者明細卡；user_id＝JGB 系統編號（jgb2 必帶），非個資姓名 | 營運要看單一使用者用量；認證保護＋遺忘權 SQL 不變 |
| 5 | 事件保留期 | 預設 18 個月（env 可調）；提供冪等清理 SQL，自動排程掛帳 | 計費爭議舉證週期 |
| 6 | 通路值域 | `channel` text，預設 `'web'`（LINE 等未來直接新值） | 零 schema 變更擴充 |
| ＋ | 日界時區 | **Asia/Taipei**（落 `date_tpe` 欄，寫入時計算） | 與營運/計費口徑一致，避免查詢時轉換成本 |
| ＋ | user_type 推導 | 寫入時定案存欄：target_user 有值用之；b2b＋無 role_id→prospect；內部→internal；其餘 unknown | 推導規則單元可測，查詢不用重推 |

## 風險與緩解

1. **fire-and-forget 背壓**：`asyncio.create_task`＋佇列上限（滿→丟棄記 log；寧漏勿堵，R1.3）。
2. **middleware 對非 /message 路徑的干擾**：以路徑白名單掛載，其餘請求零觸碰。
3. **迴圈寫入量**：內部流量單日可達數千筆——索引含 is_internal，報表查詢天然跳過。
```
