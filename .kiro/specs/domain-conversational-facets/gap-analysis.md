# 落差分析：domain-conversational-facets

> 建立時間：2026-07-01｜性質：Brownfield Extension（既有對話引擎 + 系統脈絡 + 檢索 grounding 之加性擴充）
> 對照：requirements.md（R1–R8）｜research.md（合約 ground-truth）
> 結論先行：**8 個需求中 7 個是「擴充既有元件」，零件多已存在；最大單一決策是 R2/R3 的邊界（基底架構走 system_md 常駐 vs 收斂時檢索）。**

## 一、現況元件盤點（可重用）

| 能力 | 既有元件 | 位置 | 重用度 |
|---|---|---|---|
| 系統脈絡載入 | `get_system_context(db_pool)` 全域單例、查 `category='系統脈絡'`、單槽快取 | `services/system_context.py` | **改造點**（參數化） |
| 規則載入（**per-角色**範本） | `load_rules(db_pool, role)`：查 `category='對話規則' AND target_user @> [role]`、**per-role 快取** | `services/conversational_rules.py` | **模式範本**（R2 照抄） |
| 分類撈知識 | `_grounding_by_category(category, target_user)`（含**父層展開**）、`_grounding_by_ids(kb_ids)` | `conversational_engine.py` | **直接重用**（R3） |
| 母/子分類 | `category_config.parent_value`（欄位已存在，有索引） | DB | **直接重用**（R1） |
| API grounding + 候選 | `_ground_by_api`：三路、候選 `[{id,label}]` 取自 `result_mapping.id_field/label_field` | `conversational_engine.py` | **改造點**（R4 label_fields） |
| 混合合成 | `synthesize_presales_answer(grounding, ctx, system_md, …)`（**已同時吃 grounding + system_md**） | `llm_answer_optimizer.py` | **直接重用**（R3） |
| 設定載入 | `ConversationalConfig`（`grounding_scope`/`topic_scope` 自由 dict）、`_config_from_row`、快取 | `services/conversational_config.py` | 擴充（加鍵，payload 不變） |
| 引擎注入脈絡 | `prepare`/插點A 呼叫 `self._get_system_context(self.db_pool)`；`app.py` 注入 `get_system_context` | `conversational_engine.py`, `app.py` | **改造點**（傳領域鍵） |

**關鍵觀察**：`synthesize(...)` 本來就同時吃 `grounding`（收斂檢索）與 `system_md`（系統脈絡）。所以「讓 LLM 有領域框架」有兩條路，見下方 R3。

## 二、逐需求落差與實作選項

### R1 母分類組織的領域 — 落差小（多為資料/慣例）
- 有：`category_config.parent_value`、`_grounding_by_category` 父層展開、診斷 `topic_scope.category` 已宣告領域。
- 缺：沒有明確「領域」實體把四件套綁一起；目前是慣例。
- **選項**：(a) 純慣例——以母分類值當領域鍵，四件套各自用既有欄位（target_user/category/topic_scope）對應，不建新表（**推薦**，零 schema）；(b) 建 `domain` 設定表顯式化（重、非必要）。

### R2 per-領域系統脈絡 — 主改造點
- 缺：`get_system_context` 無領域鍵、單槽快取、`系統脈絡` 列無領域標記。
- **選項（領域鍵）**：
  - **(a) target_user 鍵（推薦，最小驚訝）**：`系統脈絡` 列加 `target_user=[領域角色]`（合約=property_manager），`get_system_context(db_pool, role)` 查 `category='系統脈絡' AND target_user @> [role]`、**per-role 快取**——**與 `load_rules` 完全同構**。售前那份 target_user 設 prospect（或留 NULL 當預設）。
  - (b) 母分類鍵：`系統脈絡` 列用 categories/另欄標領域（注意 `系統脈絡` 是保留值不能進 `categories`，需另闢欄或關聯 → 較彆扭）。
  - (c) config 帶 `system_context_ref`：最彈性但最多接線。
- **接線改動**：`system_context.py`（簽名 + 快取改 dict）、`conversational_engine._get_system_context(db_pool, 領域鍵)` 呼叫點（prepare、插點A 兩處）、`app.py` 注入不變（fn 簽名擴充向後相容）、`ConversationalConfig` 提供領域鍵（persona_role/target_user 已有）。
- **回退**：查無領域脈絡 → 回既有預設/`MINIMAL_FALLBACK`（R2.3）。售前 target_user=prospect 續用原內容（R2.4）。

