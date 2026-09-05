# `nli_model/` — 離線抽審用的中文 NLI 服務（DSP-034 後）

## 狀態（2026-09-06 起）

- **離線抽審工具**：需要時手動起、用完關；⛔ **不在任何 compose 服務**裡
  （`docker-compose.prod.yml`／`docker-compose.dev.yml` 都已無 `nli-model` 服務與 `NLI_*` env）。
- ⛔ **不接 Verifier**：`rag-orchestrator` 的 Verifier 步③已回到 DSP-029a 的
  「相對覆蓋率 ∧ 絕對下限 ∧ 全極性」，程式裡不再有任何 NLI 客戶端、降級概念或蘊涵拒因。
  查證：`grep -rn 'NLI_URL\|entail_score\|nli_client' rag-orchestrator` 應為空。
- ⚠️ `Dockerfile` 與 `scripts/api_server.py` 的內嵌註解仍寫著 DSP-033 時期的
  「Verifier 步③用」——那是**當時**的用途，⛔ 不得據以認為它現在接在線上；
  現況以本檔為準（DSP-034 未改動那兩個檔，避免無謂的差異）。
- 決策紀錄：`.claude/DECISIONS.md` 的 **DSP-034**（撤出線上路徑、保留離線）。

## 啟動方式

```bash
# 建置（權重在建置期下載並比對目錄指紋；指紋不符會 fail-closed）
docker build -t aichatbot-nli-model nli_model/

# 起服務（⛔ 只綁 127.0.0.1，這個服務吃知識庫原文與模型輸出，沒有對外的理由）
docker run --rm -p 127.0.0.1:8003:8000 aichatbot-nli-model
```

- `GET /health` → `{"nli_ready", "model_sha", "canary_ok"}`；`nli_ready` 為真代表
  **canary 相符且目錄指紋相符**。
- `POST /nli` → body 為 `{"pairs": [{"premise": ..., "hypothesis": ...}]}`，
  每一對**只收 `premise` 與 `hypothesis` 兩個欄位**（多餘欄位不是介面的一部分）；
  回 `{"scores", "model_sha", "tau_hint"}`，`scores[i]` 為蘊涵機率，
  該對算不出來（例如 `hypothesis` 超長）時是 `null`。
  ⚠️ `tau_hint` 只是映像自己 canary 用的值，⛔ 不是任何線上判定門檻。
- 單元測試（用假模型物件、⛔ 不載 torch、⛔ 不觸網）跑在 dev 測試容器裡：
  `nli_model/` 以 `./nli_model:/nli_model:ro` 掛入，測試路徑要另外指定，
  ⛔ 不會被 `run-tests.sh unit tests/unit/agent/` 帶到。

## ⚠️ 前提形狀教訓（⛔ 勿再踩）

尺自證原本宣稱三句捏造有 1/3 落在 τ=0.40 之下（0.92／0.44／**0.36**）。
**2026-09-06 查明：那三個數是拿「整段大綱」當前提算出來的**，
而線上 Verifier（refs → unit）與 τ 校準用的 R8 181 對，前提都是
`provenance_units` 切出的**單句**。同模型、同權重、同 tokenizer 設定下，
單句前提實測為 **0.9615／0.5899／0.5923 ⇒ 0/3** 低於 τ（有據兩句 0.9918／0.9896）。

⇒ **任何 canary／門檻樣本的前提，一律用 `provenance_units` 切出的單句**；
前提形狀換了就是換了一把尺，期望值只能因為「輸入形狀量錯」而更正，
⛔ 不得為了讓自證變綠而調 τ 或改期望值。四向對照見
`.kiro/specs/agentic-mcp-orchestration/eval/nli-offline-20260905.md`。

## 第三批盲標結論與重提條件

第三批盲標（兩位獨立代理、365 句、二分一致 98%，一致子集 350 句：有據 273／無據 77）：
**NLI 尺誤殺有據句 19.0%（52/273）、抓到無據句 80.5%（62/77）；同批現行 DSP-029a 尺為 13.9%／62.3%**
（`.kiro/specs/agentic-mcp-orchestration/eval/perf-agent-regression-20260905/round9-dsp033/README.md` 驗收②）。
抓到率 +18 點，但誤殺率遠超 ≤10% 的門檻，且「多 ref 串成單一前提」的結構性選項離線量測顯示
誤殺／抓到完全不變 ⇒ 此路無效。故 DSP-034 撤出線上路徑。

**重提條件（DSP-034）**：新尺（新模型、新前提組法或新複合規則）在**凍結的 holdout** 上，
**誤殺 ≤10% 且抓到 > 現行尺同批**，才重新討論上線。
⛔ 不得看過結果再改 holdout 範圍、⛔ 不得改判準遷就結果。
