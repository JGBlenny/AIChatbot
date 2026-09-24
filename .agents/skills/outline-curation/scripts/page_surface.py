#!/usr/bin/env python3
"""步 0a：大綱覆蓋基準＝JGB 使用者可到達的頁面樹（DSP-065，取代功能全表當分母）——決定性、StepEnvelope 化。

一格＝一條使用者可到達的頁面（業主 2026-09-19 裁：一條具名路由一格），兩段來源、缺一不可：
(a) SPA 具名路由：jgb2 `src/routes/*.js`（Vue Router；`name:` 配最近的 `path:`／`component:`）。
(b) 後端直接渲染的非內部頁：`routes/web.php` 的 `Route::get|match(...)` 中 controller 非 `IndexController@vueIndex`、
    非 `Admin\\*`／`Internal\\*`／`Vendors\\*`／`Api*`、路徑不以 `api` 開頭，且該 controller 方法本文（去 PHP 註解）含 `return view(`，
    或一層轉呼叫 `return $this->x()` 的 x 含 `return view(`；web.php 先去註解（被註解掉的路由不是頁面）。
歸架：版控中的 `schemas/page-shelf-map.json`（路由檔或 controller → 架；`route:<name|path>` 可逐路由覆寫），缺對應 ⇒ exit 2。
標記：路徑段 `/tenant` 底下或路由名以 `tenant.` 開頭 ⇒ 租客側（DSP-054 未開，不計缺口；業者頁上的「租客資料」分頁不是租客側）；`nthurc` ⇒ 住都特定業者專屬（DSP-065，不入通用基準）；
SPA 具名路由無 `component`（父路由／轉址／`:pathMatch` catch-all）⇒ 不計（DSP-065a，業主 2026-09-19 裁「剔除」：使用者到不了內容，內容由子格承接）。
權限 action（`config/character.php`）與幫助中心段只當粒度對照，另由 `feature_surface.py` 產；後端 API 路由是實作，⛔ 不計。

用法：
  python3 page_surface.py --jgb2 <repo> --branch master --map schemas/page-shelf-map.json \\
      --canon rag-orchestrator/canon/jgb --out-json <run>/page-surface.json --out-md <run>/page-surface.md
  python3 page_surface.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import make_envelope, sha256_path, validate_file, write_json  # noqa: E402
from feature_surface import parse_canon_titles  # noqa: E402

SKILL_VERSION = "0.1-page-surface"
INTERNAL_PREFIXES = ("Admin\\", "Internal\\", "Vendors\\", "Api")
VUE_INDEX = "IndexController@vueIndex"


def _git(repo: str, *args: str) -> str:
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"❌ git {' '.join(args)} 失敗於 {repo}：{out.stderr.strip()}")
    return out.stdout


_NAME_RE = re.compile(r"(?:^\s*|[{,]\s*)name:\s*['\"]([^'\"]+)['\"]")  # 行首或同行 `{`／`,` 之後（單行路由物件也算，如 index.js 的 404）
_PATH_RE = re.compile(r"(?:^\s*|[{,]\s*)path:\s*['\"]([^'\"]*)['\"]")
_COMP_RE = re.compile(r"(?:^\s*|[{,]\s*)component:.*?['\"]@src/pages/([^'\"]+)['\"]")


_CALL_OBJ_RE = re.compile(r"\(\s*\{\s*$|redirect:\s*\{\s*$")  # `next({`／`return next({`／`redirect: {` 開的物件：不是路由定義


def _prev_nonblank(lines: list[str], i: int) -> str:
    j = i - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    return lines[j] if j >= 0 else ""


def parse_spa_routes(text: str, route_file: str) -> list[dict]:
    """逐行掃：每個路由物件的 `name:` 一格；path／component 取同一物件內（name 之後、下一個 name 之前）最先出現者。決定性。
    `beforeEnter` 裡 `next({ name: … })` 與 `redirect: { name: … }` 的 `name:` 不是路由定義（前一行以 `({`／`redirect: {` 收尾）⇒ 跳過——
    否則 phantom 列（空 path／空 component）會在 dedup 搶走真路由（2026-09-19 verifier 抓到 9 個真頁被錯剔）。"""
    lines = text.splitlines()
    rows: list[dict] = []
    i = 0
    while i < len(lines):
        m = _NAME_RE.search(lines[i])
        if not m or _CALL_OBJ_RE.search(_prev_nonblank(lines, i)) or re.search(r"\bnext\s*\(|redirect:", lines[i][:m.start()]):
            i += 1
            continue
        name = m.group(1)
        path = comp = ""
        pm = _PATH_RE.search(lines[i]); cm = _COMP_RE.search(lines[i])  # 單行路由物件：path／component 與 name 同行
        path, comp = (pm.group(1) if pm else ""), (cm.group(1) if cm else "")
        j = i + 1
        while j < len(lines) and not _NAME_RE.match(lines[j]):
            if not path:
                pm = _PATH_RE.search(lines[j])
                if pm:
                    path = pm.group(1)
            if not comp:
                cm = _COMP_RE.search(lines[j])
                if cm:
                    comp = cm.group(1)
            if path and comp:
                break
            j += 1
        rows.append({"kind": "spa", "route_file": route_file, "name": name, "path": path, "component": comp})
        i += 1
    if not rows:
        print(f"❌ {route_file} 解析到 0 條具名路由——格式變了，⛔ 不得當作沒有頁面"); sys.exit(2)
    return rows


_PHP_COMMENT_RE = re.compile(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", re.S)


def strip_php_comments(src: str) -> str:
    """去掉 `/* */` 與行尾 `//` 註解（保留 `http://` 這類字串內的 //）；決定性。"""
    return _PHP_COMMENT_RE.sub("", src)


