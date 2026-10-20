#!/usr/bin/env python3
"""不變量 45：**DSP-091 分工防偏離**（分工防偏離片 DG-4；計畫 plan-division-guard-20261020.md）。

DSP-091 規定「寫入全程、已選定的那筆紀錄、帶狀態的句子與確認卡、轉人規則、知識完全查無的出口、
唯讀查詢的查詢與篩選」由程式決定下一步。尚未接手的環節登記為已知偏離（KD），其餘由單元測試
`test_dsp091_division_contract_req.py` 保證；這條不變量補兩件事：

## 不變量陳述

> ① 靜態（不需 DB）：目標正本 `architecture-target-20261018.md` §3.1 表的 KD ID 集合與接手片，
>    ＝登記檔 `rag-orchestrator/tests/unit/agent/dsp091_known_deviations.py` 的 KD 集合與接手片。
>    不一致 ⇒ FAIL。
> ② 線上（近 7 天 `usage_events.decision_snapshot->'agent'->'violations'`，jsonb 陣列）：
>    有 `confirm_source:program_*` 樣本（正對照）時，`confirm_source:model:unregistered` 次數 > 0 ⇒ FAIL，
>    並列出 `trace_id`。無程式來源樣本 ⇒ 「未判」（非 0 退出碼 3，⛔ 當 PASS）。
> ③ 各來源計數與 `prose_confirm_suspect` 次數只印數字，不 WARN、不 FAIL、不設門檻（DSP-087）。

退出碼：0 通過；1 FAIL；2 前置條件失敗（讀不到正本／登記／DB，⛔ 靜默跳過）；3 未判。
用法：python3 scripts/audit/checks/division_guard.py [--self-test]
"""
import importlib.util
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
TARGET_DOC = os.path.join(REPO, ".kiro", "specs", "agentic-mcp-orchestration",
                          "architecture-target-20261018.md")
REGISTRY = os.path.join(REPO, "rag-orchestrator", "tests", "unit", "agent",
                        "dsp091_known_deviations.py")
PSQL = ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot", "-d", "aichatbot_admin",
        "-t", "-A", "-F", "\t"]
SRC_PREFIX = "confirm_source:"
WINDOW = "7 days"

OK, FAIL, PRECONDITION, UNJUDGED = 0, 1, 2, 3


class Precondition(Exception):
    pass


