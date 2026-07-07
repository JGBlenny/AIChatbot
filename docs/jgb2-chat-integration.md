# jgb2 AI 客服串接規格（正式版：業者 b2b／租客 b2c／售前 prospect）

> 版本：v3（2026-07-07）　對象：jgb2 工程團隊
> v1 僅涵蓋租客端（b2c）；v2 整合三種身分形狀；v3 定案 **vendor_id 由 AI 側經 role_id 關聯解出，JGB 端一律不送**（見 §4、§8）。
> 業者端（b2b）為現役已上線串接（HelpSystem `useChat.ts`），本文件同時列出前端與 AI 側**待補齊項**（§8）。

> **一句話原則**：jgb2 端送出的身分只有 `role_id`（＋`user_id`）；`vendor_id` 是 AI 側用 `role_id` 關聯解出，jgb2 不管、不送。

## 1. 總覽：一支 API，三種身分形狀

所有入口都打同一支 API，差別只在請求的身分欄位；身分形狀決定回答資源池與資料隔離：

| 身分 | 誰在用 | 請求形狀（jgb2 送出） | 回答資源池 |
|---|---|---|---|
| **業者用戶**（b2b） | 管理公司員工（JGB 後台） | `mode=b2b`＋`target_user=property_manager`＋`role_id`＋`user_id` | 只走 JGB 系統知識（不走 SOP） |
| **租客**（b2c） | 業者的租客（租客端 widget） | `mode=b2c`＋`target_user=tenant`＋所屬業者 `role_id`＋`user_id` | 該業者 SOP＋租客知識，比分擇優 |
| **潛在客戶**（售前） | 未註冊的潛在業者 | `mode=b2b`＋`target_user=prospect`＋**不帶 role_id/user_id** | 售前顧問知識 |

> `vendor_id` 不在任何形狀的 jgb2 送出欄位內——AI 側以 `role_id` 關聯解出（見 §4、§8）。

## 2. 端點與通則

```
POST https://chatai.jgbsmart.com/rag-api/v1/message
Content-Type: application/json
X-API-Key: <發放之金鑰>          # 認證啟用（RAG_API_AUTH_ENFORCE）後必帶
```

- 非串流：`fetch`＋`response.json()`（與 b2b 現行相同）。
- 回應時間一般 3–15 秒；**建議 timeout 90s**＋loading 態。現役 b2b 端為 30s——多輪診斷／API 查詢題偶有超過，建議一併調升（§8）。
- 錯誤處理：非 2xx 顯示重試選項即可；額度攔截**不是**錯誤（HTTP 200，見 §5）。

## 3. 請求格式（逐形狀）

### 3.1 業者用戶（b2b）

```json
{
  "message": "使用者輸入的問題（1–2000 字）",
  "mode": "b2b",
  "target_user": "property_manager",
  "user_id": "<業者用戶的 JGB user id>",
  "role_id": "<該業者的 role id>",
  "session_id": "<對話識別，見 §6>"
}
```

> 不送 `vendor_id`；AI 側由 `role_id` 關聯解出（§8）。

### 3.2 租客（b2c）

```json
{
  "message": "使用者輸入的問題（1–2000 字）",
  "mode": "b2c",
  "target_user": "tenant",
  "user_id": "<租客的 JGB user id>",
  "role_id": "<該租客所屬業者的 role id>",
  "session_id": "<對話識別，見 §6>"
}
```

> 不送 `vendor_id`；AI 側由 `role_id` 關聯解出（§8）。`role_id` 是租客**所屬業者**的 role id，非租客自身角色。

### 3.3 潛在客戶（售前）

```json
{
  "message": "使用者輸入的問題（1–2000 字）",
  "mode": "b2b",
  "target_user": "prospect",
  "session_id": "<對話識別，見 §6>"
}
```

不帶 `role_id`／`user_id`（沒有身分可帶），也不帶 `vendor_id`（售前無所屬業者）。

## 4. 欄位語義（三形狀合併）

