# 實作任務：conversational-routing-execution

> 建立 2026-08-23｜語言 zh-TW
> 來源：[requirements.md](./requirements.md)（Req.1–10）、[design.md](./design.md) v1.6、[research.md](./research.md)
> ⚠️ `.kiro/settings/rules/tasks-generation.md`、`tasks-parallel-analysis.md`、
> `templates/specs/tasks.md` **均不存在**，本文件採標準 kiro 任務格式（兩層、數字需求 ID）。

---

## 註記圖例

| 註記 | 意義 | 判準 |
|---|---|---|
| **⚡F** | **可交 Fable 執行** | 全機械、brief 可一次寫完、**無設計判斷**；產物對錯可由既有斷言或契約當場判定 |
| **🧠主** | **須主 session 親自做** | 診斷、判型、裁決、跨元件整合；或本 spec 明訂「不得預設處置」者 |
| **🔍V** | **完成後須獨立代理驗證** | 觸發獨立審查條件：安全邊界／資料寫入／外部副作用／驗收結論所依賴 |
| **(P)** | 可與同層其他 (P) 任務並行 | 無共享檔案、無順序依賴 |

> ⚠️ **⚡F 的鐵則**：交付 Fable 的 brief 必須自帶完整契約與驗收條件。
> 凡需要「先讀碼判斷再決定怎麼寫」的任務一律不掛 ⚡F——
> 那是判型工作，錯誤會被下游當成事實。
>
> ⚠️ **🔍V 的鐵則**：驗證代理收到的是**明確的宣稱**與相關 diff／路徑，不是「幫我看看」。
> 自驗不作收案證據（本 spec 已三次證實）。

---

## 執行順序（依 design.md 的依賴 DAG）

```text
任務 1 ─┬─ 任務 2 ──────────────┐
        │                        ├─ 任務 5（C4a）─┬─ 任務 6（C4b／上線 gate）
        ├─ 任務 3 (P) ───────────┤                ├─ 任務 7（skip_refine）
        └─ 任務 4 (P) ──────────┘                 ├─ 任務 8（step 契約）
                                                   └─ 任務 9（repair_create）
                                                          ↓
                                              任務 10（文件分層）→ 任務 11（品質基準）
任務 12（contract smoke）＝橫向，任務 4 後任意時點
```

⚠️ **不得依編號順序執行**：任務 4（mock 契約）是任務 5（C4a）可驗的前提［需求優先序段］。

---

## 1. 測試執行入口供裝與失效可見性

**目標**：使 `make test-integration` / `make test-e2e` 在結構上有能力真正執行，
且「因環境略過」「因標記未啟用略過」「真的跑完且全過」三者在輸出與退出碼上可分辨。

**狀態（2026-08-23）**：

```text
1.1–1.12  COMPLETE — Requirement 1 機制鏈 PASS
          （1.6 獨立驗證 CONFIRMED；1.10 三層守門結構完成；
            1.7 以 105/58/24、gate_skipped=0、rc=1 結案）
```

**Task 1 最終形成的守門結構**（三層，非單點）：

```text
L1  runner intent      REQUESTED_TEST_LAYERS（宣告「要跑什麼」）
L2  pytest actual      selected items（實際「會跑什麼」）      ← L1 與 L2 互相校驗
L3  runner contract    unit 測試鎖 LAYER→selection→宣告→旗標 四者成套
```

不是「runner 告訴守門自己要跑什麼，守門相信它」。

**獨立驗證（1.6 🔍V）結論：CONFIRMED**。四條宣稱皆以真實測試套件實跑驗過——
rc=10 穿透 CI 吞噬（183 skipped 場景，`STEP_EXIT=1`）；rc=1 仍不擋（18 failed／160 env-skip，`STEP_EXIT=0`）；
`continue-on-error` 已移除且無其他吞噬路徑（YAML parse 而非 grep 目視）；
skip 分類器實跑確認未失效（160 筆 DB 不可達全歸 `[env]`，0 筆誤歸 `[gate]`）。
另驗出一條未被列入宣稱但關鍵的優先序：結構性失效與測試失敗並存時 **10 勝過 1**。

**未處置的 advisory**（見文末「已知 advisory」）：A2（守門可自我停用）待業主裁示；
A4（移除 job 級 `continue-on-error` 使 `pip install` 暫時性故障會擋合併）待業主知情裁示。

> ⚠️ **實作期已發現並修正一個假綠燈**：design.md 原訂分類器為
> `reason.startswith("[gate]")`，但 pytest 實際在 reason 前加 `"Skipped: "`
> （實測 `longrepr[2] == 'Skipped: [gate] …'`），該判斷**恆為 False** →
> gate-skip 恆為 0 → **空跑守門變成永遠通過的不變量**。
> 已於 `conftest.py` 剝除該前綴後比對，並以三情境實跑確認 `gate_skipped=1` 真的出現。
> **教訓**：新增不變量時，必須先證明它在「該失敗的情境」下真的會失敗（negative control），
> 否則新增的是一個假綠燈，而非一道守門。

- [x] 1.1 **⚡F** 於 `scripts/run-tests.sh` 依 `LAYER` 注入測試旗標至 `docker compose run -e`：
  `integration → RUN_INTEGRATION=1`、`e2e → RUN_E2E=1`、`all → 兩者`、`unit → 皆不注入`。
  注入規則為決定性查表，不得用啟發式判斷。
  _Requirements: 1.1, 1.5_

- [x] 1.2 **⚡F** 於 `docker-compose.dev.yml` 加入 external network `aichatbot_default`，
  使測試容器可解析 `DB_HOST=postgres`（該 alias 已實查存在於該網路，無須改連線設定）。
  _Requirements: 1.2_

- [x] 1.3 **⚡F** 使兩類 skip 在輸出上可分辨：於 `tests/conftest.py` 為 **gate skip**
  （`pytest_collection_modifyitems` 內的兩處）加 `[gate]` 前綴；
  並於 `pytest.ini` 的 `addopts` 加 `-ra` 使 skip 原因進入摘要。
  ⚠️ **實作方式（v1.6 細化）**：分類採「reason 以 `[gate]` 開頭者為 gate，其餘為 env」，
  **不逐一改動 69 處測試檔內的 `pytest.skip()`**——那些是各測試自己的環境判定，
  改它們違反「既有測試判定邏輯零改動」。env 前綴由摘要 hook 於顯示時補上。
  _Requirements: 1.3_

- [x] 1.4 **🧠主** 實作空跑守門：以 `pytest_sessionfinish` 判定「被請求層的 gate-skip 數 == 0」，
  違反則設 `EXIT_STRUCTURAL_FAILURE = 10`（避開 pytest 保留的 0–5）。
  退出碼在此決定，**shell 不得解析人類可讀 summary**。
  _Requirements: 1.4_

- [x] 1.5 **🧠主** 定案 CI 與本地入口分工（design.md 元件 1-C）：
  不變量（旗標語義、skip 型別、空跑守門、DB 守門）掛 pytest 層兩邊共用；
  供裝（容器、network、pip）各自負責。**修正 `run-tests.sh` 檔頭「本地與 CI 同一支」的假宣稱**，
  不強迫 CI 改走該腳本。
  _Requirements: 1.1, 1.5_

- [x] 1.6 **🧠主 🔍V** 修改 `.github/workflows/tests.yml` 的 integration job，
  使結構性失效穿透既有的雙層吞噬：移除 job 級 `continue-on-error: true`；
  step 改為判斷 `rc == 10` 則 `exit 1`（硬擋），其餘 `exit 0`（維持測試失敗非阻擋的既有決定）。
  **🔍V 理由**：此任務的正確性決定了整套守門在 CI 端是否真的有訊號——
  若做錯，失效模式正是本 spec 的起因（量測工具靜默失效）。
  _Requirements: 1.1, 1.4_

- [x] 1.8 **🧠主** **requested-layer 的權威來源改為明示，不 parse `-m` 運算式**
  （2026-08-23 業主裁示；1.4 的 regex 作法由本項取代）。

  **問題**：`_requested_gated_layers` 以 `re.search(r"\bintegration\b", markexpr)` 推導執行意圖，
  實測 `-m "not integration"` → `requested={'integration'}`、`-m "not e2e"` → `{'e2e'}`，
  **誤判成「已請求該層」→ 無辜硬擋（假紅燈）**。
  繼續補 regex（排除 `not`、括號…）等於自己寫一個 pytest `-m` 布林運算式 parser，
  與本 spec「不自行重建 production semantics」的精神相違。

  **修法**：由 runner／CI **明示 intent**，pytest hook 只讀該變數；
  `-m` 只負責 pytest 自己的 selection，**不拿來推導執行意圖**。

  | 入口 | 設定 |
  |---|---|
  | `run-tests.sh` `LAYER=integration` | `REQUESTED_TEST_LAYERS=integration` ＋ `RUN_INTEGRATION=1` |
  | `run-tests.sh` `LAYER=e2e` | `REQUESTED_TEST_LAYERS=e2e` ＋ `RUN_E2E=1` |
  | `run-tests.sh` `LAYER=all` | `REQUESTED_TEST_LAYERS=integration,e2e` ＋ 兩旗標 |
  | CI integration job `env` | `REQUESTED_TEST_LAYERS: integration` ＋ `RUN_INTEGRATION: "1"` |
  | 裸跑 `pytest` / `LAYER=unit` | 不設 → 不受空跑守門管轄 |

  **明文語義**：裸跑 pytest **不保證** structural guard 的 requested-layer 語義；
  **正式驗收入口是 `make` / `run-tests.sh` 與 CI job**。
  （若日後要讓裸跑也完整支援，另做第二層 fallback；**regex 不得作為唯一權威來源**。）
  _Requirements: 1.1, 1.4, 1.5_

- [x] 1.10 **🧠主** **雙來源交叉守門**（2026-08-23 業主裁示，取代單一宣告來源）。
  共因失效：`RUN_*` 旗標與 `REQUESTED_TEST_LAYERS` 出自 `run-tests.sh` 同一個 `case`，
  該注入壞掉則兩者一起消失 → 守門判「未請求」→ 不管轄 → **守門連同它要防的東西一起消失**。
  改為兩個獨立來源互相校驗：
  **A（declared）** `REQUESTED_TEST_LAYERS`；**B（selected）** pytest 完成 selection 後的 item 集合。
  `I1` declared layer → 旗標須在，且該層須有 item 被選中；
  `I2` selected gated layer → 旗標須在，**不論有無宣告**。
  ⚠️ I2 使**裸跑 pytest 也受管轄**——業主接受此行為改變：
  裸跑整套卻讓 integration／e2e 靜默 skip，本來就不該回綠。
  來源 B **不解析 `-m`**，只讀 pytest 已解析完的結果（否定式／`-k`／路徑選取語義全留給 pytest）。
  _Requirements: 1.1, 1.4, 1.5_

- [x] 1.11 **🧠主** **runner 層級契約測試**（第三層，防「整組注入被一起改壞」）：
  `tests/unit/_meta/test_runner_layer_contract_req.py` 斷言
  `LAYER → pytest selection → REQUESTED_TEST_LAYERS → RUN_* flags` 四種成套對應
  （`unit`／`integration`／`e2e`／`all`），並鎖 CI job 的成對宣告與
  「job 級 `continue-on-error` 不得復活」。7 passed。
  _Requirements: 1.1, 1.4, 1.5_

- [x] 1.12 **🧠主** **修正層級判定：`item.keywords` → marker**（1.10 實測逼出的既存 bug）。
  `keywords` 含 parametrize 的**參數值**，因此
  `@pytest.mark.parametrize("layer", ["integration", ...])` 的 **unit** 測試
  會被誤判成 integration 層而 gate-skip——**又一個會靜默製造假綠燈的類別**。
  全套 1274 筆實測：`keywords` 與 marker 判定僅 **2 筆分歧**，且都是該類參數化測試，
  **既有測試分層零變動**；改後該 2 筆由「靜默 skip」恢復為實跑通過。
  _Requirements: 1.3, 1.4_

