# Plan 9.10：正本改三層＋由 drafts 生成新正本（DSP-067 程式面）— 2026-09-21 立案，第 3 稿（2026-09-23）

> 稿次：第 4 稿。狀態（2026-09-23 收工）：業主 2026-09-21「核可」「開」。**S1／S2／S3／S4／S6 已實作並各經 fresh verifier CONFIRMED**（新正本 `canon_sha256 = 9b67e763…`），S3a 已撤案；**S5 已於 2026-09-24 實作並經 fresh verifier CONFIRMED（首驗 REFUTED 1 條 F1 已修）**；S6 另有真回合驗收未跑（受測物已改為新正本全審暫存副本，需支出授權）。各片現況見 §3 與 `../HANDOFF-20260923.md`。第 1 稿經 plan-verifier 七條 blocker 全 FIX（無 DEFER／REJECT），處置表見 §6。
> 前置：DSP-067 骨架定案、九架 drafts 每架 verifier CONFIRMED（57 粗目／515 細目／1,327 句／81 待裁）。

## 0. 目標與非目標

**目標**：讓 `rag-orchestrator/canon/jgb/` 承載「架 → 粗目 → 細目」三層，並用腳本把 `runs/outline-20260920/drafts-*.json` 決定性生成為新正本，取代現行 210 條。

**非目標（⛔ 本 Plan 不做）**：業主裁 81 題（可平行；裁完重跑 S3 即可）；審核（DSP-066，生成後另批）；部署與 DB 寫入（業主）；`build_toc`（pm／tenant 的 DB 目錄，另案）；租客線；療效回測（S4 之後，支出由業主定）。

## 1. 量測（先量再決定，非事後解釋）

以 drafts 實算（1.1 字元/token 近似，`reference_canon_token_ratio`；⚠️ 近似值只用來**排除明顯不可行的選項**，真值由 S4 以 `_count_tokens` 真 tokenizer 覆量，見 §3 S4）：

| 量 | 近似值 | 上限 | 判定 |
|---|---|---|---|
| 目錄＝515 細目平鋪 | 37,680〜37,681 近似／**38,015 真值** | 8,000 | ❌ 4.8 倍，任何 tokenizer 誤差都救不回來 |
| 目錄＝57 粗目 | 2,005 近似／**2,079 真值** | 8,000 | ✅ 26%，餘裕 3.8 倍（2026-09-23 重算；原寫 1,807 不可重算，已更正） |
| 最大粗目的細目清單（E「帳單列表與帳單狀態」24 條） | 1,707 tokens | — | ✅ |
| K=5 上界（最長 5 條細目和） | 2,097 近似／**3,109 真值**（節組法 3,671）——**皆為 drafts 側**；S4 對生成後的 canon 側覆量為 **3,108／3,670**，差 1 來自 DSP-068 在 `jgb/F/repair-edit-application-detail-readonly` 刪去的那個字元 | 12,000 | ✅ 26–31%，餘裕 3.3 倍 |

⇒ 目錄**必須**改列粗目（DSP-067 已裁的方向，此處是量化理由）。`OUTLINE_K_TOKEN_LIMIT`（12,000）與 `OUTLINE_TOC_TOKEN_LIMIT`（8,000）**兩張常數表都不改**；依真值餘裕 3.3 倍以上（目錄 3.8、K 上界 3.3），近似誤差（實測歷史約 ±10%）不可能翻轉結論。⛔ 原訂「預算重量」一項取消。**若 S4 真值量出任一項超過上限 ⇒ 停止，不得自行調高常數表**（env 只能調小，調高要業主裁）。

## 2. 形態決定

| 候選 | 作法 | 否決理由 |
|---|---|---|
| A. 加一層標題 | `##` 架／`###` 粗目／`####` 細目 | 動到 `FINE_HEADING_RE`、細目 id 形狀、兩份閘門 hook、CATALOG 導出；改動面最大 |
| B. 粗目當細目屬性 | 細目加 `- coarse_title:` | 粗目不成結構、無法排序、parser 無從驗「粗目齊了沒」 |
| **C. 一架多粗目（採用）** | 架檔內多個 `## 粗目標題 {#A-slug}`，細目 `###` 不動 | `_parse_body` 本就是多粗目狀態機；細目 id、屬性區塊、hook 的 `FINE_HEADING_RE`／`ATTR_LINE_RE` 不動 |

⚠️ **候選 C 仍會動到閘門 hook 的粗目規則**（第 1 稿誤寫成「hook 全不動」）：`.claude/hooks/outline_gate.py` 的 `COARSE_HEADING_RE` 同樣只認單一大寫字母，且 `check_structure` 硬性要求「架須恰一個粗目」——不同步放寬，新形狀架檔一寫下去就被 PostToolUse exit 2 擋掉，S3／S4 無法執行。該 hook 有 `.codex/` 鏡像（現為逐位元相同），兩份都要改。

**採用的形狀**（A.md 為例）：

```
---
coarse: A            ← 架字母（front matter 六鍵不變）
title: 帳號與身分      ← 架標題：新形態下的唯一來源
scope: …
---
## 註冊帳號 {#A-account-registration}          ← 粗目（新）
### 怎麼用 Email 註冊 {#jgb/A/email-register}   ← 細目（層級、id、屬性全不變）
- phrasings: …
內容句…
## 登入 {#A-login}                              ← 同架第二個粗目
```

**單一粗目正則（同時容納新舊，⛔ 不分兩條）**：

```python
COARSE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*\{#([A-Z](?:-[a-z0-9-]+)?)\}\s*$")
```

裸字母 `{#A}` 是**過渡鷹架**（業主 2026-09-21：「新格式一通 舊格式就需要清除棄用」）：它只為了讓現行 210 條在 S1–S4 期間仍能解析、當 S1 的正對照組，⛔ 不是新正本的寫法，**S5 移除**。新正本一律 `<架字母>-<slug>`；粗目 id 全域唯一、首字母＝所在架字母。

## 3. 片

### S1 parser 與閘門放行架下多粗目
**擁有檔案（獨占）**：`rag-orchestrator/services/agent/canon/canon_parser.py`、`rag-orchestrator/tests/unit/agent/test_canon_parser_req.py`、`rag-orchestrator/tests/unit/agent/test_canon_export_sync_req.py`、`rag-orchestrator/tests/fixtures/canon_jgb/expected.json`、`rag-orchestrator/canon/jgb.json`、`.claude/hooks/outline_gate.py`、`.codex/hooks/outline_gate.py`、`rag-orchestrator/tests/unit/_meta/test_outline_gate_req.py`。⛔ 不碰 `canon/jgb/*.md`（S3 才動）、⛔ 不碰他線未提交檔（`services/agent/agent_rules.py`、`runtime.py`、`outline.py`——三檔皆 ` M`；⚠️ `scripts/review_coverage.py` 已追蹤且乾淨，先前列它是錯的）。

