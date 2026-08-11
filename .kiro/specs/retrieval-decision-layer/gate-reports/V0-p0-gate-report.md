# V0｜P0 階段關卡報告（決策集中化＋評測底座）——呈業主簽核

> 2026-08-11｜涵蓋任務：1.1 評測 harness、1.2 決策快照埋點、1.3 行為等價搬移、1.4 E-5 歸因
> commit：`77c1d9f`（1.1＋1.2）、`bfc504d`（1.3）＋本報告批次｜分支 `spec/retrieval-decision-layer`（未 push）
> 關卡主張：**①門檻收進單一模組後路由行為零漂移；②E-5 已歸因、上限提案待核**
> 簽核後才進 P1。E-5 上限（≤3/104 中位）核定後寫入 design.md 不得放寬。

## 欄 1｜真實情境逐字

**判準（先定標準）**：V0 是「沒變壞」關卡——同一輪在搬移前（b 輪）與搬移後（a 輪）的
路由類別多數決必須一致；判準門檻＝多數決不一致輪數 ≤ 基線重跑變異 5/107（凍結
run2 vs run3、rc-v1 同尺）。以下逐字皆為系統原始輸出，未改寫。

### 案 A｜#04 T2（帶編號帳單查詢——最常見路徑，前後一致）PASS
- 使用者原句：`608169`（T1 先問「查帳單ID608169」被索取識別後補號）
- 搬移前 b1：「帳單「充洋-512」的資訊如下：  - **狀態**：已繳費 - **金額**：NT$ 140,047 - **繳費期限**：2026/03/10 …」
- 搬移後 a1：「帳單「充洋-512」的資訊如下：  - 狀態：已繳費 - 金額：NT$ 140,047 - 繳費期限：2026/03/10 …」
- 判準：金額、狀態、期限逐項同值，路由類別同為 ANSWER（措辭/粗體差異屬 LLM 生成層，R8.4 不苛求逐字）→ **PASS**

### 案 B｜#18 T2（帶編號知識題——病灶輪，前後同樣病）PASS（等價視角）
- 使用者原句：`合約 ID 64488（紙本合約）續約 12 個月後，在帳單頁找不到續約後的帳單，詢問原因（年繳）。`
- 搬移前 b1/b2/b3 與搬移後 a1/a2：「查無對應的資料，請再確認一下識別資訊（如編號或名稱）是否正確？」（FACET_EMPTY）
- 搬移後 a3（同輸入偶發翻動）：「合約帳單管理 查詢統計  業者查詢與管理合約帳單：（1）合約管理：…」（ANSWER）
- 判準：此輪 10 樣本量測翻動率 7:3（歸因報告實驗①），**搬移前後病灶原樣保留、未惡化未偷修**——多數決兩側皆 FACET_EMPTY → 等價 **PASS**。（把它修好是 P1 任務 2.1 的驗收，不是 V0。）

### 案 C｜#07 T4（面向黏著——E-5 初翻點現場逐字）
- 使用者原句：`我要如何設定線上金流？`（前三輪在 bill_diagnosis 問帳單）
- 9/10 輪（正常切題，進 billing_setup_guide）：「請問您是否已經開通新的收款帳戶驗證？」
- 1/10 輪（黏著，a2）：「目前我們專注於帳單操作問題。如果您有其他問題，建議聯繫客服或查看我們的幫助中心。請提供帳單編號，以便查詢該帳單的目前狀態。」→ 之後 T5–T8 五輪全場索編號
- 判準：這是歸因報告主結論的逐字現場（黏著單點翻動→級聯 ×5），供上限提案核定參考。

### 案 D｜多數決唯一不一致輪 #11 T15（預先聲明的灰帶輪）
- 使用者原句：`修改成三個月`（17 輪長對話第 15 輪）
- before 三輪：ANSWER／ANSWER／ASK_ID；after 三輪：ASK_ID／ASK_ID／ANSWER（10 樣本擴測：ASK_ID 3：ANSWER 4：FALLBACK 3——三類擲骰）
- 判準：兩側各自輪內就不穩，屬 E-5 既有病灶輪，不歸罪搬移；計入不一致 1/107 ≤ 5/107 → 總判準 **PASS**

