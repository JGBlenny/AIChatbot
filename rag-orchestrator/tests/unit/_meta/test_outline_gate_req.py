"""unit：`.claude/hooks/outline_gate.py` 五道判定自證（knowledge-outline-and-intent-architecture 任務 1.2｜R1.4）。

**驗什麼**：真的驅動 `outline_gate.py`（subprocess，非 import）——事件從 stdin 餵 JSON，
`CLAUDE_PROJECT_DIR` 指到 `tmp_path` 建的最小 repo（隔離真實 repo 狀態）。五道判定：

  1. PreToolUse（Edit|Write 命中受眾正本白名單）：缺 `diff_report` 或 `inputs_sha.canon` 與目標檔
     現 sha256 不符 ⇒ exit 2。
  2. PostToolUse：寫入後的正本結構檢查（front matter 七鍵、粗目/細目標題、細目 id 唯一、屬性區塊合法鍵）。
  3. PostToolUse：細目 `phrasings` 與凍結題集合（samples-manifest.json 各 set 的 `q`）NFKC 交集非空 ⇒ 擋。
  4. PostToolUse：正本或 `.claude/skills/outline-curation/runs/` 命中識別碼（email／手機／…）⇒ 擋。
  5. Stop：讀 `session.json`——`evals_ran` 非空時查 object-under-test 核可＋材料凍結；
     `answerability.needs_rubric_revision`／`cost.over_budget` 為 true 時各自擋（與 evals_ran 無關）。

⚠️ 假事件 `file_path` 一律用**絕對路徑**（1.1 實測：Claude Code 事件的 file_path 是絕對路徑）。
"""
import hashlib
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.4")]

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_HOOK_PATH = os.path.join(_REPO_ROOT, ".claude", "hooks", "outline_gate.py")

_VALID_CANON = """---
audience: prospect
version: 2026-09-06.1
reviewers: [owner]
language: zh-TW
budget_tokens: 10000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品基本盤 {#A}
### 系統定位與適用對象 {#prospect/A/positioning}
- phrasings:
  - {text: "你們系統適合我嗎", source: "question_summary:3585", status: approved}
- sources: [kb:3585]
- reviewed: {by: owner, at: 2026-09-06}
金箍棒是……可引用句。
"""

_FROZEN_PHRASING_TEXT = "你們系統適合我嗎"


# ---------------------------------------------------------------------------
# 建構 tmp repo 與驅動 hook 的共用工具
# ---------------------------------------------------------------------------

