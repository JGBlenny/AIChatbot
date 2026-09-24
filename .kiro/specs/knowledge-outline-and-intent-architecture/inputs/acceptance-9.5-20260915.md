# 9.5 重切驗收標準（業主 2026-09-15 凍結；⛔ 跑回測前定，⛔ 不依結果改）

## 一、硬閘（任一紅＝不收，機器判）
| # | 閘 | 量法 |
|---|---|---|
| H1 | 正本 `parse_canon_dir("canon/jgb")` 通過（`target_user` 值域／`see_also` 存在／policy 值域）——⚠️ 原文「兩份正本」寫於 DSP-058 前，`canon/{prospect,property_manager}.md` 已於 2026-09-15 刪除 | 9.1a parser |
| H2 | 講法跨細目重複 0 組；同細目重複句 0 | hook `check_phrasing_unique`＋句計數 |
| H3 | 內容保真：舊正本未排除的每一句在新正本恰好一次、總字數相等 | 盤查腳本 |
| H4 | `export_json`／`export_catalog` 後三源逐位元同源；預算改兩把尺 `OUTLINE_K_TOKEN_LIMIT` 12,000／`OUTLINE_TOC_TOKEN_LIMIT` 8,000（9.8 DSP-059 D′；⛔ 不再量整份篩選結果） | `canon_parser.export_json`＋`outline.check_turn_budget` |
| H5 | 不變量 34：講法 ∩ 凍結題句＝∅ | `canon_phrasing_frozen_disjoint` |
| H6 | 每細目 `target_user` 非空、無 `all_users` | parser（DSP-052） |

## 二、檢索面（先有基線，再比）
| # | 尺 | 基線 | 門檻 |
|---|---|---|---|
| R1 | prospect `index_eval` r@5 三臂 | **基線＝`inputs/index-eval-20260907.json`（同工具、同 gold，⛔ 不是 round-9 探針的 .870／.913，那是另一組 46 句非同源問法）**：title＋phrasing＋content 臂 r@5 依問法型 俗稱 .774／口語 .613／情境 .733／直接 .742／邊界 .533（loo=exact）。gold 綁舊 id ⇒ 先 `remap_ids` 重映；split／merge 格重判、只報不擋 | keep／move 格 r@5 **依問法型逐型 ≥ 基線** |
| R2 | pm 三臂 | 無（講法從未進索引）。**⚠️ 2026-09-15 實查：pm 沒有任何帶 gold 細目的題集**（`inputs/`、`eval/` 全掃 0；`outline-probe-scenario-gold` 18 條全是 prospect；`index_eval` 的 gold 靠 `helpcenter:` sources，pm 講法來源全是 `line-doc`）⇒ **R2 卡在沒有 gold，要先建 pm 題集**（每細目 ≥3 真實問法＋gold 細目，來源可取 demo 帳本 §1h 劇本 63 案；業主核可後凍結） | 本次即基線；門檻「＋講法臂 ≥ 標題臂」；**題集未建前 R2 記「未量」，⛔ 不得以無題集當通過** |
| R3 | 任一查詢 top-5 無「同題兩細目」 | — | 0 |

## 三、回答面（步 4 雙判者）
| A1 | 每格 2 判者互不可見，不一致加第 3 | skill 步 4 |
| A2 | 可答率 ≥ 上次（prospect 40.8%／放行句無據 1.15%）；pm 首量 | 不退步 |
| A3 | 敏感 0 漏 | 既有 |
| A4 | 15 條無 `reviewed` 細目在回測中顯示為不可見 | 正對照（證 fail-closed） |

## 四、情境面
| S1 | 八種情境走查在新正本重跑 | 8/8 出口與 `AGENTIC_MCP_ARCHITECTURE.md` §3 一致 |
| S2 | 每個非零粗目至少一句真實問法命中該粗目細目 | 覆蓋圖 |

## 五、⛔ 不算驗收
「代理說沒問題」；補審 15 條（內容核准，非驗收，但 A4 拿它當正對照）。

## 六、量測紀錄