- [x] 1.9 **🧠主** 1.8 改完後重跑空跑守門實測——**11 情境全數符合**：
  宣告+旗標→0／宣告但旗標漏→10（integration、e2e、all 三者皆驗）／
  `-m "not integration"` 未宣告→**0（誤擋已消除）**／未知層名→忽略。
  **1.10 後補測 8 情境**（新語義）：共因失效（宣告+旗標同時消失）→**10**／
  裸跑 pytest →**10**／路徑選取 `tests/integration/` →**10**／
  `-m "not integration"` →0／`-m unit` →0／宣告 e2e 但未選中（I1 後半）→**10**／all 全設→0。
  _Requirements: 1.4_

- [x] 1.7 **🧠主** ✅ **結案**（2026-08-23 業主裁示）— 執行驗收：`make test-integration` 的
  passed/failed/skipped 三個數字與繞過 runner 直跑一致，並記錄實際數字（作為任務 3 的判定基準）。

  **實跑結果**：

  | | 修前 | 現在 |
  |---|---|---|
  | 結果 | **183 skipped** | **105 passed / 58 failed / 24 env-skipped** |
  | `gate_skipped` | （不可分辨）| **0** ← 旗標真的傳到了 |
  | 退出碼 | **0**（假綠）| **1**（真測試失敗，非結構性的 10）|

  ⚠️ **驗收目的不是「integration 全綠」**，而是證明 `make test-integration`
  真正執行、且與直跑的結構語義一致。原本「183 skipped ＋ rc=0」的結構性 bug 已消除，
  **Requirement 1 的機制鏈 PASS**。
  58 筆失敗全為檢索依賴案例（測試庫無 KB／embedding），屬 **Task 3 的資料前提**，
  非 Task 1 或 2.4 的缺漏。
  _Requirements: 1.1, 1.2, 1.3, 1.4_

---

## 2. 測試資料庫安全邊界與供裝

**目標**：接上共用網路後，測試不得觸及 production database。
⚠️ **本任務的守門一旦落地，`aichatbot_test` 供裝完成前 integration 與 e2e 皆會全數拒絕連線——
這是預期行為，不是回歸。**

- [x] 2.1 **🧠主 🔍V** 實作 `assert_non_production_db`：fail closed 雙驗
  （`DB_ENV != "production"`，缺值視為未證明即拒絕；`db_name ∈ ALLOWED_TEST_DATABASES` 白名單），
  違反時 `raise ProductionDatabaseRefused`，**不得降級為 skip 或 warning**。
  掛於 `tests/conftest.py` 的 session 級 autouse fixture，先於任何 `asyncpg.create_pool`。
  **🔍V 理由**：安全邊界；做錯的後果是測試寫進 production DB。
  _Requirements: 1.2_

- [x] 2.2 **⚡F** 注入 `DB_ENV`：`docker-compose.dev.yml` 加 `DB_ENV: ${DB_ENV:-test}`；
  `.github/workflows/tests.yml` integration job env 加 `DB_ENV: test`。
  （實查：`DB_ENV` 目前在整個 repo 不存在，不注入即全紅。）
  _Requirements: 1.2_

- [x] 2.3 **⚡F** 統一測試庫名為 `aichatbot_test`：
  `docker-compose.dev.yml` 的 `DB_NAME` 預設、CI 的 `POSTGRES_DB` 與 job `DB_NAME` 三處。
  **不得改為把 `aichatbot_admin` 加進白名單**——那會在所有環境一併解除對真 production 庫的保護。
  _Requirements: 1.2_

- [x] 2.4 **🧠主** 供裝 `aichatbot_test`【**IN SCOPE**，2026-08-23 業主定案】。
  **2.5 決定的是本項的「供裝深度」，不是本項是否納入範圍。**

  **必備（無條件納入）**：
  ① database 本身；② schema／migrations；③ 本 spec integration 所需 seed；
  ④ Face configs；⑤ system context；⑥ dialogue rules；⑦ C4 deterministic fixture 所需狀態。

  **條件式（預設不納入）**：⑧ 完整 KB；⑨ embedding／semantic-model index。
  → 條件式項目**僅在 2.5 證明 `trigger_facet_key` 無法 production-faithful 地直達 C4b 所需 Face 時**，
  才升格為本 spec 的必要供裝。
  _Requirements: 1.2_

- [x] 2.5 **🧠主** 先驗證 `trigger_facet_key` 收窄候選是否成立，再決定 e2e 供裝規模：
  確認 Step 0.4 直達路徑（`handle_trigger_facet` → `_seed_repair_facet`）對**診斷面向**
  是否與分類路由出口的 `_conversational_respond` 等價。
  成立 → 2.4 只做必備七項；不成立 → 2.4 追加條件式兩項（完整 KB ＋ embedding）。
  ⚠️ **本項為 spike，先於 2.4 執行**；屆時只做**一次**範圍展開判定，不重新討論架構。
  _Requirements: 1.5, 3.2_

---

## 3. 面向進場路由回歸改走 production seam (P)

**目標**：把進場路由回歸從「自行重演決策鏈」改為「呼叫 production 決策函式」，
使 Requirement 2 的失敗判定有意義。

**狀態（2026-08-23）**：

```text
3.0–3.2  COMPLETE
3.3      NEXT — 逐案 evidence packet 後才判型

已證明：harness 已接上 production seam；測試環境已與 production routing 組態對齊
未證明：哪一筆屬 HARNESS_DRIFT／REGRESSION／EXPECTATION_DRIFT
```

> ⚠️ **這一輪最重要的成果不是「5 變 3」**，而是證明了：
> **只要測試環境少一個 production env 或多一個宿主視角 URL，
> `HARNESS_DRIFT` 的判定本身就可能是假證據。**
>
> 兩個保真度 bug（皆在 commit `d290006` 修正）：
> ① 測試容器不帶 `.env` → 門檻跑 **0.55** 而 production 是 **0.65**
>    （舊 harness 硬編預設 0.65，反而比未帶 env 的容器更貼近 production）；
> ② 補 `env_file` 後 `.env` 的**宿主視角服務 URL** 生效 → 向量檢索整組失效
>    → 「應進對話」案例集體轉紅 59 筆。
>
> **在這兩者修正前跑出的紅綠，全部不可作為 Requirement 2 的證據。**

**現況（171 passed / 5 failed / 11 env-skip / gate_skipped=0 / rc=1）**：

| 案例 | 期望 | 舊 harness | production seam |
|---|---|---|---|
| 點退帳單的金額是怎麼算的 | 單發 | 紅 | 紅 |
| 點退做完後，帳單會自動出來嗎？ | 單發 | 紅 | 紅 |
| **收據 PDF 在哪裡下載** | 單發 | **綠** | **紅** ← 可能是舊 harness 掩蓋 production 真行為 |
| 點退的前置條件是什麼 | 單發 | 紅 | 綠 |
| 合約快到期了，系統會自動提醒我嗎？ | 單發 | 紅 | 綠 |
| 我的合約狀態怪怪的 | 進對話 | 紅 | 綠 |

另 2 筆（`test_grounding_by_parent_expands_to_children`、`test_three_layer_context_isolated`）
為 **corpus 暴露的既有假設**，獨立 triage，**不併入 Requirement 2 的判定**。

- [x] 3.0 **🧠主 🔍V** **前置供裝：frozen retrieval corpus**（2026-08-23 業主裁示）。

  **為何不回頭擴 2.4**：2.4 驗的是 Face **execution** path（105 passed 即證據）；
  Task 3 驗的是 **retrieval → entry routing**，本質上依賴檢索語料與 embedding。
  58 筆紅不是 2.4 做錯，而是 Task 3 有**額外資料前提**。範圍切法：

  ```text
  2.4  ＝ Face execution 最小供裝
         database／schema／seed／Face configs／system context／
         dialogue rules／form_schemas／C4 fixture state
  3.0  ＝ retrieval routing corpus（本項）
         KB rows ＋ embeddings ＋ 足以重現現行 routing cohort 的候選空間
  ```

  ⚠️ **絕不可只 seed「正確答案那幾筆」**：

  ```text
  只灌 55 個 case 的 expected KB
    → corpus 幾乎只剩 expected
    → top1 當然容易命中
    → routing test 假綠
  ```

  Task 3 驗的不是「那筆 KB 找不找得到」，而是
  **在真實候選空間裡，production retrieval 會不會把正確 evidence 排到足以觸發正確 routing 的位置**。
  故必須保留**競爭候選**。

  **供裝形態＝frozen retrieval corpus**（非模糊的「完整 production KB」）：
  ① 凍結一份可重現的 KB corpus；② 對應 embeddings 一併凍結；
  ③ 涵蓋 routing cohort 執行時會參與競爭的候選；
  ④ 測試一律驅動 production `retrieve_knowledge_hybrid`，
  **不在測試內重算或重建 routing 語義**。

  縮減依據 SHALL 為 **retrieval candidate space**，不得為「只留 expected rows」。
  現行 routing-relevant KB 規模若不大，直接凍結當下全部即可。

  **🔍V 理由**：corpus 的組成直接決定 Requirement 2 全部判定的可信度；
  只留 expected rows 會讓整組結論假綠。
  _Requirements: 2.1, 9.3, 9.4_

- [x] 3.1 **🧠主** 實作 `route_via_production`：內部只做兩件事——
  呼叫 production `retrieve_knowledge_hybrid` 取 `best_knowledge`，
  再呼叫 `routers.chat._diagnosis_config_for_knowledge(db_pool, best_knowledge, DecisionConfig.load(), user_message=question)`。
  檢索參數一律取自 production 讀值點（`DecisionConfig.load().kb_threshold`、`top_k` 對齊 production 預設），
  harness 不得自行 `os.getenv`。門檻、雙欄位退化、pre-entry gate 皆不在本函式內複刻。
  _Requirements: 2.1, 9.4_

- [x] 3.2 **⚡F**（併入 3.1）改寫 `test_facet_entry_routing_req.py` 的 `_route` 為呼叫 `route_via_production`；
  **所有既有案例（DIALOG／SINGLE／BOUNDARY，含五域）與斷言文字一字不改**。
  `RouteOutcome.reason` 僅用於失敗訊息，**永不進斷言**。
  _Requirements: 2.1, 9.4_

