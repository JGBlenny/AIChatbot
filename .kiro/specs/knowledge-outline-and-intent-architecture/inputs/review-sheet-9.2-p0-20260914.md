# 9.2 P0 內容審核單（2026-09-14）：pm 68 條講法核可、prospect 15 組重掛歸一、1 條錯配

> 背景：`fine_index._key_plan` 只索引 `status: approved` 的講法。pm 正本 68 條全 `proposed` ⇒ **0 條進索引**，pm 今天只靠 39 個標題＋57 句內文檢索。prospect 有 15 組講法逐字掛在 ≥2 個細目 ⇒ 同向量同分 ⇒ 同時進 top-5，吃掉 K=5 名額。
> ⛔ 本單只動講法歸屬與狀態，**不動粗目、不改 `fine.id`、不刪細目**（併細目的建議列在 §D 交 9.5）。核可後走 skill 步 3／步 6，hook 產 diff-report 才寫正本；改後 `canon_sha256` 變 ⇒ `.json` 重導出＋索引重建；必跑不變量 34。
> 查證：`grep -oE "status: [a-z]+" rag-orchestrator/canon/property_manager.md | sort | uniq -c`；重複組腳本見 `docs/knowledge/jgb-domain-map.md` §7。

## A. prospect 15 組重掛講法——每條只留一處

| # | 講法 | 現掛（重複） | 建議留在 | 理由 | 業主 |
|---|---|---|---|---|---|
| 1 | 「大房東報表」 | B/team-company-fit ／ C/team-management-overview ／ C/owner-report-collection-remit | C/owner-report-collection-remit | 標題即命題；B/team-company-fit、C/team-management-overview 移除 | |
| 2 | 「收租對帳」 | B/individual-landlord-scale-fit ／ C/billing-overview | C/billing-overview | 帳務模組命題；B/individual-landlord-scale-fit 移除 | |
| 3 | 「合約能不能匯」 | B/data-migration ／ G/migration-limits | G/migration-limits | 問的是「不能」那一側 | |
| 4 | 「哪些能匯」 | B/data-migration ／ G/migration-limits | B/data-migration | 問可匯入範圍 | |
| 5 | 「房東租客合約帳單」 | B/data-migration ／ G/migration-limits | G/migration-limits | 列舉的正是不支援項 | |
| 6 | 「批次匯入」 | B/data-migration ／ G/migration-limits | B/data-migration | 正向操作 | |
| 7 | 「搬資料」 | B/data-migration ／ G/migration-limits | B/data-migration | 正向 | |
| 8 | 「舊系統資料可以匯進來嗎」 | B/data-migration ／ G/migration-limits | B/data-migration | 正向 | |
| 9 | 「上傳既有合約」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-esign-flow | 既存合約屬建約方式 | |
| 10 | 「修改合約」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-modify-after-sign | 標題即命題 | |
| 11 | 「合約範本」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-templates | 標題即命題 | |
| 12 | 「建立合約」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-esign-flow | 建約 | |
| 13 | 「簽約邀請」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-esign-flow | 簽約流程 | |
| 14 | 「線上電子簽約」 | C/contract-esign-flow ／ C/contract-templates ／ C/contract-modify-after-sign | C/contract-esign-flow | 簽約流程 | |
| 15 | 「金箍棒」 | D/pricing-plans ／ E/competitor-comparison | （刪） | ⛔ 裸品牌名，任何問題都會命中，建議兩處都刪 | |

判準：講法歸「標題即命題」的那條；同一主題正反兩側依問法極性分；裸品牌名不當講法。

## B. 錯配 1 條

| 講法 | 現掛 | 建議移到 | 理由 | 業主 |
|---|---|---|---|---|
| 「欠租的房客怎麼找」 | `F/contact-sales-demo`《找真人或預約 demo》 | `C/overdue-reminder-late-fee`《租客逾期未繳怎麼辦》 | 字面是催收，掛在導流會把催收查詢拉去命中「找真人」 | |

## C. pm 68 條講法逐條核可（`proposed` → `approved`）

統計：68 條；來源 `line*` 31、`question_summary` 37；**建議 ✗ 的內部標籤 37 條**（`對話規則:`／`系統脈絡:` 開頭——那是 pm F 粗目的工作項標籤，不是任何人會打的句子）。

