# LIFF 線③④⑤ 28 情境 → AIChatbot 能力缺口表（2026-09-08，scout 盤查；**R10 後承接入口改為 `/mcp`，本表舊鏈落點僅供對照；G1 作廢**）

> 來源：line-bot `docs/chatai-repair-capture-spec.md`（③ A–Q，驗收 17）、`docs/chatai-digest-followup-spec.md`（⑤ A–K＋④ 催繳，驗收 12）。入口＝REST 面向（`trigger_facet_key`＋`facet_context`），⛔ 不是 demo 的 `/mcp`。**28 個中 0 個以其入口實跑過**（demo 收案時未對，業主 2026-09-08 指正）。

## 能力對照（有 9／部分 8／無 11；scout 判定，⚠️ 部分計數重疊，以逐條為準）

| 線 | 情境 | 能力 | 落點 | 缺什麼 |
|---|---|---|---|---|
| ③A | 3 張照片→確認→開單 | 部分 | `repair_create` 面向、`image_recognition_service` | 業務身分進場被 `repair_prefill.get_tenant_contracts` 租約查詢擋（R2） |
| ③B | 分類改錯只重確認該項 | 部分 | `conversational_engine` R3.2 | 已設計，需實跑 |
| ③C | 信心低→候選→選一 | 部分 | `repair_prefill` 0.7 門檻 | 候選只在文字、不進 `quick_replies` |
| ③D | 看不出損壞→描述留空 | 有 | `image_recognition_service` `is_damage=false` | — |
| ③E | 帳單單據不進報修 | N/A | line-bot 分岔 | AIChatbot 需誠實拒當報修 |
| ③F | ≥3 張全部進單 | 部分 | `chat.py` 3 張上限 | `VendorChatRequest` 無完整照片清單欄位 |
| ③G | 中途取消 | 有 | `form_cancelled` | — |
| ③H | 30 分鐘後回來 | 無 | `form_manager` 30 分鐘清會話 | 無過期訊號（R4） |
| ③I | 建單失敗→重試 | 有 | `chat.py` 誠實告知 | — |
| ③J | 重複同意不重複建 | 有 | R4.4 冪等 | — |
| ③K | 空屋無租約直接開 | 無 | `repair_prefill` 必查租約 | 同 R2 |
| ③L | 逾時／401／422 呈現 | 部分 | `chat.py` 驗證 | 需 key 實測 |
| ③M | 同名多戶（line-bot 收斂） | 部分 | — | 無 `facet_context.estate_id` 進場欄位（R5） |
| ③N | 已有未結同類單 | 無 | — | 無「未結單」判定與回應 |
| ③O | 只改急迫性 | 部分 | `repair_prefill` 槽位確認 | 值域已對碼（2＝緊急）、預設非緊急 ✅ |
| ③P | 一組照片兩問題 | 無 | — | 行為未定義（業主未裁） |
| ③Q | 分類樹無對應→大類 | 有 | 面向逐級問 | — |
| ⑤A | 逾期帳單追問 | 有 | `bill_diagnosis` 面向 | 缺 `bill_id` 進場欄位（R3） |
| ④B | 催繳草稿 | 無 | — | 無 `dunning_draft` 端點／動作 |
| ⑤C | 問別戶→退出 | 有 | `scope_exit` | — |
| ⑤D | JGB 無此欄位 | 有 | 面向規則 | — |
| ⑤E | 合約到期追問 | 有 | `contract_renew` 面向 | 缺 `contract_id` 進場欄位 |
| ⑤F | 緊急修繕追問 | 無 | — | 無修繕進度面向（舊鏈；agent 路徑已有 `jgb2.query.repairs`） |
| ⑤G | 結束會話 | 有 | `form_cancelled` | — |
| ⑤H | 30 分鐘後回來 | 無 | — | 同 ③H |
| ⑤I | 電錶追問 | 有 | `iot_meter` 面向 | 缺 `meter_id` 進場欄位 |
| ⑤J | 點開時資料已變 | 無 | — | 無「現況 vs 帶入值衝突」回應 |
| ⑤K | 同戶問別類別 | 部分 | `scope` 邏輯 | 與 C 分不開；同戶別類應指路不退出 |

> ⚠️ **2026-09-08 更新（demo 上線後）**：六類缺口的現況——**G2 已解**（業務身分不查租約，正本 delta2＋`repair_create` 描述）、**G3 已解**（`session_expired` 第六鍵，DSP-042）、**G4 部分解**（修繕進度面向可查、未結單提示已落地 W8 (3)；③P 兩問題仍待裁）、**G5 未做**（催繳草稿 `dunning.draft`＝W8 (4)，等業主給語氣分級與模板）、**G6 已解**（候選進 `quick_replies`＝照片低信心 ask；確認回執改由 `outcome{state:confirmed, ref}` 表達（DSP-043，⛔ 不叫 `form_completed`）；同戶別類指路＝規則兩句；資料已變以現查為準＝規則兩句）、**G1 早已作廢**（R10-b／R10-c：清單點選走機器值 `select:`）。⚠️ 本表其餘欄位是 2026-09-08 白天的判定，以帳本 §1h 與 `HANDOFF-20260909.md` 為準。

## 缺口六類（修一類解多格）

| # | 類 | 情境 | 落點 |
|---|---|---|---|
| ~~G1~~ | ~~`facet_context` 進場欄位~~ **作廢（R10-b：清單點選以文字帶編號／名稱送入 `agent.turn`）** | ③M、⑤A／E／I、③N 以文字進場即為真實入口 | — |
| G2 | **業務身分進場被租約查詢擋** | ③A、③K | `repair_prefill.get_tenant_contracts` 改為可缺 |
| G3 | **會話過期訊號** `session_expired` | ③H、⑤H | `form_manager`／回應形狀 |
| G4 | **缺面向／動作**：修繕進度（⑤F）、未結單判定（③N）、兩問題（③P，待裁） | 舊鏈面向 |
| G5 | **催繳草稿端點**（`dunning_draft`：模板＋語氣三級＋佔位符） | ④B | 新端點或面向內動作 |
| G6 | **應答細節**：候選進 `quick_replies`（③C）、確認回執 `form_completed`＋`repair.{id,no}`（R3）、同戶別類指路（⑤K）、資料已變以現查為準（⑤J） | `conversational_engine` |

## line-bot 端自理
文件明寫由其端處理的：③M 同名多戶收斂、③P 上傳前提示「一次一個問題」（降級）、③E 帳單單據分岔——但 AIChatbot 仍需對應的進場欄位與誠實回應。

## 要驗這 28 個需要
① G1–G6 決定做哪些；② REST 入口的 demo 用 key（現行 `RAG_API_AUTH_ENFORCE=true`）；③ 以 line-bot §6 的 30 個驗收案例（含 wire JSON）寫成 REST 劇本實跑（替身資料）；④ 盲判。估：G1＋G2＋G3＋G6 一週級、G4／G5 各一刀。
