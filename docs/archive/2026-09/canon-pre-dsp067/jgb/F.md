---
coarse: F
title: 修繕
scope: 報修、派工、進度與狀態、修繕通知；⛔ 費用入帳歸 E
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 修繕 {#F}
### 修繕進度追問可答範圍與查詢方式 {#jgb/F/repair-progress-followup-scope}
- phrasings:
  - {text: "熱水器維修歷史查詢", source: "line-doc:⑤#F", status: approved}
- sources: [draft:batch#18, kb:1558, kb:3365, kb:4420]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
修繕進度可查：單號、物件、分類、狀態、急迫程度、建單時間、指派；開單仍走拍照確認流程。
維修進度可以透過系統查詢，請提供您的物件地址，我幫您查詢。
為您查詢名下的報修單處理進度；若目前沒有任何報修單，代表尚未提出報修——需要的話跟我說「我要報修」，我可以直接協助您建單。

### 線上報修與進度追蹤 {#jgb/F/repair-system}
- phrasings:
  - {text: "修繕系統", source: "question_summary:3605", status: approved}
  - {text: "線上報修", source: "question_summary:3605", status: approved}
  - {text: "進度追蹤", source: "question_summary:3605", status: approved}
- sources: [kb:3605, helpcenter:repair]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
報修處理慢、追蹤不易？
金箍棒的修繕系統讓租客線上報修、房東與管理方追蹤處理進度，把報修流程數位化。
想看實際流程可預約 demo。

### 確認送出後的單如何處理 {#jgb/F/repair-ticket-after-submit}
- phrasings:
  - {text: "我要改一下描述", source: "line-doc:③#H4", status: approved}
  - {text: "廚房抽風機不會轉 同一戶", source: "line-doc:③#H4", status: approved}
- sources: [draft:batch#31]
- reviewed: {by: owner, at: 2026-09-09}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
確認送出後，這張單不在對話裡修改：業務要改內容時，說明這張單已送出，並指到 JGB 的修繕單頁面處理。
送出後再描述同一戶的另一個問題，視為另一張新單：物件不重問，依口述描述出新的確認摘要，仍只有按「確認送出」才建單。

### 報修流程中途取消的規則 {#jgb/F/repair-ticket-mid-flow-cancel}
- phrasings:
  - {text: "取消", source: "line-doc:③#G", status: approved}
- sources: [draft:batch#10]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。

### 代開單時的租約查詢身分與空屋／無租約物件開單規則 {#jgb/F/repair-ticket-no-lease}
- phrasings:
  - {text: "客廳日光燈故障報修", source: "line-doc:③#K", status: approved}
- sources: [draft:batch#6, draft:batch#9]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。
可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。

### 開修繕單基本流程與確認機制（拍照進場／文字口述） {#jgb/F/repair-ticket-open-and-confirm}
- phrasings:
  - {text: "浴室天花板漏水報修", source: "line-doc:③#A", status: approved}
  - {text: "確認送出", source: "line-doc:③#A", status: approved}
  - {text: "廚房水槽下方漏水報修", source: "line-doc:③#F", status: approved}
- sources: [draft:batch#1, kb:4416, kb:4418, kb:4421, kb:4422]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
由拍照進場時，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；聊天以文字口述時，以口述的物件、問題描述與分類直接出確認摘要與三顆按鈕，不要求照片；兩者都只有按下「確認送出」才建單，任何未經確認的自動建單視為重大錯誤。

### 修繕辨識與附件的照片張數限制 {#jgb/F/repair-ticket-photo-count-limit}
- sources: [draft:batch#5]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。

### 照片辨識信心不足或看不出損壞時的處理 {#jgb/F/repair-ticket-photo-recognition-uncertain}
- phrasings:
  - {text: "牆角疑似損壞報修", source: "line-doc:③#C", status: approved}
  - {text: "牆面滲水", source: "line-doc:③#C", status: approved}
  - {text: "熱水器不出熱水", source: "line-doc:③#D", status: approved}
- sources: [draft:batch#3, draft:batch#4]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。
看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣寫進修繕單給師傅。

### 確認卡上修改辨識結果的規則 {#jgb/F/repair-ticket-reclassify}
- phrasings:
  - {text: "報修分類改為水管", source: "line-doc:③#B", status: approved}
  - {text: "我要修改", source: "line-doc:③#B", status: approved}
- sources: [draft:batch#2]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
**確認卡尚在時**按「我要修改」只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。

### 建單失敗時的處理與重試規則 {#jgb/F/repair-ticket-submit-failure}
- phrasings:
  - {text: "確認送出重試", source: "line-doc:③#I", status: approved}
- sources: [draft:batch#8]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。

### 修繕單急迫程度的判斷來源與值域 {#jgb/F/repair-ticket-urgency-judgment}
- sources: [draft:batch#7]
- reviewed: {by: owner, at: 2026-09-08}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
急迫與非急迫由辨識建議或業務口述；未表明時以非緊急建單，不得預設為急迫、也不為此反問；值域以 JGB 資料庫為準：2＝緊急、1＝非緊急。

### 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） {#jgb/F/repair-responsibility-landlord-vs-tenant}
- phrasings:
  - {text: "修繕條款", source: "question_summary:2969", status: proposed}
  - {text: "修繕維護責任", source: "question_summary:3221", status: proposed}
  - {text: "修繕義務", source: "question_summary:2973", status: proposed}
  - {text: "修繕責任", source: "question_summary:2964", status: proposed}
  - {text: "修繕費用負擔", source: "question_summary:2968", status: proposed}
  - {text: "房屋修繕責任", source: "question_summary:2963", status: proposed}
  - {text: "房屋維修責任", source: "question_summary:3030", status: proposed}
  - {text: "房東維護責任", source: "question_summary:3277", status: proposed}
  - {text: "租屋設施維護責任", source: "question_summary:3222", status: proposed}
  - {text: "維修責任", source: "question_summary:3029", status: proposed}
  - {text: "維護責任", source: "question_summary:2971", status: proposed}
  - {text: "維護責任範圍", source: "question_summary:3203", status: proposed}
- sources: [kb:2963, kb:2964, kb:2968, kb:2969, kb:2971, kb:2973, kb:3029, kb:3030, kb:3203, kb:3221, kb:3222, kb:3277, kb:3287, kb:3289]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東在租約期間負責維護房屋的結構及主要設施的修繕，例如水電管路、固定設備等。
若因房客使用不當造成的損壞，則由房客負責修繕費用。
若您遇到任何修繕問題，請隨時聯繫您的管理師協助處理。
租客在租約期間對於房屋的修繕責任包括日常維護和小型修繕，例如更換燈泡或清理排水管等。
若遇到結構性問題或重大故障，則由房東或管理師負責修繕。
建議您如有問題，立即聯繫您的管理師以獲取具體指導。
一般來說，房東負責房屋的結構性修繕及設施的維護，例如水管漏水或電力故障等。
而租客則需負責因日常使用導致的輕微損壞，例如燈泡更換。
具體的負擔劃分可能依合約有所不同，建議您確認租約內容以了解自己的權益。
常見的修繕條款包括：房東負責結構性修繕，例如水管、電路和屋頂的維修；房客則需負責日常小修小補，如燈泡更換和小型設備的維護。
如果發現重大損壞，房客應立即通知管理師以便及時處理。
根據租約，房客有權要求房東在合理時間內完成必要的修繕工作，確保居住環境的安全與舒適。
租客對於租屋內部設施的維護責任通常限於日常使用中的小修小補，例如更換燈泡或清潔空調濾網等。
主要的設備故障或損壞維修責任則由出租方或包租代管公司負責。
您可以隨時向管理師報告任何需要維修的問題，讓我們幫您處理。
房東在租約中通常負責大部分的修繕義務，包括維持租屋的結構、安全與基本設施的正常運作，如水電、暖氣等。
如果修繕問題是因租客使用不當而產生的，則可能由租客負責。
建議您詳細閱讀租約內容，確保了解自身及房東的責任。
在租屋期間，房客對於小型維修和日常保養負有一定責任，例如更換燈泡、清潔空調濾網等。
不過，主要的結構性維修如水管漏水或電路故障等，則應由房東或管理師負責處理。
您可以隨時聯繫管理師報告需要維修的問題，確保您的居住環境安全舒適。
房東在租屋期間負責維修房屋的主要結構及設施，例如水電系統、供暖和冷氣設備等，確保租客可以安全居住。
如果發現任何需要維修的問題，請及時通知管理師，我們會協助處理維修事宜。
房東的維護責任通常包括房屋結構、暖氣系統、冷氣系統、水管、電力系統、以及其他固定設備的正常運作。
如果您遇到任何設備故障，請及時聯繫您的管理師進行維修申請。
修繕完成後，維持修繕狀態的責任通常屬於房東，但您應該確保不會因使用不當而造成損壞。
如果發現任何問題，請及時通知管理師以便處理。
租客對於租屋內部設施的維護責任主要是保持設施的清潔和正常使用。
如果設施出現故障或損壞，通常由房東或管理公司負責修繕。
建議您在發現問題時及時通知管理師，以便快速處理。
房東的維護責任範圍通常包括房屋的結構、供水、供電、供氣系統，以及其他基本設施的運作和維修。
例如，水管漏水、電器故障等問題一般應由房東負責處理。
如果您遇到具體的維修問題，請聯繫您的管理師進行報修。
根據一般的租賃合約，房東負責房屋的主要結構及設施的修繕，例如水管、電路等問題；而租客則負責日常使用造成的損壞修繕。
但具體情況可能因合約而異，建議您確認合約內容或聯繫您的管理師以獲取詳細資訊。
在租約中，修繕責任通常會明確規定由房東或租客負責。
一般來說，房東負責結構性修繕和設備維護，而租客則負責日常的輕微維護。
如果您對租約條款有疑問，建議請聯繫您的管理師確認具體內容。

### 公共設備的維護、損壞、更新、費用與檢查紀錄責任 {#jgb/F/common-equipment-maintenance-responsibility}
- phrasings:
  - {text: "公共設備損壞責任", source: "question_summary:3188", status: proposed}
  - {text: "公共設備更新責任", source: "question_summary:3194", status: proposed}
  - {text: "公共設備檢查", source: "question_summary:3190", status: proposed}
  - {text: "公共設備維護", source: "question_summary:3186", status: proposed}
  - {text: "公共設備維護費", source: "question_summary:3192", status: proposed}
  - {text: "公共設備維護費用", source: "question_summary:3274", status: proposed}
  - {text: "公共設施維護", source: "question_summary:2970", status: proposed}
  - {text: "設備維護記錄", source: "question_summary:3197", status: proposed}
- sources: [kb:2970, kb:3186, kb:3188, kb:3190, kb:3192, kb:3194, kb:3197, kb:3274]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東對於公共設施的維護責任是確保這些設施的安全性和良好運作，包括定期檢查和必要的修繕。
如果您發現公共設施有問題，建議立即通知您的管理師，以便及時處理。
公共設備的維護責任通常由物業管理方負責，您作為房客在使用公共設施時，若遇到問題可以隨時通知管理師進行處理。
公共設備的損壞通常由房東或管理公司負責維修與維護。
作為房客，您有權要求迅速處理這些問題，確保居住環境的安全與舒適。
如果發現設備損壞，建議您立即聯繫管理師報修。
公共設備的檢查頻率通常為每月或每季一次，具體頻率會依據物件的管理規定而有所不同。
如有特殊需求或問題，您可以隨時聯繫您的管理師確認詳細資訊。
公共設備的維護費用通常由房東負擔，這是根據租約的約定來決定的。
您作為房客，應該不需要承擔這部分費用。
如果有任何疑問，建議您聯繫您的管理師確認具體的責任分配。
公共設備的更新責任通常由房東負責，但具體情況可能會根據租賃合約的不同而有所變動。
如果您對設備的狀況有疑問或需要協助，請聯繫您的管理師確認相關責任。
房東需要保留公共設備的維護記錄，這是確保設備正常運作及保障租客權益的重要措施。
這些記錄不僅有助於房東管理物業，也能在設備出現問題時提供必要的依據，讓租客享有更好的居住環境。
公共設備的維護費用通常由房東或物業管理公司負擔，這是房客的權益之一。
若有任何維護需求或問題，請隨時聯繫您的管理師進行報修。

### 租客設備的使用、維護、損壞賠償、更新與費用責任 {#jgb/F/tenant-equipment-maintenance-responsibility}
- phrasings:
  - {text: "租客設備維護", source: "question_summary:3187", status: proposed}
  - {text: "租客設備責任", source: "question_summary:3275", status: proposed}
  - {text: "設備使用責任", source: "question_summary:3198", status: proposed}
  - {text: "設備損壞責任", source: "question_summary:3189", status: proposed}
  - {text: "設備損壞賠償", source: "question_summary:3200", status: proposed}
  - {text: "設備更新責任", source: "question_summary:3195", status: proposed}
  - {text: "設備維護責任", source: "question_summary:3272", status: proposed}
  - {text: "設備維護費用", source: "question_summary:3193", status: proposed}
- sources: [kb:3187, kb:3189, kb:3193, kb:3195, kb:3198, kb:3200, kb:3272, kb:3275]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客在租期內應負責日常的設備保養與清潔，並及時報告任何故障或損壞。
若設備因正常使用而出現的磨損，通常由房東負責維修或更換，但如因租客不當使用造成的損壞，租客需承擔維修責任。
如果租客設備損壞，通常需要負擔修繕費用，但這取決於損壞的原因。
若是因正常使用造成的磨損，房東通常會負責修繕。
建議您查看租約中的相關條款，必要時可聯繫管理師確認具體責任。
在租期內，租客對租屋內設備的維護費用通常由房東負擔，除非租約中有特別約定。
建議您查看租約內容，或洽詢您的管理師以獲取具體資訊。
租客通常不需要負擔租客設備的更新責任，這一般由房東或管理公司負責。
若設備出現問題，我們會協助處理相關的維修或更換事宜，確保您能居住在安全舒適的環境中。
租客在使用租客設備時，需確保設備的正常使用及維護，並對因不當使用造成的損壞或故障負責。
如果設備出現問題，請及時通知管理師進行檢修，以免影響後續使用權益。
如果租客造成設備損壞，賠償標準通常依據合約內容及損壞程度來決定。
一般來說，租客需負擔修復或更換的費用，但具體金額需由管理師評估後告知。
如有疑問，建議您與您的管理師進一步確認。
租客在租期內對租客設備的維護責任主要包括日常的保養和清潔。
如設備出現故障或需修理，應及時通知管理師協助處理。
租客不需負責因正常使用造成的磨損，但如因不當使用導致損壞，則需負擔修理費用。
租客在使用租客設備時，需妥善保管並合理使用設備，避免因使用不當導致的損壞。
如果設備因正常使用而發生故障，管理公司會負責維修，但若是因租客不當操作造成損壞，租客可能需要承擔修復費用。
建議在發現設備問題時，及時聯繫管理師以獲得協助。

### 租客發現需修繕時的通知義務與要求合理期限修繕的權利 {#jgb/F/tenant-repair-notification-duty}
- phrasings:
  - {text: "修繕通知", source: "question_summary:2966", status: proposed}
  - {text: "修繕通知義務", source: "question_summary:3219", status: proposed}
  - {text: "修繕通知責任", source: "question_summary:3286", status: proposed}
- sources: [kb:2966, kb:3219, kb:3286]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客在發現房屋需要修繕時，有通知房東的義務。
這樣可以確保問題得到及時處理，避免進一步損壞或影響居住品質。
您可以透過管理師提交修繕申請，我們會協助您處理相關事宜。
租客在發現房屋需要修繕時，確實有通知房東的義務。
這樣可以確保問題及時獲得處理，避免情況惡化。
此外，租客有權要求房東在合理的時間內進行修繕，以維持居住環境的安全與舒適。
租客在發現房屋需要修繕時，應主動通知房東。
這是租客的責任之一，以確保房屋的安全與舒適，同時也保護您的租住權益。
如果您發現任何問題，請儘快聯繫管理師進行報修。

### 緊急情況下租客自行修繕的條件、事後通知與費用報銷 {#jgb/F/tenant-emergency-self-repair}
- phrasings:
  - {text: "修繕權限", source: "question_summary:3288", status: proposed}
  - {text: "自行修繕", source: "question_summary:3220", status: proposed}
- sources: [kb:2965, kb:3220, kb:3288]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客可以在出現影響居住安全或健康的情況下進行緊急修繕，例如漏水、電力故障或設備故障等。
若發生此類情況，請立即聯繫您的管理師以報修，並記得保留相關證據，以保障您的權益。
租客在緊急情況下，例如水管破裂或電力故障，若不及時修繕會造成更大損失，可以自行進行修繕。
但請務必在修繕後的第一時間通知房東，以便後續處理。
建議保留收據，房東應負擔合理的修繕費用。
如果修繕涉及到緊急情況，例如漏水或電力故障，租客可以自行進行必要的修繕而無需事先取得房東的同意。
這些情況下，為了避免進一步損害，租客有權立即處理，但建議在修繕後儘快通知房東以便報銷相關費用。

### 緊急修繕的標記、優先處理與回應時效 {#jgb/F/emergency-repair-flag-and-handling}
- phrasings:
  - {text: "判定處理", source: "question_summary:3426", status: proposed}
  - {text: "緊急修繕", source: "question_summary:3426", status: proposed}
  - {text: "緊急維修服務", source: "question_summary:3145", status: proposed}
  - {text: "緊急的可以優先處理嗎", source: "koyu:TOFILL-repair#8", status: proposed}
- sources: [kb:3145, kb:3426]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
我們的業者確實提供緊急維修服務，以確保您的居住安全與舒適。
若您遇到任何緊急問題，請及時聯繫您的管理師報修，他們將協助您處理相關事宜。
修繕申請時可標記為「緊急」狀態，用於區分需要優先處理的維修項目（如漏水、門鎖故障、電力問題等）。
緊急修繕在系統中以特殊標記顯示，方便管理者快速識別並優先安排。
實際的處理優先順序和回應時間由管理公司自行規範，系統提供標記功能供管理者判斷排序。
建議緊急修繕問題應在 24 小時內安排處理。

### 鄰居漏水的修繕責任與處理 {#jgb/F/neighbor-leak-responsibility}
- phrasings:
  - {text: "漏水修繕責任", source: "question_summary:2967", status: proposed}
- sources: [kb:2967]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果鄰居漏水，通常由漏水方負責修繕，您可以先聯繫您的管理師，協助您進行後續處理。
如果漏水影響到您的居住環境，請儘快報修，我們會協助您解決問題。

### 修繕責任有爭議時的處理 {#jgb/F/repair-responsibility-dispute}
- phrasings:
  - {text: "修繕責任爭議", source: "question_summary:2974", status: proposed}
- sources: [kb:2974]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
若您與房東對修繕責任有爭議，建議先查看租約中對於修繕責任的相關條款。
您也可以向管理師反映此問題，管理師會協助調解並提供必要的支持。
您的權益受到重視，請確保所有溝通和協調都有紀錄，以便維護您的權益。

### 修繕後的保固期 {#jgb/F/repair-warranty-period}
- phrasings:
  - {text: "修繕保固期", source: "question_summary:2975", status: proposed}
- sources: [kb:2975]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
修繕後的保固期通常為一年，但具體內容可能會依合約條款而異。
建議您查看租約內關於修繕的相關條款，或聯繫您的管理師以確認詳細信息。

### 社會住宅的維修責任 {#jgb/F/social-housing-repair-responsibility}
- phrasings:
  - {text: "社會住宅維修責任", source: "question_summary:3320", status: proposed}
  - {text: "房東教學09:社會住宅篇", source: "helpcenter:Landlordonboarding09Socialhousing", status: proposed}
- sources: [kb:3320]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社會住宅的維修責任一般由管理單位負擔，主要維修和維護工作會由管理師負責處理。
如果您在居住過程中遇到維修問題，可以隨時聯繫您的管理師進行報修。

### 修繕流程六階段與各狀態意義 {#jgb/F/repair-flow-stages}
- phrasings:
  - {text: "修繕流程", source: "question_summary:3424", status: proposed}
  - {text: "狀態說明", source: "question_summary:3424", status: proposed}
- sources: [kb:3424]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
修繕流程共有 6 個階段：（1）申請中：租客或房東提出修繕申請，填寫損壞原因、照片和說明；（2）安排修繕：管理者指派維修廠商，填寫廠商資訊和預估費用；（3）進行中：廠商正在進行維修工作；（4）完成修繕：維修工作完成，記錄實際費用和完修照片；（5）結單：管理者確認修繕結案，若有費用會自動產生修繕費帳單；（6）封存：修繕紀錄歸檔。
每個階段變更時系統會自動通知相關人員。

### 修繕費用的記錄、分擔與結單自動產生修繕費帳單 {#jgb/F/repair-cost-recording-and-settlement}
- phrasings:
  - {text: "修繕費用", source: "question_summary:3425", status: proposed}
  - {text: "結算方式", source: "question_summary:3425", status: proposed}
  - {text: "帳單是自動產生的嗎", source: "koyu:slug76#2", status: proposed}
  - {text: "點退之後會自動產生帳單嗎", source: "koyu:slug66#3", status: proposed}
- sources: [kb:3425]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
修繕費用由管理者在修繕流程中記錄：安排修繕時填寫預估費用，完成修繕時更新為實際費用。
結單時若修繕費用大於零，系統會自動產生一張修繕費帳單，向相關方收取費用。
費用的分擔方式由房東自行決定並記錄在系統中，系統不強制特定的分擔規則。
常見做法是依損壞原因判斷：自然耗損由房東負擔，人為損壞由租客負擔。

### 在系統提出修繕申請的步驟與需填資料（租客／房東） {#jgb/F/repair-request-how-to-submit}
- phrasings:
  - {text: "修繕申請", source: "question_summary:3427", status: proposed}
  - {text: "修繕請求", source: "question_summary:2972", status: proposed}
  - {text: "報修方式", source: "question_summary:3427", status: proposed}
  - {text: "報修步驟", source: "question_summary:3446", status: proposed}
  - {text: "提出修繕", source: "question_summary:3446", status: proposed}
- sources: [kb:2972, kb:3427, kb:3446]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
您可以通過填寫報修申請表來提出修繕請求。
請提供報修地點、問題描述、緊急程度以及方便聯繫的時間。
這樣我們的管理師可以迅速處理您的請求。
租客或房東都可以在系統中提出修繕申請。
申請時需填寫：修繕類別（如水電、門窗、設備等）、損壞原因描述、現場照片。
提交後系統自動通知管理者（房東或物管），管理者會安排維修廠商並回覆預估處理時間。
申請人可在系統中查看修繕進度，每個階段更新時也會收到通知。
租客提出修繕申請步驟：1. 登入系統，進入修繕功能頁面；2. 選擇要報修的物件（合約）；3. 填寫修繕資訊：選擇修繕類別（如水電、門窗、設備等）、描述損壞原因、上傳現場照片；4. 若為緊急問題（如漏水、門鎖故障），可標記為緊急修繕；5. 提交後系統自動通知房東或物管，可在修繕列表中追蹤處理進度。
每個階段更新時租客都會收到通知。

### 業者受理報修、安排廠商、完工登錄到結單封存的操作 {#jgb/F/repair-dispatch-and-close}
- phrasings:
  - {text: "修繕受理派工", source: "question_summary:3488", status: proposed}
  - {text: "安排廠商", source: "question_summary:3488", status: proposed}
  - {text: "怎麼受理處理", source: "question_summary:4249", status: proposed}
  - {text: "收到租客修繕申請", source: "question_summary:4249", status: proposed}
- sources: [kb:3488, kb:4249]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
業者處理修繕的操作流程：1. 收到租客報修通知後，在修繕列表中查看新申請（狀態為「申請」）；2. 安排廠商：填入維修日期、時段、廠商名稱與聯繫電話，狀態更新為「安排修繕」，系統通知租客廠商資訊；3. 維修完成後更新備註：填寫完工日期、維修說明、上傳完工照片、填入結算金額；4. 確認修繕完成後將狀態推進至「結單」，系統通知租客修繕已結案；5. 最後可將修繕記錄「封存」歸檔。
業者也可自行發起修繕申請（選擇物件、修繕分類、描述問題、上傳照片）。
只有業者可以推進修繕狀態，租客僅能查看進度和補充備註。
收到租客的修繕申請後，業者的處理流程：1. 到修繕列表查看新申請（狀態「申請」），確認損壞描述與照片；2. 安排廠商——填入維修日期、時段、廠商名稱與聯繫電話，狀態更新為「安排修繕」，系統會自動通知租客廠商資訊；3. 維修完成後填寫完工日期、維修說明與實際費用完成結案。
緊急案件可先電話聯繫租客再補系統紀錄。

### 多個品項是否分開報修（合併在一張報修單） {#jgb/F/repair-multiple-items-one-ticket}
- phrasings:
  - {text: "一張報修單", source: "question_summary:4654", status: proposed}
  - {text: "報修多個品項", source: "question_summary:4654", status: proposed}
  - {text: "都壞了分開報嗎", source: "question_summary:4654", status: proposed}
- sources: [kb:4654]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
同一次報修有多個品項（例如浴室三個設備）時，不必分開建立多張報修單：修繕品項選「其他」自行輸入，即可把多個品項整合寫在同一張報修單裡。
