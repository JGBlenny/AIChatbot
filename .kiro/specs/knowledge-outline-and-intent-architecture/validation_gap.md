# 實作缺口分析：knowledge-outline-and-intent-architecture（2026-09-06）

> 依 requirements v2（R1–R8）對碼；⚠️ `.kiro/settings/rules/gap-analysis.md` 不存在，沿用 agentic-mcp 的分析結構。資訊與選項為主，⛔ 不在此定案。查證來源：本 session 對碼＋scout 盤點（六節，附檔案／符號）。

## 0. 一句話
既有系統有「組裝」「匯入」「回測」「可見性」四塊可直接用；缺的是三個新物件——**正本（粗目／細目／講法）**、**細目索引**、**skill 流程機制（schema／閘門／回放）**——以及對話邏輯從 kb 3645 搬進 agent 的接線。

## 1. 既有元件對照（R → 可用／要改／缺）

| 需求 | 既有元件 | 狀態 | 缺口 |
|---|---|---|---|
| R1 skill | `.claude/skills/retrieval-improvement-loop/SKILL.md`（七步、五閘門 G0–G4、成因八類、`g2_selftest.py`、rules/／steps/）；`scripts/status.py` 母體正本 | **可延伸**：閘門與成因分類思想直接沿用 | 無輸入輸出 schema；閘門靠 SKILL.md 文字不靠 hook；無「正本結構變更」步；無回放（輸入 sha→輸出）；無成本記錄 |
| R1 執行形態 | `.claude/agents/` 與 `.claude/workflows/` 於本 repo **不存在**（角色定義在使用者層）；canon-audit 閘門實作在 `~/.claude/canon/`（使用者層）；`.claude/settings.local.json` 只有 allow 清單、無 hooks | **缺** | 若採 hook 閘門須在 repo 層新增 hooks 設定；若採 Workflow 須新建 `.claude/workflows/`；兩者皆無先例於本 repo |
| R2 正本 | `outline.py::build_prospect_outline`／`build_toc`／`_build_doc`／`OutlineDoc{audience,version,sha256,token_count,sections,text}`／`check_budget`／`OUTLINE_TOKEN_LIMIT_DEFAULTS`（prospect 10k／pm 8k／tenant 8k） | **組裝機制可用，資料來源要換**：現由 kb 列＋`SIX_MODULES` 分類表產節；改為讀正本 | 無正本檔格式；無粗目／細目／講法資料結構；`OutlineSection` 缺 audience／approval／paragraph 層；`_CTA_TEXT`／`DSP009_DELIBERATE_GAPS`／`_extract_boundary_sentences` 三段要併入正本 G／F |
| R2.7／R5.4 審核狀態 | `knowledge_base.outline_approved_by`（一次性 UPDATE 標記）；`tools/kb.py::fetch_visible_row` 走 `build_visibility_predicate` **不看**該旗標 | **要改** | 旗標語義（池標記 vs 內容已審）；`kb.get(整數 id)` 直取須受約束（R8.4 需求票） |
| R2.9 治理 | 知識匯入 `tools/import_facet_knowledge.py`（dry-run、冪等、rollback SQL、`instance_applicability` 強制、question 改重算 embedding）；`scripts/knowledge-batches/README.md` | **可用**：正本入庫可走同一工具的批次格式 | 正本（版控 Markdown）→ 批次 JSON 的轉換器缺；「正本寫入權＝prompt 寫入權」的 code review 閘門缺 |
| R3 覆蓋閉環 | 缺口地圖成品 `coverage-map/map-v2.{json,md}`、`demand-v2.json`（55 格）；**無**獨立生成腳本（人審凍結／臨時腳本） | **缺工具** | 格→細目對應、去向欄、受眾維度、重量腳本皆缺；判者一致率報表缺 |
| R4 對話邏輯 | kb 3645（DB 覆寫）＋`conversational_config.py`（`PRESALES_ANSWER_RULES`／`PRESALES_CTA_RULES`／handoff 設定）；agent 端 `agent_rules.py::_POLICY_TEXT`＋`_SENSITIVE_LINE`；`AgentOutput.kind{answer,ask,recommend,handoff}` | **要搬**：定義文字有正本，契約有 kind | A/B 判準、補問策略、CTA 程式端附加、handoff 設定接線（runtime 現傳 None）、persona 分支皆缺 |
| R4.1 身分槽位 | `Identity.resolved_audience()`；`SlotKey` 六值；`slots_set` 需 `COLLECTING` 會話列、⛔ 不建列；`prompt_assembler._slot_blocks` 渲染 | **要改** | 加 identity／team／pain／interested；預填時機（回合開始、會話列可能不存在）；R8.2 需求票 |
| R5 檢索 | `services/embedding_utils.EmbeddingClient`（`get_embedding`／`get_embeddings_batch`，30 s timeout，吞例外回 None）；`build_visibility_predicate`；`provenance_units`／`resolve_refs`（標記 `[nonce:outline:<source>§i]`，`_REF_RE` 可吃 `#`） | **可用**：向量、可見性、引用解析都有 | 細目索引（標題向量＋講法向量、取最大、快取鍵＝正本 sha＋講法集 sha）缺；講法表缺；候選注入路徑（DSP-035 Plan v3 的 `CandidateOutlineDoc` 走既有 `outline` 參數）可沿用設計但需改為細目 |
| R5.6 講法治理 | 無 | **缺** | `agent_paragraph_anchors`（tasks 4.7 草案）改名為細目講法表；命中數要 trace（R8.3） |
| R6 驗證 | `tools/agent_eval.py`（四組樣本、`--repeat`、`--dump-texts`、manifest sha 拒跑 exit 3／4、`EvalRecord` 18 欄）；`agent_attempts_report.py`；blind 封包法（scratchpad `packet.py`／`score.py`，一次性）；`tests/unit/_meta/test_env_parity_req.py`（compose 對齊） | **可用** | 材料：問法正本切選規則（scratchpad `s1_material_candidates.jsonl` 422 句）未入版控；可答性判者流程未工具化；留一驗證腳本（`recall_para.py` 代替品）需改為細目標題＋講法；探針多條件 arm 需 `agent_eval` 支援依賴注入（`--candidates` 草案） |
| R7 LINE 知識區塊 | chatai 四份文件（scout 四表）；面向 `repair_create`／`bill_diagnosis`／`contract_renew`／`iot_meter` 既存 | **缺正本** | LINE 受眾正本、可見性定義（不帶 vendor_id → 入口填 0 → b2b 嚴格過濾）、待驗清單 |
| R8 平台票 | agentic-mcp 的 trace／snapshot 白名單（`test_runtime_req.py::_ALLOWED_AGENT_DECISION_KEYS`）、不變量 30（`agent_boundary.py::DECISION_BANNED_KEYS`） | **可用** | 新鍵（candidate_ids、winning_phrasing_id、miss_kind）需走該 spec 的變更流程 |