_WEB_RE = re.compile(
    r"Route::(get|match)\(\s*(?:\[[^\]]*\]\s*,\s*)?'([^']*)'\s*,\s*'([^']+)'\s*\)(?:\s*->\s*name\(\s*'([^']*)'\s*\))?"
)


def parse_blade_pages(web_php: str, controller_src: dict[str, str]) -> tuple[list[dict], dict]:
    """web.php GET／match 路由 → 非內部、非 vueIndex、controller 方法含 `return view(` 者為 blade 頁。回 (rows, stats)。"""
    rows: list[dict] = []
    stats = {"get_routes": 0, "vue_index": 0, "internal": 0, "api_path": 0, "no_view": 0, "controller_missing": 0}
    for m in _WEB_RE.finditer(strip_php_comments(web_php)):
        verb, path, target, name = m.groups()
        stats["get_routes"] += 1
        if target == VUE_INDEX:
            stats["vue_index"] += 1
            continue
        if target.startswith(INTERNAL_PREFIXES):
            stats["internal"] += 1
            continue
        if path.lstrip("/").startswith("api"):
            stats["api_path"] += 1
            continue
        ctrl, _, method = target.partition("@")
        src = controller_src.get(ctrl)
        if src is None:
            stats["controller_missing"] += 1
            continue
        if not _renders_view(src, method):
            stats["no_view"] += 1
            continue
        rows.append({"kind": "blade", "route_file": "routes/web.php", "name": name or path, "path": path,
                     "component": f"{ctrl}@{method}"})
    return rows, stats


def _renders_view(src: str, method: str) -> bool:
    """方法本文（去註解後）含 `return view(`；或一層轉呼叫 `return $this->x(...)` 且 x 含 `return view(`。"""
    clean = strip_php_comments(src)
    body = _method_body(clean, method)
    if body is None:
        return False
    if "return view(" in body:
        return True
    for callee in re.findall(r"return\s+\$this->([A-Za-z_]\w*)\(", body):
        sub = _method_body(clean, callee)
        if sub is not None and "return view(" in sub:
            return True
    return False


def _method_body(src: str, method: str) -> str | None:
    m = re.search(r"function\s+" + re.escape(method) + r"\s*\(", src)
    if not m:
        return None
    start = src.find("{", m.end())
    depth, k = 0, start
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[start:k]
        k += 1
    return src[start:]