**改動**：
1. `COARSE_HEADING_RE` 換成 §2 的單一正則。
2. `parse_canon_dir`：移除「恰一個粗目」與「粗目碼＝檔名字母」；改為 ①≥1 個粗目 ②每個粗目 id 首字母＝檔名字母 ③粗目 id 跨架唯一。
3. **架標題來源**：新增 `CanonDoc.shelf_titles: tuple[tuple[str, str], ...]`（架字母, front matter `title`），與 `scopes` 同款只在目錄路徑有值。⛔ 不改 `scopes` 形狀（`dict(doc.scopes)` 有兩個 skill 腳本消費者 `apply_proposal.py`、`canon_to_library.py`）。`to_dict` 對 `shelf_titles` 比照 `scopes`／`name`（單檔路徑 pop、目錄路徑保留）⇒ **目錄路徑導出位元組會變**，故 `canon/jgb.json` 與 golden fixture `expected.json` 由本片一併重產並列入驗收。
4. **fm-title 守門的去留**：舊形態（架內恰一個裸字母粗目）**保留**現行相等檢查逐字不變；新形態（出現任一 `<字母>-<slug>` 粗目）下架內沒有與架同名的 `##`，該檢查不適用 ⇒ 由新不變量 ②③ 取代（架標題唯一來源＝front matter `title`，無第二處可矛盾）。
5. **細目 id 中段規則**：`_parse_body` 新增選填參數 `shelf_letter: Optional[str] = None`。`None`（單檔路徑 `parse_canon_text`）⇒ 行為與訊息**逐字不變**（仍比 `current_coarse[0]`）；目錄路徑傳入架字母 ⇒ 改比架字母，訊息另寫一句（⛔ 不改動單檔那句，既有回歸測試釘它）。
6. 兩份 `outline_gate.py`：`COARSE_HEADING_RE` 同值放寬；`check_structure` 的「架須恰一個粗目」改為與 parser 同值的三條不變量；改完 `cmp` 兩份鏡像必須仍逐位元相同。

**驗收（每條可被外部證偽）**：
- 正對照組：`parse_canon_dir("rag-orchestrator/canon/jgb")` 對**現行 210 條**成功，且 `load_canon_or_die` 三源逐位元比對通過（重產 `jgb.json` 後）。
- 新形狀：一份多粗目 `A.md` fixture 解析成功，粗目數＝2、細目歸位正確。
- 負對照 5 條：粗目 id 首字母≠架字母、粗目 id 跨架重複、零粗目、細目 id 中段≠架字母（`{#jgb/B/...}` 寫在 A.md）、粗目 id 大小寫或 slug 不合法。
- 單檔路徑：`test_canon_parser_req` 既有訊息斷言**未改一字**全綠。
- 閘門：多粗目 `A.md` 跑 `check_structure(path, "A")` 回空清單；`test_outline_gate_req` 全綠（既有「恰一個粗目」案例改寫為新不變量）；`cmp .claude/hooks/outline_gate.py .codex/hooks/outline_gate.py` 相同。
- `test_canon_export_sync_req` 三條位元組比對全綠。

**停止條件**：現行 210 條在新 parser 下解析失敗、或三源比對失敗、或單檔路徑任一既有訊息斷言需要改動 ⇒ **停，不推進 S2**，交業主。
**預算**：一個工作段落；fix/reverify 最多 3 輪，第 3 輪仍紅 ⇒ `PAUSED_VERIFICATION`。
**執行**：`executor`（非 security-sensitive：不碰認證、憑證、可見性謂詞）＋fresh `verifier`。

### S2 目錄改列粗目（第 2 稿：plan-verifier 片級審查五條全 FIX）
**擁有檔案（獨占）**：`canon_assembler.py`、`canon_parser.py::export_catalog`、`tests/unit/agent/test_canon_assembler_req.py`、`tests/unit/agent/test_canon_export_sync_req.py`、**`tests/unit/agent/test_outline_unit_req.py`**、**`tests/unit/agent/test_library_view_req.py`**、**`tests/integration/agent/test_canon_startup_req.py`**、**`tests/unit/agent/test_candidate_outline_req.py`**（後四者以細目 id／細目標題釘住舊目錄行，目錄一改必紅；⚠️ `test_candidate_outline_req.py` 的落選細目標題斷言是同檔「內文不得外洩」負對照的**量尺自證**，⛔ 不得直接刪除，須改寫成「落選細目所屬的粗目行出現在 system prompt」）。⛔ 不碰 `canon/jgb/*.md`、⛔ 不碰 `agent_rules.py`（他線未提交，見下方前置）。

**改動**：
1. `build_canon_toc`：每個「含 ≥1 條可見已審細目」的粗目一行 `<粗目 id>｜<粗目標題>｜<可見細目數>`，⛔ 不列細目。
2. `resolve_canon_section` 新增粗目導航分支，判別順序寫死三句：**先比細目 id（`FINE_ID_RE` 形狀）、再比粗目 id、其餘 `NO_MATCH`**（兩種 id 形狀互斥，不會碰撞）；**粗目存在但零可見已審細目 ⇒ `NO_MATCH`**，與「不存在」逐欄位相同，⛔ 不回空清單（沿 `_no_match` 的「不對模型區分」設計）；過渡期裸字母粗目（`outline:A`）**放行**，與 `<架>-<slug>` 同一條路徑。回傳為該粗目可見已審細目的 `<細目 id>｜<標題>` 清單，`citable=False`。
3. `export_catalog` 改為**逐粗目判別**（⛔ 不以「架內粗目數 > 1」分流——一架只有一個帶 slug 粗目是 S3 必然會產生的情形）：
   - `coarse.id` 為**裸字母** ⇒ 沿用今日整段輸出（`## <id> <title> {#<id>}` ＋ `scope:` ＋細目行），保證現行 210 條逐位元不變。
   - `coarse.id` 為 `<架字母>-<slug>` ⇒ 以 `coarse.id[0]` 取 `shelf_titles`／`scopes`：該架**第一次出現**時先出架層兩行（`## <架字母> <架標題> {#<架字母>}`、`scope: …`），之後每個粗目出一行 `### <粗目 id> <粗目標題> {#<粗目 id>}`，再接該粗目的細目行。
   - **空行規則**：架與架之間一個空行；**同架的粗目之間不插空行**。
   - **查無鍵 ⇒ raise，訊息帶架字母與粗目 id，⛔ 不得回退空字串或省略該行**（現行 `.get(key, "")` 會把空 scope 靜默寫進被位元組比對的衍生物，而比對的是自己的導出，永遠測不出來）。

**CATALOG 新舊兩形態的逐行字面（寫死，S3／S4 直接消費）**

