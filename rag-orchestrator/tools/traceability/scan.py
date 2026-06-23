#!/usr/bin/env python3
"""追溯掃描器（spec testing-traceability 元件 5・R6/R7/R8）。

掃描三方並建立雙向追溯：
  - 測試標記／docstring（`@pytest.mark.req("spec:id")` 為主、docstring `spec:id` 過渡，D3）
  - 文件章節標註（`<!-- tested-by: spec:id [behavior="..."] -->`，D4）
  - spec 需求 ID（requirements.md 數字驗收條件標題）

產出追溯矩陣 + 五類缺口（漸進式：未標記不報錯）：
  孤兒需求 / 孤兒測試（待標記） / 失效引用 / 未受測試背書文件 / 候選過時文件。

純標準庫，可在 host 或容器執行。用法：
  python3 tools/traceability/scan.py [--out .kiro/specs/testing-traceability/traceability-matrix.md] [--json ...]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# rag-orchestrator/ 根（本檔位於 rag-orchestrator/tools/traceability/）
_RAG_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _RAG_ROOT.parent

# 規格需求 ID 行（如 "5.2 對話引擎..."）；canonical 引用 "spec:id"（如 "a:1.1"）。
_REQ_LINE = re.compile(r"^(\d+\.\d+)\s+\S")
_CANON_REF = re.compile(r"\b([A-Za-z][\w-]+):(\d+\.\d+)\b")
# 文件標註：<!-- tested-by: spec:id[, spec:id ...] [behavior="..."] -->
_TESTED_BY = re.compile(
    r"<!--\s*tested-by:\s*([^>]*?)(?:\s+behavior=\"([^\"]*)\")?\s*-->", re.IGNORECASE
)
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass(frozen=True)
class TestRef:
    __test__ = False  # 防止 pytest 將此 dataclass 誤收為測試類別（名稱以 Test 開頭）
    nodeid: str
    layer: str
    req_ids: tuple[str, ...]
    source: str  # "marker" | "docstring" | "marker+docstring" | ""


@dataclass(frozen=True)
class DocRef:
    file: str
    section: str
    req_ids: tuple[str, ...]
    behavior: str = ""


@dataclass
class TraceReport:
    matrix: list[dict] = field(default_factory=list)
    orphan_requirements: list[str] = field(default_factory=list)
    orphan_tests: list[str] = field(default_factory=list)
    dangling_refs: list[str] = field(default_factory=list)
    docs_unbacked: list[str] = field(default_factory=list)
    docs_stale: list[str] = field(default_factory=list)

    def gap_count(self) -> int:
        return (
            len(self.orphan_requirements)
            + len(self.orphan_tests)
            + len(self.dangling_refs)
            + len(self.docs_unbacked)
            + len(self.docs_stale)
        )

    def to_json(self) -> dict:
        return {
            "matrix": self.matrix,
            "gaps": {
                "orphan_requirements": self.orphan_requirements,
                "orphan_tests": self.orphan_tests,
                "dangling_refs": self.dangling_refs,
                "docs_unbacked": self.docs_unbacked,
                "docs_stale": self.docs_stale,
            },
            "gap_count": self.gap_count(),
        }

    def to_markdown(self) -> str:
        lines = ["# 追溯矩陣（traceability matrix）", ""]
        lines.append(f"> 缺口總數：**{self.gap_count()}**（漸進式，預設警示不硬擋）")
        lines.append("")
        lines.append("## 需求 ↔ 測試 ↔ 文件")
        lines.append("")
        lines.append("| 需求 ID | 測試 | 文件章節 |")
        lines.append("|---|---|---|")
        for row in self.matrix:
            tests = "<br>".join(row["tests"]) or "—（孤兒需求）"
            docs = "<br>".join(row["docs"]) or "—"
            lines.append(f"| {row['req_id']} | {tests} | {docs} |")
        lines.append("")

        def _section(title: str, items: list[str], hint: str) -> None:
            lines.append(f"## {title}（{len(items)}）")
            if hint:
                lines.append(f"> {hint}")
            lines.append("")
            if items:
                lines.extend(f"- {it}" for it in items)
            else:
                lines.append("_（無）_")
            lines.append("")

        _section("孤兒需求（無測試）", self.orphan_requirements, "R6.3：每條需求應 ≥1 測試。")
        _section("孤兒測試（未標記需求・待標記）", self.orphan_tests,
                 "R6.5：漸進導入，未標記非錯誤，列為待補。")
        _section("失效引用（宣告的需求 ID 不存在）", self.dangling_refs, "R6.4")
        _section("未受測試背書之文件章節", self.docs_unbacked, "R7.3")
        _section("候選過時文件（人工確認）", self.docs_stale, "R7.4：啟發式，僅供人工確認。")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 掃描器
# --------------------------------------------------------------------------- #
def scan_requirements(specs_dir: str | os.PathLike) -> dict[str, list[str]]:
    """回傳 {spec_name: [req_id, ...]}，解析各 spec requirements.md 的數字驗收條件標題。"""
    specs_dir = Path(specs_dir)
    result: dict[str, list[str]] = {}
    if not specs_dir.exists():
        return result
    for spec_path in sorted(specs_dir.iterdir()):
        req_file = spec_path / "requirements.md"
        if not (spec_path.is_dir() and req_file.exists()):
            continue
        ids: list[str] = []
        for line in req_file.read_text(encoding="utf-8").splitlines():
            m = _REQ_LINE.match(line.strip())
            if m:
                ids.append(m.group(1))
        # 去重保序
        seen: set[str] = set()
        result[spec_path.name] = [x for x in ids if not (x in seen or seen.add(x))]
    return result


def _marker_req_ids(decorator: ast.expr) -> list[str]:
    """從 @pytest.mark.req(...) 取字串引數。"""
    if not isinstance(decorator, ast.Call):
        return []
    func = decorator.func
    if not (isinstance(func, ast.Attribute) and func.attr == "req"):
        return []
    # 確認鏈為 *.mark.req
    val = func.value
    if not (isinstance(val, ast.Attribute) and val.attr == "mark"):
        return []
    out: list[str] = []
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append(arg.value)
    return out


def _marker_layer(decorators: list[ast.expr]) -> str:
    for dec in decorators:
        # @pytest.mark.unit / .integration / .e2e（Attribute）或被呼叫形式
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr in {"unit", "integration", "e2e"}:
            return target.attr
    return ""


def _docstring_refs(node: ast.AST) -> list[str]:
    doc = ast.get_docstring(node) or ""
    return [f"{spec}:{rid}" for spec, rid in _CANON_REF.findall(doc)]


def scan_tests(tests_dir: str | os.PathLike) -> list[TestRef]:
    """掃描 test_*.py，回傳每個測試（函式或測試類別）的 TestRef。"""
    tests_dir = Path(tests_dir)
    refs: list[TestRef] = []
    if not tests_dir.exists():
        return refs
    for py in sorted(tests_dir.rglob("test_*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = py.relative_to(tests_dir.parent if tests_dir.parent.exists() else tests_dir)
        rel = os.path.join("tests", py.name)

        def _emit(node, nodeid: str, class_layer: str = "", class_marker_ids=()):
            marker_ids: list[str] = list(class_marker_ids)
            for dec in node.decorator_list:
                marker_ids.extend(_marker_req_ids(dec))
            layer = _marker_layer(node.decorator_list) or class_layer
            doc_ids = _docstring_refs(node)
            ids = tuple(dict.fromkeys(marker_ids + doc_ids))
            if marker_ids and doc_ids:
                source = "marker+docstring"
            elif marker_ids:
                source = "marker"
            elif doc_ids:
                source = "docstring"
            else:
                source = ""
            refs.append(TestRef(nodeid=nodeid, layer=layer, req_ids=ids, source=source))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                _emit(node, f"{rel}::{node.name}")
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                cls_layer = _marker_layer(node.decorator_list)
                cls_ids: list[str] = []
                for dec in node.decorator_list:
                    cls_ids.extend(_marker_req_ids(dec))
                cls_ids.extend(_docstring_refs(node))
                has_test_method = False
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test"):
                        has_test_method = True
                        _emit(sub, f"{rel}::{node.name}::{sub.name}", cls_layer, cls_ids)
                if not has_test_method and cls_ids:
                    refs.append(TestRef(f"{rel}::{node.name}", cls_layer, tuple(dict.fromkeys(cls_ids)),
                                        "marker" if cls_ids else ""))
    return refs


def scan_docs(docs_dir: str | os.PathLike) -> list[DocRef]:
    """掃描 docs/*.md 的 `<!-- tested-by: ... -->` 標註，章節＝最近的前置標題。"""
    docs_dir = Path(docs_dir)
    refs: list[DocRef] = []
    if not docs_dir.exists():
        return refs
    for md in sorted(docs_dir.rglob("*.md")):
        section = ""
        rel = str(md.relative_to(docs_dir.parent)) if docs_dir.parent.exists() else md.name
        for line in md.read_text(encoding="utf-8").splitlines():
            hm = _MD_HEADING.match(line)
            if hm:
                section = hm.group(2)
                continue
            tm = _TESTED_BY.search(line)
            if tm:
                raw_ids = tm.group(1)
                behavior = (tm.group(2) or "").strip()
                ids = tuple(
                    x.strip() for x in re.split(r"[,\s]+", raw_ids.strip()) if ":" in x
                )
                if ids:
                    refs.append(DocRef(file=rel, section=section or "(檔首)",
                                       req_ids=ids, behavior=behavior))
    return refs


def build_matrix(reqs: dict[str, list[str]], tests: list[TestRef],
                 docs: list[DocRef]) -> TraceReport:
    """建立追溯矩陣與五類缺口。"""
    all_req_ids = {f"{spec}:{rid}" for spec, rids in reqs.items() for rid in rids}

    tests_by_req: dict[str, list[str]] = {r: [] for r in all_req_ids}
    docs_by_req: dict[str, list[str]] = {r: [] for r in all_req_ids}

    report = TraceReport()

    # 測試 → 需求
    for t in tests:
        if not t.req_ids:
            report.orphan_tests.append(t.nodeid)
            continue
        for rid in t.req_ids:
            if rid in all_req_ids:
                tests_by_req[rid].append(t.nodeid)
            else:
                report.dangling_refs.append(f"{t.nodeid} → {rid}（需求不存在）")

    # 文件 → 需求
    for d in docs:
        label = f"{d.file} › {d.section}"
        for rid in d.req_ids:
            if rid in all_req_ids:
                docs_by_req[rid].append(label)
            else:
                report.dangling_refs.append(f"{label} → {rid}（需求不存在）")
        # 未受測試背書：文件聲稱對應的（存在的）需求卻無任何測試
        valid_ids = [r for r in d.req_ids if r in all_req_ids]
        if valid_ids and all(not tests_by_req.get(r) for r in valid_ids):
            report.docs_unbacked.append(label)
        # 候選過時（啟發式）：文件聲稱的行為關鍵字未出現在其背書測試的 nodeid/docstring
        if d.behavior:
            backing = [t for t in tests if set(t.req_ids) & set(valid_ids)]
            hay = " ".join(t.nodeid for t in backing).lower()
            keys = [k for k in re.split(r"\s+", d.behavior.lower()) if k]
            if backing and not any(k in hay for k in keys):
                report.docs_stale.append(f"{label}（behavior=\"{d.behavior}\" 未見於背書測試）")

    # 矩陣 + 孤兒需求
    for rid in sorted(all_req_ids):
        report.matrix.append({
            "req_id": rid,
            "tests": sorted(set(tests_by_req[rid])),
            "docs": sorted(set(docs_by_req[rid])),
        })
        if not tests_by_req[rid]:
            report.orphan_requirements.append(rid)

    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="追溯掃描器")
    ap.add_argument("--specs", default=str(_REPO_ROOT / ".kiro/specs"))
    ap.add_argument("--tests", default=str(_RAG_ROOT / "tests"))
    ap.add_argument("--docs", default=str(_REPO_ROOT / "docs"))
    ap.add_argument("--out", default=str(_REPO_ROOT / ".kiro/specs/testing-traceability/traceability-matrix.md"))
    ap.add_argument("--json", dest="json_out",
                    default=str(_REPO_ROOT / ".kiro/specs/testing-traceability/traceability-matrix.json"))
    args = ap.parse_args(argv)

    reqs = scan_requirements(args.specs)
    tests = scan_tests(args.tests)
    docs = scan_docs(args.docs)
    report = build_matrix(reqs, tests, docs)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report.to_markdown(), encoding="utf-8")
    Path(args.json_out).write_text(
        json.dumps(report.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✅ 追溯報告：{args.out}")
    print(f"   需求 {sum(len(v) for v in reqs.values())}｜測試 {len(tests)}｜文件標註 {len(docs)}"
          f"｜缺口 {report.gap_count()}"
          f"（孤兒需求 {len(report.orphan_requirements)}、孤兒測試 {len(report.orphan_tests)}、"
          f"失效引用 {len(report.dangling_refs)}、未背書文件 {len(report.docs_unbacked)}、"
          f"候選過時 {len(report.docs_stale)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