def _mk_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".claude" / "hooks" / "state" / "outline-gate").mkdir(parents=True)
    (repo / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (repo / "rag-orchestrator" / "canon").mkdir(parents=True)
    (repo / ".claude" / "skills" / "outline-curation" / "runs").mkdir(parents=True)
    return repo


def _write_manifest(repo, frozen_texts):
    eval_dir = repo / ".kiro" / "specs" / "agentic-mcp-orchestration" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    set_path = eval_dir / "test-set.json"
    set_path.write_text(
        json.dumps({"items": [{"q": t} for t in frozen_texts]}, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest = {
        "version": "test",
        "sets": {
            "test_set": {
                "available": True,
                "path": ".kiro/specs/agentic-mcp-orchestration/eval/test-set.json",
            }
        },
    }
    (eval_dir / "samples-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )


def _write_session(repo, data):
    state_path = repo / ".claude" / "hooks" / "state" / "outline-gate" / "session.json"
    state_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_hook(repo, event: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(event, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _pre_event(abs_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": abs_path},
        "session_id": "test-session",
    }


def _post_event(abs_path: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": abs_path},
        "session_id": "test-session",
    }


def _stop_event() -> dict:
    return {"hook_event_name": "Stop", "session_id": "test-session"}


# ---------------------------------------------------------------------------
# 判定 1：PreToolUse — diff_report／sha
# ---------------------------------------------------------------------------

def test_gate1_pretooluse_missing_diff_report_blocks(tmp_path):
    """紅：本 session 無 session.json（因此無 diff_report）⇒ exit 2。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 2
    assert proc.stderr  # 印一行原因


def test_gate1_pretooluse_sha_mismatch_blocks(tmp_path):
    """紅：diff_report.inputs_sha.canon 與目標檔現 sha256 不符 ⇒ exit 2（材料已過期）。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")
    _write_session(repo, {
        "diff_report": {"path": "x.json", "inputs_sha": {"canon": "0" * 64}},
    })

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 2
    assert proc.stderr


def test_gate1_pretooluse_matching_sha_allows(tmp_path):
    """綠：diff_report.inputs_sha.canon 等於現 sha256 ⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")
    _write_session(repo, {
        "diff_report": {"path": "x.json", "inputs_sha": {"canon": _sha256_text(_VALID_CANON)}},
    })

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 0


def test_gate1_pretooluse_new_file_empty_sha_allows(tmp_path):
    """綠：目標檔尚不存在（新建）＝現 sha 空字串，diff_report 也記空字串 ⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"  # 尚未建立
    _write_session(repo, {
        "diff_report": {"path": "x.json", "inputs_sha": {"canon": ""}},
    })

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# 判定 2：PostToolUse 結構檢查
# ---------------------------------------------------------------------------

def test_gate2_posttooluse_valid_structure_allows(tmp_path):
    """綠：七鍵齊全、粗目/細目、屬性鍵合法 ⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 0


def test_gate2_posttooluse_missing_front_matter_key_blocks(tmp_path):
    """紅：front matter 缺一鍵（business_types）⇒ exit 2。"""
    repo = _mk_repo(tmp_path)
    broken = _VALID_CANON.replace("business_types: [system_provider]\n", "")
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(broken, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "business_types" in proc.stderr


def test_gate2_posttooluse_duplicate_fine_id_blocks(tmp_path):
    """紅：兩個細目共用同一個 id ⇒ exit 2（含列號）。"""
    dup = _VALID_CANON + (
        "### 重複測試 {#prospect/A/positioning}\n"
        "- sources: [kb:9999]\n"
        "另一句可引用內容。\n"
    )
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(dup, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "重複" in proc.stderr


def test_gate2_posttooluse_bad_fine_id_shape_blocks(tmp_path):
    """紅：細目 id 不符 `^[a-z_]+/[A-Z]/[a-z0-9-]+$` ⇒ exit 2。"""
    broken = _VALID_CANON.replace(
        "{#prospect/A/positioning}", "{#Prospect/A/Positioning}"
    )
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(broken, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2


def test_gate2_posttooluse_illegal_attr_key_blocks(tmp_path):
    """紅：屬性區塊出現不在白名單的鍵 ⇒ exit 2。"""
    broken = _VALID_CANON.replace(
        "- sources: [kb:3585]\n",
        "- sources: [kb:3585]\n- not_a_real_key: oops\n",
    )
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(broken, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "not_a_real_key" in proc.stderr


# ---------------------------------------------------------------------------
# 判定 3：講法 ∩ 凍結題
# ---------------------------------------------------------------------------

def test_gate3_posttooluse_frozen_phrasing_overlap_blocks(tmp_path):
    """紅：細目 phrasings 的句子與凍結題集合（NFKC 後）相同 ⇒ exit 2，印細目 id 不印題句。"""
    repo = _mk_repo(tmp_path)
    _write_manifest(repo, [_FROZEN_PHRASING_TEXT])
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")  # 本身就含 _FROZEN_PHRASING_TEXT

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "prospect/A/positioning" in proc.stderr
    assert _FROZEN_PHRASING_TEXT not in proc.stderr  # ⛔ 不印題句原文


def test_gate3_posttooluse_no_frozen_overlap_allows(tmp_path):
    """綠：凍結題集合存在但與講法無交集 ⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    _write_manifest(repo, ["跟正本講法完全不同的一句話"])
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 0


def test_gate3_nfkc_normalization_catches_width_variant(tmp_path):
    """紅：凍結題與講法只差全形/半形或前後空白，NFKC 正規化後仍須判定為交集。"""
    repo = _mk_repo(tmp_path)
    # 全形問號＋前後空白 vs. 正本內半形/無空白版本
    _write_manifest(repo, [f"  {_FROZEN_PHRASING_TEXT}  "])
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# 判定 4：識別碼掃描
# ---------------------------------------------------------------------------

def test_gate4_posttooluse_identifier_email_blocks(tmp_path):
    """紅：正本內文塞一個 email ⇒ exit 2，印類別＋列號、不印內容。"""
    repo = _mk_repo(tmp_path)
    leaked = _VALID_CANON + "聯絡窗口 foo.bar@example.com 可協助處理。\n"
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(leaked, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "email" in proc.stderr
    assert "foo.bar@example.com" not in proc.stderr


def test_gate4_posttooluse_identifier_phone_blocks(tmp_path):
    """紅：正本內文塞一個台灣手機號碼 ⇒ exit 2。"""
    repo = _mk_repo(tmp_path)
    leaked = _VALID_CANON + "請撥打 0912345678 聯繫窗口。\n"
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(leaked, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "phone" in proc.stderr
    assert "0912345678" not in proc.stderr


def test_gate4_runs_path_identifier_blocks(tmp_path):
    """紅：非正本但命中 `.claude/skills/outline-curation/runs/` 的檔案，識別碼掃描同樣適用。"""
    repo = _mk_repo(tmp_path)
    target = repo / ".claude" / "skills" / "outline-curation" / "runs" / "run1.md"
    target.write_text("原始候選：foo.bar@example.com\n", encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "email" in proc.stderr


def test_gate4_posttooluse_identifier_clean_allows(tmp_path):
    """綠：正本乾淨（無任何識別碼類別命中）⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# 判定 5：Stop
# ---------------------------------------------------------------------------

def test_gate5_stop_missing_session_allows(tmp_path):
    """綠：本 session 沒有 session.json（沒跑 skill）⇒ Stop 放行、exit 0。"""
    repo = _mk_repo(tmp_path)

    proc = run_hook(repo, _stop_event())

    assert proc.returncode == 0


def test_gate5_stop_needs_rubric_revision_blocks(tmp_path):
    """紅：answerability.needs_rubric_revision=true ⇒ exit 2 + stdout JSON {"decision":"block",...}。
    （正對照：與 test_gate5_stop_missing_session_allows 同檔案佈局，只加這個欄位就必擋。）
    """
    repo = _mk_repo(tmp_path)
    _write_session(repo, {
        "evals_ran": [],
        "answerability": {"path": "a.json", "needs_rubric_revision": True},
        "cost": {"path": "c.json", "over_budget": False},
    })

    proc = run_hook(repo, _stop_event())

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "block"
    assert payload["reason"]


def test_gate5_stop_over_budget_blocks(tmp_path):
    """紅：cost.over_budget=true ⇒ exit 2（與 evals_ran 是否跑過無關）。"""
    repo = _mk_repo(tmp_path)
    _write_session(repo, {
        "evals_ran": [],
        "answerability": {"path": "a.json", "needs_rubric_revision": False},
        "cost": {"path": "c.json", "over_budget": True},
    })

    proc = run_hook(repo, _stop_event())

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "block"


def test_gate5_stop_evals_ran_missing_object_under_test_blocks(tmp_path):
    """紅：evals_ran 非空但 object_under_test_path 缺／未核可 ⇒ exit 2。"""
    repo = _mk_repo(tmp_path)
    _write_session(repo, {
        "evals_ran": ["agent_eval"],
        "materials_frozen": True,
        "object_under_test_path": "inputs/does-not-exist.md",
        "answerability": {"path": "a.json", "needs_rubric_revision": False},
        "cost": {"path": "c.json", "over_budget": False},
    })

    proc = run_hook(repo, _stop_event())

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "block"


def test_gate5_stop_compliant_allows(tmp_path):
    """綠：evals_ran 跑過、object-under-test 存在且已核可、材料已凍結、rubric／cost 都正常 ⇒ exit 0。"""
    repo = _mk_repo(tmp_path)
    oud_dir = repo / "inputs"
    oud_dir.mkdir(parents=True, exist_ok=True)
    (oud_dir / "object-under-test.md").write_text("核可：owner\n", encoding="utf-8")
    _write_session(repo, {
        "evals_ran": ["agent_eval"],
        "materials_frozen": True,
        "object_under_test_path": "inputs/object-under-test.md",
        "answerability": {"path": "a.json", "needs_rubric_revision": False},
        "cost": {"path": "c.json", "over_budget": False},
    })

    proc = run_hook(repo, _stop_event())

    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# 負對照：非目標路徑一律不命中、零輸出零副作用
# ---------------------------------------------------------------------------

def test_negative_control_repo_root_canon_not_matched(tmp_path):
    """負對照：repo 根 `canon/prospect.md`（⛔ 非 `rag-orchestrator/canon/`）⇒ 不命中，exit 0 無輸出。"""
    repo = _mk_repo(tmp_path)
    (repo / "canon").mkdir(parents=True, exist_ok=True)
    target = repo / "canon" / "prospect.md"
    target.write_text("不合法但不該被檢查", encoding="utf-8")
    # 刻意不建 session.json：若誤判命中，PreToolUse 會因缺 diff_report 而紅——用這個當放大鏡。

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_negative_control_readme_not_matched(tmp_path):
    """負對照：`rag-orchestrator/canon/README.md` ⇒ 不命中（白名單排除檔名）。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "README.md"
    target.write_text("占位", encoding="utf-8")

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_negative_control_non_canon_path_not_matched(tmp_path):
    """負對照：非目標路徑（如 services/x.py）⇒ 不命中，PostToolUse 也零輸出零副作用。"""
    repo = _mk_repo(tmp_path)
    (repo / "rag-orchestrator" / "services").mkdir(parents=True, exist_ok=True)
    target = repo / "rag-orchestrator" / "services" / "x.py"
    target.write_text("print('hi')\n", encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_negative_control_positive_control_target_path_does_hit(tmp_path):
    """正對照（配對上面三個負對照）：同樣缺 session.json，但目標路徑真的是白名單內 ⇒ 必紅。
    證明「不命中」不是因為 PreToolUse 本身失靈。
    """
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON, encoding="utf-8")

    proc = run_hook(repo, _pre_event(str(target)))

    assert proc.returncode == 2
    assert proc.stderr != ""


# ---------------------------------------------------------------------------
# verifier 2026-09-06 回饋（F1／F3／F4）——修正後補的回歸鎖
# ---------------------------------------------------------------------------

import re as _re


def test_f1_canon_date_and_budget_tokens_are_not_tax_id(tmp_path):
    """綠：正本內文的 8 位日期（20260906）與 front matter 的 budget_tokens 大數字不得被當統編誤擋（F1，P2）。"""
    repo = _mk_repo(tmp_path)
    text = _re.sub(r"budget_tokens:.*", "budget_tokens: 12000000", _VALID_CANON)
    text += "本版於 20260906 定案。\n"
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(text, encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""


def test_f1_positive_control_real_tax_id_still_blocks(tmp_path):
    """正對照：非日期形狀的 8 位數（12345678）仍以 tax_id 擋——證明上一條的綠不是把掃描關掉。"""
    repo = _mk_repo(tmp_path)
    target = repo / "rag-orchestrator" / "canon" / "prospect.md"
    target.write_text(_VALID_CANON + "統編 12345678 開立發票。\n", encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "tax_id" in proc.stderr


def test_f3_non_object_json_event_is_silent(tmp_path):
    """綠：stdin 是合法 JSON 但非物件（[1,2]）⇒ exit 0、零輸出，與壞 JSON 同款（F3）。"""
    repo = _mk_repo(tmp_path)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    proc = subprocess.run([sys.executable, _HOOK_PATH], input="[1,2]",
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    assert proc.stdout == "" and proc.stderr == ""


def test_f4_stop_block_reason_also_on_stderr(tmp_path):
    """Stop 擋回合時 exit 2 的 harness 契約是讀 stderr：理由必須同時寫到 stderr（F4）。"""
    repo = _mk_repo(tmp_path)
    _write_session(repo, {
        "evals_ran": [],
        "answerability": {"path": "a.json", "needs_rubric_revision": True},
        "cost": {"path": "c.json", "over_budget": False},
    })
    proc = run_hook(repo, _stop_event())
    assert proc.returncode == 2
    assert "needs_rubric_revision" in proc.stderr
    assert json.loads(proc.stdout)["decision"] == "block"


def test_a1_runs_file_with_front_matter_still_scanned(tmp_path):
    """紅→綠（verifier A1）：`runs/` 產物以 `---` 開頭時識別碼掃描不得跳過該區段——front matter 豁免只屬正本。"""
    repo = _mk_repo(tmp_path)
    runs = repo / ".claude" / "skills" / "outline-curation" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    target = runs / "note.md"
    target.write_text("---\ncontact: abc@example.com\n---\n乾淨內文\n", encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "email" in proc.stderr


def test_a1_runs_file_with_unclosed_front_matter_still_scanned(tmp_path):
    """綠（verifier 第 3 輪指出無鎖）：`runs/` 檔首行 `---` 且從未閉合，其後識別碼仍要掃到——舊行為會整檔跳過。"""
    repo = _mk_repo(tmp_path)
    runs = repo / ".claude" / "skills" / "outline-curation" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    target = runs / "unclosed.md"
    target.write_text("---\ntitle: x\nowner_email: bob@example.com\n", encoding="utf-8")

    proc = run_hook(repo, _post_event(str(target)))

    assert proc.returncode == 2
    assert "email" in proc.stderr
