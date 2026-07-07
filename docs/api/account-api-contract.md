# 帳號 G/J 契約（交付 jgb2 端）

> 交付日期：2026-07-03　來源：account-conversational-facets research.md（jgb2 真碼盤查，file:line 齊）
> 消費端一律**存在性驅動**：端點/欄位出現即自動啟用 grounded 分支，缺失走降級——**不需與 AIChatbot 同步上版**。

## G 清單：查詢能力擴充（第 1 層，非阻塞）

| # | 項目 | 建議做法 | 用途 |
|---|---|---|---|
| G-A1 | **以 phone/email 查名下租客的註冊/綁定狀態** | ✅ **已上線並實測（2026-07-04 preview）**：`GET /api/external/v1/tenants/registration-status?role_id=&(email|phone=)` → 回 `{found, is_bound, is_registered, lessee_email_verify_status, lessee_user_id, lessee_name}`。防枚舉驗證通過（查非名下租客回 `found:false`）；連待發送草稿合約的租客都查得到。**AIChatbot 已對接**（登入排障 secondary_call）。〔**兩件待 JGB 確認**：①端點路徑是否為正式命名（AIChatbot 猜中接入，改路徑會斷）；②email 比對是否大小寫敏感（同 J1，影響查詢命中）〕 | 登入排障 found 歸屬閘門＋三態排查 |
| G-A2 | **團隊成員權限查詢** | ✅ **已上線（2026-07-03 preview 驗證）**：`GET /roles/{role_id}/members/{user_id}/permissions` 回角色名＋27 能力旗標白名單（TeamMemberApiController；權限點 roles:read）。消費缺口：以 email/名字解析成員 user_id 的途徑（可併入 G-A1 或補 members 列表） | 團隊權限面向 grounded 判因；亦覆蓋合約 G5（edit_contract 旗標） |

**個資最小揭露（雙層，2026-07-04 均已落地）**：
- **API 層（JGB 已部署 preview）**：`lessee_name` 已從回應移除；保留 `lessee_user_id`（串 `tenants/{user_id}/summary` 用）。實測三態回應欄位 = `{found, is_bound, is_registered, is_lessee_user_registered, lessee_email_verify_status, lessee_user_id}`，防枚舉不變（非名下 `found:false`）。文件見 jgb2 `docs/api/tenants.md`。
- **消費層（AIChatbot）**：builder **只讀不吐**——僅用 `found`／`is_registered`／`email_verify` 決定分支，`lessee_user_id` 也不進回話（unit+integration 合成假名遮罩＋e2e 真 preview 全綠）。兩層獨立，任一層失效另一層仍守住。

**明文排除**：驗證碼查詢不納入任何對外能力——**jgb2 已在 docs/external-api-permission.md 明文採納此紅線** ✅。

**額外上線（超出原契約）**：Layer 2 `viewer_user_id` 圈定（bills/contracts/payments/invoices 支援按成員主體 owner/agent/大房東/租客圈資料，2026-07-03 preview 驗證）——JGB Web 內嵌場景若把當前登入成員 user_id 傳給 AI session，可升級為「按發問者職權圈定」的 grounded 查詢。

## J 清單：缺陷回報（真碼證據，建議修復）

| # | 缺陷 | 證據 | 影響 |
|---|---|---|---|
| J1 | **Email 比對實質大小寫敏感** | email 以 xxtea 密文存放與比對（User.php:263-275、:923），大小寫不同→密文不同→查重放行；會員端無 lowercase 正規化（admin 端有：Admin/IndexController.php:87）；users.email 無 unique 索引 | 重複帳號（客服實案：Yajingli4444@ 與 yajingli4444@ 兩帳號，租客登錯看不到電表）。建議：註冊/登入前 `strtolower(trim())` 正規化＋存量掃描 |
| J2 | **邀請成員 character_id 寫入 NULL** | `$defaultCharacterId = null` 宣告後從未賦值（UserController.php:10636），invite attach 直接用（:11646）；常數 `ROLE_DEFAULT_CAPABILITY_ID=6` 存在但未用（Role.php:30） | 新成員零權限、看不到社區也無法新增（客服實案 11）。建議：invite 帶預設角色或強制前端指派 |
| J3 | **authPhone 換綁後端未擋** | `sendVerSms`/`verifyPhone` 未檢查使用者是否已有已驗證手機（AuthController.php:724-745），「不能換綁」僅由前端 UI 保證 | 已綁定用戶直接打 API 可自行換綁（安全） |
| J4（小疏漏） | `GET /contracts/status-overview` 未掛 `_resource/_action` 權限點——**機制已從 source 確認**（jgb/jgb2＋jgb_interrogation 兩分支一致） | routes/api.php:40 無 defaults 宣告；middleware `if ($resource && $action)` 才檢查（ExternalApiAuth.php:73），讀不到即跳過該支的 `contracts:read` 檢查；同檔其他端點皆有掛 | **範圍被 role 白名單框死**（ExternalApiAuth.php:87 白名單另外恆檢）：僅「授權讀 role X 帳單」的 key 可連帶讀 role X 合約，**不能撈任意業者**——屬同授權範圍內的跨資源越權，非廣泛外洩。建議：補兩行 `->defaults('_resource','contracts')->defaults('_action','read')`。root key（AI 端這把）本就全通、不受影響 |
| J5 | 變更綁定信箱的重發冷卻起算欄位疑誤 | `getReSendEmailRemainSec()` 以 `email_verified_at` 起算（User.php:552），且 `reSendVerEmail()` 會改寫該欄位（:592） | 僅影響變更綁定信箱流程的冷卻計時（觀察級） |

## 消費端承諾

- 全部存在性驅動：G-A1/A2 未上線前，對應分支自動降級（引導問句/自查路徑/導客服附線索摘要），不阻斷、不虛構。
- 個資遮罩：登入信箱等識別性欄位輸出一律遮罩（g***@gmail.com 形式）；非明文（密文）視同欄位不可用（沿合約 G2 教訓，防假錯配）。
- J1 修復前，AI 知識口徑以「請以當初註冊時的確切寫法輸入」引導（不對使用者提及 bug）；修復後口徑可簡化。

## 優先序建議

**J1、J2 是客服實案的直接成因**（重複帳號/成員零權限），修復可直接消掉兩類高頻工單；G-A1/A2 依 jgb2 排程，到一項 AI 端自動啟用一項。
