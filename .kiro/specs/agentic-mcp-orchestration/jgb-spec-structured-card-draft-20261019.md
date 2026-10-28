# 站內幫手：JGB 面板上線前事項與確認卡結構化——需求稿草稿（2026-10-19）

> 狀態：**草稿，尚未寄出**；寄出與否由業主決定。上線範圍依 DSP-107、DSP-112、DSP-117、DSP-120（A＋期別＋A+＋B＋A-2a＋選對紀錄＋F12＋W2＋E＋填欄只填答覆＋照片與文件上傳）；第 4、5.2 節的結構化 `card` 對應目標正本 `architecture-target-20261018.md` §4 C 片（原則 P8），不擋上線，C 片計畫核可前只是提案。
> JGB 端現況依據（本機 checkout `~/dev/work/jgb2/dev1` 的遠端追蹤分支，最後一次 fetch 2026-10-27 18:28）：`origin/preview` `fe4daec748`（2026-10-23）、`origin/master` `3515960cd7`（2026-10-27）；兩張 ticket 的 commit（`1f151705f4`、`c0e33721c2`、`daf09380a6`）都是 `origin/preview` 的祖先、都不是 `origin/master` 的祖先。

## 0. 一句話

面板改接 `agent.turn` 與確認卡畫面，JGB 已在 preview 做完（2026-10-15）；上線前 JGB 端剩下的是**合入正式版並填正式環境設定**。確認卡改用結構化資料（C 片）是上線後的改善，不擋上線。

## 1. 改接現況：preview 已完成，master 未合入

| 項目 | 現況 | 依據（可 grep） |
|---|---|---|
| 改接 `agent.turn` | jgb2 ticket_13290303502：`AgentTurnClient` 走 MCP streamable HTTP（initialize → initialized → tools/call `agent.turn`，帶 `Mcp-Session-Id`，結束送 DELETE）；身分由伺服端組 `X-JGB-Identity`，團隊 role_id 經 `vendor_map` 對到 vendor_id，不在表內一律不走 agent（fail-closed） | `app/Services/Assistant/AgentTurnClient.php` `TOOL_NAME`；`app/Http/Controllers/HelpAssistantController.php`；commit `c0e33721c2` |
| 確認卡等畫面 | jgb2 ticket_13290307734：`AgentMessage`、`ConfirmCard`、`ResultCard`、`AgentChoices`、`NextSteps`、格式守門 `guards.ts` | `src/components/HelpSystem/agent/`；commit `daf09380a6` |
| 合入狀態 | 兩張 ticket 都已在 `origin/preview`，**都不在 `origin/master`** | `git merge-base --is-ancestor 1f151705f4 origin/master` ⇒ 非祖先 |
| 送出的工具參數 | 只送 `message`；⛔ 採用瀏覽器送來的身分欄位與 `image_urls` | `AgentTurnClient.php` `'arguments' => ['message' => $message]` |
| 設定 | `config/services.php` `assistant_agent`：`ASSISTANT_AGENT_URL`、`ASSISTANT_AGENT_API_KEY`、`ASSISTANT_AGENT_VENDOR_MAP`（`role_id:vendor_id,…`）、`ASSISTANT_AGENT_ENABLED`（預設 false）、`ASSISTANT_AGENT_TIMEOUT_SECONDS`（預設 60） | `config/services.php` `"assistant_agent"` |

正式環境（2026-10-28 唯讀查詢，只看有無值、不看值）：`ASSISTANT_AGENT_URL`、`ASSISTANT_AGENT_API_KEY`、`ASSISTANT_AGENT_VENDOR_MAP`、`ASSISTANT_AGENT_ENABLED` 四個鍵都是空或不存在（同次查詢的正對照 `APP_KEY` 有值）；正式機 www 部署版 `bb217ebc6a`，兩張 ticket 都不在內。

## 2. 上線前 JGB 端要做的事（DSP-093）

