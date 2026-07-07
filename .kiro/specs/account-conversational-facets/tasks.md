# 實作任務：account-conversational-facets（註冊登入/帳號領域對話面向擴充）

> 建立時間：2026-07-03
> 需求：requirements.md（R1–R10）｜設計：design.md（v1.0）｜落差：gap-analysis.md｜研究：research.md（主題 1 驗證碼 主題 2 登入 主題 3 綁定 主題 4 權限 主題 5 G/J 主題 6 b2c 主題 7 歸類）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後（G-gated）
> 鐵律：TDD（先紅後綠）；面向字面只准出現在資料列與 `services/jgb/` 領域檔；合約 6＋帳務 5 面向/售前/form_fill 零回歸；機制數字（300s/3 次/120s/72h）以 research 為準寫死、LLM 不得自創；**驗證碼值絕不經 AI 輸出**；個案資訊（電話/信箱/公司名）不進知識庫

## 1. accounts.py 領域檔＋face 分發底座（先做）

- [x] 1.1 `services/jgb/accounts.py` 建檔：`ACCOUNT_FACE_BUILDERS` 註冊表＋`build_login_trouble_facts`——由合約現值決定性判三分支（is_tenant_registered=False → 未註冊引導（含快速驗證信 72h）；True＋to_user_login_email 與邀請 email 不一致 → 疑似登錯帳號/多帳號；一致 → 帳號正常轉角色視角/密碼路徑）；欄位缺失存在性降級（僅註冊分支）；密文/非 email 格式視同不可用（沿 G2 教訓）；email 遮罩沿 `_mask_email`。`jgb_response_formatter` 的 jgb_contracts face 分發讓「登入排障」route 至本檔；face=None/未註冊 → 原路恆等。含型別定義。
  - 需求：3.3, 6.1, 6.4, 6.5
- [x] 1.2 單元測試（先紅後綠）：builder 全分支矩陣（未註冊/錯配/一致/欄位缺失/密文）＋face=None 恆等（既有 contracts 面向測試不改一字全綠，mutation 證明）＋email 遮罩斷言＋紅線斷言（輸出不含 4 位驗證碼樣式內容）。
  - 需求：6.2, 10.1

## 2. 面向資料四件套（migrations）

- [x] 2.1 (P) `add_account_facet_categories.sql`：category_config 母 `帳號中心`＋4 子分類（`註冊驗證排障`/`登入排障`/`帳號綁定異動`/`團隊成員權限`，冪等）；整合驗證 `_domain_faces` 含四面向（互轉天然成立）。
  - 需求：1.1, 7.1
- [x] 2.2 (P) `seed_account_facet_system_context.sql`：系統脈絡 5 列——母薄層 ~150 字（名詞對照：主/子帳號、綁定、角色視角、團隊/成員/角色＋代問模式一句，**不含兩類機制細節**）；4 子各 300–600 字依 research 主題 1–4 撰寫（註冊驗證：Email 主路徑/TTL 300s/錯 3 次/冷卻 120s 重按不產碼/ver_id 對碼/快速驗證信 72h/B.Bug 特徵導客服；登入：帳密帳號不能 LINE 快速登入→改帳密/「確切寫法」口徑/忘記密碼雙路徑/忘記帳號星號提示/角色視角；綁定異動：自助 vs 後台判定表/藍字兩但書（簽署前連動、簽署後鎖定）/申請書骨架；團隊權限：成員需先註冊/可見範圍三層/成員列表「變更角色」/自查路徑）；長度預算自檢 ≤4500。
  - 需求：1.3, 1.5, 2.2, 2.5, 3.2, 4.1, 5.1, 5.3
- [x] 2.3 (P) `seed_account_facet_configs.sql`：對話 config 4 筆（persona_role 用 `pm_account_*` 專屬鍵）——`登入排障` select='api' endpoint=jgb_contracts＋required_slots=[contract_ref]；其餘三面向 select='category'；外部類 persona 寫代問模式（給業者可執行動作＋可轉述租客的指引）、內部類寫業者自身操作；分流問句各面向差異（註冊驗證：管道×現象至多兩輪；綁定異動：自助/後台分流→申請書出口；團隊權限：判因分流）；answer_rules 紅線（不輸出驗證碼值/不代辦後台操作/不建議分身帳號/不承諾處理時效/查不到時誠實導客服附線索摘要/申請書關鍵 token/email 手機遮罩）。
  - 需求：1.2, 1.6, 1.7, 2.1, 2.3, 3.1, 4.2, 4.3, 4.4, 5.4, 6.2, 6.3