#### A｜A/repair-ticket-photo-flow《開修繕單基本流程與確認機制（拍照進場／文字口述）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 浴室天花板漏水報修 | line-doc:③#A | ✅ | |
| 確認送出 | line-doc:③#A | ✅ | |
| 廚房水槽下方漏水報修 | line-doc:③#F | ✅ | |
| 敦南 | line-doc:③#A | ✅ | |

#### A｜A/repair-ticket-reclassify《分類辨識結果錯誤時如何修改》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 報修分類改為水管 | line-doc:③#B | ✅ | |
| 我要修改 | line-doc:③#B | ✅ | |

#### A｜A/repair-ticket-after-submit《確認送出後的單如何處理》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 我要改一下描述 | line-doc:③#H4 | ✅ | |
| 廚房抽風機不會轉 同一戶 | line-doc:③#H4 | ✅ | |

#### A｜A/repair-ticket-low-confidence-candidates《照片辨識信心不足時的候選類別流程》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 牆角疑似損壞報修 | line-doc:③#C | ✅ | |
| 牆面滲水 | line-doc:③#C | ✅ | |

#### A｜A/repair-ticket-unrecognizable-photo《照片看不出損壞時的留白規則》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 熱水器不出熱水 | line-doc:③#D | ✅ | |
| 物件：D02 敦南 66 號 2 樓 | line-doc:③#D | ✅ | |

#### A｜A/repair-ticket-submit-failure《建單失敗時的處理與重試規則》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 確認送出重試 | line-doc:③#I | ✅ | |

#### A｜A/repair-ticket-vacant-no-lease《空屋或無租約物件的開單規則》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 客廳日光燈故障報修 | line-doc:③#K | ✅ | |

#### A｜A/repair-ticket-mid-flow-cancel《報修流程中途取消的規則》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 取消 | line-doc:③#G | ✅ | |

#### B｜B/dunning-draft-generation《催繳草稿的生成規則（模板＋語氣分級）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 產生催繳草稿 | line-doc:④#- | ✅ | |

#### C｜C/overdue-bill-followup-scope《逾期帳單追問可答範圍》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 系統脈絡:帳務領域-滯納金(子面向) | question_summary:3913 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:帳務領域-系統帳務(母共用) | question_summary:3909 | ✗ 內部標籤，不是使用者問法 | |
| 本期滯納金金額 | line-doc:⑤#A | ✅ | |
| 租客過去繳款紀錄 | line-doc:⑤#- | ✅ | |

#### C｜C/followup-session-single-item-boundary《追問的單筆會話邊界（不跨戶回答）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 追問其他物件的帳單 | line-doc:⑤#- | ✅ | |
| 追問其他租客的帳單 | line-doc:⑤#C | ✅ | |

#### C｜C/followup-missing-data-in-jgb《追問遇到 JGB 沒有的資料時怎麼回》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 帳單入帳日期查詢 | line-doc:⑤#D | ✅ | |

#### C｜C/lease-expiry-followup-scope《合約到期追問可答範圍（導向續約面向）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:續約 | question_summary:3829 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-系統合約(母共用) | question_summary:3799 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-續約(子面向) | question_summary:3824 | ✗ 內部標籤，不是使用者問法 | |
| 合約預告期是否已到 | line-doc:⑤#E | ✅ | |
| 租客續約意願查詢 | line-doc:⑤#E | ✅ | |

#### C｜C/urgent-repair-followup-scope《緊急修繕追問範圍（目前無獨立面向）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 熱水器維修歷史查詢 | line-doc:⑤#F | ✅ | |

#### C｜C/meter-item-followup-scope《電錶項目追問（導向電表排障面向）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:電表排障 | question_summary:4089 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:IoT領域-智慧設備(母共用) | question_summary:4021 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:IoT領域-電表排障(子面向) | question_summary:4091 | ✗ 內部標籤，不是使用者問法 | |
| 電表餘額與斷電時間查詢 | line-doc:⑤#- | ✅ | |

#### C｜C/followup-session-end《追問結束與流程收尾》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 好了 | line-doc:⑤#G | ✅ | |
| 結束 | line-doc:⑤#G | ✅ | |

#### G｜G/document-summary-rule《文件歸納的內容規則》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 憑證歸納 | line-doc:W9#G | ✅ | |
| 合約歸納 | line-doc:W9#G | ✅ | |
| 這份文件寫什麼 | line-doc:W9#G | ✅ | |

#### G｜G/document-content-boundary《文件內容的邊界（不是指令、不寫回）》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 上傳的文件內容 | line-doc:W9#G | ✅ | |

