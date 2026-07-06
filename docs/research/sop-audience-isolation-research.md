# 研究記錄：sop-audience-isolation

> 日期：2026-07-04　方法：AIChatbot 檢索鏈實測（file:line）＋jgb2 真碼平行盤查（agent）
> 定位：設計與補位知識產製的唯一事實來源。

## 摘要（定案清單）

| # | 問題 | 定案 | 證據 |
|---|---|---|---|
| 1 | 檢索漏斗 | 兩路徑匯進 `VendorSOPRetrieverV2.retrieve()` 單點；SQL 兩塊（向量 :104／關鍵字備選 :184）加謂詞即全覆蓋；比分在檢索後 → SQL 過濾天然在比分前 | vendor_sop_retriever_v2.py、chat.py:1572/1591、sop_orchestrator.py:145 |
| 2 | orchestrator 穿線 | `process_message`（:58）簽名無 target_user，但兩個呼叫端（chat.py:1678 B2C 並行、:520 報修觸發）都有 `request.target_user` 現成——加 optional 參數穿線即可 | sop_orchestrator.py:58-68、chat.py:520/1678 |
| 3 | 未帶 target_user 流量 | `VendorChatRequest.target_user` 為 **Optional（None）**——未帶流量真實存在 ⇒ NULL 請求語義採**選項 A：不過濾**（R2.5 向下相容）；不沿 KB 的 None→tenant 正規化 | chat.py:3397-3410 |
| 4 | platform 同構缺口 | `vendor_sop_items.template_id → platform_sop_templates`（vendors.py:706 JOIN、:1023 從範本建立）——platform 範本無 target_user，複製建立的 item 也不會有 ⇒ **同構缺口確認，掛帳另案**（vendor 端欄位為權威，本 spec 只修 vendor 端） | routers/vendors.py:704-1023 |
| 5 | 過濾謂詞 | `(si.target_user IS NULL OR %s = ANY(si.target_user))`——排除語義；tenant 請求在回填後（絕大多數列=['tenant']）命中集合不變，零回歸資料面成立 | 沿 knowledge_base 慣例 |

## jgb2 真相三題（補位知識口徑，agent 盤查 file:line 齊）

### ① 租客繳租支付方式（SOP 1256「信用卡」口徑裁決：**真，但條件式**）
- 權威枚舉 `Payment.php:352-470 manufacturerActionLists()`：藍新（信用卡/Google Pay/Samsung Pay/ATM/超商代碼/信用卡自動扣款）、國泰世華（ATM/超商條碼）、永豐（信用卡/ATM）、中信（轉帳Pay/ATM）、愛金卡（icash Pay）、台大金流（信用卡/ATM）；另有線下現金/匯款與儲值金扣抵。
- **前提**：業者收款設定啟用對應通道（RolePayment.php:13-36 旗標：credit_card_active/atm_active/cvs_active…）——知識口徑必須寫「視業者收款設定而定」。
- **LINE Pay 與 Apple Pay 不支援**（客服模組 METHOD_MAP 僅顯示映射非實際通道）——知識不得列入。

### ② 電費計收模式（contracts.fees『電費』鍵，6 模式）
建約「租金費用」步驟設定：租金已包含（rent_include）／租客自繳（self）／每月固定金額（unit=month＋amount）／按度數計（unit=meter＋amount，可設夏季電價 summer_amount）／依當期每度平均電價（average_price）／**依儲值電錶設定（topup_meter，即台科電儲值模式）**，另可自訂文字。證據：Estate.php:1748-1755、ContractController.php:10380-10427、Contract.php:6348-6365。儲值電錶模式收款方式限信用卡/ATM/現金（rent/Index.jsx:317-321）。

### ③ 統編發票（合約層級，B2B 自動判定）
- 設定位置：建約/編約「稅務與發票」步驟填**買受人統編＋抬頭**，存 `contracts.invoice_info`（buyer_ubn/buyer_name，ContractController.php:10633-10642）——是合約層級，非租客個資、非單張帳單。
- 開票判定：buyer_ubn＋buyer_name 齊備 → 自動開 **B2B 發票（強制紙本）**；否則 B2C（ezPay 載具）——Bill.php:17048-17053、16968-16972。
- 事後補改：合約發票設定可改（影響後續發票）；**已開立的發票要改統編需作廢重開**（後台客服 InvoiceSupplementController voidInvoice:1181/resetInvoice:1239），無法直接改號。

## 回填工序定案

- 規則預判：內容含租客向口吻特徵（「管理師」「您的房東」等稱謂）→ 預標 tenant（370 筆）；無特徵 37 筆逐筆人工欄。
- 審表必列：4 實彈（1256/1193/1285/1268——預期全 tenant）＋修繕 1166（預期 tenant）＋370 筆抽樣複核欄（每 vendor 抽 10）。
- 載體：審表 → 人工閘門 → `backfill_sop_target_user.sql`（id 清單式、冪等、不動 content/embedding）。

## 風險補充

- SOP 主戰場在 B2C（租客）——過濾對 tenant 請求的謂詞開銷極小（407 筆小表）；效能非議題。
- 補位知識先於過濾部署（runbook 順序註記），避免空窗。