## 2. 取代規則：skill 產出細目取代既有 kb 列與草稿（R1.9）

```
首跑讀取：21 列 prospect kb ＋ 18 筆草稿（舊形狀）
skill 產出：粗目／細目／講法／內容 ＋ 取代對應表（舊 id → 細目 id）
之後：舊列標「由細目取代」退役，不再作索引或內容來源；kb 內容列由正本匯入衍生（匯入工具沿用）
  question_summary 關鍵字 → 併入細目講法（各一向量；⛔ 不再是一條匹配摘要）
  answer 文字            → 細目內容（可引用句），或併入既有細目
  target_user／業態      → 細目受眾維度與可見性（沿用謂詞）
  非本受眾列（F2 的 8 列 IS NULL 業者列）→ 不進售前正本，留給對應受眾的正本
```
含意：`knowledge_base` 對 agent 路徑退為「正本的衍生儲存＋可見性標記」，真相源移到正本；舊鏈仍讀 kb（不受影響），直到各受眾切到 agent。

## 3. 實作選項（供 design 選，各附取捨）

### 3.1 正本格式
| 選項 | 內容 | 取捨 |
|---|---|---|
| A. Markdown＋YAML front matter，每細目一節 | 人可讀、diff 友善、版控 review 天然 | 需解析器；講法多時檔案長 |
| B. JSON／YAML 結構檔 | 直接餵組裝器與匯入工具、schema 校驗容易 | 人審不友善 |
| C. 混合：Markdown 為人審正本，skill 產生同 sha 的 JSON 中介檔 | 兩邊各得其所 | 兩份要同步（以 JSON 由 Markdown 導出、單向） |

