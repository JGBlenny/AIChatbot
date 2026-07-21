# AI 客服對話邏輯——業務版流程圖

> 受眾：非技術人員。技術對照版：[conversation-flow-complete.mmd](./conversation-flow-complete.mmd)（兩版同步維護）。
> 呈現方式說明：所有回覆都是**逐字即時顯示**（像真人打字）。
> **通路現況（2026-07-16 對 jgb2 程式查實）**：已上線進線＝業者員工（後台）＋售前訪客；租客／房東進線與**照片上傳**＝後端已建成並以 mock 驗證，**等 jgb2 前台串接後才開放**（照片放開場或流程中屬前台設計待拍板，後端兩路皆支援）。
> 最後更新：2026-07-16（逐節點對碼驗證：46 條斷言，證據見 [conversation-flow-evidence.md](./conversation-flow-evidence.md)）。

## 怎麼讀這份文件

- **圖 1 是主流程總覽**：一則訊息從進來到回覆的骨幹，每個粗框對應一張詳細圖。
- 圖 2～8 是各段落的放大圖，內容互相銜接。
- 圖示慣例：菱形＝判斷、綠色＝回覆用戶、紅色＝降級或失敗處理、紫色＝業者可自訂的部分。

---

## 圖 1｜主流程總覽

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    A(["👤 用戶送出訊息"]) --> B{"接續進行中的服務？<br/>（填表中／對話中）<br/>📄 圖 2"}
    B -->|"是"| B1["回到原本的表單或對話<br/>📄 圖 6／圖 7"]
    B -->|"否"| C{"照片報修？指定主題進來？<br/>潛在客戶？<br/>📄 圖 2"}
    C -->|"命中其中一種"| C1["直接進對應的多輪對話<br/>📄 圖 7"]
    C -->|"都不是"| D{"熱門問題？"}
    D -->|"是"| D1["✅ 立即回覆標準答案"]
    D -->|"否"| E["AI 理解問題後<br/>同時查：業者 SOP＋知識庫<br/>📄 圖 3"]
    E --> F{"哪邊比較切題？"}
    F -->|"業者 SOP"| G["照 SOP 引導處理<br/>📄 圖 4"]
    F -->|"知識庫"| H["回答，或接後續服務<br/>📄 圖 5"]
    F -->|"都不夠切題"| I["兜底：業者基本資料→真人客服<br/>📄 圖 3"]
    G & H --> J["視需要接：引導填表 📄 圖 6<br/>多輪對話 📄 圖 7｜查系統 📄 圖 8"]
    J --> K(["✅ 回覆用戶"])
    style A fill:#e0f2fe
    style K fill:#dcfce7
    style D1 fill:#dcfce7
```

---

## 圖 2｜開場判斷（由上而下攔截，命中就直接接手）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    START(["👤 用戶送出訊息"]) --> ONGOING{"1️⃣ 有正在進行中的服務？"}
    ONGOING -->|"表單填到一半"| RF["回到表單續填（圖 6）"]
    ONGOING -->|"多輪對話進行中"| RA["接續對話（圖 7）"]
    ONGOING -->|"都沒有"| ENTRYBTN{"2️⃣ 帶著指定主題進來？<br/>（特定入口／深連結參數，<br/>例：從報修頁開啟客服）"}
    ENTRYBTN -->|"是"| GATECHK
    ENTRYBTN -->|"一般輸入"| PHOTO{"3️⃣ 有附損壞照片？<br/>（🚧 前台附圖待串接）"}
    PHOTO -->|"有"| VISION["🖼️ AI 影像辨識<br/>判斷損壞的東西和嚴重程度"]
    VISION -->|"辨識出損壞"| GATECHK{"該業者有開這個功能？<br/>（例：報修開關）"}
    VISION -->|"認不出／非損壞照片"| RVIS["🙋 請改用文字描述<br/>或提供更清晰的照片"]
    GATECHK -->|"有開"| GO["進入申辦對話（圖 7）"]
    GATECHK -->|"關閉"| RGATE["🙋 說明此服務未開放<br/>引導聯絡客服"]
    PHOTO -->|"沒有"| WHO{"4️⃣ 是潛在客戶嗎？（還不是會員）"}
    WHO -->|"是"| PS["進入售前諮詢（圖 7）"]
    WHO -->|"否"| HOT{"5️⃣ 最近答過的熱門問題？"}
    HOT -->|"是"| R1["✅ 立即回覆標準答案"]
    HOT -->|"否"| UNDERSTAND["AI 先理解問題（改寫口語、判斷意圖）<br/>一句話同時問到多件事也能一起判斷<br/>（以主要問題為主，可帶到相關主題）"]
    UNDERSTAND --> STAFF{"6️⃣ 是業者員工嗎？"}
    STAFF -->|"租客／房東"| TOSEARCH["同時查 SOP＋知識庫（圖 3）"]
    STAFF -->|"業者員工"| STAFFKB["查 JGB 平台系統操作知識庫<br/>（平台共通、不分業者，按角色給內容；<br/>無 SOP、無表單，可進入查詢診斷對話）"] --> TOKB["依知識設定接後續（圖 5）"]
    style R1 fill:#dcfce7
    style RGATE fill:#ffe4e6
    style RVIS fill:#ffe4e6
```

