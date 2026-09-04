# 決策紀錄

**起始日:2026-08-22**

⛔ **本表只保證此日之後的決策。** 在此之前的決策沒有回填,不在此表**不代表**沒有決定過——
歷史散落在 git log、`.kiro/specs/*/design.md` 的技術決策段落,以及
`.kiro/specs/retrieval-decision-layer/decisions/DECISIONS.md`(該 spec 自帶的 D-01 起決策表)。
⚠️ 回填歷史會製造「這就是全部」的假象,那比空表更危險。

## 怎麼寫一列

| ID | 決定 | 來源 | 出處 | 落點 | supersedes |
|---|---|---|---|---|---|

- **來源** = 誰做的決定。`業主` / `代理`(代理發現的爭議,未經裁決)
- **出處** = 證據在哪(對話日期、commit、spec 段落)
- **落點** = 這個決定落在程式的哪個符號或路徑,⛔ 會被 refcheck 驗
- **supersedes** = 這一條取代了哪一條(填 ID)

⚠️ `來源=代理` 的條目會被算成 **unresolved**,⛔ 永遠不會變成 current,
直到人裁決為止。這是刻意的:系統不准偷偷選邊。

---

| ID | 決定 | 來源 | 出處 | 落點 | supersedes |
|---|---|---|---|---|---|
| D-001 | 架構母圖 §3 的過濾公式**以 runtime 為準逐行修正**，⛔ 不是加警語。判準:`descriptive` 類文件描述「現在怎麼跑」而描述錯了，處置是修文件，不需裁決 | 業主 | 2026-09-01 對話「錯誤順便修正處理？」 | `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` | |
| D-002 | b2b 業態過濾 `business_types && {system_provider}` **無 `IS NULL` 放行**，⛔ 補上會打穿跨業者隔離。b2c 才是 `IS NULL OR &&` | 業主 | `docs/retrieval-recall-audit-20260822.md`「勿改」條 ＋ 2026-09-01 逐行對碼 | `rag-orchestrator/services/vendor_knowledge_retriever_v2.py` | |
| D-003 | 已封存 spec ⛔ **不得列為前置必讀**。`decision_layer.py` 的 3 條死引用**移除**而非改指 `archive/`——後者會強迫閱讀一份已停案的 spec | 業主 | 2026-09-01 對話「避免被讀到」；`HANDOFF-20260901.md` §0「⛔ 不是主線」 | `.claude/prerequisites.json` | |
| D-004 | `KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md` 退休歸檔並自標——它引用的兩個檔案都不存在、過濾模型已被 v2 取代 | 業主 | 2026-09-01 對話；`b2b-doc-status-ledger.md` 第一類 | `docs/archive/2026-09/KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md` | |
| D-005 | 文件的**刪除判準是「錯的是什麼」不是「有沒有錯」**:前提全滅且無唯一資訊→刪；前提滅但記錄決策→歸檔；局部錯而其餘是唯一正本→修正，⛔ 不准刪 | 業主 | 2026-09-01 對話「沒有留著的必要就刪了吧」（據此刪 3 份零引用檔） | `scripts/BACKLOG.md` | |
| D-006 | `.claude/MAP.md` 與 `DECISIONS.md` **移出 `.git/info/exclude`、納入版控**——`canon.json` 自己寫明它們是專案資產;先前被排除⇒修改無版本歷史 | 業主 | 2026-09-01 對話「好 進 git」 | `.claude/MAP.md` | |
| D-007 | IVFFlat 缺陷**降級為潛在地雷**:原判「靜默丟答案影響生產」**是錯的**——生產 `ORDER BY (1-dist) DESC` 用不上向量索引，35 題修前後逐筆相同。危險在於有人把它改成正規寫法就引爆 | 代理 | `ivfflat-index-defect.md`「2026-09-01 更正」節 | `.kiro/specs/conversational-routing-execution/ivfflat-index-defect.md` | |