### 3.2 細目索引存放
| 選項 | 內容 | 取捨 |
|---|---|---|
| A. 記憶體內（啟動時由正本組裝，快取鍵＝正本 sha＋講法集 sha） | 最簡、決定性、無 migration；量級 ≤2k 向量 | 多 worker 各算一份；重啟重算（幾秒） |
| B. pgvector 新表 | 可查、可稽核 | migration、與 kb 表雙軌 |

### 3.3 講法表
| 選項 | 內容 | 取捨 |
|---|---|---|
| A. 新表（tasks 4.7 草案改名）：細目 id／phrasing／source／status／hit_count | 治理欄位齊 | migration＋工具 |
| B. 存在正本檔（版控）內，命中數另記 trace | 無 migration、審核走 review | 命中數與正本分離 |

### 3.4 skill 執行形態（R1.5）
| 選項 | 內容 | 取捨 |
|---|---|---|
| A. SKILL.md＋腳本（沿用 retrieval-improvement-loop 形態） | 有先例；改動小 | 閘門靠文字；判者隔離靠人為 |
| B. Workflow 管線（固定步驅、schema、判者 fan-out） | 步驟輸出可機器校驗、判者天然隔離、可從步續跑 | 本 repo 無先例；成本／代理數要控 |
| C. 混合：SKILL.md 定義流程、關鍵步（提議結構、判可答性、重量）走 Workflow、紀律走 hook | 各取所長 | 三種機制並存的維護成本 |

### 3.5 候選注入路徑（R5.1）
沿用 DSP-035 Plan v3 的形狀（runtime 建 `CandidateOutlineDoc` 走既有 `outline` 參數、audience/sha 從母 doc 複製、同一物件餵渲染與解析側），把「段落」換成「細目」；三輪審查的 P1 處置（政策文允許 kb.get、select 綁 doc sha、app.py 主／影子共用 selector、fallback 三態、health 三態）仍適用。

## 4. 風險與研究項
- **正本無原稿**：售前 A–F 只能由 21 列 prospect 重排；E 競品內容單薄（現存 1 列）；需業主提供或標「現有不足」。
- **細目標題匹配未量**：F10 的 86% 是內文匹配的代替品；R6 步 1 三臂（標題／標題＋講法／＋內文）決定 R5.2。
- **判者變異**：兩批盲標對同尺評價差距曾達 9 點；R6.5 的一致率門檻與第三判者機制要先定。
- **LINE 受眾可見性**：入口對缺 vendor_id 填 0 的實際可見集合未實查（需一次 SQL 對照）。
- **Workflow 與 hook 在本 repo 無先例**：需一個最小試作（例如只把「判者 fan-out」做成 Workflow）量成本與可回放性後再決定 R1.5。
- **平台票排程**：R8.1–8.4 若 agentic-mcp 未排，R4.1／R5.8／R5.9 無法落地；design 要標依賴順序。

## 5. 建議的 design 切法（非定案）
1. 先 R1 skill 最小可用版（輸入舊形狀 kb 列＋草稿 → 提議粗目／細目／講法 → 判者可答性 → 差異表），用售前 21 列＋18 筆草稿首跑，產出人審正本草稿。
2. R2 正本格式與組裝器改讀正本；R2.7 旗標語義。
3. R6 步 1（細目標題匹配上限，免費）→ 決定 R5.2 與講法表形態。
4. R5 細目索引＋候選注入（沿 Plan v3 形狀）＋R4.1 身分槽位（需 R8.2 票）。
5. R4 對話邏輯搬遷（含 CTA 程式端、handoff 設定接線）→ R6 步 2／3 探針。
6. R3 覆蓋閉環工具化與重量；R7 LINE 正本。
