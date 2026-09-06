#!/usr/bin/env python3
"""不變量 33：正本可見性與 kb 衍生列三軸對帳（spec knowledge-outline-and-intent-architecture・任務 3.5）。

design.md `| 33 |`：**必查組＝本 spec 有正本的身分**——b2b（pm、vendor_id=0）、
b2b（prospect）；每組命中 <1 ⇒ FAIL（空跑不得綠）；b2c（tenant、vendor 1）標
「M4 開放 tenant 正本時納入」，現階段列 notes、⛔ 不列 bad。

owner 對帳（2026-09-07，tasks.md 3.5）：衍生列（`generation_metadata.canon_ref`）
的 `business_types`／`target_user` 為 NULL ⇔ 正本該細目該欄為空清單；出現字面
`'{}'`（空陣列，非 NULL）或被預設成 `system_provider` 而正本為空 ⇒ FAIL
（帶 row id／fine id）。

## SKIP(pending-D1)（同 3.1 的不變量 32 慣例）

衍生列在 D1（重寫成 `pool-marked-<date>` 後 `VALIDATE CONSTRAINT`）入庫前恆為
0——此時「SQL 側／記憶體側對不上」無從比較，印 `SKIP(pending-D1)`、⛔ 不計
FAIL；SKIP 只由「衍生列數＝0」這個事實觸發（程式自動，非人工判斷）。D1 後
衍生列 >0，本檢查轉硬失敗。

## 為什麼走 docker exec 到 `aichatbot-rag-orchestrator`，不在本檔 import canon 模組

`load_canon_or_die`／`FineIndex`／`build_visibility_predicate` 這條 import 鏈
會拉入 `pydantic`（`services/agent/tools/registry.py`）、`httpx`
（`services/embedding_utils.py`）、`psycopg2`（`vendor_knowledge_retriever_v2.py`）
——host 稽核環境（`make audit` 直接以 host `python3` 執行本檔）未安裝這三個
套件（已實測 `ModuleNotFoundError`）。⛔ 本檔不重寫一套可見性判準（那正是
`FineIndex.visible_subset` docstring 明言要避免的「第二份可見性真相」）——
改用 `docker exec -i aichatbot-rag-orchestrator python3` 執行**真正的產線函式**
（`build_visibility_predicate`／`canon_visible`／`load_canon_or_die`），單一
來源不變，只是執行位置搬進已經有這些套件的容器。今天（D1 前）衍生列＝0，
`main()` 一律在呼叫任何 docker-exec-to-rag-orchestrator 之前就回 SKIP，
⇒ host 空跑不需要那個容器，只需要 `aichatbot-postgres`（跟其餘 checker 一致）。

## `--self-test` 為什麼不打容器

`--self-test` 驗的是**本檔的三態判斷與對帳邏輯**（SKIP／PASS／FAIL 分支、
`'{}'` 與 NULL 的對帳規則、必查組命中數<1 即紅），不是重新驗證
`FineIndex.visible_subset`／`canon_visible` 本身是否正確——那條已由 3.2／3.3
（`check_29b_canon_visibility_single_source`、`fine_index.py` 自身測試）覆蓋。
故 `--self-test` 全程注入假的 `predicate_visible_fn`／`mem_visible_fn`／
`canon_fine_map_fn`（合成細目、合成衍生列），⛔ 不連 docker、⛔ 不連 DB。

用法：python3 scripts/audit/checks/canon_visibility_reconcile.py [--self-test]
"""
from __future__ import annotations

import json
import subprocess
import sys

POSTGRES_CONTAINER = "aichatbot-postgres"
RAG_CONTAINER = "aichatbot-rag-orchestrator"

#: 必查組（design.md 33：本 spec 有正本的身分）。⛔ 順序即檢查順序——
#: 第一個命中 0 就直接回 FAIL（不再往下算第二組）。
REQUIRED_GROUPS = (
    ("b2b pm", {"vendor_id": 0, "target_user": "property_manager", "mode": "b2b"}),
    ("b2b prospect", {"vendor_id": 0, "target_user": "prospect", "mode": "b2b"}),
)
#: notes-only 組（M4 開放 tenant 正本時納入必查；現階段 ⛔ 不列 bad）。
NOTE_GROUP = ("b2c tenant (vendor 1)", {"vendor_id": 1, "target_user": "tenant", "mode": "b2c"})

CANON_AUDIENCE = "prospect"

