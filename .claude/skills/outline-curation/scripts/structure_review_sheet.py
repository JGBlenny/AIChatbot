#!/usr/bin/env python3
"""structure_review_sheet：決定性產「歸屬審核單」Markdown（knowledge-outline-and-intent-architecture 任務 9.3⑤／9.5 前置）。

輸入：`--run-dir runs/<aud>-<date>/`（讀 `kb-rows.json`／`structure-proposal.json`；三角度提議優先讀
envelope 的 `raw_outputs_path`，讀不到才退回 `payload.proposals`；舊標題讀 `structure/items.json`）。
輸出（依序）：
  A 舊→新（op、三角度各自歸哪個粗目、⚠️ 三角度分歧或與合成結果不同）
  B split（一個舊細目拆成多個新細目）
  C merge（多個舊細目併成一個新細目，含 `reason`）
  D rejected_alternatives（合成否決的替代方案）
  E 粗目分佈（合成後每個粗目的細目數）
  F 待審清單——⚠️ **本腳本輸入不含 `--canon`，無法讀到舊細目的實際講法／`see_also`／`reviewed`
    內容，故只列「結構上預測會受影響」的細目與拆分群組；實際 `pending-*.json` 筆數要
    `apply_proposal.py --canon` 真的套用後才知道**（F2 附此提醒，⛔ 不假裝算得出筆數）。

決定性：同輸入兩次逐位元相同（無時間戳；所有清單依 id 排序）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_ci = _load_sibling("canon_items")
_sp = _load_sibling("structure_propose")

ANGLE_KEYS = [k for k, _def in _sp.ANGLES]


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _repo_root_candidates(run_dir: str) -> list:
    """`raw_outputs_path` 是相對 repo 根的字串；由 `run_dir` 往上找可能的 repo 根（容器內＝`/`，本機＝實際 repo 根）。"""
    out = []
    cur = os.path.abspath(run_dir)
    for _ in range(8):
        out.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    out.append("/")
    return out


def load_angle_proposals(run_dir: str, envelope: dict, proposals3: list) -> dict:
    """回 `{angle_key: proposal_dict}`。優先讀 `raw_outputs_path/angle-<key>.json`，讀不到（缺檔／已被
    `raw_purge.py` 清掉）才退回 `payload.proposals`（用 `angle` 欄比對）。"""
    by_angle_fallback = {p.get("angle"): p for p in proposals3}
    out = {}
    raw_path = envelope.get("raw_outputs_path")
    for key in ANGLE_KEYS:
        found = None
        if raw_path:
            for root in _repo_root_candidates(run_dir):
                cand = os.path.join(root, raw_path, f"angle-{key}.json")
                if os.path.isfile(cand):
                    try:
                        found = _load_json(cand)
                    except (OSError, json.JSONDecodeError):
                        found = None
                    break
        if found is None:
            found = by_angle_fallback.get(key)
        out[key] = found
    return out


def load_old_titles(run_dir: str) -> dict:
    path = os.path.join(run_dir, "structure", "items.json")
    if not os.path.isfile(path):
        return {}
    items = _load_json(path)
    return {it["id"]: it.get("title", "") for it in items}


def coarse_of(angle_proposal: dict | None, old_full_id: str) -> str:
    if not angle_proposal:
        return "?"
    for f in angle_proposal.get("fines", []):
        if old_full_id in (f.get("merge_of") or []) or old_full_id in (f.get("split_from") or []):
            return f.get("coarse_id", "?")
    return "?"


def build_sections(run_dir: str, envelope: dict) -> dict:
    payload = envelope["payload"]
    proposal = payload["synthesis"]
    proposals3 = payload.get("proposals", [])
    angle_proposals = load_angle_proposals(run_dir, envelope, proposals3)
    old_titles = load_old_titles(run_dir)

    id_map = proposal["id_map"]
    fines_by_id = {f["id"]: f for f in proposal["fines"]}
    old_to_news: dict = {}
    for row in id_map:
        old = row.get("old")
        if old:
            old_to_news.setdefault(_ci.bare_id(old), set()).add(row["new"])

    def is_split(bare: str) -> bool:
        return len(old_to_news.get(bare, ())) > 1

    def srcs_of(new_id: str) -> list:
        f = fines_by_id.get(new_id, {})
        return _dedupe([_ci.bare_id(s) for s in (list(f.get("merge_of") or []) + list(f.get("split_from") or []))])

    # A：舊→新
    rows_a = []
    for row in sorted(id_map, key=lambda r: (r.get("old") or "", r["new"])):
        old_full = row.get("old")
        if not old_full:
            continue
        bare = _ci.bare_id(old_full)
        new_id = row["new"]
        new_title = fines_by_id.get(new_id, {}).get("title", "")
        angles = [coarse_of(angle_proposals.get(k), old_full) for k in ANGLE_KEYS]
        final_coarse = fines_by_id.get(new_id, {}).get("coarse_id", "?")
        divergent = len(set(angles)) > 1 or any(a != final_coarse for a in angles if a != "?")
        rows_a.append({
            "old": old_full, "old_title": old_titles.get(old_full, ""),
            "new": new_id, "new_title": new_title, "op": row["op"],
            "angles": angles, "divergent": divergent,
        })

    # B：split
    rows_b = []
    for bare in sorted(k for k in old_to_news if is_split(k)):
        children = sorted(old_to_news[bare])
        rows_b.append({
            "old": _ci.TMP_PREFIX + bare, "old_title": old_titles.get(_ci.TMP_PREFIX + bare, ""),
            "children": [{"id": c, "title": fines_by_id.get(c, {}).get("title", "")} for c in children],
        })

    # C：merge（目標的來源數 >1，⛔ 不管來源是否本身被拆分——兩者可能同時成立）
    rows_c = []
    for new_id in sorted(fines_by_id):
        srcs = srcs_of(new_id)
        if len(srcs) > 1:
            rows_c.append({
                "new": new_id, "new_title": fines_by_id[new_id].get("title", ""),
                "from": [_ci.TMP_PREFIX + s for s in srcs],
                "reason": fines_by_id[new_id].get("reason", ""),
            })

    # D：rejected_alternatives
    rows_d = list(proposal.get("rejected_alternatives", []))

    # E：粗目分佈
    coarse_order = [c["id"] for c in proposal["coarses"]]
    counts = {cid: 0 for cid in coarse_order}
    for f in proposal["fines"]:
        counts[f["coarse_id"]] = counts.get(f["coarse_id"], 0) + 1

    # F：待審清單（結構預測，⛔ 不含實際講法／see_also 筆數——本腳本輸入不含 --canon）
    rows_f1 = []
    for new_id in sorted(fines_by_id):
        srcs = srcs_of(new_id)
        split_members = [s for s in srcs if is_split(s)]
        if len(srcs) > 1 or split_members:
            reason = []
            if len(srcs) > 1:
                reason.append("merge")
            if split_members:
                reason.append("split-child")
            rows_f1.append({"new": new_id, "reason": "+".join(reason)})
    rows_f2 = rows_b  # 拆分來源預測：與 B 同一組（子細目清單），實際筆數見 apply 產出

    return {
        "A": rows_a, "B": rows_b, "C": rows_c, "D": rows_d, "E": (coarse_order, counts), "F1": rows_f1, "F2": rows_f2,
    }


def _dedupe(items) -> list:
    seen: set = set()
    out: list = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def render_markdown(audience: str, sections: dict) -> str:
    lines = [f"# 步 2 歸屬審核單（{audience}，自動產出）", ""]
    lines.append("> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。")
    lines.append("")

    lines.append("## A. 舊細目 → 新細目（合成結果）")
    lines.append("")
    lines.append(f"| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（{'/'.join(ANGLE_KEYS)}） | 業主 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(sections["A"], 1):
        mark = "⚠️ " if r["divergent"] else ""
        lines.append(f"| {i} | `{r['old']}` | {r['old_title']} | `{r['new']}` | {r['new_title']} | {r['op']} | "
                      f"{mark}{'/'.join(r['angles'])} | |")
    lines.append("")

    lines.append("## B. 拆分（split）——一個舊細目拆成多個新細目")
    lines.append("")
    if sections["B"]:
        lines.append("| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |")
        lines.append("|---|---|---|---|")
        for r in sections["B"]:
            children = "；".join(f"`{c['id']}`《{c['title']}》" for c in r["children"])
            lines.append(f"| `{r['old']}` | {r['old_title']} | {children} | |")
    else:
        lines.append("（本次無拆分）")
    lines.append("")

    lines.append("## C. 合併（merge）——多個舊細目併成一個新細目")
    lines.append("")
    if sections["C"]:
        lines.append("| 新細目 | 併自 | 理由 | 業主 |")
        lines.append("|---|---|---|---|")
        for r in sections["C"]:
            lines.append(f"| `{r['new']}`《{r['new_title']}》 | {'＋'.join(f'`{x}`' for x in r['from'])} | {r['reason']} | |")
    else:
        lines.append("（本次無合併）")
    lines.append("")

    lines.append("## D. 合成否決的替代方案（⚠️ 你可以翻案）")
    lines.append("")
    if sections["D"]:
        lines.append("| 被否決 | 理由 | 業主 |")
        lines.append("|---|---|---|")
        for r in sections["D"]:
            lines.append(f"| {r.get('alternative', '')} | {r.get('reason', '')} | |")
    else:
        lines.append("（合成未記錄被否決的替代方案）")
    lines.append("")

    lines.append("## E. 粗目分佈（合成後）")
    lines.append("")
    coarse_order, counts = sections["E"]
    lines.append("| " + " | ".join(coarse_order) + " |")
    lines.append("|" + "---|" * len(coarse_order))
    lines.append("| " + " | ".join(str(counts[c]) for c in coarse_order) + " |")
    lines.append("")

    lines.append("## F. 待審清單")
    lines.append("")
    lines.append("⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的"
                  "實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；"
                  "確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／"
                  "`pending-phrasings.json`／`pending-see_also.json`。")
    lines.append("")
    lines.append("### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目")
    lines.append("")
    if sections["F1"]:
        lines.append("| 新細目 | 原因 |")
        lines.append("|---|---|")
        for r in sections["F1"]:
            lines.append(f"| `{r['new']}` | {r['reason']} |")
    else:
        lines.append("（無）")
    lines.append("")
    lines.append("### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源")
    lines.append("")
    if sections["F2"]:
        lines.append("| 舊細目 | 子細目數 |")
        lines.append("|---|---|")
        for r in sections["F2"]:
            lines.append(f"| `{r['old']}` | {len(r['children'])} |")
    else:
        lines.append("（無）")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run-dir", required=True, help="runs/<audience>-<date>/")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    structure_path = os.path.join(a.run_dir, "structure-proposal.json")
    envelope = _load_json(structure_path)
    audience = envelope["payload"]["synthesis"]["fines"][0]["id"].split("/")[0] if envelope["payload"]["synthesis"]["fines"] else "?"
    sections = build_sections(a.run_dir, envelope)
    md = render_markdown(audience, sections)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"[structure_review_sheet] ok A={len(sections['A'])} B={len(sections['B'])} C={len(sections['C'])} "
          f"D={len(sections['D'])} F1={len(sections['F1'])} → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
