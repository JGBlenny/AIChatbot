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
