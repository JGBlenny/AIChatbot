# Testing（程式碼測試）＋ 文件追溯 Steering

> 由 spec **testing-traceability** 沉澱（R9.3）。本軌道評估「程式碼行為正確性與文件一致性」，
> 與 [testing.md](./testing.md)「答案品質回測迴圈」**並存互補、不互相取代**。

## 一、執行環境（canonical）

- **一律在 Python 3.11 容器內跑 pytest**（對齊執行期；host 可能為 3.9，產品碼用 3.10+ 語法會收集失敗）。
- 單一入口（本地與 CI 同一支）：
  - `make test`（＝unit）、`make test-cov`、`make test-integration`、`make test-all`
  - 或 `scripts/run-tests.sh [unit|integration|e2e|all] [--cov]`
  - 底層：`docker compose -f docker-compose.dev.yml run --rm rag-orchestrator ...`（掛載源碼、改碼即跑、免 rebuild）
- 測試相依在 `rag-orchestrator/requirements-test.txt`（dev/CI 安裝，**正式 image 不含**）。

## 二、分層與標記（D3）

- **unit**：純函式／mock、可離線、<1s → **CI 主力、必綠**。
- **integration**：真實 DB／跨模組 → 預設略過，`RUN_INTEGRATION=1` 才跑。
- **e2e**：經 `/api/v1/message`／SSE、需整服務 → 預設略過，`RUN_E2E=1` 才跑。
- 既有測試的分層**集中於 `tests/conftest.py`** 以 `pytest_collection_modifyitems` 指派（不逐檔改、零行為變動）；
  分層依據＝離線實跑結果。**新測試一律用顯式 marker**：`@pytest.mark.unit/integration/e2e`。
- 真實相依層在無相依時**標示略過（skipped）而非失敗**，避免假綠燈（R4.5）。

### 目錄架構（layer-first，跨服務統一）

測試以「**層級 → 領域**」兩層目錄組織,讓測試金字塔在檔案樹上可見;`conftest.py` 留在 `tests/` 根(套用所有子目錄):

```
<service>/tests/
  conftest.py                     # 共用 fixtures(套用全部子層)
  unit/        <領域>/            # category/ retrieval/ conversational/ forms/ security/ api/ _meta/
  integration/ <領域>/            # 真實 DB/跨模組
  e2e/         <領域>/            # 整服務 HTTP/SSE
```

- **層級＝第一層目錄**(unit/integration/e2e)＝測試金字塔;**領域＝第二層**(依功能)。
- 檔案仍須帶顯式 `@pytest.mark.<層級>`(目錄是給人看,marker 是給 `-m` 選層與 skip gate 用,兩者一致)。
- pytest `testpaths=tests` 遞迴收集、追溯 `scan.py` 用 `rglob` → 子目錄皆自動納入,無需改設定。
- 新服務(如 knowledge-admin)沿用相同 `tests/<層級>/<領域>/` 架構 + 自己的 conftest。

## 三、追溯標記（需求↔測試↔文件,D3/D4）

- 測試宣告需求：`@pytest.mark.req("testing-traceability:5.2")`（marker 為主；舊 docstring `spec:id` 過渡）。
- 文件章節背書：在 docs 關鍵行為章節加 `<!-- tested-by: spec:id -->`。
- 產報告：`make trace` 或 `python3 rag-orchestrator/tools/traceability/scan.py`
  → `.kiro/specs/testing-traceability/traceability-matrix.{md,json}`。
- 五類缺口：孤兒需求／孤兒測試（待標記）／失效引用／未背書文件／候選過時。**漸進式**：未標記不報錯。

## 四、覆蓋率 ratchet（R3/D5）

- 基準：`rag-orchestrator/tests/coverage-baseline.json`（unit 層、`--cov=services --cov=routers`）。
- 守門：`tools/coverage/check_baseline.py`——**CI 只讀比對**，低於基準→非 0（擋合併）。
- **只升不降**：覆蓋率提升後由**人工**重量測、更新 baseline 並 commit（CI 不自動寫回）。

## 五、排除範圍（不納入正式回歸／覆蓋）

- 根 `./tests/`：手動工具腳本樹（D6），排除於 CI／覆蓋率。
- `rag-orchestrator/tests/verify_migration_*.py`、`*/migrations/*`、`scripts/*`、`app.py`：見 `.coveragerc` omit。
- `rag-orchestrator/test_*.py`（根層調試腳本）：`.gitignore` 已排除，非正式測試集。
- `coverage-baseline.json` **要版控**；`tests/.coverage*.json` 為執行產物（已 gitignore）。

## 六、CI（R4/D2）

- `.github/workflows/tests.yml`：
  - **unit job（硬把關）**：unit+cov → ratchet 守門 → 追溯掃描＋artifact。
  - **integration job（非阻擋）**：起 postgres/redis 嘗試 integration；完整 schema/seed 供裝為後續工作。
  - e2e 不在 CI 跑（未設 RUN_E2E）→ 略過不假綠燈。

## 七、好測試鐵則

可重複（LLM/時間/亂數 mock）、隔離（不依賴順序/共用狀態）、測行為不測實作、一條測一件事、
失敗訊息清楚、真實相依需標記可略過。新測試務必歸層 ＋ 貼 `req` 標記（自動納入追溯）。
