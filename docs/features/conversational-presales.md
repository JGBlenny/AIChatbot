# 對話式回答模式（Conversational）＋ 售前顧問

> option-routing R14–R19。將「單次直答」升級為通用的「**多輪自適應問答 → 收斂**」回答模式；
> 售前（prospect）為第一個套用此模式的面向。資料驅動、可擴充、支援真 token 串流。
> 串接 API 見 [`docs/api/conversational-api.md`](../api/conversational-api.md)。

## 一、概念

- **answer_mode**：`direct`（單次直答，現況）/ `conversational`（多輪問答→收斂）。
- **opt-in 資料驅動**：只有「有設定」的角色/主題走 conversational；其餘一律 direct（不把直答題拖進迴圈）。
- **售前首例**：`prospect`（mode=b2b）整角色走 conversational；像顧問一樣先了解再推薦。

## 二、流程（每輪）

```
prospect 訊息（mode=b2b, target_user=prospect, 固定 session_id）
  → 對話引擎 brain（單次 structured LLM call）判斷：
       ask      → 反問一題（標準欄位：身分/規模/痛點/有無團隊/有興趣功能；一次一題）
       converge → 收斂
                   ├ recommend：已知身分+(規模或痛點) → 依 grounding 知識合成「個人化推薦＋CTA」
                   └ answer   ：明確事實問題（競品/價格/功能）→ 直接用知識 grounding 回答
```

- **基本資訊門檻**：推薦型收斂前至少要有 `identity ＋（scale 或 pain）`；不足先補問（即使喊「直接給建議」）。
- **提問硬上限**：`MAX_ASKS=20`（保底，正常由 AI 自行判斷收斂）。
- **推薦後判斷**：使用者下一句分三類處理 —— 結束/接受（簡短肯定）、追問（脈絡內直答、不重述方案）、新主題（照一般規則）。
- **收斂不關閉會話**：保留上下文供後續追問；只有使用者「取消」才結束。

## 三、合規鐵則（內容硬約束）

- **不報價**：價格一律導 `https://www.jgbsmart.com/pricing` 或留資，不講數字。
- **IoT 不主動**：被問才說「細節由專人說明」、不報價。
- **競品中立**：被問才比較、只憑事實、未列明說「不確定，建議向對方確認」、不斷言對方沒有。
- **CTA**：推薦結尾導預約 demo `https://www.jgbsmart.com/demo-form`（連結用純網址，不用 markdown `[]()`）。
- 事實只能來自「系統脈絡 md ＋ 選定知識」，不杜撰。

## 四、架構與檔案

| 層 | 檔案 | 職責 |
|---|---|---|
| 設定 | `rag-orchestrator/services/conversational_config.py` | `ConversationalConfig`＋DB 載入（資料驅動）＋角色/主題 dispatch |
| 規則 | `rag-orchestrator/services/conversational_rules.py` | 依 target_user 載入 persona 規則（DB `category='對話規則'` ＋ code fallback） |
| 引擎 | `rag-orchestrator/services/conversational_engine.py` | 狀態（form_sessions 偽會話 form_id=`conversational`）、prepare/handle/stream_answer、grounding 三態 |
| brain/合成 | `rag-orchestrator/services/llm_answer_optimizer.py` | `conversational_step`（brain）、`synthesize_presales_answer(_stream)`（合成/串流） |
| 系統脈絡 | `rag-orchestrator/services/system_context.py` | 載入 `category='系統脈絡'` md（合規底座＋功能索引） |
| 接線 | `rag-orchestrator/routers/chat.py` | Step 1.5 engine-first dispatch、續對話 hook、SSE 串流 |
| 設定 API | `rag-orchestrator/routers/conversational_configs.py` | 對話設定 list/upsert/delete |
| 管理畫面 | `knowledge-admin/frontend/src/views/ConversationalConfigView.vue` | 後台「對話設定」頁 |

### 模型分流（成本）
- 推薦（force）＝ `PRESALES_SYNTH_MODEL`（預設 gpt-4o，主打體驗/串流）
- 追問/事實答（suppress/auto）＝ `PRESALES_ANSWER_MODEL`（預設 gpt-4o-mini，省成本）
- brain ＝ `PRESALES_SYNTH_MODEL`

## 五、資料（DB，category 保留分類）

- `category='對話規則'`：每列＝一個角色的 persona 規則（`answer`）＋設定（`generation_metadata.conversational_config`）。
- `category='系統脈絡'`：售前系統脈絡 md（合規底座，注入所有 prospect 合成）。
- 兩者皆**排除於檢索之外**（vendor_knowledge_retriever_v2 WHERE 排除），不會被當答案回傳。
- 售前知識：b2b / `target_user=prospect` scope（C1–C6 模組、競品 E1–E3、價格 D1、方案…）。

## 六、啟用範圍與擴充（資料驅動）

- **啟用角色明確控制**：`routers/chat.py` 的 `CONVERSATIONAL_ENABLED_ROLES`（目前 `{'prospect'}`）；不因 DB 有設定就自動開。
- **新增一組面向/角色**（白名單內角色）＝ 後台「對話設定」頁新增一筆（角色、規則、grounding 範圍、進入方式），**零改程式**。
- **進入方式**：`freetext`（整角色，如 prospect）/ `topic`（命中某分類/關鍵字才進，需 Phase 3）。
- **grounding 選材三態**（決定性優先）：`vector`（語意，廣主題）/ `category`（整批撈某分類，窄主題）/ `ids`（明列知識 id）。
- 全新角色「名稱」需在 `CONVERSATIONAL_ENABLED_ROLES` 與 `TARGET_USER_ROLES` 白名單各加 1 行（安全防呆）。

> 詳見設計藍圖：`.kiro/specs/option-routing/design.md` 修訂 3.1/3.2（X1–X4、決策 19–21）。

## 七、後台管理畫面

knowledge-admin → 側欄「💬 對話設定」（`/conversational-config`）：
- 列出/新增/編輯/停用對話設定；存檔即時生效（清快取）。
- 欄位：角色、啟用、answer_mode、persona 規則、進入方式（freetext/topic）、grounding 選材（vector/category/ids）、seed。

## 八、部署注意（重要）

1. 程式：合併 main → prod `git pull` → 重建 `rag-orchestrator` ＋ 前端 build → restart `knowledge-admin-web`。
2. env：`PRESALES_SYNTH_MODEL=gpt-4o`、`PRESALES_ANSWER_MODEL=gpt-4o-mini`。
3. **DB 資料**：售前知識/系統脈絡/對話規則/conversational 佔位 form 需在 prod 存在（換庫或 seed）。
4. ⚠️ **換庫/推版必一併重建 `semantic-model`（reranker）**，否則排序/表單觸發會與新資料不同步（見 [部署指南](../deployment/DEPLOY_GUIDE.md)）。

## 九、相關規格

- 需求/設計/任務：`.kiro/specs/option-routing/`（R14–R19、通用化 X1–X4）。
- 串接 API：[`docs/api/conversational-api.md`](../api/conversational-api.md)。