def build_cells(spa: list[dict], blade: list[dict], shelf_map: dict) -> list[dict]:
    cells = []
    seen: dict[str, tuple[str, str]] = {}
    for r in sorted(spa + blade, key=lambda r: (r["kind"], r["route_file"], r["name"], r["path"])):
        # blade 頁用 `page:web:` 命名空間：同名的 blade／SPA 是兩個不同頁（如 contracts.show），⛔ 不得互相吞掉
        uid = (f"page:{r['name']}" if r["name"] else f"page:{r['route_file']}:{r['path']}") if r["kind"] == "spa" else f"page:web:{r['name'] or r['path']}"
        if uid in seen:
            if seen[uid] != (r["path"], r["component"]):
                print(f"❌ 同名路由內容不同：{uid} {seen[uid]} vs {(r['path'], r['component'])}——parser 抓到 phantom 列，⛔ 不得靜默取第一筆"); sys.exit(2)
            continue
        seen[uid] = (r["path"], r["component"])
        key = r["route_file"] if r["kind"] == "spa" else r["component"].split("@")[0]
        route_key = f"route:{r['name'] or r['path']}"
        if route_key in shelf_map:
            key = route_key  # 逐路由覆寫（同一 controller 服務多架時）
        hay = (r["name"] + " " + r["path"] + " " + r["component"]).lower()
        vendor_specific = "nthurc" in hay
        tenant = bool(re.match(r"^/?tenant(/|$)", r["path"])) or r["name"].startswith("tenant.")  # 租客側＝路徑段 `tenant` 底下的頁；業者頁上的 tenant-basic 之類分頁不是
        no_page = r["kind"] == "spa" and not r["component"]  # 具名路由但無頁面元件（父／轉址／catch-all）⇒ 不計（DSP-065a）
        shelf = shelf_map.get(key)
        if shelf is None and not vendor_specific:
            print(f"❌ 歸架表缺對應：{key}（格 {uid}）——⛔ 不得靜默不歸架"); sys.exit(2)
        cells.append({"unit_id": uid, "kind": r["kind"], "label": r["name"] or r["path"], "path": r["path"],
                      "component": r["component"], "source": r["route_file"], "shelf": shelf or "",
                      "side": "租客側" if tenant else "房東側", "vendor_specific": vendor_specific, "no_page": no_page,
                      "in_baseline": (not tenant) and (not vendor_specific) and (not no_page) and bool(shelf) and shelf != "-"})
    return cells


