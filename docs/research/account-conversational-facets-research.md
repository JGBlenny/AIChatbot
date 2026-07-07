# 研究記錄：account-conversational-facets

> 建立時間：2026-07-03
> 目的：jgb2 帳號真碼盤查（五路平行）＋本站 b2c 機制盤查＋33 案歸類——design 的 ground truth 依據
> jgb2 盤查基準：`/Users/lenny/jgb/project/jgb/jgb2`（branch ticket_12405815624；帳號核心屬穩定舊碼，分支敏感度低）

## 摘要

### 調查範圍
gap-analysis §四的 8 條研究題：驗證碼機制、LINE 登入、大小寫敏感、自助修改範圍、團隊權限模型、G 授權可行性、b2c 現況、33 案歸類。

### 關鍵發現
- **驗證碼「新舊碼對不上」機制證實**：重發即產新碼覆寫舊碼（舊碼立即失效）；冷卻中（簡訊/Email 皆 120s）按重發**不產新碼也不發送**；訊息帶 3 字母 ver_id 供對碼——排障口徑=「只用 ID 對得上的最後一封、冷卻中別狂按」。
- **三個 jgb2 缺陷被真碼證實**（入 J 清單回報）：email 比對走 xxtea 密文＝實質大小寫敏感（重複帳號真因）；邀請成員 `character_id` 寫入 NULL（成員看不到社區真因）；手機換綁 API 未擋僅 UI 擋。
- **登入排障可以立即 ground**：`jgb_contracts` 已回 `is_tenant_registered`＋`to_user_phone/email`（master 就有）＋`to_user_login_email`（G2/preview）——「租客登不進去」可查合約判註冊狀態與帳號錯配，本領域**不是全無 API**。
- **b2c 隔離證實**：tenant 檢索命不中 property_manager-only 錨點（target_user＋business_types 雙閘）；但 config 無角色維度、tenant 若經任何路徑進面向會原樣載 pm persona——錨點標 pm-only 即為正確初版策略。
- **33 案歸類**：機制類 16／B.Bug 事故 11／跨域簽約頁 4／其它 2——機制類足撐四面向，策略 A 成立不縮編。

## 研究主題

### 主題 1：驗證碼與註冊機制（jgb2 真碼）

**發現**（file:line 皆 jgb2 repo）：
- 註冊主路徑是 **Email**（Welcome→EmailVerify→設密碼→選角色→綁手機），手機驗證是最後一步**且可跳過**（`src/pages/users/auth/Create.vue:11-15`、`PhoneVerify.vue:72`）；之後可於 `/users/verify/phone` 補綁（`routes/web.php:774`）。
- 驗證碼：4 位數字＋3 字母 ver_id，存 `users` 表欄位（`app/User.php:517-527`、`:726-742`）；**TTL 300 秒**（`User.php:637`、`:768`）；**錯 3 次失效**（`:617-620`、`:769`），訊息「驗證次數過多，驗證碼已失效」（`AuthController.php:272`、`:804`）。
- **重發規則**：成功重發→新碼覆寫、舊碼立即失效（`User.php:520/526/728/741`）；**冷卻**簡訊 120s＋每日 5 則（超量鎖到隔日；`User.php:684-699`）、Email 120s＋日上限後鎖 5 小時（`User.php:477`）；冷卻中重發直接 return false 不產碼（`User.php:512-515`、`:731-735`）。
- 重複註冊：「此帳號已註冊。」（`AuthController.php:132-137`）／「此手機已註冊。」（`:682-686`，條件 `phone_verified_at` 非空＋`is_registered=1`，`User.php:1086-1099`）。
- **「網路金鑰無效」＝reCAPTCHA sitekey 事故**：`vite.config.js:57` 註解自證（build 漏 `NOCAPTCHA_SITEKEY` → 註冊頁 Google widget 顯示「網站金鑰無效」），已加預設 key 防呆（`:60-61`）→ 歸 B.Bug 類，知識口徑=系統面事故導客服。
- 免註冊快速驗證信（房東代發）：連結 **72 小時**失效（`User.php:838-841`）；註冊頁連結=`/users/create`（`routes/web.php:773`）。

