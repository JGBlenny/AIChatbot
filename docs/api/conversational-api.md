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
  "stream": false                   // true = SSE 逐字串流
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

## Response A — 非串流（`stream:false`）

JSON（`VendorChatResponse`，重點欄位）：

```json
{
  "answer": "回覆文字（可能含 • 條列、純網址、\\n 換行）",
  "intent_type": "conversational",   // 對話中；導到表單時為 "form_filling"
  "session_id": "...",
  "form_triggered": false,           // 導到 CTA 表單時 true
  "form_id": null,                   // 表單 id（如 trial_form / demo_form）
  "current_field": null,             // 表單下一欄提示
  "quick_replies": null,             // 選項（若有）
  "confidence": 1.0,
  "mode": "b2b",
  "timestamp": "..."
}
```

> `answer` 顯示請用 **`white-space: pre-wrap`** 或 markdown 渲染（含換行/條列/純網址連結）。

## Response B — 串流（`stream:true`）

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

- 模糊需求 → 顧問式反問（一次一題：身分/規模/痛點…）
- 事實題（競品/價格/某功能）→ 直接答
- 了解夠 → 個人化推薦 ＋ 預約連結 `https://www.jgbsmart.com/demo-form`
- 合規：不報價（導 `https://www.jgbsmart.com/pricing`）、IoT 被問才提、競品中立

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
