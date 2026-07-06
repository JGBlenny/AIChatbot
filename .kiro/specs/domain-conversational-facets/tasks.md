# 實作任務：domain-conversational-facets（領域化對話面向）

> 建立時間：2026-07-01
> 需求：requirements.md（R1–R8）｜設計：design.md（v1.1，含審查 3 修正）｜落差：gap-analysis.md｜研究：research.md
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後的測試覆蓋子任務
> 鐵律：TDD（先紅後綠）；通用性硬約束（程式不得出現合約/領域欄位字面硬編，一律讀設定）；售前不回歸
> 承接：`conversational-diagnosis`（select:api 三路、插點 A/B、分類路由、種子）之上

## 0. 可行性 spike（D3 預算閘，先做，決定 A/B）

- [x] 0.1 把合約基底架構（`knowledge-contract-base.md`）精簡到 append ≤ ~2500 字之版本，評估「base(1377) + append ≤ ~3900、且仍夠 LLM 判斷（12 階段/流轉/違約金滯納金/同名多份）」。壓得下→走選項 A（system_md 常駐）；壓不下→啟用 fallback 選項 B（knowledge_ref 收斂時載，影響任務 2.3）。產出精簡版文字 + 決策記錄。
  - 需求：3
  - ✅ 結果：append 精簡至 **1368 字**、疊加後 **2747 字**（≤3900 目標、餘裕 1753 到 4500 上限），判斷力要素全保留 → **走選項 A**，fallback B 未觸發。產出：`knowledge-contract-base.append.md` + `spike-0.1-decision.md`（詳見後者）。task 2.3 因走 A 不需實作。

## 1. per-領域系統脈絡（疊加載入）

- [x] 1.1 改 `services/system_context.py::get_system_context(db_pool, domain_key=None)`：疊加 base（`target_user IS NULL` 通用列）＋ 領域 append（`target_user @> [domain_key]`）串接；`_cache` 改 per-key（key＝domain_key 或 ""）；base 亦無→`MINIMAL_FALLBACK`。`reset_cache` 清全部。
  - 需求：2.1, 2.3
- [x] 1.2 引擎呼叫點傳領域鍵：`conversational_engine.py` 之 prepare 與插點A 兩處改 `self._get_system_context(self.db_pool, config.persona_role)`；`app.py` 注入的 fn 簽名向後相容（新增可選參數，不改注入）。
  - 需求：2.1, 2.2
- [x] 1.3 單元測試：領域 append 疊加於 base；無 domain_key / 無領域 append → 只回 base（售前不回歸）；per-key 快取隔離（不同領域取不到彼此）；reset 後重載；base 缺→fallback。
  - 需求：2.1, 2.2, 2.3, 2.4, 2.5, 7.1

## 2. 混合 grounding（走 system_md ＋ 現值為準）

- [x] 2.1 接線/驗證混合：收斂合成 `synthesize(grounding=API, system_md=base+領域架構)` 兩者皆入底稿；`_ground_by_api` 不改（元件2）。
  - 需求：3.1, 3.5
- [x] 2.2 對話規則 persona 加原則（資料）：「以 API 現值為準、領域架構僅供解讀、不得以通則覆寫該筆實際資料」。
  - 需求：3.2
- [~]* 2.3 （條件，僅 spike 判走 B 時）escape hatch：`grounding_scope.knowledge_ref` 於 `_ground_by_api` 收斂以既有 `_grounding_by_category`/`_grounding_by_ids` 撈併入 grounding；未設不改行為。
  - 需求：3.3, 3.4
  - ⏭️ **不實作**：spike 0.1 判走選項 A（system_md 常駐），fallback B 未觸發 → 本 escape hatch 非首案交付路徑（見 spike-0.1-decision.md 四）。
- [x] 2.4 單元測試：混合底稿含 system_md（mock synthesize 驗傳入 base+領域架構）；未設 knowledge_ref 走 system_md（向後相容）；若走 B 則 knowledge_ref 撈併入。
  - 需求：3.1, 3.2, 3.3, 3.4

## 3. 候選可辨識與分流 (P)

- [x] 3.1 (P) `_ground_by_api` 候選建構讀 `result_mapping.label_fields`（`label_date_fields` 者 Ymd→Y/m/d 格式化）以「｜」串帶區別標籤；無 `label_fields`→回退單 `label_field`。欄位一律讀 result_mapping（零硬編）。
  - 需求：4.1, 4.2
- [x] 3.2 (P) 大 N 分流：`N ≤ candidate_cap` → 列候選（帶區別欄位）存 pending_candidates 選序號；`N > cap` → 請補更明確識別重查；補不動（重查仍 > cap，同名多份）→ 截斷列前 cap 筆並提示「可給合約編號直接指定」。`candidate_cap` 未設＝不限。
  - 需求：4.3, 4.4
- [x] 3.3 (P) 單元測試：label_fields 組合 + 日期格式化；同名多份帶區別欄位可辨識；N≤cap 列候選、N>cap 請補條件、補不動截斷提示；未設 label_fields/cap → 回退既有行為。
  - 需求：4.1, 4.2, 4.3, 4.4, 7.5

## 4. 領域組織 ＋ 合約領域資料

- [x] 4.1 母分類組織驗證：診斷 config `topic_scope.category` 對應領域鍵（`persona_role`），據此載入對應系統脈絡與知識；不建新表（沿用 `category_config.parent_value` 慣例）。
  - 需求：1.1, 1.2, 1.3, 1.4
- [x] 4.2 合約系統脈絡種子：把 spike（0.1）精簡版落成 `category='系統脈絡'`、`target_user=[property_manager]` 之列（部署種子 SQL）；一般合約知識維持 `direct_answer` 不被領域化。
  - 需求：5.1, 5.2, 5.4
- [x] 4.3 單元測試：合約系統脈絡種子內容解析 + `get_system_context(db_pool,'property_manager')` 疊加得 base＋合約架構；`bit_status` 逐位元語義可由架構解讀（12 階段對照）；一般合約知識維持三出口。
  - 需求：5.1, 5.3, 5.4, 1.3

## 5. 通用性 ＋ 不回歸 ＋ 端到端

- [x] 5.1 通用性零硬編：以第二個「假領域」（mock）驗證僅加資料即得 per-領域脈絡疊加 + 候選 label_fields，無需改程式；靜態掃描新程式（system_context / _ground_by_api 候選建構）無合約/領域字面硬編。
  - 需求：6.1, 6.2, 6.3
- [x] 5.2 不回歸單元/整合：售前（prospect）只吃 base 脈絡、進入/追問/收斂不變；`conversational-diagnosis` 既有能力（select:api 三路、插點 A/B、分類路由）對外行為不變；無新設定→既有行為。
  - 需求：7.1, 7.2, 7.3, 7.4, 7.5
- [x] 5.3 e2e（容器內 TestClient + 真服務 + 真 jgb2 API，role_id=20151）：模糊→（多筆）帶區別候選→選擇→單筆→以合約架構**解讀**真實狀態（bit_status 逐位元）；候選過多→請補條件；一般合約知識→靜態知識（三出口）；售前不回歸。
  - 需求：5.3, 8.1, 8.2, 8.3, 8.4
  - ⚠️ e2e 測試已交付並 env-gated（`tests/e2e/conversational/test_domain_facets_e2e_req.py`，預設 skip）；離線全綠，**真環境實跑待部署**（套三種子＋清快取＋設 jgb2 API env / RUN_E2E=1）。

## 下一步
- 審核任務；通過後逐 Stage 實作（建議每任務間清 context）：
```bash
/kiro:spec-impl domain-conversational-facets 0.1
```