- [x] 3.3 **🧠主** 逐案 **evidence packet** ＋ 三向判型。

  ### 3.3-a `HARNESS_DRIFT` 定義擴充（2026-08-23 業主裁示）

  原定義只寫「production seam 執行即通過」，**僅涵蓋 false red**。
  實跑出現「收據 PDF 在哪裡下載」由綠轉紅——舊 harness 可能**掩蓋 production 真行為**。
  把 false green 硬塞成 `REGRESSION` 並不精確，故擴充定義（**只擴判型名稱，不動產品行為**）：

  ```text
  HARNESS_DRIFT ＝ 舊 harness 與 production seam 的行為差異，
                   且差異可歸因於 harness 複刻失真。
    ・false red  ：舊紅 → production 綠
    ・false green：舊綠 → production 紅
  ```

  ### 3.3-b 每案凍結 evidence packet

  **不得只印 top-1 與分數。** 每案兩側各記：

  | 節點 | OLD HARNESS | PRODUCTION SEAM |
  |---|---|---|
  | retrieval kwargs | ✓ | ✓ |
  | top-k candidates（id／similarity／summary／categories／category）| ✓ | ✓ |
  | selected best_knowledge | ✓ | ✓ |
  | 門檻判定 | threshold result | `DecisionConfig` resolved values ＋ `facet_entry_eligible` |
  | 分類推導 | derived category | `_knowledge_category` result |
  | config 查表 | config result | config result |
  | 適用性 | —（舊 harness 無）| `_preentry_routable` result |
  | final route | ✓ | ✓ |

  → **找出第一個發生分歧的節點**，判型即以該節點命名：

  ```text
  retrieval candidates 就不同   → 查還有哪個 kwarg／preprocessing 不同
  candidate 同、category 不同   → 雙欄位 fallback divergence
  category 同、config 同、route 不同 → pre-entry／applicability divergence
  ```

  ### 3.3-c 判型規則

  | 判定 | 條件 | 依據要求 |
  |---|---|---|
  | `REGRESSION` | production 行為確實不合理 | 修程式，斷言不動 |
  | `EXPECTATION_DRIFT` | 有**後來的產品決策**支持現行行為 | 書面依據（commit／定案紀錄），**不得為「測試沒過」本身** |
  | `HARNESS_DRIFT` | 差異可歸因於複刻失真 | **必須指名第一個分歧節點**；無法指名者一律回退為 `REGRESSION` |

  ⚠️ **原先以為的兩個分歧候選已被排除，不得用來結案**：
  門檻（舊 harness 0.65 vs production-faithful seam 0.65）與
  `top_k`（舊 harness 硬編 5 vs `VendorChatRequest.top_k` Field(5)）**皆非現行分歧**。
  故三筆轉綠目前狀態為 **candidate HARNESS_DRIFT，divergence 尚未定位**。

  **不得以「更新斷言」作為預設處置**，亦不得調整 `FORM_TRIGGER_THRESHOLD`。
  _Requirements: 2.1, 2.2, 2.3_

- [ ] 3.4 **🧠主 🔍V** 依 3.3 的判定執行修復，並確認全部案例通過。
  **🔍V 理由**：Requirement 2 的結論（哪些是真回歸）是後續工作的判定基準，
  且三向判定有「改 harness 就綠」的隱蔽逃生門。
  _Requirements: 2.1, 2.2_

---

## 4. JGB 替身邊界下移至 HTTP transport (P)

**目標**：讓 `bill_ref` adapter、參數組裝、client 端防衛過濾在測試中真正執行，
消除「mock 造假通過」的結構可能。

- [x] 4.1 **🧠主** 定義 `Transport` Protocol 與 `TransportResponse`／`Pagination` 型別，
  使 `JGBSystemAPI` 僅依賴該 Protocol；`_send` 依 `use_mock` 派發至 real 或 mock 實作。
  _Requirements: 4.1, 4.3_

  **實作**：新增 `services/jgb/transport.py`——`HttpMethod`／`Pagination`／`TransportResponse`
  ／`Transport` Protocol ＋ `RealHttpTransport`（httpx 與 `_headers` 由 `jgb_system_api` 下移）
  ＋ 失敗型別**宣告**（`TransportError` 基底、`UnresolvedEndpointError`、
  `UnmigratedMockEndpointError`、`MissingFixtureError`、`UnexpectedRealNetworkError`）。
  `FALLBACK_MESSAGE` 隨 `_send` 一併下移，`jgb_system_api` 再匯出以維持相容。

  ⚠️ **本任務只定契約，不做 resolver**（業主指定）：endpoint 樣板解析屬 4.2、
  未遷移端點 fail loudly 屬 4.3；本檔僅先宣告其失敗型別。
  ⚠️ **mock 與 real 共用同一份 caller-facing Protocol**，避免 4.4／4.5 長出「測試專用 API」。

  **fail-loudly 已生效**：`use_mock=True` 但未裝配 mock transport → `_send` 直接
  `raise UnexpectedRealNetworkError`，**不 fallback 至真實 HTTP**。
  實查 22 個公開方法皆有 `if self.use_mock` 前置短路 → 目前 mock 模式走不到 `_send`，
  故此舉**不改變現行行為**，只封住「靜默對 jgb2 發真請求」這條路。

  **驗收（容器內）**：`make test-unit` → **1107 passed / 13 failed**，
  13 筆全數落在 `tests/unit/_meta/`（`test_env_parity_req.py` 6 ＋
  `test_runner_layer_contract_req.py` 7），為既有 container mount 錯配 known-red，
  **與本次改動無關**（基準值同為 1107 passed）。
  針對性：`-k jgb` **19 passed**；四支直接觸及 `JGBSystemAPI` 的測試 **31 passed / 0 failed**。
  行為探針：mock 模式呼叫 `_send` 如期拋 `UnexpectedRealNetworkError`。

- [x] 4.2 **🧠主** 實作 `JGBMockTransport.resolve_endpoint`：以**樣板比對**（`{bill_id}` 比對單一 path segment、
  段數不同不匹配）解析 `(method, path) → endpoint_key`。
  ⚠️ **不得以 `path in WHITELIST` 判定**——detail path 實際為 `/api/external/v1/bills/12345`，
  字面永遠不會命中樣板。
  _Requirements: 4.1_

  **實作**（`services/jgb/transport.py`）：`match_template()` ＋ `ROUTES` ＋ `resolve_endpoint()`。
  **matching 與 parameter extraction 刻意分開**——`match_template` 命中即回傳抽出的 path 參數
  （`{"bill_id": "987654321"}`），使 adapter 測試日後能驗「`bill_id` 確實是從 concrete path 解析出來」，
  而不只是「有命中 detail 路由」。

  ⚠️ **歧義即失敗**：多樣板同時命中 → `raise UnresolvedEndpointError(reason="ambiguous")`，
  **不取宣告順序第一筆**（否則 correctness 綁在 registry 的 incidental ordering 上）。
  ⚠️ **4.2 ≠ 4.3**：`resolve_endpoint` 只回答 endpoint identity，**不消費** `MIGRATED_ENDPOINTS`
  （該常數刻意尚未定義），避免 `resolved == safe-to-mock` 變成隱性 fallback。
  ⚠️ **偏離 design 一處（已知並刻意）**：design 把 `ROUTES`／`resolve_endpoint` 掛在
  `JGBMockTransport` 上，本任務改為模組級函式——因該類的 `__init__` 需要 `BillFixtureTable`（4.4），
  提前建類會把 4.4 的相依拉進 4.2。內容與 design 一致，僅載體位置與引入時機不同。

  **驗收（容器內）**：新增 `tests/unit/api/test_transport_endpoint_resolution_req.py`
  → **14 passed / 0 failed**，逐條對應七項驗收＋歧義＋registry 去重＋「resolver 不查遷移狀態」守衛。
  **尺會咬的反證**：同一條 detail path 下，字面 whitelist 實作回 `None`、
  本實作回 `bill_detail` 並抽出 `bill_id=987654321`（該 ID 刻意未在任何原始碼／範例中出現）。
  全域回歸：`make test-unit` → **1121 passed / 13 failed**（1107 → 1121，即本組 14 筆全新增），
  13 筆仍全數落在 `tests/unit/_meta/`（既有 container mount known-red，與本次改動無關）。

- [x] 4.3 **🧠主 🔍V** 實作未遷移端點的 fail loudly：`resolve_endpoint` 回 None
  或 `endpoint_key ∉ MIGRATED_ENDPOINTS` → `raise UnmigratedMockEndpointError`，
  **SHALL NOT fallback 至真實 HTTP**。
  **🔍V 理由**：外部副作用邊界；做錯的失效模式是 integration 測試靜默對 jgb2 發真請求。
  _Requirements: 4.1, 4.3_
  ✅ **獨立驗證：CONFIRMED**（fresh verifier，2026-08-24）。三項驗收皆由其**自建探針**支持，
  未重用作者斷言：三態逐一驅動（未遷移那條改 monkeypatch `MIGRATED_ENDPOINTS` 而非改 `ROUTES`）；
  **在作者未驗的縫再驗一次**——patch `services.jgb.transport.httpx.AsyncClient` ＋ 封住
  `socket.socket`(AF_INET/INET6)／`getaddrinfo`／`create_connection`：三條失敗路徑下
  **無 AsyncClient 建構、無 INET socket、無 DNS/connect**。
  並反證量尺不瞎：直呼 `RealHttpTransport.send` 當場被同組 patch 抓到；
  `USE_MOCK_JGB_API=false` 時 `_send` 確實走到 real 分支 → mock 模式的 0 次是被 gate 擋掉，
  非路徑不存在。另以 **AST 去 docstring** 確認 `JGBMockTransport` 本體不含
  `httpx`／`RealHttpTransport`／`_real_transport`，實例屬性恰為 `{"fixtures"}`。
  補查：`jgb_system_api.py` 唯一的 `except Exception` 位於 real 分支內，結構上吞不到 mock 的 `TransportError`。

  ⚠️ **verifier 的兩則非阻斷 advisory（P4，已記錄，本輪不改）**：
  - **A1**：`MIGRATED_ENDPOINTS` 與 `ROUTES` 的 key 集合**目前完全相同**，故
    `UnmigratedMockEndpointError` 分支在正式組態下**不可達**，只能靠 monkeypatch 驅動。
    這是 4.3 階段的正常樣態（gate 先於端點就位），但該分支的「真實可達性」尚無非 patch 證據。
    → 日後新增未遷移端點時補一條非 patch 實例。
  - **A2**：結構不可達的強度是「類別本體無引用」而非「模組邊界隔離」——
    `transport.py` 頂層有 `import httpx`，且兩個 transport 同檔；未來同檔編輯可在
    `JGBMockTransport.send` 內直接建 client 而不需新增 import。
    現有 `test_mock_transport_holds_no_real_transport` 只檢查實例屬性名，抓不到這種寫法。
    → 建議補「原始碼（去 docstring）不得出現 `httpx`／`RealHttpTransport`」的斷言，
      或把 mock 移出獨立模組。verifier 已實測該斷言在現行實作下為綠。
    ⚠️ **業主裁定（2026-08-24）：A1／A2 皆 P4 deferred，不改 production/test code。**
      A2 揭露的是**我們對證據強度的描述過頭**，不是 invariant 被反證，故改以
      **收窄 claim ceiling** 處理：

```text
✅ 可宣稱：目前 implementation path 經反事實驗證不會產生 real-network side effect
❌ 不得宣稱：mock transport 在**模組邊界**上結構性無法碰真網路
             （transport.py 自身 import httpx，且 mock/real 共檔）
```

      ⚠️ 亦**不補** source-text assertion：它只證明「目前 class body 沒寫這個名字」，
      不是 architectural isolation，反而容易讓後人看到 green test 就重新說成「結構上不可能」。
      若日後真要把 invariant 升級為「mock 在架構上取不到 real-network capability」，
      選的是**拆模組**（`transport/protocol.py`／`real_http.py`（唯一 import httpx）／`mock.py`）
      ＋ import boundary test——那才是與 claim 同強度的 enforcement。**屬後續 architecture hardening。**

  **實作**（`services/jgb/transport.py`）：`MIGRATED_ENDPOINTS` ＋ `JGBMockTransport`（僅 admission gate，
  回應建構屬 4.5）。三態：resolve 回 None → `UnresolvedEndpointError(reason="no_match")`；
  命中但不在 admission set → `UnmigratedMockEndpointError`；已遷移但未裝配 fixture → `MissingFixtureError`。
  `JGBSystemAPI` 於 mock 模式裝配替身（22 個公開方法仍前置短路，故現行行為不變）。

  ⚠️ **admission set 只放 endpoint identity**，不放 concrete path、不再做一次樣板比對——
  endpoint identity 的唯一權威仍是 4.2 的 `resolve_endpoint`。
  ⚠️ **結構性保證**：`JGBMockTransport` **不持有也不 import** real transport，
  「跑到真網路」是**不可達**，而非「剛好沒寫那行 fallback」。

  **驗收（容器內）**：新增 `tests/unit/api/test_transport_migration_gate_req.py` → **11 passed**；
  併 4.2 一組共 **25 passed / 0 failed**。
  **反事實控制（本 task 核心）**：三條失敗路徑下 real transport 的 `calls == 0`；
  以 sentinel real transport 反證——刻意寫一個「失敗後 fallback 到 real」的壞實作，
  `spy.calls = 1`（測試會紅）；現行實作 `MissingFixtureError` 且 `spy.calls = 0`。
  這條專門殺掉「先發真請求 → 出錯 → 包成正確例外」的假綠。
  **層次分離**：4.2 的守衛測試改寫為行為證明（未列入 admission set 的 endpoint 仍能被正確 resolve），
  4.3 後仍綠 → endpoint identity 語義未被本任務改動。
  全域回歸：`make test-unit` → **1132 passed / 13 failed**（1121 → 1132，即本組 11 筆全新增），
  13 筆仍全數落在 `tests/unit/_meta/`（既有 container mount known-red）。

