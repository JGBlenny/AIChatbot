# 對話式回答 API 串接指南（售前顧問）

> 給外部專案串接 JGB 售前對話(conversational)。功能說明見
> [`docs/features/conversational-presales.md`](../features/conversational-presales.md)。

## 端點

`POST {BASE}/v1/message`，`Content-Type: application/json`，**無需驗證 token**。

**BASE 三種**（依你的專案如何連到這台服務）：

| 連法 | URL | 說明 |
|---|---|---|
| 直連 rag-orchestrator | `http://<host>:8100/api/v1/message` | 同 VPC / 內網最直接 |
| 經 nginx（web :80） | `http://<host>/rag-api/v1/message` | nginx 把 `/rag-api/` 改寫成 `/api/` |
| CloudFront | ❌ 不可（CloudFront 只服務 S3 靜態前端，未代理 `/rag-api/`） | 不要用 |

> 服務在 bastion 後、EC2 無 public IP；**對外入口（ALB/域名）請向基礎設施確認**。合約與位址無關。

## Request（售前對話）

```json
{
  "message": "使用者訊息",          // 必填
  "mode": "b2b",                    // 售前固定
  "target_user": "prospect",        // 售前固定（走對話引擎的關鍵）
  "session_id": "整段對話固定的ID",  // 必給且穩定 ← 多輪狀態靠它
  "user_id": "選填",
  "stream": false,                  // true = SSE 逐字串流
  "trigger_facet_key": null         // 選填：直達對話面向（見下）
  // vendor_id：售前不要帶
}
```

| 欄位 | 必填 | 說明 |
|---|---|---|
| `message` | ✅ | 使用者訊息（1–2000 字） |
| `mode` | ✅ | 售前固定 `"b2b"` |
| `target_user` | ✅ | 售前固定 `"prospect"` |
| `session_id` | ✅（多輪必須） | **整段對話用同一個**；後端據此保存已收集情境/已推薦狀態 |
| `stream` | — | `true` 走 SSE 逐字串流；預設 `false` |
| `user_id` | — | 選填追蹤用 |
| `trigger_facet_key` | — | **直達對話面向鍵**（如 `"repair_create"`）：命中面向 registry 且 enabled → 跳過意圖辨識直接進該面向；**未命中則忽略、照常走既有管線（防呆，不報錯）**。交易面向（如修繕）另需 b2c 身份與 gate 通過（見 [`facet-architecture.md` §七](../architecture/facet-architecture.md)） |

## Response A — 非串流（`stream:false`）

JSON（`VendorChatResponse`，重點欄位）：

```json
{
  "answer": "回覆文字（可能含 • 條列、markdown 連結 [標籤](網址)、\\n 換行）",
  "intent_type": "conversational",   // 對話中；導到表單時為 "form_filling"
  "session_id": "...",
  "form_triggered": false,           // 導到 CTA 表單時 true
  "form_id": null,                   // 表單 id（如 trial_form / demo_form）
  "current_field": null,             // 表單下一欄提示
  "quick_replies": null,             // 選項（若有）；交易面向確認 gate 為三顆固定鈕（見下）
  "handoff": null,                   // 轉人訊號（售前，2026-09-04 起）；null＝不需轉人（見下）
  "confidence": 1.0,
  "mode": "b2b",
  "timestamp": "..."
}
```

> `answer` 內含 **markdown**（換行/`•` 條列/`[標籤](網址)` 連結），顯示端請用 **markdown 渲染**（連結才會變可點按；純 `pre-wrap` 會顯示原始 `[]()` 文字）。

### `handoff`——售前無知識佐證時的轉人訊號（presales-grounding-gate）

<!-- tested-by: presales-grounding-gate:4.1 -->

```json
"handoff": {
  "reason": "sensitive_no_grounding",   // no_grounding | sensitive_no_grounding | llm_mentioned_handoff | partial_grounding
  "fact_class": "customer_reference",   // customer_reference | pricing | contract_sla | compliance | security | feature | other
  "channel": "line_official",           // 真人入口識別（對齊 jgb2 切片 2 LINE 官方帳號；可由設定覆寫）
  "message": "這題我這邊沒有可靠資料，幫您轉專人——點下方的『找真人』。"   // 與 answer 同句（固定文案）
}
```

