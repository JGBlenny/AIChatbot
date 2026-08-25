# JGB 資料保真架構與任務定義

> 2026-08-26｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> 目的：先把**架構**講清楚，再從架構推出**任務**。避免像先前那樣做到哪算到哪。
> 本檔是任務的唯一來源；`transport-migration-inventory.md` 是端點層的進度帳本。

## 一、架構：一筆事實從 jgb2 走到使用者嘴邊，會經過幾層

```text
┌ jgb2（PHP／Laravel）＝ 規則與資料的唯一權威 ─────────────────────────┐
│ ① DDL           欄位型別／nullable／預設        ⚠️ 建表 migration 不在 repo │
│ ② $casts        Eloquent 型別轉換                                        │
│ ③ accessor      getXxxAttribute 改寫輸出                                  │
│ ④ controller    恆定 where／參數篩選／投影／衍生欄位／回應信封             │
└──────────────────────────── HTTP JSON ────────────────────────────────┘
                                  │  /api/external/v1/*（22 條路由）
┌ rag-orchestrator ────────────────┼────────────────────────────────────┐
│ ⑤ adapter    JGBSystemAPI 的 22 個公開方法                              │
│              · 3 個走 transport 替身（bills／bill_detail／contracts）     │
│              · 其餘走方法級 mock；`use_mock` 決定分支                    │
│ ⑥ registry   api_call_handler.api_registry：endpoint key → adapter 方法  │
│ ⑦ 領域層     services/jgb/*.py：把 API 列組成**決定性 facts**            │
│              （bills／contracts／estates／invoices／payments／accounts／  │
│                iot／subscription／repair_prefill）                        │
│ ⑧ Brain      只組話，不算事實                                            │
└──────────────────────────────────────────────────────────────────────┘
┌ 設定層（DB，後台可編，**不在 repo**）────────────────────────────────┐
│ conversational_configs／knowledge_base.api_config／form_schemas／        │
│ vendor_sop_items.next_api_config → 決定哪個面向在什麼時候叫哪個 key      │
└──────────────────────────────────────────────────────────────────────┘
```

**兩條容易被忽略的事實**

1. **值的形狀不是 controller 決定的**：①②③ 都會改寫輸出。今天抓到的
   `facilities`／`fees` 空值回 `[]`（accessor）、`size_data` 是 JSON **字串**（無 cast）
   都在這一層。只讀 controller ＝ 只證了一半。
2. **消費端契約是獨立的一層**：⑦ 讀哪些鍵，和 ④ 回哪些鍵，是兩件事。
   今天三個「線上靜默失效」全部出在這條縫（`data`／`response`／`response_data`）。

## 二、保真度的四個維度（判準，不是形容詞）

```text
D1 投影鍵集合   formatX() 逐鍵；多一鍵是捏造、少一鍵是失真
D2 過濾語義     恆定 where ＋ 參數解析（含 production 怪癖：靜默忽略、白名單回退、intval）
D3 值形狀       DDL → $casts → accessor → controller 加工（(float)／三態／0→null）
D4 回應信封     data／mapping／pagination／自訂鍵（payment-logs 就沒有 data）
D5 消費端契約   ⑦ 實際讀的鍵，必須存在於 D1，且語義一致
```

## 三、證據等級（決定一件事「證得了／證不了」）

```text
E1 讀 jgb2 原始碼可證     契約（D1-D4）——不必連線、不花錢
E2 替身可測               行為（過濾、排序、分頁、消費端串接）
E3 只有真 API 能證         權限圈定、403/404 之分、延遲與錯誤碼、快取陳舊
E4 只有 production 資料能證 真實分佈（標題格式、null 比例、狀態組合、量級）
```

**紀律**：E3／E4 的事情**不得**用 E2 的綠燈宣稱已證；替身模擬不到的，寧可拒答
（`UnsupportedMockParameterError` 的用途），不得靜默忽略後回一個看起來像答案的東西。

## 四、任務（每項含：產出、驗收、依賴、不做什麼）

### T1 補完端點層盤查（剩 2 個）

```text
T1.1 jgb_tenant_registration（TenantApiController@registrationStatus，168 行）
     產出：稽核段落＋具名測試；驗收：D1-D4 四維度各有對照，測試引用行號
T1.2 jgb_create_repair（RepairApiController@store，485 行，**寫入端點**）
     ⚠️ 先產出「mock 寫入語義定義」：回什麼算成功／要不要模擬副作用／
        重送與冪等怎麼表現／失敗碼怎麼折疊。**定義先審過再實作**
依賴：無｜不做：不在此順手改 repair 面向的對話行為
```

### T2 消費端契約全掃（**最高優先**）

