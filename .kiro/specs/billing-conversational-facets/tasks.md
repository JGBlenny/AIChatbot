# 實作任務：billing-conversational-facets（帳務領域對話面向擴充）

> 建立時間：2026-07-03
> 需求：requirements.md（R1–R11）｜設計：design.md（v1.0，五路盤查後定案）｜落差：gap-analysis.md｜研究：research.md（§一金流 §二產生 §三發票 §四滯納金 §五API/分支風險 §六修正結論）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後（G-gated 或後補覆蓋）
> 鐵律：TDD（先紅後綠）；面向字面只准出現在資料列與 `services/jgb/` 領域檔；合約 6 面向/既有 form_fill/售前零回歸；facts 決定性算、**金額只引用存值禁重算**；口徑衝突以 research 為準

## 1. face 透傳帳務分支＋BILL_FACE_BUILDERS 底座（先做）

- [x] 1.1 `jgb_response_formatter.py` 四個帳務分支（jgb_bills/jgb_bill_detail/jgb_payment_logs/jgb_invoice_logs）補 face 透傳；`services/jgb/bills.py` 建 `format_bill_response` 入口＋`BILL_FACE_BUILDERS` 佔位註冊表——face 命中 → builder；未命中/None → 現行 diagnose 路由與通用格式化。含型別定義。
  - 需求：1.4, 7.1, 11.1
- [x] 1.2 單元測試（先紅後綠）：face=None／未註冊 → 輸出與現行完全一致（既有 diagnose 測試不改一字全綠）；face 從引擎 state 傳抵 bills.py（沿 test_face_param_threading 模式）。
  - 需求：11.1

## 2. 識別 adapter（診斷面向共同前置）

- [x] 2.1 `jgb_system_api.get_bills` 擴充 `bill_ref` 識別語意參數（TDD）：純數字 → `get_bill_detail` 直查包成單筆列；查無/非數字 → 經 `get_contracts`（keyword/ids）解析 contract_id → `bills?contract_id` 回列。單元測試三路＋降級（解析失敗回空列不拋）＋既有呼叫零回歸。
  - 需求：2.1, 7.3
- [x] 2.2 候選展示整合驗證：result_mapping 讀 title/sub_title/date_expire/total 組候選 label（日期格式化沿 label_date_fields；金額原樣）；同合約多期帳單可依 label 區分選擇。
  - 需求：2.1, 3.1

## 3. 四個 fact-builder（TDD，1.1 佔位接入後可平行）

- [x] 3.1 (P) `build_payment_flow_facts`（繳費金流排障）：status/bit 解碼（1/32/2/8/16/64）；status=8＋超商通道 → 撥付逢 5/15/25 時程 facts；status=2 無 pay_at → 查無繳費引導核對；金額不符異常/無分支 → 導客服附事實（帳單編號/狀態/最後金流事件）；attach `payment_logs` 存在性驅動（缺不虛構）；VA 效期欄位存在才判（G）。單元測試狀態×通道×attach 有無矩陣。
  - 需求：2.2, 2.3, 2.4, 7.1, 7.4
- [x] 3.2 (P) `build_bill_anomaly_facts`（帳單異常）：金額類逐項列存值（品項/金額/期間/rate，禁重算）；缺漏類（提前一月產生閘/過去起始補產/封存）；可見類三條件機械判（payer＋READY＋active）；封存/點退範疇 → 導合約域共用出口 facts。單元測試判因矩陣。
  - 需求：3.1, 3.2, 3.3, 3.4, 7.2
- [x] 3.3 (P) `build_invoice_facts`（發票）：invoice_status（0/1/2）×Invoice.status（0–4）×**number 空=失敗**判準；分類器七類語意 facts；設定未啟用 → 指出設定位置（帳單/合約/團隊層級）；開立時點依 invoice_mode 三軌；補開/作廢條件（已有有效發票/未付款拒絕）；不虛構號碼日期。單元測試含 attach invoices/invoice_logs 有無。
  - 需求：4.1, 4.2, 4.3, 4.4, 7.4
- [x] 3.4 (P) `build_late_fee_facts`（滯納金）：**兩機制分流**——延遲金版（付款後公式：租金×(付款日−期限−緩衝)×費率）vs 排程版（未付款開單：階梯/固定額，各自到期日與逾期標記差異）；合約滯納金欄位存在性驅動（G：preview 三欄）；金額引用結算存值；個案減免導客服。單元測試兩機制×欄位有無矩陣。
  - 需求：5.1, 5.2, 5.3, 7.4

## 4. 面向資料四件套（migrations）

- [x] 4.1 (P) `add_billing_facet_categories.sql`：category_config 母 `系統帳務`＋5 子分類（冪等）；整合驗證 `_domain_faces` 含 5 面向。
  - 需求：1.1