- **出現條件**：⓪ `partial_grounding`：事實題有知識、但使用者一次問多個項目（如房東／租客／合約／帳單）而知識只涵蓋一部分 ⇒ `answer`＝知識原文＋固定尾句「以上是我有資料的部分；沒提到的項目我這邊沒有資料，可點下方『找真人』。」（D6 抽取式，env `PRESALES_EXTRACTIVE` 開時才出現；**目前預設關**，事實題由 LLM 依知識合成，此 reason 不會出現）。① prospect 事實題（brain `converge_kind=answer`）在知識庫**查無過門檻的知識** ⇒ `answer` 為固定句、`reason=no_grounding`；屬客戶名單／報價／合約 SLA／法遵／資安五類時 `reason=sensitive_no_grounding`。② 無 `session_id` 的 prospect 零命中 ⇒ 同固定句，`fact_class=other`。③ 有知識、回覆文字含「專人／真人／客服／沒有資料」⇒ `reason=llm_mentioned_handoff`（只加訊號，文字不變；**知識原文自帶「專人」的抽取式回覆也算**，如「可預約 demo 由專人帶您看」）。
- **前端預期行為**：`handoff` 非 null ⇒ 在該則回覆下方畫「找真人」入口（依 `channel`）。`reason` 為 `no_grounding`／`sensitive_no_grounding` 時 `message` 已在 `answer` 內，⛔ 不要重複顯示；`llm_mentioned_handoff` 時 `answer` 是 LLM 自己的回答、`message` 是一句入口提示（「需要真人協助可點下方的『找真人』。」），可當按鈕旁說明。
- **相容**：可選欄位；未升級的前端忽略即可，行為不變（只是看不到按鈕，使用者會讀到「點下方的『找真人』」卻沒有按鈕——上線時間請與 jgb2 切片 2 對齊）。
- ⛔ 不要用 `answer` 文字是否含「專人」判斷要不要畫按鈕——那是本欄位存在的理由。

### `quick_replies`——交易面向確認 gate（conversational-repair）

<!-- tested-by: conversational-repair:4.1 -->

交易面向（如修繕）收齊必填槽位後，回覆會帶**確認摘要＋三顆固定 quick reply**；使用者送出前必須明確同意（**收齊≠送出**）。每顆的 `value` 為**穩定機器值**（顯示文字可由業者配置覆寫，機器值不變），前端應以 `value` 回傳判定：

| `value`（機器值） | 語義 | 引擎行為 |
|---|---|---|
| `confirm_submit` | 確認送出 | 引擎層決定性判定同意 → 執行寫入（建單），回回執＋單號 |
| `confirm_edit` | 修改 | 帶否定語境重出確認（槽位保留、局部更新，不重跑流程） |
| `confirm_cancel` | 取消 | 結束面向、丟棄槽位、不留殘單 |

> 同意判定在**引擎層（決定性）**，非 LLM——除按鈕機器值外，明確同意詞（好/確認/送出/OK）亦觸發送出；模糊語則不送出。`executed` 後重複同意**冪等**、不重複建單。

## Response B — 串流（`stream:true`）

<!-- tested-by: testing-traceability:5.5 -->

`Content-Type: text/event-stream`，事件序：

```
event: start
data: {"cached": false, "message": "開始輸出答案..."}

event: intent
data: {"intent_type": "conversational", "intent_name": "售前對話", "confidence": 1.0}

event: answer_chunk
data: {"chunk": "逐"}
event: answer_chunk
data: {"chunk": "字"}
...（多個）

event: metadata
data: {"intent_type": "conversational", "action_type": "conversational", "cache_hit": false}
       // 有轉人訊號時多一鍵："handoff": {...}（形狀同 Response A；無則鍵不出現）；交易確認時多 "quick_replies"

event: done
data: {"success": true, "message": "答案生成完成"}
```

**解析**：把所有 `answer_chunk` 的 `chunk` 依序串接 = 完整答案。`handoff`／`quick_replies` 在 **metadata** 事件裡，⛔ 不在 chunk 裡；轉人固定句本身仍以 `answer_chunk` 送出（整句一次）。

