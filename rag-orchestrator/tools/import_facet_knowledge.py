#!/usr/bin/env python3
"""知識批次匯入工具（部署重放依賴——runbook §1.3/§2 引用，非一次性）。

來源：批次 JSON（預設合約面向批次；可帶路徑參數指定，如 scripts/audit/reports/*-import.json）
行為：
  - updates：修正既有知識 answer；若帶 question 則同時改 question_summary 並**重算 embedding**（S 類「講法」修法）
  - knowledge：INSERT 新知識（含 embedding；冪等：question_summary 已存在則跳過）
  - anchors：INSERT 錨點列（answer 空、掛面向、含 embedding）
匯入後請執行：reranker semantic model 重建＋清系統脈絡/設定快取（tasks 6.3）。

⛔ 2026-09-04 起的必填契約（steering knowledge.md「instance applicability」節，P1d 2026-08-30 生效）：
  - knowledge／anchors 每筆必填 `instance_applicability` ∈ {"instance","general"}，寫入
    `generation_metadata.instance_applicability`；缺或寫錯字 ⇒ **整批不寫、exit 2**（不變量 10 會抓，這裡先擋）。
  - updates 會更新 updated_at，讓舊列的 touched_at 跨過 P1d 生效日 ⇒ 目標列若尚未宣告，批次必須補 `instance_applicability`，
    否則該筆拒絕更新（⛔ 不得把未宣告的舊列悄悄推過生效日）。
  - `business_types` 可逐筆指定，未給則沿用舊行為 ["system_provider"]（b2b 池）；anchors 的 target_user 未給沿用 ["property_manager"]。
  - `--allow-legacy-undeclared`：只給 2026-08-30 前定稿的舊批次重放用；仍會逐筆印警告，且新列照樣會被不變量 10 列為未宣告。

用法：python3 rag-orchestrator/tools/import_facet_knowledge.py [批次.json] [--dry-run] [--allow-legacy-undeclared]
需求：本機 aichatbot-postgres（5432 對外）與 embedding-api（5001 對外）。
"""
import asyncio
import json
import os
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple

# 宣告鍵與合法值**只能**從契約模組取（不變量 10：鍵名字串不得出現在契約模組以外的程式碼）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from services.instance_applicability import (  # noqa: E402
    DECLARED_VALUES, KNOWLEDGE_APPLICABILITY_KEY as APPLICABILITY_KEY, knowledge_instance_applicability,
    APPLICABILITY_UNKNOWN,
)
DEFAULT_BUSINESS_TYPES = ["system_provider"]
DEFAULT_ANCHOR_TARGET_USER = ["property_manager"]
EMB_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:5001/api/v1/embeddings")


# ── 純函式（可測）──────────────────────────────────────────────────────────────
def validate_batch(d: dict, *, allow_legacy_undeclared: bool = False) -> List[str]:
    """回傳錯誤清單（空＝可寫）。⛔ 任何一條錯 ⇒ 呼叫端整批不寫。"""
    errs: List[str] = []
    for section, need_answer in (("knowledge", True), ("anchors", False)):
        for i, k in enumerate(d.get(section) or []):
            tag = f"{section}[{i}] {str(k.get('question', ''))[:30]!r}"
            if not k.get("question"):
                errs.append(f"{tag}: 缺 question")
            if need_answer and not k.get("answer"):
                errs.append(f"{tag}: 缺 answer")
            if section == "knowledge" and not k.get("target_user"):
                errs.append(f"{tag}: 缺 target_user")
            if section == "anchors" and not k.get("facet"):
                errs.append(f"{tag}: 缺 facet")
            v = k.get(APPLICABILITY_KEY)
            if v is None:
                if not allow_legacy_undeclared:
                    errs.append(f"{tag}: 缺 {APPLICABILITY_KEY}（必填 instance／general；舊批次重放才可用 --allow-legacy-undeclared）")
            elif v not in DECLARED_VALUES:
                errs.append(f"{tag}: {APPLICABILITY_KEY}={v!r} 不合法（只接受 instance／general，⛔ 不接受變體）")
            for arr in ("target_user", "business_types", "categories", "keywords"):
                if arr in k and k[arr] is not None and not isinstance(k[arr], list):
                    errs.append(f"{tag}: {arr} 必須是陣列")
    for i, u in enumerate(d.get("updates") or []):
        tag = f"updates[{i}] id={u.get('id')}"
        if not isinstance(u.get("id"), int):
            errs.append(f"{tag}: id 必須是整數")
        if not u.get("answer") and not u.get("question"):
            errs.append(f"{tag}: answer 與 question 至少一個")
        v = u.get(APPLICABILITY_KEY)
        if v is not None and v not in DECLARED_VALUES:
            errs.append(f"{tag}: {APPLICABILITY_KEY}={v!r} 不合法")
    return errs