⚠️ 本表的 `D-0xx` 與已封存 spec `archive/retrieval-decision-layer/decisions/DECISIONS.md`
的 `D-01` 系列是**兩套獨立編號**，⛔ 不得互相引用。
⚠️ `D-007` 來源為**代理**⇒ 依本檔規約算 unresolved，⛔ 在業主裁決前不會變成 current。
| DSP-001 | ⚠️爭議:面向 grounding_scope.requires_instance_reference=true 是否構成該面向所屬知識的 knowledge 層 instance machine evidence | 代理 | rag-orchestrator/services/instance_applicability.py 模組 docstring（裁定②證據門檻不對稱 vs 兩層契約語義不同） ／ 實作:instance_applicability_decision 允許 general×REQUIRED→INELIGIBLE；contract_closeout/contract_change/contract_sign/contract_renew 四面向 requires_instance_reference=true |  |  |
| DSP-002 | ✅**已裁（業主 2026-09-02）**:①空 answer 錨點 ⛔ **不計為面向覆蓋**（它不能成為答案）；②**api 型與對話型面向的答案不來自 KB answer 欄**（`_ground_by_api` 以 API 回傳為合成底稿） ⇒ 對它們「知識數」量到的是**提名入口數**、⛔ 不是答案覆蓋。三個數字各自的用途（非爭議，事實層）：293 答題母體約定（`_B2B`，含刻意窄化：僅 property_manager、扣 4253，⛔ 不是生產答題路徑的模型）／354 兩路聯集上界／354·320 分路上界（`visibility().paths.*`）。⚠️ `visibility()` 只給**結構上界**：`visible=False` 是硬結論，`visible=True` ⛔ 不保證任何一題撈得到。 | 業主 | spec:conversational-diagnosis/design.md 核心元件 1（API grounding：收斂以 API 回傳為合成底稿）、domain-conversational-facets/design.md 元件 2 ／ 實作:`conversational_engine` 符號 `_ground_by_api`；`status.py` 符號 `print_b2b_surface`（已依 select 分開標示） ／ ⚠️ 原版問法「_B2B vs visibility() 二選一」不成立且引用錯數字（293/264，實為 354/320），已作廢 | scripts/status.py:print_b2b_surface |  |
| DSP-003 | ⚠️爭議:回測 session_id 前綴：量測層級.md 說避開 backtest_，run_batch.py 說必須 backtest_session_ —— 兩者都自稱 ⛔ | 代理 | .claude/skills/retrieval-improvement-loop/rules/量測層級.md〈執行規約〉「⛔ 前綴避開內部保留字（backtest_／loop_／smoke_）否則會被標成內部流量」 ／ 實作:run_batch.py 符號 _REQUIRED_PREFIX='backtest_session_'（為吃到 chat._record_no_knowledge_scenario 的題庫豁免）；usage_metering 符號 INTERNAL_RULES 比對 startswith('backtest_') ⇒ 用了必被標成內部流量 |  |  |
| DSP-004 | ✅ 租約特有欄位來源＝**A**：chatai 消費 DocuMind 既有 `rental_terms`（租約值優先、通用進 conflicts；`deposit` 混鍵不消費），第二段 LLM 抽取（B）作廢；缺欄由 DocuMind 補樣式 | 業主 2026-09-04「依序處理」採預設 A | .kiro/specs/documind-ocr-mapping/requirements.md〈待業主裁決〉D1 ／ 實作:services/ocr_mapping/contract_mapper.py 符號 CONTRACT_SOURCE_MAP（DocuMind contract 型無 deposit_type／cycle_date／cycle／early_termination_*；second_pass_extractor 未實作、ENABLE_OCR_SECOND_PASS 預設 false）；⚠️ 2026-09-03 晚新事實：DocuMind `contract_field_extractor.py` 符號 `rental_fields` 已輸出 `rental_terms` 群組（14 欄，僅制式標籤命中），chatai 未消費 ⇒ A 可先零改 DocuMind 起步 |  |  |
| DSP-005 | ⚠️爭議:端點形狀：新資源 POST /api/v1/ocr-mapping/{document_type}（A，已實作）還是掛在 /api/v1/message 加 action（B） | 代理 | .kiro/specs/documind-ocr-mapping/requirements.md〈待業主裁決〉D2 ／ 實作:routers/ocr_mapping.py 符號 router = APIRouter(prefix="/api/v1/ocr-mapping")（已依建議 A 實作；若改掛 /api/v1/message 需重做 router） |  |  |
| DSP-006 | ⚠️爭議:承租方姓名要不要由 chatai 切姓／名（split，預設）還是整串交 LIFF 拆（keep_full）；複姓表以 JGB 慣例為準（Q5） | 代理 | .kiro/specs/documind-ocr-mapping/requirements.md〈待業主裁決〉D3 ／ 實作:services/ocr_mapping/name_splitter.py 符號 NamePolicy／COMPOUND_SURNAMES（兩策略皆已實作；env OCR_NAME_POLICY 預設 split，兩欄恆進 needs_confirmation） |  |  |
| DSP-007 | ✅ 不變量 10 與 17 互斥的解法＝**D 明示排除**：R10-P V1 母體維持 08-29 凍結的 54 列；凍結後才宣告的 id 登記於 `r10p/v1-scope-exclusions.txt`（＝明示版本決策），不變量 17 只對**未登記**的新宣告判漂移、且排除清單不得含凍結成員。⛔ 否決 B（凍結 54 內本有 5 筆 general，改定義成「只納 instance」會把母體縮到 49）；⛔ 未採 A（升版 88 需重跑 F1 proposal／P4 projection，三支檢查器寫死 54）。代價：3327／3329／3331／3333 標 general 的責任變化 V1 看不到，V2 必納 | 業主 2026-09-04「好」（採建議 D） | scripts/audit/checks/instance_applicability_contract.py 不變量 10（2026-08-30 後 touched 的情境知識必須明示 instance_applicability）vs scripts/audit/checks/r10p_population_integrity.py 不變量 17（R10-P 母體＝la ∪ alias ∪ 所有已宣告列，凍結 54，任何新宣告＝漂移 FAIL） ／ 實作:2026-09-04 00:4x 對 3327–3360＋3930 共 34 筆寫入 generation_metadata.instance_applicability=general（業主授權）⇒ 不變量 10 轉綠、不變量 17 現況乾淨轉紅：聯集多出 34 id；還原則 10 重紅。symbol: r10p_population_integrity.py declared AS (SELECT id FROM knowledge_base WHERE generation_metadata ? 'instance_applicability') |  |  |
| DSP-008 | ✅ **業主 2026-09-04 裁：匯入事實以 jgb2 現況為準。** jgb2 原始碼（`~/jgb/project/jgb/jgb2`，分支 ticket_12899002511，scout 2026-09-04）：可批次匯入＝物件（`routes/web.php` `/general/batch/*`→`EstateController@generalBatch*`、社宅 `socialHousingBatch*`）、租客（`routes/api.php` `/batch/import`→`LesseeController@batchImport`）、帳單（`BillController@batchImportExcel*`，僅 Ango role＋法人房東；匯入＝建立待發送新帳單，⛔ 不是搬歷史帳單）、社區（`CommunityController::batchPreview`）、大房東記錄（`BiglandlordController::importBigLandlordRecordsFromExcel`）；**合約 ⛔ 不支援**（Web 只有單份 PDF 上傳 `/api2/contract/upload/{id}` 與 `batchDelete`；社宅合約是後台 CLI `social-housing-contract:import`）。⇒ 盤查檔 §P1-3「只有帳單支援批次匯入，物件／合約／租客都要手動建」**錯誤**（幫助中心 `onboarding4_zh-Hant.html` 亦明寫物件批次上傳）；知識 3357／3431／3476／3404／4638 **與 jgb2 一致、不改**；真缺口＝「合約不能批次匯入、帳單匯入不是搬歷史」邊界句 ⇒ 補一筆 prospect 知識。P1-2／P1-3 定性：LLM 把「物件／租客可匯」推廣成「合約／歷史帳單可匯」＝**答錯**（非答不完整）。⚠️ 證據取自 ticket 分支非 master；四類功能路由＋Controller＋Validator＋Job＋前端俱全，上線狀態以 preview 部署為準 | 業主 | docs/presales-assistant-quality-audit-20260902.md §P1-3（原爭議）；scout 報告見本 session；幫助中心 onboarding4／Landlordonboarding06Finance | scripts/knowledge-batches/presales-phrasing-batch-20260904.json（匯入邊界句列）；docs/presales-assistant-rootcause-20260904.md §DSP-008 | 原 DSP-008 爭議列 |
| DSP-009 | 售前缺口地圖「刻意不補」五格的裁決引用：客戶案例／規模、SLA／賠償、資安認證／資料存放、個資法、客製報價 ⇒ 一律固定句轉人、⛔ 不補知識。依據＝presales-grounding-gate requirements「已拍板決策」#2（敏感五類 customer_reference／pricing／contract_sla／compliance／security 由 fact_class 分流出口）與 #3（客戶規模／案例類刻意不補），業主 2026-09-04 裁 A 收案時確認。地圖 demand JSON 的 policy=deliberate_no 必引本條；無引用者不得計入刻意不補（plan-verifier P2） | 業主 | .kiro/specs/presales-grounding-gate/requirements.md 已拍板決策表；perf-20260904.md §9–10 | .kiro/specs/presales-grounding-gate/coverage-map/demand-v2.json cells C10/C48–C51 policy_ref |  |
| DSP-010 | ⚠️爭議（未裁）：合約範本數——幫助中心 `landlordonboarding04lease_zh-Hant.html` 寫「內政部所規範的五種合約範本」（原房東中文／包租業中文／代租代管中文／英文／英越文），`qa06_zh-Hant.html`（編輯日期 2026/06/29）寫「通用範本共 12 種」＋三種特殊用途範本。兩份官方文件不一致；3600 主題頁採較新的 qa06。待業主向內容端確認，⛔ 未裁前不得改回五種 | 代理（verifier 2026-09-04） | 幫助中心兩檔逐字；scripts/knowledge-batches/presales-topic-contract-3600-20260904.json `_meta.disputes` | 3600 主題頁【範本】段 |  |
| DSP-011 | ✅ **業主 2026-09-04 裁：權限由 jgb2 API 全權處理，本系統只管額度。** 適用 agentic-mcp 全路徑（in-process 與 MCP 門面）：`role_id`／`user_id` 為上游信任輸入（沿用 F-C25），個資可見範圍由 jgb2 `external/v1` 兩層權限（API Key 權限表＋`viewer_user_id`→`VisibleScope`）裁；本系統對呼叫者只有 `api_key_guard`（服務層）與 `quota_check`（額度）。⇒ MCP 門面定為**非公開認證面**（只給上游／內部呼叫者），⛔ 不實作 bearer 簽發／claims 驗證；security-reviewer 的 P0「bearer 信任鏈未定義」「MCP 暴露 jgb2.query 打穿上游授權前提」依本條 REJECT。**例外**：知識池可見性（vendor_ids／business_types／target_user／保留分類）住本系統 DB，仍由本系統謂詞守（`build_visibility_predicate`）。前提破了（出現未經上游的公網呼叫者）要重開 | 業主（「權限的部分 由 api 全權處理」「此系統只管額度」） | .kiro/specs/agentic-mcp-orchestration/design.md 1.1〈授權定案〉；jgb2-source-index.md §3.5；memory project_role_trust_boundary | design 1.1 元件 4、決策 8、附錄 C |  |
| DSP-012 | ⚠️爭議（未裁）：agentic-mcp requirements R11.1「知識文字視為不可信輸入，⛔ 不得把回傳文字拼進 system prompt」vs R5.1「售前池整理成大綱進上下文（system prompt）」字面衝突。design 1.2 假設：大綱是 server 端由已審核知識列組裝、非工具回傳，套 nonce 分隔標記後允許；知識入庫（knowledge_import／document_converter）作者面仍是注入面。待業主裁：接受此假設（改 R11.1 措辭）或大綱改走 `kb.get("outline:*")` 按需讀取不進 system prompt | 代理（security-reviewer 第二輪 2026-09-04） | .kiro/specs/agentic-mcp-orchestration/requirements.md R5.1／R11.1；design.md 1.2 元件 5、決策 14 | design 1.2 元件 5 |  |