- [x] 4.4 **⚡F** 依 research.md 主題 7 的契約盤查（附 file:line）建 `BillFixtureTable`：
  至少 3 筆分屬 2 個 `contract_id`；每筆 `bit_status`／`invoice_status` 互異
  （使 C4a 能區分「引用對的那一筆」與「引用錯的那一筆」）；
  欄位限於 External 白名單投影，**不得新增真 API 不存在的欄位**；**不得含任何真實個資**。
  _Requirements: 4.1, 4.2_

  **實作**：新增 `services/jgb/fixtures.py`——`EXTERNAL_BILL_FIELDS`（33 欄，逐鍵取自
  jgb2 `External/BillApiController.php:130-167` `formatBill`）＋ `BillFixture` ＋ `BillFixtureTable`
  ＋ `assert_external_projection()`／`ForeignFixtureFieldError`。
  ⚠️ **`archive_at` 不在投影內**——真 API 輸出的是衍生的 `is_archived`（:163）；
  照 select 清單抄會憑空多一個 production 拿不到的欄位。

  **差異矩陣（刻意設計，非隨機湊數）**：

```text
bill_id  contract_id  bit_status  invoice_status  date_expire
900001   700100       3           0               20260815
900002   700100       19          1               20260915
900003   700200       3           1               20260915
```

  **每一對只共用一個維度** → 任何單一過濾條件都**無法複製**另一條件的結果集
  （contract={900001,900002}／bit={900001,900003}／invoice={900002,900003}，兩兩相異），
  且 month 亦可分辨（8月{900001}／9月{900002,900003}）。
  ⚠️ **identity 靠 `by_id()`，不靠 list position**——日後加第四筆不改變既有測試語義。

  **驗收（容器內）**：新增 `tests/unit/api/test_bill_fixture_table_req.py` → **13 passed / 0 failed**。
  **兩個 negative control 皆實測會咬**：
  ① 白名單 guard——`assert_external_projection({"id":1,"bill_ref":"900001"})` 拋
     `ForeignFixtureFieldError`（`bill_ref` 是 rag 端 adapter 參數，真 API 不存在）；
  ② 差異矩陣——反證「三筆只有 id 不同」的弱 fixture 會讓三個過濾集合**完全相同**（測試會紅），
     本 fixture 則三集合兩兩相異。
  全域回歸：`make test-unit` → **1145 passed / 13 failed**（1132 → 1145，即本組 13 筆全新增），
  13 筆仍全數落在 `tests/unit/_meta/`（既有 container mount known-red）。

- [x] 4.5 **⚡F** 實作 `/bills` 與 `/bills/{bill_id}` 的 mock 回應，依真 API **實際存在**的參數過濾
  （`role_id` 必填缺則 400、`user_id`、`contract_id` 單數、`bill_id`、`status`、`type`、
  `month` 以 `YYYY-MM` 比對 `date_expire` 整數區間、`sort_by` 白名單、`page`／`per_page` 上限 200）；
  補齊 `pagination` 五鍵與 `show` 的 `cvs_info`；`mapping` 沿用既有（已確認與真契約一致）。
  ⚠️ **絕不可實作 `bill_ref` 過濾**——真 API 無此參數，它是 rag 端 adapter。
  _Requirements: 4.1_


  **實作**（`services/jgb/transport.py`：`_bills_index()`／`_bills_show()` ＋ 類別常數
  `DEFAULT_PER_PAGE=50`／`MAX_PER_PAGE=200`／`ALLOWED_SORT_FIELDS`／`MAPPING`）。
  過濾**實算**、不查表：`month` 走 `^\d{4}-\d{2}$` → `YYYYMM01~YYYYMM31` 與 `date_expire` 比對。

  ⚠️ **三個 production 怪癖照抄，不「修正」**（mock 的價值在保真）：
  - `month` 非法格式 → **靜默忽略、不報錯**（`BillApiController:78-85` 只在 preg_match 命中才加條件）；
  - `month` 區間是 `YYYYMM01~YYYYMM31` **inclusive**，**非**「次月初」開區間——2 月同樣用 31（:81-83）；
  - `sort_by` 非白名單 → **回退 `created_at`**、`sort_direction` 非 asc/desc → 回退 `desc`（:88-96），
    皆非拒絕。此條同時殺掉 `getattr(record, user_supplied_field)` 寫法。

  ⚠️ **404 的資訊折疊照抄**：「不存在」與「無權存取」回**同一句**「帳單不存在或無權存取」（:230），
  **不得**在 mock 端拆成 404-not-found／403-no-access——否則上層取得 production 根本沒有的辨識能力
  （同 N1 的 E5 結論：404 仍是 ambiguous fact）。
  ⚠️ **list／detail 外殼分開**：detail **不帶** `pagination`（`TransportResponse total=False` 的用途即在此，
  避免假對稱）。

  **已知未建模（誠實記錄，非遺漏）**：`role_id` 為必填但**不做 owner 圈定**、`user_id`（經
  `belongContract.to_user_id`）過濾未實作、detail 的 `pay_info`／`cvs_info`／`details` 未附——
  fixture 投影不含這些欄位，補上等同虛構真 API 沒有的資料。`MIGRATED_ENDPOINTS` 仍只有兩個端點。

  **驗收（容器內）**：新增 `tests/unit/api/test_bill_mock_responses_req.py` → **28 passed / 0 failed**。
  沿用 4.4 差異矩陣實測：contract 700100→{900001,900002}｜2026-08→{900001}｜2026-09→{900002,900003}｜
  detail 900001→單筆且**無 pagination**｜unknown id→`{'code':404,'message':'帳單不存在或無權存取'}`｜
  非法 month `2026-8`→三筆全回（靜默忽略）。
  **`bill_ref` 反證（response 層再驗一次）**：即使請求帶 `bill_ref`，list 與 detail 的資料列皆不含該鍵——
  防的是 `{**fixture, "bill_ref": requested}` 這種繞過 fixture guard 的方便寫法。
  全域回歸：`make test-unit` → **1173 passed / 13 failed**（1145 → 1173，即本組 28 筆全新增）；
  逐檔查證 13 筆**全數**落在 `tests/unit/_meta/`（單獨跑該目錄：13 failed / 23 passed），
  且非 _meta 的 api／conversational／retrieval 三目錄 **796 passed / 0 failed**。
- [x] 4.6 **🧠主** 移除 `get_bills`／`get_bill_detail` 的方法級 mock 短路，使 adapter 實際執行；
  其餘約 18 個端點維持既有方法級 mock。
  於設計文件與程式註解記錄**混合邊界狀態**：adapter 的**非數字分支**會呼叫未遷移的 `get_contracts`，
  故本階段僅**數字分支**被端到端執行，**不得聲稱 adapter 已全分支證實**。
  _Requirements: 4.1, 4.3_

  ⚠️ **三層狀態必須分開讀（業主裁定 2026-08-24）**：

```text
4.6 implemented on branch      ✅ 本 commit
4.6 verified / evidence ready  ✅ 見下方驗收
4.6 production-released        ❌ **6.3 人工放行前禁止**
```

  ⚠️ 看到 `4.6 ✅` **不等於**已獲准上線；release decision 屬 6.3，且**不得由測試綠燈自動視為放行**。

  **實作**：`jgb_system_api.py` 移除 `get_bills`／`get_bill_detail` 的
  `if self.use_mock: return self._mock_*` 兩處短路（原處留註解記錄理由與混合邊界），
  並於 `__init__` 裝配 `JGBMockTransport(BillFixtureTable())`。其餘約 18 個端點**不動**。

  ⚠️ **混合邊界（實測確認）**：`bill_ref` 的**非數字分支**呼叫 `get_contracts`，
  而 `jgb_contracts` **未遷移**（仍走方法級 mock）→ 本階段端到端執行的只有**數字分支**。

  **驗收（容器內）**：
  - 端到端探針：`get_bills(bill_ref='900001')` → `success=True`，資料列 `[900001]`
    （**經 adapter 數字分支 → transport → detail → 包成單列**）；
    `get_bill_detail(900003)` → `900003`；未知 id → `{'code':404,'message':'帳單不存在或無權存取'}`；
    未遷移端點 `get_invoices` 仍走方法級 mock（`success=True`）。
  - **既有 no-real-network 斷言同步加強**：原本只涵蓋失敗路徑，4.6 後
    `/bills` 與 detail 已非失敗路徑 → 改為涵蓋**成功路徑**，
    斷言 mock 模式下**任何**路徑的 real transport 呼叫次數皆為 0
    （只測失敗路徑會漏掉「成功路徑其實打了真 API」）。
  - `make test-unit` → **1211 passed / 13 failed**（1145 → 1211）；
    13 筆全數落在 `tests/unit/_meta/`（單獨跑該目錄：13 failed / 23 passed）。

---

## 5. API-grounded Face 執行鏈閉環（C4a）

**目標**：以 deterministic control-flow 證實執行鏈閉環，並使失敗型 (a)/(b)/(c) 可判。
⚠️ **依賴任務 4**——mock 不依真參數過濾即無法收斂單筆，C4a 無從驗證。

- [x] 5.1 **🧠主** 定義 `ChainClosureAssertion` 與 `assert_chain_closure`：
  斷言對象為 grounding，**明文禁止對最終回答文字下斷言**（腳本化 brain 的輸出是測試自己寫的，
  對它斷言等於自證）。兩個正交維度——`grounding_must_contain`（送達性）與
  `required_grounding_facts`（充分性，比對 formatter 產出的 facts 鍵，不看 LLM 措辭）。
  _Requirements: 3.1, 4.2_

  **實作**：`tests/support/chain_closure.py`（**測試基礎設施，不進 production 程式**）——
  `ChainClosureAssertion`（frozen dataclass）＋ `assert_chain_closure()` ＋ `extract_fact_keys()`
  ＋ `CLOSURE_SCOPES`。三條禁令**以拋例外實現，不只寫在註解**：
  ① 傳入 dict／非字串（疑似最終回應）→ `AnswerTextAssertionError`
     （腳本化 brain 的輸出是測試自己寫的，對它斷言等於自證）；
  ② `required_grounding_facts` 為空 → `SufficiencyNotAssertedError`
     （任務 5.2 的紀律在**機制上**強制，無法靠忘記填繞過）；
  ③ 未知 `closure_scope` → `ChainClosureScopeError`。

  ⚠️ **closure scope 只承認 `numeric_bill_ref`（部分閉環）**：`bill_ref` adapter 的非數字分支
  會呼叫**尚未遷移**的 `get_contracts`，故該分支不在 claim 內。
  `not_covered` 欄位會原樣帶進結果摘要——**5.5 報告不得把部分閉環寫成 full closure**。

  **驗收（容器內）**：`tests/unit/api/test_chain_closure_assertion_req.py` → **15 passed / 0 failed**；
  `tests/unit/api` 全目錄綠。**尺會咬的兩項實證**：
  ① 送達性過、充分性缺 → 仍紅（防「查到了就算閉環」）；
  ② 對真 formatter 實跑——`build_bill_diagnosis_facts` 在 fixture 900001 上產出事實鍵
     `['取消判定','手動到帳判定','發送判定']`，量尺可正確抽出並斷言。

  ⚠️ **本任務逼出的一個問題（實測，非推測）**：
  `build_bill_anomaly_facts` 在同一筆上產出的 `【鍵】` 為 **`[]`**——該 formatter 不用此表示法。

  ### ✅ 業主裁定（2026-08-24）：採 (b)，但**觀測分離、判準唯一**

