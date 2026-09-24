# 事實表對照（A vs B）— 2026-09-16

兩位盤查者互不知情、各自對 `design.md` 元件 5／6、程式、容器實測。本檔只列「兩表一致／不一致」與「規格 vs 程式不一致」，⛔ 不含改法。原表：`factsheet-outline-injection-A-20260916.md`、`factsheet-outline-injection-B-20260916.md`。

## 1. 兩表一致（可當事實用）

| 事實 | A | B |
|---|---|---|
| 每回合注入＝K=5 候選細目節＋當回合 `build_canon_toc` 的目錄節，經 `wrap_provenance_data("outline")` 進**唯一一則** system 訊息 | ✓ | ✓ |
| toc **每回合**注入、每回合依身分重算；靜態啟動 toc 被丟掉 | ✓ | ✓ |
| K＝5，`candidate_selector.py::K` 模組常數，無 env 可改 | ✓ | ✓ |
| 降級（索引未 ready／sha 不符／查詢失敗／例外）＝`from_visible(可見已審全集＋toc)`，⛔ 不是未過濾整份 | ✓ | ✓ |
| 「沒有候選機制」路徑（`agent_eval --candidates off`）才會原樣注入啟動整份視圖（含未審標題） | ✓ | ✓ |
| 啟動 `check_budget` 量的是整份受眾視圖（含未審標題行＋靜態 toc、不含 nonce 標記）；每回合候選路徑**零** `check_budget` | ✓ | ✓ |
| `check_budget` 在啟動鏈被呼叫兩次（`build_audience_outline` 內＋`app.py` 迴圈） | ✓ | ✓ |
| 上限＝`OUTLINE_TOKEN_LIMIT_DEFAULTS`（12,000／8,000／8,000）；env 只能調小；正本 `budget_tokens` 恆 0 不再讀 | ✓ | ✓ |
| 工作樹：prospect 視圖 6,187 tokens（60 節＝13 可引用＋46 未審標題＋toc）；**pm 視圖 10,896 > 8,000 ⇒ `OutlineBudgetExceeded`**，`test_real_views_fit_the_budget` FAILED、`test_env_cannot_raise_the_cap` PASSED | ✓ | ✓ |
| 正本 210 細目、未審 190、可引用 prospect 13／pm 9；toc prospect 13 行 373 tokens／pm 9 行 283 tokens | ✓ | ✓ |
| `kb.get("outline:toc")` 當場重算目錄（citable=False）；`outline:<id>` 需 `canon_visible`；tenant 一律 `NO_MATCH` | ✓ | ✓ |
| 所有數字量在**未提交工作樹**，HEAD 仍是兩份單檔正本；線上常駐容器未量 | ✓ | ✓ |

## 2. 兩表數字不同（原因已知，非矛盾）

| 項目 | A | B | 原因 |
|---|---|---|---|
| 一回合注入段 tokens | 2,017／2,870（prospect 兩題） | 2,752（prospect 一題） | 假向量後端、題目不同 ⇒ 候選組合不同；B 另給上下界 1,960–3,449（含標記＋toc） |
| `CandidateOutlineDoc.token_count`（無標記） | 1,334／2,042 | 1,889 | 同上 |
| 降級注入段 | `token_count` 3,751 | 資料段 5,222（含標記） | 量的層不同（無標記 vs 含標記） |

## 3. 規格 vs 程式／文件不一致（兩表皆點名；待裁，不是改法）

1. `design.md` 附錄 A 名詞「降級整份正本＝注入整份 `OutlineDoc`」與主要流程圖 else 分支「整份正本」 vs 元件 7／非功能／1.16 修訂「可見細目全集＋toc」——**規格內部自相矛盾**；程式照後者。
2. `design.md` 元件 5 介面碼塊：`load_canon_or_die(canon_dir, audience)`、`build_outline(doc, *, include_unreviewed_titles)`、`check_budget(min(env, doc.budget_tokens))`、呼叫鏈 `build_prospect_outline` 首行——程式已是 `load_canon_or_die(dir)`、`build_outline(doc, audience, identity, *, vendor_business_types)`、`min(env, 常數)`、`app.py` 逐受眾 `build_audience_outline`（3.2／DSP-058 註記有寫，原碼塊未改）。
3. `design.md` 非功能「整份 3,078 tokens／K=5≈500–800 字／toc ≤300 字」：3,078 無出處；現況整份 6,187、toc 518 字（prospect）；「字」未定義 chars/tokens。
4. `docs/api/mcp-facade.md` §10 與 `docker-compose.prod.yml` 註解：prospect 預設 10000（程式 12,000）、「pm 尚未消費」（程式啟動即組 pm 視圖）、「覆寫」（程式只准調小）；`AGENTIC_MCP_ARCHITECTURE.md` §A-9「可由 env 覆寫」同病。
5. `design.md` API：health 應有 `fine_items`／`approved_fine_items`／`phrasing_set_sha256`——程式 `health._canon_state` 無。
6. `OutlineDoc.token_count`／`PromptMeta.outline_token_count` 量的是無 nonce 標記文字，實際注入段大 30–45%（規格未寫）。
7. `agentic-mcp requirements.md` R5.5「prospect ≤10K」已被 design 1.12 改 12,000（兩份文件未同步）。

## 4. 兩表都沒量到
真 embedding 後端下的候選集與注入量；全審後投影（tasks.md 記的 35,893／106,064 由主 session 先前投影，B 未重算）；線上容器與 `.env` 的 env 值；完整 system prompt 含工具清單（B 量到 5,451 不含工具清單）。
