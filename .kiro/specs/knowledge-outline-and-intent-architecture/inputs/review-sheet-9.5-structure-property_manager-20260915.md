# 步 2 歸屬審核單（property_manager，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:kb:property_manager/A/repair-ticket-after-submit` | 確認送出後的單如何處理 | `property_manager/F/repair-ticket-after-submit` | 確認送出後的單如何處理 | move | F/F/F | |
| 2 | `tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup` | 業務代開修繕單時的租約查詢身分規則 | `property_manager/F/repair-ticket-no-lease` | 代開單時的租約查詢身分與空屋／無租約物件開單規則 | merge | F/F/F | |
| 3 | `tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates` | 照片辨識信心不足時的候選類別流程 | `property_manager/F/repair-ticket-photo-recognition-uncertain` | 照片辨識信心不足或看不出損壞時的處理 | merge | F/F/F | |
| 4 | `tmp:kb:property_manager/A/repair-ticket-mid-flow-cancel` | 報修流程中途取消的規則 | `property_manager/F/repair-ticket-mid-flow-cancel` | 報修流程中途取消的規則 | move | F/F/F | |
| 5 | `tmp:kb:property_manager/A/repair-ticket-photo-count-limit` | 修繕辨識與附件的照片張數限制 | `property_manager/F/repair-ticket-photo-count-limit` | 修繕辨識與附件的照片張數限制 | move | F/F/F | |
| 6 | `tmp:kb:property_manager/A/repair-ticket-photo-flow` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | `property_manager/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | move | F/F/F | |
| 7 | `tmp:kb:property_manager/A/repair-ticket-reclassify` | 分類辨識結果錯誤時如何修改 | `property_manager/F/repair-ticket-reclassify` | 確認卡上修改辨識結果的規則 | move | F/F/F | |
| 8 | `tmp:kb:property_manager/A/repair-ticket-submit-failure` | 建單失敗時的處理與重試規則 | `property_manager/F/repair-ticket-submit-failure` | 建單失敗時的處理與重試規則 | move | F/F/F | |
| 9 | `tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo` | 照片看不出損壞時的留白規則 | `property_manager/F/repair-ticket-photo-recognition-uncertain` | 照片辨識信心不足或看不出損壞時的處理 | merge | F/F/F | |
| 10 | `tmp:kb:property_manager/A/repair-ticket-urgency-judgment` | 修繕單急迫程度的判斷來源 | `property_manager/F/repair-ticket-urgency-judgment` | 修繕單急迫程度的判斷來源與值域 | move | F/F/F | |
| 11 | `tmp:kb:property_manager/A/repair-ticket-vacant-no-lease` | 空屋或無租約物件的開單規則 | `property_manager/F/repair-ticket-no-lease` | 代開單時的租約查詢身分與空屋／無租約物件開單規則 | merge | F/F/F | |
| 12 | `tmp:kb:property_manager/B/dunning-draft-generation` | 催繳草稿的生成規則（模板＋語氣分級） | `property_manager/E/dunning-draft-template-tone-late-fee` | 催繳草稿的生成規則（模板、語氣分級與滯納金提及） | merge | E/E/E | |
| 13 | `tmp:kb:property_manager/B/dunning-draft-late-fee-mention` | 催繳草稿是否提及滯納金的規則 | `property_manager/E/dunning-draft-template-tone-late-fee` | 催繳草稿的生成規則（模板、語氣分級與滯納金提及） | merge | E/E/E | |
| 14 | `tmp:kb:property_manager/B/dunning-draft-not-auto-send` | 催繳草稿不可一鍵發送給租客 | `property_manager/E/dunning-draft-not-auto-send` | 催繳草稿不可一鍵發送給租客 | move | E/E/E | |
| 15 | `tmp:kb:property_manager/C/lease-expiry-followup-scope` | 合約到期追問可答範圍（導向續約面向） | `property_manager/D/lease-expiry-followup-scope` | 合約到期追問可答範圍（導向續約面向） | move | D/D/D | |
| 16 | `tmp:kb:property_manager/C/meter-item-followup-scope` | 電錶項目追問（導向電表排障面向） | `property_manager/G/meter-item-followup-scope` | 電錶項目追問可答範圍（導向電表排障面向） | move | G/G/G | |
| 17 | `tmp:kb:property_manager/C/overdue-bill-followup-scope` | 逾期帳單追問可答範圍 | `property_manager/E/overdue-bill-followup-scope` | 逾期帳單追問可答範圍 | move | E/E/E | |
| 18 | `tmp:kb:property_manager/C/urgent-repair-followup-scope` | 緊急修繕追問範圍（目前無獨立面向） | `property_manager/F/repair-progress-followup-scope` | 修繕進度追問可答範圍 | move | F/F/F | |

## B. 拆分（split）——一個舊細目拆成多個新細目

（本次無拆分）

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `property_manager/E/dunning-draft-template-tone-late-fee`《催繳草稿的生成規則（模板、語氣分級與滯納金提及）》 | `tmp:kb:property_manager/B/dunning-draft-generation`＋`tmp:kb:property_manager/B/dunning-draft-late-fee-mention` | 兩角度合併：滯納金提及規則引用語氣分級（第 1 級不提）才能成立，互相依賴才完整；催繳屬收款金流子題，歸 E。 | |
| `property_manager/F/repair-ticket-no-lease`《代開單時的租約查詢身分與空屋／無租約物件開單規則》 | `tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup`＋`tmp:kb:property_manager/A/repair-ticket-vacant-no-lease` | 三角度一致合併：兩項答案重疊於「查不到租約時合約欄位留空、照常開單、開單人由系統帶入」。 | |
| `property_manager/F/repair-ticket-photo-recognition-uncertain`《照片辨識信心不足或看不出損壞時的處理》 | `tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates`＋`tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo` | 兩角度合併：使用者問「照片認不出來怎麼辦」是同一問題路徑，給候選類別與留白是同一答案依信心程度的兩個分支。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：把 photo-flow、reclassify、mid-flow-cancel 合併為單一「確認流程（操作層）」細目。 | 三者是不同階段的獨立問題（怎麼進場、分類錯了怎麼改、中途不報了會不會留單），user_question_path 與 content_boundary 兩角度皆獨立，合併會讓單一問法對應到過大的答案。 | |
| audience_level：把 after-submit 與 submit-failure 合併為「送出後與建單失敗處理」細目。 | 「已送出能不能改」與「送出失敗要怎麼重試」是不同問題路徑且答案互不依賴，兩角度皆獨立；合併違反一細目一可獨立回答主題。 | |
| audience_level：把 photo-count-limit 併入照片辨識能力細目（與信心不足、看不出損壞同列）。 | 張數上限與附件保存是數量／附件問題，不依賴辨識結果即可完整回答，兩角度皆獨立；只合併信心不足與看不出損壞。 | |
| content_boundary：low-confidence-candidates 與 unrecognizable-photo 各自獨立成細目。 | 兩者對使用者是同一個問題「照片認不出來怎麼辦」，答案依信心程度分為給候選或留白兩個分支，另兩角度皆合併；拆開會讓同一講法掛兩個細目。 | |
| user_question_path：dunning-draft-generation 與 dunning-draft-late-fee-mention 各自獨立成細目。 | 滯納金提及規則以「語氣第 1 級不提」引用分級定義，單獨無法完整回答，另兩角度皆合併；獨立會造成兩細目重複語氣分級內容。 | |
| audience_level：對粗目已從 A／B／C 改到 F／E／D／G 的單一來源項目標 op=keep。 | 粗目歸屬已變動，依定義應為 move；keep 會讓 id_map 看不出跨粗目搬移。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 1 | 3 | 10 | 1 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `property_manager/E/dunning-draft-template-tone-late-fee` | merge |
| `property_manager/F/repair-ticket-no-lease` | merge |
| `property_manager/F/repair-ticket-photo-recognition-uncertain` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

（無）