- [x] 4.2 (P) `seed_billing_facet_system_context.sql`：系統脈絡 6 列（母：帳單狀態機表＋名詞對照「待對帳=已繳未入帳」；5 子各 300–600 字，內容以 research §一–§四撰寫——金流排障含超商撥付時程、異常含可見三條件、發票含三軌時點與失敗分類、滯納金含兩機制、設定引導含分流框架與一元帳單測試）；長度預算自檢 ≤4500。
  - 需求：1.3, 1.5
- [x] 4.3 (P) `seed_billing_facet_configs.sql`：對話 config 5 筆（persona_role 用 `pm_billing_*` 專屬鍵；4 診斷 select='api' endpoint=jgb_bills＋required_slots=[bill_ref]＋search_params；金流排障宣告 secondary_call→jgb_payment_logs、發票宣告 secondary_call→jgb_invoices；`帳單設定引導` select='category'）；persona 各寫面向差異（金流排障確認「繳了沒入帳」現象、異常確認異常型態、發票直趨收斂、滯納金未鎖定走單發、設定引導兩輪分流＋涉現況 switch）＋「API 現值為準、金額只引用不計算」紅線。
  - 需求：1.2, 1.6, 2.5, 5.4, 6.1, 6.2, 7.2
- [x] 4.4 整合測試：五面向 config_for_category 進場；三層脈絡疊加正確且不含售前與合約層；面向內切換保留已鎖定帳單不重問；設定引導 scope=switch；secondary_call attach 生效；全程零引擎修改驗證。
  - 需求：1.2, 1.3, 1.4, 7.5, 8.1

## 5. 知識工程（4 完成後可與 6 交錯）

- [x] 5.1 (P) help 中心帳務素材抓取：fetch 工具改帳務關鍵字重跑（一次性腳本，不 commit）。
  - 需求：9.1
- [x] 5.2 (P) 既有知識盤點＋補標：帳務 27+ 筆逐筆歸屬主面向或維持單發（互斥）→ 人工確認清單 → backfill migration；**form_fill 6 筆混合制落定**（精確診斷句維持 form_fill、不掛面向）。
  - 需求：8.4, 9.2
- [x] 5.3 各面向知識產製：Excel 官方回覆 11 則＋回測缺口清單＋help 素材轉製；**修正 3531/3532（滯納金兩機制）與虛擬帳號過期歸因知識**；question 短關鍵字、answer 先述情境；target_user/業態隔離；全部進審核流程。
  - 需求：9.1, 9.3, 9.4
- [x] 5.4 錨點知識＋進場路由回歸擴充：每面向模糊起手句（一種講法一筆，避開合約域語彙如封存/點退）；`test_facet_entry_routing_req.py` 擴帳務案例——錨點進對話＋教學/制度單發＋**與合約錨點互不誤吸雙向驗證**；紅→調→綠。
  - 需求：8.3, 11.2

## 6. 金流排障全流程＋端到端

- [x] 6.1 整合測試（真 DB＋stub jgb2 參數感知）：追問識別→adapter 三路鎖定→secondary attach→分支 facts 正確（超商時程/查無繳費/金額異常導客服）；跨域 switch 雙向（帳務→合約、合約→帳務）。
  - 需求：2.1, 2.2, 2.3, 8.2, 11.5
- [x] 6.2 e2e（preview 真服務＋真 LLM＋真 jgb2）：每面向口語第一句進場（正常管線含 reranker）；金流排障多輪真資料；G 缺欄位降級不阻斷；**金額原樣 token 斷言**（facts 中金額出現於回答且未被改寫）；進對話 vs 單發各一例。
  - 需求：7.4, 8.3, 11.3

## 7. 回歸＋部署

- [x] 7.1 回歸：合約 6 面向／既有 form_fill 診斷／售前全綠（unit＋integration＋e2e 全套重跑）；進場路由全案例（合約＋帳務）綠。
  - 需求：11.1, 11.2
- [ ] 7.2 部署執行（依 design.md 順序）：migrations → 知識匯入（審核後）＋3531/3532 修正 → reranker semantic model 重建 → 清快取 → 煙囪驗證（每面向一句真跑）。
  - 需求：11.4

## 8. 外部依賴（G-gated，可延後）

- [x] 8.1 帳務 G 清單契約文件交付 jgb2：research §五候選表（含 **preview→master 併版清單**與 bills `status` 欄補正 bug、VA/超商效期、payment-logs 過濾分頁、invoice-logs 個資白名單化）。
  - 需求：10.1, 10.3, 10.4
- [ ]* 8.2 G 欄位上線後：VA 效期／取號狀態完整分支真資料驗證（3.x 存在性驅動已備，僅補 e2e）。**滯納金屬客製功能，真資料補驗排除（使用者定案 2026-07-04）**。
  - 需求：10.2