def self_test() -> int:
    fails = []
    spa = parse_spa_routes("export default [{\n beforeEnter: (to, from, next)=>{\n  if (x) {\n   return next({\n    name: 'a.index',\n    params: {}\n   })\n  }\n  next({\n\n   name: 'a.child'\n  })\n },\n redirect: {\n  name: 'a.index'\n },\n name: 'a.index',\n path: '/a',\n component: ()=>import('@src/pages/a/Index.vue'),\n children: [{\n name: 'a.child',\n path: 'c',\n component: ()=>import('@src/pages/a/c/Index.vue') }] },\n { path: '/:pathMatch(.*)*', name: '404', component: ()=>import('@src/pages/404.vue') },\n { beforeEnter: (to, from, next)=>{ next({ name: 'a.index' }) } },\n { redirect: { name: 'a.index' } },\n { name: 'a.one', path: '/one', component: ()=>import('@src/pages/one/Index.vue') }]", "a.js")
    if [(r["name"], r["path"], r["component"]) for r in spa] != [("a.index", "/a", "a/Index.vue"), ("a.child", "c", "a/c/Index.vue"), ("404", "/:pathMatch(.*)*", "404.vue"), ("a.one", "/one", "one/Index.vue")]:
        fails.append(f"① SPA parser 錯（next({{ name }})／redirect 的 name 不是路由）：{spa}")
    try:
        build_cells([{"kind": "spa", "route_file": "a.js", "name": "a.index", "path": "", "component": ""}] + spa, [], {"a.js": "A"}); fails.append("①b 同名不同內容沒大聲失敗")
    except SystemExit as e:
        if e.code != 2:
            fails.append(f"①b exit code 應為 2，實際 {e.code}")
    web = ("Route::get('/x', 'IndexController@vueIndex')->name('x');\n"
           "// Route::get('/old', 'OldController@index')->name('old.index');\n"
           "Route::get('/sign', 'ContractController@sign')->name('contracts.sign');\n"
           "Route::match(['get','post'], '/notifications', 'NotificationController@index')->name('notifications.index');\n"
           "Route::get('/api/z', 'ZController@z')->name('api.z');\n"
           "Route::get('/adm', 'Admin\\YController@y')->name('admin.y');\n"
           "Route::get('/pdf', 'BillController@pdf')->name('bills.pdf');\n")
    ctrls = {"NotificationController": "class N { public function index() { $x=1; return view('n.index'); } }",
             "BillController": "class B { public function pdf() { return response()->download('x'); } }",
             "OldController": "class O { public function index() { return view('old'); } }",
             "ContractController": "class C { public function sign() { /* } */ return $this->render(); } public function render() { return view('c.sign'); } }"}
    blade, st = parse_blade_pages(web, ctrls)
    if [b["name"] for b in blade] != ["contracts.sign", "notifications.index"] or st["vue_index"] != 1 or st["internal"] != 1 or st["api_path"] != 1 or st["no_view"] != 1 or st["get_routes"] != 6:
        fails.append(f"② blade 判定錯：{[b['name'] for b in blade]} {st}")
    cells = build_cells(spa, blade, {"a.js": "A", "NotificationController": "B", "ContractController": "D"})
    if [c["unit_id"] for c in cells] != ["page:web:contracts.sign", "page:web:notifications.index", "page:404", "page:a.child", "page:a.index", "page:a.one"] or not all(c["in_baseline"] for c in cells):
        fails.append(f"③ cells 錯：{[c['unit_id'] for c in cells]}")
    c2 = build_cells(spa + [{"kind": "spa", "route_file": "a.js", "name": "nthurc.list", "path": "/nthurc", "component": "nthurc/Index.vue"},
                            {"kind": "spa", "route_file": "a.js", "name": "tenant.bills", "path": "/tenant/bills", "component": "t.vue"},
                            {"kind": "spa", "route_file": "a.js", "name": "contracts.edit.tenantBasic", "path": "tenant-basic", "component": "contracts/edit/tenantBasic/Index.jsx"},
                            {"kind": "spa", "route_file": "a.js", "name": "a.list", "path": "", "component": ""},
                            {"kind": "spa", "route_file": "a.js", "name": "a.404", "path": ":pathMatch(.*)*", "component": ""}], blade, {"a.js": "A", "NotificationController": "B", "ContractController": "D"})
    flags = {c["unit_id"]: (c["vendor_specific"], c["side"], c["in_baseline"]) for c in c2}
    if flags["page:nthurc.list"] != (True, "房東側", False) or flags["page:tenant.bills"] != (False, "租客側", False) or flags["page:contracts.edit.tenantBasic"] != (False, "房東側", True):
        fails.append(f"④ 住都／租客標記錯：{flags}")
    nop = {c["unit_id"]: c["no_page"] for c in c2}
    if flags["page:a.list"] != (False, "房東側", False) or flags["page:a.404"] != (False, "房東側", False) or not (nop["page:a.list"] and nop["page:a.404"]) or nop["page:a.index"]:
        fails.append(f"④b 無頁面元件路由未剔除：{flags} {nop}")
    try:
        build_cells(spa, [], {}); fails.append("⑤ 缺歸架表沒大聲失敗")
    except SystemExit as e:
        if e.code != 2:
            fails.append(f"⑤ 缺歸架表 exit code 應為 2，實際 {e.code}")
    try:
        parse_spa_routes("nothing", "z.js"); fails.append("⑥ 空路由檔沒大聲失敗")
    except SystemExit:
        pass
    for f in fails:
        print("❌ self-test:", f)
    if not fails:
        print("✅ self-test 通過（正對照 7、負對照 3）")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("--jgb2", required=True)
    ap.add_argument("--branch", default="master")
    ap.add_argument("--map", required=True)
    ap.add_argument("--canon", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    sha = _git(a.jgb2, "rev-parse", a.branch).strip()
    files = [p for p in _git(a.jgb2, "ls-tree", "-r", "--name-only", a.branch, "src/routes").splitlines()
             if p.endswith(".js") and "__tests__" not in p]
    spa: list[dict] = []
    for p in files:
        spa += parse_spa_routes(_git(a.jgb2, "show", f"{a.branch}:{p}"), os.path.basename(p))
    web = _git(a.jgb2, "show", f"{a.branch}:routes/web.php")
    ctrl_names = sorted({t.partition("@")[0] for _, _, t, _ in _WEB_RE.findall(web) if not t.startswith(INTERNAL_PREFIXES) and t != VUE_INDEX})
    ctrl_src: dict[str, str] = {}
    for c in ctrl_names:
        rel = "app/Http/Controllers/" + c.replace("\\", "/") + ".php"
        out = subprocess.run(["git", "-C", a.jgb2, "show", f"{a.branch}:{rel}"], capture_output=True, text=True)
        if out.returncode == 0:
            ctrl_src[c] = out.stdout
    blade, stats = parse_blade_pages(web, ctrl_src)
    shelf_map = json.load(open(a.map, encoding="utf-8"))
    cells = build_cells(spa, blade, shelf_map)
    canon = parse_canon_titles(a.canon)
    base = [c for c in cells if c["in_baseline"]]
    payload = {
        "sources": {"jgb2": a.jgb2, "branch": a.branch, "jgb2_sha": sha, "map": a.map, "canon": a.canon},
        "blade_stats": stats,
        "counts": {"route_files": len(files), "spa_named_routes": len(spa), "blade_pages": len(blade), "units": len(cells),
                   "baseline": len(base), "tenant": sum(1 for c in cells if c["side"] == "租客側" and not c["vendor_specific"]),
                   "vendor_specific": sum(1 for c in cells if c["vendor_specific"]),
                   "not_counted": sum(1 for c in cells if not c["in_baseline"] and c["side"] != "租客側" and not c["vendor_specific"]),
                   "no_page": sum(1 for c in cells if c["no_page"] and c["side"] != "租客側" and not c["vendor_specific"]),
                   "canon_fines": len(canon)},
        "units": cells, "canon_titles": canon,
    }
    env = make_envelope(step="page_surface", skill_version=SKILL_VERSION, deterministic=True, payload=payload,
                        inputs_sha={"jgb2_sha": sha, "map": sha256_path(a.map), "canon": sha256_path(a.canon)})
    write_json(a.out_json, env)
    validate_file(a.out_json, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "page-surface.json"))
    by_shelf: dict[str, list[dict]] = {}
    for c in base:
        by_shelf.setdefault(c["shelf"], []).append(c)
    md = [f"# 大綱覆蓋基準：JGB 頁面樹（步 0a，DSP-065）— {a.branch} @ {sha[:12]}", "",
          f"SPA 路由檔 {len(files)}、具名路由 {len(spa)}；blade 頁 {len(blade)}（web.php GET/match {stats['get_routes']}：vueIndex {stats['vue_index']}、內部 {stats['internal']}、api 路徑 {stats['api_path']}、無 view {stats['no_view']}、controller 缺 {stats['controller_missing']}）。",
          f"格 {len(cells)}＝基準 {len(base)}＋租客側 {payload['counts']['tenant']}（未開）＋住都專屬 {payload['counts']['vendor_specific']}（不入基準）＋不計 {payload['counts']['not_counted']}（無頁面元件 {payload['counts']['no_page']}＋非功能 {payload['counts']['not_counted'] - payload['counts']['no_page']}）。正本 {len(canon)} 條。", ""]
    for sh in sorted(by_shelf):
        md.append(f"## {sh}（{len(by_shelf[sh])} 格）")
        md.append("")
        md.append("| 格 | 路徑 | 頁面／controller | 來源 |")
        md.append("|---|---|---|---|")
        for c in by_shelf[sh]:
            md.append(f"| `{c['label']}` | `{c['path']}` | {c['component']} | {c['source']} |")
        md.append("")
    others = [c for c in cells if not c["in_baseline"]]
    md += ["## 不入基準（租客側／住都／不計）", "", "| 格 | 原因 | 路徑 |", "|---|---|---|"]
    for c in others:
        why = "租客側未開" if c["side"] == "租客側" else ("住都專屬" if c["vendor_specific"] else ("不計（無頁面元件：父／轉址／catch-all）" if c.get("no_page") else "不計（非功能）"))
        md.append(f"| `{c['label']}` | {why} | `{c['path']}` |")
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"✅ 頁面樹基準：格 {len(cells)}＝基準 {len(base)}＋租客 {payload['counts']['tenant']}＋住都 {payload['counts']['vendor_specific']}＋不計 {payload['counts']['not_counted']}（無頁面元件 {payload['counts']['no_page']}）；SPA {len(spa)}、blade {len(blade)} → {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