舊形態（現行 210 條，架內恰一個裸字母粗目）⇒ **與今日逐位元相同，⛔ 不插粗目行**：
```
## A 帳號與身分 {#A}
scope: 註冊、登入、找回帳號…
jgb/A/account-registration｜怎麼註冊帳號…｜target_user=property_manager,prospect｜怎麼開帳號／…
```
新形態（架內多粗目）⇒ 架層行取自 `shelf_titles`／`scopes`，每個粗目插一行 `### <粗目 id> <粗目標題> {#<粗目 id>}`：
```
## A 帳號與身分 {#A}
scope: 註冊、登入、找回帳號…
### A-account-registration 註冊帳號 {#A-account-registration}
jgb/A/email-register｜怎麼用 Email 註冊｜target_user=property_manager,prospect｜怎麼開帳號／…
### A-login 登入 {#A-login}
jgb/A/password-reset｜…
```

**⚠️ 阻斷性前置（P1，⛔ S2 落地後在補上之前不得進產線）**：提示詞規則 `services/agent/agent_rules.py` 現寫「id 形狀為 `outline:` 加上目錄那一行的章節 id」——目錄改列粗目後，模型會拿粗目 id 當可引用章節去 `kb.get`，拿到 `citable=False` 的導航清單，走進 `SOURCE_NOT_CITABLE → budget_exhausted`。規則要改成**兩跳導航**：目錄行是粗目、先 `kb.get("outline:<粗目 id>")` 取細目清單、再 `kb.get("outline:<細目 id>")` 引用。⚠️ 該檔是**他線未提交檔**（工作樹 `M agent_rules.py`），依「別的視窗的檔只交裁決不落檔」⛔ 本片不動它 ⇒ **交業主裁定由誰在哪一片改**。⚠️ 此前置對**現行 210 條同樣生效**（S2 一落地，舊正本的目錄就從細目行變成 9 行粗目），⛔ 不是等 S3 才發生。

**驗收（含負對照）**：
- 目錄行數＝可見粗目數；行格式三欄；⛔ 目錄內不得出現任何細目 id（負對照）。
- 粗目導航回正確細目清單；**「存在但全未審的粗目」與「不存在的粗目」兩者回傳逐欄位相同**（負對照，證明不洩漏差異）。
- 未審細目與他受眾細目的 id 與標題皆不出現在目錄或導航清單（負對照）。
- 六處舊斷言（`test_outline_unit_req.py` 兩處、`test_library_view_req.py`、`test_canon_startup_req.py`、`test_candidate_outline_req.py` 兩處）改寫為等價的新斷言，各自同時含正對照與負對照；`test_candidate_outline_req.py` 改寫後，落選細目**內文**與 pm-only 細目的負對照必須仍在，且正對照在「目錄改回列細目」或「粗目行消失」時會紅（量尺自證）。
- CATALOG 三組比對：①**單一帶 slug 粗目**的架 fixture 逐行等於寫死字面（架層兩行＋一行 `###`）且不拋例外；②多架多粗目 fixture 的跨架空行逐位元符合；③現行 210 條位元組比對仍綠（`test_canon_export_sync_req::test_versioned_catalog_is_byte_identical_to_export`）。①②須含 mutation 檢查：故意改動粗目行任一欄位即紅。
- `scopes`／`shelf_titles` 缺該架的 `CanonDoc` ⇒ `export_catalog` 丟出點名該架的例外（負對照）。
- 容器內全測試套件綠（既有 9 條他線紅燈除外，須逐條與 S1 驗證報告對齊，數量不得增加）。

**停止條件**：現行 210 條的 CATALOG 位元組比對無法在不改舊形態輸出的前提下通過 ⇒ 停；或全測試套件紅燈數超過 9 條（S1 驗證報告逐條列名的既有紅燈）⇒ 停。
**預算**：一個工作段落；fix/re-run 最多 3 輪。
**執行**：`executor`＋fresh `verifier`（agent 路徑契約變更）。

### S3a 斷句器改成不在引號內斷句 — ❌ **已撤案（業主 2026-09-23「照建議」）**

**為什麼撤**：drafts 有 27 行在 `split_sentences` 下切成 ≥2 段，其中 23 行的終止符落在成對 `「」`／`『』`／`（）` 內（UI 標籤本身含 `？！。`）。原提案是讓斷句器在引號內不斷句，但**已證它會讓引用驗證變鬆**——`verifier` 的覆蓋率門檻只由模型給的片段決定，來源單位變長即單調變寬；`QUOTE_TOO_SHORT` 比的也是來源單位長度。那是失敗方向為放行的一側，且影響面不只正本，任何含引號的 KB 文字都一樣。

**改採（DSP-068，業主 2026-09-23）**：**寫進正本時省略標籤句末標點，標籤主體逐字不變**。21 行的標點剛好落在標籤結尾（「忘記密碼？」→「忘記密碼」），2 行在標籤中間改寫成兩段引號（兩段仍逐字）。⛔ 不動 `provenance_units.split_sentences`、⛔ 不動引用驗證路徑。

### S3 生成腳本（新檔 `.claude/skills/outline-curation/scripts/drafts_to_canon.py`）
**前置**：S1、S2 已落地並驗過；**S3a 已撤案**，改走 DSP-068 標點例外（見上片）。
**擁有檔案（獨占）**：該新檔、其測試、`rag-orchestrator/canon/jgb/`（九架＋`CATALOG.md`）、**`rag-orchestrator/canon/jgb.json`**（S1 對此檔的獨占權在 S1 完成時結束）、`docs/archive/2026-09/canon-pre-dsp067/`、**`.claude/skills/outline-curation/runs/outline-20260920/drafts-A.json` 與 `drafts-C.json`**（只為改那 2 條標籤中間含終止符的細目，⛔ 不得改其他任何細目）；`inputs/coarse-ids-20260921.md`、`inputs/dsp-068-punctuation-lines-20260923.md`（只讀）。

⛔⛔ **本片已於 2026-09-23 執行完畢並驗過。重跑前必讀**：封存步驟會把**現行** `canon/jgb/*` 複製到 `docs/archive/2026-09/canon-pre-dsp067/`——現行已經是新正本，直接重跑會**用新正本蓋掉舊 210 條**，而新舊兩份**都未進 git、無從還原**（`git ls-files rag-orchestrator/canon` 只回 `README.md`）。要重跑必須先把 `canon-pre-dsp067/` 移到別處，或改用 `--archive-dir` 指向新路徑。

**步驟 0（手改，生成前）**：由 executor 先改 `drafts-A.json` 的 `jgb/A/login-no-account-register-link`#0 與 `drafts-C.json` 的 `jgb/C/forcebinding-completion-states`#0，**拆後字面寫死在** `inputs/dsp-068-punctuation-lines-20260923.md` §步驟 0，逐字照抄；改完 `git diff` 只該有這兩處。⛔ 不由腳本代改。⚠️ 拆後那兩段引號會**各新增一個可刪標點** ⇒ 生成時的預期刪除清單是 **23 行／27 個字元**（非步驟 0 前的 21／25）。

