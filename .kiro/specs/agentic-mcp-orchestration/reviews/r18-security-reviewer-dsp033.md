# r18：DSP-033 v3——security-reviewer（唯讀，2026-09-05）

**判定：BLOCKING（F-1、F-2）**；其餘 14 條在 v4 內 FIX／接受／BACKLOG。處置全文見 `DECISIONS.md` DSP-033 v4「r18 安全審處置」。

- F-1（P1）τ=0.40 下尺自證 1/3 → **待業主**（選項 a 接受／b 停案）。
- F-2（P1）覆蓋絕對下限消失 → FIX 保留 `min_coverage_chars` 硬拒；順帶量窄化極性（零代價）保留。
- F-3～F-16：投影拒因、對數逾時、四格重算、canary 下沉、目錄指紋＋revision、only_first 截斷、記憶體上限、可用性不快取＋比率告警＋降級分計、長度不符降級、錯誤回應無原文、網段接受現狀、萬用前提探測、term_id None、semantic-model 權重 BACKLOG。

CONFIRMED：降級不開敏感出口；逐字引用未被取代；entail_score 不可反推原文；trust_remote_code 不需；授權 Apache-2.0；決定性同機一致（跨機以 verdict 可重現定義）；不阻塞事件迴圈已處置。第 7 題：v3 表述誠實，補「可重現的是 verdict 不是理由」與「前提來自可寫知識庫」兩點。
