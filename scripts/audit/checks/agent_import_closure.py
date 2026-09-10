#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新線／舊線 import 分桶與可刪清單（Plan `inputs/plan-legacy-isolation-20260910.md` §1.1）。

⛔ **射程聲明（別拿它當萬用保證）**：
1. 本檢查器**只看 import 邊**。⛔ 它看不見 `app.state` 注入的執行期耦合——
   例如 `services/agent/state_store.py` 曾經透過 `app.state.conversational_engine`
   呼叫 `ConversationalEngine.get_state/_start/_save/_close`，那條邊在這裡完全不可見。
   這類模組登記在 `RUNTIME_COUPLED`（第四桶），⛔ 不得進 legacy_only。
2. 它綠 **不構成**「該模組可安全刪除」的授權；刪除仍需人工複核＋實跑。

⚠️ **2026-09-10 舊鏈隔離 S3 完成後：本檢查器進入 RETIRED 狀態**（見
`retirement_status()`）。`LEGACY_SEEDS` 宣告的五個舊線進入點已隨 S3 全數刪除，
分桶（新線／舊線兩條線）的前提不再成立——`main()`／`self_test()` 偵測到這個狀態
會印明確訊息、exit 0，⛔ 不會假裝分桶結果仍然有效，也⛔ 不會因為 `LEGACY_SEEDS`
的模組消失而靜默略過變成「綠但瞎」（FATAL 只留給**部分**種子消失的不一致狀態）。
`scripts/audit/lists/*.txt` 停在退役當下最後一次核可的內容，當歷史記錄。

