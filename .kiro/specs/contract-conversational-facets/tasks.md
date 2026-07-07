# 實作任務：contract-conversational-facets（合約領域對話面向擴充）

> 建立時間：2026-07-02
> 需求：requirements.md（R1–R11）｜設計：design.md（v1.0＋審查 3 修正）｜落差：gap-analysis.md｜研究：research.md（§六 申請書、§七 收斂、§八 設計定案）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後（G-gated 或後補覆蓋）
> 鐵律：TDD（先紅後綠）；面向字面只准出現在資料列與 `services/jgb/contracts.py`；狀態判斷/售前零回歸；facts 決定性算、LLM 只轉述

## 1. face 參數貫穿（基礎鏈路，先做）

- [x] 1.1 選配參數貫穿三簽名：`conversational_engine.py::_ground_by_api` 呼叫 `execute_api_call` 補傳 `user_input=user_message`、新增 `face=state.get("face")`；`api_call_handler.py::execute_api_call` 與 `jgb_response_formatter.py::format_jgb_response` 各加 `face: str | None = None` 透傳（不解讀）；`services/jgb/contracts.py::format_contract_response` 加 `face` 參數。全部預設 None。
  - 需求：2.2, 3.1, 6.1, 7.1
- [x] 1.2 單元測試（先紅後綠）：face=None／face 未註冊 → 輸出與現行完全一致（既有狀態判斷矩陣測試不改一字全綠）；face 值從引擎 state 一路傳抵 contracts.py。
  - 需求：11.1

## 2. FACE_BUILDERS 與四個 fact-builder（TDD，佔位註冊表接入後各 builder 可平行）

- [x] 2.1 `FACE_BUILDERS` 註冊表接入 `format_contract_response`：face 命中 → builder；未命中 → 現行意圖關鍵字/狀態路由。含 `CheckResult`／`FaceBuilder` 型別定義。
  - 需求：7.1, 11.1
- [x] 2.2 (P) `build_change_exit_facts`（合約異動三出口）：status==1→可直接編輯＋路徑；status∈{2,4}→取消退回（主路徑保留租客資料）；status>=8→不可直改、複製重建或異動申請書；附「藍字不可改 vs DB 可調＋不一致風險」事實。單元測試全 status 矩陣。
  - 需求：2.2, 2.6, 7.1
- [x] 2.3 (P) `build_closeout_facts`（退租收尾步驟鏈）：以 bit 256/512→64/128→封存→轉歷史排程時點 判定當前步驟與下一步；重用 `check_can_move_out`（點交點退互不相依）；提前解約未發起→發起路徑＋回簽效期 30 天＋帳單封存提醒；封存步驟輸出通用指引（G3 前常態）；逾期未轉歷史→導客服 facts。單元測試旗標組合矩陣。
  - 需求：3.1, 3.2, 3.3, 3.4, 3.5, 7.4
- [x] 2.4 (P) `build_sign_facts`（簽署排障）：bit 4/8 →「還差誰簽」；`to_user_email/phone` → 發送通道；`to_user_connect` → 綁定狀態；G1 欄位存在 → 效期判斷＋過期自動退回並清租客資料說明；G2 欄位存在 → 登入信箱錯配比對（遮罩輸出）；欄位缺 → 略過分支不虛構。單元測試含 G1/G2 有無欄位矩陣。
  - 需求：6.1, 6.2, 6.3, 6.4, 7.4, 10.3
- [x] 2.5 (P) `build_renew_facts`（續約）：`date_end` 剩餘天數；可否系統續約（雙簽完成＋未過期）；`is_tenant_registered` → 免註冊單方確認／已註冊重簽（72h）；G4 `is_newest` 存在且 =0 → 已被續約提示；`father_id` 鏈 facts。單元測試含 G4 有無欄位。
  - 需求：4.1, 4.3, 4.5, 10.3

## 3. 面向資料四件套（migrations）

- [x] 3.1 (P) `add_contract_facet_categories_v2.sql`：category_config 加 5 子分類（parent=`系統合約`，冪等）；整合驗證 `_domain_faces` 自動含 6 面向。
  - 需求：1.1, 8.1
- [x] 3.2 (P) `seed_contract_facet_system_context.sql`：系統脈絡 5 列（`categories=[<面向>]` 各一列，300–600 字；`合約異動` 列含申請書三段格式骨架與團隊擁有者提示；內容以 research.md §二–§六 ground truth 撰寫）；長度預算自檢（base＋母＋最長子 ≤4500）。
  - 需求：1.3, 1.5, 2.4, 2.5, 2.6
- [x] 3.3 (P) `seed_contract_facet_configs.sql`：對話 config 5 筆（`topic_scope.category=<面向>`；4 診斷面向 `grounding_scope.select='api'` 沿用狀態判斷參數形狀；`建約引導` select='category'）；persona 規則各寫面向差異——合約異動追問「要改什麼」＋申請書槽位（異動項目/異動前/異動後）、退租收尾確認退租型態、續約直趨收斂、建約引導兩輪分流＋「涉及特定合約現況→scope=switch」＋特殊個案導客服、簽署排障確認現象＋自助排查收斂導客服；皆含「API 現值為準」原則。
  - 需求：1.2, 2.1, 5.1, 5.3, 5.4, 5.6, 6.5, 7.2