| 欄位 | 必要性 | 語義與後果 |
|---|---|---|
| `mode` | **必填** | `b2b`＝業者側資源池；`b2c`＝租客側（SOP＋租客知識）。**帶錯即受眾錯位**——租客帶成 b2b 會吃到業者知識庫 |
| `target_user` | **必填** | 知識受眾過濾：`property_manager`／`tenant`／`prospect`。漏帶時系統**只依 mode 推導**（`b2b`→`property_manager`；`b2c`→`tenant`）——**`prospect` 不會被自動推導**，售前務必明帶。統計正確性依賴它，三形狀都請明帶 |
| `vendor_id` | **jgb2 不送** | 由 AI 側以 `role_id` 關聯解出（真值來源＝AI 側 `vendors.settings.jgb_role_id`）。用途：①決定吃哪家業者的 SOP／參數／案場資料（跨業者嚴格隔離）②使用量計量與**月額度**歸屬。**jgb2 端不管、不帶**——解不出對應 vendor 屬 AI 側資料就緒問題（§8） |
| `user_id` | b2b/b2c **必填**；prospect 免 | ①個人資料查詢（我的帳單／合約／電表）的身分之一 ②per-user 使用統計 |
| `role_id` | b2b/b2c **必填**；prospect **禁帶** | jgb2 端唯一送出的業者身分錨點，一值兩用：①個資雙證（`role_id`＋`user_id` 缺一即降級「無法查個人資料」，一般問答不受影響）②AI 側據此關聯 vendor。b2b＝業者自己的 role id；b2c＝該租客**所屬業者**的 role id（同一值域） |
| `session_id` | **必填** | 同一場對話沿用同值——多輪對話、對話數統計、額度語義都依賴它（§6） |
| `message` | **必填** | 1–2000 字 |

## 5. 回應格式

```json
{
  "answer": "回答內容（Markdown）",
  "action_type": "direct_answer | form_fill | api_call | conversational | quota_blocked",
  "quick_replies": ["..."],
  "form_triggered": true,
  "form_completed": false,
  "progress": { "...": "..." },
  "session_id": "...",
  "source_count": 3
}
```

- **最小整合只需渲染 `answer`**（＋選配 `quick_replies`，建議渲染為可點按鈕——多輪識別的候選清單靠它體驗最好）。
- `form_triggered`／`form_completed`／`progress`：表單流程狀態，b2b 現役端已用於 UI 態（`isFormFilling`），可沿用。
- **多輪**：系統可能反問（「請問是哪一個物件？」「1. …2. …請回覆序號」）——widget 不需特殊處理，使用者直接回下一句（同 `session_id`）即可。
- **`action_type: "quota_blocked"`**：該 vendor 本月 AI 額度用盡，`answer` 為中性服務暫停文案（不含商業字眼），HTTP 仍為 200——照常渲染即可。

## 6. session_id 規則

- 格式自由，建議 `{身分}_{userId}_{隨機}`；**不得**以下列前綴開頭（系統內部流量標記，會被計量排除）：`backtest_`、`loop_`、`smoke_`、`verify_`、`probe_`、`demo_`、`dev_`、`fp_`、`reg_`。
- 同一場對話（使用者未關閉視窗）沿用同值；新開對話換新值。b2b 現役的 UUID 產生方式符合規則。

## 7. 身分與安全紅線（AI 系統側已內建，列出供知悉）

- 個資 API 雙證：缺 `role_id` 或 `user_id` 時個人資料查詢誠實降級，不會撈到別人資料。
- 跨業者隔離：SOP／參數／案場資料嚴格按 `vendor_id` 隔離（已實測）；`vendor_id` 由 AI 側經 `role_id` 關聯解出。
- 地址個資：物件相關回答只出顯示用地址，完整地址／經緯度不出口。
- 請求原文不落庫（計量僅記長度）。

## 8. 待補齊項

### 8.1 vendor_id 解析責任在 AI 側（本版定案）

