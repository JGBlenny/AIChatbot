# 知識大綱架構定案（v2，2026-09-14；業主「照建議」裁 11 題＝DSP-047～057；⛔ 尚未實作，實作走 tasks §9）

> 配套 `jgb-domain-map.md` v2。本檔所有 [待裁] 已由 DSP-047～057 定案，下列每節標註對應 DSP。
> 🔴 v0 三處 [已定] 被推翻：§4 失敗方向「只會少給」（假：未知身分在 b2b 分支會**多給**）；§5「過濾在算分前所以永不並存」（非因果：互斥來自 `target_user` 集合不交）；§2「改粗目 top-5 不變」（同分時拆序用 `fine_id`，粗目字母在其中）。

## 0. 三個結論先講

1. **粗目對檢索分數零影響** [已定]，但**會改同分拆序**（`scored.sort(key=(-score, fine_id))`，prospect 現有 15 組同分）。
2. **架構今天真正同時「進得來＋查得到資料」的受眾只有 property_manager** [已定]：`AGENT_TURN_SPEC["stage"]` 無 tenant；`_jgb2_spec` stage 無 prospect ⇒ 售前一支資料工具都沒有。
3. **兩條 P0 與粗目無關、先做** [已定]：pm 68 條講法全 `proposed`（0 進索引）；prospect 15 組講法重掛（37/189，吃 K=5 名額）。

## 1. 四層 [已定；第 1 層＝九架正本 `canon/jgb/`（DSP-058）]

```
第 0 層  事實帳本   docs/knowledge/jgb-product-facts.md — 程式證明的事實，受眾中立
第 1 層  正本(git)  canon/*.md — 粗目＝領域骨架；細目＝一個命題＋屬性；講法＝真流量問法
第 2 層  每回合選取 resolve_vendor_business_types → visible_subset(身分過濾) → select K=5 → CandidateOutlineDoc → outline provenance
第 3 層  模型       只看到過濾完的 K 條＋平表目錄；看不到屬性
```
⚠️ **第 2 層有兩條路** [已定]：已註冊正本走 `resolve_canon_section`；**未註冊受眾（現況 tenant）走 `outline.build_toc` 的 DB 目錄，`citable=False`，⛔ 不受本架構管轄**。
規則住 `agent_rules.py`；工作清單 ⛔ 不在正本。

## 2. 粗目 [已定 DSP-047／048：9 個＝A 帳號與身分／B 團隊、人員與大房東／C 社區與物件／D 租約（委託約為子題）／E 帳務／F 修繕／G 裝置／H 幫助中心／I 方案與導入；售前漏斗併入 I]

A 帳號與身分／B 團隊、人員與大房東／C 社區與物件／D 租約（含委託約子題）／E 帳務（含發票、收款金流、抄表）／F 修繕／G 裝置／H 幫助中心／I 方案與導入。

- 粗目碼單一大寫字母 [已定]——由**三處 regex 各自釘住**：`canon_parser.FINE_ID_RE`、`.claude/hooks/outline_gate.py::FINE_ID_RE`（另有 `.agents/`、`.codex/` 複本）、`turn_context._CANDIDATE_ID_RE`（不合 ⇒ 整批 `candidate_ids` 被丟）。⛔ 不得只改其一。
- 粗目影響的四件事 [已定]：`fine.id` 中段、`canon_sha256`（⇒ `.json` 逐位元組重導出）、目錄與整份大綱章節序（⇒ `outline_sha`）、**同分拆序**。
- 委託約 ⛔ 不佔粗目（DSP-047）：external API 0 支、兩份正本 0 條、幫助中心 0 頁、只開法人房東 ⇒ 為 D 租約的子題。
- ⚠️ **無粗目可歸的現有內容** [已定]：pm `G/document-summary-rule`、`G/document-content-boundary`（agent 能力非領域）；prospect `C/notification-channels`（通知在 domain-map 降為屬性，但 §4 沒有通知軸）。**已定 DSP-049**：通知＝細目屬性；文件歸納移 `agent_rules.py`。
- **跨粗目命題** [已定]：幫助中心 92 頁有 14 頁跨兩粗目（租約↔帳務／物件↔租約／帳號↔租約）。`jgb-domain-map` §3 的三條分界線必須**凍結進正本的歸位規則**（步 2 可吃），否則會以「同題兩條細目」回來。