**映射（每一項都要有來源，⛔ 不得自造值；任一項缺 ⇒ 停）**：
| 正本欄位 | 來源 | 缺值時 |
|---|---|---|
| 架 front matter `coarse`／`title`／`scope`／`reviewers`／`language` | **逐字沿用現行 `canon/jgb/<X>.md` 的 front matter**（九架皆有，`reviewers: [owner]`、`language: zh-TW`） | 停 |
| 架 front matter `version` | 字面 `2026-09-21.0`（九架相同） | — |
| 粗目 id | **查 `inputs/coarse-ids-20260921.md` 凍結表**（標題去 `⇄ …` 後綴後逐字比對；57 列已自檢：id 唯一、首字母符架、drafts 57 個粗目查表零落空） | 停（⛔ 不自行造 slug） |
| 粗目標題 | drafts `coarse`（去 `⇄ …` 後綴） | — |
| 細目 id／標題 | `proposed_id`／`title`（515 條已驗全部符合 `^jgb/[A-I]/[a-z0-9-]+$`） | 停 |
| 內容行 | `sentences` 逐句過 `split_sentences`；**切出多句者一句一行**。標點例外（DSP-068）：**僅細目內容行**——成對 `「」`／`『』`／`（）` 內、且緊接右括號前的終止符，寫入正本時**刪去**（標籤主體逐字不變）。⛔ 標題、`phrasings`、屬性行**一字不動**（標題裡的「忘記密碼？」照留）。適用行＝凍結清單 `inputs/dsp-068-punctuation-lines-20260923.md`（**步驟 0 後 23 行／27 個字元**；該檔另列步驟 0 前的 21／25 供對照）；**實算與清單不符即停**；刪後若仍切出多句 ⇒ 大聲失敗 | 停 |
| 標籤中間含終止符的 2 行 | `jgb/A/login-no-account-register-link`#0、`jgb/C/forcebinding-completion-states`#0 ⇒ **先改 drafts 本身**（拆成兩段引號，兩段逐字），⛔ 不由腳本代改 | 停 |
| `phrasings` | 每則寫 `- {text: "<原文>", source: "draft:outline-20260920", status: proposed}`；**1,670** 則皆為純字串、**零則含 `"`／`{`／`}`**（已驗；原 1,674，業主 2026-09-23 裁定刪去 4 則跨細目重複，紀錄見 `inputs/phrasing-dedup-20260923.md`），出現即停 | 停 |
| `sources`／`target_user`／`business_types`／`instance_applicability` | 照搬（515 條皆非空、`business_types` 皆 `[system_provider]`、`target_user` 皆在值域內，已驗） | 停 |
| `reviewed` | **一律不寫**（DSP-066：未審 ⇒ 模型不可見） | — |
| `open_questions` | 另出 `runs/outline-20260920/open-questions-20260923.md`，⛔ 不進正本 | — |

**句子對應的重新定義**：一條 draft `sentences[i]` 可能落成正本的**連續多行**；驗收＝「每條 draft 句子對應正本一段連續行，串接後與 draft 原句逐字相等，**唯一允許的差異是 DSP-068 明列的刪除**」。腳本必須輸出 `runs/outline-20260920/dsp-068-deletions-<日>.json`（每筆：細目 id、句索引、被刪字元位移、被刪字元），供 verifier 逐條回填比對；回填後仍不逐字相等 ⇒ 判紅。`evidence[].sentence_index` 仍指向 drafts，不受影響。

**產出順序**：生成九架 `.md` → `parse_canon_dir` → `export_json` 出 `canon/jgb.json` → `export_catalog` 出 `canon/jgb/CATALOG.md` → `load_canon_or_die` 三源比對。⛔ 不自己組 JSON／CATALOG。腳本比照 `apply_proposal.py` 的 `sys.path` 插入與 `/app` 後備，**容器內執行**（`canon_parser` 透過 `_target_user_universe()` 間接相依 psycopg2）。

**封存**：先把現行 `canon/jgb/*.md`＋`CATALOG.md`＋`canon/jgb.json` **複製**到 `docs/archive/2026-09/canon-pre-dsp067/`（⛔ 不移動、⛔ 不刪），確認複本可 `parse_canon_dir` 後才覆寫。

**驗收**：
- `--self-test` 正對照 6／**負對照 3（指定）**：①標籤結尾終止符被刪後落成一行、且刪的只有那一個字元（證 DSP-068 例外生效且未多刪）；②粗目標題查表落空 ⇒ 大聲失敗且訊息印出該標題；③講法含 `"` ⇒ 大聲失敗。
- **標點例外的驗收（新增，單向比對）**：對每個 DSP-068 適用行，「生成的內容行 ＋ 回填刪除清單記載的字元」必須與 drafts 原句**逐字相同**；刪除清單恰 **23 行／27 個字元**（步驟 0 後）、每筆位移都落在成對引號內且下一字為右括號。**標題行與 `phrasings` 子項與 drafts 逐位元相等**（含標題裡的 `？`）。mutation：故意多刪一個引號外的句號、或刪一個標題裡的 `？` ⇒ 皆須紅。
- **引號平衡（無條件大聲失敗）**：生成的任一內容行若 `「」`／`『』`／`（）` 不成對 ⇒ 中止並印出細目 id 與該行。**在步驟 0 未做的狀態下跑生成，必須以非 0 結束並點名那 2 條細目**（負對照）。
- 連跑兩次逐位元相同。
- 生成物過 `parse_canon_dir`＋`load_canon_or_die`（三源位元組）。
- 抽 30 條細目回 drafts：標題、屬性逐欄相符，內容依上面的「連續行串接相等」規則相符（fresh verifier 自行抽樣，⛔ 不用腳本自報）。
- 57 個粗目 id 與凍結表逐列相同；515 條細目一條不少。
- `open-questions-20260923.md` 條數＝81。

**停止條件**：任一映射欄位缺值或需自造 ⇒ 停；生成物 `parse_canon_dir` 失敗 ⇒ 停；封存複本不可解析 ⇒ 停；全套件紅燈超過**現行基線 17**（9 他線既有＋8 換正本預期）或出現名單外的紅 ⇒ 停；⛔ skip 不計入紅燈數。⚠️ 本片**覆寫** `canon/jgb/*.md`（S1／S2 的正對照組）⇒ 覆寫前封存必須完成，且 S5 依 Plan 只能在 S4 之後。
**預算**：一個工作段落；fix/re-run ≤ 3 輪。**執行**：`executor`＋fresh `verifier`。

### S4 生成後的量測、斷言修復與驗收（⛔ 不部署、⛔ 不 commit）
**前置**：S3 已落地並經 verifier CONFIRMED（新正本 57 粗目／515 細目，`canon_sha256 = 9b67e763e9c50b04f0eaf9ce30981ce90f149ddb2704cd50b781145eeade4e25`；舊 210 條封存於 `docs/archive/2026-09/canon-pre-dsp067/`，sha `b94acd63…`）。

**S3 換正本後必須在本片收拾的紅燈與盲點（verifier 逐條歸因，⛔ 不得靠調低期望值帶過）**