定案：**jgb2 端不送 `vendor_id`**，一律只送 `role_id`；vendor 由 AI 側經 `role_id` 關聯解出。對照現行 AI 碼，尚有兩項待補：

| # | AI 側現況（`rag-orchestrator/routers/chat.py`） | 缺口 | 補齊 |
|---|---|---|---|
| A | `validate_vendor_id`（約 L3593）：`b2c` 未帶 `vendor_id` → 直接 422 | jgb2 b2c 只送 role_id 會被擋在驗證層 | 放寬 b2c 的 `vendor_id` 必填（改為可由 role_id 補全） |
| B | Step 0a 自動補全（約 L3782）只做 **`vendor_id`→`role_id`** 單向反查（`vendors.settings.jgb_role_id`） | 沒有 **`role_id`→`vendor_id`** 的反查，jgb2 只送 role_id 時 vendor 無從解出 → 隔離／計量／額度失去 vendor 掛點 | 新增 `role_id`→`vendor_id` 反查（`vendors.settings->>'jgb_role_id' = role_id`），並在缺對應時明確處置 |

> 前提：`vendors.settings.jgb_role_id` 需為各業者建妥且與 JGB role id 一致，否則同一 role_id 解不出唯一 vendor。此為 AI 側資料就緒工作。

### 8.2 b2b 現役前端待補齊（對照 `useChat.ts` 現況）

現役 b2b 串接可運作，但有兩項與本契約的落差，建議排入前端修版：

| # | 現況 | 影響 | 補齊 |
|---|---|---|---|
| 1 | 未帶 `target_user` | 系統依 mode 預設為 `property_manager`（`migrate_user_role` validator，約 L3550），目前結果正確；明帶可去除歧義並確保統計正確 | body 加 `"target_user": "property_manager"` |
| 2 | timeout 30s | 多輪診斷／真 API 查詢題偶爾超過 30s，使用者看到假性「回應逾時」 | 調升至 90s |

> `vendor_id` 已於 §8.1 定案由 AI 側解析，故不再列為前端待補。

## 9. 租客端上線前置（非 jgb2 工程，供排程參考）

**已知缺口（AI 系統側立案，2026-07-06 模擬驗收）**：「租客查自己的承租資料」（我這期帳單繳了沒／我的合約何時到期）的**租客視角進場配置未建置**——API 雙證與表單機制就緒，但既有帳務面向的問法錨點與 persona 皆為業者視角，租客自然問法目前落誠實 fallback；另「租客問平台操作」語料部分覆蓋（租客庫系統基準 52%，run 314）。兩缺口合併為「租客視角補全案」，租客端開放前需收案。

各業者資料就緒直接決定其租客的回答品質：①SOP 建置（vendor 1 目前為零）②通用參數真值核實（vendor 3 目前為佔位假值）③lookup 案場資料核實（vendor 2 客服類待重匯）。建議每業者過就緒清單後再對其租客開放入口。

## 10. 驗收案例（串接完成後煙囪）

| 形狀 | 問句 | 預期 |
|---|---|---|
| b2b | 「帳單為什麼發不出去」 | 進入多輪識別（要編號／物件名→候選→判定） |
| b2b | 只帶 `role_id`（不帶 vendor_id）打一次 | AI 側由 role_id 解出 vendor，使用量／額度正確歸屬該業者（§8.1 驗證） |
| b2c | 「你們客服電話幾號」 | 出**該業者**的專線（configs 值） |
| b2c | 「管理費包含什麼項目」 | 列該業者案場明細（lookup）或該業者 SOP |
| b2c | 「我這期帳單繳了沒」 | 進入識別／查詢流程（雙證齊才查得到） |
| b2c | 換一個 `role_id`（對應另一業者）問同樣問題 | AI 側解出不同 vendor，資料完全不同（隔離驗證） |
| b2c | 額度測試（該 vendor 設低額度） | `action_type=quota_blocked`＋中性文案 |
| prospect | 「你們系統怎麼收費」 | 售前口徑（不報價、引導聯繫），無個資查詢能力 |