### R3 混合 grounding — **最大設計決策：與 R2 邊界**
- 現況：`_ground_by_api` 只回 API grounding；`synthesize` 卻已吃 `system_md`。
- **選項 A（基底架構走 system_md，推薦）**：合約基底架構＝合約領域 **系統脈絡**（R2 常駐注入）。則收斂時 `synthesize(grounding=API, system_md=合約架構)` **自動就是混合**——**R3 幾乎被 R2 吸收，`_ground_by_api` 零改**。優點：領域框架是常駐背景（每輪都在，符合「判斷」需常態），最省。缺點：system_md 每輪注入、內容需精簡（現有 MAX_CHARS_WARN 4500）。
- **選項 B（收斂時檢索 knowledge_ref）**：`grounding_scope` 加 `knowledge_ref:{select:category/ids,…}`，`_ground_by_api` 收斂時 `_grounding_by_category` 撈 + 併 API。優點：只在收斂時載、不佔每輪 token。缺點：追問輪 LLM 沒有領域框架（可能較不會引導）；要改 `_ground_by_api`/prepare。
- **選項 C（A+B 併用）**：精簡框架放 system_md（常駐），細節知識收斂時檢索。最完整、最貴。
- **待決**：這是本 spec 核心分歧，建議設計階段拍板（我傾向 **A**：符合前面對話「判斷框架該常駐」的共識，且改動最小）。

### R4 候選可辨識 — 自足、低風險
- 缺：候選 label 只 `title`；無區別欄位；無大 N 上限。
- **改動**：`result_mapping` 加 `label_fields:[...]`（多欄位，含日期格式化）；`_ground_by_api` 候選建構改讀 label_fields；加 `candidate_cap`，超過改「請補條件」（可回 ask 不列表）。全在 `_ground_by_api` + config，測試易。
- 注意：候選目前只存 `{id,label}`；若日後要「本地屬性反問收斂」需存更多欄位（本 spec 先做「帶資訊列出」即可，屬性反問列為後續）。

### R5 合約首案 — 依賴 R2/R3；知識草稿已備
- 有：`knowledge-contract-base.md`（已對齊真碼）。
- 缺：成為 `系統脈絡`（領域標記）列的資料；`bit_status` 逐位元解讀（R5.3）——需確認合成端或格式化端能逐位元（現 `jgb_response_formatter` 已能解，見真 API 驗證輸出）。
- **改動**：資料（種子）+ 依 R2 選項落領域鍵。

### R6/R7/R8 — 通用性/不回歸/驗證
- R6：全走設定/資料，與既有一致；靜態掃描守零硬編。
- R7：所有新能力**預設關閉即回退既有行為**（無領域脈絡→預設；無 knowledge_ref/label_fields→既有）。售前 target_user=prospect 續用原脈絡＝關鍵不回歸點。
- R8：擴充 `conversational-diagnosis` 既有 e2e 骨架；真 API role_id=20151 已證可打（本 session 實測 50 筆）。

## 三、整合點與風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| `get_system_context` 快取改 per-key 破壞既有全域快取行為 | 中 | 保留無鍵呼叫的向後相容（無鍵→預設/售前）；per-key dict 快取 |
| R2/R3 邊界選錯 → 重工 | 中 | 設計階段先定 A/B/C；建議 A |
| system_md 每輪注入變大（合約架構）→ token/延遲 | 中 | 精簡基底架構、守 MAX_CHARS_WARN；或選 B 收斂時載 |
| 售前系統脈絡誤被領域化改動影響 | 高 | target_user=prospect 專列 + 回歸測試；無鍵/無 prospect 標記時回原單例內容 |
| `系統脈絡`/`對話規則` 是保留分類（categories 不可含）| 低 | 領域鍵用 target_user（不動 categories），與既有約束相容 |

## 四、需研究／待決（設計階段）
1. **R2/R3 邊界**：基底架構走 system_md（A）還是 knowledge_ref（B）還是併用（C）。→ 影響 `_ground_by_api` 是否改。
2. **領域鍵**：target_user（推薦）vs 母分類 vs config ref。
3. **候選上限值**與「請補條件」措辭（R4.3）——落實作常數還是設定。
4. **售前系統脈絡如何標領域**：target_user=prospect 專列，還是 NULL 當全域預設（現況即 NULL/單列）。
5. `bit_status` 逐位元解讀由誰負責（格式化端已可；合成端是否需再加工）。

## 五、建議策略（供設計參考，非定案）
- **主線＝擴充**（不新建子系統）：R2 照 `load_rules` 模式把 `get_system_context` 參數化（target_user 鍵）；R3 採**選項 A**（基底架構＝領域 system_md，常駐注入，`_ground_by_api` 零改）；R4 於 `_ground_by_api` 加 `label_fields`+上限；R5 把合約基底架構落成 `系統脈絡`(property_manager) 種子。
- 如此本 spec 的引擎程式改動集中在 `system_context.py` + `conversational_engine` 兩處呼叫點 + `_ground_by_api` 候選建構，其餘皆資料/設定 → 通用性與不回歸都好守。

## 下一步
```bash
/kiro:spec-design domain-conversational-facets -y
```