| 類 | 測試 | 病灶 |
|---|---|---|
| 釘舊形狀 | `test_canon_assembler_req::test_load_canon_or_die_accepts_versioned_canon`（`_TOTAL_FINES = 210`、`_UNREVIEWED_IDS` 190 筆） | 寫死舊條數 |
| 釘舊形狀 | `test_canon_assembler_req::test_load_canon_or_die_reads_content_only_from_markdown`（找 `coarse_id == "A"`） | 假設粗目 id 是裸字母 |
| 釘舊形狀 | `test_canon_parser_req::test_real_canon_still_parses_under_9_1a_and_9_6_checks`（`[c.id …] == list("ABCDEFGHI")`） | 同上 |
| 全未審 | `test_canon_assembler_req::test_prospect_outline_is_deterministic_and_registers_canon`、`…::test_env_limit_lower_than_actual_raises`、`test_agent_turn_pm_outline_req`（2 條）、`test_agent_eval_req::test_candidates_on_hit_rows_…` | 假設「真正本有已審細目」 |
| **量尺失效（比紅燈更危險）** | `test_library_view_req.py` 與 `test_fine_index_content_parity_req.py` 兩條**自己 skip 掉**（釘 `canon_sha256` 前綴 `b94acd63`） | skip 不進紅燈數 ⇒ 「≤9 條紅」的停止條件**看不見它們** |
| **負對照變空** | `test_env_limit_lower_than_actual_raises`、`test_failed_pm_view_skips_pm_only_and_fails_closed` | 兩者都靠「把 K 預算壓到低於真實 `k_upper`」製造失敗；`k_upper=0` 時無法再壓低 ⇒ fail-closed 路徑目前沒有任何測試在走 |

**改動**：把上述斷言改成配合新形狀（條數由正本現算、粗目 id 不假設裸字母、已審相關的測資改用「全審假設副本」）；兩條自 skip 的量尺改成對新 sha 生效；兩條變空的負對照改用不依賴 `k_upper` 的手段製造失敗。⛔ 不得以放寬期望值或刪測試了事。

**擁有檔案（獨占）**：`rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py`、`test_canon_parser_req.py`、`test_agent_turn_pm_outline_req.py`、`test_agent_eval_req.py`、`test_library_view_req.py`、`test_fine_index_content_parity_req.py`；S4 的量測報告 `inputs/s4-measurement-<日>.md`（新檔）。⛔ 不碰 `services/agent/**`（S1／S2 已驗）、⛔ 不碰 `canon/jgb/**`（S3 已驗）、⛔ 不碰 drafts。

**量測（避免假綠）**：新正本落地時 515 條**全未審**，`build_canon_toc` 只列已審、`check_turn_budget` 只算 `citable=True` ⇒ **未審狀態下實測必為 toc 0 行／K 上界 0，這不是通過**。報告必須**同時列兩組，缺一即判不過**：
- **(a) 未審實測（控制組）**：`toc_tokens` 與 `k_upper` 對兩受眾皆須為 **0**；**不是 0 ⇒ 可見性壞了，大聲失敗**。
- **(b) 全審假設**：對一份「全數補上 `reviewed`」的**暫存副本**（⛔ 不得寫進 `canon/jgb/`）量同式，用 `outline._count_tokens` 真 tokenizer，報告須標 `token_count_approx=False`，列出 `k_upper`／`toc_tokens` 與上限（12,000／8,000）的比值。
  ⚠️ (b) 任一項超上限 ⇒ **停止交裁**，⛔ 不得自行調高常數表。

**驗收**
- 上面 (a)(b) 兩組數字齊備且判定明確。
- 8 條換正本紅燈全部修綠，且**每條都以「斷言改配合新形狀」或「測資改用全審副本」處理**，⛔ 不得放寬期望值、⛔ 不得刪測試；逐條列出改法。
- 2 條因釘舊 `canon_sha256` 而自 skip 的量尺（`test_library_view_req.py`、`test_fine_index_content_parity_req.py`）改成對新 sha 生效，**並證明它們真的會紅**（mutation：改壞被量的值即紅）。
- 2 條因 `k_upper=0` 而變空的負對照（`test_env_limit_lower_than_actual_raises`、`test_failed_pm_view_skips_pm_only_and_fails_closed`）改用不依賴 `k_upper` 的手段製造失敗，同樣附 mutation。
- `load_canon_or_die` 三源同位元組仍過；與舊 210 條的差異報告（`diff_report.py`；⚠️ 兩份形態不同，吃不下就記為停止條件交裁）。
- 全套件容器內跑：紅燈只剩 9 條他線既有且名單相同；**skip 數須逐條列名並說明為何 skip**（⛔ skip 不計紅燈，不得靠它藏問題）。

**停止條件**：(a) 組不是 0／0；(b) 組任一項超上限；任一紅燈只能靠放寬期望值或刪測試才綠；`diff_report.py` 吃不下兩種形態 ⇒ 停，交業主。
**預算**：一個工作段落；fix/re-run ≤ 3 輪。**執行**：`executor`＋fresh `verifier`。

### S5 清除舊格式（業主 2026-09-21「新格式一通 舊格式就需要清除棄用」；2026-09-23 依片級審查七條全 FIX 改寫）

**⚠️ 2026-09-23 改判（DSP-070）**：原「S6 → S5」排序作廢——它的唯一理由是 S6 真回合要跑封存舊正本，而那個受測物本身是錯的（見 S6）。封存已存進 git `c06575a9` 並移出工作樹。⇒ **前置：S4 通過（已通過）**；⛔ 不再依賴 S6。

**核心決定（業主 2026-09-23 裁，DSP-070 取代原「保留封存唯讀入口」）**：目錄路徑的裸字母形態**整條移除，⛔ 不留任何旗標或相容入口**。
- 現行正本、寫入路徑、閘門、導出、目錄導航：**一律只認新格式** `{#<架字母>-<slug>}`。
- 封存舊正本已不在工作樹（git `c06575a9`）；要讀它就 `git show` 取出，⛔ 不為它在 parser 留路。原先它撐的四件事已各自處置：parity 測試改為先比 sha（DSP-070，行為不變）；S4 差異報告已完成；S6 真回合改測新正本全審副本；「業者可用 9 條」基線要量時從 git `c06575a9` 取出重建（⛔ 不為它在 parser 留路）。

**擁有檔案（獨占）**
- `rag-orchestrator/services/agent/canon/canon_parser.py`（正則、`parse_canon_dir` 旗標、`export_catalog` 的 `is_bare` 分支、錯誤訊息）
- `rag-orchestrator/services/agent/canon/canon_assembler.py`（`resolve_canon_section` 的 `outline:A` 裸字母導航分支）
- `.claude/hooks/outline_gate.py` 與 `.codex/hooks/outline_gate.py`（兩份須逐位元相同）
- `.claude/skills/outline-curation/scripts/canon_to_library.py` 與 **`apply_proposal.py`**（兩支都會產出裸字母架檔，且產後以 `parse_canon_dir` 回讀才落檔）
- `rag-orchestrator/canon/jgb.json`、`rag-orchestrator/tests/fixtures/canon_jgb/expected.json`（重產）
- 測試與 fixture（**逐檔實查後的完整清單**）：`tests/fixtures/canon_jgb/shelves/A.md…I.md` 九檔、`test_canon_parser_req.py`、`test_outline_gate_req.py`、`test_canon_export_sync_req.py`、`test_canon_assembler_req.py`、`test_fine_index_content_parity_req.py`、`test_library_view_req.py`、`test_index_eval_req.py`、`test_outline_curation_reweigh_req.py`、`test_outline_curation_apply_remap_req.py`、`test_canon_to_library_req.py`、`tests/integration/agent/test_visible_subset_sql_equiv_req.py`
- ⛔ **不碰** `docs/archive/2026-09/canon-pre-dsp067/`（唯一一份、未進 git）、⛔ 不碰 `canon/jgb/*.md`、⛔ 不碰 drafts。

