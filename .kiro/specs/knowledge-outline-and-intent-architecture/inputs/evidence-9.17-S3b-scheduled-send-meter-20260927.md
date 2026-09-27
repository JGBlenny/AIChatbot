# Plan 9.17 S3b 證據表：排定發送與空白度數

> 程式基準：jgb2 釘住匯出 `scratchpad/jgb2-b2ee2ac/`。本表只陳列證據；⛔ 主 session 裁決。本計畫不改任何細目（兩條都已審）。

## 1. 兩條細目現行正本（`rag-orchestrator/canon/jgb/E.md`）

- **A＝`jgb/E/bill-power-reading-draft-defaults`**（已審）：草稿帳單電費度數預設空白；編輯頁電費列有「取得即時電錶度數」按鈕，物件有綁定智慧電錶時可帶入，未綁定則提示此物件未綁定智能電表；部分特定合作團隊沒有這個按鈕。**——現行內容沒有談排定發送。**
- **B＝`jgb/E/bill-scheduled-send-rule`**（已審）：句 2「只有已經填寫完，或本來就沒有水電、瓦斯度數細節要填的帳單，才能執行批次排定發送。」來源 `code:src/pages/bills/pick/Index.jsx`。

⇒ 9.16 抽驗所說的「A 與 B 矛盾」，前提已不成立：A 在 9.16 S2 被改寫後不再提排定發送。真正要問的是 **B 句 2 是否完整**（以及帳本 `#p914-power-reading-draft` 與 B 是否一致）。

## 2. 程式證據

| # | 命題 | 證據（檔案＋可 grep 符號） |
|---|---|---|
| E1 | 挑選頁的「只有已填寫完…」是畫面提示文字 | `src/pages/bills/pick/Index.jsx`：`case 'bulkScheduled':` 下 `t('只有已填寫完或沒有水電/瓦斯度數細節的帳單才能執行批次發送功能，我們將於每日 12:00 將選取的帳單統一發送給租客。（建議先執行批次填入生活費用後再進行排定發送帳單）')`；送出鈕 `allowSubmit` 只看 `pickedIds?.length > 0` |
| E2 | 挑選清單不依度數過濾 | `app/Http/Controllers/BillController.php` 挑選 `case 'bulkScheduled':` 的 `$conditions` 只有 `owner_role_id`／`active`／`status => Bill::BILL_PREPARE`／`type`／`sort` |
| E3 | 真正排入時後端會檢查度數 | 同檔排入動作 `case 'scheduled':` ⇒ `if (!$bill->canSchedule())` 擋下；`app/Bill.php` `canSchedule()` ＝ `unfinishedDetailsJudgment(unfinishedDetails())` ＆ `canSend()` ＆ 非設算息 |
| E4 | **例外**：唯一未填的是「電費」且物件綁定 IoT 電錶、讀得到讀數 ⇒ 視為完成、可排入 | `app/Bill.php` `private function checkIotBill(`：`if (count($unFinishDetails) != 1) return false;`、`$item->name != '電費'` ⇒ false、`Iot::getPowerMeterOfBindingEstate(...)` 查無 ⇒ false、讀數空 ⇒ false，否則 `// 讀數可取得即視同可完成；度數…改由 prepareIotMeterForSend() 於排入排定發送清單當下…與發送瞬間…補值` `return true` |
| E5 | 排入當下與中午發送時補抓空白 IoT 電費度數；補不到或 0 度則不送出 | `BillController.php` `// 人工排入排定發送清單時也補入 IoT 電費度數`＋`$bill->prepareIotMeterForSend()`（攔截只記 log、不影響排定成敗）；`app/Console/Commands/BillBatchSend.php` `$iotGuard = $bill->prepareIotMeterForSend();`、`if ($iotGuard !== true) { … 已跳過不送出 … continue; }` |
| E6 | 帳本與程式一致 | `docs/knowledge/jgb-product-facts.md` `#p914-power-reading-draft`：「走排定發送的帳單…在度數仍為空或 0 時由 `prepareIotMeterForSend()` 自動補抓；已有非 0 度數者不重抓覆寫」 |

## 3. 主 session 對證據的讀法（供參考，⛔ 裁決）

- A 與 B 目前沒有直接矛盾；A 內容無誤（9.16 驗證通過、本次抽驗也過）。
- B 句 2 大致成立（未填度數的帳單排不進去，E3），但**漏了 E4 的例外**：唯一缺的是 IoT 綁定物件的電費度數時仍可排入，度數在排入與發送時自動補上（E5）。
- 帳本 `#p914-power-reading-draft` 與程式一致，不需更正。

## 4. ⏳ 請業主四選一

1. **A 錯**（A 要修）
2. **B 錯／不完整**（B 句 2 補上 IoT 電費例外；B 會失去已審、修正後交業主重審）
3. **兩條都對、範圍不同**（維持現狀，不改）
4. **無法判斷**（不改，列待查）

業主裁決原文：（待填）