---

## 圖 3｜找答案與裁決（租客／房東）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    SEARCH["🔍 同時查兩個來源：<br/>業者 SOP（該業者自訂）<br/>＋知識庫（平台共通為主，可加掛業者專屬）"]
    SEARCH --> JUDGE{"哪邊的答案比較切題？<br/>（都切題時，有後續服務的優先<br/>→ 業者客製壓過平台通用）"}
    JUDGE -->|"業者 SOP 較切題"| SOP["走 SOP 路線（圖 4）"]
    JUDGE -->|"知識庫較切題"| KB["走一般問答路線（圖 5）"]
    JUDGE -->|"兩邊都不夠切題"| PARAMTRY{"問的是業者基本資料？<br/>（電話、營業時間、地址⋯）"}
    PARAMTRY -->|"是"| RPARAM["✅ 用業者登錄的資料直接答"]
    PARAMTRY -->|"否"| R4["🙋 禮貌說明沒有把握回答<br/>並提供真人客服管道"]
    style RPARAM fill:#dcfce7
    style R4 fill:#ffe4e6
```

---

## 圖 4｜路線一：業者 SOP（各業者自訂的處理流程）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    SOPSHOW["先照 SOP 說明處理步驟<br/>（例：冷氣不冷 → 先檢查濾網）"] --> SOPMODE{"這條 SOP 設定的接手方式？"}
    SOPMODE -->|"純說明，不接服務"| R2["✅ 回覆處理步驟"]
    SOPMODE -->|"等用戶開口"| SOPWAIT["等用戶說「試過了還是不行」<br/>這類關鍵字才接手"]
    SOPMODE -->|"主動詢問"| SOPASKGO["主動問一句：<br/>「需要幫您安排處理嗎？」<br/>（反問、答非所問、或回一長串<br/>像在講新的事，都不算同意）"]
    SOPWAIT -->|"用戶開口了"| SOPNEXT{"接手後做什麼？（依 SOP 設定）"}
    SOPWAIT -->|"用戶沒再反應"| R2
    SOPASKGO -->|"用戶說好"| SOPNEXT
    SOPASKGO -->|"用戶說不用"| R2
    SOPNEXT -->|"幫用戶填資料（填完可自動送出）"| F["引導填表（圖 6）"]
    SOPNEXT -->|"幫用戶查系統"| Q["查系統（圖 8）"]
    style R2 fill:#dcfce7
```

---