## 欄 2｜重現指令（業主可自行戳穿）

```bash
# 前置：逐字稿自 S3 取回（reports/ 已 gitignore）
cd /Users/lenny/jgb/AIChatbot
aws s3 sync s3://jgb2-production-upload/assistant-reports/ \
  docs/backtest/corpus-20260810/reports/ --exclude '*' --include '*.md'

# 全量重播一輪（三道前置閘門：audit 不變量 3／語料樹雜湊／CACHE_ENABLED 實測核對）
python3 rag-orchestrator/scripts/backtest/decision_replay.py --cache-mode off --tag backtest_x1

# 只重播 #18（抽一案獨立戳穿）
python3 rag-orchestrator/scripts/backtest/decision_replay.py --cache-mode off --tag backtest_x18 --only 18

# 單輪 curl（#18 T2 原句、b2b 形狀同 harness；session 自取）
curl -s -X POST http://localhost:8100/api/v1/message -H 'Content-Type: application/json' -d '{
  "message":"合約 ID 64488（紙本合約）續約 12 個月後，在帳單頁找不到續約後的帳單，詢問原因（年繳）。",
  "mode":"b2b","target_user":"property_manager","session_id":"owner_probe_18","role_id":"93920","user_id":"93920"}'

# 決策快照回查（跑完上面 curl 後）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
 "SELECT facet_event, decision_snapshot FROM usage_events WHERE session_id='owner_probe_18' ORDER BY ts DESC LIMIT 1"

# 多數決比較重算（獨立腳本邏輯見欄 5 fresh 代理——或以任意語言自 JSON 重算）
```

## 欄 3｜原始輸出位置（可稽核工件）

| 工件 | 位置 |
|---|---|
| 等價重播 6 輪（b1–b3／a1–a3）全量 JSON＋log | S3 `s3://jgb2-production-upload/aichatbot/eval-corpus/corpus-20260810/task13-equiv-replay-20260811.tar.gz`（sha256 `6ebf25ca68e8c9ac850df2791d285cfbac91ee6886100189d0a6e3649d566fd9`）；本機 `docs/backtest/corpus-20260810/out_backtest_{b1,b2,b3,a1,a2,a3}_cacheoff/` |
| 歸因加測 7 輪（n1–n7，5 案）＋元件 ×10 腳本＋快照匯出 | S3 `.../task14-attribution-20260811.tar.gz`（sha256 見同名 .sha256）；本機 `out_backtest_n{1..7}_cacheoff/` |
| 決策快照原始列 | 本機 dev DB `usage_events WHERE session_id LIKE 'backtest_a%'`（321 列，含 176 快照＋91 面向事件）；匯出檔 `a_events.psv` 在歸因歸檔包內 |
| 嚴格等價測試 | `rag-orchestrator/tests/unit/decision/test_decision_layer_equivalence_req.py`（26,912 格對拍，`scripts/run-tests.sh unit tests/unit/decision/` 可重跑） |
| E-5 歸因報告全文 | `.kiro/specs/retrieval-decision-layer/e5-attribution-report.md` |

## 欄 4｜未驗清單（顯式）

1. **快取 on 軌未跑**：R1.7 雙軌中 cache-on 組尚未量測——C8 快取修正是 P1 任務 2.3，
   修正前跑 cache-on 只會量到已知的快取汙染；P1 收案（V1）補雙軌。
2. **六 case 仲裁的 live 路徑未被凍結語料覆蓋**：凍結語料全走 b2b 短路（不進六 case）。
   六 case 等價由 26,912 格參考實作對拍＋整合測試承擔；b2c live 行為未在本階段實跑。
