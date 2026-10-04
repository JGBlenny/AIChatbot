#!/usr/bin/env python3
"""不變量 34：凍結題不入講法（spec knowledge-outline-and-intent-architecture・任務 3.5）。

design.md `| 34 |`：`rag-orchestrator/canon/*.json` 所有講法（不分 status）∩
`.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json` 各 set 的題句
（NFKC 正規化）＝∅。⚠️ **跨 spec 依賴（E8）**：manifest 是另一個 spec
（agentic-mcp-orchestration）的凍結樣本——manifest／任一 set 檔缺讀 ⇒ 大聲失敗
（⛔ 不 SKIP，這是「凍結樣本消失」而非「D1 前本來就是空」，兩者性質不同）。

正對照：故意塞一句必紅（`--self-test`）。

⚠️ 目標驗收的 H 留出題（holdout 99＋material 97）另由 `goal_eval_holdout_guard.py` 守
（目標驗收規格 2026-10-04 裁決 8、Plan 9.27）；本檢查語義不變。

用法：python3 scripts/audit/checks/canon_phrasing_frozen_disjoint.py [--self-test]
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CANON_GLOB_REL = "rag-orchestrator/canon/*.json"
HASH_PREFIX = "sha256:"
MANIFEST_REL = ".kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json"


def _resolve_canon_glob() -> str:
    """`rag-orchestrator/canon/*.json` 的絕對路徑（含容器佈局）。

    ⚠️ 兩種佈局：① host（`make audit`）——`REPO/rag-orchestrator/canon`；
    ② pytest 測試容器（`docker-compose.dev.yml`）——`./rag-orchestrator` 掛在
    `/app`（目錄名不是 `rag-orchestrator`，⛔ 不能只靠「根＝/」的字串拼接）。
    """
    if os.path.isdir("/app/canon"):
        return "/app/canon/*.json"
    return os.path.join(REPO, CANON_GLOB_REL)


def _resolve_manifest_path() -> str:
    """凍結樣本 manifest 的絕對路徑（含容器佈局：`./.kiro` 掛在 `/.kiro`）。"""
    if os.path.isdir("/.kiro"):
        return os.path.join("/.kiro", MANIFEST_REL.split("/", 1)[1])
    return os.path.join(REPO, MANIFEST_REL)


def _resolve_repo_root() -> str:
    """凍結樣本 set 檔的第二個候選根（`collect_frozen_questions` 的 `rel_path`
    是相對 repo 根，容器內 `.kiro` 掛在 `/.kiro`，等效根＝`/`）。"""
    if os.path.isdir("/.kiro"):
        return "/"
    return REPO


def _norm(s: str) -> str:
    """NFKC 正規化＋去頭尾空白（全形／半形、間距差異都視為同一句）。"""
    return unicodedata.normalize("NFKC", s).strip()


_HN_WS_RE = re.compile(r"\s+")
_HN_TRAILING_PUNCT_RE = re.compile(r"[?？!！。.．,，;；:：~～…]+$")


def hash_norm(text: str) -> str:
    """Plan 9.13 §4 **唯一**正規化＋雜湊（題目文字不進 git 的留出集只登記這個值）。

    ＝`sha256(NFKC → 去全部空白 → 去句尾標點)`，與 `phrasing_map.norm` 同一套規則（句尾加問號、
    中間加空白都算同一句）。產 index、`ruler_eval.py --text-file` 驗證、本檢查三處 ⛔ 只准用這一個符號。
    """
    t = unicodedata.normalize("NFKC", text)
    t = _HN_TRAILING_PUNCT_RE.sub("", _HN_WS_RE.sub("", t))
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_canon_phrasings(canon_glob_abs: str) -> tuple[frozenset[str], list[str]]:
    """`{正規化後的講法文字}`（不分 status）＋掃到的檔案清單。缺檔／掃到 0 個檔 ⇒ 大聲失敗。"""
    paths = sorted(glob.glob(canon_glob_abs))
    if not paths:
        raise RuntimeError(f"找不到任何正本 JSON（{canon_glob_abs}）——大聲失敗，⛔ 不當成 0 句")
    phrasings = set()
    for p in paths:
        doc = _read_json(p)
        for coarse in doc.get("coarses", []):
            for fine in coarse.get("fines", []):
                for ph in fine.get("phrasings", []):
                    text = ph.get("text")
                    if isinstance(text, str) and text.strip():
                        phrasings.add(_norm(text))
    return frozenset(phrasings), paths


def _extract_questions(shape_key: str, data: dict) -> list[str]:
    """依 manifest 記載的 `shape` 抽問句字串（三種已知 shape；未知 shape ⇒ 大聲失敗）。"""
    if shape_key == "topics":
        qs = []
        for topic in data.get("topics", []):
            for p in topic.get("phrasings", []):
                if isinstance(p.get("q"), str):
                    qs.append(p["q"])
            for b in topic.get("boundary", []):
                if isinstance(b.get("q"), str):
                    qs.append(b["q"])
        return qs
    if shape_key == "scenarios":
        qs = []
        for sc in data.get("scenarios", []):
            for t in sc.get("turns", []):
                if isinstance(t.get("q"), str):
                    qs.append(t["q"])
        return qs
    if shape_key == "sensitive":
        return [it["q"] for it in data.get("items", []) if isinstance(it.get("q"), str)]
    if shape_key == "outline-probe":
        # 4.4a 凍結題集（knowledge-outline-and-intent-architecture）：單題 `items[].q`；
        # 劇本 item `stratum="multi"` 帶 `turns[].q`（一劇本一 item、同 session 貫穿）。
        qs = []
        for it in data.get("items", []):
            if isinstance(it.get("q"), str):
                qs.append(it["q"])
            for t in it.get("turns", []) or []:
                if isinstance(t.get("q"), str):
                    qs.append(t["q"])
        return qs
    if shape_key == "ruler-9.13":
        # Plan 9.13 真實客服留出集：題目文字不進 git，只登記 `items[].q_sha256`（`hash_norm`）。
        # 回傳以 `HASH_PREFIX` 標記的雜湊，由 `check_*` 與講法的 `hash_norm` 比對。
        # 只取留出集（Plan 9.13 §4「正本講法 ∩ 留出集 ＝∅」）：`material` 是講法素材池，本來就可能成為講法，⛔ 不是洩題。
        items = data.get("items", [])
        if any(it.get("split") not in ("holdout", "material") for it in items):
            raise RuntimeError("ruler-9.13 index 有題目缺 split 或值域外（應為 holdout／material）——⛔ 不猜哪些算留出集")
        return [HASH_PREFIX + it["q_sha256"] for it in items
                if it.get("split") == "holdout" and isinstance(it.get("q_sha256"), str)]
    if shape_key == "ruler-9.12":
        # Plan 9.12 檢索量尺（knowledge-outline-and-intent-architecture）：單題 `items[].q`。
        return [it["q"] for it in data.get("items", []) if isinstance(it.get("q"), str)]
    raise RuntimeError(f"未知的 manifest set 名稱 {shape_key!r}——本檢查只認得 topics／scenarios／sensitive／outline-probe／ruler-9.12／ruler-9.13"
                       "（shape 與抽取規則須同步擴充，⛔ 不可默默略過新 set）")


def collect_frozen_questions(manifest_abs: str, verify_sha: bool = True):
    """`(frozen_set, counts_by_set, files_checked)`；manifest／任一 available set 檔缺讀 ⇒ raise。"""
    manifest_dir = os.path.dirname(manifest_abs)
    manifest = _read_json(manifest_abs)
    frozen = set()
    counts = {}
    files_checked = []
    for name, meta in manifest.get("sets", {}).items():
        if not meta.get("available", False):
            continue  # 例：traffic 尚未凍結（path=null），⛔ 不是缺讀，是刻意未提供
        rel_path = meta.get("path")
        if not rel_path:
            raise RuntimeError(f"manifest set {name!r} available=true 但 path 缺失——大聲失敗")
        candidates = [
            os.path.normpath(os.path.join(_resolve_repo_root(), rel_path)),
            os.path.normpath(os.path.join(manifest_dir, rel_path)),
        ]
        abs_path = next((c for c in candidates if os.path.isfile(c)), None)
        if abs_path is None:
            raise RuntimeError(
                f"manifest set {name!r} 的樣本檔讀不到（{rel_path}；試過 {candidates}）——"
                "跨 spec 依賴（E8）：凍結樣本消失，大聲失敗"
            )
        with open(abs_path, "rb") as f:
            raw_bytes = f.read()
        if verify_sha and meta.get("sha256"):
            actual = hashlib.sha256(raw_bytes).hexdigest()
            expected = meta["sha256"]
            if actual != expected:
                raise RuntimeError(
                    f"manifest set {name!r} 的樣本檔 sha256 不符（manifest={expected}，"
                    f"實際={actual}）——樣本已變動或路徑對錯了，大聲失敗"
                )
        data = json.loads(raw_bytes.decode("utf-8"))
        qs = _extract_questions(name, data)
        for q in qs:
            frozen.add(q if q.startswith(HASH_PREFIX) else _norm(q))
        counts[name] = len(qs)
        files_checked.append(abs_path)
    return frozenset(frozen), counts, files_checked


def check_canon_phrasing_frozen_disjoint(
    canon_glob_abs: str | None = None,
    manifest_abs: str | None = None,
    verify_sha: bool = True,
):
    canon_glob_abs = canon_glob_abs or _resolve_canon_glob()
    manifest_abs = manifest_abs or _resolve_manifest_path()

    try:
        phrasings, canon_files = collect_canon_phrasings(canon_glob_abs)
    except Exception as e:  # noqa: BLE001
        return False, f"正本講法收集失敗（{e}）"

    try:
        frozen, counts, sample_files = collect_frozen_questions(manifest_abs, verify_sha=verify_sha)
    except Exception as e:  # noqa: BLE001
        return False, f"凍結題句收集失敗（{e}）"

    frozen_hashes = {q[len(HASH_PREFIX):] for q in frozen if q.startswith(HASH_PREFIX)}
    frozen_texts = {q for q in frozen if not q.startswith(HASH_PREFIX)}
    overlap = sorted(phrasings & frozen_texts)
    if frozen_hashes:
        overlap += sorted(f"（hash 留出題）{p}" for p in phrasings if hash_norm(p) in frozen_hashes)
    detail_base = (
        f"講法 {len(phrasings)}（{len(canon_files)} 個正本 JSON）、"
        f"凍結題 {len(frozen)}（{counts}，{len(sample_files)} 個樣本檔）"
    )
    if overlap:
        listed = "、".join(overlap[:5])
        more = "" if len(overlap) <= 5 else f"（其餘 {len(overlap) - 5} 句略）"
        return False, f"{detail_base}；交集非空：{listed}{more}"
    return True, f"{detail_base}；交集為空"


# ───────────────────────── --self-test（hermetic temp dirs）─────────────────────────


def _write_canon(canon_dir: str, phrasing_texts: list[str]) -> None:
    doc = {
        "audience": "prospect", "version": "test", "reviewers": [], "language": "zh-Hant",
        "budget_tokens": 100, "target_user": [], "business_types": [],
        "canon_sha256": "x", "phrasing_set_sha256": "x",
        "coarses": [{
            "id": "A", "title": "t",
            "fines": [{
                "id": "prospect/A/f1", "coarse_id": "A", "title": "f1",
                "phrasings": [{"text": t, "source": "test", "status": "approved"} for t in phrasing_texts],
                "content_units": [], "content_sha256": "x", "sources": [],
                "reviewed_by": None, "reviewed_at": None, "see_also": [],
                "policy": "answerable", "policy_ref": None,
                "target_user": [], "business_types": [], "categories": [],
                "instance_applicability": "general",
            }],
        }],
    }
    with open(os.path.join(canon_dir, "prospect.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)


def _write_manifest(manifest_dir: str, sensitive_questions: list[str], sha_override: str | None = None):
    items = [{"id": f"s:{i}", "q": q, "fact_class": "x", "sensitive": True,
              "expect_kind": "handoff", "must_not_contain": []}
             for i, q in enumerate(sensitive_questions)]
    sample_path = os.path.join(manifest_dir, "sensitive-v1.json")
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False)
    with open(sample_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    manifest = {
        "sets": {
            "sensitive": {
                "available": True,
                "path": "sensitive-v1.json",
                "sha256": sha if sha_override is None else sha_override,
            },
        }
    }
    manifest_path = os.path.join(manifest_dir, "samples-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    return manifest_path


def self_test() -> int:
    cases = []

    with tempfile.TemporaryDirectory() as td:
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)

        # ① 講法與凍結題不相交 ⇒ PASS
        _write_canon(canon_dir, ["你們系統介紹", "想了解金箍棒"])
        manifest_path = _write_manifest(manifest_dir, ["你們有幾家業者在用", "怎麼收費"])
        ok1, detail1 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("① 講法與凍結題不相交 ⇒ PASS", ok1 is True))
        cases.append(("① detail 印計數（見輸出）", "講法 2" in detail1 and "凍結題 2" in detail1))

    with tempfile.TemporaryDirectory() as td:
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)

        # ② 塞一句講法字面等於某凍結題 ⇒ FAIL
        _write_canon(canon_dir, ["你們有幾家業者在用", "想了解金箍棒"])
        _write_manifest(manifest_dir, ["你們有幾家業者在用", "怎麼收費"])
        ok2, detail2 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"),
            manifest_abs=os.path.join(manifest_dir, "samples-manifest.json"))
        cases.append(("② 講法撞凍結題（正對照：故意塞一句必紅）⇒ FAIL", ok2 is False))

        # 全形版：講法用全形括號句、凍結題半形，NFKC 正規化後應視為同一句 ⇒ 仍要抓到
        canon_dir2 = os.path.join(td, "canon2")
        os.makedirs(canon_dir2)
        _write_canon(canon_dir2, ["ＡＢＣ全形測試"])
        manifest_dir2 = os.path.join(td, "manifest2")
        os.makedirs(manifest_dir2)
        _write_manifest(manifest_dir2, ["ABC全形測試"])
        ok2b, _d = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir2, "*.json"),
            manifest_abs=os.path.join(manifest_dir2, "samples-manifest.json"))
        cases.append(("② NFKC 正規化後全形／半形視為同一句仍抓到 ⇒ FAIL", ok2b is False))

    with tempfile.TemporaryDirectory() as td:
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)
        _write_canon(canon_dir, ["你們系統介紹"])
        manifest_path = _write_manifest(manifest_dir, ["怎麼收費"])
        os.remove(os.path.join(manifest_dir, "sensitive-v1.json"))
        # ③ set 檔缺失 ⇒ FAIL（大聲失敗，⛔ 不當成空集合）
        ok3, detail3 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("③ manifest set 檔缺失 ⇒ FAIL（大聲失敗）", ok3 is False))

    with tempfile.TemporaryDirectory() as td:
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)
        _write_canon(canon_dir, ["你們系統介紹"])
        manifest_path = _write_manifest(manifest_dir, ["怎麼收費"], sha_override="0" * 64)
        # ④ sha256 對不上 ⇒ FAIL
        ok4, detail4 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("④ 樣本檔 sha256 與 manifest 不符 ⇒ FAIL", ok4 is False))

    with tempfile.TemporaryDirectory() as td:
        # ⑤ 正本 JSON 一個都掃不到 ⇒ FAIL（正對照：不是「0 句所以綠」）
        canon_dir = os.path.join(td, "canon_empty")
        os.makedirs(canon_dir)
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(manifest_dir)
        manifest_path = _write_manifest(manifest_dir, ["怎麼收費"])
        ok5, detail5 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("⑤ 正本 JSON 掃到 0 個檔 ⇒ FAIL（正對照，不當成 0 句）", ok5 is False))

    with tempfile.TemporaryDirectory() as td:
        # ⑥ ruler-9.12 形狀：講法撞量尺題 ⇒ FAIL；不撞 ⇒ PASS（正對照：新 set 真的被讀進交集）
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)
        sample_path = os.path.join(manifest_dir, "ruler.json")
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {}, "items": [{"id": "r:0", "q": "量尺測試題"}]}, f, ensure_ascii=False)
        with open(sample_path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        manifest_path = os.path.join(manifest_dir, "samples-manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"sets": {"ruler-9.12": {"available": True, "path": "ruler.json", "sha256": sha}}}, f)
        _write_canon(canon_dir, ["量尺測試題"])
        ok6, _d6 = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("⑥ ruler-9.12 題句撞講法 ⇒ FAIL", ok6 is False))
        _write_canon(canon_dir, ["別的講法"])
        ok6b, _d6b = check_canon_phrasing_frozen_disjoint(
            canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
        cases.append(("⑥ ruler-9.12 題句不撞 ⇒ PASS", ok6b is True))

    with tempfile.TemporaryDirectory() as td:
        # ⑦ ruler-9.13 hash 形狀：講法「X？」／中間有空白 vs 題目 hash_norm(X) ⇒ FAIL；不撞 ⇒ PASS
        canon_dir = os.path.join(td, "canon")
        manifest_dir = os.path.join(td, "manifest")
        os.makedirs(canon_dir)
        os.makedirs(manifest_dir)
        sample_path = os.path.join(manifest_dir, "idx.json")
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {}, "items": [{"id": "h:0", "split": "holdout", "q_sha256": hash_norm("合約可以續約嗎")},
                                               {"id": "m:0", "split": "material", "q_sha256": hash_norm("押金怎麼退")}]}, f)
        with open(sample_path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        manifest_path = os.path.join(manifest_dir, "samples-manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"sets": {"ruler-9.13": {"available": True, "path": "idx.json", "sha256": sha}}}, f)
        for label, ph, expect in (("同句", "合約可以續約嗎", False), ("句尾全形？", "合約可以續約嗎？", False),
                                  ("中間空白", "合約 可以 續約嗎", False), ("不撞", "帳單怎麼開", True),
                                  ("撞講法素材池（material）", "押金怎麼退", True)):
            _write_canon(canon_dir, [ph])
            ok7, _d7 = check_canon_phrasing_frozen_disjoint(
                canon_glob_abs=os.path.join(canon_dir, "*.json"), manifest_abs=manifest_path)
            cases.append((f"⑦ ruler-9.13 hash：{label} ⇒ {'PASS' if expect else 'FAIL'}", ok7 is expect))

    # ── 正對照：現樹真的掃到東西（⛔ 不是空跑）──
    real_phrasings, real_files = collect_canon_phrasings(_resolve_canon_glob())
    cases.append((f"正對照：現樹正本講法真的掃到（{len(real_phrasings)} 句，{len(real_files)} 個檔，⛔ 不是 0）",
                  len(real_phrasings) > 0 and len(real_files) > 0))
    real_frozen, real_counts, real_sample_files = collect_frozen_questions(_resolve_manifest_path())
    cases.append((f"正對照：現樹凍結題真的掃到（{len(real_frozen)} 句，{real_counts}，⛔ 不是 0）",
                  len(real_frozen) > 0 and len(real_sample_files) >= 1))

    for name, ok in cases:
        print(f"{'✅' if ok else '❌'} {name}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        ok, detail = check_canon_phrasing_frozen_disjoint()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 不變量 34：凍結題不入講法 —— 檢查無法執行（{e}）——大聲失敗")
        return 1
    print(f"{'✅' if ok else '❌'} 不變量 34：凍結題不入講法 —— {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
