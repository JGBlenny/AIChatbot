# Agentic SDLC and Spec-Driven Development

Kiro-style Spec-Driven Development on an agentic SDLC

## 事實紀律（CANON，⛔ 優先於本檔其餘各節）

**⛔ 禁止推測。任何關於「系統現在怎麼跑」的陳述，都必須來自實際程式、DB 或實跑輸出。**

1. **動任何子系統之前先起盤查**：`/canon-audit <功能鍵>`。功能鍵見 `.claude/MAP.md`
   （例：測對話邏輯用 `dialogue-logic`）。⚠️ **唯讀任務同樣要起**——M1 只擋 Edit/Write，
   盤查從頭到尾不寫檔，閘門一次都不會觸發，而「讀了一部分就下結論」正是這套系統的起點。
2. **回報事實一律附可重跑的查證指令**（檔案路徑＋可 grep 的符號，⛔ 不寫行號當事實，行號會漂）。
   查不到就說查不到，⛔ 不從文件補值。
3. **否定結論（沒有／找不到／不存在）必須帶正對照組**：檢查清單裡要有一個「已知必然存在」的項目；
   它若也沒中，就是工具或條件壞了，不是目標不存在。⛔ 沒有正對照組的否定結論一律不得回報。
4. **文件與程式衝突時 ⛔ 不自行選邊**：指出反證並交回裁決。
   ⚠️ 已知錯誤文件清單見 `.kiro/specs/conversational-routing-execution/HANDOFF-*.md` 的「已知錯誤文件」節——
   例如 `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` §3 漏了 b2b 嚴格分支，
   **照它補 `IS NULL` 會打穿刻意設計的跨業者隔離**。

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