DERIVED_SQL = (
    "SELECT id::text || '~|~' || COALESCE(generation_metadata->>'canon_ref','')"
    " || '~|~' || COALESCE(business_types::text,'<NULL>')"
    " || '~|~' || COALESCE(target_user::text,'<NULL>')"
    " FROM knowledge_base WHERE generation_metadata->>'canon_ref' IS NOT NULL ORDER BY id"
)


# ───────────────────────── 底層執行（docker exec，⛔ 不在本檔 import 重套件）─────────────────────────


def _psql(sql: str, timeout: int = 60) -> str:
    out = subprocess.run(
        ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def _container_python(script: str, timeout: int = 60) -> str:
    out = subprocess.run(
        ["docker", "exec", "-i", RAG_CONTAINER, "python3"],
        input=script, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(
            f"容器 {RAG_CONTAINER} 內 python3 失敗：{out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def default_query() -> str:
    """衍生列查詢（唯一入口，`main()`／`--self-test` 皆經此注入點）。"""
    return _psql(DERIVED_SQL)


def parse_derived_rows(raw: str) -> list[dict]:
    rows = []
    for line in raw.strip("\n").splitlines():
        if not line.strip():
            continue
        parts = line.split("~|~")
        if len(parts) != 4:
            raise RuntimeError(f"衍生列解析失敗，欄位數不對：{line!r}")
        rid, canon_ref, business_types, target_user = parts
        rows.append({
            "id": rid, "canon_ref": canon_ref,
            "business_types": business_types, "target_user": target_user,
        })
    return rows


def _pg_scalar_literal(x) -> str:
    if isinstance(x, bool):
        return "TRUE" if x else "FALSE"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, str):
        return "'" + x.replace("'", "''") + "'"
    raise ValueError(f"不支援的 SQL 參數型別：{x!r}")


def _pg_literal(param) -> str:
    if isinstance(param, list):
        return "ARRAY[" + ",".join(_pg_scalar_literal(x) for x in param) + "]"
    return _pg_scalar_literal(param)


def _render_predicate_sql(sql_template: str, params: list) -> str:
    """把 `build_visibility_predicate` 回傳的 `%s` 佔位符換成字面值（⛔ 不做通用防注入——
    參數只來自本檔硬寫的必查身分，非外部輸入）。"""
    out = sql_template
    for p in params:
        out = out.replace("%s", _pg_literal(p), 1)
    return out


def default_predicate_visible_ids(identity_kwargs: dict) -> frozenset:
    """SQL 側：以真正的 `build_visibility_predicate`（容器內執行，見模組 docstring）
    算出「這個身分可見且 `canon_ref` 非空」的 kb 列 `canon_ref` 集合。"""
    script = (
        "import sys, json\n"
        "sys.path.insert(0, '/app')\n"
        "from services.vendor_knowledge_retriever_v2 import build_visibility_predicate\n"
        "from services.agent.identity import Identity\n"
        f"identity = Identity(**{identity_kwargs!r})\n"
        "sql, params = build_visibility_predicate(identity)\n"
        "print(json.dumps({'sql': sql, 'params': params}))\n"
    )
    obj = json.loads(_container_python(script))
    predicate_sql = _render_predicate_sql(obj["sql"], obj["params"])
    full_sql = (
        "SELECT string_agg(DISTINCT generation_metadata->>'canon_ref', ',') "
        f"FROM knowledge_base kb WHERE generation_metadata->>'canon_ref' IS NOT NULL {predicate_sql}"
    )
    raw = _psql(full_sql).strip()
    return frozenset(raw.split(",")) if raw else frozenset()


def default_mem_visible_ids(identity_kwargs: dict, vendor_business_types: frozenset) -> frozenset:
    """記憶體側：以真正的 `FineIndex.visible_subset`（容器內執行）算這個身分在
    `prospect` 正本上可見的**全部**細目 id（不限於已材料化到 kb 的那些——
    與 kb 的交集由呼叫端算，見 `check_canon_visibility_reconcile`）。"""
    script = (
        "import sys, json\n"
        "sys.path.insert(0, '/app')\n"
        "from services.agent.canon.canon_assembler import load_canon_or_die, resolve_canon_dir\n"
        "from services.agent.canon.fine_index import FineIndex\n"
        "from services.agent.identity import Identity\n"
        f"doc = load_canon_or_die(resolve_canon_dir(), {CANON_AUDIENCE!r})\n"
        f"identity = Identity(**{identity_kwargs!r})\n"
        "idx = FineIndex(backend=None)\n"
        f"ids = idx.visible_subset(identity, doc, vendor_business_types=frozenset({sorted(vendor_business_types)!r}))\n"
        "print(json.dumps(sorted(ids)))\n"
    )
    return frozenset(json.loads(_container_python(script)))


def default_canon_fine_map() -> dict:
    """`{fine_id: {"business_types": [...], "target_user": [...]}}`——供逐列對帳。"""
    script = (
        "import sys, json\n"
        "sys.path.insert(0, '/app')\n"
        "from services.agent.canon.canon_assembler import load_canon_or_die, resolve_canon_dir\n"
        f"doc = load_canon_or_die(resolve_canon_dir(), {CANON_AUDIENCE!r})\n"
        "out = {f.id: {'business_types': list(f.business_types), 'target_user': list(f.target_user)}"
        " for f in doc.fines()}\n"
        "print(json.dumps(out))\n"
    )
    return json.loads(_container_python(script))


def default_vendor_business_types(vendor_id: int):
    """`vendors.business_types`（notes-only 組用；查不到 ⇒ `None`）。"""
    raw = _psql(
        f"SELECT COALESCE(business_types::text, '<NULL>') FROM vendors WHERE id={int(vendor_id)}"
    ).strip()
    if raw in ("", "<NULL>"):
        return None
    inner = raw.strip("{}")
    return [] if not inner else inner.split(",")


# ───────────────────────── 對帳主體（三態：True／None=SKIP(pending-D1)／False）─────────────────────────


def check_canon_visibility_reconcile(
    query=None,
    predicate_visible_fn=None,
    mem_visible_fn=None,
    canon_fine_map_fn=None,
    vendor_business_types_fn=None,
):
    """回 `(ok, detail)`；`ok` 為 `True`／`False`／`None`（SKIP(pending-D1)）。

    所有依賴一律可注入（`--self-test` 用），省略時走 `default_*`（真跑）。
    """
    query = query or default_query
    predicate_visible_fn = predicate_visible_fn or default_predicate_visible_ids
    mem_visible_fn = mem_visible_fn or default_mem_visible_ids
    canon_fine_map_fn = canon_fine_map_fn or default_canon_fine_map
    vendor_business_types_fn = vendor_business_types_fn or default_vendor_business_types

    try:
        raw = query()
    except Exception as e:  # noqa: BLE001
        return False, f"衍生列查詢失敗（{e}）——⛔ 大聲失敗，不當成 SKIP"

    try:
        rows = parse_derived_rows(raw)
    except Exception as e:  # noqa: BLE001
        return False, f"衍生列解析失敗（{e}）"

    if len(rows) == 0:
        return None, (
            "SKIP(pending-D1)：衍生列（generation_metadata.canon_ref）目前 0 列——"
            "D1（重寫成 pool-marked-<date> 後 VALIDATE CONSTRAINT）尚未執行，"
            "此檢查在 D1 後轉硬失敗"
        )

    materialized_ids = frozenset(r["canon_ref"] for r in rows if r["canon_ref"])

    try:
        fine_map = canon_fine_map_fn()
    except Exception as e:  # noqa: BLE001
        return False, f"正本細目對照載入失敗（{e}）"

    # ── owner 對帳（2026-09-07）：NULL ⇔ 正本該欄空清單；'{}' 一律紅 ──
    row_bad = []
    for r in rows:
        fid = r["canon_ref"]
        fine = fine_map.get(fid)
        if fine is None:
            row_bad.append(f"row {r['id']}：canon_ref={fid!r} 在正本查無此細目")
            continue
        for field in ("business_types", "target_user"):
            raw_val = r[field]
            db_null = (raw_val == "<NULL>")
            db_empty_array = (raw_val == "{}")
            canon_empty = (len(fine[field]) == 0)
            if db_empty_array:
                row_bad.append(
                    f"row {r['id']}（fine {fid}）：{field} 為 '{{}}' 空陣列——⛔ 應為 NULL 或有值"
                )
            elif db_null != canon_empty:
                row_bad.append(
                    f"row {r['id']}（fine {fid}）：{field} NULL={db_null} 但正本該欄空清單="
                    f"{canon_empty}——與正本對不上"
                )
    if row_bad:
        listed = "；".join(row_bad[:8])
        more = "" if len(row_bad) <= 8 else f"（其餘 {len(row_bad) - 8} 條略）"
        return False, f"逐列對帳失敗：{listed}{more}"

    detail_parts = [f"衍生列 {len(rows)}（materialized fine ids {len(materialized_ids)}）"]

    for label, identity_kwargs in REQUIRED_GROUPS:
        try:
            sql_set = predicate_visible_fn(identity_kwargs)
        except Exception as e:  # noqa: BLE001
            return False, f"{label}：SQL 側可見性查詢失敗（{e}）"
        if len(sql_set) < 1:
            return False, f"{label}：SQL 側命中 0 列——空跑不得綠"
        try:
            mem_full = mem_visible_fn(identity_kwargs, frozenset())
        except Exception as e:  # noqa: BLE001
            return False, f"{label}：記憶體側可見性計算失敗（{e}）"
        mem_set = frozenset(mem_full) & materialized_ids
        if sql_set != mem_set:
            only_sql = sorted(sql_set - mem_set)[:5]
            only_mem = sorted(mem_set - sql_set)[:5]
            return False, (
                f"{label}：SQL 側與記憶體側對不上——只在 SQL 側 {only_sql}、"
                f"只在記憶體側 {only_mem}"
            )
        detail_parts.append(f"{label}：命中 {len(sql_set)}（SQL／記憶體一致）")

    note_label, note_kwargs = NOTE_GROUP
    try:
        vbt = vendor_business_types_fn(note_kwargs["vendor_id"])
        if vbt is None:
            note_detail = f"{note_label}：未解析（查無業者資料）——M4 開放 tenant 正本時納入"
        else:
            note_mem = mem_visible_fn(note_kwargs, frozenset(vbt))
            note_detail = (
                f"{note_label}：記憶體側命中 {len(note_mem)}（notes only，不計入必查｜"
                "M4 開放 tenant 正本時納入）"
            )
    except Exception as e:  # noqa: BLE001
        note_detail = f"{note_label}：未解析（{e}）——M4 開放 tenant 正本時納入"
    detail_parts.append(note_detail)

    return True, "；".join(detail_parts)


# ───────────────────────── --self-test（純邏輯，⛔ 不連 docker／DB）─────────────────────────

_FINE_MAP = {
    "A": {"business_types": ["system_provider"], "target_user": []},
    "B": {"business_types": ["system_provider"], "target_user": ["property_manager"]},
    "C": {"business_types": ["system_provider"], "target_user": ["prospect"]},
}

_CONSISTENT_RAW = (
    "101~|~A~|~{system_provider}~|~<NULL>\n"
    "102~|~B~|~{system_provider}~|~{property_manager}\n"
    "103~|~C~|~{system_provider}~|~{prospect}\n"
)


def _fake_canon_visible(fine: dict, identity_kwargs: dict) -> bool:
    """`canon_assembler.canon_visible` 的簡化重現（⛔ 只供自測合成資料用，
    產線路徑一律走真正的 `canon_visible`／`build_visibility_predicate`；
    見模組 docstring「為什麼 --self-test 不打容器」）。"""
    target_user = identity_kwargs["target_user"]
    mode = identity_kwargs["mode"]
    is_b2b = target_user in ("property_manager", "system_admin") or mode == "b2b"
    ftu = set(fine["target_user"])
    fbt = set(fine["business_types"])
    if is_b2b:
        if not (fbt & {"system_provider"}):
            return False
        return (not ftu) or (target_user in ftu)
    return (not ftu) or (target_user in ftu) or ("all_users" in ftu)


def _fake_mem_visible_fn(fine_map: dict):
    def fn(identity_kwargs, _vendor_business_types):
        return frozenset(fid for fid, fine in fine_map.items()
                          if _fake_canon_visible(fine, identity_kwargs))
    return fn


def _fake_predicate_fn(mem_fn, override: dict | None = None):
    override = override or {}
    def fn(identity_kwargs):
        key = (identity_kwargs["target_user"], identity_kwargs["mode"])
        if key in override:
            return override[key]
        return mem_fn(identity_kwargs, frozenset())
    return fn


def _fake_canon_fine_map_fn(fine_map: dict):
    def fn():
        return fine_map
    return fn


def self_test() -> int:
    cases = []

    # ── ① 零衍生列 ⇒ SKIP(pending-D1) ──
    ok1, _d1 = check_canon_visibility_reconcile(query=lambda: "")
    cases.append(("① 零衍生列 ⇒ SKIP(pending-D1)", ok1 is None))

    # ── ② 一致 ⇒ PASS，兩必查組命中 ≥1 ──
    mem_fn = _fake_mem_visible_fn(_FINE_MAP)
    pred_fn = _fake_predicate_fn(mem_fn)
    ok2, detail2 = check_canon_visibility_reconcile(
        query=lambda: _CONSISTENT_RAW,
        predicate_visible_fn=pred_fn,
        mem_visible_fn=mem_fn,
        canon_fine_map_fn=_fake_canon_fine_map_fn(_FINE_MAP),
        vendor_business_types_fn=lambda _vid: [],
    )
    cases.append(("② 衍生列與正本一致 ⇒ PASS", ok2 is True))
    cases.append((
        "② detail 含兩必查組命中數（見輸出）",
        ("b2b pm：命中" in detail2) and ("b2b prospect：命中" in detail2),
    ))

    # ── ③ 突變：b2b pm 的 SQL 側少了 B（模擬該列 business_types 被改壞）⇒ FAIL ──
    pred_fn_mutated = _fake_predicate_fn(
        mem_fn, override={("property_manager", "b2b"): frozenset({"A"})}
    )
    ok3, _d3 = check_canon_visibility_reconcile(
        query=lambda: _CONSISTENT_RAW,
        predicate_visible_fn=pred_fn_mutated,
        mem_visible_fn=mem_fn,
        canon_fine_map_fn=_fake_canon_fine_map_fn(_FINE_MAP),
        vendor_business_types_fn=lambda _vid: [],
    )
    cases.append(("③ 突變一列 business_types（SQL／記憶體對不上）⇒ FAIL", ok3 is False))

    # ── ④ 一列 business_types 為 '{}' 但正本該細目為空清單 ⇒ FAIL ──
    fine_map_with_d = {**_FINE_MAP, "D": {"business_types": [], "target_user": []}}
    raw_with_bad_empty = _CONSISTENT_RAW + "104~|~D~|~{}~|~<NULL>\n"
    ok4, detail4 = check_canon_visibility_reconcile(
        query=lambda: raw_with_bad_empty,
        predicate_visible_fn=pred_fn,
        mem_visible_fn=mem_fn,
        canon_fine_map_fn=_fake_canon_fine_map_fn(fine_map_with_d),
        vendor_business_types_fn=lambda _vid: [],
    )
    cases.append((
        "④ business_types='{}' 對空清單細目 ⇒ FAIL",
        ok4 is False and "'{}'" in detail4,
    ))

    # ── ⑤ 查詢丟例外 ⇒ FAIL（⛔ 不是 SKIP）──
    def _raising_query():
        raise RuntimeError("Cannot connect to the Docker daemon（自測模擬）")
    ok5, _d5 = check_canon_visibility_reconcile(query=_raising_query)
    cases.append(("⑤ 查詢例外 ⇒ FAIL（不是 SKIP）", ok5 is False))

    # ── ⑥ 必查組其中一組命中 0（只有另一組的衍生列）⇒ FAIL ──
    only_c_raw = "103~|~C~|~{system_provider}~|~{prospect}\n"
    pred_fn_only_c = _fake_predicate_fn(
        mem_fn, override={("property_manager", "b2b"): frozenset()}
    )
    ok6, detail6 = check_canon_visibility_reconcile(
        query=lambda: only_c_raw,
        predicate_visible_fn=pred_fn_only_c,
        mem_visible_fn=mem_fn,
        canon_fine_map_fn=_fake_canon_fine_map_fn(_FINE_MAP),
        vendor_business_types_fn=lambda _vid: [],
    )
    cases.append((
        "⑥ 必查組（b2b pm）命中 0 ⇒ FAIL",
        ok6 is False and "b2b pm" in detail6,
    ))

    for name, ok in cases:
        print(f"{'✅' if ok else '❌'} {name}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        ok, detail = check_canon_visibility_reconcile()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 不變量 33：正本可見性與 kb 衍生列三軸對帳 —— 檢查無法執行（{e}）——大聲失敗")
        return 1
    if ok is None:
        print(f"⚠️  不變量 33：正本可見性與 kb 衍生列三軸對帳 —— {detail}")
        return 0
    print(f"{'✅' if ok else '❌'} 不變量 33：正本可見性與 kb 衍生列三軸對帳 —— {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