**結論**：註冊驗證排障的分支樹全部可決定性寫死（TTL/3 次/冷卻/ver_id 對碼/改走 Email 主路徑/快速驗證信 72h），無需 API。

### 主題 2：LINE 快速登入與帳號比對（jgb2 真碼）

**發現**：
- LINE SSO 綁定存 `users` 子帳號 row（`social_id`＋`social_key`＋`father_id`；`User.php:986-1001`）；callback **只查綁定 row、不做 email 歸戶**（`AuthController.php:573`、`:597-604`）→ **帳密註冊的帳號用 LINE 登入必被導去註冊畫面**，且全專案無「登入後補綁 LINE」功能 → 帳密老帳號永遠不能 LINE 快速登入，**唯一解法=改用帳密登入**（客服口徑正確，機制證實）。
- **Email 大小寫敏感＝缺陷**：email 以 xxtea 密文存放與比對（`User.php:263-275`、`:923`），大小寫不同→密文不同→查重放行→重複帳號；後台管理員登入有 `strtolower`（`Admin/IndexController.php:87`）但會員端沒有；`users.email` 無 unique 索引。客服實案完整成因鏈：LINE 導註冊→手打 email 大小寫不同→第二帳號→租客 role 無合約→看不到電表。
- 忘記密碼：Email 或 SMS 驗證碼擇一自助重設（`Password.vue:76-100`、`AuthController.php:1274-1417`）；**忘記帳號**：SMS 驗證後回**打星號 email 提示**（`AuthController.php:1419-1450`）；未綁手機只能找客服。
- 角色視角：`?role_id=` 切換（`Controller.php:512-544`），登入落點順序 `selected_role_type → default_role_id → last_role_id → 租客`（`:702-789`）——實案 31（忘記密碼後看不到公司選項）屬落點/allTeams 判定範疇。

### 主題 3：綁定唯一性與自助修改範圍（jgb2 真碼）

**自助 vs 後台判定表**（證據見 agent 報告，摘錄關鍵）：

| 項目 | 自助 | 後台 |
|---|---|---|
| 手機首次綁定（簡訊驗證） | ✅ `/users/verify/phone` | — |
| 手機換綁 | ❌ UI 無入口（API 未擋＝J 清單） | ✅ 覆蓋式（TenantInfoUpdateController） |
| Email 變更/解綁 | ❌「請聯繫 JGB 客服」（`account.blade.php:211`，input disabled） | ✅ |
| 姓名/稱謂 | ✅（**雙方簽署完成後 `is_basic_info_locked=1` 即鎖定**，`Contract.php:577-596`） | ✅ |
| 聯絡電話 phone2/地址/社群 | ✅ | ✅ |

- **藍字連動真相**（修正客服口徑）：藍字讀的是 `contracts` 快照欄位（`to_user_last_name/first_name`），**簽署時**才把帳號資料回填快照（`PaymentController.php:831-849`）→「帳號改名→藍字連動」**僅簽署前成立**；已簽合約要改走後台；簽署完成後帳號姓名還會被鎖。知識口徑必須帶這兩個但書。
- 綁定唯一性：應用層密文比對，DB 無 unique 約束；後台工具 update 端點不複驗唯一性、改手機不驗簡訊（觀察，屬 jgb2 內部風險）。
- 帳號合併（實案 32）：無此功能——後台覆蓋式變更＋申請書流程，AI 出口=資料異動申請書。

### 主題 4：團隊權限模型（jgb2 真碼）

