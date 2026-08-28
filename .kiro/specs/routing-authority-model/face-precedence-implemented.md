# 刀 A：authority-aware Face precedence 已落地

- 日期：2026-08-28｜依據：裁定 001-A ②、裁定 001-B
- 分支：`fix/retrieval-routing-stability`
- 動到的產線檔：`rag-orchestrator/services/responsibility.py`、`rag-orchestrator/routers/chat.py`

## Claim ceiling（**只能宣稱到這裡**）

```text
✅ Implement authority-aware Face precedence while preserving pre-change config
   selection semantics. Technical fail-open retains compatibility candidate but
   cannot obtain responsibility commit authority.
❌ routing regression fixed｜❌ integration fully deterministic｜❌ P2.5 fixed
```

## 形狀

`services/responsibility.py` 新增仲裁的**唯一 oracle**——產線兩個判定點與測試都呼叫它：

```text
face_precedence(face_authority, knowledge_present) → face｜knowledge｜compat_face｜fallback

authoritative              YES / NO   → face
unevaluated（resolver 未跑）YES / NO   → face（既有行為，不在本裁定射程）
compat_fail_open           YES        → **knowledge**（技術故障不得取得 routing authority）
compat_fail_open           NO         → compat_face（相容性，**非** responsibility-confirmed）
no_face                    YES / NO   → knowledge ／ fallback
```

`routers/chat.py`：

```text
_resolve_pre_commit_candidate   → (config, authority)
_diagnosis_config_for_knowledge → (config, authority)
handle_retrieval
  進 direct-answer gate 前：face_precedence(authority, knowledge_present=True)
    == "face"          → 立即進場
    otherwise          → **不 commit**，暫存 deferred face，讓 Knowledge 先走
  gate 後：face_precedence(authority, knowledge_present=bool(knowledge_list))
    == "compat_face"   → 相容性進場（telemetry 標 responsibility_confirmed=false）
_enter_diagnosis_facet(...)     → 兩個判定點**共用同一段進場**
telemetry facet_entry 新增 face_authority／responsibility_confirmed
```

### 三個刻意的選擇

```text
1 `FACE_UNEVALUATED`（旗標關／不在 allowlist ⇒ resolver 根本沒跑）維持既有行為立即進場。
  ⚠️ 若把它也當成無 authority，allowlist 外的**所有**面向會被一次改掉語義——
     而 scoped rollout 的設計意圖就是只在 allowlist 內生效。
2 進場程式抽成一個 helper 共用。抽出的理由不是省行數，是**避免相容性進場另寫一份**：
  兩份程式遲早在 telemetry 或交易面向前置上分岔，而分岔處正是
  「相容性 Face 被誤記成 responsibility-confirmed」的地方。
3 `.stay` 不刪（compatibility control flow 仍需要），改以機器 guard 守：
  `test_face_precedence_req.py` 掃 `routers/chat.py` 的 AST，禁止任何 `.stay` 讀取，
  並附**正對照組**（餵植入 `.stay` 的合成程式，掃描器必須抓到）。
```

## 驗證

### 決定性等價（本次的主要證據）

⚠️ 不用「routing 看起來差不多」推論，直接鎖 compatibility contract。
`test_returned_config_is_identical_to_pre_change_behaviour` 枚舉五種 resolver 結果形狀：

```text
model_commit       → committed_config   ✅
fail_open_commit   → committed_config   ✅  ← 第一格與舊碼相同，只有 authority 是新的
no_commit          → None               ✅
resolver_exception → seed cfg           ✅
flag_off           → seed cfg           ✅
```

### Mutation（三個不同失敗模式，全部被殺）

```text
M3 重新用 stay 布林判 authority                    → 3 條轉紅（含四列表第 3 列）
M4 technical fail-open 冒充 authoritative stay      → 1 條轉紅
M5 為了阻止越權乾脆把 compatibility candidate 丟掉  → 2 條轉紅
⇒ 測試同時保護「不能越權」與「不能破壞舊 compatibility」兩個方向。
```

### 套件

```text
unit         1466 / 0（刀 A 前 1448）
integration  235 / 6（乾淨基線 236 / 6）
⚠️ integration 的 passed 差 1 **不構成**證據——見裁定 001-B ③ 的非決定性規約。
```

### production 真入口（讀取級）

```text
POST /api/v1/message（vendor 2／property_manager／b2b／role 20151）四句 canary 語料
四句全部進面向；commit_source 皆 model、has_commit_authority=true
⇒ 刀 A 未改變這些 authoritative 進場的行為
```

## 未解、且**不在**本刀射程

```text
P2.5 production reachability：目前**不重現**（見交接與 trace 記錄）。
  舊的兩個歸因（gate 消滅 nomination／0.740 < 0.75）皆已作廢，
  要再宣稱它存在必須先從真入口重現。
FORM_TRIGGER_THRESHOLD 的 nomination eligibility 屬 `retrieval-decision-layer`，
  ⛔ 不得在 authority 這條線順手調成 0.73 或繞過門檻。
test harness debt：本套件名為 integration regression suite，實含 live LLM
  nondeterminism；應提供可切換的 deterministic evaluator。已登記，不阻塞。
```