| # | 事項 | 怎樣算完成 |
|---|---|---|
| L1 | ticket_13290303502、ticket_13290307734 合入 master 並部署正式版 | `origin/master` 含 `1f151705f4` 與 ticket_13290307734 的最後一個 commit |
| L2 | 正式環境設定：`ASSISTANT_AGENT_URL=https://chatai.jgbsmart.com/rag-api/mcp`（完整路徑，不跟隨轉址）、`ASSISTANT_AGENT_API_KEY`（AIChatbot 發給站內幫手的金鑰，只放伺服端）、`ASSISTANT_AGENT_VENDOR_MAP`、`ASSISTANT_AGENT_ENABLED=true` | 正式站登入一個已對到 vendor 的團隊，送一句話收到 `agent.turn` 回覆；未對到的團隊照舊走原本對話 |
| L3 | 正式環境的 Origin：AIChatbot 端 `MCP_ALLOWED_ORIGINS` 只管瀏覽器直連；JGB 由伺服端呼叫不送 Origin，⛔ 需要加白名單 | L2 的實打通過即可 |
| L4 | 面板支援照片與文件上傳（DSP-120）：照接口 A（`docs/api/jgb2-web-assistant-integration.md`）§7 上傳到 JGB 專用上傳網域，`agent.turn` 帶 `image_urls`（照片，≤10）、`file_urls`（PDF，≤1）、`attachment_purpose`（報修照片 `repair`；謄本、收據、發票 `document`）；回覆 `quick_replies` 的 `image` 鍵要開拍照／相簿。現況 `AgentTurnClient.php` 只送 `message`。另請回覆接口 B #22（照片交付方式、專用上傳網域名稱） | 正式站上傳一張報修照片收到確認卡且卡上「附照片：1 張」；上傳一份謄本 PDF 收到物件確認卡 |

金鑰交付走雙方既有的安全管道，⛔ 寫進本稿、ticket 或 Monday。

## 3. preview 面板與 AIChatbot 回應的對照（上線相容性）

| AIChatbot 回應 | preview 面板怎麼處理 | 依據 |
|---|---|---|
| `quick_replies` 為 `[{label, value}]` | 收 `{label,value}`，顯示 `label`、按下原樣送 `value`；字串陣列相容 | `guards.ts` `normalizeReplies`；`useChat.ts` `normalizeQuickReplies` |
| 確認卡：`outcome.state=confirm_pending`、`expects=button`、三顆 `confirm_*:<pending_id>` | 依 `confirm_(submit|edit|cancel):[0-9a-f]{16}` 畫三顆鍵；格式不合或碼不一致 ⇒ 整卡只顯示文字。AIChatbot `pending_id` 為 16 位小寫十六進位，相符 | `guards.ts` `CONFIRM_VALUE_RE`、`buildConfirmButtons`；`rag-orchestrator/services/agent/tools/confirm.py` `PENDING_ID_CHARS` |
| 卡片內容 | 卡身顯示 `answer` 純文字（不經 Markdown）；鍵的文字固定，不用 AI 給的 `label` | `ConfirmCard.vue` `agent-confirm-body`；`guards.ts` `CONFIRM_LABELS` |
| 按過與舊卡 | 按過即鎖；只有最後一則訊息可互動 | `ConfirmCard.vue` `locked`；`AgentMessage.vue` `interactive` |
| `confirm_*` 出現在一般選項 | 一律濾掉，只准在確認卡出現 | `guards.ts` `withoutConfirm` |
| `state` 為 `confirmed`／`cancelled` | 結果卡；`ref.type=repair` 時帶修繕單連結 | `AgentMessage.vue`、`guards.ts` `repairLinkId` |
| `state=handoff` 或 `kind=handoff` | 顯示文字＋「找真人」（`mailto:service@jgbsmart.com`） | `guards.ts` `HUMAN_SUPPORT_HREF` |
| `expects=image`／`file` | 顯示「此功能即將開放，請先用文字描述」 | `AgentMessage.vue` `agent-hint` |
| `state` 為 `failed`／`out_of_scope` | 不在 `KNOWN_STATES`，走「未知 state」：純文字＋選項 | `guards.ts` `KNOWN_STATES` |
| `session_expired=true` | 顯示「對話已重新開始，先前的待確認項目已失效」 | `AgentMessage.vue` `agent-expired` |
| 確認送出逾時 | 不給重試鈕，提示先到清單確認是否已建立 | `useChat.ts` `CONFIRM_TIMEOUT_TEXT` |

AIChatbot 端第 3 步改了：A 片改「我要修改」鍵與卡後改欄位的回法；A+ 改出卡的觸發方式（出卡只由程式依草稿觸發）；B 改帶狀態的句子；E 片的程式轉人回 `kind=handoff`、`state=handoff`，文字請客人點「找真人」，對應上表 handoff 列。上表各列是否仍成立，要在 preview 面板實點確認（交接待辦表）。