- [x] 2.4 整合測試：四面向 config_for_category 進場；三層脈絡疊加正確、**外部面向脈絡不含內部類關鍵詞（反之亦然）**、不含售前/合約/帳務層；面向互轉（「已註冊過」→ 綁定異動）已蒐集線索保留不重問；登入排障 identify→ground→三分支 facts；跨域 scope=switch（簽約頁話題 → 合約簽署排障）；全程零引擎修改驗證。
  - 需求：1.2, 1.3, 1.4, 3.4, 7.1, 7.2

## 3. 知識工程（2 完成後可與 4 交錯；含人工確認閘門）

- [x] 3.1 (P) help 中心帳號素材抓取：fetch 工具改帳號關鍵字（註冊/登入/驗證/綁定/成員/權限/密碼）重跑（一次性腳本，不 commit）。
  - 需求：8.1
- [x] 3.2 (P) 既有知識盤點＋補標：帳號管理 10 筆逐筆歸屬主面向或維持單發（互斥；預判 3436→登入排障、3437→帳號綁定異動、3439/3544-3547→團隊成員權限、3435/3438/3440 維持單發教學）；target_user 雙角色之 b2c 配置一併定案 → 人工確認清單 → backfill migration。
  - 需求：8.2
- [x] 3.3 各面向知識產製：機制類 16 案理解情境後轉製（個案電話/信箱/公司名剝除）＋help 素材；機制口徑以 research 為準（大小寫寫「以當初註冊的確切寫法」、藍字帶兩但書、成員無權限指向「變更角色」）；question 短關鍵字、answer 先述情境；全部進審核流程。
  - 需求：2.5, 8.1, 8.3, 8.4, 8.5
- [x] 3.4 錨點知識＋進場路由回歸擴充：每面向口語起手句 1–2 筆（自 33 案措辭取材，**target_user=['property_manager'] only**，避開「簽」「帳單」強詞）；`test_facet_entry_routing_req.py` 擴帳號案例——錨點進對話＋教學/制度單發＋**三組誤吸邊界點名覆蓋**（登入排障 vs 合約簽署排障雙向、3436 重疊處置後不誤吸、「看不到帳單」歸帳務域）；紅→調→綠。
  - 需求：7.3, 7.4, 10.2

## 4. 全流程＋端到端

- [x] 4.1 整合測試（真 DB＋stub jgb2 參數感知）：登入排障全流程（現象起手→追問合約識別→候選→ground→三分支 facts）；註冊驗證排障兩輪分流→分支收斂；B.Bug 特徵句 → 導客服不進個案排障；綁定異動 → 申請書出口內容（關鍵 token）；團隊權限判因分流。
  - 需求：2.1, 2.4, 3.1, 3.2, 4.2, 5.1, 5.2
- [x] 4.2 e2e（preview 真服務＋真 LLM＋真 jgb2）：每面向口語第一句進場（正常管線含 reranker）；登入排障真資料多輪（preview 合約 is_tenant_registered 實值）；**機制 token 斷言**（「5 分鐘」「三次」「確切寫法」出現且未被改寫）；申請書出口 token；跨域 switch（帳號→合約簽署排障）至少一例；進對話 vs 單發各一例；G 缺欄位降級不阻斷。
  - 需求：2.2, 6.3, 6.4, 10.3, 10.5

## 5. 回歸＋部署

- [x] 5.1 回歸：合約 6 面向／帳務 5 面向／售前／既有 form_fill 全綠（unit＋integration＋e2e 全套重跑）；進場路由全案例（合約＋帳務＋帳號）綠。
  - 需求：10.1, 10.2
- [ ] 5.2 部署執行（併入統一部署 runbook）：migrations → 知識匯入（審核後）＋10 筆補標 → reranker semantic model 重建 → 清快取 → 煙囪驗證（每面向一句真跑）。
  - 需求：10.4

## 6. 外部依賴（交付 jgb2；G-gated 可延後）

- [x] 6.1 帳號 G/J 契約文件交付 jgb2：G-A1（以 phone/email 查名下租客註冊/綁定狀態——existed_lessees 資料源、role_id 圈定防枚舉、tenants:read 權限點、加密欄位待確認標注）＋G-A2（團隊成員權限查詢）＋**驗證碼查詢明文排除聲明**；J 清單 5 條（email 大小寫/invite character NULL/authPhone 未擋/status-overview 權限點/Email 冷卻起算）。
  - 需求：9.1, 9.2, 9.3, 9.4
- [x] 6.2 G-A1 上線後：登入排障 grounded 升級完成（secondary_call→jgb_tenant_registration，found 歸屬閘門＋is_registered/email_verify 三態排查，嚴格遮罩 name/user_id 不出口；unit+integration+e2e 真 preview 全綠）。**團隊權限 grounded 待「成員 email→user_id 解析」（G-A2 消費缺口）另補**。
  - 需求：9.2