## 3. 細目 [已定]

- **一個細目＝一個可回答命題**；**一條講法只掛一個細目**。⚠️ **兩條鐵則目前都沒有執行者**：parser 只擋「細目 id 重複」，hook 只擋「講法撞凍結題」，⛔ 沒有跨細目重複講法檢查。P0-2 修完會長回來——要嘛在 `outline_gate` 加檢查，要嘛列已知債。
- 屬性分兩類：
  | 屬性 | runtime 讀？ | 誰讀 |
  |---|---|---|
  | `reviewed` | ✅ | `canon_visible` 第一行、`citable` |
  | `target_user`／`business_types` | ✅ | `canon_visible` |
  | `policy`／`policy_ref` | ⛔ **零** | 只有離線：`coverage_map`、`index_eval` 排除題。**寫 `policy: not_available` 不改模型任何行為**，效果只能來自內文 |
  | `instance_applicability` | ⛔ | 離線量尺 |
  | `see_also` | ⛔ | **無人驗證目標存在**（parser 對死 id 不報錯，正對照：細目 id 重複會 fail） |
  | `categories` | ⛔ | 無消費者 |
- 講法 `status: approved` 才進索引；⚠️ 未 approved 講法仍改 `canon_sha256`（涵蓋整份 `.md`）⇒ 把 pm 68 條翻成 approved 會同時觸發 `.json` 重導出與索引重建。
- 現況 77 條 `instance_applicability` **全 `general`、0 條 `instance`** ⇒ 「我的那一筆」型情境知識側一條槽都沒有，全靠 face。

## 4. 身分軸與失敗方向 [已定；值域擴充 DSP-053]

**過濾點** `canon_visible`：
```python
effective = _effective_target_user(identity.target_user)   # 未知值 ⇒ 'tenant'（fail-safe）
is_b2b   = (identity.target_user in B2B_TARGET_USERS) or (identity.mode == "b2b")   # 讀原值
```
**兩行不對齊 ⇒ 未知身分＋b2b 入口 ⇒ 走 b2b 嚴格分支、拿 `tenant` 鑰匙比對 ⇒ 看到租客向細目（多給，靜默）。** 今天沒炸只因 77 條全是 `[prospect]`／`[property_manager]`、且 A 案有 runtime 受眾閘（`_select_outline` 的 `audience != resolved_audience() ⇒ 不做候選`）。B 案拿掉那道閘就是外洩。

失敗方向（完整版）：
| 情況 | 結果 | 可觀測 |
|---|---|---|
| 身分可見集合為空 | `none_visible` ⇒ 零內容 | trace 有值，但不說**為什麼**空 |
| 正本側 `target_user` 拼錯／用了未知值（`social_housing`、`big_landlord`） | **parser 不報錯**，細目對所有身分永遠不可見、仍進索引算錢 | ⛔ 無 log |
| 未知身分＋b2b | **多給**租客向細目 | ⛔ 無 log |
| `all_users` | 只在 b2c 分支放行，b2b 看不到 ⇒ 半可見 | ⛔ 無 |
| 任何離題問題 | K=5 無門檻 ⇒ 永遠 `hit` 滿 5 條（「今天天氣」對售前正本最高分 0.282 照回 5 條） | 分數在 trace |