**單檔路徑的處置（審查 blocker 1）**：`COARSE_HEADING_RE` 是 `_parse_body` 唯一的粗目比對點，單檔與目錄共用；單檔正本的細目 id 中段還是比 `current_coarse[0]`，本質上要求裸字母。⇒ **拆成兩條**：`COARSE_HEADING_RE`（單檔路徑，**維持現值不動**）與 `SHELF_COARSE_HEADING_RE`（目錄路徑，收緊；⛔ 無寬版退路，DSP-070）。`_parse_body` 依 `shelf_letter is None` 選用。⇒ **逐檔實查（2026-09-23，⛔ 取代先前「20 檔全在單檔側」的錯誤宣稱）**：含裸字母粗目的檔共 30 個，分三類——

| 類 | 檔 | 處置 |
|---|---|---|
| **目錄路徑 fixture（必改）** | `tests/fixtures/canon_jgb/shelves/A.md…I.md` 九檔 | 改新形狀；連帶重產 `expected.json` |
| **目錄路徑測試（必改，合成裸字母九架再送 `parse_canon_dir`）** | `test_canon_parser_req.py`、`test_canon_export_sync_req.py`、`test_library_view_req.py`、`test_index_eval_req.py`、`test_fine_index_content_parity_req.py`、`test_outline_curation_reweigh_req.py`、`test_outline_curation_apply_remap_req.py`、`test_canon_to_library_req.py`、`test_visible_subset_sql_equiv_req.py` | 改新形狀（`test_fine_index_content_parity_req.py` 已於 DSP-070 改為先比 sha、不再讀封存目錄，⛔ 本片不動） |
| **單檔路徑（不動）** | `test_fine_index_req.py`、`test_candidate_selector_req.py`、`test_candidate_outline_req.py`、`test_agent_turn_unit_req.py`、`test_agent_policy_kb_outline_req.py`、`test_outline_curation_structure_req.py`、`test_outline_gate_req.py` 等 | ⛔ 不改（單檔正則維持原值） |

上表的「必改」兩類**全部納入本片獨占擁有清單與回退備份清單**。

**移除清單（逐項裁定，⛔ 不留「順手保留」）**
| # | 位置 | 處置 |
|---|---|---|
| 1 | `SHELF_COARSE_HEADING_RE`（目錄路徑） | 收緊為 `^##\s+(.+?)\s*\{#([A-I]-[a-z0-9-]+)\}\s*$`；⛔ 無寬版 |
| 2 | `parse_canon_dir` 舊形態分支（fm-title 相等檢查、「恰一個粗目」殘留） | 移除 |
| 3 | `export_catalog` 的 `is_bare` 整段輸出分支 | **移除**（導出只服務現行正本；封存不需重新導出） |
| 4 | `canon_assembler.resolve_canon_section` | **零改動**——該函式**沒有**裸字母特例分支（只有 `c.id == raw_id` 單一查找），新正本下 `outline:A` 本就回 `NO_MATCH`。⛔ 不得為此新增任何裸字母特例判斷（違反禁止特例修改與「不對模型區分」設計）；以既有測試證明 `outline:A` 與不存在粗目逐欄位相同 |
| 5 | 兩份 `outline_gate.py` 的裸字母放行 | 移除，兩份 `cmp` 須相同 |
| 6 | `canon_to_library.py` 與 `apply_proposal.py` 產出裸字母架檔（後者三處渲染、且產後回讀 `parse_canon_dir`） | **兩支都改產新形狀**；⚠️ `canon_to_library` 的 5 條紅燈屬既有 `sources` 問題，本片 ⛔ 不順手修 |
| 7 | 測試 fixture 內裸字母錨點（目錄路徑用者） | 改新形狀；`expected.json`／`jgb.json` 重產 |
| 7b | **裸字母專用錯誤訊息**（新增） | 目錄路徑時，以 `^##\\s+.+\\{#[A-Z]\\}\\s*$` 先行偵測並 raise 指定訊息；⛔ 只在 `shelf_letter is not None` 生效，⛔ 不影響單檔路徑與現行「標題行無法解析」斷言。否則收緊正則後裸字母只會落到泛用訊息，驗收第一條不可達 |
| 7c | **導出／啟動的拒絕**（新增） | `export_json`／`export_catalog` 進入點各加一條「任一 `coarse.id` 為單一大寫字母 ⇒ raise，訊息點名該粗目 id」；`load_canon_or_die` 經 `parse_canon_dir` 即擋住。否則移除 `is_bare` 分支後，裸字母會**靜默**掉進新形態分支輸出 |
| 8 | 封存目錄 | 已於 DSP-070 移出工作樹（git `c06575a9`）；本片⛔ 不再處理 |

**驗收（每條可證偽）**
- 負對照：裸字母架檔送 `parse_canon_dir` ⇒ 解析失敗，訊息**逐字含**「粗目 id 須為 `<架字母>-<slug>`，裸字母形態已於 DSP-067／S5 停用」；⛔ 同時把 `canon_parser` 那句泛用提示裡的 `{#X}` 範例改成新形狀（否則訊息自己在示範被停用的寫法）。
- 正對照：現行正本九架 `parse_canon_dir` 全綠，`canon_sha256 = 9b67e763…` 不變；`load_canon_or_die` 三源逐位元仍過。
- 單檔路徑：`parse_canon_text` 對含 `## X {#A}` 的單檔正本**仍成功**；`test_canon_parser_req.py` 單檔訊息斷言未改一字。
- **拒絕負對照（三條）**：含裸字母粗目 id 的**圖書館形態** doc（`library=True`）分別送 `export_json`／`export_catalog` ⇒ **皆 raise 且訊息點名裸字母粗目 id**；合成裸字母九架目錄送 `load_canon_or_die` ⇒ raise；mutation：拿掉新加的檢查後即紅。⚠️ 2026-09-24 更正（S5 verifier A1）：原文寫「以單檔 `parse_canon_text` 解析所得的 doc」自相矛盾——單檔路徑的裸字母是合法形態（`FINE_ID_RE` 中段須等於粗目 id），既有單檔測試 `test_roundtrip_deterministic` 本就對含裸字母的 SAMPLE 呼叫 `export_json`；照字面做會撞「單檔路徑不動」停止條件。⇒ 拒絕只對圖書館形態生效，單檔 doc 不拒（實作 `canon_parser._reject_bare_coarse_ids`）。
- 完整性：全庫搜尋裸字母粗目分支後的**殘留清單與上表逐項相符**（預期殘留＝單檔路徑 `COARSE_HEADING_RE` 一處，其餘為零；`rg allow_legacy_coarse` 零命中）。
- `test_fine_index_content_parity_req.py` 在 S5 後仍停在既有的 sha 不符 skip（DSP-070 前已改為先比 sha、不讀封存目錄），⛔ 不是紅燈、也不是新增 skip。
- 兩份 hook `cmp` 相同；全套件容器內紅燈仍 9 條且名單相同，skip 逐條列名。