## 多輪對話規則

- **同一段對話用同一個 `session_id`** → 後端自動記狀態（已收集情境、已推薦），逐步反問再收斂。
- **結束**：使用者送「取消」。
- **新對話**：換新的 `session_id`。

## 售前對話行為（prospect）

<!-- tested-by: testing-traceability:5.2 -->

- 模糊需求 → 顧問式反問（一次一題：身分/規模/痛點…）
- 事實題（競品/價格/某功能）→ 直接答
- 了解夠 → 個人化推薦 ＋ 預約連結 `[立即預約 demo](https://www.jgbsmart.com/demo-form)`
- 合規：不報價（導 `[查看方案與費用](https://www.jgbsmart.com/pricing)`）、IoT 被問才提、競品中立；連結一律 markdown、禁止裸網址

## 範例

非串流：
```bash
curl -X POST {BASE}/v1/message -H 'Content-Type: application/json' -d '{
  "mode":"b2b","target_user":"prospect","session_id":"conv-abc-001",
  "message":"想了解適不適合我用"}'
```

串流（逐字）：
```bash
curl -N -X POST {BASE}/v1/message -H 'Content-Type: application/json' -d '{
  "mode":"b2b","target_user":"prospect","session_id":"conv-abc-001",
  "message":"我是個人房東有20間","stream":true}'
```

多輪（同一 session_id 連續送）：
```
1) {"...","session_id":"conv-abc-001","message":"想了解適不適合我用"}   → 反問身分
2) {"...","session_id":"conv-abc-001","message":"個人房東，20間"}        → 反問痛點
3) {"...","session_id":"conv-abc-001","message":"收租對帳很亂"}          → 收斂推薦 + demo 連結
```

## 交易面向範例——修繕報修（conversational-repair，b2c 租客）

<!-- tested-by: conversational-repair:1.1 -->

> 交易面向為 **b2c 租客**情境（`mode:"b2c"`＋`target_user:"tenant"`＋`vendor_id`＋`user_id`＋`role_id`，雙證身份），與售前 prospect 不同。可經 `trigger_facet_key:"repair_create"` 直達，或以報修語句/損傷照片自然進場。收齊必填槽位後過**確認 gate**（三顆 quick reply）才建單。

情境 A（≤3 輪建單）：

```
1) 進場（可帶直達鍵與照片）
   {"mode":"b2c","target_user":"tenant","vendor_id":2,"user_id":"u123","role_id":"r1",
    "session_id":"repair-abc-001","message":"冷氣壞了",
    "image_urls":["https://.../damage.jpg"],"trigger_facet_key":"repair_create"}
   → 系統帶入物件（租約預填）＋照片辨識分類，僅問推不出的急迫性：
     「幫您報修 XX 路 5 樓的冷氣——照片看起來是不製冷，發生多久了？急嗎？」

2) 補槽＋岔題（同一 session_id）
   {"...","session_id":"repair-abc-001","message":"昨天開始，蠻急的，這要自己出錢嗎"}
   → 先答費用政策（岔題即答），再出確認摘要＋三顆 quick_replies：
     answer: "牆內管線與設備由業者負責…\n確認送出：XX路5F／冷氣不製冷／昨天起／緊急——送出嗎？"
     quick_replies: [
       {"value":"confirm_submit","label":"確認送出"},
       {"value":"confirm_edit","label":"修改"},
       {"value":"confirm_cancel","label":"取消"}
     ]

3) 確認送出（回傳按鈕機器值或明確同意詞）
   {"...","session_id":"repair-abc-001","message":"confirm_submit"}
   → 建單並回執：「已建單 #R2071，之後隨時問『修得怎樣』可查進度。」
```

> 確認前修改（`confirm_edit` 或「不是客廳是臥室的」）→ 更新後重出確認、不重跑流程；取消（`confirm_cancel`/「不報了」）→ 不留殘單。建單失敗會誠實告知並附「再試一次」，**不會假裝成功**；重複同意**冪等**、不重複建單。