3. **FORM 類別對凍結舊檔（run2/run3）不可判**：舊檔未記 form_triggered 結構欄位，
   重判時 FORM 永不成立（新跑輪已記錄，harness 註解與 unit 有明示）。
4. **面向內續輪無決策快照**：快照覆蓋仲裁點＋進場事件（176/321），引擎內每輪的
   ask/answer 決策未快照——屬 C3（任務 2.2）逃生門事件範圍。
5. **integration 5 失敗為既有環境性**（facet_entry_routing 5/83；stash 基線對照搬移前
   後逐項相同）——非本次引入，屬本機 KB=0.65 組態下的灰帶題既有債，列 P1 觀察。
6. **E-5 上限量測綁 rc-v1 分類器**：與立案值 13%（人工判讀尺）不同尺；分類器第六類
   FACET_CLARIFY（面向內澄清）擴充案待業主裁決，若採納需重測基線。
7. **自驗與獨立驗證邊界**：歸因實驗（①②③）之設計與判讀為主 session 自做；獨立驗證
   覆蓋的是欄 5 四項可機械覆核宣稱，歸因**判讀**本身未經獨立代理複核。

## 欄 5｜fresh 代理獨立驗證紀錄

**狀態：四項全數獨立 CONFIRMED。**

時間線如實記錄：首派 verifier 1 小時無回報，依 08-10 前例先行判定凍結並以「未獨立驗證」
呈報（commit f9b5a1d 版本）；業主裁示「要驗完」後改小探分段重派；**原代理其後於 2.8 小時
完成全部四項**（未凍結、屬極慢——判定過早，於此更正），分段代理亦陸續回報。每項皆有
獨立代理自寫腳本重算（未用主 session 任何比較腳本）：

1. **多數決比較｜CONFIRMED**（原代理逐字）：「六個目錄各 37 個案例 JSON…各 107 筆
   turn_results…差異輪數 1/107、位置 #11 T15、UNSTABLE=0，三項全數吻合」；鍵集合
   union 107／intersection 107 無缺漏。DIFF 明細：`('11',15) before=ANSWER
   [ANSWER,ANSWER,ASK_ID] → after=ASK_ID [ASK_ID,ASK_ID,ANSWER]`。
2. **unit 全綠｜CONFIRMED**（原代理＋分段代理雙確認）：「953 passed, 266 deselected,
   7 warnings」；確認於容器內執行（輸出路徑 /app/…）。
3. **不變量 8｜CONFIRMED**（原代理＋分段代理雙確認）：兩個 env 鍵讀值僅
   decision_layer.py:47-48；六 case 常數在 chat.py「不只無賦值定義，連引用都沒有」，
   全 repo 只在 decision_layer.py 與等價測試的參照實作出現。
4. **決策快照落庫｜CONFIRMED**（原代理＋分段代理雙確認）：
   `enter|b2b_knowledge_only|dl-v1|…`；原代理另查證非殘留（該 session 僅 1 筆、
   寫入時間為查詢前 20 秒）。

代理另附兩則非阻斷 advisory，與主 session 歸因報告互相印證、無新增風險：
- A-1（P3）：clarify_question 欄 3 輪多數決在此欄位不具鑑別力（同側自身噪音
  21/20 輪）——與歸因報告「clarify 尺 19=19、不作 gate 只作觀測」的處置一致。
- A-2（P4）：after 側輪內非全一致 7→11/107，落二項噪音內——與歸因報告
  「判讀為抽樣噪音」一致；若在意加輪次重測。

## 簽核請求

1. **V0 等價主張**：多數決不一致 1/107 ≤ 5/107，六 case 嚴格等價全網格通過——請裁決是否過關。
2. **E-5 目標上限**：`rc-v1` 尺、104 輪母體、3 輪 pairwise 中位數 **≤ 3/104**——請核定或改值；核定後寫入 design.md。
3. **附帶裁決**：評測分類器是否增設第六類 `FACET_CLARIFY`（面向內澄清問句；現歸 ANSWER＋旗標）——影響 P1 起的所有量測，採納則基線重測。
