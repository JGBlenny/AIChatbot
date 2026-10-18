# 計畫草稿：W3 查詢改由程式主導（2026-10-17）

> ⚠️ **草稿、未審**。前置：W1c 驗收通過（沿用其意圖判斷呼叫）。送審前須先跑 §2 第 0 步盤查。
> 業主原話（2026-10-17）：「流程交給程式，模型只負責聽懂」、「好 先起草 W2 和查詢的計畫」。
> 驗收清單草稿：`acceptance-query-program-led-w3-20261017.md`

## 0. 現況（已對碼／實測）

| 事實 | 查證 |
|---|---|
| 一般查詢由模型決定要不要查、查什麼（模型自呼 `jgb2.query.<domain>`，必填 `face`） | `rag-orchestrator/services/agent/tools/jgb2.py`（`*_FACE_BUILDERS`、`args.get("face")`） |
| 程式先查只涵蓋：編號、≤6 字短名稱、程式追問名稱後 ≤30 字答覆（僅物件 `jgb2.query.estates`） | `grep -n "def _pre_lookup_trigger\|_PRE_LOOKUP_ESTATE_TOOL =\|_PRE_LOOKUP_ANSWER_MAX_CHARS =" rag-orchestrator/services/agent/runtime.py` |
| 候選上限 5 筆（`JGB2_CANDIDATE_CAP`，預設 5）——以物件名查帳單只回 5 張（2027 年），不含 2026/11 那張 | `grep -n "_DEFAULT_CANDIDATE_CAP" rag-orchestrator/services/agent/tools/jgb2.py`；`~/jgb-archive/bedrock-eval-20261017/w1/D_A_before.json`（gpt-6-luna 自查後選錯帳單 750528） |
| 期別解析已有程式（`parse_period`、`_filter_bills`），但只用在延期繳費出卡路徑 | `grep -n "async def _resolve_bill_by_period\|def _filter_bills" rag-orchestrator/services/agent/tools/confirm.py` |
| 程式先查的結果以資料段注入（可引用），模型只組話 | `grep -n "PRE_LOOKUP_LABEL" rag-orchestrator/services/agent/runtime.py` |

## 1. 目標

查詢型問題（帳單、合約、修繕單、物件、電錶、帳號）由程式決定查什麼、查到後怎麼篩，模型只負責「聽懂要查什麼」與「把查到的講成話」。業界同型：Rasa CALM 由 Command Generator 輸出指令、程式執行（已渲染）。

## 2. 第 0 步：盤查（唯讀，送審前）

- `/canon-audit agentic-mcp` 後，列出 6 個 domain 的全部 `face`、每個 face 的必填參數與回傳形狀、候選上限與分頁行為。
- 從評估題庫與 demo 帳本挑真實查詢問句，標每句「應查哪個 domain／face／參數」，作為意圖抽取的期望表。
- 量模型自查現況：gpt-oss 跑查詢腳本 ×3（只量 gpt-oss，DSP-086），記查對率（以 fixture 為準）。

## 3. 設計候選（第 0 步後定案）

1. **意圖判斷呼叫擴充**（沿用 W1c 那一次呼叫，⛔ 另加呼叫）：輸出增加 `lookup: {domain, face, ref, keyword, period} | null`，值域由 `*_FACE_BUILDERS` 與表單導出（說明文字列值域，gpt-oss 不讀 enum）。
2. **程式執行查詢**：主模型之前由程式呼叫 `jgb2.query.<domain>`（同身分範圍、同計量），結果以資料段注入（沿用 pre_lookup 的注入與保留 id 機制）；有期別 ⇒ 程式以既有 `parse_period`／`_filter_bills` 篩選後再注入，⛔ 讓模型從 5 筆候選自挑。
3. **值閘**：`ref`／`keyword`／`period` 須出自使用者原話（沿用 W1 值閘）。
4. **模型仍可自呼查詢工具**作後備（先不拿掉，量測後再議）。
5. **候選上限**：程式篩選後仍多筆 ⇒ 列表＋追問（程式產出），⛔ 截斷成前 5 筆讓模型猜。

## 4. 不做

- 寫入流程（W1c）、截斷處置（W2）、知識章節選取。
- 改 jgb2 API 或 fixture。

## 5. 待業主決定（送審前）

- 是否在量測後拿掉模型自呼 `jgb2.query.*`（完全由程式查）。
- 多筆候選時的追問形式（清單按鈕 `select:` 或文字）。

## 6. 用量回報與分片

不設 token 上限；每片收尾回報實際用量（子代理 token 加總＋模型 API 費用估算）。可依第 0 步結果拆成多片（先帳單＋修繕，再其餘）；停點只用結果條件。