def build_generation_metadata(entry: dict, *, declared_by: str = "import_script") -> Optional[Dict[str, str]]:
    """組 generation_metadata 片段；未宣告（legacy）回 None ⇒ 不寫該鍵，讓不變量 10 照實列為未宣告。"""
    v = entry.get(APPLICABILITY_KEY)
    if v is None:
        return None
    if v not in DECLARED_VALUES:
        raise ValueError(f"{APPLICABILITY_KEY}={v!r} 不合法")
    return {APPLICABILITY_KEY: v, f"{APPLICABILITY_KEY}_declared_by": declared_by}


def existing_declaration(generation_metadata) -> Optional[str]:
    """讀既有列的宣告——經契約模組讀（只認合法值，⛔ 不猜變體）。asyncpg 可能回 str 或 dict。"""
    meta = generation_metadata
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return None
    v = knowledge_instance_applicability({"generation_metadata": meta})
    return None if v == APPLICABILITY_UNKNOWN else v


def update_decision(existing_meta, entry: dict) -> Tuple[str, Optional[str]]:
    """updates 每筆的處置：('write', 要寫的宣告或 None) 或 ('refuse', 原因)。
    規則：目標列已宣告 ⇒ 可寫（批次若也給且不同 ⇒ 以批次為準並印出）；未宣告 ⇒ 批次必須補，否則拒絕。"""
    have = existing_declaration(existing_meta)
    want = entry.get(APPLICABILITY_KEY)
    if have is None and want is None:
        return "refuse", f"目標列尚未宣告 {APPLICABILITY_KEY}，更新會把它推過 P1d 生效日 ⇒ 批次必須補 instance／general"
    return "write", (want if want is not None else None)


def insert_params_knowledge(k: dict) -> dict:
    return {"question": k["question"], "answer": k["answer"], "categories": k.get("categories"),
            "target_user": k["target_user"], "business_types": k.get("business_types") or DEFAULT_BUSINESS_TYPES,
            "keywords": k.get("keywords"), "generation_metadata": build_generation_metadata(k)}


def insert_params_anchor(a: dict) -> dict:
    return {"question": a["question"], "answer": "", "categories": [a["facet"]],
            "target_user": a.get("target_user") or DEFAULT_ANCHOR_TARGET_USER,
            "business_types": a.get("business_types") or DEFAULT_BUSINESS_TYPES,
            "keywords": a.get("keywords"), "generation_metadata": build_generation_metadata(a)}


