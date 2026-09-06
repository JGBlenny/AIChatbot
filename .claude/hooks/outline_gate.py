#!/usr/bin/env python3
"""outline_gate.py — repo 層 hook：正本流程閘門（knowledge-outline-and-intent-architecture 任務 1.2）。

五道判定（design 元件 3；tasks 1.2）：
  1. PreToolUse（Edit|Write 命中受眾正本白名單）：本 session 狀態檔須有 diff_report 且其
     inputs_sha.canon == 目標檔「動作前」的現 sha256（不存在的新檔以空字串比對），否則 exit 2 擋寫。
  2. PostToolUse（同白名單）：寫入後的檔案做結構檢查（front matter 七鍵、粗目/細目標題與 id、
     屬性區塊合法鍵）；任一錯 exit 2 印錯誤（⛔ 不還原檔案）。
  3. PostToolUse：細目 phrasings 各句與凍結題集合（samples-manifest.json 各 set）NFKC 正規化後
     交集非空 ⇒ exit 2（印命中的細目 id，⛔ 不印題句原文）。
  4. PostToolUse：命中 `.claude/skills/outline-curation/runs/` 或正本白名單 ⇒ 識別碼掃描
     （email／電話／LINE id／統編／車牌／合約或帳單編號／金額+日期），命中 ⇒ exit 2（類別＋列號）。
  5. Stop：讀 session.json，evals_ran 非空時檢查 object_under_test 核可、materials_frozen、
     answerability.needs_rubric_revision、cost.over_budget；擋回合結束並印 JSON
     {"decision":"block","reason":"..."}（Stop hook 契約）。

**只在目標路徑命中時動作，其餘一律 exit 0 且不印任何東西**（噪音會訓練人略過）。
零第三方依賴（只用標準庫）；⛔ 不讀網路、⛔ 不讀 `.env`、⛔ 不讀事件的 `transcript_path` 內容。
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# 路徑與白名單
# ---------------------------------------------------------------------------

# design 元件 3／tasks 1.2：受眾正本白名單，⛔ 不含 README.md。
CANON_RE = re.compile(r'^rag-orchestrator/canon/[a-z_]+(-[a-z_]+)*\.md$')
RUNS_RE = re.compile(r'^\.claude/skills/outline-curation/runs/')

STATE_REL = os.path.join(".claude", "hooks", "state", "outline-gate", "session.json")

FRONT_MATTER_KEYS = (
    "audience", "version", "reviewers", "language",
    "budget_tokens", "target_user", "business_types",
)

# 細目 id：^<audience>/<粗目碼 A-Z>/<slug>$
FINE_ID_RE = re.compile(r'^[a-z_]+/[A-Z]/[a-z0-9-]+$')
COARSE_HEADING_RE = re.compile(r'^##\s+.+\{#([A-Z])\}\s*$')
FINE_HEADING_RE = re.compile(r'^###\s+.+\{#([^}]+)\}\s*$')

# 細目屬性區塊允許的鍵（brief／design 元件 4 FineItem 欄位）
ATTR_KEYS = (
    "phrasings", "sources", "reviewed", "see_also", "policy", "policy_ref",
    "target_user", "business_types", "categories", "instance_applicability",
)
ATTR_LINE_RE = re.compile(r'^-\s*(' + "|".join(ATTR_KEYS) + r')\s*:')
# 屬性子項延續行（例如 phrasings 底下的 "  - {text: ...}"）
ATTR_CONTINUATION_RE = re.compile(r'^\s+-\s')

# 識別碼掃描（N3）——封閉清單，各類獨立 regex。
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
# 2026-09-06 實測：sha256 摘要（…cf017929054d…）被當成電話——舊版邊界 `(?<!\d)…(?!\d)` 只擋
# 數字相鄰，十六進位字串裡夾著的 9 位數會整批誤判。邊界改為排除**十六進位字元**。
# ⛔ 不用「排除全部英數」：`PHONE_RE` 同時被 `phrasing_map.deidentify` 拿去做去識別，
# 英數邊界會漏掉 `TEL0912345678` 這種緊貼英文字的真號碼（該側必須「寧可多遮」）。
# ⚠️ 已知取捨：號碼緊貼 a–f 字母（`0912345678a`）會漏——中文語境不現實。
PHONE_RE = re.compile(r'(?<![0-9A-Fa-f])(0\d{1,2}-?\d{6,8}|09\d{8})(?![0-9A-Fa-f])')
LINE_ID_RE = re.compile(r'@[A-Za-z0-9_.-]{3,}')
# 統編＝**獨立**的 8 位數：前後都不得是英數（⛔ 舊版 `(?<!\d)\d{8}(?!\d)` 只擋數字相鄰，
# sha256 十六進位字串裡夾著的 8 位數 `…133c28659231b098…` 會整批誤判）。
# 另外兩道排除**不寫進 regex**，放在 `check_identifiers`：
#   a. 看起來是日期的 8 位數（`_looks_like_date8`：19xx／20xx＋合法月日）
#   b. JSON／YAML 計數欄位的裸數值（`NUMERIC_FIELD_KEY_RE`，如 `"prompt_tokens": 10848979`）
# 理由：skill（`.claude/skills/outline-curation/scripts/phrasing_map.py`）直接 import 這支 regex 做
# 去識別，那一側要維持「寧可多遮」——排除留在 hook 這一側，skill 因此永遠 ⊇ hook（同一把尺、方向只更嚴）。
TAX_ID_RE = re.compile(r'(?<![0-9A-Za-z])\d{8}(?![0-9A-Za-z])')

# 計數／金額／耗時欄位的鍵名白名單：**只有這些鍵**的裸數值不算統編。
# ⛔ 不用「凡是 `key: 數字` 一律放行」——`"tax_id": 12345678` 這種真外洩正好就是裸數值，
# 放行等於把統編這一面關掉。鍵名必須整段命中（`prompt_tokens` ✓、`discount` ✗）。
NUMERIC_FIELD_KEY_RE = re.compile(
    r'(?:^|[\s{,])"?(?:[A-Za-z0-9.\-]+_)*'
    r'(?:tokens?|count|usd|cost|bytes?|size|length|budget|total|elapsed|duration|ms|chars)'
    r'"?\s*:\s*$'
)

# 車牌（台灣現行式樣）：2–3 英文字母＋4 數字（`AB-1234`／`ABC-1234`），或 4 數字＋2 字母（`1234-AB`）。
# ⛔ 不含 3 字母＋3 數字——那不是任何一種車牌式樣，卻正是文件編號（`DSP-012`／`R2-123`）的形狀。
PLATE_RE = re.compile(r'(?<![A-Za-z0-9])(?:[A-Z]{2,3}-?\d{4}|\d{4}-?[A-Z]{2})(?![A-Za-z0-9])')

# 合約號／帳單號，兩種形狀（聯集）：
#   a. 標籤在前：`合約號 12345`／`帳單編號12345`（標籤與數字之間只准空白與 `:：#＃`）
#   b. 數字在前：**≥6 位**且**緊貼**標籤：`123456帳單`
# ⛔ 舊版 `\d{4,}\s*(?:合約|帳單|編號|號)` 允許「4 位數＋空白＋標籤」，會把
# 「<kb id> 帳單版面自訂」這種引用當成帳單號；kb id 是 4 位數、後面接的是主題詞不是編號。
NUMBER_LABEL_RE = re.compile(
    r'(?:合約|帳單)(?:編號|號碼|序號|號)?\s*[:：#＃]?\s*\d{4,}'
    r'|\d{6,}(?:合約|帳單|編號|號)'
)
AMOUNT_DATE_RE = re.compile(
    r'(?:NT\$|\$|新台幣)?\s*\d{2,}(?:,\d{3})*\s*元.{0,20}?\d{2,4}[-/年]\d{1,2}[-/月]\d{1,2}'
)

IDENTIFIER_CATEGORIES = (
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("line_id", LINE_ID_RE),
    ("tax_id", TAX_ID_RE),
    ("plate", PLATE_RE),
    ("number_label", NUMBER_LABEL_RE),
    ("amount_date", AMOUNT_DATE_RE),
)


# ---------------------------------------------------------------------------
# 共用工具
# ---------------------------------------------------------------------------

def _find_project_dir() -> str:
    """CLAUDE_PROJECT_DIR 缺時，從 cwd 往上找 .claude/settings.json 當根；找不到回空字串。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    cur = os.getcwd()
    while True:
        if os.path.isfile(os.path.join(cur, ".claude", "settings.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return ""
        cur = parent


def _read_event() -> dict:
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        ev = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    # verifier F3：合法 JSON 但非物件（如 [1,2]）也要靜默放行，⛔ 不得 traceback
    return ev if isinstance(ev, dict) else {}


def _rel_path(file_path: str, project_dir: str) -> str:
    """絕對/相對事件 file_path -> 以 project_dir 為基準的相對路徑（正斜線）。"""
    if not file_path:
        return ""
    base = project_dir or os.getcwd()
    try:
        rel = os.path.relpath(file_path, base)
    except ValueError:
        # 不同磁碟機代號等，relpath 會丟例外；退回原字串。
        rel = file_path
    return rel.replace(os.sep, "/")


def _is_canon_target(rel: str) -> bool:
    if not CANON_RE.match(rel):
        return False
    if os.path.basename(rel) == "README.md":
        return False
    return True


def _sha256_file(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _state_path(project_dir: str) -> str:
    return os.path.join(project_dir or os.getcwd(), STATE_REL)


def _load_state(project_dir: str) -> Optional[dict]:
    path = _state_path(project_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _nfkc_norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def _collect_q(obj, out: list) -> None:
    """遞迴收集 manifest 各 set 檔內所有 "q" 鍵的字串值（各 set shape 不同，"q" 是共通題句欄）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "q" and isinstance(v, str):
                out.append(v)
            else:
                _collect_q(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_q(item, out)


def _frozen_questions(project_dir: str) -> set:
    manifest_path = os.path.join(
        project_dir or os.getcwd(),
        ".kiro", "specs", "agentic-mcp-orchestration", "eval", "samples-manifest.json",
    )
    if not os.path.isfile(manifest_path):
        return set()
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        return set()

    questions: list = []
    sets = manifest.get("sets") or {}
    for _, spec in sets.items():
        if not isinstance(spec, dict) or not spec.get("available"):
            continue
        set_path = spec.get("path")
        if not set_path:
            continue
        full = os.path.join(project_dir or os.getcwd(), set_path)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        _collect_q(data, questions)
    return {_nfkc_norm(q) for q in questions if q}


# ---------------------------------------------------------------------------
# 判定 1：PreToolUse
# ---------------------------------------------------------------------------

def check_pre_tool_use(project_dir: str, abs_path: str) -> int:
    state = _load_state(project_dir)
    if state is None or "diff_report" not in state:
        sys.stderr.write(
            "[outline_gate] PreToolUse 擋寫：本 session 缺 session.json 或無 diff_report"
            "（先跑 outline-curation skill 產出 diff report）\n"
        )
        return 2
    diff_report = state.get("diff_report") or {}
    inputs_sha = (diff_report.get("inputs_sha") or {}).get("canon")
    current_sha = _sha256_file(abs_path)
    if inputs_sha != current_sha:
        sys.stderr.write(
            "[outline_gate] PreToolUse 擋寫：diff_report.inputs_sha.canon 與目標檔現 sha256 不符"
            f"（diff_report={inputs_sha!r}, 現況={current_sha!r}）——材料已過期，須重新產生 diff report\n"
        )
        return 2
    return 0


# ---------------------------------------------------------------------------
# 判定 2：PostToolUse 結構檢查
# ---------------------------------------------------------------------------

def _parse_front_matter(lines: list) -> tuple:
    """回 (front_matter_dict_keys_present, body_start_index, errors)。"""
    errors = []
    if not lines or lines[0].strip() != "---":
        return set(), 0, ["缺 front matter（首行須為 ---）"]
    keys_present = set()
    idx = 1
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx]
        stripped = line.strip()
        if stripped and ":" in stripped:
            key = stripped.split(":", 1)[0].strip()
            keys_present.add(key)
        idx += 1
    if idx >= len(lines):
        errors.append("front matter 未閉合（缺結尾 ---）")
        return keys_present, idx, errors
    return keys_present, idx + 1, errors


def check_structure(abs_path: str) -> list:
    """回錯誤訊息清單（列號＋原因）；空清單＝通過。"""
    errors: list = []
    try:
        with open(abs_path, encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        return [f"讀檔失敗：{exc}"]

    lines = text.split("\n")
    keys_present, body_start, fm_errors = _parse_front_matter(lines)
    errors.extend(fm_errors)
    missing_keys = [k for k in FRONT_MATTER_KEYS if k not in keys_present]
    if missing_keys:
        errors.append(f"front matter 缺鍵：{', '.join(missing_keys)}")

    fine_ids_seen: dict = {}
    current_coarse = None
    in_fine = False

    for i in range(body_start, len(lines)):
        lineno = i + 1
        line = lines[i]

        coarse_m = COARSE_HEADING_RE.match(line)
        if coarse_m:
            current_coarse = coarse_m.group(1)
            in_fine = False
            continue

        fine_m = FINE_HEADING_RE.match(line)
        if fine_m:
            fid = fine_m.group(1)
            in_fine = True
            if not FINE_ID_RE.match(fid):
                errors.append(f"第 {lineno} 行：細目 id 不合法格式 {fid!r}")
            if fid in fine_ids_seen:
                errors.append(f"第 {lineno} 行：細目 id 重複 {fid!r}（首見於第 {fine_ids_seen[fid]} 行）")
            else:
                fine_ids_seen[fid] = lineno
            continue

        if not in_fine:
            continue
        if not line.strip():
            continue
        # 屬性區塊行：頂層鍵行或其延續行皆合法；其他非空行視為內容行（一句一行，不檢查）。
        if ATTR_LINE_RE.match(line) or ATTR_CONTINUATION_RE.match(line):
            continue
        # 一行純文字內容（正文），非屬性區塊，跳過不視為錯誤——
        # 只有「看起來是屬性行但鍵不在白名單」才判錯：`- xxx:` 開頭且 xxx 不在允許清單。
        stray_attr = re.match(r'^-\s*([a-zA-Z_]+)\s*:', line)
        if stray_attr and stray_attr.group(1) not in ATTR_KEYS:
            errors.append(f"第 {lineno} 行：屬性區塊出現不允許的鍵 {stray_attr.group(1)!r}")

    return errors


# ---------------------------------------------------------------------------
# 判定 3：講法 ∩ 凍結題
# ---------------------------------------------------------------------------

PHRASING_TEXT_RE = re.compile(r'text:\s*"((?:[^"\\]|\\.)*)"')


def check_frozen_overlap(abs_path: str, project_dir: str) -> list:
    """回命中的細目 id 清單（空＝無交集）。"""
    frozen = _frozen_questions(project_dir)
    if not frozen:
        return []
    try:
        with open(abs_path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return []

    hits: list = []
    current_fine_id = None
    for line in lines:
        fine_m = FINE_HEADING_RE.match(line)
        if fine_m:
            current_fine_id = fine_m.group(1)
            continue
        for m in PHRASING_TEXT_RE.finditer(line):
            text = m.group(1)
            if _nfkc_norm(text) in frozen:
                if current_fine_id and current_fine_id not in hits:
                    hits.append(current_fine_id)
    return hits


# ---------------------------------------------------------------------------
# 判定 4：識別碼掃描
# ---------------------------------------------------------------------------

def check_identifiers(abs_path: str, skip_front_matter: bool = False) -> list:
    """回 (類別, 列號) 清單；空＝乾淨。

    `skip_front_matter` 只對**正本**為 True（front matter 七鍵只有 version／budget 數字）；
    `runs/` 產物一律全掃（verifier A1：豁免外溢到 runs/ 會在個資主面開盲區）。"""
    try:
        with open(abs_path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return []
    hits: list = []
    in_front_matter = False
    for i, line in enumerate(lines, start=1):
        # verifier F1：front matter 只有 version／budget_tokens 這類數字，⛔ 不是識別碼面；整段跳過
        if skip_front_matter and i == 1 and line.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if line.strip() == "---":
                in_front_matter = False
            continue
        for category, pattern in IDENTIFIER_CATEGORIES:
            if category == "tax_id":
                if any(_is_tax_id_hit(line, m) for m in pattern.finditer(line)):
                    hits.append((category, i))
                continue
            if pattern.search(line):
                hits.append((category, i))
    return hits


def _looks_like_date8(s: str) -> bool:
    if len(s) != 8 or s[:2] not in ("19", "20"):
        return False
    mm, dd = int(s[4:6]), int(s[6:8])
    return 1 <= mm <= 12 and 1 <= dd <= 31


def _is_numeric_field_value(line: str, start: int) -> bool:
    """該 8 位數是否為 JSON／YAML 計數欄位的裸數值（`"prompt_tokens": 10848979`）。

    只看**緊接在數字之前**的那段前綴：鍵名要整段落在白名單，且中間只准空白與冒號。"""
    return bool(NUMERIC_FIELD_KEY_RE.search(line[:start]))


def _is_tax_id_hit(line: str, m) -> bool:
    """TAX_ID_RE 的命中是否真的算統編（兩道排除見 TAX_ID_RE 註解）。"""
    token = m.group(0)
    if _looks_like_date8(token):
        return False
    if _is_numeric_field_value(line, m.start()):
        return False
    return True


# ---------------------------------------------------------------------------
# 判定 5：Stop
# ---------------------------------------------------------------------------

APPROVAL_RE = re.compile(r'(核可|approved_by)\s*[：:]\s*(\S+)')


def _object_under_test_approved(project_dir: str, rel_path: str) -> bool:
    if not rel_path:
        return False
    full = os.path.join(project_dir or os.getcwd(), rel_path)
    if not os.path.isfile(full):
        return False
    try:
        with open(full, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    m = APPROVAL_RE.search(text)
    return bool(m and m.group(2).strip())


def check_stop(project_dir: str) -> list:
    """回未滿足條件的原因清單；空＝放行。"""
    state = _load_state(project_dir)
    if state is None:
        return []

    reasons: list = []
    evals_ran = state.get("evals_ran") or []
    if evals_ran:
        oud_path = state.get("object_under_test_path")
        if not _object_under_test_approved(project_dir, oud_path):
            reasons.append("object_under_test_path 不存在或核可欄為空")
        if state.get("materials_frozen") is not True:
            reasons.append("materials_frozen 非 true（材料 sha 尚未凍結）")

    answerability = state.get("answerability") or {}
    if answerability.get("needs_rubric_revision") is True:
        reasons.append("answerability.needs_rubric_revision=true（rubric 待修）")

    cost = state.get("cost") or {}
    if cost.get("over_budget") is True:
        reasons.append("cost.over_budget=true（預算超支）")

    return reasons


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ev = _read_event()
    hook_event = ev.get("hook_event_name")
    project_dir = _find_project_dir()

    if hook_event == "Stop":
        reasons = check_stop(project_dir)
        if reasons:
            payload = {"decision": "block", "reason": "；".join(reasons)}
            print(json.dumps(payload, ensure_ascii=False))
            # verifier F4：exit 2 時 harness 回饋給模型的是 stderr；理由兩邊都寫，⛔ 不能只靠 stdout JSON
            sys.stderr.write("[outline_gate] Stop 擋回合：" + "；".join(reasons) + "\n")
            return 2
        return 0

    tool_input = ev.get("tool_input") or {}
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not file_path:
        return 0

    rel = _rel_path(file_path, project_dir)
    is_canon = _is_canon_target(rel)
    is_runs = bool(RUNS_RE.match(rel))

    if not is_canon and not is_runs:
        return 0

    abs_path = file_path if os.path.isabs(file_path) else os.path.join(project_dir or os.getcwd(), file_path)

    if hook_event == "PreToolUse":
        if not is_canon:
            return 0
        return check_pre_tool_use(project_dir, abs_path)

    if hook_event == "PostToolUse":
        if is_canon:
            struct_errors = check_structure(abs_path)
            if struct_errors:
                sys.stderr.write("[outline_gate] PostToolUse 結構檢查失敗：\n")
                for e in struct_errors:
                    sys.stderr.write(f"  - {e}\n")
                return 2

            overlap_hits = check_frozen_overlap(abs_path, project_dir)
            if overlap_hits:
                sys.stderr.write(
                    "[outline_gate] PostToolUse 講法撞凍結題（命中細目 id，⛔ 不印題句原文）：\n"
                )
                for fid in overlap_hits:
                    sys.stderr.write(f"  - {fid}\n")
                return 2

        id_hits = check_identifiers(abs_path, skip_front_matter=is_canon)
        if id_hits:
            sys.stderr.write("[outline_gate] PostToolUse 識別碼掃描命中（類別＋列號，⛔ 不印內容）：\n")
            for category, lineno in id_hits:
                sys.stderr.write(f"  - {category} 第 {lineno} 行\n")
            return 2

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