```text
Layer 1  事實怎麼從 formatter 輸出被觀測      → 面向專屬 extractor（可不同）
Layer 2  哪些事實存在才叫 grounding sufficient → **同一個** ChainClosureAssertion
```

  `(a)` 跨 formatter 萬用 parser **不採**——會讓 renderer syntax 變成從未宣告的 grounding contract，
  且普通句子裡的「• 金額：1000」可能被誤認為 evidence。
  `(c)` 為測試一致性改 production formatter **不採**——那是 test harness 反過來塑造 production contract；
  目前只證明「它沒用 diagnosis 的表示法」，**未**證明它缺必要 facts。

  **5.1 的最小演進（核心三禁令未改）**：`assert_chain_closure(grounding, spec, *, observed_fact_keys)`
  —— 觀測改為**注入**，框架**完全不認識 formatter**。新增守衛測試：
  `extract_fact_keys` 已自框架移除、框架程式碼不得出現 `【` 標記語法、`observed_fact_keys` 為必填。

  **新增** `tests/support/fact_extractors.py`（兩個 observation adapter，輸出**同一組 canonical key**）：
  - `diagnosis_bracket_fact_extractor`：`【發送判定/取消判定/手動到帳判定】` → `send_/cancel_/manual_complete_determination`
  - `anomaly_labeled_field_extractor`：語義欄位 → `bill_status`／`amount_stored`／`due_date`／`billing_period`

  三條硬限制逐條落地並實測（`tests/unit/api/test_fact_extractors_req.py` → **17 passed**）：
  - **B-1 observer ≠ judge**：以 `inspect.signature` **結構檢查**（非文字掃描）——
    公開 callable 只吃 `grounding`，模組不得暴露含 required／sufficient／assert 的介面；
  - **B-2 不綁排版**：`• 狀態：X`／`狀態：X`／`  狀態 ： X`／半形冒號皆觀測到 `bill_status`；
  - **B-3 negative controls**：「目前帳單看起來正常」→ 空；「金額可能有問題」→ 無 `amount_stored`；
    `狀態：`（無值）→ 空；未登錄括號鍵 → 忽略；兩觀測器**互不越界**（各自認不得對方的語法）。

  ⚠️ **與業主示例的一處刻意差異**：示例寫 `• 金額：1,000 → amount`，但**真 formatter 實際輸出**
  為 `帳單金額 NT$ 18,000（系統存值）`（`_bill_head()`）。觀測契約以**實際輸出**為準——
  故 `• 金額：1,000` **不**被觀測成 `amount_stored`（已寫成具名測試），否則觀測的是想像中的 formatter。

- [x] 5.2 **🧠主** 為每個 C4a 案例明列 `required_grounding_facts`（執行前明示為斷言基準）。
  ⚠️ **`required_grounding_facts` 為空的案例不構成 C4a 通過的證據**——那等於沒驗充分性。
  例：「為什麼發不出去」需失敗原因類事實；「這期帳單多少錢」只需金額與期別。
  _Requirements: 3.1, 3.2, 4.2_

- [x] 5.3 **⚡F** 實作 `bill_diagnosis` 的 C4a 測試：真 DB ＋ 真 `ConversationalEngine` ＋
  **真 `APICallHandler`** ＋ 真 `JGBSystemAPI` ＋ `JGBMockTransport` ＋ 腳本化 brain（零 OpenAI）。
  涵蓋：反問 → 收齊 `bill_ref` → adapter 數字分支 → transport → `secondary_call: jgb_bill_detail`
  → grounding。
  _Requirements: 3.1, 7.1_

  **實作**：`tests/integration/conversational/test_c4a_bill_diagnosis_closure_req.py`
  → **4 passed / 0 failed**（真 DB，非 skip）。

  ⚠️ **scope（業主裁定）**：本檔帶 **OB-3**；**OB-1／OB-2 屬 `c4a-anom-01`，在 5.4 落地**——
  本檔只提供通用 primitive（`_RecordingTransport`），**不得**宣稱 OB-1／OB-2 已由 5.3 驗收。

  **六項鎖定逐條落地**：
  ① 真的走 frozen chain（真 DB／真 engine／真 `APICallHandler`／真 `JGBSystemAPI`／
     `JGBMockTransport`／腳本化 brain，零 OpenAI）——**非**直接呼 formatter 或 fixture helper；
  ② **OB-3 驗實際 request identity**：以 `_RecordingTransport` 記錄每次 transport 請求，
     斷言 detail 請求的 bill_id **集合**等於該案 fixture；
  ③ `secondary_call_required=true` **machine-observable**：斷言 `endpoint_keys()` 含 `bill_detail`，
     **不以** grounding 內容反推；
  ④ sufficiency 用 **frozen 5.2**：diag-01 `{amount_due}`／diag-02 `{cancel_determination}`，
     未因 formatter 另吐其他 determination 而改 required set；
  ⑤ **送達 ≠ 充分的 negative control（完整 chain 上）**：chain 正常查到帳單、
     但把該案 required key 自觀測移除 → 必須紅（實測拋「充分性缺事實鍵」）；
  ⑥ claim ceiling 寫在檔頭。

  ⚠️ **實測逼出的既有 production 行為（記錄，非缺陷）**：detail 端點在一次收斂中被呼叫**兩次**——
  adapter 數字分支直查一次、面向 `secondary_call` 再一次。故 OB-3 斷言「**集合**相符且非空」，
  **不鎖次數**；原以為只會有一次的寫法已修正。

  **OB-3 反證（component negative control，未新增第五個 case）**：
  把期望綁到另一筆 fixture 時斷言必須紅——實測 `{900001} != {900003}` 成立，
  證明「兩案綁不同 fixture」真能殺掉 constant-record 實作。

  ⚠️ **claim ceiling**：5.3 PASS 只證明兩個 frozen case 的 **numeric branch** chain closure；
  **不得**升格為「bill_diagnosis 全自然語言穩健」「非數字分支已證」
  「routing 到 bill_diagnosis 正確」「adapter 全分支已 closure」。

- [x] 5.4 **⚡F** 實作 `billing_anomaly` 的 C4a 測試（第二面向，**無 `secondary_call`** 的對照組）。
  兩面向共用同一份 `jgb_bills` 契約與 fixture 表。
  _Requirements: 3.1, 3.3, 7.1_

  **實作**：`tests/integration/conversational/test_c4a_billing_anomaly_closure_req.py`
  → **6 passed**；併 5.3 共 **10 passed / 0 failed**（真 DB，非 skip）。
  共用 primitive 抽到 `tests/support/c4a_harness.py`（`RecordingTransport`＋`RecordingHandler`）。

  ⚠️ **本檔要證的不是「grounding 會動」，而是：chain closure 不依賴 `secondary_call` 才能成立。**

  **本檔最容易假紅之處（已實測並寫成具名測試）**：
  `billing_anomaly` 沒有 `secondary_call`，但 **adapter 的數字分支仍會打一次 `bill_detail` 端點**。
  故 secondary call 的有無 **MUST** 由 `execute_api_call` 的**派發次數**判定
  （`conversational_engine.py:985-987` 的第二次派發），
  **不得**以「`bill_detail` 有沒有被呼叫」代表——後者在兩個面向都成立。

  **對照 invariant（由 execution trace 證明，非從文字推得）**：

```text
diagnosis frozen cases   secondary dispatch > 0   ← 5.3 已同步改為正向斷言
anomaly   frozen cases   secondary dispatch = 0
兩邊                      OB-3 ✅｜delivery ✅｜sufficiency ✅
```

  **OB-1 落地**：`c4a-anom-01` 同時斷言 `billing_period` 已觀測 ＋ `date_start`／`date_end`
  **兩個來源值**皆送達；expected 一律自 frozen fixture 取值、經 **production 渲染器**
  （`_format_date_int`）產生，**不在測試中手抄日期**（避免第二個 truth source）。

  **OB-2 落地且實測會咬**：分別抽掉 start／end 之一 →
  **即使「計費期間」label 仍在、observer 仍觀測到 `billing_period`**，仍必須紅（拋「送達性缺字面」）。
  兩個前提各有具名斷言，證明紅來自 **delivery** 而非 label 消失或 observation 失效。
  → 這證成：**`billing_period` observer green ≠ provenance delivery complete**。

  **`c4a-anom-02`**：required 僅 `bill_status`，**未**加入 `bit_status`、
  **未**因 formatter 同時帶金額／期間而擴尺；並有完整 chain 的充分性 negative control。

  ⚠️ **claim ceiling**：`execution_face = billing_anomaly` 只是 test context。
  5.4 PASS **SHALL NOT** 寫成「使用者問『帳單現在的狀態』就應 route billing_anomaly」——
  那會越界到 `routing-authority-model`（BLOCKED_BY_EXTERNAL_DECISION）。

- [x] 5.5 **🧠主 🔍V** 執行 C4a 並依判型流程分類失敗（若有）：
  (a) 鏈路未跑通／(b) mock 契約不保真／**(c) grounding insufficiency**（充分性維度判出）。
  依業主裁示：**(a) 與 (c) 觸發 Req.3.4 降級**（routing 工作降 P1 以下、執行鏈修復升 P0）；
  (b) 不觸發（修 mock 即可）；(c) 的修法（擴 External 欄位或改打 Internal）**另立案**，
  不進本 spec 的修復迴圈。
  **🔍V 理由**：本任務的結論直接決定整個 spec 的優先序走向。
  _Requirements: 3.1, 3.3, 3.4, 3.5_
  ✅ **獨立驗證：CONFIRMED**（fresh verifier，2026-08-24，covered bytes = `8968986`）。
  它另注入 probe 逐節點重建判斷，並實做三組對抗破壞（翻轉 anomaly dispatch 期望／
  改綁他筆 fixture／drop required key）皆如期變紅 → 證明判型由 execution facts 驅動。
  ⚠️ **其後依 advisories A-1／A-2／A-3 之文字修正屬 post-verifier owner adjudication**，
  **未**經該 verifier 覆核；implementation／test bytes 與判型輸入皆未更動，故不重跑 verifier。

  **結果**：見 `c4a-classification-result.md`——四案皆抵達 frozen 流程圖的 **PASS 節點**
  → **C4a PASS**；`(a) 0/4｜(b) 0/4｜(c) 0/4` → **不觸發 Req.3.4 降級**。
  ⚠️ **未重新解釋 (a)/(b)/(c)、未新增第四種結果**（`PASS` 本就是流程圖終點之一）。
  ⚠️ **判型依據為 execution evidence**（逐案的 fixture identity／送達性／充分性／
  secondary dispatch），`10 passed` 僅為驗收摘要、**不是**判型依據。
  ⚠️ **射程寫窄**：只證 4 個 protocol-frozen cases × `numeric_bill_ref` × 兩個 execution_face；
  **不得**升格為非數字分支／一般自然語言／routing ownership／adapter 全分支／最終答案能力。

---

## 6. C4b production-brain smoke 與上線 gate

**目標**：證明真 brain 會**使用** grounding 作答（C4a 只證明 grounding 送達）。
⚠️ **依賴任務 2.5**（e2e 供裝規模）與任務 5（C4a 先通過）。