## 4. 目標形態（業界原文，C 片依據）

| 做法 | 原文（逐字） | 來源 |
|---|---|---|
| 內容由發送方給結構化資料，另附文字備援 | 「Structured content is returned as a JSON value in the structuredContent field of a result.」「For backwards compatibility, a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block.」 | MCP 規格 https://modelcontextprotocol.io/specification/latest/server/tools（`~/jgb-archive/devflow-20261018/sources-card/mcp-tools-latest.txt`） |
| 內容歸發送方、外觀歸呈現方 | 「Card Authors own the content, Host App owns the look and feel」 | Adaptive Cards https://learn.microsoft.com/en-us/adaptive-cards/（`sources-card/ms-adaptive-cards-overview.txt`） |
| 畫不出卡片時顯示文字 | fallbackText：「The text that should be displayed if the client is not able to render the card.」 | Adaptive Cards schema https://adaptivecards.microsoft.com/?topic=AdaptiveCard（`sources-card/adaptive-cards-schema-AdaptiveCard.txt`） |
| 按鈕怎麼畫由呈現端決定 | 「it is up to the implementation of the output channel how to display the defined buttons」 | Rasa https://rasa.com/docs/reference/primitives/responses/（`sources-card/rasa-responses.txt`） |
| 按鈕帶機器值，按下後送回伺服器 | Slack button `value`：「The value to send along with the interaction payload.」；Zendesk：「Each reply button has an associated payload, which should uniquely identify the intent of the action.」；Rasa：「payload: The message sent from the user to the assistant when the button is clicked.」 | Slack https://docs.slack.dev/reference/block-kit/block-elements/button-element（`sources-card/slack-button-element.txt`）；Zendesk structured messages（`sources-card/zendesk-structured-messages-real.txt`）；Rasa 同上 |

preview 面板已做到後兩列（按鈕機器值、外觀由面板決定）；與目標形態的差距是**卡身仍是文字**——欄位由面板以純文字顯示 `answer`，無法逐欄排版或依欄位給樣式。

## 5. 上線後的改善：結構化確認卡（C 片提案）

### 5.1 AIChatbot 會多回什麼

新增 `card`，只在 `outcome.state = "confirm_pending"` 時出現：

```json
{
  "type": "confirm",
  "action": "repair_create",
  "title": "報修確認",
  "fields": [
    {"label": "物件", "value": "（物件正式名稱）"},
    {"label": "急迫程度", "value": "非緊急"}
  ],
  "buttons": [
    {"label": "✅ 確認送出", "value": "confirm_submit:<pending_id>", "role": "submit"},
    {"label": "✏️ 我要修改", "value": "confirm_edit:<pending_id>", "role": "edit"},
    {"label": "❌ 取消", "value": "confirm_cancel:<pending_id>", "role": "cancel"}
  ]
}
```

- `buttons` 與同一回合的 `quick_replies` 內容相同；`answer` 仍是完整文字版。
- 按鈕機器值的前綴來自 `rag-orchestrator/services/form_contract.py` 的 `QR_SUBMIT`／`QR_EDIT`／`QR_CANCEL`（穩定契約）。

### 5.2 請 JGB 改的項目

| # | 改什麼 | 怎樣算完成 |
|---|---|---|
| J2 | 有 `card` 時卡身改依 `fields` 逐列顯示（`label`：`value`），標題用 `title`；外觀由 JGB 決定；按鈕維持現行 `buildConfirmButtons` 的檢查 | 報修、延期各一張卡逐欄顯示；欄位與 `answer` 文字版一致 |
| J3 | `card` 缺欄位、未知 `type`，或與 `quick_replies` 的按鈕不一致 ⇒ 退回現行做法（卡身顯示 `answer`） | 送一張未知 `type` 的卡，畫面與現行相同、按鈕可按 |

### 5.3 欄位表（待補）

各寫入動作卡片上的欄位清單，C 片計畫時補上（A 片已把 enum 欄位改由程式轉成中文標籤）。

## 6. 待決

1. `card` 放 `agent.turn` 結果頂層，還是照 MCP 放進 `structuredContent`——C 片計畫決定；JGB 的 `AgentTurnClient` 目前讀哪一層，C 片計畫時再對碼。