分桶（宣告式，⛔ 新線不用可達性算——`shadow`／`agent_rules`／`bootstrap`／`canon`
由 `app.py` 接線而非被 facade import，可達性會漏掉它們）：

    新線集合   := services/agent/**  ∪  {routers/agent_entry.py}       # 宣告
    新線閉包   := reach(新線集合)
    舊線可達   := reach(舊線進入點)
    舊線獨有   := 舊線可達 − 新線集合 − 新線閉包 − 第四桶
    第三方     := reach(其他 routers.*)                                 # 後台等第三個消費者
    可刪候選   := 舊線獨有 − 第三方 − 套件 __init__

用法：
    agent_import_closure.py            # 比對凍結清單（audit 模式，唯讀）
    agent_import_closure.py --regenerate   # 重寫 lists/*.txt（⛔ 需重走人工核可）
    agent_import_closure.py --self-test    # 檢查器自我測試
"""
from __future__ import annotations
import ast, os, sys, fnmatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "rag-orchestrator")
DATA = os.path.join(REPO, "scripts", "audit", "lists")

SKIP_PARTS = ("/tests/", "/__pycache__/", "/.venv/", "/.probe-run", "/_sweep", "/database/")
AGENT_GLOBS = ("services.agent", "services.agent.*")
AGENT_EXTRA = {"routers.agent_entry"}
LEGACY_SEEDS = {"routers.chat", "routers.platform_sop", "routers.intents",
                "routers.suggested_intents", "services.sop_orchestrator"}
#: 第四桶：靠**非 Python-import 的邊**共用，`reach()` 的可達性算法天生看不到。
#: ⛔ 不得進 legacy_only、⛔ 不得刪。⚠️ **成員的依賴也要保**，而且不只 import
#: 閉包——`app.py` 用**建構子參數**注進去的也算，`injected_deps()` 就是掃這一類
#: （`app.py` 建構第四桶類別時，引數裡出現的每個本地模組名都併進來）。
#:
#: 這個集合會隨時間**非空 → 空 → 非空**地變動，理由每次都不同，逐次記錄如下，
#: ⛔ 都不要因為看到「曾經清空過」就假設現在也該是空的——每次變動都要重新查證：
#:
#: **① 2026-09-10（舊鏈隔離 S3／D 案）：app.state 注入邊——`conversational_engine`
#: ／`api_call_handler` 曾在這裡，之後被移除。**
#: `app.py` 以前用 `ConversationalEngine(api_handler=get_api_call_handler(db_pool))`
#: 注入到 `app.state.conversational_engine`，新線（`services/agent/state_store.py`）
#: 透過它存取 `form_sessions`。業主裁定 B 案：把新線實際用到的四個狀態方法
#: （43 行純 SQL，對 `api_handler` 零命中）抽成 `services/agent/session_persistence.
#: AgentSessionStore`，`app.py` 改注入 `app.state.agent_session_store`——這兩個
#: 模組從此不再被任何存活線 import 或注入，故移除，讓它們隨 S3 落入 `legacy_only`。
#:
#: **② 2026-09-10（同一輪 S3，同日但後一步）：docker-exec 耦合邊——七個
#: `responsibility_*`／`fulfillment_registry`／`grounding_presentation` 模組。**
#: `scripts/audit/check_invariants.sh`（`make audit` 的真正入口，⛔ 不是本檔）
#: 的不變量 24／25 用 `docker exec … python3 -c "from services.responsibility_artifacts
#: import validate"` 與 `"from services.responsibility_completion import
#: RESPONSIBILITY_FORMS, _RESOLVER_SPECS"` 直接在**容器內**匯入這兩個模組來驗
#: R10P sealed artifact 完整性與 responsibility form 輸入鍵契約——這條耦合邊既不是
#: Python import、也不是 `app.py` 的建構子注入，是**跑在 shell 腳本裡的字串**，
#: `injected_deps()`／`reach()` 兩種機制都看不到。`responsibility_completion.py`
#: 自己又 import `fulfillment_registry`／`grounding_presentation`／
#: `responsibility_bill_resolution`／`responsibility_entity_resolution`／
#: `responsibility_session` 五個模組，缺一個 docker exec 那行就 ImportError，
#: 故七個一起收進本桶。⚠️ **這是刪除 32 模組清單時真正刪錯的地方**——第一輪誤
#: 以為它們只被 `services/conversational_engine.py`／`routers/chat.py` 的
#: responsibility-resolution 舊邏輯引用，實際上它們同時是**完全獨立、與舊 REST
#: 對話鏈無關**的 R10P canonical-responsibility-registry 稽核基礎設施。
#: ⛔ **不要**因為模組名字面上像「responsibility」（聽起來像舊鏈的責任解析）
#: 就假設它屬於舊鏈——這批模組的真正身分要看**誰在 import 它**，不是看名字。
#:
#: **什麼情況要讓它再度變動**：任何「`app.py` 或某支 shell／CI 腳本把一個模組
#: 塞進只能用字串／屬性存取到的位置，而不是 Python import」的新模式出現，都要
#: 手動查一遍該模組（與它的遞移依賴）有沒有被這樣用，找到了就要加進來——
#: `reach()` 永遠只看得到 import 邊，這類邊只能靠人宣告。
RUNTIME_COUPLED: set[str] = {
    "services.responsibility_artifacts",
    "services.responsibility_completion",
    "services.fulfillment_registry",
    "services.grounding_presentation",
    "services.responsibility_bill_resolution",
    "services.responsibility_entity_resolution",
    "services.responsibility_session",
}


def load(src: str) -> dict:
    mods = {}
    for dp, _dn, fn in os.walk(src):
        if any(p in dp + "/" for p in SKIP_PARTS):
            continue
        for f in fn:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, src)[:-3].replace(os.sep, ".")
            if rel.endswith(".__init__"):
                rel = rel[:-9]
            mods[rel] = p
    return mods


def imports_of(mods, rel):
    try:
        tree = ast.parse(open(mods[rel], encoding="utf-8").read())
    except Exception:
        return set()
    out = set()
    for n in ast.walk(tree):            # ⛔ 整棵樹：函式內 import 大量存在
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                parts = rel.split(".")
                base = ".".join(parts[: len(parts) - n.level] + ([base] if base else []))
            out.add(base)
            for a in n.names:           # from <套件> import <子模組>
                out.add(base + "." + a.name)
    return {m for m in out if m in mods}


def injected_deps(src: str, mods: dict) -> set:
    """掃 `app.py`：第四桶類別的建構子被注入了哪些模組（import 圖看不見的邊）。

    ⛔ 這條是 `api_call_handler` 漏判逼出來的：`conversational_engine.py` 從不 import 它，
    `app.py` 卻以 `ConversationalEngine(api_handler=get_api_call_handler(db_pool))` 注入，
    而引擎內部真的呼叫 `self.api_handler.execute_api_call(...)`。
    純 import 可達性看不到這種邊，回傳值必須併進第四桶。
    """
    app = os.path.join(src, "app.py")
    if not os.path.exists(app):
        raise SystemExit("FATAL：找不到 app.py（掃描條件或路徑壞了）")
    tree = ast.parse(open(app, encoding="utf-8").read())

    name2mod = {}                       # app.py 的 import 表：本地名 → 模組
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module in mods:
            for a in n.names:
                name2mod[a.asname or a.name] = n.module
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name in mods:
                    name2mod[a.asname or a.name] = a.name

    coupled_names = {nm for nm, m in name2mod.items() if m in RUNTIME_COUPLED}
    out = set()
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id in coupled_names):
            continue
        for sub in ast.walk(n):         # 建構子引數裡出現的每個本地名
            if isinstance(sub, ast.Name) and sub.id in name2mod:
                out.add(name2mod[sub.id])
    return out - RUNTIME_COUPLED


def retirement_status(src: str) -> str:
    """舊鏈退役偵測——⛔ 別讓「target 消失」靜默變成綠但瞎（見 check_invariants.sh
    同款教訓）。三態：

    - `"active"`：`LEGACY_SEEDS` 全部還在——舊鏈還沒開始砍，正常跑分桶。
    - `"retired"`：`LEGACY_SEEDS` **全部**不在——舊鏈隔離 S3 已完成（2026-09-10），
      這支檢查器的宣告式分桶（新線／舊線兩條線）不再有意義，`main()`／`self_test()`
      改印明確的退役訊息、exit 0，⛔ 不假裝分桶結果仍然有效。
    - `"inconsistent"`：**部分**在、部分不在——這不是正常的「還沒砍」或「砍完了」，
      是掃描條件壞了或砍到一半就停，維持原本的 FATAL 大聲失敗。
    """
    mods = load(src)
    present = LEGACY_SEEDS & set(mods)
    if present == LEGACY_SEEDS:
        return "active"
    if not present:
        return "retired"
    return "inconsistent"


def buckets(src: str) -> dict:
    mods = load(src)
    missing = LEGACY_SEEDS - set(mods)
    if missing:
        raise SystemExit("FATAL：舊線進入點不存在 %s（掃描條件或路徑壞了，或舊鏈已退役——"
                          "呼叫端該先查 retirement_status()，不是直接呼叫 buckets()）"
                          % sorted(missing))
    graph = {m: imports_of(mods, m) for m in mods}

    def reach(seeds):
        seen, st = set(), list(seeds)
        while st:
            m = st.pop()
            if m in seen or m not in graph:
                continue
            seen.add(m)
            st.extend(graph[m])
        return seen

    agent_set = {m for m in mods if any(fnmatch.fnmatch(m, g) for g in AGENT_GLOBS)}
    agent_set |= AGENT_EXTRA & set(mods)
    agent_closure = reach(agent_set)
    legacy_reach = reach(LEGACY_SEEDS)
    # 第四桶＝宣告成員 ∪ 其 import 閉包 ∪ app.py 建構子注入的模組
    coupled = reach(RUNTIME_COUPLED) | injected_deps(src, mods)
    legacy_only = legacy_reach - agent_set - agent_closure - coupled

    # 第三方消費者（後台等）。⛔ 不含 app（它掛兩線、當種子會讓一切變爭議），
    # ⛔ 不含本身就落在 legacy_only 的 router，⛔ test_* 路由另計。
    others = {m for m in mods if m.startswith("routers.")}
    others -= LEGACY_SEEDS | agent_set | legacy_only
    others = {m for m in others if not m.startswith("routers.test_")}
    third = reach(others)

    pkg_inits = {m for m in mods if mods[m].endswith("__init__.py")}
    deletable = legacy_only - third - pkg_inits
    return dict(mods=mods, reach=reach, agent_set=agent_set, agent_closure=agent_closure,
                legacy_only=legacy_only, shared=(legacy_reach & agent_closure) - coupled,
                coupled=coupled,
                third=third, deletable=deletable, contested=legacy_only & third,
                pkg_inits=legacy_only & pkg_inits)


def controls(b) -> list:
    """正／負對照。⛔ 否定結論必須有正對照，否則工具壞了也看不出來。"""
    errs = []
    bad = sorted(m for m in b["legacy_only"] if m in b["agent_set"] or m.startswith("services.agent"))
    if bad:
        errs.append("負對照 FAIL：legacy_only 含新線模組 %s" % bad)
    if "services.sop_orchestrator" not in b["legacy_only"]:
        errs.append("正對照① FAIL：legacy_only 未含 services.sop_orchestrator（已知必然的舊線模組）")
    if "routers.chat" not in b["legacy_only"]:
        errs.append("正對照② FAIL：legacy_only 未含 routers.chat")
    dup = sorted((b["legacy_only"] | b["shared"]) & b["coupled"])
    if dup:
        errs.append("一致性 FAIL：第四桶成員同時出現在其他清單 %s" % dup)
    return errs


def self_test() -> int:
    """植入一條假的新線→舊線邊，負對照必須紅；⛔ 自測不紅 ⇒ 本檢查器的 PASS 不可信。

    舊鏈已退役時（`retirement_status(SRC) == "retired"`）：植入邊要打的靶
    （`services.sop_orchestrator` 等 `LEGACY_SEEDS`）已經不存在，這個自測從
    「驗證分桶邏輯」變成「驗證一個已經不成立的前提」——印明確訊息、PASS，
    ⛔ 不假裝還在驗證分桶。
    """
    if retirement_status(SRC) == "retired":
        print("自我測試 SKIP（舊鏈已退役，LEGACY_SEEDS 全部不存在——"
              "分桶自測的前提〔存在可注入邊的舊線種子〕不再成立，無需驗證）")
        return 0
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(SRC, os.path.join(td, "s"),
                        ignore=shutil.ignore_patterns("__pycache__", "tests", ".venv", "*.pyc"))
        s = os.path.join(td, "s")
        b0 = buckets(s)
        if controls(b0):
            print("自我測試 FAIL：乾淨複本就有對照失敗 %s" % controls(b0)); return 1
        if "services.sop_orchestrator" not in b0["deletable"]:
            print("自我測試 FAIL：乾淨複本的可刪清單未含 sop_orchestrator"); return 1
        # 植入：新線 import 舊線 ⇒ sop_orchestrator 應從 legacy_only 消失（被吸進新線閉包）
        rt = os.path.join(s, "services", "agent", "runtime.py")
        open(rt, "a", encoding="utf-8").write("\nfrom services.sop_orchestrator import SOPOrchestrator  # self-test\n")
        b1 = buckets(s)
        if "services.sop_orchestrator" in b1["legacy_only"]:
            print("自我測試 FAIL：植入新線→舊線邊後 sop_orchestrator 仍在 legacy_only（可達性沒生效）"); return 1
    print("自我測試 PASS（乾淨複本對照全過；植入邊後分桶如預期改變）")
    return 0


def write_lists(b) -> None:
    os.makedirs(DATA, exist_ok=True)
    for name, key in (("legacy_deletable", "deletable"), ("legacy_contested", "contested"),
                      ("shared", "shared"), ("agent_line", "agent_set")):
        with open(os.path.join(DATA, name + ".txt"), "w", encoding="utf-8") as fh:
            for m in sorted(b[key]):
                fh.write(os.path.relpath(b["mods"][m], REPO) + "\n")
    with open(os.path.join(DATA, "runtime_coupled.txt"), "w", encoding="utf-8") as fh:
        for m in sorted(b["coupled"]):
            fh.write(os.path.relpath(b["mods"][m], REPO) + "\n")


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    status = retirement_status(SRC)
    if status == "retired":
        print("ℹ️ RETIRED：舊鏈隔離 S3 已完成（2026-09-10）——LEGACY_SEEDS 全部已刪除"
              "（%s）。本檢查器的宣告式分桶（新線／舊線兩條線）任務已完成，"
              "repo 現在只剩一條線，⛔ 分桶結果不再有意義（不是「查不到」，是「不再適用」）。"
              "`scripts/audit/lists/*.txt` 停留在退役當下最後一次核可的內容，當歷史記錄，"
              "⛔ 不再由本檢查器維護／比對。" % sorted(LEGACY_SEEDS))
        return 0
    if status == "inconsistent":
        present = LEGACY_SEEDS & set(load(SRC))
        raise SystemExit("FATAL：LEGACY_SEEDS 部分存在部分不存在（現存 %s／全集 %s）——"
                          "這不是正常的『還沒砍』或『砍完了』，是掃描條件壞了或砍到一半就停"
                          % (sorted(present), sorted(LEGACY_SEEDS)))
    b = buckets(SRC)
    errs = controls(b)
    for e in errs:
        print("❌ " + e)
    if errs:
        return 1
    if "--regenerate" in sys.argv:
        write_lists(b)
        print("已重寫 %s/*.txt ——⛔ 需重走人工核可" % os.path.relpath(DATA, REPO))
    frozen = os.path.join(DATA, "legacy_deletable.txt")
    if os.path.exists(frozen) and "--regenerate" not in sys.argv:
        want = {l.strip() for l in open(frozen, encoding="utf-8") if l.strip()}
        got = {os.path.relpath(b["mods"][m], REPO) for m in b["deletable"]}
        if want != got:
            print("❌ 可刪清單與凍結檔漂移：多 %s／少 %s" % (sorted(got - want), sorted(want - got)))
            return 1
    print("✅ PASS：對照全過；可刪 %d／爭議 %d／共用 %d／第四桶 %d"
          % (len(b["deletable"]), len(b["contested"]), len(b["shared"]), len(b["coupled"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
