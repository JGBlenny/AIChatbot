#!/usr/bin/env python3
"""一次性工具（不 commit）：抓 JGB help 中心「新手上路」「常見問題」合約相關文章全文轉純文字素材。

contract-conversational-facets 任務 4.1（R9.1）。
來源：公開 API /api2/helpCenter/getGroups、/api2/helpCenter/post?slug=
輸出：.kiro/specs/contract-conversational-facets/materials/help/<group>/<slug>.md ＋ index.md
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.jgbsmart.com/api2/helpCenter"
OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   ".kiro", "specs", "contract-conversational-facets", "materials", "help")

# 目標群組（research.md §七：新手上路＋常見問題）
TARGET_GROUPS = {"onboarding", "faq"}

# 合約相關過濾（標題關鍵字；寬鬆抓、人工再篩）
KEYWORDS = ["合約", "簽約", "簽署", "租約", "點交", "點退", "退租", "解約", "終止",
            "續約", "電子簽", "承租", "房客資料", "條款", "用印", "章", "滯納金",
            "審閱", "藍字", "複製", "歷史合約", "建約", "租客邀請", "驗證"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _to_text(html_str):
    t = html_str or ""
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", t, flags=re.I)
    t = re.sub(r"<li[^>]*>", "• ", t, flags=re.I)
    t = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r"[圖:\1]", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def main():
    groups = _get(f"{BASE}/getGroups")
    picked = []
    for g in groups:
        if g["slug"] not in TARGET_GROUPS:
            continue
        for sg in g.get("sub_groups") or []:
            for p in sg.get("posts") or []:
                title = p.get("title") or ""
                if any(k in title for k in KEYWORDS):
                    picked.append({"group": g["slug"], "sub": sg["title"],
                                   "slug": p["slug"], "title": title})
    print(f"標題過濾命中 {len(picked)} 篇（人工可再增刪）")

    os.makedirs(OUT, exist_ok=True)
    index = []
    for i, p in enumerate(picked, 1):
        try:
            post = _get(f"{BASE}/post?slug={urllib.request.quote(p['slug'])}")
        except Exception as e:
            print(f"  ✗ {p['slug']}: {e}")
            continue
        body = _to_text((((post.get("data") or {}).get("post")) or {}).get("content") or "")
        sub_dir = os.path.join(OUT, p["group"])
        os.makedirs(sub_dir, exist_ok=True)
        safe_slug = re.sub(r"[^\w\-]", "_", p["slug"])
        path = os.path.join(sub_dir, f"{safe_slug}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {p['title']}\n\n> 來源：help 中心 {p['group']}/{p['sub']}｜slug={p['slug']}\n\n{body}\n")
        index.append(f"- [{p['group']}/{p['sub']}] {p['title']}（{p['slug']}，{len(body)} 字）")
        print(f"  ✓ {i}/{len(picked)} {p['title']}")
        time.sleep(0.3)

    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as f:
        f.write("# 合約相關 help 中心素材索引（任務 4.1）\n\n" + "\n".join(index) + "\n")
    print(f"完成：{len(index)} 篇 → {os.path.abspath(OUT)}")


if __name__ == "__main__":
    sys.exit(main())