- 團隊=法人 Role（`entity_type=2`）；成員=`role_user` pivot（`type=1`）＋`character_id` 指向 `role_characters`（每團隊一套、50+ 布林能力旗標；範本 10 角色：擁有者/最高管理者/店長/會計/高專/資深業務/一般業務/秘書/一般成員/修繕廠商，`config/character.php`）。
- **可見範圍三層**：`show_estate`（全團隊）→ `show_owner_estate`（僅被指派為經理人的物件，`Role.php:701-742`）→ 皆無＝逐筆指派（`user_biglandlords`）。新增社區需 `edit_estate`、新增合約需 `add_contract`。
- **邀請成員 bug（實案 11 真因）**：`$defaultCharacterId = null` 宣告後從未賦值，invite attach 直接寫 NULL（`UserController.php:10636`、`:11646`）；`character_id` 空→一律無權限（`Role.php:4749-4751`）→ 成員看不到社區也不能新增。**排障口徑：管理者到成員列表「變更角色」補指派**；bug 本身入 J 清單。
- 新增成員**必須**對方已註冊（查無帳號「您輸入的帳號不存在」，`UserController.php:11472-11478`）——與外部類註冊排障有天然銜接（成員加不進來→先確認對方註冊）。
- 多團隊切換：`?role_id=` 驗 `roles()∪allTeams()`；`last_role_id` 記憶落點。

### 主題 5：帳號 G 清單可行性與授權模型（jgb2 真碼）

- External API 三層授權：key（sha256/有效期）→ resource×action 權限表 → **role 白名單 opt-in**（`ExternalApiAuth.php:33-111`）；資料範圍靠 controller `where('role_id',...)`。
- **現成資料源**：`existed_lessees`（以 `lessor_role_id` 圈定業者，含 `lessee_email/lessee_registered_phone/is_lessee_user_registered`）；`GET /tenants/{user_id}/summary` 先例（`TenantApiController.php:16-45`）。
- **G-A1（以 phone/email 查名下租客註冊/綁定狀態）可行且防枚舉**：授權沿 role_id 必填＋白名單，查詢範圍天然限定該業者名下租客——把定位條件從 `lessee_user_id` 換成 phone/email 即可。〔注意：users 表 phone/email 為密文，existed_lessees 欄位加密與否需 jgb2 確認寫入路徑〕
- 順帶發現（jgb2 內部）：`GET /contracts/status-overview` 未掛 `_resource/_action`＝任何有效 key 可讀（`routes/api.php:40`）——入 J 清單提醒。
- **jgb_contracts 現值已可用**：`is_tenant_registered`、`to_user_phone/email`（`ContractApiController.php:38`，master）＋`to_user_login_email`（G2/preview）→ 登入排障免等 G 清單即可 ground。

### 主題 6：b2c 進對話機制現況（本站真碼）

- tenant 檢索雙閘：`target_user ∈ {NULL, tenant, all_users}`＋business_types 依業者業態（`vendor_knowledge_retriever_v2.py:63-81`）→ **pm-only 錨點對 tenant 不可見**；合約錨點雖標雙角色但 `business_types=['system_provider']` 在 b2c 被擋。
- config 無角色維度：`by_category` 一 category 一 config（`conversational_config.py:162-168`）；進面向後 persona_role 原樣載入（`conversational_engine.py:407`），**無依請求者換 persona 機制**。
- 潛在風險（不在本 spec 修）：tenant 帶 `mode='b2b'` 命中含 tenant 標籤錨點→以 pm persona 對租客開診斷——設計面以「帳號錨點一律 pm-only」規避新增暴露，存量風險另議。
- prospect 前門是唯一 target_user 路由先例，硬編白名單（`chat.py:591-593`），不適合本領域擴用。

### 主題 7：33 案逐案歸類（策略 A 退出條款判準）