```text
理由：今天三個線上靜默失效全部是 D5 類，而且都是「mock 全綠、production 無聲失能」。
方法：對 services/jgb/*.py 逐檔列出**實際讀取的鍵**（含巢狀），
      逐鍵比對該 endpoint 的 formatX() 投影：
        · 讀了 production 不回的鍵 → P0（今天已找到 3 個：data／response／response_data）
        · 讀了但語義不同（如 character_name vs character.name）→ P0
        · 投影有、消費端沒用到 → 記錄即可，不動
產出：一張 formatter × endpoint 的鍵對照表＋每個 P0 的修法與測試
驗收：表格覆蓋 services/jgb/ 全部檔案；每個 P0 有一條會紅的測試
依賴：T1 不必先做｜不做：不改對話措辭，只修鍵與取值
```

### T3 情境覆蓋（把「形狀對」升級成「分支走得到」）

```text
T3.1 checkin-eligibility 三個 blocker 分支＋「無帳單」label＋押金兩條計算路（GAP-C1）
T3.2 帳單／合約既有面向的失敗態（逾期、作廢、提前解約中）是否都有替身資料
T3.3 每個面向至少一條「查無」情境（sentinel 口徑）——estates 已做，其餘未檢查
產出：每個情境一條具名測試；驗收：情境清單逐項打勾，未做的標 GAP
依賴：T2 之後做較省（可能一起改）｜不做：不為了情境去改凍結的 C4a／C4b 資產
```

### T4 fixture 宇宙連通（解 GAP-B1／GAP-I1）

```text
現況：bills(900001-3) 掛在合約 700100/700200，contracts fixture 是 678/600，
      estates 是 54126/54200/54305——三個宇宙互不連通，
      故所有跨表過濾（bills.user_id、invoices.user_id）**只能忽略**。
產出：一份「連通方案」——改哪一邊的 id、影響哪些既有斷言、C4a 凍結資產怎麼處理
⚠️ 需要業主授權：會動到 C4a 已凍結的 fixture 值（5.x 的 covered bytes 會失效）
驗收：連通後 bills/invoices 的 user_id 過濾各有一條會咬的測試
依賴：T2、T3 之後；不做：在未授權前改動任何凍結資產
```

### T5 transport 遷移擴張

```text
把已稽核且無跨表依賴的端點移進 MIGRATED_ENDPOINTS（estates／invoices／meters 優先），
沿用 4.3 的三態 admission gate（不得 fallback 真網路）。
產出：fixture 模組＋路由＋admission 測試；驗收：mock 模式下真的走 transport（spy 可證）
依賴：T4（跨表過濾若要正確，需先連通）｜不做：一次全遷
```

### T6 Real API Contract Smoke（E3）

```text
用真 API key 對 external/v1 每個端點各打一次，比對**回應鍵集**與我方投影、
以及 403／404／400 的實際行為。這是唯一能一次證掉 D1 漂移與錯誤碼的手段。
⚠️ 需要業主授權（真 key、可能碰 staging）；指令逐條給、由業主執行
產出：鍵集 diff 報告；驗收：每個端點的 D1 有真 API 佐證或明確標記未取得
```

### T7 分佈校準（E4）

```text
線上**聚合式**唯讀查詢（長度分佈、null 比例、狀態計數、分位數），
用統計調整 fixture 的代表性。⚠️ 個資紅線：不得逐列 dump、不得把真值寫進 repo 或對話。
⚠️ 由業主執行；優先走 jgb2 既有的 internal/v1 唯讀 API
產出：分佈摘要＋fixture 調整；驗收：「真實分佈」從各稽核檔的未涵蓋清單移除
```

### T8 反漂移機制回歸（本檔的自我保護）

```text
問題：六步協議在第 2 份稽核檔之後退化成自由結構（§11 已記錄）。
產出：稽核檔模板（六段標題固定）＋一條 _meta 測試：
      `.kiro/specs/**/**-source-audit.md` 必須含六個段落標題，缺一即紅。
驗收：把現有四份稽核檔補成模板格式後，該測試全綠
依賴：無｜這是唯一能讓「少一項一眼看得出來」重新成立的做法
```

## 五、排序與門檻

```text
不需授權、不花錢、可直接做：T2 → T8 → T3 → T1
需要授權（碰凍結資產）：T4
需要授權（真 key／碰線上）：T6、T7
T5 夾在中間：技術上隨時能做，但跨表過濾要等 T4 才會正確
```

## 六、這份任務單怎麼防漂

```text
· 每項任務的「驗收」都寫成**可機械檢查**的東西（測試會紅／表格逐項打勾／鍵集 diff）
· 任務只在三種情況下可以停：需要授權、需要花錢、發現的問題超出替身層需要產品決策
· 停下來時必須在本檔標記狀態，不得只在對話裡講
```
