# smoke 計分尺（2026-09-10 升格進 repo；Plan R §1.4 的對照尺）

- `mcp_smoke.py`：以 pm 身分經 `/mcp` 打 `agent.turn` 多回合並逐回合抓 trace；金鑰**只從 stdin 第一行**進變數（⛔ 不進 argv／env／log）。用法見檔頭。
- `b4_score.py`：line-bot 第二輪劇本（`scenarios_lb2.json`，21 回合）13 項判準計分。⚠️ 正則看不見「複誦型」病灶，該類以 golden／verifier 守。
- `liff_score.py`：線③（LIFF 拍照報修 48 回合）出卡／洩漏／轉人／p50／p95 對照（`old new` 兩檔）。

劇本 JSON 與結果 jsonl 不進 repo（含測試用金鑰 id 與物件名）；跑法見 `docs/deployment-runbook.md` §20 與帳本 §1o。
