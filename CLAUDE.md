# Agentic SDLC and Spec-Driven Development

Kiro-style Spec-Driven Development on an agentic SDLC

## 事實紀律（CANON，⛔ 優先於本檔其餘各節）

**⛔ 禁止推測。任何關於「系統現在怎麼跑」的陳述，都必須來自實際程式、DB 或實跑輸出。**

1. **動任何子系統之前先起盤查**：`/canon-audit <功能鍵>`。功能鍵見 `.claude/MAP.md`
   （例：測現行對話邏輯用 **`agentic-mcp`**——⛔ 不是 `dialogue-logic`，那條是 2026-09-11 已退役的舊 REST 鏈）。⚠️ **唯讀任務同樣要起**——M1 只擋 Edit/Write，
   盤查從頭到尾不寫檔，閘門一次都不會觸發，而「讀了一部分就下結論」正是這套系統的起點。
2. **回報事實一律附可重跑的查證指令**（檔案路徑＋可 grep 的符號，⛔ 不寫行號當事實，行號會漂）。
   查不到就說查不到，⛔ 不從文件補值。
3. **否定結論（沒有／找不到／不存在）必須帶正對照組**：檢查清單裡要有一個「已知必然存在」的項目；
   它若也沒中，就是工具或條件壞了，不是目標不存在。⛔ 沒有正對照組的否定結論一律不得回報。
4. **文件與程式衝突時 ⛔ 不自行選邊**：指出反證並交回裁決。
   ⚠️ 已知錯誤文件清單見 `.kiro/specs/conversational-routing-execution/HANDOFF-*.md` 的「已知錯誤文件」節
   與同目錄 `b2b-doc-status-ledger.md` 的「不可依據」節——
   ⚠️ 這兩份都是 **2026-09-01 當時的快照，⛔ 不是現況**：其中
   `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` §3 已於 commit `96e526ae`（2026-09-01）
   補上 b2b 嚴格分支與 🔴 警語，該條**已失效**。引用帳本前先對碼。
   ⚠️ 但被它保護的事實仍然成立：b2b 業態過濾是 `business_types && ARRAY['system_provider']`、
   **無 `IS NULL` 放行**，**補上 `IS NULL` 會打穿刻意設計的跨業者隔離**。

## 對話線分工（DSP-091，2026-10-18 業主定案）

站內幫手對話線採混合式：理解使用者一律由 AI。下列環節的下一步由程式依宣告與狀態決定——寫入全程與確認、已選定的那筆紀錄、帶狀態的句子（請確認／已完成／已取消／已轉人）與確認卡、按鈕、轉人規則（含收尾）、知識完全查無的出口、唯讀查詢的查詢與篩選（依 AI 理解出的條件；AI 自呼工具為後備）。知識作答（要不要查、查什麼、怎麼組答案；只答得出一部分時說明缺什麼、部分回答、追問）與一般對話由 AI 決定，答案有沒有依據由 Verifier（程式）把關。

⛔ 任何計畫或改動讓 AI 決定上列程式環節的下一步，即違反本節。反過來也違反：⛔ 程式重新理解使用者的話（自己解析原話得出值或意圖，用它取代或否決 AI 的理解）；程式只驗 AI 結果的格式、範圍、值域，並決定下一步（DSP-127）。要改分工，先改 DSP-091 並經業主核可。

誰呼叫誰（現況；目標架構見 DSP-130，要對齊，見 DSP-131）：MCP 只是工具對外的協定（呼叫端 → 本系統）；AI 只提出工具呼叫，由 AgentRuntime 用內部函式執行（主要是 `registry.call`），都不走 MCP 協定；打 JGB API 的是本系統程式，AI 不打。講到呼叫工具時寫明由 AI 提出或由程式發起，⛔ 用「MCP」泛指工具層。

**目標架構（DSP-130、DSP-131，現行工作就是對齊它）**：本系統是對話服務，不是 MCP 系統。呼叫端走專用對話 API，`/mcp` 不是最終入口，呼叫端改完就關。JGB 工具由 JGB 維護、一定搬出本系統，本系統當 MCP client 呼叫，語意層留本機。模型呼叫、embedding、辨識都不走 MCP。⛔ 照現況文件設計新功能；現況文件寫的是目前跑的樣子。

分工表、原則、目標架構圖、差距：`docs/architecture/TARGET_ARCHITECTURE.md`（架構唯一正本）。工作線目標、驗收、分片與路徑：`.kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md`。決策與依據：`.claude/decisions/DSP-091.md`、`.claude/decisions/DSP-127.md`。