## 圖 5｜路線二：一般問答（知識庫）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    KTYPE{"這則知識設定的後續動作？"}
    KTYPE -->|"直接回答"| POLISH["AI 把答案整理成親切好讀的說法<br/>需要時綜合多則知識"] --> BRAND["帶入該業者的名稱、<br/>客服電話、營業時間"] --> R3["✅ 回覆答案"]
    KTYPE -->|"需要收集資料（依設定：直接開始／<br/>先問一句同意／等特定關鍵字）"| F["引導填表（圖 6）"]
    KTYPE -->|"需要查系統"| Q["查系統（圖 8）"]
    KTYPE -->|"需要多輪釐清<br/>（問題夠明確、且該主題<br/>有設定多輪劇本才轉）"| A["多輪對話（圖 7）"]
    style R3 fill:#dcfce7
```

---

## 圖 6｜路線三：引導填表

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    COLLECT["一次問一項，逐步收集<br/>每一項都檢查格式（電話、日期⋯）"]
    COLLECT -.-> DIGRESS["中途問別的問題 → 先回答，<br/>再問你要不要繼續填（說「繼續」才回表單）<br/>說「不填了」→ 隨時可取消<br/>放著不理 → 暫停，回來能接著填<br/>（30 分自動清理已寫成、尚未啟用）"]
    COLLECT --> REVIEW["全部填完 → 給摘要請用戶確認<br/>可逐項修改，確認才送出"]
    REVIEW -->|"取消"| R5["✅ 取消，資料不送出"]
    REVIEW -->|"確認送出"| AFTERFORM{"送出後接什麼？（依表單設定）"}
    AFTERFORM -->|"查系統／建立資料（失敗最多重試 2 次，<br/>試滿依失敗原因說明後結束）"| Q["查系統（圖 8）"]
    AFTERFORM -->|"顯示相關說明"| R6["✅ 回覆結果"]
    AFTERFORM -->|"依答案分岔接下一份表單<br/>（例：報修後追問金流，最多接 3 層）"| COLLECT
    style R5 fill:#dcfce7
    style R6 fill:#dcfce7
```

---

## 圖 7｜路線四：智慧多輪對話（同一顆引擎，三種用途）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    subgraph USES["三種用途"]
        direction LR
        PRESALE["💼 售前諮詢（潛在客戶）<br/>介紹平台服務與方案<br/>不碰個資、不報價、競品保持中立"]
        DIAG["🩺 查詢診斷類（租客／房東／業者員工）<br/>合約、帳單、帳號、電表、物件⋯<br/>自動調閱真實資料：剛好一筆→直接說明<br/>多筆→列出來請你選（選不出來會再問一次）<br/>查不到→反問確認<br/>AI 只負責把事實講清楚，不編造數字"]
        TX["📝 申辦類（例：報修）"]
    end
    PRESALE --> R10["✅ 回覆諮詢（可繼續追問）"]
    DIAG --> R11["✅ 依真實資料說明（可繼續追問）"]
    TX --> AGENTSTART["自動帶入該用戶的租約與房屋資料<br/>照片辨識結果也自動填入<br/>➡️ 已知的不重複問"]
    AGENTSTART --> ASKMISS["只問缺少的資訊（例：急不急？）<br/>中途岔題也會先回答再繼續<br/>對話中再上傳照片也會自動併入"]
    ASKMISS --> CONFIRM{"送出前一定先給摘要請用戶確認<br/>（要修改就改，改完再確認；<br/>回答模糊時寧可再問，不會擅自送出）"}
    CONFIRM -->|"✅ 確認"| EXEC["確認後才真正建立報修單"]
    CONFIRM -->|"取消"| R7["✅ 取消，不留半筆資料"]
    EXEC -->|"成功"| R8["✅ 回覆報修單號＋後續追蹤方式<br/>（再按一次也不會重複建單）"]
    EXEC -->|"失敗"| FAIL["⚠️ 誠實告知失敗、提供重試<br/>絕不假裝成功"]
    SWITCHN["中途換主題？→ 自動換到對的服務重新處理"]
    USES -.-> SWITCHN
    style R7 fill:#dcfce7
    style R8 fill:#dcfce7
    style R10 fill:#dcfce7
    style R11 fill:#dcfce7
    style FAIL fill:#ffe4e6
