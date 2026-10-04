#!/usr/bin/env python3
"""頁面入口檔的閉包（Plan 9.26）：入口檔＋其 `src/pages/` 內 import 與子路由——供 `endpoint_progress.py --closure`。

量尺原本只認「細目 `sources` 逐字引用頁面入口檔」才算覆蓋；細目引用的若是該頁實際渲染的子元件
（`parts/forget/Password.vue`、`facilities/SocialHousing.vue`…）就算不到（Plan 9.25 §5 對碼：11 頁「真缺口」中 10 頁屬此）。
本腳本從 jgb2 **釘住 commit 的匯出**（⛔ 工作樹；重建見 `review_pipeline/README.md`）靜態解析：
- `import … from '…'`／`import('…')`（`@src/` 與相對路徑、副檔名與 `index`／`Index`）；
- `src/routes/*.js` 的子路由：以大括號與 `children:` 追蹤巢狀，同檔 `const X = [ … ]` 被 `...X` 展開處就地內嵌
  （⛔ 以路由名稱前綴猜：名稱前綴與實際巢狀不一定一致）。
**只收 `src/pages/` 底下的檔**（⛔ `src/components` 等共用元件：一個共用按鈕不得點亮所有頁）；也 ⛔ 以「同目錄」比對
（`users/auth/` 下的 `Forget.vue`／`Login.vue`／`Verify.vue` 是不同頁）。

用法：page_import_closure.py --export <jgb2 匯出根目錄> --surface <page-surface.json> --sha <釘住 commit> --out <closure.json>
輸出：{"sha": …, "pages": {"<component>": ["users/auth/Forget.vue", "users/auth/parts/forget/Password.vue", …]}}
（路徑相對 `src/pages/`，含入口檔本身）。前置拿不到（匯出無 `src/pages`、入口檔不存在、SPA 頁 0）⇒ 非 0 並印原因（⛔ 不靜默）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

IMPORT_RE = re.compile(r"""(?:\bimport\s+(?:[^'"`;]*?\sfrom\s+)?|\bimport\s*\(\s*)['"]([^'"]+)['"]""")
COMP_RE = re.compile(r"""\bcomponent\s*:\s*\(\s*\)\s*=>\s*import\(\s*['"]@src/pages/([^'"]+)['"]""")
EXTS = ("", ".vue", ".jsx", ".js", ".ts", ".tsx")
INDEX = ("index.vue", "index.jsx", "index.js", "index.ts", "Index.vue", "Index.jsx", "Index.js", "Index.ts")


def resolve(spec: str, here: str, root: str) -> str | None:
    if spec.startswith("@src/"):
        base = os.path.join(root, "src", spec[len("@src/"):])
    elif spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(here), spec))
    else:
        return None  # 第三方套件
    for e in EXTS:
        if os.path.isfile(base + e):
            return base + e
    if os.path.isdir(base):
        for n in INDEX:
            if os.path.isfile(os.path.join(base, n)):
                return os.path.join(base, n)
    return None


def _balanced(text: str, start: int) -> int:
    """text[start] 是 '['：回傳對應 ']' 的位置。"""
    d = 0
    for j in range(start, len(text)):
        if text[j] == "[":
            d += 1
        elif text[j] == "]":
            d -= 1
            if d == 0:
                return j
    raise SystemExit("❌ routes 陣列括號不平衡")


def inline_spreads(text: str) -> str:
    """同檔 `const NAME = [ … ]` 被 `...NAME` 展開時，把陣列內容就地內嵌（否則 `contracts.edit` 的分頁全漏算）。"""
    arrays = {}
    for m in re.finditer(r"\b(?:export\s+)?const\s+(\w+)\s*=\s*\[", text):
        s = m.end() - 1
        arrays[m.group(1)] = text[s + 1:_balanced(text, s)]
    for _ in range(5):
        new = re.sub(r"\.\.\.(\w+)", lambda m: arrays.get(m.group(1), m.group(0)), text)
        if new == text:
            break
        text = new
    return text


def route_children(root: str) -> dict:
    """{父路由 component: [所有子孫路由 component]}——子路由經 router-view 渲染在父頁裡。"""
    out: dict = {}
    rdir = os.path.join(root, "src", "routes")
    for fn in sorted(os.listdir(rdir)):
        if not fn.endswith(".js"):
            continue
        text = open(os.path.join(rdir, fn), encoding="utf-8", errors="replace").read()
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"(?m)//.*$", "", text)
        text = inline_spreads(text)
        depth = 0
        pending_children = False
        child_owner = []  # 每個開著的 '['：(所在深度, 擁有它的路由物件) 或 (None, None)
        objs = []  # 每個開著的 '{'：{"comp": …, "parent": 外層路由物件}
        for i, ch in enumerate(text):
            if ch == "{":
                owner = child_owner[-1][1] if child_owner and child_owner[-1][0] == depth else None
                objs.append({"comp": None, "parent": owner})
                depth += 1
            elif ch == "}":
                depth -= 1
                o = objs.pop() if objs else None
                if o and o["comp"]:
                    anc = o["parent"]
                    while anc is not None:
                        if anc["comp"]:
                            out.setdefault(anc["comp"], set()).add(o["comp"])
                        anc = anc["parent"]
            elif ch == "[":
                if pending_children and objs:
                    child_owner.append((depth, objs[-1]))
                    pending_children = False
                else:
                    child_owner.append((None, None))
            elif ch == "]":
                if child_owner:
                    child_owner.pop()
            elif ch == "c" and objs:
                if re.match(r"children\s*:", text[i:i + 20]):
                    pending_children = True
                else:
                    m = COMP_RE.match(text, i)
                    if m and objs[-1]["comp"] is None:
                        objs[-1]["comp"] = m.group(1)
    return {k: sorted(v) for k, v in out.items()}


def closure(entry: str, root: str) -> list[str]:
    pages = os.path.join(root, "src", "pages") + os.sep
    seen, stack = set(), [entry]
    while stack:
        f = stack.pop()
        if f in seen or not f.startswith(pages):
            continue
        seen.add(f)
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for spec in IMPORT_RE.findall(text):
            r = resolve(spec, f, root)
            if r and r.startswith(pages) and r not in seen:
                stack.append(r)
    return sorted(os.path.relpath(p, pages) for p in seen)


def build(export: str, units: list) -> dict:
    kids = route_children(export)
    out = {}
    for comp in sorted({u["component"] for u in units}):
        entry = os.path.join(export, "src", "pages", comp)
        if not os.path.isfile(entry):
            raise SystemExit(f"❌ 入口檔不存在：src/pages/{comp}")
        files = set(closure(entry, export))
        for k in kids.get(comp, []):
            ke = os.path.join(export, "src", "pages", k)
            if os.path.isfile(ke):
                files |= set(closure(ke, export))
        out[comp] = sorted(files)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", required=True)
    ap.add_argument("--surface", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if not os.path.isdir(os.path.join(a.export, "src", "pages")):
        raise SystemExit(f"❌ 匯出沒有 src/pages：{a.export}")
    units = [u for u in json.load(open(a.surface, encoding="utf-8"))["payload"]["units"]
             if u.get("in_baseline") and u.get("kind") == "spa" and u.get("component")]
    if not units:
        raise SystemExit("❌ in_baseline 的 SPA 頁為 0")
    out = build(a.export, units)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"sha": a.sha, "pages": out}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    sizes = sorted(len(v) for v in out.values())
    print(f"[closure] spa components {len(out)}; files per page min {sizes[0]} median {sizes[len(sizes)//2]} max {sizes[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