def load_registry(path=REGISTRY):
    if not os.path.isfile(path):
        raise Precondition(f"讀不到登記檔：{path}")
    spec = importlib.util.spec_from_file_location("dsp091_known_deviations", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {kd["id"]: kd["takeover"] for kd in mod.KNOWN_DEVIATIONS}


def parse_section_31(text):
    """目標正本 §3.1 表 ⇒ {ID: 接手片}（欄：ID | 偏離 | 分工表列 | 接手片）。"""
    m = re.search(r"^###\s+3\.1\b.*$", text, re.M)
    if not m:
        raise Precondition("目標正本找不到 §3.1 標題")
    rest = text[m.end():]
    nxt = re.search(r"^#{1,3}\s", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    rows = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"KD-\d+", cells[0]):
            rows[cells[0]] = cells[3]
    if not rows:
        raise Precondition("目標正本 §3.1 沒有任何 KD 列（表格式變了？）")
    return rows


def static_problems(doc_rows, reg_rows):
    bad = []
    for kd in sorted(set(doc_rows) - set(reg_rows)):
        bad.append(f"{kd} 在目標正本 §3.1 但不在登記檔")
    for kd in sorted(set(reg_rows) - set(doc_rows)):
        bad.append(f"{kd} 在登記檔但不在目標正本 §3.1")
    for kd in sorted(set(doc_rows) & set(reg_rows)):
        if doc_rows[kd] != reg_rows[kd]:
            bad.append(f"{kd} 接手片不一致：正本「{doc_rows[kd]}」≠ 登記「{reg_rows[kd]}」")
    return bad


def psql_query(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Precondition(f"無法執行 psql：{type(exc).__name__}")
    if out.returncode != 0:
        raise Precondition(f"psql 失敗（容器／DB 不在線？）：{out.stderr.strip()[:200]}")
    return [ln.split("\t") for ln in out.stdout.splitlines() if ln.strip()]


SQL_COUNTS = f"""
SELECT s, count(*) FROM (
  SELECT jsonb_array_elements_text(decision_snapshot->'agent'->'violations') AS s
  FROM usage_events
  WHERE ts > now() - interval '{WINDOW}'
    AND jsonb_typeof(decision_snapshot->'agent'->'violations') = 'array'
) t
WHERE s LIKE 'confirm_source:%' OR s = 'prose_confirm_suspect'
GROUP BY s ORDER BY s"""

SQL_UNREGISTERED = f"""
SELECT decision_snapshot->'agent'->>'trace_id' FROM usage_events
WHERE ts > now() - interval '{WINDOW}'
  AND decision_snapshot->'agent'->'violations' @> '["{SRC_PREFIX}model:unregistered"]'::jsonb
ORDER BY ts"""


def run_checks(doc_text, reg_rows, query=psql_query):
    """回 (退出碼, 輸出行)。`query` 可注入（self-test）。"""
    lines = []
    code = OK
    try:
        doc_rows = parse_section_31(doc_text)
    except Precondition as exc:
        return PRECONDITION, [f"❌ FAIL（前置條件）：{exc}"]
    bad = static_problems(doc_rows, reg_rows)
    if bad:
        code = FAIL
        lines.append("❌ FAIL：目標正本 §3.1 與 dsp091_known_deviations.py 不一致：")
        lines += [f"   - {b}" for b in bad]
    else:
        lines.append(f"✅ 靜態：目標正本 §3.1 與登記檔一致（{len(doc_rows)} 筆已知偏離：{', '.join(sorted(doc_rows))}）")
    try:
        counts = {row[0]: int(row[1]) for row in query(SQL_COUNTS)}
    except Precondition as exc:
        return PRECONDITION, lines + [f"❌ FAIL（前置條件）：{exc}"]
    program = sum(n for s, n in counts.items() if s.startswith(SRC_PREFIX + "program_"))
    unreg = counts.get(SRC_PREFIX + "model:unregistered", 0)
    for s in sorted(counts):
        if s.startswith(SRC_PREFIX):
            lines.append(f"ℹ️  近 7 天 {s} = {counts[s]}")
    lines.append(f"ℹ️  近 7 天 prose_confirm_suspect = {counts.get('prose_confirm_suspect', 0)}")
    if program == 0:
        lines.append(f"⚠️ 未判：近 7 天 無程式出卡樣本（confirm_source:program_* = 0；正對照未中，不能當 PASS）")
        return (code if code != OK else UNJUDGED), lines
    if unreg > 0:
        try:
            ids = [r[0] for r in query(SQL_UNREGISTERED)]
        except Precondition as exc:
            return PRECONDITION, lines + [f"❌ FAIL（前置條件）：{exc}"]
        lines.append(f"❌ FAIL：近 7 天 有 {unreg} 筆一般寫入回合由模型出卡（confirm_source:model:unregistered）；trace_id：")
        lines += [f"   - {i}" for i in ids]
        return FAIL, lines
    lines.append(f"✅ 線上：程式來源樣本 {program} 筆，unregistered = 0")
    return code, lines


def _self_test():
    reg = {"KD-1": "A-2", "KD-2": "文件回合"}
    doc = "### 3.1 仍由模型主導\n\n| ID | 偏離 | 分工表列 | 接手片 |\n|---|---|---|---|\n" \
          "| KD-1 | x | y | A-2 |\n| KD-2 | x | y | 文件回合 |\n\n## 4. 路徑\n| KD-9 | x | y | Z |\n"

    def q(counts, ids=()):
        def f(sql):
            if sql == SQL_COUNTS:
                return [[k, str(v)] for k, v in counts.items()]
            if sql == SQL_UNREGISTERED:
                return [[i] for i in ids]
            raise AssertionError(sql)
        return f

    good = {"confirm_source:program_draft": 3, "confirm_source:model:select_scope": 1,
            "prose_confirm_suspect": 2}
    failures = []

    def expect(name, got, want, must_have=()):
        code, lines = got
        text = "\n".join(lines)
        if code != want or any(m not in text for m in must_have):
            failures.append(f"{name}：退出碼 {code}（要 {want}）／輸出缺 {[m for m in must_have if m not in text]}\n{text}")

    expect("有樣本且 unregistered=0 ⇒ PASS", run_checks(doc, reg, q(good)), OK, ("unregistered = 0", "= 3"))
    bad_counts = dict(good, **{"confirm_source:model:unregistered": 2})
    expect("unregistered>0 ⇒ FAIL 列 trace_id",
           run_checks(doc, reg, q(bad_counts, ["tr-aaa", "tr-bbb"])), FAIL, ("tr-aaa", "tr-bbb"))
    expect("無樣本 ⇒ 未判", run_checks(doc, reg, q({})), UNJUDGED, ("未判",))
    only_model = {"confirm_source:model:flag_off": 4}
    expect("只有模型來源、無程式來源 ⇒ 未判（正對照未中）", run_checks(doc, reg, q(only_model)), UNJUDGED, ("未判",))
    expect("§3.1 缺 KD-2 ⇒ FAIL", run_checks(doc, dict(reg, **{"KD-3": "B"}), q(good)), FAIL, ("KD-3",))
    expect("登記缺 KD-2 ⇒ FAIL", run_checks(doc, {"KD-1": "A-2"}, q(good)), FAIL, ("KD-2",))
    expect("接手片不同 ⇒ FAIL", run_checks(doc, {"KD-1": "A-2", "KD-2": "B"}, q(good)), FAIL, ("接手片不一致",))
    expect("靜態 FAIL 壓過未判", run_checks(doc, {"KD-1": "A-2"}, q({})), FAIL, ("KD-2",))
    expect("正本沒有 §3.1 ⇒ 前置條件失敗", run_checks("# x\n", reg, q(good)), PRECONDITION, ("§3.1",))

    def boom(sql):
        raise Precondition("psql 失敗")
    expect("DB 不在線 ⇒ 前置條件失敗（⛔ 靜默）", run_checks(doc, reg, boom), PRECONDITION, ("前置條件",))
    # 正對照：§3.1 之後的下一節不被吞進表（KD-9 不能出現在解析結果）
    if "KD-9" in parse_section_31(doc):
        failures.append("解析越過 §3.1 的結尾")
    if failures:
        print("❌ 自我測試未過：")
        for f in failures:
            print(" -", f)
        return 1
    print("✅ self-test 通過（10 案：PASS／unregistered FAIL 列 trace_id／無樣本未判／只有模型來源未判／"
          "§3.1 與登記不一致 ×3／靜態壓過未判／無 §3.1／DB 不在線）")
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    try:
        with open(TARGET_DOC, encoding="utf-8") as fh:
            doc = fh.read()
        reg = load_registry()
    except (OSError, Precondition) as exc:
        print(f"❌ FAIL（前置條件）：{exc}")
        return PRECONDITION
    code, lines = run_checks(doc, reg)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