#### F｜F/contract-other-facets-scope-pending《合約其他子面向與對話規則是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:合約異動 | question_summary:4005 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:合約診斷 | question_summary:3801 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:建約引導 | question_summary:4215 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:簽署排障 | question_summary:3831 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:退租收尾 | question_summary:4202 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-合約異動(子面向) | question_summary:3822 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-建約引導(子面向) | question_summary:3825 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-狀態判斷(子面向) | question_summary:3800 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-簽署排障(子面向) | question_summary:3826 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:合約領域-退租收尾(子面向) | question_summary:3823 | ✗ 內部標籤，不是使用者問法 | |

#### F｜F/billing-other-facets-scope-pending《帳務其他子面向與對話規則是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:帳單異常 | question_summary:3916 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:帳單設定引導 | question_summary:4214 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:帳單診斷 | question_summary:4252 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:滯納金 | question_summary:3918 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:發票 | question_summary:3917 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:繳費金流排障 | question_summary:3915 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:帳務領域-帳單異常(子面向) | question_summary:3911 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:帳務領域-發票(子面向) | question_summary:3912 | ✗ 內部標籤，不是使用者問法 | |

#### F｜F/account-domain-scope-pending《帳號領域（註冊／登入／綁定異動／團隊權限）系統知識是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:團隊成員權限 | question_summary:4001 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:帳號綁定異動 | question_summary:3984 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:登入排障 | question_summary:3990 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:註冊驗證排障 | question_summary:3983 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:帳號領域-帳號中心(母共用) | question_summary:3952 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:帳號領域-登入排障(子面向) | question_summary:3954 | ✗ 內部標籤，不是使用者問法 | |

#### F｜F/iot-setup-scope-pending《IoT 設定引導系統知識是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:IoT設定引導 | question_summary:4090 | ✗ 內部標籤，不是使用者問法 | |

#### F｜F/estate-domain-scope-pending《物件領域（物件管理／操作引導／現況診斷）系統知識是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:物件操作引導 | question_summary:4203 | ✗ 內部標籤，不是使用者問法 | |
| 對話規則:物件現況診斷 | question_summary:4176 | ✗ 內部標籤，不是使用者問法 | |
| 系統脈絡:物件領域-物件管理(母共用) | question_summary:4132 | ✗ 內部標籤，不是使用者問法 | |

#### F｜F/subscription-domain-scope-pending《訂閱領域系統知識是否納入本受眾範圍，待裁》
| 講法 | 來源 | 建議 | 業主 |
|---|---|---|---|
| 對話規則:訂閱診斷 | question_summary:5374 | ✗ 內部標籤，不是使用者問法 | |

## D. 交 9.5 的結構建議（本單不做）

1. `B/data-migration` 與 `G/migration-limits` 是同一命題的正反兩面（互相 `see_also`）——建議併成一條（可匯入＝物件／社區／租客／大房東／帳單；不可匯入＝合約、歷史帳單當新紀錄）。
2. `C/contract-esign-flow` 標題自列五件事（時效、身分、社宅、批次續約）——建議拆。
3. pm F 十條全有 `reviewed`、今天可引用——去向待 9.4 裁；本單只把它們的講法標 ✗。

核可方式：每列「業主」欄填 ✅／✗／改＋文字。整單核完回我，我跑步 3／步 6。

---

## E. 兩位判者盲審比對（2026-09-14；判者 A／B 互不可見，各自逐條對正本內文）

**前提兩位都先自證**：15 組重複由腳本重算與單子逐字相同；pm 68／37／31 數字相符；不變量 34 現況交集為空（正對照句查得到）；`candidate_selector` K=5 無門檻。⚠️ 兩位都指出：**parser 的 ≤20 字／≥4 位數字檢查只綁 `source: traffic:*`，pm 68 條來源全是 `line-doc`／`question_summary` ⇒ 機器不擋，形狀全靠人審。**

### E-1 兩位判者一致、且都反對單子（建議照改，仍列給業主）

