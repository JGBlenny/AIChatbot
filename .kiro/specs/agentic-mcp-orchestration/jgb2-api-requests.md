# jgb2 API 缺口總帳（mock 替代 → 日後一次請 JGB 開）

> 業主 2026-09-05：「JGB API 不足的部分可以用 mock 替代，之後整理一起請 JGB 開。」
> 本檔是**唯一總帳**：每一個 mock 都必須對得回這裡的一列；每一列都寫清楚「解除條件」。日後要請 JGB 開時，直接從本檔匯出一頁版。
> 來源三處合併：本 spec `jgb2-source-index.md` §6 缺口登記、line-bot-platform `docs/jgb-api-requests.md` §2、`docs/chatai-*.md` 提到的 JGB 端未驗證主張。

## 0. mock 紀律（⛔ 不遵守就不准 mock）

| 規則 | 為什麼 |
| --- | --- |
| **只在一個邊界 mock**：`rag-orchestrator/services/jgb_system_api.py` 的 `JGBSystemAPI`（既有 `USE_MOCK_JGB_API` 開關，22 個公開方法皆有 `if self.use_mock` 短路）。agent 工具層（`services/agent/tools/jgb2.py`）與面向層 ⛔ 不各自造假 | 一個開關可全關；分散的假資料會混進正式路徑 |
| **mock 資料一律「錄」不「編」**：能打到的端點用真回應錄成 fixture（去識別、附錄製日期與端點版本）；JGB 還沒有的端點，fixture 形狀以本檔對應列的「期望契約」為準並標 `contract: proposed` | 編出來的欄位會變成我們對 JGB 的錯誤假設，日後對接時才炸 |
| **每個 mock 標回本檔列號**：fixture 檔名或 docstring 含 `jgb2-req#<n>`；本檔該列「現況替代」欄反向列出 fixture 路徑 | 解除條件成立時能一次找出要拆的 mock |
| **mock 路徑的結果 ⛔ 不得宣稱 e2e 已驗**：`agent_eval` 報表、perf 檔、收案紀錄一律標 `jgb_mock=true` 的題數；M3／M4 放行必須有真 API 路徑的 e2e | 「回測前先驗容器」同理：假的下游會讓整輪結論翻盤 |
| **正式環境 ⛔ 不開 mock**：`docker-compose.prod.yml` 預設 `USE_MOCK_JGB_API:-true`，本機 `.env` 已覆寫（容器啟動日誌 `use_mock=False`）；線上部署 runbook 必查此值 | 預設值是 true，忘了設就是全假資料上線 |
| **mock 有期限**：每列寫「解除條件」；JGB 開了就拆 mock、補真路徑 e2e、關列 | 沒有期限的 mock 會變永久 |

查證：`grep -n "use_mock" rag-orchestrator/services/jgb_system_api.py`；`docker logs aichatbot-rag-orchestrator 2>&1 | grep -o "use_mock=[A-Za-z]*"`。

## 1. 總帳

阻擋等級：🔴 沒有它整條線走不通　🟠 有替代但品質差　🟡 非阻擋　❓ 待對碼確認（不一定是缺口）
誰要：`agent`＝本 spec（M1–M5）；`facet`＝現有面向鏈（線③④⑤接入）；`line`＝line-bot 自己直打 JGB