**值域現況**：`KNOWN_TARGET_USERS` 5 值 `{tenant, landlord, property_manager, system_admin, prospect}`。
- 缺：**大房東**、**社宅**、**團隊成員權限**（後者不是 `target_user` 能表達的——`canon_visible` 沒有權限維度，看不到財務的成員照樣拿到全部帳務細目）。
- ⚠️ **`system_admin` 已在值域、被路由進 pm 受眾、但 pm 正本 0/39 可見**（front matter 繼承 `[property_manager]`）。
- 大房東雙身分：`Identity.target_user` 純量、`canon_visible` 單值∈集合，**沒有第二維度**；且 `audience_of(mode='b2b', 'big_landlord')` 仍回 pm。擴值域單獨做不到，要連動 `Audience` Literal、`CANON_AUDIENCES`／`INDEX_AUDIENCES`、`_STATIC_TOC_IDENTITY`、`app._AGENT_OUTLINE_AUDIENCES`、各工具 `stage`。
- **前置必做**：`canon_parser` 加 `target_user` 值域檢查（比照 `policy` 的 enum 檢查），否則擴軸過程每個錯字都是靜默死亡。

**已定 DSP-053**：加大房東、社宅（身分軸一個值）、`system_admin` 補洞；團隊成員權限 ⛔ 不做第四軸（交 jgb2 `character.php`／API 收口）；前置＝`canon_parser` 值域檢查、⛔ 不只綁 `traffic:`。

## 5. 同一命題、多受眾 [已定：允許；⛔ 理由改寫]

同粗目下同題細目各受眾一條（不同 id、不同內容、講法可同文）。**它們互斥的原因是 `target_user` 集合彼此不交**（`[tenant]` vs `[property_manager]`），⛔ 不是「過濾在算分前」——過濾在算分前只保證不可見的不進池，不保證可見的不並列。
**規則**：一個命題要嘛一條中立細目 `target_user: []`，要嘛每受眾各一條；⛔ 不得並存；⛔ 不得用 `all_users` 表示中立（b2b 看不到）。並存＝該受眾同時看到兩條、同分 1.0、誰在前由 slug 字典序決定。⚠️ **零閘門**——同 §3。

## 6. 受眾模型 [已定 DSP-058（2026-09-15）：九架正本一份，受眾＝細目必填屬性 `target_user`]

