# 落差分析：billing-conversational-facets

> 分析日期：2026-07-03　基準：requirements.md（R1–R11）＋現行 codebase（contract-conversational-facets 全收案後）
> 定位：提供資訊與選項，不做最終決定；〔研究〕標記者入設計階段研究清單。

## 一、現況元件盤點（可重用，比合約開工時厚很多）

| 元件 | 現況 | 對本 spec 的意義 |
|---|---|---|
| 對話引擎全套 | face 貫穿、候選辨識、中途切換、收斂槽位保底、身分參數保底、secondary_call 宣告式機制——全部現成且已真站驗證 | **零引擎修改**的前提比合約時更穩 |
| 面向化資料路徑 | category_config 母子、三層脈絡疊加、config_for_category、persona_role 專屬鍵慣例 | 純資料複製模式 |
| **帳務決定性引擎（v1.1）** | `bills.py`：診斷分支 cannot_send／cannot_cancel／**late_fee**／manual_complete／**atm_expired（虛擬帳號過期）**＋STATUS_LABELS；`payments.py`：**payment_not_reflected（繳了未入帳）**／credit_card_failure／auto_pay_failure；`invoices.py`：issue_failure／invalid_failure | R2–R5 的核心分支**已有骨架**，落差是「意圖關鍵字分發→FACE_BUILDERS 面向分發」的升級與分支補全 |
| 既有 form_fill 診斷知識 | 6 筆（3495/3496/3498/3499 帳單＋3503/3504 發票，走 `jgb_bill_diagnosis`/`jgb_invoice_diagnosis` 表單） | R8.4 處置對象；精確問句已有可用出口 |
| API 端點 | `jgb_bills`（含 G3 is_archived、online_payment_action/method、pay_at、invoice_status）、`jgb_bill_detail(role_id+bill_id)`、`jgb_payment_logs(role_id, payment_id|bill_id)`、`jgb_invoice_logs(role_id, invoice_id|bill_id)`、`jgb_subscription`；合約 status-overview 已露滯納金設定（enable_late_fee/late_fee_percent/calc_late_fee_buffer_days） | 識別鏈以 **bill_id 為鍵**；滯納金設定 R5 免擴 API |
| 驗證 harness | 進場路由回歸測試模式、面向 e2e 模式、知識匯入/調校工具、g1-g4 契約文件模板 | R11 直接沿用擴案例 |

## 二、逐需求落差與實作選項

### R1 底座 — 落差＝純資料
新母分類 `系統帳務`＋5 子分類、脈絡 6 列、config 5 筆——照合約四件套 migration 模式。無程式落差。

### R2 繳費金流排障 — **主落差 1：帳單識別鏈**
合約用單槽 contract_ref（id/名稱後端裁判）；帳單識別更間接（使用者常說「XX 物件這期的帳單」而非帳單編號）。選項：
- **A. 單槽 bill_ref＋search_params 多層裁判**：先當 bill_id 查、查無 fallback `jgb_bills?contract_ids/keyword` 列候選（label 帶期間/金額/狀態）——沿既有模式，機制零改。
- B. 雙槽（contract_ref＋期別）：更精準但追問成本高、brain 抽取變複雜。
- C. 先鎖合約再 secondary_call 撈帳單清單：兩跳，複雜。
**傾向 A**；候選 label_fields 用 title/sub_title/date_expire/total〔研究：jgb_bills 是否支援 bill_id 直查參數〕。

### R2 — **主落差 2：金流事件證據面**
「超商已繳未轉出 vs 待對帳」分支需要金流事件欄位。現況 payment_logs 有 logs 列、bills 有 pay_at/online_payment_action；**超商轉出狀態、對帳批次時點的露出程度未知**〔研究：jgb2 Payment/對帳排程真碼→定 G 候選〕。既有 `_diagnose_payment_not_reflected`／`_atm_expired` 為分支骨架，缺的是狀態機全圖與時程證實。

### R3 帳單異常 — 落差＝builder 升級＋產生規則盤查
diagnose_bill 分支現成；「金額怎麼算的」需 bill_detail 品項組成露出程度確認〔研究〕；「帳單沒產生」需產生時點/補產規則（qa32 有口徑：起始日過去→簽完即產、比例計算）〔研究證實〕。

### R4 發票 — 落差＝builder 升級＋開立時點規則
invoices.py 現成兩分支；開立觸發（繳費後？月結？）與補開/差額後台功能邊界〔研究〕。

### R5 滯納金 — 落差最小
合約欄位已露、diagnose late_fee 現成、知識 3531/3532 現成；落差＝客製版本結算規則覆核〔研究〕＋facts 組裝。

### R6 帳單設定引導 — 落差＝純資料
select=category 同建約引導模式；一元帳單測試流程（Excel row37）為現成素材。

### R7 決定性計算 — **同構小程式落差：face 貫穿 bills 分支**
`format_jgb_response` 目前只有 jgb_contracts 分支收 face；需把 face 透傳至 jgb_bills/jgb_bill_detail/jgb_payment_logs/jgb_invoice_logs 分支＋`bills.py` 建 FACE_BUILDERS 註冊表（與 contracts.py 同構，face=None 恆等零回歸）。金額禁重算＝facts 只引存值（bills.total/final_total 為實體欄位 ✓）。

### R8 路由 — 落差＝form_fill 處置定案
6 筆 form_fill 知識的選項：
- a. 全升級掛面向（表單廢除）——對話體驗一致，但精確問句被迫多輪。
- b. 全保留並行——零風險，但同主題雙軌維護。
- **c. 混合（傾向）**：模糊起手掛新面向進對話；「為什麼發不出去」等精確診斷句保留 form_fill（它本來就是單發即答的好體驗）——與「進對話 vs 單發」準則一致。
跨域 switch 機制現成；帳務↔合約錨點互不誤吸需路由測試把關（合約錨點已在庫，帳務錨點設計時需避開「帳單封存/點退帳單」語彙——那是合約域）。

### R9–R11 — 落差＝執行工作
help 帳務文章未抓（fetch 工具改 keyword 重跑即可）；既有 27+ 筆盤點補標照合約 4.2 模式；路由/整合/e2e 測試照模式擴。

## 三、實作策略選項

| 策略 | 內容 | 權衡 |
|---|---|---|
| A. 全面向一次做 | 照合約 22 任務結構完整走 | 機制成熟風險低；research 範圍大（金流狀態機最重） |
| B. 兩波 | 先高頻雙診斷（金流排障＋帳單異常），後發票/滯納金/設定 | 快出價值；但四件套 migration 拆兩次、回歸跑兩輪 |
| C. 先升級 form_fill 再擴面向 | 最小步 | 走回頭路——form_fill 與面向雙軌期更長 |

**建議 A**（合約經驗：一次做的邊際成本低；真正的 gate 是 research 而非開發量），但 research 按面向優先序推進，金流狀態機先行。

## 四、設計階段研究清單（jgb2 真碼，file:line 證據）

1. **金流狀態機全圖**：Payment/Bill model 狀態欄位、超商/虛擬帳號金流事件、對帳排程（cron）時點——R2 分支集定案的前提。
2. 帳單產生/補產時點規則（週期、發送日、起始日在過去）。
3. bill_detail 品項組成、payment_logs/invoice_logs 露出欄位全清單 → 帳務 G 清單定案。
4. 發票開立觸發與補開/差額/作廢後台功能邊界。
5. 滯納金四版本結算規則覆核（對 3531/3532）。
6. jgb_bills 識別參數支援面（bill_id 直查？期別過濾？）→ R2 識別鏈選項 A 可行性。