- [x] 3.4 整合測試：五面向 config_for_category 進場；三層脈絡疊加正確且不含售前；面向內 face 切換保留已鎖定合約不重問；建約引導 scope=switch 關會話重路由；全程零引擎程式修改驗證（新面向純資料成立）。
  - 需求：1.2, 1.3, 1.4, 8.1, 8.2

## 4. 知識工程（3 完成後可與 5/6 交錯）

- [x] 4.1 (P) help 中心素材抓取：公開 API（getGroups/post）抓「新手上路」「常見問題」合約相關 45 篇全文轉純文字素材（一次性工具腳本，不 commit）。
  - 需求：9.1
- [x] 4.2 (P) 既有知識盤點＋補標：既有 JGB 合約類知識逐筆歸屬主面向（一筆一主面向互斥；具體操作問句維持單發不掛面向）→ 人工確認清單 → `backfill_contract_knowledge_facet_categories.sql`。
  - 需求：9.3, 11.2
- [x] 4.3 各面向知識產製（8–15 筆/面向）：官方文章為主幹＋Excel 真實問法為邊界；question_summary 短主題關鍵字、answer 先述情境再帶條件；與程式盤查衝突處以 research.md 為準（續約配額真因、免註冊不重簽、取消保留租客資料路徑差異）；共同承租話術與條款法律 QA 掛 `建約引導`；target_user/業態隔離；全部進審核流程。
  - 需求：5.5, 9.2, 9.3, 9.4, 9.5
- [x] 4.4 錨點知識：每面向模糊起手問法（自 Excel 真實問句取材）掛面向分類；具體操作問句不掛（進對話 vs 單發準則）；「合約」口語第一句進場既有保證不回歸。
  - 需求：8.3

## 5. 合約異動樹全流程（申請書出口）

- [x] 5.1 整合測試：追問「要改什麼」→ 鎖定合約 → 三出口 facts 正確分流 → 已簽分支收集申請書槽位（缺→追問；齊→收斂）→ 收斂產出含可抄錄申請內容＋範本＋提交指引；「編輯不了」先分流狀態擋 vs 權限擋；轉歷史/刪除訴求走共用出口。
  - 需求：2.1, 2.2, 2.3, 2.4, 2.7
- [x] 5.2 申請書產出格式 e2e 斷言：關鍵 token（`service@jgbsmart.com`、「異動前」「異動後」、合約 ID、團隊擁有者提示於團隊管理者情境）。
  - 需求：2.4, 2.5

## 6. 回歸＋端到端（正常管線）＋部署

- [x] 6.1 回歸：既有 conversational 測試全綠（unit 464/int 58/e2e 全綠）；檢索回歸改聚焦驗證——80% 舊基準經查為失效 harness（Run 285–288 盤查），以「非合約對照組 69.5% 無異常＋進場路由回歸測試 24 案（誤進場調校收斂，routing-tuning.md）」取代；正式兩段式基準另案立項。
  - 需求：11.1, 11.2
- [x] 6.2 e2e（容器內真服務＋真檢索＋reranker＋真 jgb2 API）：每面向口語第一句進場（意圖分類→檢索→reranker→config_for_category→引擎）；收斂後同面向追問（指涉/換識別）會話續存；scope=switch／會話結束後下一句回正常管線；進對話 vs 單發各驗一例；grounding 缺欄位（G1–G4 未上線）降級不阻斷。
  - 需求：7.3, 7.4, 8.3, 11.3, 11.4, 11.5
- [ ] 6.3 部署執行（依 design.md 順序）：migrations 1–4 → 知識匯入（審核通過後）→ **reranker semantic model 重建** → 清系統脈絡快取；部署後煙囪驗證（每面向一句真跑）。
  - 需求：11.6

## 7. 外部依賴（G-gated，可延後）

- [x] 7.1 G1–G4 欄位契約文件交付 jgb2 端（status-overview 加 6 欄、bills 加 2 欄；design.md API 設計節）。
  - 需求：10.1
- [x]* 7.2 G1/G2 上線後：簽署排障完整分支真資料驗證（效期判斷、信箱錯配遮罩）——程式已備（2.4 存在性驅動），僅補 e2e。
  - 需求：6.3, 6.4, 10.2, 10.3
- [x]* 7.3 G3 上線後：`secondary_call` 通用機制實作（grounding_scope 宣告、單筆收斂後執行、attach 給 formatter）＋退租收尾封存個人化 facts＋測試。
  - 需求：3.3, 10.2, 10.3
- [x] 7.4 G5 上線後（jgb2 permissions 端點 edit_contract 旗標滿足，2026-07-04）：contract_change config 加 secondary_call→jgb_member_permissions（user_id={session.user_id}），`build_change_exit_facts` 權限層三分支（無權限→權限擋明示／有權限+READY→確認非權限／有權限+狀態擋→分流明示）；存在性驅動：session user_id 非 jgb2 成員→查無 skip、現行輸出恆等（e2e 常態）。**完整啟用待 JGB Web 把登入成員 user_id 傳入 AI session**。
  - 需求：2.3, 10.3
