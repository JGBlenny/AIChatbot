# Nomination 可作用範圍：靜態盤查（**不需部署、不需流量**）

- 日期：2026-08-29｜方法：純 SQL，對 `knowledge_base` 與 Face `topic_scope.category` 做 join
- 為什麼不必等 production：**情境本來就在專案裡**——每一筆知識就是系統宣稱能處理的一個情境，
  而它的 `categories` 決定 nomination。這是設定事實，與流量分布無關。

## 結論

> **現行 KB 中，21.5% 的 knowledge rows 具備 category→Face nomination capability；
> 78.4% 的 rows 若成為 top1，無法透過此 nomination mechanism 產生 Face candidate。
> 此比例是 KB configuration coverage，不是 production traffic coverage，
> 也不是需求漏接率。**

⚠️ **2026-08-29 更正**：本檔初版寫成「可作用範圍**上限**是 21.5%，流量只會更低或相等」
——**錯的**。流量可能高度集中在那 188 筆 mapped rows；極端情況下 production 的 top1
全部落在 mapped rows，request-level 的 nomination opportunity 可以**遠高於** 21.5%。
`KB row coverage` 與 `request coverage` 是兩個不同的量，⛔ 不得互推。

```text
S3  有 categories 但無 Face mapping → 永不提名   573 筆  65.6%
S2  無 categories                 → 永不提名   112 筆  12.8%
S4/S5 可提名                                   188 筆  21.5%
```

分類層面同樣的形狀：

```text
無 Face mapping   53 個 category（652 筆知識）
有 Face mapping   21 個 category（210 筆知識）
```

未 mapping 的大宗（依知識筆數）：

```text
合約管理 43｜帳單管理 26｜付款金流 24｜設備管理責任 24｜分租與轉租 24
社會住宅制度 24｜管理費收費規則 24｜公共設施與社區規範 23｜租客權益與爭議處理 23
包租業 vs 代管業差異 23｜業者操作指引 23｜租賃契約與法規 23｜…
```

## ⚠️ Claim ceiling（**這條最容易被讀壞**）

```text
✅ 可說：78.4% 的知識**若成為 top1，永遠不會產生 Face nomination**——決定性設定事實
⛔ 不得說：78.4% 的使用者需求被漏掉
   ——那 573 筆裡有大量制度／法規／常識型知識，本來就**應該**單發答完。
     「該不該進面向」是 Layer 0 問題，Stage 1 沒有 user utterance，答不了。
⇒ 本數字量的是**架構觸及上限**，不是**漏接率**。
```

## 這回答了 Stage 1 的核心命題（的一半）

Stage 1 規格第七節問：

> retrieval + category 這套 mechanism，在真實 production traffic 上到底有沒有足夠 support？

靜態盤查回答的是**設定側**：21.5% 的 knowledge rows 具備 nomination capability。
⛔ 它**不能**推出 request-level 的覆蓋率——流量可能集中在 mapped rows。

⇒ 要主張「nomination 覆蓋足夠／不足」，都還需要 request 側的分布；
   而要說出「**該**補多少」，仍須 Layer 0。

## 與先前實測的一致性

```text
D3 的 60 句合成 instance 問句 → 36 句完全沒有 facet nomination
    落點散在 iot_meter／estate_diag／contract_* 等，多數 category 未 mapping
「文山路那間現在還有人在住嗎」「3樓的電表度數現在是多少」→ 未進任何面向
⇒ 那些軼事與本次靜態盤查指向同一個結構，而非取樣巧合。
```

## 方法上的修正紀錄

```text
第一版查詢用 `category <> '對話規則'` 過濾，只得 1 筆——
`category`（單數）多為 NULL，`NULL <> '對話規則'` 為 NULL ⇒ 整批被濾掉。
已改用 COALESCE。⚠️ 這與既有定案一致：單數 category 只當角色標記，主題一律走 categories。
```
