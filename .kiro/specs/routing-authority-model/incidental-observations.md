# Incidental observations（偶遇觀察記錄）

> 語言 zh-TW｜**本檔不解讀、不推論、不作為任何判定的依據。**
> 存在理由：查核過程中偶遇的真實事實，若不記錄會流失；但寫進當時的判定文件會污染該判定。

## 使用規約（寫死）

```text
本檔每一則的 status 一律為 diagnostic observation only。

NOT used for：
  ❌ G1 verdict（已凍結，不因本檔改變）
  ❌ B／C rescue（B／C 已依協議 §6 退場，本檔不得用於翻案）
  ❌ member acceptance（任何 member 的通過與否）
  ❌ 任何 family disposition 的變更

若未來某一則被認為可能是合法的 runtime-binding evidence source，
**MUST 依當時生效的 qualification（如 E1–E6）重新受審**，
不得因為「早就記在這裡」而取得任何優先地位或既得資格。
```

---

## OBS-1｜`bills.status` 常數集中含「待對帳／待查收」

```text
發現時點    2026-08-24，執行 G1 audit 期間（唯讀）
來源位置    /Users/lenny/jgb/project/jgb_1/jgb2 ｜ master ｜ HEAD 5eaebb7f0a
            app/Bill.php:40-46
```

**看到的事實（原文引用，未加詮釋）**：

```php
const BILL_PREPARE = 1;         // 狀態 1：待發送
const BILL_READY = 2;           // 狀態 2：應到帳/待繳費
// const BILL_PAYING = 4;          // 狀態 4：付款中（後來已決定拿掉此標記，付款中一律算在待繳費）
const BILL_PAYED = 8;           // 狀態 8：待對帳/待查收
const BILL_COMPLETE = 16;       // 狀態 16：已到帳/已繳費
const BILL_PREPARE_TO_READY = 32; // 狀態 32：排定發送
const BILL_EXPIRED = 64;        //  狀態 64：已失效
```

**關聯**：Round 1 exhibit `bf-05-a`（「錢明明已經進來了，這筆一直卡在待對帳」）。

**未作、且本檔不得作的解讀**：

```text
❌ 不解讀為「該 Face 的 contract 有缺口」
❌ 不解讀為「bf-05-a 應判 applicable」
❌ 不解讀為「此常數集可作為某個 dimension 的 domain」
   （G1 已就 `App\Bill` 類別常數判定 INSUFFICIENT：class constant 是命名慣例，
     非寫入端 enforcement；`bills` 建表 migration 不在該 repo，無法查核 DDL 層約束）
```

⚠️ `bf-05-a` 在 `round1-failure-analysis-result.md` 的 ERRATA E2 中被移出 F2 標靶集合，
**其依據是另一件事**（該 Face 的 `does_not_handle` 四項中無對帳條目），
**與本則觀察無關**，兩者不得互相引用作為佐證。