# ── I/O ────────────────────────────────────────────────────────────────────────
def get_embedding(text: str):
    req = urllib.request.Request(EMB_URL, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        emb = json.loads(r.read())["embedding"]
    assert len(emb) == 1536, f"embedding 維度異常：{len(emb)}"
    return "[" + ",".join(f"{v:.8f}" for v in emb) + "]"


_INSERT_SQL = (
    "INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types, keywords, "
    " scope, priority, is_active, source_type, created_by, embedding, generation_metadata) "
    "VALUES ($1,$2,$3,$4,$5,$6,'global',0,TRUE,'manual','import_script',$7::vector, "
    "        COALESCE($8::jsonb, '{}'::jsonb))"
)


async def _insert(conn, p: dict, dry: bool):
    if dry:
        return
    emb = get_embedding(p["question"])
    meta = json.dumps(p["generation_metadata"], ensure_ascii=False) if p["generation_metadata"] else None
    await conn.execute(_INSERT_SQL, p["question"], p["answer"], p["categories"], p["target_user"],
                       p["business_types"], p["keywords"], emb, meta)


async def run(batch_path: str, *, dry: bool, allow_legacy_undeclared: bool) -> int:
    import asyncpg
    d = json.load(open(batch_path, encoding="utf-8"))
    errs = validate_batch(d, allow_legacy_undeclared=allow_legacy_undeclared)
    if errs:
        print(f"❌ 批次驗證未過（{len(errs)} 條），整批不寫：")
        for e in errs:
            print("   -", e)
        return 2
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"), min_size=1, max_size=2)

    n_upd = n_new = n_anchor = n_skip = n_refuse = n_legacy = 0
    async with pool.acquire() as conn:
        # 1) 既有知識修正。answer 變不影響向量（embedding 以 question_summary 為準，feedback_embedding_integrity）；
        #    question 變 ⇒ 重算 embedding。兩者都會更新 updated_at ⇒ 宣告契約見 update_decision。
        for u in d.get("updates", []):
            row = await conn.fetchrow("SELECT id, question_summary, generation_metadata FROM knowledge_base WHERE id=$1", u["id"])
            if not row:
                print(f"  ⚠️ UPDATE 目標 id={u['id']} 不存在，跳過")
                n_skip += 1
                continue
            verdict, payload = update_decision(row["generation_metadata"], u)
            if verdict == "refuse":
                print(f"  ⛔ UPDATE {u['id']} 拒絕：{payload}")
                n_refuse += 1
                continue
            new_q = u.get("question")
            print(f"  ✏️ UPDATE {u['id']} {row['question_summary'][:30]}" + (f" → question 改為 {new_q[:30]!r}（重算 embedding）" if new_q else "")
                  + (f"；宣告 {payload}" if payload else ""))
            if not dry:
                sets, args = ["updated_at=now()", "updated_by='import_script'"], [u["id"]]
                if u.get("answer"):
                    args.append(u["answer"]); sets.append(f"answer=${len(args)}")
                if new_q:
                    args.append(new_q); sets.append(f"question_summary=${len(args)}")
                    args.append(get_embedding(new_q)); sets.append(f"embedding=${len(args)}::vector")
                if payload:
                    args.append(json.dumps(build_generation_metadata(u), ensure_ascii=False))
                    sets.append(f"generation_metadata=COALESCE(generation_metadata,'{{}}'::jsonb) || ${len(args)}::jsonb")
                await conn.execute(f"UPDATE knowledge_base SET {', '.join(sets)} WHERE id=$1", *args)
            n_upd += 1

        # 2) 新知識
        for k in d.get("knowledge", []):
            exists = await conn.fetchval("SELECT id FROM knowledge_base WHERE question_summary=$1", k["question"])
            if exists:
                print(f"  ⏭️ 已存在（id={exists}）：{k['question']}")
                n_skip += 1
                continue
            p = insert_params_knowledge(k)
            if p["generation_metadata"] is None:
                n_legacy += 1
                print(f"  ⚠️ 未宣告 {APPLICABILITY_KEY}（legacy）：{k['question'][:30]}——不變量 10 會列為未宣告")
            print(f"  ＋ [{k.get('facet','單發')}] {k['question']}" + ("（掛面向）" if k.get("categories") else "")
                  + f" bt={p['business_types']} tu={p['target_user']}")
            await _insert(conn, p, dry)
            n_new += 1

        # 3) 錨點（answer 空、掛面向）
        for a in d.get("anchors", []):
            exists = await conn.fetchval("SELECT id FROM knowledge_base WHERE question_summary=$1", a["question"])
            if exists:
                print(f"  ⏭️ 錨點已存在（id={exists}）：{a['question']}")
                n_skip += 1
                continue
            p = insert_params_anchor(a)
            if p["generation_metadata"] is None:
                n_legacy += 1
                print(f"  ⚠️ 錨點未宣告 {APPLICABILITY_KEY}（legacy）：{a['question'][:30]}")
            print(f"  ⚓ [{a['facet']}] {a['question']} tu={p['target_user']}")
            await _insert(conn, p, dry)
            n_anchor += 1

    await pool.close()
    mode = "（dry-run，未寫入）" if dry else ""
    print(f"完成{mode}：修正 {n_upd}、新知識 {n_new}、錨點 {n_anchor}、跳過 {n_skip}、拒絕 {n_refuse}、legacy 未宣告 {n_legacy}")
    if not dry:
        print("⚠️ 後續：reranker semantic model 重建＋清快取（tasks 6.3），否則排序不含新知識")
    return 1 if n_refuse else 0


def _parse_argv(argv: List[str]) -> Tuple[str, bool, bool]:
    args = [a for a in argv if not a.startswith("--")]
    batch = args[0] if args else os.path.join(os.path.dirname(__file__), "..", "..",
                                              "scripts", "knowledge-batches", "contract-knowledge-batch.json")
    return batch, "--dry-run" in argv, "--allow-legacy-undeclared" in argv


if __name__ == "__main__":
    _batch, _dry, _legacy = _parse_argv(sys.argv[1:])
    sys.exit(asyncio.run(run(_batch, dry=_dry, allow_legacy_undeclared=_legacy)))
