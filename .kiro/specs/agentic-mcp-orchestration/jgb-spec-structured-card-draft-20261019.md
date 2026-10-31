# 站內幫手：JGB 面板上線前事項與確認卡結構化——需求稿草稿（2026-10-19）

> 狀態：**草稿，尚未寄出**；寄出與否由業主決定。上線範圍依 DSP-107、DSP-112、DSP-117、DSP-119、DSP-120、DSP-122（A＋期別＋A+＋B＋A-2a＋選對紀錄＋F12＋W2＋E＋填欄只填答覆＋填欄結構化＋照片與文件上傳）；第 4、5.2 節的結構化 `card` 對應目標正本 `architecture-target-20261018.md` §4 C 片（原則 P8），不擋上線，C 片計畫核可前只是提案。
> JGB 端現況依據（本機 checkout `~/dev/work/jgb2/dev1`，2026-10-30 查）：staging `8ff2f7b8e7`、master `eeccdfd8eb`；兩張 ticket 的 commit（`1f151705f4`、`c0e33721c2`、`daf09380a6`）都是 staging 的祖先、都不是 master 的祖先。

## 0. 一句話

**上線前 JGB 面板要改接 AIChatbot 的專用對話 API，不是把現行走 `/mcp` 的 `AgentTurnClient` 合入 master 就上線**（DSP-130、DSP-131；排在第 4 步切換正式機之前是主會話讀法，等級 C）。專用對話 API 已定案（業主 2026-10-31 核可，接口 A §3.1）：`POST https://chatai.jgbsmart.com/rag-api/v1/agent/turn` 與 `.../v1/agent/upload-ticket`，一回合一次 POST，金鑰、`X-JGB-Identity`、參數與回應內容同現行；AIChatbot 正式機部署後通知 JGB。本稿 §1 寫到的 `agent.turn`、`/mcp` 描述 JGB 現行介面。面板現行版與確認卡畫面已完成（2026-10-15），JGB 目前接 staging 分支。確認卡改用結構化資料（C 片）是上線後的改善，不擋上線。

## 1. 面板現況：staging 走現行介面，master 未合入

| 項目 | 現況 | 依據（可 grep） |
|---|---|---|
| 改接 `agent.turn` | jgb2 ticket_13290303502：`AgentTurnClient` 走 MCP streamable HTTP（initialize → initialized → tools/call `agent.turn`，帶 `Mcp-Session-Id`，結束送 DELETE）；身分由伺服端組 `X-JGB-Identity`，團隊 role_id 經 `vendor_map` 對到 vendor_id，不在表內一律不走 agent（fail-closed） | `app/Services/Assistant/AgentTurnClient.php` `TOOL_NAME`；`app/Http/Controllers/HelpAssistantController.php`；commit `c0e33721c2` |
| 確認卡等畫面 | jgb2 ticket_13290307734：`AgentMessage`、`ConfirmCard`、`ResultCard`、`AgentChoices`、`NextSteps`、格式守門 `guards.ts` | `src/components/HelpSystem/agent/`；commit `daf09380a6` |
| 合入狀態 | 兩張 ticket 都已在 staging，**都不在 master** | `git merge-base --is-ancestor 1f151705f4 eeccdfd8eb` ⇒ 非祖先；`git merge-base --is-ancestor 1f151705f4 8ff2f7b8e7` ⇒ 祖先 |
| 送出的工具參數 | `message`（非空才帶），有附件時加 `upload_ids`、`attachment_purpose`；取上傳票走 `agent.upload_ticket`，只帶 `attachment_purpose`；⛔ 採用瀏覽器送來的身分欄位 | staging `AgentTurnClient.php` `TICKET_TOOL_NAME`；commit `446b84c8a4` |
| 設定 | `config/services.php` `assistant_agent`：`ASSISTANT_AGENT_URL`、`ASSISTANT_AGENT_API_KEY`、`ASSISTANT_AGENT_VENDOR_MAP`（`role_id:vendor_id,…`）、`ASSISTANT_AGENT_ENABLED`（預設 false）、`ASSISTANT_AGENT_TIMEOUT_SECONDS`（預設 60） | `config/services.php` `"assistant_agent"` |

正式環境（2026-10-28 唯讀查詢，只看有無值、不看值）：`ASSISTANT_AGENT_URL`、`ASSISTANT_AGENT_API_KEY`、`ASSISTANT_AGENT_VENDOR_MAP`、`ASSISTANT_AGENT_ENABLED` 四個鍵都是空或不存在（同次查詢的正對照 `APP_KEY` 有值）；正式機 www 部署版 `bb217ebc6a`，兩張 ticket 都不在內。

## 2. 上線前 JGB 端要做的事（DSP-093）