一份正本 `rag-orchestrator/canon/jgb/A.md…I.md`＋衍生目錄 `CATALOG.md`；每條細目 `target_user`／`business_types` 必填非空、id 前綴 `jgb/`；各身分看到的是同一份正本依 `canon_visible` 篩出的細目集合，不是各自一份檔。計畫與切片：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.6-library-canon-20260915.md`。

## 7. 租客 [已定 DSP-054：先不開]

`AGENT_TURN_SPEC["stage"]` 無 tenant ⇒ 六支 `jgb2.query.*` 對 tenant 開 M0 **卻永遠到不了**。開線需：stage 鍵、`_STATIC_TOC_IDENTITY`、`_AGENT_OUTLINE_AUDIENCES`、正本（粗目切法可能依生命週期）、front matter `business_types` ⛔ 不得沿用 `[system_provider]`（實測 0/N）。

## 8. 資料側 [已定]

- external/v1 27 支：**活鏈 11 支**；16 支 0 呼叫點（其中 5 支只在已退役的 `responsibility_*` 鏈）。
- **`發票` face 有 builder，`get_invoices` 非測試呼叫 0** ⇒ 模型可選「發票」，`query_bills` 卻拿帳單列餵發票 builder（正對照：`登入排障` 已用 `_invalid_input()` 擋）。
- **六域全部單列**（`builder(rows[0])`、多列回候選清單截 5）⇒ 加總／計數／排序**沒有路**。pm 正本粗目 C「今天要顧的追問」整條是彙總題。要補的是 `jgb2.query.*` 的 aggregate 形態，不是加 face。
- 委託約／總收支／統計報表／清冊／大房東報表／簽核：external API **0 支**。
- 🔴 **爭議交裁**：`jgb_system_api.agent_patch_bill_due_date` 打 `PATCH /agent/v1/bills/{id}`，dev2 preview 與 master 的 `routes/api.php` **都沒有這條路由**（正對照：agent/v1 有 `GET /bills`、`GET /bills/{id}`）⇒ `bill_due_extend` 寫入工具只能對替身生效。

## 9. 遷移 [已定；順序 DSP-057：P0 與重切一起做]

改粗目／細目 id 連動：
1. `canon_sha256` ⇒ `.json` 逐位元組重導出（忘了＝啟動紅）⇒ 索引重建
2. **`coarses-<audience>.json`**（步 2 封閉 enum；`.claude/`、`.agents/`、`.codex/` 三份）先改，否則 9 領域提議 exit 2；pm 那份還缺 G
3. **`outline_gate.py` hook**：每寫一次正本要重產 diff report 且 `inputs_sha.canon` 相符；⛔ 不繞過
4. 三份 `FINE_ID_RE`＋`_CANDIDATE_ID_RE`（若碼形狀變）
5. **`see_also`** 隨 id-map 改寫（無檢查會抓死連結）
6. 寫死 `fine.id` 的測試、fixture
7. **凍結驗收材料**：`index-eval-20260907.json`(432 處)、`coverage-map(-v3)`(169/144)、`phrasing-map`(1020)、gold、`id-map`；`coverage_map.py` 對「fine_id 不在正本」fail-loud exit 2。⚠️ 基線在重切後**跑不動**，且改名後才重建 gold＝看過結果再動 holdout ⇒ **先用 id-map 重映舊 gold，重映不成立的格（合併／拆分）必須重判**
8. **DB 衍生列 `generation_metadata.canon_ref`＋不變量 33**：今天 0 列 `SKIP(pending-D1)`；D1 之後改名不重匯 ⇒ `make audit` 硬紅
9. 不變量 34：改講法後必跑；新講法 ⛔ 不得取自凍結題集
10. 已落地 trace 的 `candidate_ids` 對不回正本（回溯分析靜默失效）

P0（先做、與粗目無關）：pm 68 講法人審 `approved`；prospect 15 組重掛講法各歸一處。

## 10. 驗收 [已定：先定再改；材料重映見 §9-7]

`index_eval.py` r@5 基線與下限；步 4 可答性雙判者；步 5 覆蓋圖；情境回測一輪。

## 11. 裁決對照（2026-09-14「照建議」）

| # | 題 | 裁決 |
|---|---|---|
| 1 | 售前漏斗粗目並列 vs 併入「方案與導入」 | DSP-048 併入 I 方案與導入 |
| 2 | 委託約要不要佔一格（現況空頭） | DSP-047 不佔格，租約子題 |
| 3 | 通知／文件歸納：第 10 粗目 vs 新橫切軸 | DSP-049 通知＝屬性；文件歸納→agent_rules |
| 4 | pm F 十條：移出／撤 reviewed／維持 | DSP-050 移出正本 |
| 5 | pm D／E 六條規則：搬 `agent_rules`（+524 字撞 DSP-028）／留 | DSP-051 搬 agent_rules |
| 6 | 受眾模型 | DSP-058（2026-09-15）：九架正本一份、受眾＝細目屬性 `target_user` |
| 7 | 身分值域：加大房東／社宅／system_admin 補洞；團隊成員權限第四軸？ | DSP-053 加大房東／社宅／system_admin 補洞；權限不做第四軸 |
| 8 | 租客線開不開 | DSP-054 先不開 |
| 9 | 資料側 aggregate 形態要不要立案 | DSP-055 立案排後 |
| 10 | `PATCH /agent/v1/bills` 路由爭議 | DSP-056 交 jgb2 確認 |
| 11 | P0 先做 vs 與粗目一起遷 | DSP-057 一起遷 |