### R1（2026-09-15，prospect 重切草稿 sha `3582950df671…`，同工具同 gold，loo=exact）
- **寬鬆版**（gold 經 `sources` 自動對映；split 子細目共享來源 ⇒ gold 細目 47→59，一對多文章 10→13）：三臂 × 五型 **15/15 ≥ 基線**。證據 `inputs/index-eval-recut-20260915.json`。
- **嚴格版**（非主要 split 子細目拿掉 helpcenter 來源 ⇒ gold 細目 **44**，比基線 47 少＝對草稿**不利**的口徑）：
  - **產線臂 title+phrasing+content**（`candidate_selector` 三種鍵取最高分＝這一臂）：**5/5 ≥ 基線**——俗稱 .774→.806、口語 .613→.645、情境 .733→.767、直接 .742→.742、邊界 .533→.667。
  - title 臂：情境 .600→.567、直接 .613→.581（各 −1 句／30）；title+phrasing 臂：直接 .742→.710（−1 句）。三格皆在單句噪音內且非產線臂，並且發生在 gold 比基線少 3 的口徑下。證據 `inputs/index-eval-recut-strict-20260915.json`。
- **判定：R1 通過**（產線臂兩種口徑皆 ≥ 基線）。⚠️ 附註：嚴格版跑時 hook 狀態檔寫入被 read-only 掛載擋（`/.claude/hooks/state/…`），量測輸出完整、僅 session 狀態未記。
- misrouted：基線 82 → 草稿 79。
- R3 尚未量（需逐句 top-5 輸出，`index_eval` 只留 misrouted）。

### A4（2026-09-15，對已覆寫的正本 pm sha `a859784b…`／prospect sha `3582950d…`）
- 15 條未審細目（pm 3／prospect 12）：`canon_visible`＝False、`build_outline` 該節 text 為空、`kb.get("outline:<id>")`＝NO_MATCH，**15/15 成立**；正對照：已審細目 visible=True、kb.get ok=True。
- **判定：A4 通過**（fail-closed 真的在）。⚠️ 依 plan-verifier：A4 必須在補審之前量——本紀錄即為補審前證據；補審後本項失去正對照，⛔ 不得再宣稱重量。

### S1 前置（2026-09-15，`agent_eval --set scenarios --provider fake`，$0）
- 新正本上 23 案跑通：candidate_fallback 0/23、candidate_selector_error 0/23、candidate_none_visible 0/23、avg_candidates 5.0 ⇒ **結構與候選選取在新正本上無故障**。
- ⚠️ fake provider 不驅動模型，敏感／固定句／boundary 等數字**無意義**（`outline_sha` 亦為空），⛔ 不作 S1 判定；S1 正式判定需 `--provider openai` 重跑（付費，待業主）。
- 收①狀態：H1–H6 ✅、R1 ✅、A4 ✅、S1 前置 ✅；R2 未量（無 pm 題集）、R3 未量（工具無逐句 top-5）、A1–A3／S1 正式／S2 待付費跑（步 4 雙判者、openai 情境）。

## 修訂紀錄（⚠️ 非業主授權；H1 只換物件名稱，H4 依業主已裁的 DSP-059 D′ 換掉量測對象——⛔ 兩者都不改及格線）

⚠️ A4／補審的「15 條」是 2026-09-15 當時的量（⚠️ 2026-09-23 換正本後，今天未審 **515＝全部**；190 是換版前的數），**刻意不改**——改它等於動判準，超出「只換物件名稱」的授權。

| 日期 | 列 | 原句 | 改為 | 為什麼 |
|---|---|---|---|---|
| 2026-09-23 | H1 | 兩份正本 `parse_canon` 通過 | 正本 `parse_canon_dir("canon/jgb")` 通過 | DSP-058 後只有一份正本；`canon/{prospect,property_manager}.md` 2026-09-15 已刪 |
| 2026-09-23 | H4 | `check_budget` 在 prospect 12,000／pm 8,000 內 | 兩把尺 `OUTLINE_K_TOKEN_LIMIT` 12,000／`OUTLINE_TOC_TOKEN_LIMIT` 8,000 | 9.8 DSP-059 D′ 改量兩尺，⛔ 不再量整份篩選結果 |