- [x] 6.1 **🧠主** 定義 `BrainGroundingAssertion` 與 `assert_brain_uses_grounding`：
  斷言僅鎖「該筆實際值字面是否出現」與「是否退回泛用 KB 答案」，**不鎖措辭**（真 LLM 非決定性）。
  實作 `tests/support/brain_grounding.py`；量尺自驗 `tests/unit/api/test_brain_grounding_assertion_req.py`（17 passed）。
  逐案尺 `c4b-ruler-frozen.md`（v1，FROZEN 未執行，經執行前 audit 反證）
  → **現行為 `c4b-ruler-v2-amendment.md`（FROZEN）**；執行參數 `c4b-run-parameters-frozen.md`
  （FROZEN，失敗分類與 evidence 欄位由 v2 §5 併同修訂）；
  進場與供裝前置 `c4b-entry-path-equivalence-resolved.md`（已解除）。
  _Requirements: 3.2_

- [x] 6.2 **⚡F** 實作兩面向的 C4b e2e 測試（真 `conversational_step`、少量案例）；
  於檔頭標明預期成本量級；掛 `@pytest.mark.e2e` 使其預設略過、不擋 CI。
  `tests/e2e/conversational/test_c4b_brain_grounding_e2e_req.py`；已執行一次（真 OpenAI）。
  ⚠️ **實作完成 ≠ C4b 通過**——執行結果為 **NOT PASSED**（見 6.3）。
  _Requirements: 3.2, 7.2_

- [x] 6.3 **🧠主 🔍V** 執行 C4b 並產出**上線 gate 放行報告**：逐面向列出斷言結果與實際引用字面。
  `c4b-release-gate-report.md`（**業主已簽核** 2026-08-25）：C4b **NOT PASSED**、
  production-facing gate **CLOSED**；evidence 見 `evidence/`。
  ⚠️ **放行人為業主，人工放行；不得由測試綠燈自動視為放行。**
  未放行前，本 spec 的三項 production-facing 變更（任務 4.6、任務 8、任務 9）**不得上線**。
  C4b 失敗**不觸發** Req.3.4 降級，該案例併入任務 11 的 `grounding_utilization_rate` 分母分子。
  **🔍V 理由**：上線 gate；且需獨立確認「引用字面」不是測試自己餵進去的。
  _Requirements: 3.2_

- [x] 6.4 **🧠主** 報告紀律落實：C4b 未過而僅 C4a 過時，
  所有對外表述 SHALL 為「執行鏈閉環已證實，**最終答案能力尚未放行**」，
  SHALL NOT 為「最終答案能力已證實」。
  `c4b-report-discipline-record.md` ＋ 機器檢查 `tests/unit/_meta/test_c4b_report_discipline_req.py`。
  _Requirements: 3.2, 9.1_

---

## 7. 已知缺陷：`skip_refine` 語義定案

⚠️ **依賴任務 4**。**不得在任務 4 完成前先改 `skip_refine` 的實作**——那會在錯誤的症狀上動刀。

- [x] 7.1 **🧠主** 以 `bill_diagnosis` 重現原觀測情境（候選 > `candidate_cap` 分流 → 選定候選 → 重查）。
  _Requirements: 5.1_

- [x] 7.2 **🧠主** 依重現結果定案並記錄哪一邊是正確語義：
  若重查後收斂至單筆 → 判定宣告與行為**一致**，處置為文件與命名
  （於配置鍵註解與 `steering/dialogue.md` 明寫「跳過補識別輪，非跳過重查」）；
  若仍不收斂 → 回到 Req.5.1 原始二選一，修正其一。
  _Requirements: 5.1_

- [x] 7.3* **⚡F** 補 unit 測試鎖定 `skip_refine` 語義（候選 > cap 時不追問直接列候選；
  選定後重查收斂單筆）。
  → `skip-refine-semantics-decision.md`；重現 `tests/unit/conversational/test_skip_refine_semantics_req.py`
  （2 passed）；**行為未改**（重查確實收斂），處置為註解＋`steering/dialogue.md` 候選分流速查。
  _Requirements: 5.1_

---

## 8. 已知缺陷：`conversational_step` 契約分層

**目標**：`action` 越界時不再連同可用的 `scope` 一併丟棄，且**不引入 `action=None` 半合法狀態**。
⚠️ ［需求 5.2］此修復**須獨立上線，不得與其他改動同批**。

- [ ] 8.1 **🧠主** 實作 `_parse_conversational_step() → StepResult`（解析層）：
  先正規化 `scope`／`face`、再驗 `action`。不變量——`payload` 非 None 時
  `payload['action'] ∈ VALID_ACTIONS` 必然成立，**payload 內永不出現 `action=None` 或越界值**。
  _Requirements: 5.2_

- [ ] 8.2 **🧠主** 新增 `conversational_step_result()` 為主要介面；
  將 `conversational_step()` 改為相容層（`return result.payload if result else None`），
  **簽章與回傳形狀與現行逐位一致**，現有 caller 零感知。
  _Requirements: 5.2_

- [ ] 8.3 **🧠主** 遷移兩個呼叫點至新介面：`conversational_engine`（進場輪與續輪）
  與 `chat._preentry_routable`。以 `FACET_SCOPE_SALVAGE`（預設 off）控制
  **呼叫端在 `payload is None` 時是否依 `scope` 行動**——旗標不改變解析結果，
  回退時不需回退解析層。
  _Requirements: 5.2_

- [ ] 8.4 **⚡F** 補 unit 測試：`action` 合法時輸出與現行**逐位一致**（零回歸鎖）；
  `action` 越界 ＋ `scope=switch` 時 `payload is None` 且 `scope == 'switch'`；相容層回 None。
  _Requirements: 5.2_

- [ ] 8.5 **🧠主 🔍V** 獨立驗收並獨立上線：確認兩項 delta——
  `decision_snapshot` 歸因由 `facet_engine_degraded` 改為 switch 語義；
  `_preentry_routable` 由 fail-open 轉為實際擋下進場（受 `PREENTRY_ROUTABILITY_GATE` 預設 off 二重保護）。
  **🔍V 理由**：［需求 5.2］明文要求獨立驗收；且此變更會改變面向退出的歸因值域。
  _Requirements: 5.2_

---

## 9. `repair_create` 進場點（先判型，再補 metadata）

⚠️ 實查：`修繕報修` 目前 **0 個知識進場點**；kb3365（修繕進度查詢）與 kb4249（業者受理，
`target_user` 僅 `property_manager`）與面向的 `tenant`／`b2c` **意圖與角色皆不符**，
且 `config_for_category` **不比對 `target_user`／`mode`**。

- [ ] 9.1 **🧠主** 依設計決策 3 採**選項 C**：新增語義正確的**租客向報修觸發知識**
  （`categories=['修繕報修']`、`target_user=['tenant']`），
  **不替 kb3365／kb4249 加標**（照字面補標會替 b2b 業者開出通往 b2c 租客面向的路徑）。
  _Requirements: 5.3, 6.6_

- [ ] 9.2 **🧠主** 明確記錄新增的 **Face entry points**（`EntryPointChange` 的
  `declared_entry_points`），並以**現行 production routing 規則**執行回歸。
  _Requirements: 5.3, 6.6_

- [ ] 9.3 **🧠主 🔍V** 驗證新增 trigger **不造成已知資訊型問題誤進 `repair_create`**
  （`misroute_probe_cases`），並確認 `make audit` 不變量 1 的掛帳清單與不變量 4 的狀態變化
  符合預期（**注意：3365／1558 的 WARN 在不變量 1，非 requirements.md 所記的不變量 4**）。
  **🔍V 理由**：metadata 變更即 routing 變更（R6.6）；且此面向為**交易型**，
  誤進場的後果是替錯的角色建報修單。
  _Requirements: 5.3, 6.6_

- [ ] 9.4 **🧠主** 通過 9.3 且通過任務 6.3 的上線 gate 後，始得上線。
  _Requirements: 5.3_

---

## 10. Routing Hint／Action／Execution 三層責任分層文件化

**目標**：語義分層落於文件與審查流程。⚠️ **不變更 DB schema、不新建任何 decision component**。

- [x] 10.1 **⚡F** 更新 `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md`：
  以 Routing Hint／Action Declaration／Execution Configuration 三層描述 KB 攜帶的資訊；
  明確標示「`categories` 命中 ≠ 決定」「帶 `form_id` ≠ 直接開表單（`trigger_mode` 另有分支）」
  「`grounding_scope` 僅在選定後生效，非 routing 階段選項」。
  → 新增 **§0 三層責任分層**（含三條禁止推論、0.3 的 architecture fact
  「entry nomination 不消費 responsibility contract」、0.4 含責任判定的實際流程圖、
  0.5 KB 三層欄位對照、0.6 `skip_refine` 定位）。⚠️ 刻意**不畫**應有的 bridge。
  _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10.2 **⚡F** 回寫母圖的已知過時處：`QUERY_REWRITE_MODEL`（已改 gpt-4o-mini）、
  `KNOWLEDGE_MIN_THRESHOLD`（實際為 `KB_SIMILARITY_THRESHOLD`）、`LLM_SYNTHESIS_TEMP`（實際 0.1）；
  補上 `FORM_TRIGGER_THRESHOLD`、`RELEVANCE_GATE_*`、`ENABLE_QUERY_REWRITE_B2B`、
  `PREENTRY_ROUTABILITY_GATE`。**母圖只引用不複製**——參數唯一真實來源仍為 `docs/retrieval-parameters.md`。
  _Requirements: 6.1_

- [x] 10.3 **⚡F** 更新 `docs/architecture/facet-architecture.md`、`.kiro/steering/dialogue.md`
  （補三層速查表與 `skip_refine` 語義）、`.kiro/steering/knowledge.md`
  （明確區分 `knowledge_categories` 與 `routing_faces`）。
  → facet 加 §〇 三層責任分層（`Face entry ≠ responsibility ownership`；`scope=stay/switch`
  屬第②層非 entry evidence；`PREENTRY_ROUTABILITY_GATE` 的 evaluation context 不同源）；
  dialogue 加「候選分流速查」（`skip_refine`）；knowledge 加 §6
  （`categories`＝entry nomination metadata，非 ownership 宣告；禁由
  `OWNER_EXISTS_BUT_NOT_PROPOSED` 推導補 category）。⚠️ 三份皆**不畫**應有的 bridge。
  _Requirements: 6.1, 6.5_

- [ ] 10.4 **🧠主**（**業主 2026-08-25 裁定：intentionally deferred，不做**）建立審查流程條款：routing／action metadata 變更 ＝ 程式碼變更等級審查
  （PR checklist），並明寫「補 34 筆 `categories` ≠ 資料完整性修復，而是新增 34 個 Face entry point」。
  _Requirements: 6.6, 6.7, 6.8_

---

## 11. 面向對話品質基準（先量現況，不調規則）

⚠️ ［需求 10.5］**本 spec 到 baseline 落檔為止，SHALL NOT 調整任何對話規則文字。**
⚠️ 本元件為 `scripts/backtest/` 下的**獨立腳本，不是 pytest 測試**，不在 DB 守門作用域內。

- [ ] 11.1 **🧠主 🔍V** 落實 production 存取的四條安全條件：
  ①所有請求 `session_id` 帶 `INTERNAL_RULES` 認得的前綴（建議新增 `r10_` 並補進 `_SMOKE_PREFIXES`），
  使 `is_internal=True` 自動成立、不污染計量與額度；
  ②`usage_events` 保留不清（那正是要聚合的資料，且已標 internal）；
  ③`form_sessions` 依 prefix 清除；
  ④**業務資料零寫入——SHALL NOT 驅動任何交易面向**（`execute_endpoint` 存在者），那會真的建單。
  **🔍V 理由**：對 production 的寫入邊界；第 4 條做錯會產生真實報修單。
  _Requirements: 9.4, 10.1_

- [ ] 11.2 **🧠主** 以 `freeze_measurement.py` 凍結判準、分母、雜訊標記、尺版本，**再開始量測**。
  量測後任一項變更即為換尺，須重跑前後兩側。
  _Requirements: 9.3, 10.5_

