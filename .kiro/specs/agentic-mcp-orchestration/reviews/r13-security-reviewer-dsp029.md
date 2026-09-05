# r13：DSP-029 v2——security-reviewer（唯讀，2026-09-05）

**判定：BLOCKING**（P1 ×3、P2 ×6、P3 ×1）。處置全文見 `DECISIONS.md` DSP-029 v3「r13 安全審處置」。

| # | 級 | 發現 | 處置 |
|---|---|---|---|
| 1 | P1 | 0.5 相對覆蓋率擋不住 R4 三捏造句（實算：短句門檻退回 4、字元集合無序） | **REJECT 併入新資訊規則**（業主「先量誤殺再上」）；fixture 標 `known_open` 單列計數；DSP-030 用本案來源句離線量 |
| 2 | P1 | `[`→`［` 轉義被 NFKC 折回；標記在 sanitize 前貼會被自己轉義 | FIX：`wrap_provenance_data` 於 sanitize 後貼、標記綁 nonce、分隔 `§`、掃 `answer_nfkc` |
| F-A | P1 | 解析後 quote 若寄生在有預設值的模型欄位，模型可自填 | FIX：`resolved` 另傳 verifier，⛔ 不進 AgentOutput |
| 3 | P3 | 保留 id 拒收是條件式 | FIX：無條件拒收 |
| 4 | — | 無 provenance 工具不可引用（CONFIRMED）；單句問句 F-2 OPEN | 註記 |
| 5 | P2 | `kb_search` provenance citable=True；大綱 unit 含 question_summary 前綴 | FIX：citable=False；前綴不編號 |
| 6 | P2 | `--dump-texts` 落版控樹無 gitignore；30 天清理未落地 | FIX：gitignore、抽審後刪、旁路只放三元組、以 TRUNCATE 為準 |
| 7 | P2 | 子成因欄若帶模型 source 文字會繞過兩道無原文護欄 | FIX：`schema_cause` 封閉 Literal |
| F-B | P2 | 切句兩側需同一函式；jgb2 source 含 `#` 撞標記 | FIX：`provenance_units`；分隔 `§` |
| F-C | P2 | 整單元引文推高極性誤殺，打壞驗收 | FIX：POLARITY 單列基準 9/162，不得放寬 |

CONFIRMED-SAFE：`_canonicalize_outline_sources` 不汙染他工具；DSP-021 容錯消失方向是收緊；`answer` 單一導出點；R11.5 簽名不動；拒因回饋無原文；規則集不外洩。r2 #10：多句 FIX、單句 OPEN（不因本案關閉）。
