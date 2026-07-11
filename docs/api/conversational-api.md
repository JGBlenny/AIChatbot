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
  "confidence": 1.0,
  "mode": "b2b",
  "timestamp": "..."
}
```

> `answer` 內含 **markdown**（換行/`•` 條列/`[標籤](網址)` 連結），顯示端請用 **markdown 渲染**（連結才會變可點按；純 `pre-wrap` 會顯示原始 `[]()` 文字）。

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

event: done
data: {"success": true, "message": "答案生成完成"}
```

**解析**：把所有 `answer_chunk` 的 `chunk` 依序串接 = 完整答案。

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