- [ ] 11.3 **⚡F** 以既有埋點 SQL 聚合兩項指標：`turns_p50`／`turns_p90`
  （`usage_events.facet_key` ＋ `turn_number`，per-session MAX）與 `repeat_ask_rate`。
  無須新增埋點。
  _Requirements: 10.1_

- [ ] 11.4 **🧠主** 建立三項需判定的指標之判定程序並執行：`on_target_ask_rate`（反問對題率）、
  `premise_honored_rate`（前提衝突處理率）、**`grounding_utilization_rate`**
  （分母＝grounding 已具備必要事實的收斂輪；分子＝最終回答正確採用者）。
  ⚠️ ［需求 7.3］由人／協作代理直接判斷，**SHALL NOT 外包給大量 LLM 呼叫產生不可靠標註**。
  _Requirements: 10.1, 10.2, 10.3, 7.3_

- [ ] 11.5 **🧠主** 評估 `required_slots` 設計合理性：是否索取面向實際不需要的欄位、是否遺漏必要欄位。
  _Requirements: 10.4_

- [ ] 11.6 **🧠主** baseline 落檔並標註結論分級：僅通過現有基準者
  SHALL 僅聲稱「技術可行／regression-safe」；「routing 品質確實提升」SHALL 僅在通過
  production holdout 後聲稱。比較性結論須 ≥30 可判定案例。
  _Requirements: 9.1, 9.2, 9.3, 10.5_

---

## 12. Real API contract smoke（橫向）

- [ ] 12.1 **🧠主** 實作 `smoke_contract`：少量打 staging／真 API，僅比對
  params → endpoint → response schema 的漂移；**不比對資料值**（真資料會變）。
  掛 e2e 層預設略過，不進 CI 阻擋路徑。
  _Requirements: 4.4, 7.2_

- [ ] 12.2 **🧠主** 對 `jgb_bills`／`jgb_bill_detail` 執行漂移偵測。
  ⚠️ **結果 SHALL NOT 作為 Requirement 3 的主要驗收證據**——真 API 只用於確認
  mock 假設與現實 contract 是否漂移。
  _Requirements: 4.4_

---

## 需求覆蓋對照

| 需求 | 任務 |
|---|---|
| 1.1 | 1.1, 1.5, 1.6, 1.7 |
| 1.2 | 1.2, 1.7, 2.1, 2.2, 2.3, 2.4 |
| 1.3 | 1.3, 1.7 |
| 1.4 | 1.4, 1.6, 1.7 |
| 1.5 | 1.1, 1.5, 2.5 |
| 2.1 | 3.1, 3.2, 3.3, 3.4 |
| 2.2 | 3.3, 3.4 |
| 2.3 | 3.3 |
| 3.1 | 5.1, 5.2, 5.3, 5.4, 5.5 |
| 3.2 | 2.5, 5.2, 6.1, 6.2, 6.3, 6.4 |
| 3.3 | 5.4, 5.5 |
| 3.4 | 5.5 |
| 3.5 | 5.5 |
| 4.1 | 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.2 |
| 4.2 | 4.4, 5.1, 5.2 |
| 4.3 | 4.1, 4.3, 4.6 |
| 4.4 | 12.1, 12.2 |
| 5.1 | 7.1, 7.2, 7.3 |
| 5.2 | 8.1, 8.2, 8.3, 8.4, 8.5 |
| 5.3 | 9.1, 9.2, 9.3, 9.4 |
| 6.1 | 10.1, 10.2, 10.3 |
| 6.2 | 10.1 |
| 6.3 | 10.1 |
| 6.4 | 10.1 |
| 6.5 | 10.3 |
| 6.6 | 9.1, 9.2, 9.3, 10.4 |
| 6.7 | 10.4 |
| 6.8 | 10.4 |
| 7.1 | 5.3, 5.4 |
| 7.2 | 6.2, 12.1 |
| 7.3 | 11.4 |
| 8 | 全程約束：本任務清單**未包含**任何 always-on query rewrite、新全域 routing selector、pre-entry gate 上線、KB 全面結構化、hybrid recall、澄清分岔之工作 |
| 9.1 | 6.4, 11.6 |
| 9.2 | 11.6 |
| 9.3 | 11.2, 11.6 |
| 9.4 | 3.1, 3.2, 11.1 |
| 10.1 | 11.1, 11.3, 11.4 |
| 10.2 | 11.4 |
| 10.3 | 11.4 |
| 10.4 | 11.5 |
| 10.5 | 11.2, 11.6 |

---

## 註記統計

| 註記 | 數量 | 任務 |
|---|---|---|
| **⚡F**（可交 Fable）| 17 | 1.1, 1.2, 1.3, 2.2, 2.3, 3.2, 4.4, 4.5, 5.3, 5.4, 6.2, 7.3, 8.4, 10.1, 10.2, 10.3, 11.3 |
| **🧠主**（主 session）| 38 | 其餘 |
| **🔍V**（須獨立驗證）| 9 | 1.6, 2.1, 3.4, 4.3, 5.5, 6.3, 8.5, 9.3, 11.1 |
| **(P)**（可並行）| 2 組 | 任務 3 與任務 4（無共享檔案）|

**🔍V 的九項全部落在四類風險上**：
安全邊界（2.1、11.1）、外部副作用（4.3）、驗收結論所依賴（1.6、3.4、5.5、6.3）、
需求明訂獨立驗收（8.5）、交易面向誤進場（9.3）。


---

## 已知 advisory（1.6 獨立驗證產出，尚未處置）

| # | 等級 | 內容 | 狀態 |
|---|---|---|---|
| A1 | P3 | `-m "not integration"` 被 regex 誤判為請求該層 → 無辜硬擋 | ✅ **已修**（任務 1.8，改讀 `REQUESTED_TEST_LAYERS`）|
| A2 | P3 | 守門的管轄權來自宣告，**宣告本身若消失，守門會靜默自我停用** | ✅ **已修**（任務 1.10 雙來源交叉守門 ＋ 1.11 契約測試）|
| A3 | P4 | `tests.yml` 註解把 rc=10 語義寫成含「DB 無法證明為非 production」，但該守門（任務 2.1）尚未實作 | ✅ **已修**（註解改為標註待實作）|
| A4 | P4 | 移除 job 級 `continue-on-error` 後，`checkout`／`setup-python`／`pip install` 任一失敗都會擋合併 | ✅ **裁示：接受，不恢復**（2026-08-23）——「環境沒建起來」與「測試沒全綠」不共用非阻擋政策；若 PyPI 常故障，改用 pip cache ＋ 2–3 次 bounded backoff retry，**retry 全失敗仍 hard fail** |

### A2 的精確形狀（比原始 advisory 更嚴重，重新表述）

驗證代理原本擔心的是「`all` 不受管轄」——**該半已由任務 1.8 關閉**
（`LAYER=all` 現在明示 `REQUESTED_TEST_LAYERS=integration,e2e`）。

但同一份 `case` 同時注入**旗標**與**宣告**，因此殘留一個更根本的問題：

```text
若 run-tests.sh 的 ENV_ARGS 注入日後回歸（重構、複製貼上、新增 layer 漏補）
  → RUN_INTEGRATION 消失      → 整層 gate-skip
  → REQUESTED_TEST_LAYERS 消失 → 守門判定「未請求」→ 不管轄 → rc=0
  → 靜默假綠燈
```

**守門會連同它要防的東西一起消失。** 這正是本 spec 的起因形態。

**候選解法（第二層 fallback，業主先前已預留此門）**：
在 `pytest_sessionfinish` 改看 **pytest 自己實際收集到的 item**——
某層有 item 被收集且該層旗標未設 → 結構性失效，**不論有無宣告**。
這不是解析 `-m`（不重建 selection 語義），而是讀 pytest 已解析完的結果，
可同時覆蓋否定式、`-k` 過濾、路徑選取（`pytest tests/integration/`）、`all` 四種情形。

⚠️ **代價**：開發者裸跑 `pytest tests/integration/` 而未設旗標時會硬擋（rc=10）。
這與業主先前定的「裸跑不保證 requested-layer 語義」是**兩種不同的取捨**，故列為裁示項。


---

## U0：Baseline Hygiene（**不屬本 spec**，但曾阻擋執行）

> **定位**：`Baseline Hygiene Blocker — outside spec, blocking execution`。
> 不新增 Req.11、不塞進 Task 1。理由：main 的 unit baseline 已紅 →
> 本 spec 任何改動的 PR 仍紅 → **無法判斷「本 spec 是否 regression-safe」**，
> 歸因被污染。與「判定期不動被判定的東西」是同一種量測紀律。

- [x] U0.1 兩筆既存 unit 失敗窄幅 triage → **兩筆皆 `EXPECTATION_DRIFT`，Category A（局部可修）**。
  判定依據為 **commit 級證據**，不是「測試沒過就改斷言」。

| 測試 | 產品變更 commit | 性質 | 判定 |
|---|---|---|---|
| `test_score_shift_probe_req::test_malformed_shift_raises[""]` | `d5c9848` SCORE_SHIFT_PROBE 空字串視為未設定（**線上地雷**）| validation contract drift | 測試落後於產品定案 |
| `test_relevance_gate_req::test_high_vector_similarity_skips_gate` | `7d6fb03` 直答適用性把關改 precision-first（Baseline A）| 產品語義刻意變更 | 測試落後於產品定案 |

**兩筆的產品側證據都指向「不得回退」**：
① `""` 事故——`docker-compose.prod.yml` 的 `${SCORE_SHIFT_PROBE:-}` 在主機未設時展開為空字串，
舊碼 `float("")` 拋錯 → **每一次知識檢索都 500**，且任何容器重建都會再觸發。
② 高向量免判——**高語意相似正是該閘門要擋的錯題型態**，拿它當免判理由自相矛盾（業主定案）。

- [x] U0.2 修復並保住兩邊分支覆蓋（commit `f696e68`，**僅動測試、未改產品碼**）：
  `""`／純空白 自 malformed 清單移出，另立測試鎖「＝未設定、精確 no-op」語義並記下事故；
  高向量免判拆成「預設不跳過」與「顯式設 `RELEVANCE_GATE_SKIP_VEC` 才跳過」兩測試。
  兩處 docstring 的過時描述同步修正，防日後改回。

- [x] U0.3 驗收：容器內 `-m unit` → **1012 passed / 0 failed**（修前 2 failed）。
  main unit baseline 已清乾淨，本 spec 後續 checkpoint 不再背既存紅燈。


---

## 3.3 evidence packet 結果（2026-08-23）

### 結論一：**零 HARNESS_DRIFT**

六案在**保真環境**下，old harness 與 production seam 逐節點比對——
retrieval kwargs／top-k candidates／best_knowledge／門檻／分類推導／config 查表／
pre-entry／final route **全部一致**：

| 案例 | OLD route | PROD route | 期望 | 結果 |
|---|---|---|---|---|
| 點退帳單的金額是怎麼算的 | dialog／條件診斷：帳單 | 同左 | single | 兩側皆 FAIL |
| 點退做完後，帳單會自動出來嗎？ | dialog／條件診斷：帳單 | 同左 | single | 兩側皆 FAIL |
| 收據 PDF 在哪裡下載 | dialog／條件診斷：帳單 | 同左 | single | 兩側皆 FAIL |
| 點退的前置條件是什麼 | single | single | single | 兩側皆 PASS |
| 合約快到期了…自動提醒我嗎？ | single | single | single | 兩側皆 PASS |
| 我的合約狀態怪怪的 | dialog／狀態判斷 | 同左 | dialog | 兩側皆 PASS |

（`no-facet-config` vs `not-routed` 僅 reason 字串差異，**reason 不進斷言**。）