| 歸類 | 案次 | 面向去向 |
|---|---|---|
| 機制類 16 | 3,4,5,7,8,9,10,11,14,18,20,24,26,31,32,33 | 註冊驗證 3（5,10,＋教學 4）／登入 6（8,9,24,26,31,18*）／綁定異動 5（3,7,14,32,33）／團隊權限 2（11,20,18*） |
| B.Bug 事故 11 | 1,2,6,16,19,21,23,25,27,28,29 | 識別特徵→導客服（不對話化） |
| 跨域簽約頁 4 | 12,13,15,22 | 合約域簽署排障（switch） |
| 其它 2 | 17（產品建議）,30（IoT） | 範圍外 |

**結論：策略 A 成立**（機制類 16 案足撐四面向；登入排障最厚）。

## 技術選型

### 選型 1：母分類結構
| 方案 | 優點 | 缺點 |
|---|---|---|
| **A. 一母分類「帳號中心」＋薄母層（採用）** | 面向互轉天然（母衍生 faces）、線索保留；母層只放名詞對照無污染 | 母層自律要求 |
| B. 兩母分類＋faces 明列 | 硬隔離 | 母層×2、faces 手維護、無實質收益（子層本互不疊加） |

### 選型 2：各面向 grounding 形態
| 面向 | 形態 | 依據 |
|---|---|---|
| 註冊驗證排障 | select='category' 決定性知識樹 | 當事人不在系統、機制已全證實 |
| **登入排障** | **select='api'（jgb_contracts, contract_ref）＋accounts.py builder** | is_tenant_registered/to_user_login_email 現值可判註冊狀態與帳號錯配 |
| 帳號綁定異動 | select='category'＋申請書出口骨架 | 自助/後台判定表已定案 |
| 團隊成員權限 | select='category' | 權限模型知識化（G-A2 上線後可升級） |

## 風險登記

| 風險 | 影響 | 機率 | 緩解 | 狀態 |
|---|---|---|---|---|
| 登入排障錨點與合約簽署排障誤吸 | 中 | 中 | 錨點避開「簽」字＋路由回歸雙向案例 | 開放（實作把關） |
| 3436 忘記密碼知識與新錨點重疊 | 低 | 高 | 3436 補標掛登入排障（backfill 定案） | 開放 |
| 大小寫缺陷在 jgb2 修復前，知識口徑需教「檢查 email 大小寫」 | 低 | 高 | 口徑寫「以當初註冊的確切寫法登入」＋J 清單推修 | 開放 |
| existed_lessees 欄位加密未確認 | G-A1 契約細節 | 低 | 契約文件標注待 jgb2 確認 | 開放 |

## J 清單（jgb2 缺陷回報，隨 G 契約文件交付）

1. **email 大小寫敏感**：xxtea 密文比對＝實質 case-sensitive，會員端無 lowercase 正規化（admin 端有）→ 重複帳號、租客登錯帳號（實案 9/32）。建議註冊/登入前 `strtolower(trim())` 正規化＋存量掃描。
2. **邀請成員 character_id=NULL**：`$defaultCharacterId` 未賦值（`UserController.php:10636/11646`），常數 `ROLE_DEFAULT_CAPABILITY_ID=6` 存在但未用 → 成員無權限（實案 11）。
3. **authPhone 換綁未後端擋**：已綁定用戶直接打 API 可換綁，僅 UI 擋（安全）。
4. `GET /contracts/status-overview` 未掛 `_resource/_action` 權限點。
5. （觀察）`getReSendEmailRemainSec` 以 `email_verified_at` 起算冷卻疑誤（僅變更綁定信箱流程）。

## 開放問題

1. **G-A1 契約細節**（existed_lessees 加密、比對正規化）——契約文件標待確認，存在性驅動不阻塞。
2. tenant `mode='b2b'` 進面向載 pm persona 的存量風險——本 spec 只保證新增錨點 pm-only，根治屬引擎議題另立。

## 時間軸

| 日期 | 活動 | 結果 |
|---|---|---|
| 2026-07-03 | 五路 jgb2 盤查＋b2c 盤查＋33 案歸類 | 全部定案，見上 |
