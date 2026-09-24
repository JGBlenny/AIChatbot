# 9.5 重切草稿盤查——業主要裁的疑問（2026-09-15）

> 依業主「先直接歸，代理盤查有疑問我再審」。機械項（內容保真每句一次、屬性帶過 100%、E-1 套用恰好 17 條、講法唯一、值域）全部 CONFIRMED；下列是盤查代理判「非機械、要人裁」的。草稿在 scratchpad `recut/<aud>/<aud>.post-audit.md`，⛔ 正本未動。
> 盤查後我已直接套的（兩判者一致或 DSP 明文）：pm 刪 2 條識別碼講法＋8 條內部標籤；prospect 競品兩細目 `policy: deliberate_no`（DSP-048）；`I/data-migration` 自指 `see_also` 刪。

## 一、必裁 P1：15 個細目因 merge／split 失去 `reviewed` ⇒ 上線後不可見

規則（`canon/README.md` R2.9）：內容變＝待審；沒 `reviewed` ⇒ `citable=False`、`kb.get` 回 NO_MATCH。**約 2,525 字原本可見的內容會消失，prospect 佔 35%，整個 D 租約只剩 2 條有內容。**

| 受眾 | 細目 | 業主（✅ 補審／改） |
|---|---|---|
| pm | `E/dunning-draft-template-tone-late-fee`、`F/repair-ticket-photo-recognition-uncertain`、`F/repair-ticket-no-lease` | |
| prospect | `A/account-registration`、`D/contract-esign-flow`、`D/contract-batch-renewal`、`D/contract-templates`、`D/sublease-vs-management-contract`、`E/billing-overview`、`E/einvoice-issuing`、`E/overdue-reminder-late-fee`、`E/payment-gateway-options`、`E/virtual-account-prepaid`、`I/product-overview`、`I/data-migration` | |

補審＝你讀過內容後在該細目加 `- reviewed: {by: owner, at: <日期>}`（步 6 diff 一起進）。

## 二、必做 P1：pm 20 條講法仍全 `proposed` ⇒ 0 進索引

DSP-057 說與重切一起核。兩位判者已判：非內部標籤的 31 條原則 ✅（刪 2 識別碼後剩 20 在保留細目內）。**你點頭我全部翻 `approved`。** | 業主： |

## 三、必做 P2：5 組 split 的子細目目前是整段複製（+1,679 字、35 句重複）

⛔ 機器不猜分句。要人把句子分到子細目：

| 舊細目 | 子細目 |
|---|---|
| `C/contract-esign-flow` | `D/contract-esign-flow`（流程／時效／身分／社宅／費用）／`D/contract-batch-renewal` |
| `C/contract-templates` | `D/contract-templates`／`D/sublease-vs-management-contract` |
| `C/billing-overview` | `E/billing-overview`／`E/einvoice-issuing` |
| `C/payment-gateway-options` | `E/payment-gateway-options`／`E/virtual-account-prepaid` |
| `C/notification-channels` | `A/account-registration`（驗證碼句）／`D/contract-esign-flow`（簽約邀請句）／`E/overdue-reminder-late-fee`（繳費提醒句） |

分句可以由我做、你審；或你直接分。 | 業主： |

## 四、講法歸位（步 3 要吃的）

- pending 26 條：盤查判 **24 條可直接分派**（清單在盤查報告），**2 條正解在候選集外**（`儲值金`→`E/virtual-account-prepaid`、`金流代收`→`E/payment-gateway-options`），**1 條真正三邊可（`我只有租客的電話沒有email`）**。 | 業主：24 條照判／那 1 條歸哪 |
- `C/property-status-meaning` 帶著 7 條帳務／租約講法（`已失效`／`已支出`／`找補費用`／`未退押金`／`自動對帳`／`解約後30天`…），舊病灶原樣搬過來。建議：帳單語彙移 `E/bill-contents-extra-fees`／`E/overdue-reminder-late-fee`，解約／未退押金移 D。 | 業主： |
- `I/competitor-comparison` 講法 `租賃管理系統` 是泛詞，會把一般問題拉進競品。建議刪。 | 業主： |
- E-2 單判者 12 條（`review-sheet-9.2-p0` §E-2）：pm 6 條入場句集中到 photo-flow／`確認送出重試`→`再試一次`／`熱水器維修歷史查詢` 刪或改；prospect `多久可以提款`→金流、`驗證碼多久可以重發`→註冊、`凶宅`／`租賃專法`／`樓盤字典` 三條**有鍵無答**刪。 | 業主： |

## 五、`see_also`

- D 四個合約子細目的 `see_also` 都是母細目複製來的 `D/contract-modify-after-sign`——對 `templates`／`sublease` 是否成立。 | 業主： |
- `C/property-status-meaning` 提議理由寫「另見租約」但 `see_also` 空——補 `D/contract-history-retention`？ | 業主： |
- 另案：parser 加「`see_also` ≠ 自身」檢查（merge 會製造自指）。

## 六、可接受、只告知

- pm 粗目 A／B／C／H／I 空（脊椎佔位，覆蓋圖要看的零格）。
- `G/meter-item-followup-scope` 歸 G 正確（餘額／供電＝裝置資料）；日後加「度數帶進帳單」句要分家。
- `I/dashboard-overview` 歸 I 可接受。