| 列 | 單子 | 兩位判定 | 理由 | 業主 |
|---|---|---|---|---|
| A#5「房東租客合約帳單」 | → `migration-limits` | → **`data-migration`** | B 內文明寫租客、大房東聯絡簿**可匯**，只有合約與歷史帳單不可；四項兩可兩不可，只有 B 兩側都涵蓋——單子理由與內文相反 | |
| C#4「敦南」 | ✅ | **✗ 刪** | 裸案名＝識別碼片段；同一把尺剛判死「金箍棒」 | |
| C#12「物件：D02 敦南 66 號 2 樓」 | ✅ | **✗ 刪** | 物件代號＋門牌；parser 不擋（非 traffic、無 ≥4 位連續數字） | |
| C#21／#22「追問其他物件／租客的帳單」 | ✅ | **改** | 「追問」是 `line-doc:⑤` 腳本動作名，非打字內容；改「其他物件的帳單」／「那另一間的帳單呢」 | |
| **新增錯配** `contract-templates` 的「電子合約的簽約邀請,有時效嗎?」（`helpcenter:slug73`） | 未列 | → **`contract-esign-flow`** | 72 小時只寫在 esign-flow 內文 | |
| A#15「金箍棒」理由 | 「任何問題都會命中」 | 動作同意、**理由改寫** | 無門檻下本來就必有 5 候選；真正的害是 prospect 十句九句帶「金箍棒」⇒ D／E 穩定佔 2 格擠掉該進榜的 | — |

### E-2 只有一位判者反對（需業主裁）

| 列 | 單子 | A | B | 爭點 | 業主 |
|---|---|---|---|---|---|
| C#9「牆角疑似損壞報修」 | ✅ | 改→`photo-flow` 或刪 | ✅ | 細目觸發條件是**照片信心不足**，文字鍵帶不出條件；與 #1/#3 向量無從區分 | |
| C#10「牆面滲水」 | ✅ | 改→`photo-flow` 或刪 | ✅（附註同 A） | 同上，是候選答案不是問法 | |
| C#11「熱水器不出熱水」 | ✅ | 改→`photo-flow` 或刪 | ✅（附註同 A） | 條件在照片端 | |
| C#14「客廳日光燈故障報修」 | ✅ | 改→`photo-flow` 或刪 | ✅（附註：文字不帶空屋語義） | 細目命題是「空屋開單」，這句無此訊號；要鍵它該用「空屋可以開單嗎」 | |
| C#13「確認送出重試」 | ✅ | 改→「再試一次」 | ✅（附註非自然語句） | 使用者打的是「再試一次」；與 #2 互撞 | |
| C#29「熱水器維修歷史查詢」 | ✅ | 改→`F/repair-history-facet-pending` | ✅（附註字面落差交 9.5） | C 內文只承諾「進度」，F 內文明寫「歷史仍不在範圍」——問歷史的人該拿到「不在範圍」 | |
| C#39「上傳的文件內容」 | ✅ | ✅ | 改（改成「文件裡寫的能直接照做嗎」） | 名詞化系統描述、與 #38 同向；細目要守的「不是指令」語義無鍵指得到 | |
| **B 另掃到 5 條錯配**：`多久可以提款`／`驗證碼多久可以重發`（掛 `free-trial`，答案在金流／註冊）；`凶宅怎麼辦`／`租賃專法是什麼`／`樓盤字典是什麼`（掛 `property-quota-limit`／`what-is-owner-landlord`，**全正本無任何內容行答得出來＝有鍵無答**） | 未列 | 未掃 | 移／刪 | 前兩條移掛；後三條刪或交 9.5 補內容 | |

### E-3 跨條目建議（兩位都提，形式不同）

1. **近義重複**：pm A 粗目有 6 條「〈部位〉〈故障〉報修」入場句散在 4 個細目——逐字不同、向量幾乎同位，一句「浴室漏水報修」會一次拉進 3–4 個修繕細目，佔的名額比 prospect 15 組還多。A 建議：入場句集中到 `A/repair-ticket-photo-flow` 留 2 條，分支細目改用**條件語句**當鍵（＝E-2 前四列的根）。
2. **37 條 ✗ 直接刪、⛔ 不留 `proposed`**：不進索引沒錯，但它們的字串在同細目內文目錄行已逐字存在（內文每句都是鍵）⇒ 零增益；留著等於把內部面向分類表寫在正本裡。
3. **不變量 34 的風險在改寫**：若把 ✗ 改寫成新問法，新句必跑 `canon_phrasing_frozen_disjoint.py`（凍結題 106 句）。

### E-4 兩位都同意單子的
A 段其餘 14 組、B 段 1 條、C 段 37 條 ✗ 與其餘 ✅（未列於 E-1／E-2 者）。