```

---

## 圖 8｜查系統（平台正式資料）

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    QUERY["🔎 查詢平台正式資料<br/>（合約、帳單、修繕進度、電表⋯）<br/>用固定格式呈現，數字不經 AI 改寫<br/>一定核對用戶身分，只給本人資料<br/>身分或參數不足 → 明說缺什麼才能查"]
    QUERY --> R9["✅ 回覆查詢結果"]
    style R9 fill:#dcfce7
```

---

## 圖 9｜資料層：內容從哪裡來、業者能客製什麼

> 這一層不是流程的「一步」，而是前面所有路線**隨時取用的資料架**——所以它沒有自己的後續，箭頭指向它的，就是在用它的那些流程。

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"18px"}}}%%
flowchart TB
    U1["找答案（圖 3）"]
    U2["業者員工問答（圖 2）"]
    U3["售前諮詢（圖 7）"]
    U4["多輪對話（圖 7）"]
    subgraph KBCOMP["📚 知識庫的組成（同一個知識庫，平台共通，按「角色」分區隔離）"]
        direction LR
        KBT["租客／房東區<br/>FAQ、服務與<br/>平台使用知識"]
        KBPM["JGB 系統操作區<br/>（給業者員工的<br/>後台操作知識）"]
        KBPS["售前介紹區<br/>（給潛在客戶的<br/>服務與方案說明）"]
        KBRULE["多輪對話設定區（劇本）<br/>查詢型：合約、帳單、電表⋯<br/>申辦型：報修建單<br/>售前型：服務諮詢"]
    end
    U1 -. "查" .-> KBT
    U2 -. "查" .-> KBPM
    U3 -. "查" .-> KBPS
    U4 -. "載入劇本" .-> KBRULE
    C1["找答案（圖 3）"]
    C2["一般問答帶入參數（圖 5）"]
    C3["功能開關檢查（圖 2）"]
    C4["查系統（圖 8）"]
    C5["每一則訊息（全程）"]
    subgraph VENDORLAYER["🏢 業者客製層（在這些點介入；內容主體是平台共通，所有業者共用）"]
        direction LR
        VKB["業者 SOP＝完全業者自訂<br/>知識庫＝平台共通為主，可加掛業者專屬<br/>（專屬內容只有該業者看得到，<br/>並依業態只出現該出現的）"]
        VPARAM["業者參數<br/>（公司名稱、客服電話、營業時間）"]
        VSWITCH["功能開關<br/>（例：報修功能可整個關閉，<br/>關閉時改引導找客服）"]
        VDATA["業者資料集<br/>（例：社區、店點清單）"]
        VQUOTA["用量計量與額度管制<br/>（每則對話都計量，<br/>接近上限自動通知業者）"]
    end
    C1 -. "取用" .-> VKB
    C2 -. "帶入" .-> VPARAM
    C3 -. "查開關" .-> VSWITCH
    C4 -. "取用" .-> VDATA
    C5 -. "計量" .-> VQUOTA
    OUT["✅ 用戶收到的每則回覆＝<br/>知識／SOP 文本 ＋ 業者參數與文案 ＋ 平台正式資料（圖 8）<br/>AI 只負責措辭組裝（追問／兜底等引導語除外）"]
    KBCOMP == "內容成為回覆" ==> OUT
    VENDORLAYER == "參數與文案嵌入回覆" ==> OUT
    classDef vendor fill:#ede9fe,stroke:#7c3aed
    class VKB,VPARAM,VSWITCH,VDATA,VQUOTA vendor
    style OUT fill:#dcfce7,stroke:#16a34a
```

---

## 附註（完整性聲明）

- 本文件涵蓋全部對話機制：開場攔截、熱門秒回、SOP（三種接手方式）、一般問答、引導填表（含離題、暫停、修改、接續表單）、多輪對話（售前／診斷／申辦）、查系統、兜底、業者客製與知識庫組成。
- 刻意不畫的內部實作：相似度門檻數值、快取層數結構、AI 模型參數、檢索工程細節——這些不影響用戶可感知的行為，技術版都有。
- 單張合併大圖（工程用）：[conversation-flow-complete.mmd](./conversation-flow-complete.mmd)。