> ⚠️ **所有紅綠變化都來自測試環境保真度，不來自 harness 複刻。**
> 三筆「轉綠」在保真環境下**舊 harness 也 PASS** → 轉綠原因是環境修正，非 seam 替換。
> 「收據 PDF」的 false green 同理——來自錯誤的環境組態，非 harness 複刻失真。
>
> 這同時反證了原先擔心的三個 harness 分歧（門檻讀值點、雙欄位退化、
> `_preentry_routable` 缺席）在現行環境下**皆不產生差異**：
> `old cats == prod cats`、`preentry=True`（gate 預設關 → fail-open）。

### 結論二：三筆紅的根因是**同一次刻意的 metadata 變更**

三筆的 top-1（3519／3402／3406）皆掛 `條件診斷：帳單` 而進面向。
實查：掛該分類的 10 筆知識 `updated_at` **全為 2026-08-04 同一批**。

來源鎖定 `rag-orchestrator/database/migrations/20260731_assistant_report_fixes.sql` §3，
**逐字點名這三筆**：

```sql
-- ── 3. T-1：查資料型知識補面向分類（top-1 命中也能進面向查實值）──
UPDATE knowledge_base SET categories = array_append(categories, '條件診斷：帳單')
WHERE question_summary IN ('點退帳單金額計算 押金結算', '點退帳單 自動產生 費用結算',
                           '帳單收據 PDF 下載')
```

檔頭理由：「**T-1 路由缺口：查資料型知識只掛後台分類，top-1 命中時不進面向**」，
依據 `docs/backtest/assistant-report-regression.md` 批次 20260731（客服回報回歸）。

→ **有後來的產品決策支持現行行為，測試斷言寫於該決策之前**。

### ✅ 判型定案（2026-08-23 業主裁示）：三筆 **`REGRESSION`**，不更新斷言

**關鍵區分：provenance ≠ justification。**

20260731 migration 能證明的是**因果**：

```text
為什麼三筆今天會進 Face？ → 因為 T-1 刻意替這三筆 KB 掛上「條件診斷：帳單」
```

但它**不能自動成為正當性證據**：

```text
為什麼「點退帳單的金額是怎麼算的」應該反問帳單編號？ → migration 沒有證明這件事
```

`EXPECTATION_DRIFT` 的定義要求「**產品行為已合理改變**」。
現在只能證明「後來有人刻意改過 metadata」，**不能證明這三個實際問句進 Face 是合理產品行為**。

**真正發生的是：先前修一個 routing 缺口時製造了新的 routing overreach。**

```text
正確能力需求：「我的這張帳單怎麼算？」→ 需要 instance data → Face 合理
錯誤連帶效果：「點退帳單的金額是怎麼算的？」→ knowledge/rule question
              → 卻因同 KB 的 routing metadata 進 Face → 反問 bill_ref
```

| 案例 | 判型 | 根因 |
|---|---|---|
| 點退帳單的金額是怎麼算的 | **REGRESSION** | KB 3519 為支援 instance lookup 掛 Face metadata，連帶攔截**規則型**問句 |
| 點退做完後，帳單會自動出來嗎？ | **REGRESSION** | 同批 metadata broadening 將**流程／規則**問句錯導入診斷 Face |
| 收據 PDF 在哪裡下載 | **REGRESSION** | KB 3406 為支援「我的收據在哪」掛 Face metadata，連帶攔截**操作位置**問句 |
| 其餘三案 | PASS | old／prod 行為一致，現行 expectation 成立 |

```text
HARNESS_DRIFT     = 0/6
EXPECTATION_DRIFT = 0/6
REGRESSION        = 3/6
PASS              = 3/6
```

> 這個結果比「5 筆改 seam 後剩 3 筆」有價值得多——現在可以明確說：
> **原 routing harness 沒有造成這六案的判定失真；留下的三案是 production routing behavior 本身的問題。**

### ⚠️ 修法不得跳成「拿掉分類」

20260731 的需求**本身是真的**：instance-specific 問法確實需要進 Face。
直接把三筆的 `條件診斷：帳單` 拔掉，只是**把舊 T-1 bug 裝回去**。

修的是「**同一 KB 同時承載 knowledge evidence 與過寬 Routing Hint**」這個
routing metadata 問題，**不是否定 Face entry 本身**。兩邊都要保住：

```text
規則／流程／操作問句        → single answer
我的某一筆／實際狀態／實際金額 → dialog Face
```

具體採「拆 KB」／「新增更窄的 instance-oriented trigger knowledge」／
其他 metadata 收窄方式，留待修復任務讀現有 corpus 後決定——
**3.3 只負責把產品錯誤判真，不順便設計修法。**

⚠️ 兩筆 corpus-exposure failure（`test_grounding_by_parent_expands_to_children`、
`test_three_layer_context_isolated`）維持獨立 triage，**不併入本結論**。


---

## 3.4 修法 **REFUTED**（2026-08-23 獨立 verifier ＋ 業主裁示）

### 判定：instance-oriented anchor 修法不足，**不放行、不追加 anchor**

原三筆 regression 確實轉綠（83 passed / 0 failed），但 matched before/after
＋ 對抗性變體證明修法本身不成立：

| # | 反證 | 證據 |
|---|---|---|
| 1 | 合理 **instance** query 掉回 single | 「我這筆點退帳單怎麼會是這個數字」→ single（3519 **0.905** vs 錨點 **0.902**，差 **0.003**）|
| 2 | 合理 **rule** query 反被錨點拉進 Face | 「系統怎麼算點退帳單的金額」→ dialog（錨點 **0.967** vs 3519 **0.963**，差 **0.004**）|
| 3 | 判別完全依賴 **0.003～0.005** 的相似度競爭 | corpus 新增或 semantic-model 重建即可能翻面 |
| 4 | integration **原本沒有 instance-side coverage** | 「三筆 regression 綠了」曾構成**假綠**——修法只證明了一半 |

> **問題性質已改變**：不是「還少一個好句子」，而是
> **rule KB 與 instance-routing anchor 在 embedding space 高度重疊**，
> 兩邊靠極小排名差決定產品語義。再補一個錨點只是增加第三個相互競爭的向量，
> **不消除判別機制本身的脆弱性**，且等同「對著測試集調向量排名」。

處置：`ae2aedc` 已由 `89ff489` revert；該 migration **從未套用至 production**。

### 3.3 的 defect 判定**不受影響**

```text
HARNESS_DRIFT 0｜EXPECTATION_DRIFT 0｜REGRESSION 3｜根因＝routing metadata overreach
```

被推翻的只是 3.4 所選的修法。**Requirement 2 的精確狀態**：

> **production defect 已證實；本 spec 範圍內嘗試的 metadata／anchor 修法已被反證不足，
> 修復需要超出 Req.8 現有邊界的設計工作。**

### 已補：雙向 regression suite（本輪唯一保留的產出）

`test_facet_entry_routing_req.py` 新增 `BILLING_INSTANCE_CASES`（4 筆），
**斷言到 facet 而非僅 dialog**——3.4 驗證期間「我的收據在哪」被誤記為 instance 通過，
實測它進的是「帳單異常」而非「條件診斷：帳單」；只看 `route=='dialog'` 的判定式
會把**跑錯面向算成成功**。同時把「系統怎麼算點退帳單的金額」補入規則側。

另立 `BILLING_INSTANCE_FACET_UNDECIDED`：實測進其他面向、**產品歸屬尚未定案**者
（「我的收據在哪」／「我這筆點退的錢怎麼怪怪的」皆進「帳單異常」），
定案前不列入正向斷言——**不得拿「跑錯面向」當成能力成立的證據**。

### 現行 production 狀態（本 suite 首次同時描述雙邊能力）

```text
84 passed / 4 failed
  instance 側 4/4 ✅   ← T-1 能力目前成立
  rule     側 4/4 ❌   ← 代價：規則問句被誤捕
```

> **這兩件事共用同一份 metadata，用現行機制拆不開**——
> 這正是另立設計案要解的問題，也是本 suite 存在的價值：
> 它讓「修好一邊就宣稱成功」在結構上不再可能。

⚠️ **在設計案定案前，不得為求綠燈調整本組任一斷言。**

### 另立案（範圍外）：routing disambiguation

要回答的**不是**「該用哪個 instance-marker」，而是：

> **當同一語義主題同時包含教學型與 instance-specific 問句時，
> routing 應在哪一層取得足夠訊號，把兩者可靠分開？**

候選層次（何者可行、何者觸及 Req.8，由新案研究）：
lexical／structural instance signal｜routing-specific metadata／trigger representation｜
intent stage｜applicability gate｜clarification｜KB responsibility 拆分。

⚠️ **不得因為 embedding 排名分不開，就在本 spec 內偷塞全域 heuristic**（Req.8 明文排除）。


---

## U1：corpus-exposure triage（**不屬本 spec**，已結案）

- [x] U1.1 兩筆 known-red 窄幅 triage → **同一根因，Category A（provisioning drift）**

| 測試 | 依賴機制 | 缺什麼 |
|---|---|---|
| `test_grounding_by_parent_expands_to_children` | `_grounding_by_category` 父層展開：`SELECT category_value FROM category_config WHERE parent_value=$1` | 父子分類對照 |
| `test_three_layer_context_isolated` | `system_context._domain_chain` 以 `category_config` 遞迴父鏈組三層脈絡 | 同上 |

三問：①**穩定重現**——凍結 corpus 下每次皆紅；②**判型**——provisioning 缺口，
非 corpus collision、非 production regression（`category_config` 是 `knowledge_base`
之外的獨立對照表，最小供裝漏列）；③**最小處置**——加進 `SEED_TABLES`。

實查：測試庫僅 **23 列**（前幾輪 integration 殘留），prod 為 **98 列**。

- [x] U1.2 補 `category_config` 至供裝（98 列）→ 針對性重跑 **6 passed / 0 failed**

### ⚠️ 「最小供裝」的邊界只能靠實跑劃，不能靠讀 schema 推

這是第三次由實跑逼出必備項：

```text
form_schemas     ← form_sessions.form_id 有 FK，缺它任何面向會話都 ForeignKeyViolationError
provenance FK    ← knowledge_base 四條 FK 的父表鏈太深 → 改為載入時置 NULL
category_config  ← 父子分類對照，缺它父層展開與三層脈絡失效
```

三者皆已在 `scripts/provision-test-db.sh` 逐條註記理由，避免日後被當成可省項。

---

## 本 spec baseline 封存（2026-08-23）

```text
unit         1025 passed / 0 failed
integration   177 passed / 4 failed / 11 env-skipped / gate_skipped=0 / rc=1
```

**唯一的 4 筆 known-red 全部是 3.3 已判定的 `REGRESSION`**，且已在雙向 suite 中
與 instance 側能力綁定描述——修好任何一邊都會讓另一邊紅：

```text
收據 PDF 在哪裡下載
點退帳單的金額是怎麼算的
系統怎麼算點退帳單的金額
點退做完後，帳單會自動出來嗎？
```

⚠️ **這 4 筆不得為求綠燈調整斷言**；修復由 `routing-disambiguation` 新案處理。

### Known limitations（隨 spec 封存）

| # | 限制 | 出處 |
|---|---|---|
| 1 | harness 繞過 SOP 仲裁——`_diagnosis_config_for_knowledge` 僅在 `decision['type']=='knowledge'` 時可達；本 spec 無結果可證 SOP 勝出時的端到端行為 | 3.4 verifier A3（既有限制，非本輪引入）|
| 2 | 「我的收據在哪」／「我這筆點退的錢怎麼怪怪的」進「帳單異常」而非「條件診斷：帳單」，**產品歸屬未定案** | `BILLING_INSTANCE_FACET_UNDECIDED` |
| 3 | CI 無從零建 schema 的路徑（service container 為空庫，供裝腳本依賴本機來源庫做 schema dump）| 2.4（既有狀態）|
| 4 | `DecisionConfig` 程式預設 `kb_threshold=0.55` 與參數台帳 `0.65` 不一致，靠 env 覆蓋而無害；env 未設的環境會靜默跑 0.55 | 3.1 對碼（範圍外，建議 follow-up）|