| # | 需求（端點／參數／文件） | 誰要 | 等級 | 現況替代（mock／繞法） | 解除條件 | 出處 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `GET /contracts/status-overview` 加 `estate_id` 查詢參數 | facet（線③）、agent M4 | 🟡 | 業務路徑不查租約、`contract_id` 留空開單（確認訊息無租客名） | JGB 補參數；chatai 改 prefill 用 `estate_id` | line-bot `jgb-api-requests.md` §2.6 E1 |
| 2 | `POST /repairs` 的 `contract_id` 為 nullable、開單人由 `agentUser` 帶入——**JGB 端主張未經我方驗證** | facet（線③）、agent M4 | ❓ | 先以 mock 回 201；真路徑用測試團隊 role 20151 打一張再刪 | JGB 確認或我方實打證實 | `chatai-repair-capture-spec.md` 頂部警語 |
| 3 | `emergency_status` 值域：`1=緊急/2=非緊急` 還是相反；缺值預設 | facet（線③）、agent M4 | 🔴 上線前必答 | 不 mock——值域猜錯會把急件派成不急；在確認前 `suggested_emergency` 缺值一律留空讓人選 | JGB 以 DB 真值回答 | `chatai-requests.md` C1；`chatai-repair-capture-spec.md` R7 |
| 4 | `GET /bills` 缺**入帳日**欄位 | facet（線⑤）、agent M5 | 🟡 | 誠實回「JGB 沒有此資料」；⛔ 不用 `updated_at` 冒充、不 mock 一個假日期 | JGB 加欄位（若業務上需要） | `chatai-digest-followup-spec.md` §1 註、情境 D |
| 5 | 帳單 `category`（屋主直收／屋主提領／備用金…）的 `mapping` 標籤表 | agent M5、知識 | 🟠 | 本 repo 硬表暫補（標 `jgb2-req#5`）；答不出「屋主直收帳單是什麼」 | `BillApiController.getMapping()` 補 `category` | `jgb2-source-index.md` §6 缺口 4 |
| 6 | 訂閱方案：`GET /roles/{role_id}/subscription` 有端點無文件 | agent（業者問方案） | 🟠 | 以執行期 `mapping.plan_type` 自描述為準；文件缺口列知識待補 | JGB 補 `docs/api/subscription.md` | `jgb2-source-index.md` §6 缺口 2 |
| 7 | `contract_renew`／`iot_meter` 面向 `search_params` 是 `keyword`，非 id 直查——數字 id 能否唯一命中 | facet（線⑤）、agent M5 | ❓ | agent 路徑 `jgb2.query.*` 已以 `ref` 直查（bills 已驗；contracts／meters 待驗） | 我方實打驗證；不需 JGB 動 | `chatai-requests.md` C4 |
| 8 | 修繕**歷史／進度**查詢（線⑤ C 類追問） | facet、agent M5 | 🟠 | `GET /repairs` 已存在（含 `is_urgent` 過濾）⇒ 缺的是我方面向／工具，不是 JGB API；第一版不開追問 | 我方 M5 開 `jgb2.query.repairs` | `chatai-digest-followup-spec.md` R4 |
| 9 | `GET /communities`、`POST /communities` | line（建立物件流程） | 🔴（line） | line-bot 自行處理；不進 chatai | JGB 新端點 | line-bot `jgb-api-requests.md` §2 A1–A2 |
| 10 | `POST /estates` 開到對外（現在 IP 白名單群組） | line | 🔴（line） | 同上 | JGB 調整權限群組 | 同上 A3 |
| 11 | `POST /contracts` 真建約（`agent/v1` 那支是造假資料工具） | line；agent M4 若做建約 | 🔴（line） | 同上；agent M4 首批寫入**不含建約** | JGB 新端點 | 同上 B1；`chatai-requests.md` §0 地雷 |
| 12 | 帳單憑據上傳 | line | 🟠（line） | 同上 | JGB 新端點 | 同上 C |
| 13 | 抄表回寫（`/meters` 只有讀） | line；agent M4 候選 | 🟡 | 同上 | JGB 新端點 | 同上 D1 |
| 14 | 業者 API 四張權限表無 migration | agent（DSP-011 前提偵測、開新 key） | 🟡 | 權限真相問線上 DB | JGB 把 schema 進 migration | `jgb2-source-index.md` §6 缺口 3 |
| 15 | `status-overview` 以 `to_user_id` 過濾——JGB 端主張未驗 | facet（線③） | ❓ | — | 我方實打或 JGB 確認 | `chatai-repair-capture-spec.md` 頂部警語 |

## 2. 給 JGB 的一頁版（日後匯出時用）

只匯出「解除條件」欄需要 JGB 動作的列：**#1、#3、#4、#5、#6、#9–#14**；#2／#7／#8／#15 是我方要驗或要做的，⛔ 不要寄給 JGB。
排序：🔴 先（#3、#9–#11）→ 🟠（#5、#6、#12）→ 🟡（#1、#4、#13、#14）。
每列附：要什麼、為什麼、我們現在怎麼繞、誰在等（agent 哪個里程碑／line 哪條線）。

## 3. 維護

- 新增 mock 之前先在此加列；拆 mock 時把該列狀態改「已開，mock 已拆（commit）」。
- 每次 `jgb2-source-index.md` §8 同步作業跑完，對照本檔：JGB 端有動的列更新解除狀態。
- 本檔不記進度以外的事實；JGB 端行為的權威來源仍是 `jgb2-source-index.md`。
