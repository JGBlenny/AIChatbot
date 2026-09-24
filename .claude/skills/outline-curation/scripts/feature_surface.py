#!/usr/bin/env python3
"""步 0a：產品功能全表（覆蓋圖的分母）——決定性、StepEnvelope 化。

從三個權威來源機械列出 JGB 使用者可見功能面，並機械切成 **功能單位 `units[]`**（0b 只填判定，⛔ 不得增刪合併單位）：
1. jgb2 `config/character.php`：每個權限 action ＝ 1 單位（`action:<key>`）。
2. jgb2 `routes/web.php`／`routes/api.php`：每個 (controller, route name 或 path) ＝ 1 單位（`route:<controller>@<name|path>`）；
   路徑或名稱含 `tenant` 者標 租客側。`Admin\\*` controller 標 `internal=true`（JGB 內部後台，0b 不計缺口）。
3. 幫助中心 zh-Hant 頁：每頁每個 `<h3>` 段 ＝ 1 單位（`help:<file>#<section>`），無段落的頁 ＝ 1 單位。
合併只准來自版控中的顯式 allowlist `--units-merge <json>`（`{"merged_id": ["unit_id", ...]}`）。

**已知不涵蓋面**（doc 明列、⛔ 不得當作「沒有功能」）：Route group 前綴不還原（路徑為 group 內相對路徑）、
陣列 callable／closure／`Route::resource|apiResource` 不解析（只計入「未解析」計數）、前端 SPA 專屬畫面、排程／通知等無路由功能。
路由覆蓋率守門：`Route::` 出現次數 vs 解析成功筆數，未解析比例 > `--max-unparsed`（預設 0.10）⇒ exit 2。
路由單位粒度 `--route-granularity controller|route`（預設 controller：同 controller 併 1 單位，`members` 列路由名，機械無裁量）。

材料指紋：`jgb2_sha`（`git rev-parse <branch>`）、`help_dir_sha`、`canon_sha` 進 `inputs_sha`。
輸出：StepEnvelope（`schemas/feature-surface.json`）＋人讀 Markdown。缺來源、0 筆解析 ⇒ exit 2。

用法：
  python3 feature_surface.py --jgb2 /path/jgb2 --branch master \\
      --help-dir "/path/幫助中心" --canon rag-orchestrator/canon/jgb \\
      [--units-merge <allowlist.json>] [--max-unparsed 0.10] [--route-granularity controller|route] \\
      --out-json <run>/feature-surface.json --out-md <run>/feature-surface.md
  python3 feature_surface.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import re
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import make_envelope, sha256_path, validate_file, write_json  # noqa: E402

SKILL_VERSION = "0.1-feature-surface"


def _git(repo: str, *args: str) -> str:
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"❌ git {' '.join(args)} 失敗於 {repo}：{out.stderr.strip()}")
    return out.stdout


_PERM_RE = re.compile(r"^\s*'([a-z_]+)'\s*=>\s*(true|false)\s*,?\s*(//\s*(.*))?$")


def parse_character(text: str) -> dict:
    """回傳 {action: {"roles": [授權角色], "note": 註解}}；0 個 ⇒ exit 2。"""
    actions: dict[str, dict] = {}
    current_label = None
    in_perm = False
    for line in text.splitlines():
        m_label = re.match(r"^\s*'label'\s*=>\s*'([^']*)'", line)
        if m_label:
            current_label = m_label.group(1)
            in_perm = False
            continue
        if re.match(r"^\s*'permission'\s*=>\s*\[", line):
            in_perm = True
            continue
        if in_perm and re.match(r"^\s*\],?\s*$", line):
            in_perm = False
            continue
        if in_perm:
            m = _PERM_RE.match(line)
            if m:
                key, val, _, note = m.groups()
                a = actions.setdefault(key, {"roles": [], "note": ""})
                if val == "true" and current_label and current_label not in a["roles"]:
                    a["roles"].append(current_label)
                if note and not a["note"]:
                    a["note"] = note.strip()
    if not actions:
        sys.exit("❌ character.php 解析到 0 個 action——格式變了，⛔ 不得當作沒有功能")
    return actions


#: JGB 內部後台／維運／第三方套件 controller（0b 不計缺口）。規則＋顯式清單，⛔ 無裁量。
INTERNAL_CONTROLLERS = frozenset({"MondayStatisticController", "SitemapController", "LogViewerController"})


def _is_internal(controller: str) -> bool:
    return controller.startswith("Admin\\") or controller.startswith("Internal\\") or controller.split("\\")[-1] in INTERNAL_CONTROLLERS


_ROUTE_RE = re.compile(
    r"Route::(get|post|put|patch|delete|any|match)\(\s*(?:\[[^\]]*\]\s*,\s*)?'([^']*)'\s*,\s*'([^']*)'\s*\)"
    r"(?:\s*->\s*name\(\s*'([^']*)'\s*\))?"
)
_ROUTE_ANY_RE = re.compile(r"Route::(get|post|put|patch|delete|any|match|resource|apiResource)\(")


def parse_routes(text: str, source: str) -> tuple[list[dict], dict]:
    """回傳 (rows, coverage)；coverage＝{"occurrences", "parsed", "unparsed"}。0 筆 ⇒ exit 2。"""
    rows = []
    for m in _ROUTE_RE.finditer(text):
        verb, path, target, name = m.groups()
        controller, _, method = target.partition("@")
        side = "租客側" if re.search(r"tenant", path + (name or ""), re.I) else "房東側"
        rows.append({
            "source": source, "verb": verb, "path": path, "controller": controller,
            "method": method, "name": name or "", "side": side,
            "internal": _is_internal(controller),
        })
    occurrences = len(_ROUTE_ANY_RE.findall(text))
    if not rows:
        sys.exit(f"❌ {source} 解析到 0 條路由——regex 沒對上，⛔ 不得當作沒有路由")
    return rows, {"occurrences": occurrences, "parsed": len(rows), "unparsed": max(0, occurrences - len(rows))}


def parse_help_pages(help_dir: str) -> list[dict]:
    pages = []
    for fp in sorted(glob.glob(os.path.join(help_dir, "*_zh-Hant.html"))):
        raw = open(fp, encoding="utf-8", errors="replace").read()
        title = re.search(r"<title>(.*?)</title>", raw, re.S)
        eyebrow = re.search(r'class="eyebrow"[^>]*>(.*?)</', raw, re.S)
        h3 = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<h3[^>]*>(.*?)</h3>", raw, re.S)]
        pages.append({
            "file": os.path.basename(fp),
            "title": html.unescape(title.group(1)).strip() if title else "",
            "eyebrow": html.unescape(re.sub(r"<[^>]+>", "", eyebrow.group(1))).strip() if eyebrow else "",
            "sections": [s for s in h3 if s],
        })
    if not pages:
        sys.exit(f"❌ {help_dir} 沒有任何 *_zh-Hant.html")
    return pages


def parse_canon_titles(canon_dir: str) -> list[dict]:
    rows = []
    for fp in sorted(glob.glob(os.path.join(canon_dir, "[A-I].md"))):
        for line in open(fp, encoding="utf-8"):
            m = re.match(r"^### (.+?)\s*\{#([^}]+)\}\s*$", line)
            if m:
                rows.append({"id": m.group(2), "title": m.group(1).strip(), "shelf": os.path.basename(fp)[0]})
    if not rows:
        sys.exit(f"❌ {canon_dir} 解析到 0 條細目標題")
    return rows


def build_units(actions: dict, routes: list[dict], pages: list[dict], merge: dict | None,
                route_granularity: str = "controller") -> list[dict]:
    """機械切單位；同一輸入 ⇒ 逐位元相同的 units（排序固定）。

    route_granularity="controller"（預設）：同 controller 的路由併成 1 單位（`route:<controller>`，`members` 列 route name）；
    ="route"：一 (controller, route name|path) 一單位。兩者都是規則、無裁量。
    """
    units: list[dict] = []
    for k in sorted(actions):
        units.append({"unit_id": f"action:{k}", "kind": "action", "label": k,
                      "evidence": f"config/character.php:'{k}'", "side": "房東側", "internal": False,
                      "roles": actions[k]["roles"], "note": actions[k]["note"]})
    seen = set()
    if route_granularity == "controller":
        by_ctrl: dict[str, list[dict]] = defaultdict(list)
        for r in routes:
            by_ctrl[r["controller"]].append(r)
        for ctrl in sorted(by_ctrl):
            rs = sorted(by_ctrl[ctrl], key=lambda r: (r["name"] or r["path"], r["verb"]))
            members = sorted({r["name"] or r["path"] for r in rs})
            sides = {r["side"] for r in rs}
            units.append({"unit_id": f"route:{ctrl}", "kind": "route", "label": f"{ctrl}（{len(rs)} 條）",
                          "evidence": "；".join(f"{r['source']}:{r['name'] or r['path']}" for r in rs)[:400],
                          "side": "租客側" if sides == {"租客側"} else "房東側",
                          "internal": rs[0]["internal"], "roles": [], "note": "", "members": members})
    else:
        for r in sorted(routes, key=lambda r: (r["controller"], r["name"] or r["path"], r["verb"])):
            key = f"route:{r['controller']}@{r['name'] or r['path']}"
            if key in seen:
                continue
            seen.add(key)
            units.append({"unit_id": key, "kind": "route", "label": f"{r['verb']} {r['path']}",
                          "evidence": f"{r['source']}:{r['name'] or r['path']}", "side": r["side"],
                          "internal": r["internal"], "roles": [], "note": ""})
    for p in pages:
        if p["sections"]:
            seen_sec: dict[str, int] = {}
            for s in p["sections"]:
                n = seen_sec.get(s, 0) + 1
                seen_sec[s] = n
                uid = f"help:{p['file']}#{s}" + (f"#{n}" if n > 1 else "")
                units.append({"unit_id": uid, "kind": "help", "label": f"{p['title']}／{s}",
                              "evidence": f"{p['file']}#{s}", "side": "租客側" if "租客" in p["eyebrow"] else "房東側",
                              "internal": False, "roles": [], "note": p["eyebrow"]})
        else:
            units.append({"unit_id": f"help:{p['file']}", "kind": "help", "label": p["title"],
                          "evidence": p["file"], "side": "租客側" if "租客" in p["eyebrow"] else "房東側",
                          "internal": False, "roles": [], "note": p["eyebrow"]})
    if merge:
        by_id = {u["unit_id"]: u for u in units}
        used: set = set()
        for merged_id, members in merge.items():
            overlap = [m for m in members if m in used]
            if overlap:
                sys.exit(f"❌ units-merge 兩筆合併共用成員：{overlap}")
            used.update(members)
            missing = [m for m in members if m not in by_id]
            if missing:
                sys.exit(f"❌ units-merge 引用不存在的單位：{missing}")
            first = by_id[members[0]]
            units = [u for u in units if u["unit_id"] not in members]
            units.append({**first, "unit_id": merged_id, "kind": "merged", "members": list(members),
                          "evidence": "；".join(by_id[m]["evidence"] for m in members)})
    units.sort(key=lambda u: u["unit_id"])
    ids = [u["unit_id"] for u in units]
    if len(ids) != len(set(ids)):
        sys.exit("❌ units 有重複 unit_id——切單位規則出錯，⛔ 不得輸出")
    return units


def self_test() -> int:
    """正對照 2＋負對照 4：parser 對已知樣本必抓到；空輸入必大聲失敗；路由覆蓋率算得出未解析。"""
    fails = []
    ch = "return [\n '0' => [\n 'label' => '團隊擁有者',\n 'permission'=> [\n 'show_estate' => true,\n 'add_estate' => false, // 註\n ],\n ],\n];"
    acts = parse_character(ch)
    if acts.get("show_estate", {}).get("roles") != ["團隊擁有者"] or "add_estate" not in acts:
        fails.append("① character parser 沒抓到 show_estate／add_estate")
    rt, cov = parse_routes("Route::get('/tenant/bills', 'BillController@index')->name('tenant.bills');\n"
                           "Route::post('/x', 'Admin\\XController@y');\nRoute::apiResource('/z', 'ZController');", "t")
    if len(rt) != 2 or rt[0]["side"] != "租客側" or rt[1]["side"] != "房東側" or not rt[1]["internal"]:
        fails.append("② route parser 條數／側別／internal 錯")
    if cov != {"occurrences": 3, "parsed": 2, "unparsed": 1}:
        fails.append(f"③ 路由覆蓋率沒算出 apiResource 未解析：{cov}")
    import tempfile
    empty = tempfile.mkdtemp()
    for fn, arg in ((parse_character, ("return [];",)), (parse_routes, ("", "t")),
                    (parse_help_pages, (empty,)), (parse_canon_titles, (empty,))):
        try:
            fn(*arg)
            fails.append(f"④ {fn.__name__} 對空輸入沒有大聲失敗")
        except SystemExit:
            pass
    pg = [{"file": "a.html", "title": "T", "eyebrow": "租客教學", "sections": ["s1", "s1"]}]
    u1 = build_units(acts, rt, pg, None)
    u2 = build_units(acts, rt, pg, None)
    if u1 != u2 or len(u1) != 2 + 2 + 2 or u1[-1]["side"] != "租客側" or len({u["unit_id"] for u in u1}) != 6:  # 同名段落 id 必唯一
        fails.append("⑤ units 不決定性、計數錯或同名段落 id 重複")
    if not _is_internal("Internal\\BillQueryController") or not _is_internal("SitemapController") or _is_internal("BillController"):
        fails.append("⑥ internal 規則錯")
    for f in fails:
        print("❌ self-test:", f)
    if not fails:
        print("✅ self-test 通過（正對照 3、負對照 4、決定性 1）")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("--jgb2", required=True)
    ap.add_argument("--branch", default="master")
    ap.add_argument("--help-dir", required=True)
    ap.add_argument("--canon", required=True)
    ap.add_argument("--units-merge", default=None)
    ap.add_argument("--max-unparsed", type=float, default=0.10)
    ap.add_argument("--route-granularity", choices=("controller", "route"), default="controller")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()

    jgb2_sha = _git(a.jgb2, "rev-parse", a.branch).strip()
    actions = parse_character(_git(a.jgb2, "show", f"{a.branch}:config/character.php"))
    rows_w, cov_w = parse_routes(_git(a.jgb2, "show", f"{a.branch}:routes/web.php"), "routes/web.php")
    rows_a, cov_a = parse_routes(_git(a.jgb2, "show", f"{a.branch}:routes/api.php"), "routes/api.php")
    routes = rows_w + rows_a
    coverage = {"occurrences": cov_w["occurrences"] + cov_a["occurrences"], "parsed": len(routes)}
    coverage["unparsed"] = max(0, coverage["occurrences"] - coverage["parsed"])
    ratio = coverage["unparsed"] / coverage["occurrences"] if coverage["occurrences"] else 0.0
    print(f"路由：Route:: 總出現 {coverage['occurrences']}／解析 {coverage['parsed']}／未解析 {coverage['unparsed']}（{ratio:.0%}）")
    if ratio > a.max_unparsed:
        sys.exit(f"❌ 未解析路由比例 {ratio:.0%} > {a.max_unparsed:.0%}——分母少算，⛔ 不得當作全表")
    pages = parse_help_pages(a.help_dir)
    canon = parse_canon_titles(a.canon)
    merge = None
    if a.units_merge:
        import json
        merge = json.load(open(a.units_merge, encoding="utf-8"))
    units = build_units(actions, routes, pages, merge, a.route_granularity)

    by_ctrl: dict[str, list[dict]] = defaultdict(list)
    for r in routes:
        by_ctrl[r["controller"]].append(r)
    payload = {
        "sources": {"jgb2": a.jgb2, "branch": a.branch, "jgb2_sha": jgb2_sha, "help_dir": a.help_dir, "canon": a.canon,
                    "units_merge": a.units_merge, "route_granularity": a.route_granularity},
        "route_coverage": coverage,
        "counts": {"actions": len(actions), "routes": len(routes), "controllers": len(by_ctrl),
                   "help_pages": len(pages), "canon_fines": len(canon), "units": len(units)},
        "units": units, "actions": actions, "routes": routes, "help_pages": pages, "canon_titles": canon,
    }
    inputs_sha = {"jgb2_sha": jgb2_sha, "help_dir": sha256_path(a.help_dir), "canon": sha256_path(a.canon)}
    if a.units_merge:
        inputs_sha["units_merge"] = sha256_path(a.units_merge)
    env = make_envelope(step="feature_surface", skill_version=SKILL_VERSION, inputs_sha=inputs_sha,
                        deterministic=True, payload=payload)
    write_json(a.out_json, env)
    schema = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "feature-surface.json")
    validate_file(a.out_json, schema)

    md = [f"# JGB 產品功能全表（步 0a 分母）— {a.branch} @ {jgb2_sha[:12]}", "",
          f"來源：jgb2 `{a.branch}`（`config/character.php`、`routes/web.php`、`routes/api.php`）、幫助中心 `{os.path.basename(a.help_dir)}`、正本 `{a.canon}`。",
          f"路由覆蓋：Route:: 出現 {coverage['occurrences']}／解析 {coverage['parsed']}／未解析 {coverage['unparsed']}。已知不涵蓋面見腳本檔頭。", "",
          "## 0. 計數", "",
          "| 單位 | 權限 action | 路由 | controller | 幫助中心頁 | 正本細目 |", "|---|---|---|---|---|---|",
          f"| {len(units)} | {len(actions)} | {len(routes)} | {len(by_ctrl)} | {len(pages)} | {len(canon)} |", "",
          "## 1. 功能單位（0b 只填判定，⛔ 不得增刪合併）", "", "| unit_id | 種類 | 側 | 內部 | 證據 |", "|---|---|---|---|---|"]
    for u in units:
        md.append(f"| `{u['unit_id']}` | {u['kind']} | {u['side']} | {'是' if u['internal'] else ''} | {u['evidence']} |")
    md += ["", "## 2. 正本細目標題（只列，不判定）", ""]
    for c in canon:
        md.append(f"- `{c['id']}` {c['title']}")
    with open(a.out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(f"✅ 功能全表：單位 {len(units)}（action {len(actions)}、路由 {len(routes)}、幫助中心段 {sum(max(1, len(p['sections'])) for p in pages)}）、正本 {len(canon)} 條 → {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