## 站內幫手線：推進上線優先（DSP-115，2026-10-25 業主定案）

業主：「可以把整條線 主要推進上線 而不是打路上所有小事都修完」。

1. 順序：… F12 → **W2 → E → 填欄只填答覆（DSP-117） → 填欄結構化（DSP-128）∥ 對話入口對齊（DSP-131） → 第 4 步切換正式機** →（上線後）雙胞胎與手開帳單合約 → D → …；排片先看是否在上線最低範圍、是否擋上線，不在的往後排。
2. 每條審查／驗證發現先答「不修，下一步會變嗎」：不變 ⇒ 記該片「後補清單」，收案時一起處理；⛔ 為它重寫計畫、重送審查。plan-verifier 回這類 REVISE ⇒ 主會話處置 DEFER、寫進後補清單、連同理由交業主核可。
3. 不得後補、照修：寫錯資料（錯筆卡、錯筆寫入）、資安與個資外露、會讓上線出錯的事實錯誤。
4. 與全域 `~/.claude/CLAUDE.md` 的 P2 處置、「READY 才交核可」衝突時，本線依本節。

現況與下一步看 `.kiro/specs/agentic-mcp-orchestration/HANDOFF-20261018.md`；決策與依據 `.claude/decisions/DSP-115.md`。

## Project Context

### Paths
- Steering: `.kiro/steering/`
- Specs: `.kiro/specs/`

### Steering vs Specification

**Steering** (`.kiro/steering/`) - Guide AI with project-wide rules and context
**Specs** (`.kiro/specs/`) - Formalize development process for individual features

### Active Specifications
- Check `.kiro/specs/` for active specifications
- Use `/kiro-spec-status [feature-name]` to check progress

## Development Guidelines
- Think in English, generate responses in Traditional Chinese. All Markdown content written to project files (e.g., requirements.md, design.md, tasks.md, research.md, validation reports) MUST be written in the target language configured for this specification (see spec.json.language).

## Minimal Workflow
- Phase 0 (optional): `/kiro-steering`, `/kiro-steering-custom`
- Discovery: `/kiro-discovery "idea"` — determines action path, writes brief.md + roadmap.md for multi-spec projects
- Phase 1 (Specification):
  - Single spec: `/kiro-spec-quick {feature} [--auto]` or step by step:
    - `/kiro-spec-init "description"`
    - `/kiro-spec-requirements {feature}`
    - `/kiro-validate-gap {feature}` (optional: for existing codebase)
    - `/kiro-spec-design {feature} [-y]`
    - `/kiro-validate-design {feature}` (optional: design review)
    - `/kiro-spec-tasks {feature} [-y]`
  - Multi-spec: `/kiro-spec-batch` — creates all specs from roadmap.md in parallel by dependency wave
- Phase 2 (Implementation): `/kiro-impl {feature} [tasks]`
  - Without task numbers: autonomous mode (subagent per task + independent review + final validation)
  - With task numbers: manual mode (selected tasks in main context, still reviewer-gated before completion)
  - `/kiro-validate-impl {feature}` (standalone re-validation)
- Progress check: `/kiro-spec-status {feature}` (use anytime)

## Skills Structure
Skills are located in `.claude/skills/kiro-*/SKILL.md`
- Each skill is a directory with a `SKILL.md` file
- Skills run inline with access to conversation context
- Skills may delegate parallel research to subagents for efficiency
- Additional files (templates, examples) can be added to skill directories
- `kiro-review` — task-local adversarial review protocol used by reviewer subagents
- `kiro-debug` — root-cause-first debug protocol used by debugger subagents
- `kiro-verify-completion` — fresh-evidence gate before success or completion claims
- **If there is even a 1% chance a skill applies to the current task, invoke it.** Do not skip skills because the task seems simple.

## Development Rules
- 3-phase approval workflow: Requirements → Design → Tasks → Implementation
- Human review required each phase; use `-y` only for intentional fast-track
- Keep steering current and verify alignment with `/kiro-spec-status`
- Follow the user's instructions precisely, and within that scope act autonomously: gather the necessary context and complete the requested work end-to-end in this run, asking questions only when essential information is missing or the instructions are critically ambiguous.

## Steering Configuration
- Load entire `.kiro/steering/` as project memory
- Default files: `product.md`, `tech.md`, `structure.md`
- Custom files are supported (managed via `/kiro-steering-custom`)
