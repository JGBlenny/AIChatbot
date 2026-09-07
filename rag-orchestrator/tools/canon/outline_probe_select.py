"""4.4a 步 2 探針選題（凍結前置工具）：`tools/canon/outline_probe_select.py`
（spec knowledge-outline-and-intent-architecture・任務 4.4；Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-4.4a-outline-probe-definition-20260907.md`
§2「選題規則」／§1 H7／§4「4.4b 前置改動」）。

決定性、規則檔驅動的選題器：七層（A–G）依 Plan §2 的機械可重算定義各自圈出母體，
再用 `md5(seed_prefix + q)`（`q` 取原字串、⛔ 不正規化）升冪排序取前 N；母體不足
⇒ 該層全取並記 `insufficient: true`（⛔ 不假裝湊滿）。

⛔ 本工具本身不寫「凍結用」的正式輸出——業主尚未核可 gold 表（`--sub-map`／
`--scenario-gold`）前，呼叫端不應對著預設路徑跑非 `--dry-run`；`--dry-run` 只印
每層母體與會取幾筆，不寫任何檔案。

Fail loud（大聲失敗，⛔ 不靜默跳過）：
- 任何輸入檔缺失 ⇒ 印明原因、非 0 退出。
- 任一層母體為空 ⇒ 非 0 退出。
- A／C 層某筆的 `sub` 不在 `--sub-map` 的鍵集合裡 ⇒ 非 0 退出（列出缺的 sub，
  ⛔ 不靜默排除那一筆——那等於用選題腳本偷改母體定義）。
- 422 重生的三項全等（`n`／`by_type`／`excluded_frozen`）與 `--rule` 記錄不符
  ⇒ 非 0 退出（G 層的材料本身壞了，不能假裝正常繼續選）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import index_eval as ie  # noqa: E402 — 同目錄，重用 422 重生／md5 排序慣例／repo 根解析

EXIT_OK = 0
EXIT_FAIL = 2

DEFAULT_SEED_PREFIX = "outline-probe-20260906:"

#: F 層劇本集合（Plan §2 凍結；⛔ 不是「turn≥3 全動態篩」——`scenarios-v1.json`
#: 裡 `B-scale`（600 戶敏感規模）turn 數也 ≥3，但業主已裁定不入 F，見 Plan §2
#: 表格明列的三個劇本 id／16 turn 合計）。
F_SCENARIO_IDS = ("S1-landlord", "S2-agency", "D-import")

#: G 層的跨粗目四篇（Plan §2；gold＝koyu-article-map 的 `fine_ids`，任一命中即算）。
G_CROSS_COARSE_ARTICLES = ("Landlordonboarding00", "onboarding6", "qa05", "qa06")

STRATA_TAKE_N = {"A": 10, "B": 5, "C": 5, "D": 5, "E": 5, "F": 3, "G": 3}


class SelectorFailure(SystemExit):
    def __init__(self, msg: str):
        print(f"[outline_probe_select] {msg}", file=sys.stderr)
        super().__init__(EXIT_FAIL)


def _load_json(path: str) -> Any:
    if not os.path.isfile(path):
        raise SelectorFailure(f"輸入檔缺失：{path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _unwrap_table(raw: Any, key: str) -> dict:
    """gold 表兩種形狀都收：平面 `{sub: [...]}`，或帶出處的 `{"_meta": {...}, "<key>": {...}}`。

    帶 `_meta` 的形狀是業主核可狀態的載體（`_meta.status`），⛔ 不是 approved 就拒跑——
    凍結只能用核可過的表；平面形狀（無 `_meta`）視為測試／dry-run 用，不查狀態。
    """
    if not isinstance(raw, dict):
        raise SelectorFailure(f"{key} 表不是 JSON 物件")
    if "_meta" in raw and key in raw:
        status = (raw.get("_meta") or {}).get("status")
        if status != "approved":
            raise SelectorFailure(f"{key} 表 _meta.status={status!r}，⛔ 只有 approved 才准凍結")
        inner = raw[key]
        if not isinstance(inner, dict):
            raise SelectorFailure(f"{key} 表的 {key} 欄不是 JSON 物件")
        return inner
    return raw


def _sha256_file(path: str) -> str:
    if not os.path.isfile(path):
        raise SelectorFailure(f"輸入檔缺失（無法計算 sha256）：{path}")
    return ie.sha256_file(path)


def _rank_key(seed_prefix: str, q: str) -> tuple:
    """`md5(seed_prefix + q)` 升冪、`q` 原字串不正規化；ties by q。"""
    digest = hashlib.md5((seed_prefix + q).encode("utf-8")).hexdigest()
    return (digest, q)


# ---------------------------------------------------------------------------
# topics-v2.json：idx → {q, sub}（同 agent_eval.load_topics_scenarios 的 idx 編法）
# ---------------------------------------------------------------------------

def load_topics_index(topics_path: str) -> dict:
    """回 `{idx: {"q":..., "sub":..., "kind": "phrasing"|"boundary"}}`，`idx` 編法
    與 `tools/agent_eval.py:load_topics_scenarios` 同一式（`f"{topic_id}:phrasing:{i}"`／
    `f"{topic_id}:boundary:{i}"`）——round9 `topics.jsonl` 的 `idx` 就是照這個編法寫的。"""
    doc = _load_json(topics_path)
    out: dict = {}
    for topic in doc.get("topics", []):
        tid = topic["id"]
        for i, item in enumerate(topic.get("phrasings", [])):
            out[f"{tid}:phrasing:{i}"] = {"q": item["q"], "sub": item.get("sub", ""), "kind": "phrasing"}
        for i, item in enumerate(topic.get("boundary", [])):
            out[f"{tid}:boundary:{i}"] = {"q": item["q"], "sub": item.get("sub", ""), "kind": "boundary"}
    return out


def load_topics_boundary_items(topics_path: str) -> list:
    """E 層母體：topics-v2 的 boundary 題（原字串 q）。"""
    doc = _load_json(topics_path)
    out = []
    for topic in doc.get("topics", []):
        for item in topic.get("boundary", []):
            out.append({"q": item["q"], "sub": item.get("sub", "")})
    return out


# ---------------------------------------------------------------------------
# round9：r9a／r9b 的 topics.jsonl（chain=="agent" 才算）→ idx → answered 次數／總次數
# ---------------------------------------------------------------------------

def load_round9_answered_counts(round9_dir: str) -> dict:
    """回 `{idx: (answered_n, total_n)}`，聚合 `r9a/topics.jsonl` ＋ `r9b/topics.jsonl`
    兩檔中 `chain=="agent"` 的列（合計 6 rep：各檔 3 rep × 54 idx）。"""
    counts: dict = defaultdict(lambda: [0, 0])
    found_any = False
    for sub in ("r9a", "r9b"):
        path = os.path.join(round9_dir, sub, "topics.jsonl")
        if not os.path.isfile(path):
            raise SelectorFailure(f"round9 輸入檔缺失：{path}")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                found_any = True
                if row.get("chain") != "agent":
                    continue
                idx = row["idx"]
                counts[idx][1] += 1
                if row.get("answered"):
                    counts[idx][0] += 1
    if not found_any:
        raise SelectorFailure(f"round9 目錄下兩份 topics.jsonl 皆無內容：{round9_dir}")
    return {k: (v[0], v[1]) for k, v in counts.items()}


# ---------------------------------------------------------------------------
# sub-map 檢核（A／C 的 fail-loud 規則）
# ---------------------------------------------------------------------------

def check_subs_in_map(subs: list, sub_map: dict, *, stratum: str) -> None:
    missing = sorted({s for s in subs if s not in sub_map})
    if missing:
        raise SelectorFailure(
            f"{stratum} 層有 sub 不在 --sub-map 鍵集合裡（⛔ 不靜默排除，回主 session 補表）：{missing}"
        )


# ---------------------------------------------------------------------------
# 各層母體
# ---------------------------------------------------------------------------

def population_a(topics_index: dict, round9_counts: dict, sub_map: dict) -> list:
    """A：round9 agent 6 rep 0/6 答到 的 phrasing，且 sub 在 sub-map。"""
    out = []
    subs_seen = []
    for idx, meta in topics_index.items():
        if meta["kind"] != "phrasing":
            continue
        answered_n, total_n = round9_counts.get(idx, (None, None))
        if total_n != 6:
            continue
        if answered_n != 0:
            continue
        subs_seen.append(meta["sub"])
    check_subs_in_map(subs_seen, sub_map, stratum="A")
    for idx, meta in topics_index.items():
        if meta["kind"] != "phrasing":
            continue
        answered_n, total_n = round9_counts.get(idx, (None, None))
        if total_n == 6 and answered_n == 0:
            out.append({"q": meta["q"], "gold": list(sub_map.get(meta["sub"], [])), "expect_kind": "answer"})
    return out


def population_c(topics_index: dict, round9_counts: dict, sub_map: dict) -> list:
    """C：round9 agent 6 rep ≥4/6 答到 的 phrasing。"""
    out = []
    subs_seen = []
    for idx, meta in topics_index.items():
        if meta["kind"] != "phrasing":
            continue
        answered_n, total_n = round9_counts.get(idx, (None, None))
        if total_n != 6:
            continue
        if answered_n is None or answered_n < 4:
            continue
        subs_seen.append(meta["sub"])
    check_subs_in_map(subs_seen, sub_map, stratum="C")
    for idx, meta in topics_index.items():
        if meta["kind"] != "phrasing":
            continue
        answered_n, total_n = round9_counts.get(idx, (None, None))
        if total_n == 6 and answered_n is not None and answered_n >= 4:
            out.append({"q": meta["q"], "gold": list(sub_map.get(meta["sub"], [])), "expect_kind": "answer"})
    return out


def population_b(map_v2_path: str, answerability_canon_path: str) -> list:
    """B：map-v2 55 格中標籤 ∈ {deliberate_no, no_source} 的代表問句（`questions[0]`）。"""
    m = _load_json(map_v2_path)
    labels_doc = _load_json(answerability_canon_path)
    payload = labels_doc["payload"] if "payload" in labels_doc else labels_doc
    label_of: dict = {}
    for row in payload["labels"]:
        label_of.setdefault(row["cell_id"], row["label"])

    cells_index = {c["id"]: c for c in m["cells"]}
    out = []
    for cid, label in label_of.items():
        if label not in ie.DELIBERATE_LABELS_EXCLUDED:
            continue
        cell = cells_index.get(cid)
        if not cell:
            continue
        questions = cell.get("questions") or []
        if not questions:
            continue
        out.append({"q": questions[0], "gold": [], "expect_kind": "handoff"})
    return out


def population_d(sensitive_path: str) -> list:
    """D：sensitive-v1 全部 30 題（分類選取邏輯在 `select_sensitive` 裡做）。"""
    doc = _load_json(sensitive_path)
    out = []
    for item in doc.get("items", []):
        out.append({
            "q": item["q"], "gold": [], "expect_kind": "handoff",
            "fact_class": item.get("fact_class", ""),
        })
    return out


def population_e(topics_path: str) -> list:
    """E：topics-v2 boundary（不硬答型，⛔ 不含 koyu `type=="邊界"` 的可答句）。"""
    return [
        {"q": it["q"], "gold": [], "expect_kind": "handoff"}
        for it in load_topics_boundary_items(topics_path)
    ]


def population_f(scenarios_path: str) -> list:
    """F：`F_SCENARIO_IDS` 凍結集合（每個至少 3 turn，缺一即 fail loud）。"""
    doc = _load_json(scenarios_path)
    by_id = {sc["id"]: sc for sc in doc.get("scenarios", [])}
    out = []
    for sid in F_SCENARIO_IDS:
        sc = by_id.get(sid)
        if sc is None:
            raise SelectorFailure(f"F 層凍結劇本缺失：{sid}（--scenarios 材料與 Plan §2 不符）")
        turns = sc.get("turns", [])
        if len(turns) < 3:
            raise SelectorFailure(f"F 層劇本 {sid} 只有 {len(turns)} turn（<3），與 Plan §2 凍結定義不符")
        out.append({"scenario_id": sid, "turns": turns})
    return out


def population_g(koyu_path: str, topics_path: str, article_map_path: str, rule_path: Optional[str]) -> list:
    """G：422 重生句中 article ∈ `G_CROSS_COARSE_ARTICLES`；gold＝article-map 的 `fine_ids`。

    重生前先做三項全等驗證（若給了 `--rule`）：`n`／`by_type`／`excluded_frozen` 對不上
    `--rule` 記錄 ⇒ fail loud（G 的材料本身壞了，⛔ 不能假裝正常繼續選）。
    """
    frozen_raw = ie.load_frozen_54(topics_path)
    norm = ie._pm().norm
    frozen_norm_set = frozenset(norm(q) for q in frozen_raw if q)
    sentences, by_type, excluded_frozen = ie.regenerate_422(koyu_path, frozen_norm_set)

    if rule_path and os.path.isfile(rule_path):
        rule = _load_json(rule_path)
        mismatches = ie.verify_freeze_three_way(rule, len(sentences), by_type, excluded_frozen)
        if mismatches:
            raise SelectorFailure(
                "G 層 422 重生與 --rule 記錄的三項全等不符（材料本身壞了）：" + "；".join(mismatches)
            )

    article_map = _load_json(article_map_path)
    out = []
    for s in sentences:
        if s["article"] not in G_CROSS_COARSE_ARTICLES:
            continue
        info = article_map.get("articles", {}).get(s["article"]) or {}
        gold = list(info.get("fine_ids") or [])
        out.append({"q": s["q"], "gold": gold, "expect_kind": "answer"})
    return out


# ---------------------------------------------------------------------------
# 排序取前 N（一般層）／D 層專用（各類先取 md5 最小者、再依 md5 補滿）
# ---------------------------------------------------------------------------

def select_ordered(candidates: list, seed_prefix: str, take_n: int) -> tuple:
    """回 `(picked, insufficient)`；`picked` 依 `_rank_key` 升冪。"""
    ordered = sorted(candidates, key=lambda c: _rank_key(seed_prefix, c["q"]))
    insufficient = len(ordered) < take_n
    return (ordered if insufficient else ordered[:take_n]), insufficient


def select_sensitive(candidates: list, seed_prefix: str, take_n: int) -> tuple:
    """五類各 md5 最小者先取滿五類，再依全域 md5 補到 `take_n`（Plan §2 D 列）。"""
    by_class: dict = defaultdict(list)
    for c in candidates:
        by_class[c["fact_class"]].append(c)

    picked: list = []
    picked_ids = set()
    for cls in sorted(by_class):
        lst = by_class[cls]
        best = min(lst, key=lambda c: _rank_key(seed_prefix, c["q"]))
        picked.append(best)
        picked_ids.add(id(best))

    if len(picked) < take_n:
        remaining = [c for c in candidates if id(c) not in picked_ids]
        remaining_sorted = sorted(remaining, key=lambda c: _rank_key(seed_prefix, c["q"]))
        for c in remaining_sorted:
            if len(picked) >= take_n:
                break
            picked.append(c)
            picked_ids.add(id(c))

    insufficient = len(candidates) < take_n
    picked_sorted = sorted(picked, key=lambda c: _rank_key(seed_prefix, c["q"]))
    return picked_sorted, insufficient


def select_scenarios(candidates: list, seed_prefix: str, take_n: int) -> tuple:
    """F：md5 對劇本 id 排序（⛔ 不是對 q——劇本沒有單一代表句）。"""
    ordered = sorted(candidates, key=lambda c: _rank_key(seed_prefix, c["scenario_id"]))
    insufficient = len(ordered) < take_n
    return (ordered if insufficient else ordered[:take_n]), insufficient


# ---------------------------------------------------------------------------
# 題集 item 組裝
# ---------------------------------------------------------------------------

def build_single_turn_items(layer: str, picked: list, stratum_literal: str) -> list:
    items = []
    for i, c in enumerate(picked, start=1):
        items.append({
            "id": f"{layer}-{i:02d}",
            "q": c["q"],
            "stratum": stratum_literal,
            "gold": list(c.get("gold") or []),
            "expect_kind": c.get("expect_kind"),
        })
    return items


def build_scenario_items(picked: list, scenario_gold: dict) -> list:
    """F：一個劇本一個 item，`turns[]` 逐 turn 帶 gold／expect_kind（來自
    `--scenario-gold`；⛔ 缺該劇本或缺某 turn 的 gold 表 ⇒ fail loud）。"""
    items = []
    for c in picked:
        sid = c["scenario_id"]
        gold_turns = scenario_gold.get(sid)
        if gold_turns is None:
            raise SelectorFailure(f"F 層劇本 {sid} 缺 --scenario-gold 條目（業主尚未核 gold 表）")
        gold_by_turn = {g["turn"]: g for g in gold_turns}
        turns_out = []
        for t in c["turns"]:
            turn_no = t["turn"]
            g = gold_by_turn.get(turn_no)
            if g is None:
                raise SelectorFailure(f"F 層劇本 {sid} 第 {turn_no} turn 缺 --scenario-gold 條目")
            turns_out.append({
                "turn": turn_no, "q": t["q"],
                "gold": list(g.get("gold") or []), "expect_kind": g.get("expect_kind"),
            })
        items.append({"id": f"F-{sid}", "stratum": "multi", "turns": turns_out})
    return items


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

_LAYER_STRATUM_LITERAL = {
    "A": "answerable_unanswered", "B": "gold_absent", "C": "answerable_answered",
    "D": "sensitive", "E": "boundary", "G": "cross_coarse",
}


def run(args) -> int:
    seed_prefix = args.seed_prefix

    topics_index = load_topics_index(args.topics)
    round9_counts = load_round9_answered_counts(args.round9_dir)
    sub_map = _unwrap_table(_load_json(args.sub_map), "sub_map")  # `_load_json` 本身已對缺檔 fail loud

    pop_a = population_a(topics_index, round9_counts, sub_map)
    pop_b = population_b(args.map_v2, args.answerability_canon)
    pop_c = population_c(topics_index, round9_counts, sub_map)
    pop_d = population_d(args.sensitive)
    pop_e = population_e(args.topics)
    pop_f = population_f(args.scenarios)
    pop_g = population_g(args.koyu, args.topics, args.article_map, args.rule)

    for name, pop in (("A", pop_a), ("B", pop_b), ("C", pop_c), ("D", pop_d),
                      ("E", pop_e), ("F", pop_f), ("G", pop_g)):
        if not pop:
            raise SelectorFailure(f"{name} 層母體為空——材料或篩選條件可能壞了，⛔ 不繼續選")

    picked_a, insuf_a = select_ordered(pop_a, seed_prefix, STRATA_TAKE_N["A"])
    picked_b, insuf_b = select_ordered(pop_b, seed_prefix, STRATA_TAKE_N["B"])
    picked_c, insuf_c = select_ordered(pop_c, seed_prefix, STRATA_TAKE_N["C"])
    picked_d, insuf_d = select_sensitive(pop_d, seed_prefix, STRATA_TAKE_N["D"])
    picked_e, insuf_e = select_ordered(pop_e, seed_prefix, STRATA_TAKE_N["E"])
    picked_f, insuf_f = select_scenarios(pop_f, seed_prefix, STRATA_TAKE_N["F"])
    picked_g, insuf_g = select_ordered(pop_g, seed_prefix, STRATA_TAKE_N["G"])

    strata_report = [
        {"id": "A", "stratum_literal": _LAYER_STRATUM_LITERAL["A"], "population_n": len(pop_a),
         "take_n": len(picked_a), "insufficient": insuf_a},
        {"id": "B", "stratum_literal": _LAYER_STRATUM_LITERAL["B"], "population_n": len(pop_b),
         "take_n": len(picked_b), "insufficient": insuf_b},
        {"id": "C", "stratum_literal": _LAYER_STRATUM_LITERAL["C"], "population_n": len(pop_c),
         "take_n": len(picked_c), "insufficient": insuf_c},
        {"id": "D", "stratum_literal": _LAYER_STRATUM_LITERAL["D"], "population_n": len(pop_d),
         "take_n": len(picked_d), "insufficient": insuf_d},
        {"id": "E", "stratum_literal": _LAYER_STRATUM_LITERAL["E"], "population_n": len(pop_e),
         "take_n": len(picked_e), "insufficient": insuf_e},
        {"id": "F", "stratum_literal": "multi", "population_n": len(pop_f),
         "population_turns": sum(len(c["turns"]) for c in pop_f),
         "take_n": len(picked_f),
         "take_turns": sum(len(c["turns"]) for c in picked_f), "insufficient": insuf_f},
        {"id": "G", "stratum_literal": _LAYER_STRATUM_LITERAL["G"], "population_n": len(pop_g),
         "take_n": len(picked_g), "insufficient": insuf_g},
    ]

    if args.dry_run:
        for row in strata_report:
            if row["id"] == "F":
                print(
                    f"[outline_probe_select] F（multi）：population={row['population_n']} "
                    f"scenarios/{row['population_turns']} turns take={row['take_n']} "
                    f"scenarios/{row['take_turns']} turns insufficient={row['insufficient']}"
                )
                continue
            print(
                f"[outline_probe_select] {row['id']}（{row['stratum_literal']}）："
                f"population={row['population_n']} take={row['take_n']} "
                f"insufficient={row['insufficient']}"
            )
        return EXIT_OK

    scenario_gold = _unwrap_table(_load_json(args.scenario_gold), "scenario_gold")

    items = []
    items += build_single_turn_items("A", picked_a, "answerable_unanswered")
    items += build_single_turn_items("B", picked_b, "gold_absent")
    items += build_single_turn_items("C", picked_c, "answerable_answered")
    items += build_single_turn_items("D", picked_d, "sensitive")
    items += build_single_turn_items("E", picked_e, "boundary")
    items += build_scenario_items(picked_f, scenario_gold)
    items += build_single_turn_items("G", picked_g, "cross_coarse")

    r9a_topics_path = os.path.join(args.round9_dir, "r9a", "topics.jsonl")
    r9b_topics_path = os.path.join(args.round9_dir, "r9b", "topics.jsonl")

    # `source_sha256` 一律以「解析後的實際檔案路徑」為鍵（⛔ 不用邏輯別名——
    # 別名對不上檔案，重跑時查證會多一層翻譯）；`inputs_sha256`（頂層 `_meta`
    # 與 rule 檔）沿用同一份，兩處故意共用同一個 dict、不重算。
    source_shas = {
        args.koyu: _sha256_file(args.koyu),
        args.topics: _sha256_file(args.topics),
        args.article_map: _sha256_file(args.article_map),
        args.map_v2: _sha256_file(args.map_v2),
        args.answerability_canon: _sha256_file(args.answerability_canon),
        args.sensitive: _sha256_file(args.sensitive),
        args.scenarios: _sha256_file(args.scenarios),
        args.sub_map: _sha256_file(args.sub_map),
        args.scenario_gold: _sha256_file(args.scenario_gold),
        r9a_topics_path: _sha256_file(r9a_topics_path),
        r9b_topics_path: _sha256_file(r9b_topics_path),
    }
    if os.path.isfile(args.rule):
        source_shas[args.rule] = _sha256_file(args.rule)

    canon_sha256 = _sha256_file(args.canon) if os.path.isfile(args.canon) else None
    agent_rules_sha256 = _sha256_file(args.agent_rules) if os.path.isfile(args.agent_rules) else None
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    strata_out = []
    definitions = {
        "A": "round9 topics 46 問法中 agent 兩輪 6 rep 0/6 答到、且 sub 可對映到正本粗目 C 細目",
        "B": "map-v2 55 格中標籤 ∈ {deliberate_no, no_source} 的代表問句（questions[0]）",
        "C": "round9 46 問法中 ≥4/6 答到",
        "D": "sensitive-v1 30 題，五類各至少 1（每類 md5 最小者先取滿五類，再依 md5 補到 5）",
        "E": "topics-v2 boundary 8（不硬答型）",
        "F": "scenarios-v1 中 turn≥3 的劇本 {S1-landlord, S2-agency, D-import}（一個劇本一個 item）",
        "G": "koyu 422 中 article ∈ {Landlordonboarding00, onboarding6, qa05, qa06}",
    }
    source_paths_by_layer = {
        "A": [args.topics, r9a_topics_path, r9b_topics_path, args.sub_map],
        "B": [args.map_v2, args.answerability_canon],
        "C": [args.topics, r9a_topics_path, r9b_topics_path, args.sub_map],
        "D": [args.sensitive],
        "E": [args.topics],
        "F": [args.scenarios, args.scenario_gold],
        "G": [args.koyu, args.topics, args.article_map],
    }
    for row in strata_report:
        layer = row["id"]
        paths = source_paths_by_layer[layer]
        strata_out.append({
            "id": layer,
            "stratum_literal": row["stratum_literal"],
            "definition": definitions[layer],
            "source_paths": paths,
            "source_sha256": {p: source_shas[p] for p in paths},
            "population_n": row["population_n"],
            "take_n": row["take_n"],
            "insufficient": row["insufficient"],
        })

    rule_doc = {
        "seed_prefix": seed_prefix,
        "md5_normalization": "none",
        "strata": strata_out,
        "frozen_at": frozen_at,
        "canon_sha256": canon_sha256,
        "agent_rules_sha256": agent_rules_sha256,
        "inputs_sha256": source_shas,
    }
    rule_bytes = json.dumps(rule_doc, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    rule_sha256 = hashlib.sha256(rule_bytes).hexdigest()

    items_doc = {
        "_meta": {
            "rule_sha256": rule_sha256,
            "frozen_at": frozen_at,
            "n": len(items),
            "seed_prefix": seed_prefix,
            "inputs_sha256": source_shas,
        },
        "items": items,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out_rule)), exist_ok=True)
    with open(args.out_rule, "wb") as f:
        f.write(rule_bytes)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_items)), exist_ok=True)
    with open(args.out_items, "w", encoding="utf-8") as f:
        json.dump(items_doc, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"[outline_probe_select] 完成：{len(items)} 題 → {args.out_items}（規則檔 {args.out_rule}）")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--koyu", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "sources", "koyu-v2-phrasings.json"))
    p.add_argument("--rule", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "phrasing-selection-rule-20260906.json"))
    p.add_argument("--topics", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "topics-v2.json"))
    p.add_argument("--article-map", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs", "koyu-article-map.json"))
    p.add_argument("--map-v2", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "map-v2.json"))
    p.add_argument("--answerability-canon", default=os.path.join(
        ".claude", "skills", "outline-curation", "runs", "2026-09-06T00-00-00Z", "answerability-canon-v3.json"))
    p.add_argument("--round9-dir", default=os.path.join(
        ".kiro", "specs", "agentic-mcp-orchestration", "eval", "perf-agent-regression-20260905",
        "round9-dsp033"))
    p.add_argument("--sensitive", default=os.path.join(
        ".kiro", "specs", "agentic-mcp-orchestration", "eval", "sensitive-v1.json"))
    p.add_argument("--scenarios", default=os.path.join(
        ".kiro", "specs", "agentic-mcp-orchestration", "eval", "scenarios-v1.json"))
    p.add_argument("--sub-map", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "outline-probe-sub-map-20260907.json"))
    p.add_argument("--scenario-gold", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "outline-probe-scenario-gold-20260907.json"))
    p.add_argument("--out-items", default=os.path.join(
        ".kiro", "specs", "agentic-mcp-orchestration", "eval", "outline-probe-20260907.json"))
    p.add_argument("--out-rule", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "outline-probe-selection-rule.json"))
    p.add_argument("--canon", default=os.path.join("rag-orchestrator", "canon", "prospect.md"))
    p.add_argument("--agent-rules", default=os.path.join(
        "rag-orchestrator", "services", "agent", "agent_rules.py"))
    p.add_argument("--seed-prefix", default=DEFAULT_SEED_PREFIX)
    p.add_argument("--dry-run", action="store_true")
    return p


def _resolve_repo_relative(args) -> None:
    repo_root = ie.find_repo_root()

    def r(rel):
        return rel if os.path.isabs(rel) else os.path.join(repo_root, rel)

    for name in (
        "koyu", "rule", "topics", "article_map", "map_v2", "answerability_canon",
        "round9_dir", "sensitive", "scenarios", "sub_map", "scenario_gold",
        "out_items", "out_rule", "canon", "agent_rules",
    ):
        setattr(args, name, r(getattr(args, name)))


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    _resolve_repo_relative(args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
