# line-bot-platform 工作清單：LINE OA「JGB 房東管家」demo 接 AIChatbot `/mcp`（2026-09-08）

> 給 line-bot 團隊的一頁交辦。契約細節與證據在 `mcp-client-contract-line-bot-20260907.md`（形狀以本檔為準，該檔 §4 前置已全部就緒）。demo 範圍＝**文字對話＋查詢（帳單／合約／物件／電錶／修繕）＋寫入（延到期日、開修繕單，經確認卡）**；語音（W7）另排、⛔ 本輪不做。AIChatbot 後端整場跑替身資料（真 id、真名稱、已遮罩），⛔ 不打 JGB 正式站。

## 0. 一張圖

```
LINE 使用者 ──文字──▶ line-bot webhook
                        │ 依綁定推出 role_id／user_id／vendor_id（⛔ 不信前端）
                        │ session_id = HMAC(secret, lineUserId)[:32]
                        ▼
                POST https://<demo-host>/mcp   (MCP streamable HTTP, tools/call agent.turn)
                headers: X-API-Key, X-JGB-Identity(JSON)
                        ▼
                {answer, kind, handoff, quick_replies, trace_id}
                        │ answer→泡泡；quick_replies→按鈕；handoff≠null→固定轉人句＋真人入口
                        ▼
              使用者按按鈕 ──▶ 把按鈕 value **原字串**當下一則 message 送回（確認流程靠這個）
```

## 1. 要做的事（B1–B6）

| # | 事 | 規格 | 驗收 |
|---|---|---|---|
| **B1** MCP client | MCP SDK streamable HTTP 連 `POST /mcp`；每個 LINE 使用者一條 session（`initialize` 一次，之後 `tools/call`）；⛔ 不要每則訊息重新 initialize（每回合多 1 次往返） | `tools/list` 看得到 `agent.turn`（含 `jgb2.query.*` 不必理會，那是模型用的） |
| **B2** 身分與 session | `X-JGB-Identity`：`{"mode":"b2b","target_user":"property_manager","vendor_id":<int>,"role_id":"<str>","user_id":"<str>","session_id":"<假名>"}`；`session_id`＝`HMAC(secret, lineUserId)` 的穩定假名（⛔ 不放 LINE userId）；`role_id`／`user_id` 由綁定推出 | 缺 vendor_id／session_id ⇒ 400 `IDENTITY_*`（設定錯，不是使用者錯） |
| **B3** 渲染 | `answer` → 文字泡泡（可多段，保留換行）；`quick_replies[]` → LINE quick reply 按鈕，`label` 顯示、`value` 送回；`handoff` 非 null → 固定句「這題我幫您轉專人」＋真人入口（⛔ 不顯示 `handoff_reason`）；`kind` 只作記錄 | 六條劇本（§3）畫面正確 |
| **B4** 確認流程（寫入） | 模型回確認卡時 `quick_replies` 固定三顆：`{"label":"✅ 確認送出","value":"confirm_submit:<16hex>"}`、`✏️ 我要修改/confirm_edit:<16hex>`、`❌ 取消/confirm_cancel:<16hex>`（label 含 emoji 前綴，照顯示）；使用者按下 ⇒ **把 value 原字串當 message 送回**（⛔ 不改寫、不加字、不用 label）；使用者若改打字（「好」「送出」）⇒ 照一般文字送，服務端不會當確認（會回提示用按鈕） | 延 3 天／開單兩條正向：按「確認送出」後回答含新到期日／單號；按「取消」不寫 |
| **B5** 逾時與錯誤 | 呼叫端逾時 **≥60 s**；等待期間送 LINE typing／loading 指示；`ok=false` 依契約 §3 碼對照（`RATE_LIMITED`／`TOOL_TIMEOUT` ⇒「稍後再試」；`NO_MATCH`／`AGENT_UNAVAILABLE` ⇒ 服務端未就緒、記 log）；逾時後同一 session 可重送同一句 | 人工拔線測一次 |
| **B6** 日誌與個資 | ⛔ 不記整包回應（`answer` 含租客資料）；只記 `trace_id`、狀態碼、耗時；`session_id` 假名；金鑰只在 line-bot 伺服器環境變數 | code review |

## 2. 你們會拿到什麼

| 項 | 何時 | 誰 |
|---|---|---|
| demo 主機 URL（`/mcp`）與 `vendor_id` | AIChatbot 部署後 | AIChatbot |
| `X-API-Key`（`is_internal`、綁 vendor） | 業主親發（手工 SQL） | 業主 |
| demo 資料表（真 id／真物件名／可演的帳單、合約、電錶、修繕單） | 替身換真資料後另附一頁 | AIChatbot |
| 本檔＋契約 | 現在 | — |

## 3. 六條驗收劇本（你們端自測，資料 id 以 §2 資料表為準）

| # | 使用者說 | 期望畫面 |
|---|---|---|
| 1 | 「<某戶> 這個月房租繳了沒」 | 泡泡：狀態＋金額＋到期日 |
| 2 | 「<某戶> 合約什麼時候到期」 | 泡泡：到期日＋剩幾天 |
| 3 | 「<某戶> 電錶餘額剩多少」 | 泡泡：餘額 |
| 4 | 「<某戶> 有沒有修繕單在處理」 | 泡泡：單號／狀態 |
| 5 | 「<帳單> 逾期了，幫我延 3 天」→ 按「確認送出」→「<帳單> 到期哪天」 | 確認卡＋三顆按鈕 → 「已延至 …」 → 讀到新日期 |
| 6 | 「<某戶> 熱水器壞了，直接幫我開單」→ 按「取消」 | 確認卡 → 「這筆操作沒有送出」 |
| 反向 | 「租客的電話給我」 | 固定轉人句（不得出現電話） |

## 4. 不在本輪

語音訊息（`audio_urls`／`transcript`，W7）、LIFF 線③④⑤（拍照開單／催繳／清單追問的 REST 面向）、任何寫入 JGB 正式站。

## 5. 常見坑（我們踩過的）

- 多 worker 會「Session not found」：demo 主機單 worker 或 sticky。
- 服務端一回合 8–20 秒（含改寫可到 30 秒）：沒有 typing 指示會像當機。
- 按鈕 value 帶 `pending_id`，同一張卡的三顆 value 不同；重送同一顆「確認送出」會得到同一結果、不會寫兩次。
