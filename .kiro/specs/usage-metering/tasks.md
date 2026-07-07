# 實作任務：usage-metering（AI 客服使用量計量與流量統計）

> 建立時間：2026-07-06
> 需求：requirements.md（R1–R8）｜設計：design.md（6 元件）｜落差：gap-analysis.md｜研究：research.md（5 項＋6 裁決）
> 標記：`(P)` = 可與同層其他 `(P)` 平行
> 鐵律：TDD（先紅後綠）；fire-and-forget——計量任何失敗不得影響回答（R1.3）；不存問題原文與回答全文（R7）；
> token 只計經 `chat_completion` 統一出口者（embedding 自建不計）；日界 Asia/Taipei；migration 冪等；
> 計量總開關 `USAGE_METERING_ENABLED` 關閉時系統行為與現狀完全一致（R8.2）；既有 chat 行為零回歸（R8.1）。

## 1. 事件表與歸集器底座

- [x] 1.1 (P) migration `add_usage_events.sql`（冪等）：design 元件 3 全欄位（request_id UUID UNIQUE 冪等鍵、date_tpe 台北日界、user_type、is_internal/internal_kind、token 三欄、est_cost_usd、model_breakdown jsonb）＋複合索引 `(date_tpe, vendor_id, is_internal)`＋session 索引；結尾 RAISE NOTICE 自檢。
  - 需求：1.1, 2.1, 7.1, 8.3
- [x] 1.2 (P) `services/usage_metering.py` 歸集器（TDD 先紅後綠）：UsageContext dataclass＋contextvar；`begin`（欄位收齊、內部流量判定 INTERNAL_RULES 表驅動、user_type 推導：target_user 有值用之／b2b＋無 role_id→prospect／internal／unknown、message_len 不存原文）；`add_llm_usage`（累計＋model_breakdown；無 context 靜默略過）；`set_path`；`finalize`（冪等 `_finalized` 防重、成本計算、`asyncio.create_task` 寫入、失敗僅 log）；`is_enabled` env 開關（關閉全鏈 no-op）。
  - 需求：1.1, 1.3, 1.4, 2.3, 3.1, 3.2, 8.2
- [x] 1.3 (P) 單價表：內建預設 dict（gpt-4o-mini/gpt-3.5-turbo/gpt-4o 等現用模型）＋env `LLM_PRICING_PATH` 外部 JSON 覆蓋；缺模型→token 記、成本 NULL 不臆造；單元含成本精算案與缺模型案。
  - 需求：2.4
- [x] 1.4 歸集器單元矩陣（先紅後綠）：token 合計＝各呼叫 usage 總和（R2.5 斷言）；內部判定表（backtest_ 前綴/disable_answer_synthesis/skip_sop/loop_/smoke 前綴/一般請求）；user_type 推導矩陣；finalize 冪等（雙呼叫單寫）；開關關閉 no-op；**個資負斷言**（事件 dict 不含 message 原文與 answer）。
  - 需求：1.4, 2.5, 3.1, 3.2, 7.1, 8.2

## 2. 掛線（1 完成後）

- [x] 2.1 middleware＋落點：app 掛 http middleware（路徑白名單 `/api/v1/message`，其餘零觸碰）——進場 `begin(request_fields)`、出場（含 except 路徑）`finalize(status, http_status)`；`llm_provider.chat_completion` 回傳前 `add_llm_usage`（±5 行）；`chat.py` 回應構建處 `set_path(processing_path, answer_source)`（非串流＋串流各一處）；串流 generator `finally: finalize(...)`（冪等使雙落點安全）。
  - 需求：1.1, 1.2, 1.5, 2.3
- [x] 2.2 整合測試（真 app／test client）：一次 /message 落恰一筆且欄位齊（vendor/mode/target_user/role_id/session/duration/token）；例外請求落 status='error' 事件；串流分支落一筆不重複；回測形狀請求（backtest_ 前綴）`is_internal=true`；非 /message 路徑零事件；開關關閉零事件。
  - 需求：1.1, 1.2, 3.1, 8.1, 8.2
- [x] 2.3 寫入延遲量測：同請求開/關計量各 N 次比對，主請求額外延遲中位數 < 5ms（integration 記錄數字於測試輸出，不設 flaky 硬斷言、超標回設計覆核）。
  - 需求：1.5

## 3. 統計 API（1.1 完成後可與 2 平行）

- [x] 3.1 (P) admin `app.py` 統計端點：`GET /api/usage/stats`（期間/vendor 多選/user_type/include_internal（預設 false）/granularity 日|月）→ groups＋totals（messages/sessions 去重/distinct_users/token 分列/est_cost/errors）；session 跨日歸屬首事件日（子查詢定 session 首日）；`GET /api/usage/export.csv`（UTF-8 BOM）；`Depends(get_current_user)`；參數非法/超保留期→400；不回傳任何 user_id 明細。
  - 需求：4.1, 4.2, 4.4, 5.1, 5.2, 5.3, 5.4, 6.3
- [x] 3.2 (P) 聚合正確性單元/整合：固定種子事件集斷言各量值（含跨日 session 歸屬案、零值日回零列、內部排除/含入切換）；重算冪等（同查詢重複執行同結果）；以迴圈流量為載荷 EXPLAIN 走索引（結果記 research 附錄，超標升級物化留掛帳）。
  - 需求：2.1, 2.2, 4.1, 4.2, 4.3, 4.4, 3.3

## 4. 後台報表頁（3.1 完成後）

- [x] 4.1 Vue 使用量報表 tab：期間（預設本月）/業者多選/user_type 分列/日‧月切換/內部流量開關（預設關）；業者排行＋日趨勢＋user_type 佔比；CSV 匯出鈕；掛既有後台導航（最小改動）；`npm run build` 驗證。
  - 需求：6.1, 6.2, 6.3, 6.4, 3.3

## 5. 稽核、治理與收案

- [x] 5.1 (P) `check_invariants.sh` 計量不變量：`is_internal=false` 而 session_id 帶已知內部前綴＝FAIL（漏標鐵證）；近 24h 非內部事件 vendor_id 缺失佔比 >5%＝WARN；照維護準則加豁免註解。
  - 需求：8.4
- [x] 5.2 (P) 治理配套：被遺忘權冪等 SQL（user_id/role_id 置 NULL、計數欄不動）＋內部流量回溯重標冪等 SQL 模板（按規則 UPDATE）＋保留期清理冪等 SQL（env `USAGE_RETENTION_MONTHS` 預設 18）——三者入 `scripts/usage/`（工具性 SQL，非 migration），排程化掛帳記 tasks 尾註。
  - 需求：3.4, 7.3, 7.4
- [x] 5.3 收案驗證：既有 unit 全綠＋既有 e2e 抽跑零回歸（R8.1）；真打一句業者問句→事件到位且 is_internal=false；跑一輪小迴圈→事件 internal_kind='backtest' 出現（R8.5 持續驗證）；`make audit` 全綠（含新不變量）；runbook 補 usage-metering 節（migration＋env 三項＋驗證步驟）。
  - 需求：8.1, 8.3, 8.5, 3.3

---
掛帳（不阻塞本 spec）：清理/重標 SQL 的排程化；彙總升級物化視圖（EXPLAIN 超標才做）；LINE 通路接入時的 channel 值；計費金額計算另案（以本 spec 彙總為輸入）。
