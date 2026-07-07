# G1–G4 外部 API 欄位擴充契約（交付 jgb2 端）

> 交付日期：2026-07-02　來源：contract-conversational-facets design.md「API 設計」節＋research.md §四盤查（皆附 jgb2 file:line 證據）
> 消費端（AIChatbot）已按**存在性驅動**實作完成：回傳中有該欄位即自動啟用對應診斷分支、沒有則略過不報錯——**兩端可獨立部署，無版本協商需求**。

## 一、`GET /api/external/v1/contracts/status-overview`（既有端點，加 6 欄）

| Gate | 欄位 | 資料來源（jgb2） | AIChatbot 用途 |
|---|---|---|---|
| G1 | `contract_inviting_at` | `contracts` 現有欄位（發送簽約邀請時間） | 簽署排障：邀請何時發出 |
| G1 | `contract_inviting_expire_at` | `contracts` 現有欄位（效期預設 +72h，`ContractController.php:14805`；白名單角色 168h/720h `:14815-14819`） | 簽署排障：判斷邀請是否過期→說明自動退回「待發送」並清空租客資料（`ContractStatusUpdater.php:146`） |
| G1 | `contract_inviting_sign_at` | `contracts` 現有欄位（租客簽名時間） | 簽署排障：租客實際簽署時點 |
| G1 | `contract_finish_sign_at` | `contracts` 現有欄位（雙方完成時間） | 簽署排障：簽署完成佐證 |
| G2 | `to_user_login_email` | `users.email`（經 `contracts.to_user_id` join） | 簽署排障：發送信箱 vs 登入信箱錯配比對（SSO 情境「發 gmail 但用別的帳號登入」） |
| G4 | `is_newest` | `contracts` 現有欄位 | 續約：`is_newest=0` ⇒ 此約已有較新續約，提示列表僅顯示最新一筆 |

## 二、`GET /api/external/v1/bills`（既有端點，加 2 欄）

| Gate | 欄位 | 資料來源（jgb2） | AIChatbot 用途 |
|---|---|---|---|
| G3 | `is_archived` | model 已有 `archive_at`（`BillApiController` select＋formatBill 目前未選出） | 退租收尾：個人化指出「哪些帳單還沒封存」 |
| G3 | `archive_ymd` | 同上 | 退租收尾：封存時點 |

## 二之一、選配擴充（G5，評估項——非本波必要）

| Gate | 需求 | 現況缺口 | 用途 |
|---|---|---|---|
| G5 | 「發問成員對該合約的編輯權限」查詢（如 status-overview 加 `requester_can_edit`，或獨立權限端點） | 權限主體是 team member 角色，外部 API 目前只有 vendor 層（X-API-Key）＋ role_id；且需先確認 AI 客服 session 身分可對應到 jgb2 成員 | 合約異動面向「編輯不了」的**權限擋 vs 狀態擋**機械分流——現以引導問句分流（知識 qa13 自助排查），欄位上線後可升級為決定性判斷（消費端存在性驅動，同 G1–G4 模式） |

## 二之二、上線驗證狀態（2026-07-02，preview 實測）

- **G1 ✓**：四個時間戳已露出且格式可解析（`YYYY-MM-DD HH:MM:SS`），效期分支已以真資料 e2e 驗證。
- **G2 ✓（2026-07-02 已修復並驗證）**：初版回傳加密密文，jgb2 修正後已回明文；29 筆有值列全數可比對，決定性層以真資料（84927）驗證「一致」分支、e2e 全綠。錯配（不一致＋遮罩輸出）分支因 preview 資料無錯配樣本，由單元測試覆蓋。消費端保留密文防護（值非明文信箱即略過），未來回歸可自動降級不誤報。
- **G3 ✓**：`is_archived`/`archive_ymd` 已露出；secondary_call 個人化封存已以真資料 e2e 驗證。
- **G4 ✓**：`is_newest` 已露出（此端點僅回最新列，=0 分支以單元測試覆蓋）。
- **G5 ✓（換形態上線並已對接，2026-07-04）**：jgb2 permissions 端點（edit_contract 等 32 旗標）滿足 G5；AIChatbot 已接（contract 7.4，commit 見 repo）——合約異動收斂時以 `{session.user_id}` 查發問者權限，權限擋 vs 狀態擋機械分流。存在性驅動：session user_id 非 jgb2 成員→自動降級現行輸出。**完整啟用條件：JGB Web 內嵌把當前登入成員的 user_id 傳入 AI session**（同 viewer_user_id 整合議題）。

## 三、格式與安全約定

- **時間戳格式**：`YYYY-MM-DD HH:MM:SS`（或 ISO 8601；消費端以 `fromisoformat` 相容解析）。`is_newest`／`is_archived` 用 0/1。
- **個資**：`to_user_login_email` 屬個資——AIChatbot 僅用於錯配比對事實句，回覆中以遮罩形式輸出（`g***@gmail.com`），不完整揭露（已實作並有測試覆蓋）。
- **驗證**：沿用既有 `X-API-Key` per-vendor 驗證與資源權限，無新增授權需求。

## 四、部署與時程

- 四個 Gate 彼此獨立，可分批上線；**成本皆低**（G1/G4 為 contracts 現有欄位直接 select；G2 一個 join；G3 select＋format 補兩欄）。
- 欄位上線後 AIChatbot 對應分支**自動啟用**，無需通知或改版；未上線期間以降級態運作（G1/G2 略過該分支、G3 輸出通用封存指引）。
- G3 上線後 AIChatbot 端另有後續任務（`secondary_call` 二次查詢機制，見 tasks.md 7.3），屆時退租收尾的封存步驟由通用指引升級為個人化。