**停止條件**：現行正本解析或三源比對失敗；單檔路徑任一既有訊息斷言需要改動；紅燈超過 9 或出現名單外的紅；需要動擁有清單外的檔 ⇒ 停，交業主。
**回退（⛔ 不可用 `git checkout`——`canon/jgb.json`、`canon/jgb/*.md` 皆未進 git）**：動手前把 `rag-orchestrator/canon/jgb.json`、`tests/fixtures/canon_jgb/expected.json`、**`tests/fixtures/canon_jgb/shelves/A.md…I.md` 九檔**各複製一份到 scratchpad 並記下 sha256，寫進交付報告；其餘擁有檔案逐檔確認 `git ls-files`，已追蹤者可 `git checkout -- <檔>`，未追蹤者一律先備份。
**預算**：一個工作段落；fix/re-run ≤ 3 輪。**執行**：`executor`＋fresh `verifier`。

### S6 提示詞改兩跳導航（業主 2026-09-23 裁：由本線做；排在 S4 之後、首次部署之前；**與 S5 無先後依賴**（DSP-070））
**⚠️ 受測物改判（業主 2026-09-23，DSP-070）**：原訂真回合跑「封存的舊 210 條」——⛔ **作廢**。那是即將停用的二層形態（9 個架字母粗目），量不到三層正本最難的一步（從 57 個產品功能粗目挑對粗目），在它上面的「通過」推不到新正本；它還倒過來造出「S6 必須先於 S5」的假依賴。⇒ 真回合改測**新正本的全審暫存副本**：把現行 `canon/jgb/` 複製到暫存目錄、全部細目標為已審、重導出 `jgb.json`／`CATALOG.md` 使三源同位元組，以 `AGENT_CANON_DIR`（僅 `DB_ENV=test` 生效）指向它；⛔ 不動 `canon/jgb/` 本身。內容未經業主審 ⇒ **只量軌跡、⛔ 不量答對率**。

**為什麼獨立成片**：`services/agent/agent_rules.py` 屬 5.1 線且該線已收案。⚠️ **更正先前說法**：那句一跳說法**目前沒有任何逐字斷言保護**——`test_agent_policy_kb_outline_req.py::test_policy_text_drops_ban_and_states_outline_prefix_shape` 只釘三個寬鬆子串（舊禁句不得在、`kb.get` 與 `整節後再引用` 在、`outline:` 在），改成兩跳而保留那三個子串仍會綠；且它只讀 `_POLICY_TEXT`，對 `_POLICY_TEXT_NON_PROSPECT`（業者／租客版，正是吃粗目目錄的受眾）零斷言。⇒ 本片要**補上**保護，不是繞過它。

**前置（硬性）**：業主書面把下列三個檔案的歸屬交給 9.10 線（三者現為他線未提交狀態）；⛔ 未交接不得動手。
**擁有檔案（獨占）**：`rag-orchestrator/services/agent/agent_rules.py`、`rag-orchestrator/tests/unit/agent/test_agent_policy_kb_outline_req.py`、`inputs/plan-5.1-policy-definitions-20260907.md`（附錄 A 同步）。

**改動**：
1. `_POLICY_TEXT` 與 `_POLICY_TEXT_NON_PROSPECT` **兩份**的一跳句改兩跳：目錄那一行是**粗目**，先 `kb.get("outline:<粗目 id>")` 取該粗目的細目清單（不可引用），再 `kb.get("outline:<細目 id>")` 讀整節並引用。
2. `test_agent_policy_kb_outline_req.py` **各為兩份政策文新增一條逐字子串斷言**釘住兩跳字樣（現行三條寬鬆子串保留）。
3. `plan-5.1` 附錄 A 同步。

**片內預算（⚠️ 零餘裕，這是本片最硬的約束）**：實測 `len(_POLICY_TEXT) == 1584`、`count("⛔") == 8`，而上限斷言是 `≤ 1584`／`≤ 8` ——**已經頂到上限，一個字都加不得**（`agent_rules.py:82` 的註解寫「實測 len()==1511」是**過時的**，實測為 1584）。一跳那句現長 116 字，兩跳說法必然更長 ⇒ **必須同段等量或超量精簡**，且 `⛔` 數不得增。上限斷言散在三個檔（`test_agent_rules_definitions_req.py:178,179,290,291`、`test_ask_target_req.py:470,471`、`test_agent_rules_pm_canon_merge_req.py:61,62`），⛔ **不得改動那些上限值**；兩份政策文皆不得含 `_EXAMPLE_MARKERS`（`（如`／`例如`／`像是` 等）。
⚠️ **若精簡後仍超過 1584**：停，交業主裁「放寬上限」或「改寫整段」，⛔ 不得自行調高——那個數字是附錄 A 的量測值，不是任意上限。

**驗收**：
- 兩條新斷言各自成立；**逐份 mutation**：把 `_POLICY_TEXT` 改回一跳 ⇒ 其斷言紅；把 `_POLICY_TEXT_NON_PROSPECT` 改回一跳 ⇒ 其斷言紅（⛔ 不以單一份代表兩份）。
- 報告列出改前／改後的 `len(_POLICY_TEXT)`（改前 1584）、`count("⛔")`（改前 8）；**三個含上限斷言的測試檔改前／改後 sha256 逐檔相等**（⚠️ `test_agent_rules_definitions_req.py` 目前是**未追蹤檔**，`git diff` 對它恆為空 ⇒ ⛔ 不得以 `git diff --stat` 代替 sha256），且三檔全綠。mutation：把其中任一個 `1584` 改大一個字元，該驗收須判紅。
- **真回合的前置（⛔ 花錢之前必須先做，否則結果必然不可判）**：每回合會**預先注入 K=5 條候選細目**＋種子化的目錄來源（`runtime._select_outline` → `CandidateOutlineDoc.from_canon`；`_seed_outline_provenance` 的存在就是為了讓模型**不必**呼叫 `kb.get("outline:*")`）。若目標細目已在候選裡，答案就在資料段、模型不會發任何 `kb.get`，軌跡與反向對照都不會出現，而「無反向對照不得判過」是硬閘。（2026-09-23 在封存上實測：業者僅 9 條可見，19 種問法目標 19/19 落在候選內，業者臂在封存上根本做不出來——這也是改測全審副本的理由之一；全審副本兩身分各數百條可見，K=5 只占極小比例。）
  ⇒ 選題後、花錢前，先**不呼叫模型**地印出該回合的 `sel_meta["candidate_ids"]`，確認目標細目**不在**候選裡；在裡面就換題。
  ⇒ 軌跡判讀：`tools/agent_eval.py` 的回合執行與 `tools/agent_attempts_report.py`（看 `sel_meta`／`violations`）；⚠️ `agent_eval.make_agent_identity` 寫死 `prospect`，業者臂需以同一組裝路徑換身分（評估腳本，⛔ 不改產線程式）。Verifier 須為 `enforce`（評估工具預設即是），否則引用類拒因只記錄不擋、反向對照無從重現。
  ⇒ 每臂**至少 3 回合**（模型有隨機性，n=1 判不了）。⇒ 支出估算隨之更新：2 受眾 × 2 臂 × 3 回合 = **12 次**起跳。
