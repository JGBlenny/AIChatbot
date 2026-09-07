# 受測物定義清單——步 2 探針 **(a′) 基線 3 rep**（探針 55；業主 2026-09-07 裁 (a′)、新機 24 GB 實跑）

> 與探針 52／53／54 同題集、同尺、同 `agent_rules.py`，**組態＝DSP-035 開發基線逐字**：`AGENT_MODEL=gpt-5-mini`＋`AGENT_REASONING_EFFORT=low`＋`AGENT_BUDGET_REWRITES=0`＋`OPENAI_TIMEOUT_S=60`，`--repeat 3`、只跑 `on` 臂。目的不是過門，是**拿一組可寫進 DSP-036 的乾淨數字**（獨立審閱指出 52／53／54 的 43%／6/10／16% 分別來自重寫開著、被否決的 `minimal`、四輪最差，⛔ 不得進收案）。
> 本機路徑：`rag-orchestrator/.probe-run-55-baseline/`（原名 `.probe-run-55`，因與 `inputs/plan-clarify-on-reject-20260907.md` §3 規劃的 probe55 同名，業主裁改名；`.git/info/exclude` 本機排除，⛔ `texts/` 不進版控）。

核可：業主（2026-09-07 對話「選 2，--apply」「裁 (a′)」「接受 87 句全標」）

## 1. 受測物

| 項 | 值 | 查證 |
|---|---|---|
| 知識正本 `rag-orchestrator/canon/prospect.md` | `canon_sha256 = 240e1a502a856217…`（version `2026-09-07.6`，與 52–54 同） | `cd rag-orchestrator && python3 -c "from services.agent.canon.canon_parser import parse_canon; print(parse_canon('canon/prospect.md').canon_sha256)"` |
| 對話規則 `services/agent/agent_rules.py` | sha256 `5e392c00c57253fd…`（5.1 定義版，與 51–54 同） | `shasum -a 256 rag-orchestrator/services/agent/agent_rules.py` |
| 程式 HEAD | `17d3b72e`（bundle 還原；工作樹乾淨） | `git rev-parse HEAD` |
| 題集 | `eval/outline-probe-20260907.json`，samples_sha `22aa2c10…`（36 題／49 turn，與 4.4b 起全同） | `report.md` 首行 `samples_sha` |
| 模型組態 | 容器 env 實得 `AGENT_MODEL=gpt-5-mini`、`AGENT_REASONING_EFFORT=low`、`AGENT_BUDGET_REWRITES=0`、`OPENAI_TIMEOUT_S=60`；⚠️ JSONL／report 都**沒有 model 欄位**，唯一證據是 `docker inspect probe55`（容器已 `--rm`，證據只剩本檔記錄與 HANDOFF §8 指令） | `rules_sha 3077f05f…`／`outline_sha bdb3dd6e…`（report.md） |
| 候選機制 | `CandidateSelector` K=5、`FineIndex` 358 鍵、`candidates_mode=on`、backend `embedding`（與 52–54 同） | report.md「candidates」節 |
| 執行 | `docker compose -f docker-compose.dev.yml run -d --name probe55 … --set outline-probe --chain agent --provider openai --candidates on --repeat 3 --dump-texts` | HANDOFF §8 |
| 環境 | 新機 24 GB（`sysctl hw.memsize`）；六服務常駐＋探針容器，swap 0.5→1.9 GB；15 分鐘／147 回合（舊機估 25 分鐘） | 本檔 |

## 2. 前置（新機首次實跑補出的三個 README 缺步，皆已補進 README-RESTORE 4b／4a′／4c）

- `aichatbot_test` 需 `scripts/provision-test-db.sh --apply`（否則 unit 3 failed）。
- `semantic_model/data/knowledge_base.json` 被 gitignore、不在 bundle；缺它 reranker 崩潰迴圈（ExitCode 3、RestartCount 14）——**`make audit` 與 unit 在此狀態下照樣全綠**（「reranker 靜默停用而稽核看不出來」第二次實證）。
- 3.4 embedding 快取（`.claude/skills/outline-curation/raw/`）缺則 unit 1 skip。
- `FineIndex.prepare` 冷啟首跑 60 s 逾時 ⇒ `absent`（`fine_index.py` `PREPARE_TOTAL_TIMEOUT_S`）；暖機後重跑即過，⛔ 未改常數。

## 3. 事實 vs 待裁

- 事實：H4 封包＝三 rep **所有放行句母體 87 句**（答到 60 回合），非抽樣；低於 (a′) 寫的 ≥100，業主裁「接受 87 全標」（3 rep 是 DSP-035 規格、母體全標滿足樣本量本意）。
- 事實：兩判者皆 sonnet、單 pass、互不可見、只看「句子＋來源段落」（brief `judge-brief-h4.md`）。
- 待裁：無。
