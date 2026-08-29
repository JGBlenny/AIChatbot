#!/usr/bin/env python3
"""不變量 23（G10）：**canonical responsibility embedding index 完整性**（C2-SCORE，2026-08-30）。

⚠️ 這是 sealed Registry V2 的 **derived runtime artifact**，⛔ 不是 authority source。
業主鎖死的角色：row／alias embeddings ＝ nomination／recall；
canonical embeddings ＝ collapse ＋ top20 **之後**的 responsibility semantic vector component。

## 不變量陳述

> ① 30 個 reviewed_active ＝ **30 筆** embeddings（historical ⛔ 0 筆；16 unresolved rows ⛔ 不建）
> ② 每筆 `canonical_text_digest` 與 registry V2 的 canonical 文字**逐字相符**（文字 drift → 紅）
> ③ `registry_v2_digest` 與現行 registry-v2.json 相符（authority epoch drift → 紅）
> ④ `embedding_model_id` 與 manifest 一致且非空（model drift → 紅）
> ⑤ 維度一致，且每筆 `embedding_checksum` 可由向量重算（內容被改 → 紅）
> ⑥ embeddings 檔 bytes 與 manifest 的 `embeddings_file_digest` 相符

⚠️ 業主定的重建條件：canonical text 改／registry epoch 改／embedding model 改 —— 任一即須重建。

用法：python3 scripts/audit/checks/canonical_embedding_index.py [--self-test]
"""
import copy
import hashlib
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R10P = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
REG = os.path.join(R10P, "registry-v2.json")
DER = os.path.join(R10P, "derived")
EMB = os.path.join(DER, "canonical-embeddings.json")
MAN = os.path.join(DER, "canonical-embeddings-manifest.json")


def sha_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def load():
    with open(REG, "rb") as f:
        rraw = f.read()
    with open(EMB, "rb") as f:
        eraw = f.read()
    return {"reg": json.loads(rraw), "reg_digest": hashlib.sha256(rraw).hexdigest(),
            "emb": json.loads(eraw), "eraw": eraw,
            "man": json.load(open(MAN, encoding="utf-8"))}


def violations(st=None):
    st = load() if st is None else st
    reg, emb, man = st["reg"], st["emb"], st["man"]
    bad = []
    active = {r["responsibility_id"]: r for r in reg["responsibilities"]
              if r["status"] == "reviewed_active"}
    hist = {r["responsibility_id"] for r in reg["responsibilities"]
            if r["status"] != "reviewed_active"}
    entries = {e["responsibility_id"]: e for e in emb["entries"]}

    missing = sorted(set(active) - set(entries))
    extra = sorted(set(entries) - set(active))
    if missing:
        bad.append(f"reviewed_active 缺 embedding：{missing}——⚠️ 半套 semantic surface")
    if extra:
        bad.append(f"embedding 多出非 active 的責任：{extra}")
    for h in sorted(hist & set(entries)):
        bad.append(f"{h} 是 reviewed_historical，⛔ 不得有 embedding")
    if emb.get("count") != len(entries):
        bad.append(f"count {emb.get('count')} ≠ 實際 {len(entries)}")

    if emb.get("registry_v2_digest") != st["reg_digest"]:
        bad.append("registry_v2_digest 與現行 registry-v2.json 不符——⚠️ authority epoch 已變，必須重建")
    if not emb.get("embedding_model_id"):
        bad.append("embedding_model_id 為空")
    if man.get("embedding_model_id") != emb.get("embedding_model_id"):
        bad.append("manifest 與 index 的 embedding_model_id 不符")

    dim = emb.get("embedding_dimension")
    for rid, e in sorted(entries.items()):
        r = active.get(rid)
        if r is None:
            continue
        want = sha_text(r["canonical_responsibility"])
        if e["canonical_text_digest"] != want:
            bad.append(f"{rid}：canonical text drift（embedding 是對舊文字建的）——必須重建")
        v = e.get("embedding") or []
        if len(v) != dim:
            bad.append(f"{rid}：維度 {len(v)} ≠ {dim}")
        got = hashlib.sha256(",".join(f"{x:.8f}" for x in v).encode()).hexdigest()
        if got != e["embedding_checksum"]:
            bad.append(f"{rid}：embedding_checksum 重算不符——向量內容被改過")

    if man.get("embeddings_file_digest") != hashlib.sha256(st["eraw"]).hexdigest():
        bad.append("embeddings 檔 bytes 與 manifest 記錄不符")
    return bad


def self_test() -> int:
    st = load()
    cases = [("現況乾淨", violations(st) == [])]

    def mut(fn):
        m = copy.deepcopy(st); fn(m); return m
    def refresh(m):
        m["man"]["embeddings_file_digest"] = hashlib.sha256(m["eraw"]).hexdigest()

    m = mut(lambda d: d["emb"]["entries"].pop())
    cases.append(("漏一筆必須紅", any("缺 embedding" in x for x in violations(m))))

    def drift(d):
        d["emb"]["entries"][0]["canonical_text_digest"] = "deadbeef"
    m = mut(drift)
    cases.append(("canonical text drift 必須紅", any("text drift" in x for x in violations(m))))

    m = mut(lambda d: d["emb"].update({"embedding_model_id": ""}))
    cases.append(("model id 空必須紅", any("embedding_model_id 為空" in x for x in violations(m))))

    m = mut(lambda d: d["emb"].update({"registry_v2_digest": "cafebabe"}))
    cases.append(("registry epoch 漂移必須紅",
                  any("authority epoch 已變" in x for x in violations(m))))

    def tamper(d):
        d["emb"]["entries"][0]["embedding"][0] += 0.5
    m = mut(tamper)
    cases.append(("向量被改必須紅", any("checksum 重算不符" in x for x in violations(m))))

    def add_hist(d):
        h = next(r["responsibility_id"] for r in d["reg"]["responsibilities"]
                 if r["status"] != "reviewed_active")
        e = copy.deepcopy(d["emb"]["entries"][0]); e["responsibility_id"] = h
        d["emb"]["entries"].append(e)
    m = mut(add_hist)
    cases.append(("historical 有 embedding 必須紅",
                  any("不得有 embedding" in x for x in violations(m))))

    m = mut(lambda d: d.update({"eraw": d["eraw"] + b" "}))
    cases.append(("embeddings 檔 bytes 被改必須紅",
                  any("bytes 與 manifest 記錄不符" in x for x in violations(m))))

    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.exists(EMB):
        print("（canonical embedding index 尚未建立——C2-SCORE 未落地，本條不適用）")
        return 0
    bad = violations()
    if bad:
        print("❌ FAIL：canonical embedding index（G10）")
        for b in bad:
            print(f"   · {b}")
        return 1
    st = load()
    print(f"（canonical embeddings：{st['emb']['count']} 筆／dim={st['emb']['embedding_dimension']}／"
          f"model={st['emb']['embedding_model_id']}；text digest 逐筆相符；"
          f"historical ⛔ 0 筆；⛔ 非 authority source）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
