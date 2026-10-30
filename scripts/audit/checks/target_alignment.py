#!/usr/bin/env python3
"""不變量 47：**現行文件不得讓人偏離目標架構**（DSP-130、DSP-131）。

業主 2026-10-30：「我不要有誤導資訊讓你不去對其」「你這種改法 只要有 AI 讀錯部分 就又歪了」。
只靠讀者讀對不夠，下列事項由程式核對：

## 不變量陳述

> ① `docs/architecture/TARGET_ARCHITECTURE.md` 含全部核心句（定位、入口、工具搬出、雙向分工）。
> ② 現況文件清單 `CURRENT_DOCS` 每份都有目標宣告 `BANNER`。少一份就 FAIL。
> ③ 這些文件與 `DIRECTION_ONLY_DOCS` 沒有把 `/mcp` 寫成最終入口或新串接方向的句子（`FORBIDDEN`）。
> ④ `.kiro` 目標正本不得再放一份架構：分工表、原則全文、目標架構圖只留在 docs。
> ⑤ `CLAUDE.md` 與 `.claude/MAP.md` 指向架構正本；`.claude/prerequisites.json` 規定改對話程式
>    與寫計畫之前要先讀完架構正本。
> ⑥ `MISPOINTER_FILES` 不得把 `.kiro` 寫成架構或分工來源（`MISPOINTER`）。
> ⑦ 給 JGB 的規格書要寫明面板改接專用對話 API，⛔ 寫 `/mcp` 當上線網址。

退出碼：0 通過；1 FAIL；2 前置條件失敗（讀不到檔案，⛔ 靜默跳過）。
用法：python3 scripts/audit/checks/target_alignment.py [--self-test]
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
TARGET = "docs/architecture/TARGET_ARCHITECTURE.md"
WORK_LINE = ".kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md"
HANDOFF = ".kiro/specs/agentic-mcp-orchestration/HANDOFF-20261018.md"
BANNER = "本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統"
CURRENT_DOCS = (
    "docs/architecture-overview.md",
    "docs/architecture/AGENTIC_MCP_ARCHITECTURE.md",
    "docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md",
    "docs/architecture/DATABASE_SCHEMA.md",
    "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/architecture/agent-path-retired-symbols.md",
    "docs/architecture/facet-architecture.md",
    "docs/architecture/retriever-pipeline.md",
    "docs/api/conversational-api.md",
    "docs/api/jgb2-web-assistant-integration.md",
    "docs/api/mcp-facade.md",
    "docs/guides/development/how-to-add-a-query-capability.md",
    "docs/guides/getting-started/QUICKSTART.md",
    "docs/jgb2-chat-integration.md",
    "README.md",
    "rag-orchestrator/README.md",
    ".kiro/steering/product.md",
    ".kiro/steering/tech.md",
    ".kiro/steering/structure.md",
    ".kiro/steering/dialogue.md",
)
CORE_SENTENCES = (
    "本系統是對話服務，不是 MCP 系統",
    "`/mcp` 不是最終的對話入口",
    "JGB 工具一定要搬出去",
    "程式重新理解使用者的話",
    "任何計畫或改動讓 AI 決定上表「程式」列的下一步",
)
FORBIDDEN = (
    r"(請|應該?|一律|統一|永遠)(都)?(改)?(走|使用|用|接|打)\s*`?/mcp",
    r"新(的)?(串接|呼叫端).{0,8}(請|應該?|一律|接|走).{0,8}/mcp",
    r"(最終|長期|正式|未來)的?(對話)?入口(仍|將)?(是|為|維持|保持)\s*`?/mcp",
    r"/mcp`?.{0,6}(長期|永遠|繼續|一直).{0,6}(作為|當|是|為).{0,4}入口",
    r"(?<!不)(是|為)(最終|長期)的?(對話)?入口",
    r"最終入口[：:]\s*`?/mcp",
    r"以後(都|一律)?走\s*`?/mcp",
    r"請使用\s*`?/mcp",
    r"(?<!不)(?<!還)工具(留|放|維持)在本系統",
    r"(工具|JGB).{0,6}不(用|必|需要?)?搬",
    r"不(需要|用|必)(再)?(對齊|改走|改接)",
    r"對齊.{0,6}(可以?)?(等|延到|留到).{0,4}上線後",
    r"專用對話 ?API.{0,8}(不急|取消|不做|不需要)",
    r"(本系統|這個系統|系統本身)(就)?(?<!不)是\s*MCP\s*系統",
)
#: 同樣的意思，寫明是現況就放行。
FORBIDDEN_UNLESS_STATUS = (
    r"/mcp`?\s*(是|為)唯一的?(對外|對話)?的?入口",
    r"(都|統一)(改)?(走|使用|接)\s*`?/mcp",
    r"/mcp`?\s*就是.{0,4}入口",
)
STATUS_WORDS = ("現況", "現行", "現在", "目前")
#: 只該在 docs 架構正本出現的內容，出現在 `.kiro` 目標正本就是又長出第二份。
WORK_LINE_FORBIDDEN = (
    "| 環節 | 誰決定下一步",
    "**混合式：理解交給 AI",
    "JGB MCP server\n  │",
    "本檔是目標唯一正本",
    "本檔回答「對話線應該長什麼樣」",
)
#: 把 `.kiro` 當架構或分工來源的寫法，新視窗只讀這一句就會走錯。
MISPOINTER = re.compile(r"(架構|分工)[^。；，\n]{0,24}(看|以)\s*`?[^\s`]*architecture-target")
MISPOINTER_FILES = (HANDOFF, ".claude/MAP.md", "CLAUDE.md")
#: 給 JGB 的規格書要讓人看得到面板改接專用對話 API，不是合入現行 client 就上線。
JGB_SPEC = ".kiro/specs/agentic-mcp-orchestration/jgb-spec-structured-card-draft-20261019.md"
JGB_SPEC_REQUIRED = "改接 AIChatbot 的專用對話 API"
JGB_SPEC_FORBIDDEN = (
    "ASSISTANT_AGENT_URL=https://chatai.jgbsmart.com/rag-api/mcp",
    "帶 `image_urls`",
    "專用上傳網域名稱",
    "`image` 鍵",
)
#: 這些也會被當依據讀，一樣不得把 `/mcp` 寫成方向；它們不必有目標宣告。
DIRECTION_ONLY_DOCS = (
    "CLAUDE.md",
    HANDOFF,
    JGB_SPEC,
    WORK_LINE,
    ".claude/MAP.md",
    "docs/INDEX.md",
    "docs/README.md",
    "docs/api/README.md",
    "docs/api/API_REFERENCE_PHASE1.md",
    "docs/guides/api/api-path-conventions.md",
    ".kiro/steering/testing-code.md",
    ".kiro/steering/debugging-workflow.md",
)
POINTER_FILES = ("CLAUDE.md", ".claude/MAP.md")
PREREQ_FILE = ".claude/prerequisites.json"
PREREQ_KEYS = (
    "rag-orchestrator/services/agent/**",
    "rag-orchestrator/routers/**",
    "rag-orchestrator/app.py",
    "rag-orchestrator/services/jgb/**",
    "rag-orchestrator/services/jgb_system_api.py",
    "rag-orchestrator/services/presales_gate.py",
    "rag-orchestrator/services/form_contract.py",
    ".kiro/specs/agentic-mcp-orchestration/plan-*.md",
    ".kiro/specs/agentic-mcp-orchestration/acceptance-*.md",
)


def forbidden_lines(text):
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        hit = any(re.search(pat, line) for pat in FORBIDDEN)
        if not hit and not any(word in line for word in STATUS_WORDS):
            hit = any(re.search(pat, line) for pat in FORBIDDEN_UNLESS_STATUS)
        if hit:
            out.append((no, line.strip()[:100]))
    return out


def run_checks(read):
    """read(rel) 回檔案內容；讀不到丟 OSError。"""
    problems = []
    target = read(TARGET)
    for sent in CORE_SENTENCES:
        if sent not in target:
            problems.append(f"{TARGET} 少核心句：{sent}")
    for rel in CURRENT_DOCS:
        text = read(rel)
        if BANNER not in text:
            problems.append(f"{rel} 少目標宣告")
        for no, line in forbidden_lines(text):
            problems.append(f"{rel}:{no} 把 /mcp 寫成方向：{line}")
    for rel in DIRECTION_ONLY_DOCS:
        for no, line in forbidden_lines(read(rel)):
            problems.append(f"{rel}:{no} 把 /mcp 寫成方向：{line}")
    work_line = read(WORK_LINE)
    for marker in WORK_LINE_FORBIDDEN:
        if marker in work_line:
            problems.append(f"{WORK_LINE} 又放了一份架構內容：{marker.splitlines()[0]}")
    for rel in MISPOINTER_FILES:
        hit = MISPOINTER.search(read(rel))
        if hit:
            problems.append(f"{rel} 把 .kiro 當架構來源：{hit.group(0)}")
    jgb_spec = read(JGB_SPEC)
    if JGB_SPEC_REQUIRED not in jgb_spec:
        problems.append(f"{JGB_SPEC} 少：{JGB_SPEC_REQUIRED}")
    for phrase in JGB_SPEC_FORBIDDEN:
        if phrase in jgb_spec:
            problems.append(f"{JGB_SPEC} 叫 JGB 接 /mcp：{phrase}")
    for rel in POINTER_FILES:
        if TARGET not in read(rel):
            problems.append(f"{rel} 沒有指向 {TARGET}")
    prereq = json.loads(read(PREREQ_FILE))
    for key in PREREQ_KEYS:
        paths = [row.get("path") for row in prereq.get(key, [])]
        if TARGET not in paths:
            problems.append(f"{PREREQ_FILE} 的 {key} 沒有要求先讀 {TARGET}")
    return problems


def _self_test():
    good = {
        TARGET: "\n".join(CORE_SENTENCES),
        WORK_LINE: "只寫驗收與路徑",
        HANDOFF: "架構與分工看正本",
        JGB_SPEC: JGB_SPEC_REQUIRED,
        "CLAUDE.md": TARGET,
        ".claude/MAP.md": TARGET,
        PREREQ_FILE: json.dumps({k: [{"path": TARGET}] for k in PREREQ_KEYS}),
    }
    for rel in CURRENT_DOCS:
        good[rel] = BANNER
    for rel in DIRECTION_ONLY_DOCS:
        good.setdefault(rel, "現況")

    def with_doc(rel, text):
        files = dict(good)
        files[rel] = text
        return run_checks(files.__getitem__)

    assert run_checks(good.__getitem__) == [], "正對照：全部齊備要 0 筆"
    assert any("少核心句" in p for p in with_doc(TARGET, "空")), "① 少核心句要 FAIL"
    assert any("少目標宣告" in p for p in with_doc(CURRENT_DOCS[0], "沒有宣告")), "② 少宣告要 FAIL"
    for bad in ("外部串接請改走 `/mcp` 門面", "最終入口是 `/mcp`", "`/mcp` 是最終對話入口", "最終入口：`/mcp`",
                "以後都走 `/mcp`", "請使用 `/mcp`", "JGB 工具留在本系統內即可", "不需要對齊 DSP-130",
                "`/mcp` 為唯一對話入口", "應該走 `/mcp`", "一律使用 `/mcp`", "統一走 `/mcp`", "最終入口仍為 /mcp",
                "站內幫手永遠走 /mcp", "本系統是 MCP 系統", "架構對齊可以等上線後", "新呼叫端接 `/mcp` 即可",
                "`/mcp` 將長期作為對話入口", "不必改走專用對話 API", "專用對話 API 不急"):
        hits = with_doc(CURRENT_DOCS[1], BANNER + "\n" + bad)
        assert any("寫成方向" in p for p in hits), f"③ 要抓到：{bad}"
    for ok in ("`/mcp` 不是最終入口", "現行對話入口是 `/mcp`", "專用對話 API 上線前，外部串接只能走 `/mcp` 門面",
               "現況：`/mcp` 是唯一的對話入口", "本系統是對話服務，不是 MCP 系統", "現行對話都走 `/mcp`"):
        assert with_doc(CURRENT_DOCS[1], BANNER + "\n" + ok) == [], f"③ 不該誤殺：{ok}"
    for rel in (HANDOFF, JGB_SPEC, ".claude/MAP.md", "docs/INDEX.md", ".kiro/steering/testing-code.md"):
        text = good[rel] + "\n最終入口是 `/mcp`"
        assert any("寫成方向" in p for p in with_doc(rel, text)), f"③ 要掃到：{rel}"
    assert any("又放了一份" in p for p in with_doc(WORK_LINE, "| 環節 | 誰決定下一步 |")), "④ 第二份架構要 FAIL"
    assert any("當架構來源" in p for p in with_doc(HANDOFF, "架構方向與目標看 `architecture-target-20261018.md`")), "⑥ 交接檔指錯要 FAIL"
    assert any("當架構來源" in p for p in with_doc(".claude/MAP.md", TARGET + "分工以 architecture-target-20261018.md 為準")), "⑥ MAP 指錯要 FAIL"
    assert not any("當架構來源" in p for p in with_doc(
        HANDOFF, f"架構與分工看 `{TARGET}`；工作線目標、驗收與路徑看 `architecture-target-20261018.md`")), "⑥ 不該誤殺"
    assert any("少：" in p for p in with_doc(JGB_SPEC, "合入 master")), "⑦ JGB 規格沒寫改接要 FAIL"
    assert any("叫 JGB 接" in p for p in with_doc(JGB_SPEC, JGB_SPEC_REQUIRED + JGB_SPEC_FORBIDDEN[0])), "⑦ 網址要 FAIL"
    assert any("沒有指向" in p for p in with_doc("CLAUDE.md", "無")), "⑤ 沒指向正本要 FAIL"
    assert any("沒有要求先讀" in p for p in with_doc(PREREQ_FILE, "{}")), "⑤ 沒有閱讀前提要 FAIL"
    print("self-test OK")


def main(argv):
    if "--self-test" in argv:
        _self_test()
        return 0

    def read(rel):
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            return fh.read()

    try:
        problems = run_checks(read)
    except (OSError, ValueError) as exc:
        print(f"❌ 前置條件失敗：{exc}")
        return 2
    if problems:
        for prob in problems:
            print(f"❌ {prob}")
        return 1
    print(f"✅ 目標架構對齊：{len(CURRENT_DOCS)} 份現況文件有宣告，{len(CORE_SENTENCES)} 句核心句在，"
          f"{len(PREREQ_KEYS)} 條閱讀前提在")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