- **真回合**（需真 LLM 呼叫與支出，⛔ 支出授權未下即停）：在上述**全審暫存副本**上跑（`AGENT_CANON_DIR` 指向暫存目錄，僅 `DB_ENV=test`）；前置：暖 embedding 快取後索引須在 `PREPARE_TOTAL_TIMEOUT_S`（60 s）內 `ready`（封存上冷快取實測逾時、熱快取 31.8 s）；兩受眾各跑一次，提問挑一個答案落在已審細目的題目；trace 須顯示先 `kb.get("outline:<粗目 id>")`、再 `kb.get("outline:<細目 id>")`，且該回合無 `SOURCE_NOT_CITABLE`／`budget_exhausted`。**反向對照**：同環境以舊一跳政策文重跑一次，須重現 `SOURCE_NOT_CITABLE → budget_exhausted`；⛔ 無反向對照不得判過。
- 8 條換正本紅燈修綠、2 條自 skip 的量尺救回；其餘紅燈仍為 9 條他線既有且名單相同。

**交付報告須含**：三個擁有檔案的改前／改後 sha256 與 mtime；`git diff -- services/agent/agent_rules.py` 僅限兩處政策句（他線其餘未提交內容逐位元不變）。
**停止條件**：檔案歸屬未交接、或長度／`⛔` 上限撞牆、或支出未授權 ⇒ 停，交業主。
**預算**：一個工作段落；fix/re-run ≤ 3 輪。**執行**：`executor`＋fresh `verifier`。

## 4. 風險與回退

| 風險 | 處置 |
|---|---|
| S1 改壞 parser ⇒ 服務起不來 | S1 停止條件即以當時正本為正對照。⛔⛔ **回退不可用 `git checkout`**——整條 canon-library 功能都未 commit（HEAD 裡連 `parse_canon_dir`／`export_catalog` 都不存在），且 S1 擁有檔案中 `canon/jgb.json`、`tests/fixtures/canon_jgb/expected.json`、`.codex/hooks/outline_gate.py` **是未追蹤檔**。`git checkout --` 會把 S1＋S2＋S4 一起無聲抹掉。回退＝動手前自行備份並記 sha256（各片「回退」段已寫）|
| 重產 `jgb.json`／`expected.json` 與他線衝突 | 兩檔列入 S1 獨占清單；工作樹另有他線未提交檔，⛔ 不 `git add -A`、⛔ 不 stash |
| 目錄改形狀後模型找不到細目 | S2 的粗目導航分支承接；療效另以情境回測量，⛔ 不在本 Plan 宣稱 |
| 舊 210 條在新規則下不相容 | 新舊同一條正則、舊形態守門逐字保留；S1 驗收第一條就是它 |
| 生成腳本 slug 碰撞 | 大聲失敗，⛔ 不自動改名 |
| 近似 token 值誤導預算結論 | S4 (b) 用真 tokenizer 覆量；超標即停 |

## 5. 驗證安排

- 本 Plan：fresh `plan-verifier`（第 1 稿 REVISE 7 條 → 第 2 稿全 FIX → 收尾覆審 **READY**）。S5 為第 2 稿後新增的下游片，執行前另送一次片級審查（⛔ 不重開 S1 的核可）。
- S1：已實作並經 fresh `verifier` **CONFIRMED**（2026-09-21）。
- S3：方案 A 定案後改寫，送一次收尾片級審查。
- S6：新增片，執行前送片級審查。
- S2：片級審查兩輪（REVISE 5 條 → 全 FIX → 收尾覆審再 REVISE 2 條 → 全 FIX）。**依規矩兩輪 REVISE 即停止重送**，⛔ 不開第三輪規劃審查；S2 已依本稿實作並經 verifier CONFIRMED，實作後以 fresh `verifier` 作為唯一把關。
- S3：`--self-test` ＋ fresh `verifier` 抽 30 條回源。
- S4：整合驗證；`make test` 容器內；量測兩組數字缺一不可。

## 6. plan-verifier 第 1 稿七條處置（全 FIX）

| # | Blocker | 處置 |
|---|---|---|
| 1 | 粗目 id 正則與回溯相容矛盾 | §2 寫死單一正則同時容納 `{#A}` 與 `{#A-slug}`，並聲明裸字母是回溯相容形式 |
| 2 | `_parse_body` 無架字母、單檔路徑語義 | S1 改動 5：新增選填 `shelf_letter`，`None` 走原規則原訊息逐字不變 |
| 3 | 新欄位改變導出位元組 | 改用 `shelf_titles`（不動 `scopes` 形狀），S1 一併重產 `jgb.json`＋`expected.json`，導出與啟動測試列入驗收 |
| 4 | 閘門 hook 未認領且 §2 敘述誤導 | §2 加 ⚠️ 更正；S1 納入兩份 hook 與其測試，`cmp` 鏡像列入驗收 |
| 5 | 架標題／scope 在新形態失去來源 | `shelf_titles` 為唯一來源；S2 的 `export_catalog` 改查它；舊形態 fm-title 守門逐字保留 |
| 6 | S4 量測假綠 | S4 量測改雙組（未審實測須為 0、全審假設用真 tokenizer），缺項即不過 |
| 7 | envelope 缺擁有者／停止條件／預算 | 每片補擁有檔案（獨占）、停止條件、預算、執行角色 |

> 2026-09-21 追加（S3 片級審查 6 條全 FIX）：新增 **S3a**（斷句器引號感知，S3 前置）；粗目 id 改查**凍結表** `inputs/coarse-ids-20260921.md`（⛔ 不機械轉寫）；講法 `source` 定為 `draft:outline-20260920`；架 front matter 逐字沿用現行九架、`version` 寫 `2026-09-21.0`；`canon/jgb.json` 納入 S3 獨占清單；S3 補齊停止條件／預算／執行角色與三條指定負對照。

> 2026-09-21 追加：業主指示「新格式一通、舊格式就清除棄用」⇒ 新增 S5（§3），舊形態支援自此明記為過渡鷹架而非長期相容。