| # | 事項 | 怎樣算完成 |
|---|---|---|
| L1 | 面板改接專用對話 API（接口 A §3.1）：`AgentTurnClient` 不再走 MCP（拿掉 initialize／initialized／`Mcp-Session-Id`／DELETE），每回合直接 `POST .../v1/agent/turn`，body 就是現行送的工具參數（`message`、`upload_ids`、`attachment_purpose`），header 照舊 `X-API-Key`、`X-JGB-Identity`，加 `Content-Type: application/json`；200 body 就是現行 `agent.turn` 結果 JSON，非 200 依 body 的 `code` 處理（對照接口 A §11）；取上傳票改 `POST .../v1/agent/upload-ticket`（body `{"attachment_purpose": …}`）。改完連同確認卡畫面合入 master 並部署正式版 | `origin/master` 含改接後的面板；正式版對話不再走 `/mcp` |
| L2 | 正式環境設定：`ASSISTANT_AGENT_URL=https://chatai.jgbsmart.com/rag-api/v1/agent/turn`（完整路徑，不跟隨轉址；上傳票網址同前綴 `/v1/agent/upload-ticket`）、`ASSISTANT_AGENT_API_KEY`（AIChatbot 發給站內幫手的金鑰，只放伺服端）、`ASSISTANT_AGENT_VENDOR_MAP`、`ASSISTANT_AGENT_ENABLED=true` | 正式站登入一個已對到 vendor 的團隊，送一句話收到專用對話 API 的回覆；未對到的團隊照舊走原本對話 |
| L3 | 正式環境的 Origin：AIChatbot 端 `MCP_ALLOWED_ORIGINS` 只管瀏覽器直連；JGB 由伺服端呼叫不送 Origin，⛔ 需要加白名單 | L2 的實打通過即可 |
| L4 | 面板支援照片與文件上傳（DSP-120、DSP-122）：照接口 A（`docs/api/jgb2-web-assistant-integration.md`）§7，JGB 後端取上傳票，瀏覽器把檔案直傳 AIChatbot 拿 `upload_id`，對話帶 `upload_ids`（照片 ≤10、文件 1 份）與 `attachment_purpose`（報修照片 `repair`；謄本、收據、發票 `document`）；回覆 `outcome.expects=image`／`file` 時要開傳照片／傳檔鍵（⛔ 不要只開輸入框）；staging 現在顯示「此功能即將開放」（§3），要改掉。JGB 不需要專用上傳網域。上傳與引用流程 staging 已用現行介面做完（`agent.upload_ticket`、`agent.turn`）；改接專用對話 API 時取上傳票一起改接（`POST .../v1/agent/upload-ticket`，見 L1），再隨 L1 合入 master。接口 B #22 的 multipart staging 已開，同樣隨 L1 合入 master | **JGB 端完成**（JGB 自己驗得了）：正式站上傳一張報修照片，送出的對話請求帶 `upload_ids` 與 `attachment_purpose=repair`；回覆 `outcome.expects=image`／`file` 時出現傳照片／傳檔鍵。<br>**整體完成**（擋切換；要 AIChatbot 端也上線才驗得過）：正式站上傳一張報修照片，收到確認卡且卡上「附照片：1 張」，按確認後 JGB 修繕單上看得到這張照片；上傳一份謄本 PDF 收到物件確認卡。AIChatbot 端前置：修繕單照片送 JGB（#22 改接）、建物件改接（#19），見接口 A §9、§10 |
| L5 | AIChatbot 正式機要能打 staging 外部 API：AIChatbot 正式機（chatai，對外 IP `3.114.12.10`）帶金鑰打 `https://staging.jgbsmart.com/api/external/v1/repairs/categories` 回 403 純文字 `Forbidden`（非 JSON）；同一把金鑰打 www 回 200；辦公室 IP 不帶金鑰打 staging 回 Laravel JSON 401（2026-10-31 實測）。staging `routes/api.php` 的 external/v1 群組沒有 IP 白名單 middleware，純文字 `Forbidden` 不是 Laravel 回的，是 staging 入口（DNS 指向 `13.193.163.182`、`13.231.19.127`，www 走 CloudFront）在 Laravel 之前擋下。正式機主機不帶金鑰打 staging 同樣回純文字 `Forbidden`、打 www 回 JSON 401 ⇒ 擋的是來源 IP，與金鑰無關。請 JGB 在 staging 入口的防火牆、WAF 或負載平衡規則放行 `3.114.12.10`。AIChatbot 正式機要改連 staging 測完整寫入與照片（業主 2026-10-31 裁定） | chatai 正式機打 staging `GET /api/external/v1/repairs/categories` 回 JSON（200），不是純文字 `Forbidden` |

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
