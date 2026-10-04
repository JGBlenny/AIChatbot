# -*- coding: utf-8 -*-
"""Plan 9.28 彙整：24 份批次證據 × 批次清單 × 誘餌清單 × 正本 ⇒ 每批有效性、逐條結果、不成立清單。
用法：python3 aggregate.py <批次證據目錄> <decoy-manifest.json> <jgb.json> <輸出 summary.json> [--self-test]
批次證據檔名＝`*-p928-<批號>.json`。
抽查：`--sample-out <檔>` 產生種子 20261012 的 20 句抽樣；`--spotcheck <抽查證據>` 把推翻句放進獨立欄 spotcheck_overturned（⛔ 混入批次清單）。
用法補充：python3 aggregate.py <目錄> <manifest> <jgb.json> <out> [--sample-out P] [--spotcheck P]任何結構不符 ⇒ 該批 invalid（⛔ 靜默略過）；缺批 ⇒ invalid。"""
import glob, hashlib, json, os, random, re, sys, tempfile

# 合法來源路徑：jgb2 匯出內程式、幫助中心 html、事實帳本、審核單。
LEGAL = re.compile(r"[\w\-\[\]]+\.(?:php|vue|jsx?|tsx?)(?![\w])|[\w.\-]+_zh-Hant\.html|jgb-product-facts\.md|review-sheet-[\w.\-]+\.md"
                   r"|(?:src|resources|lang|config)/[\w./\-]+\.json")
# 禁讀位置（正本、drafts、驗證證據、brief／誘餌清單）：notes 引用到即表示違反禁讀 ⇒ 該批作廢。
FORBID = re.compile(r"rag-orchestrator/|canon/jgb|jgb\.json|CATALOG\.md|verification/|drafts-[A-I]\.json|outline-curation/runs|decoy-manifest|brief-B\d")


def _note(notes, n):
    return next((z for z in notes if re.match(rf"\s*句\s*{n}\s*[：:]", z)), None)
OK = {"成立", "不成立"}


def check_batch(ev, m, F):
    """回傳 (errors, real_results, decoy_result)。"""
    errs = []
    if ev is None:
        return ["缺證據檔"], {}, None
    if ev.get("kind") != "write":
        errs.append(f"kind＝{ev.get('kind')!r}，須為 'write'")
    fines = ev.get("fines")
    if not isinstance(fines, list):
        return ["fines 不是陣列"], {}, None
    got = [x.get("id") for x in fines]
    want = set(m["fines"]) | {m["decoy_id"]}
    if len(got) != len(set(got)):
        errs.append("fines 有重複 id")
    if set(got) != want:
        errs.append(f"細目集合不符：少 {sorted(want - set(got))[:5]}、多 {sorted(set(got) - want)[:5]}")
    real, decoy = {}, None
    for x in fines:
        fid = x.get("id")
        t, s, notes = x.get("title"), x.get("sentences"), x.get("notes") or []
        if not isinstance(t, str) or t not in OK or not isinstance(s, list) or any(not isinstance(v, str) or v not in OK for v in s):
            errs.append(f"{fid}：title／sentences 不是 成立／不成立 字串")
            continue
        if fid == m["decoy_id"]:
            if x.get("content_sha256") != m["decoy_sha"]:
                errs.append(f"誘餌 {fid}：content_sha256 不符")
            decoy = x
            continue
        if fid not in F:
            continue
        f = F[fid]
        if len(s) != len(f["content_units"]):
            errs.append(f"{fid}：句數 {len(s)} ≠ 正本 {len(f['content_units'])}")
        if x.get("content_sha256") != f["content_sha256"]:
            errs.append(f"{fid}：content_sha256 ≠ 正本")
        if x.get("title_text") != f["title"]:
            errs.append(f"{fid}：title_text ≠ 正本")
        if not any(isinstance(z, str) and z.lstrip().startswith("標題") for z in notes):
            errs.append(f"{fid}：缺「標題：」note")
        for i in range(1, len(s) + 1):
            z = _note([w for w in notes if isinstance(w, str)], i)
            if z is None:
                errs.append(f"{fid}：缺「句 {i}：」note")
            elif not LEGAL.search(z) and "無法判定" not in z and "同上" not in z:
                errs.append(f"{fid}：句 {i} 的 note 沒有來源檔名（也沒寫「同上」）")
        if s and not any(LEGAL.search(z) for z in notes if isinstance(z, str)):
            errs.append(f"{fid}：整條 notes 沒有引用任何合法來源檔")
        real[fid] = x
    dres = None
    if decoy is None:
        errs.append("誘餌缺席")
    else:
        n = m["sentence"]
        s = decoy["sentences"]
        caught = len(s) >= n and s[n - 1] == "不成立"
        note = _note([w for w in (decoy.get("notes") or []) if isinstance(w, str)], n) or ""
        dnotes = [w for w in (decoy.get("notes") or []) if isinstance(w, str)]
        cited = bool(LEGAL.search(note)) or ("同上" in note and any(LEGAL.search(w) for w in dnotes))
        others = sum(1 for i, v in enumerate(s, 1) if i != n and v == "不成立")
        dres = {"caught": caught, "cited_source": cited, "other_flagged": others}
        if not caught:
            errs.append(f"誘餌句 {n} 未被判不成立（驗證不可信）")
        elif not cited:
            errs.append(f"誘餌句 {n} 判不成立但 notes 沒有引用來源檔")
    allnotes = [z for x in fines for z in (x.get("notes") or []) if isinstance(z, str)] + \
        [z for z in (ev.get("findings") or []) if isinstance(z, str)]
    if any(FORBID.search(z) for z in allnotes):
        errs.append("notes／findings 引用了禁讀位置（正本、drafts、證據或 brief）")
    anyfail = any(x.get("title") == "不成立" or "不成立" in (x.get("sentences") or []) for x in fines)
    if ev.get("verdict") != ("REFUTED" if anyfail else "CONFIRMED"):
        errs.append(f"verdict＝{ev.get('verdict')!r} 與 fines 判定不一致")
    return errs, real, dres


def aggregate(evdir, manifest, canon):
    F = {f["id"]: f for c in canon["coarses"] for f in c["fines"]}
    out = {"batches": [], "fines_checked": 0, "sentences_checked": 0, "titles_failed": [], "sentences_failed": [],
           "valid_batches": 0, "holding_sentences": []}
    for m in manifest:
        paths = glob.glob(os.path.join(evdir, f"*-p928-{m['batch']}.json"))
        ev = json.load(open(paths[0], encoding="utf-8")) if len(paths) == 1 else None
        errs, real, dres = check_batch(ev, m, F)
        if len(paths) > 1:
            errs = errs + [f"同批有 {len(paths)} 份證據檔"]
        b = {"batch": m["batch"], "valid": not errs, "errors": errs, "decoy": dres,
             "base": (ev or {}).get("base"), "verdict": (ev or {}).get("verdict"),
             "source_transcript": (ev or {}).get("source_transcript"),
             "evidence": os.path.basename(paths[0]) if len(paths) == 1 else None}
        out["batches"].append(b)
        if errs:
            continue
        out["valid_batches"] += 1
        for fid, x in real.items():
            notes = [z for z in x["notes"] if isinstance(z, str)]
            out["fines_checked"] += 1
            out["sentences_checked"] += len(x["sentences"])
            if x["title"] == "不成立":
                out["titles_failed"].append({"id": fid, "batch": m["batch"],
                                             "note": next((z for z in notes if z.lstrip().startswith("標題")), "")})
            for i, v in enumerate(x["sentences"], 1):
                if v == "不成立":
                    out["sentences_failed"].append({"id": fid, "n": i, "batch": m["batch"], "note": _note(notes, i) or ""})
                else:
                    out["holding_sentences"].append([fid, i])
    out["fines_fully_holding"] = out["fines_checked"] - len({x["id"] for x in out["titles_failed"] + out["sentences_failed"]})
    return out


def spot_sample(out, k=20, seed=20261012):
    pool = sorted(tuple(x) for x in out["holding_sentences"])
    return [list(x) for x in random.Random(seed).sample(pool, min(k, len(pool)))]


def apply_spotcheck(out, sc, sample):
    """抽查證據 ⇒ out["spotcheck"]；推翻句只進 spotcheck_overturned。結構不符 ⇒ errors 非空。"""
    errs = []
    if sc.get("kind") != "change":
        errs.append("抽查證據 kind 須為 'change'")
    items = sc.get("sample") or []
    got = [(x.get("id"), x.get("n")) for x in items]
    if sorted(got) != sorted(tuple(x) for x in sample):
        errs.append("抽查集合與種子抽樣不符")
    over = []
    for x in items:
        v, z = x.get("verdict"), x.get("note")
        if not isinstance(v, str) or v not in OK or not isinstance(z, str):
            errs.append(f"{x.get('id')} 句 {x.get('n')}：verdict／note 格式不符")
            continue
        if FORBID.search(z):
            errs.append(f"{x.get('id')} 句 {x.get('n')}：note 引用禁讀位置")
        if not LEGAL.search(z) and "無法判定" not in z:
            errs.append(f"{x.get('id')} 句 {x.get('n')}：note 沒有合法來源路徑")
        if v == "不成立":
            over.append({"id": x["id"], "n": x["n"], "note": z})
    if sc.get("verdict") != ("REFUTED" if over else "CONFIRMED"):
        errs.append("抽查 verdict 與逐句判定不一致")
    out["spotcheck"] = {"valid": not errs, "errors": errs, "base": sc.get("base"), "sample": sample,
                        "source_transcript": sc.get("source_transcript")}
    out["spotcheck_overturned"] = over if not errs else []
    return out


def apply_redo(r, redo):
    """重做清單 ⇒ 每批 b["redo"]＝{resend, replace, voided, note, disclosure}；清單批號集合須恰等於彙整批號（大聲失敗）。"""
    rb = redo.get("batches") or {}
    names = [b["batch"] for b in r["batches"]]
    if set(rb) != set(names):
        raise SystemExit(f"重做清單批號與彙整不符：少 {sorted(set(names) - set(rb))}、多 {sorted(set(rb) - set(names))}")
    for b in r["batches"]:
        x = rb[b["batch"]]
        b["redo"] = {k: x.get(k, 0 if k in ("resend", "replace", "voided") else "") for k in ("resend", "replace", "voided", "note", "disclosure")}
    return r


def write_md(r, canon, path):
    """人讀版：每項附細目 id、句序、正本原句、批次 notes 理由；筆數與 JSON 相同。"""
    F = {f["id"]: f for c in canon["coarses"] for f in c["fines"]}
    L = ["# Plan 9.28 存量補核結果（機械產生，⛔ 手改；來源＝同名 .json）", "",
         f"- 有效批 {r['valid_batches']}／{len(r['batches'])}；核對細目 {r['fines_checked']}、句 {r['sentences_checked']}；全條成立 {r['fines_fully_holding']}",
         f"- 標題不成立 {len(r['titles_failed'])}；句不成立 {len(r['sentences_failed'])}"
         + (f"；抽查推翻 {len(r.get('spotcheck_overturned', []))}" if "spotcheck" in r else ""), ""]
    if all("redo" in b for b in r["batches"]):
        L += ["## 〇、各批有效性與重做次數", "", "| 批 | 有效 | 重貼 | 換人 | 作廢 | 說明 |", "|---|---|---|---|---|---|"]
        for b in r["batches"]:
            x = b["redo"]
            note = "；".join(z for z in (x["note"], x["disclosure"]) if z).replace("|", "／")
            L.append(f"| {b['batch']} | {'是' if b['valid'] else '否'} | {x['resend']} | {x['replace']} | {x['voided']} | {note} |")
        L.append("")
    L += ["## 一、標題不成立", "", "| # | 細目 | 批 | 正本標題 | 批次理由 |", "|---|---|---|---|---|"]
    for i, x in enumerate(r["titles_failed"], 1):
        L.append(f"| {i} | `{x['id']}` | {x['batch']} | {F[x['id']]['title']} | {x['note'].replace('|', '／')} |")
    L += ["", "## 二、句不成立", "", "| # | 細目 | 句 | 批 | 正本原句 | 批次理由 |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(r["sentences_failed"], 1):
        s = F[x["id"]]["content_units"][x["n"] - 1]
        L.append(f"| {i} | `{x['id']}` | {x['n']} | {x['batch']} | {s.replace('|', '／')} | {x['note'].replace('|', '／')} |")
    if "spotcheck" in r:
        L += ["", "## 三、抽查推翻（獨立欄 spotcheck_overturned）", "", "| # | 細目 | 句 | 正本原句 | 抽查理由 |", "|---|---|---|---|---|"]
        for i, x in enumerate(r["spotcheck_overturned"], 1):
            s = F[x["id"]]["content_units"][x["n"] - 1]
            L.append(f"| {i} | `{x['id']}` | {x['n']} | {s.replace('|', '／')} | {x['note'].replace('|', '／')} |")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def self_test():
    canon = {"coarses": [{"fines": [
        {"id": "a", "title": "A", "content_units": ["x", "y"], "content_sha256": hashlib.sha256(b"x\ny").hexdigest()},
        {"id": "b", "title": "B", "content_units": ["z"], "content_sha256": hashlib.sha256(b"z").hexdigest()}]}]}
    man = [{"batch": "B01", "fines": ["a", "b"], "decoy_id": "a-faq", "decoy_sha": "d" * 64, "sentence": 2}]
    F = {f["id"]: f for f in canon["coarses"][0]["fines"]}
    def fx(fid, s, t="成立"):
        f = F.get(fid)
        return {"id": fid, "title": t, "sentences": s, "content_sha256": f["content_sha256"] if f else "d" * 64,
                "title_text": f["title"] if f else "A",
                "notes": ["標題：ok"] + [f"句 {i}：app/Http/Controllers/X.php ok" for i in range(1, len(s) + 1)]}
    good = {"kind": "write", "base": "h", "verdict": "REFUTED",
            "fines": [fx("a", ["成立", "不成立"]), fx("b", ["成立"]), fx("a-faq", ["成立", "不成立"])]}
    def with_notes(fid, s, notes):
        return {**fx(fid, s), "notes": notes}
    cases = [("正確（含 1 句不成立）", good, True),
             ("誘餌漏抓", {**good, "fines": good["fines"][:2] + [fx("a-faq", ["成立", "成立"])]}, False),
             ("誘餌判不成立但沒引來源", {**good, "fines": good["fines"][:2] + [with_notes("a-faq", ["成立", "不成立"], ["標題：x", "句 1：app/A.php", "句 2：看起來不對"])]}, False),
             ("誘餌只引正本 jgb.json", {**good, "fines": good["fines"][:2] + [with_notes("a-faq", ["成立", "不成立"], ["標題：x", "句 1：src/pages/A.vue", "句 2：rag-orchestrator/canon/jgb.json 原句不同"])]}, False),
             ("誘餌只引 verification 證據", {**good, "fines": good["fines"][:2] + [with_notes("a-faq", ["成立", "不成立"], ["標題：x", "句 1：src/pages/A.vue", "句 2：.kiro/specs/x/verification/20261004-p923-write.json"])]}, False),
             ("真細目 note 引用禁讀位置", {**good, "fines": [with_notes("a", ["成立", "不成立"], ["標題：x", "句 1：app/A.php，另見 drafts-A.json", "句 2：app/A.php"])] + good["fines"][1:]}, False),
             ("真細目一句 note 沒有路徑", {**good, "fines": [with_notes("a", ["成立", "不成立"], ["標題：x", "句 1：看過了", "句 2：app/A.php"])] + good["fines"][1:]}, False),
             ("真細目 note 全是「同上」", {**good, "fines": [with_notes("a", ["成立", "不成立"], ["標題：x", "句 1：同上", "句 2：同上"])] + good["fines"][1:]}, False),
             ("真細目「同上」承接前句（有效）", {**good, "fines": [with_notes("a", ["成立", "不成立"], ["標題：x", "句 1：app/A.php ok", "句 2：同上，實際不同"])] + good["fines"][1:]}, True),
             ("真細目缺「句 n」note", {**good, "fines": [with_notes("a", ["成立", "不成立"], ["標題：x", "句 1：app/A.php"])] + good["fines"][1:]}, False),
             ("kind＝change", {**good, "kind": "change"}, False),
             ("verdict 與 fines 矛盾", {**good, "verdict": "CONFIRMED"}, False),
             ("少一條", {**good, "fines": [good["fines"][0], good["fines"][2]]}, False),
             ("句數不符", {**good, "fines": [fx("a", ["成立"]), good["fines"][1], good["fines"][2]]}, False),
             ("sha 不符", {**good, "fines": [{**fx("a", ["成立", "成立"]), "content_sha256": "0" * 64}] + good["fines"][1:]}, False),
             ("元素不是字串", {**good, "fines": [{**fx("a", ["成立", "成立"]), "sentences": [{"v": "成立"}, "成立"]}] + good["fines"][1:]}, False),
             ("缺證據檔", None, False)]
    bad = []
    for name, ev, want in cases:
        with tempfile.TemporaryDirectory() as d:
            if ev is not None:
                json.dump(ev, open(os.path.join(d, "20261004-p928-B01.json"), "w"))
            r = aggregate(d, man, canon)
        ok = r["batches"][0]["valid"] == want
        if name.startswith("正確"):
            ok = ok and r["sentences_failed"] == [{"id": "a", "n": 2, "batch": "B01", "note": "句 2：app/Http/Controllers/X.php ok"}] \
                and r["fines_fully_holding"] == 1 and sorted(map(tuple, r["holding_sentences"])) == [("a", 1), ("b", 1)]
        print(("✅ " if ok else "❌ ") + name, r["batches"][0]["errors"][:1])
        if not ok:
            bad.append(name)
    # 抽查：推翻句只進獨立欄，批次清單不變（A5 與 A7 可同時成立）
    with tempfile.TemporaryDirectory() as d:
        json.dump(good, open(os.path.join(d, "20261004-p928-B01.json"), "w"))
        base = aggregate(d, man, canon)
    sample = spot_sample(base, k=2)
    sc = {"kind": "change", "verdict": "REFUTED", "base": "h", "sample": [
        {"id": sample[0][0], "n": sample[0][1], "verdict": "不成立", "note": "src/pages/A.vue 實際不同"},
        {"id": sample[1][0], "n": sample[1][1], "verdict": "成立", "note": "app/A.php ok"}]}
    r = apply_spotcheck(json.loads(json.dumps(base)), sc, sample)
    sc_cases = [("抽查推翻 1 句 ⇒ 獨立欄 1 筆、批次清單不變", r["spotcheck"]["valid"] and len(r["spotcheck_overturned"]) == 1
                 and r["sentences_failed"] == base["sentences_failed"]),
                ("抽查集合不符 ⇒ 作廢", not apply_spotcheck(json.loads(json.dumps(base)), {**sc, "sample": sc["sample"][:1]}, sample)["spotcheck"]["valid"]),
                ("抽查 note 引用正本 ⇒ 作廢", not apply_spotcheck(json.loads(json.dumps(base)), {**sc, "sample": [sc["sample"][0], {**sc["sample"][1], "note": "rag-orchestrator/canon/jgb/A.md"}]}, sample)["spotcheck"]["valid"]),
                ("抽查 verdict 矛盾 ⇒ 作廢", not apply_spotcheck(json.loads(json.dumps(base)), {**sc, "verdict": "CONFIRMED"}, sample)["spotcheck"]["valid"])]
    for name, ok in sc_cases:
        print(("✅ " if ok else "❌ ") + name)
        if not ok:
            bad.append(name)
    rr = apply_redo(json.loads(json.dumps(base)), {"batches": {"B01": {"resend": 1, "replace": 0, "voided": 0}}})
    sc_cases.append(("重做清單帶入每批", rr["batches"][0]["redo"]["resend"] == 1))
    try:
        apply_redo(json.loads(json.dumps(base)), {"batches": {"B99": {}}})
        sc_cases.append(("重做清單批號不符 ⇒ 大聲失敗", False))
    except SystemExit:
        sc_cases.append(("重做清單批號不符 ⇒ 大聲失敗", True))
    for name, ok in sc_cases[-2:]:
        print(("✅ " if ok else "❌ ") + name)
        if not ok:
            bad.append(name)
    n = len(cases) + len(sc_cases)
    print(f"self-test {n - len(bad)}/{n}")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    evdir, man, cj, outp = sys.argv[1:5]
    r = aggregate(evdir, json.load(open(man, encoding="utf-8")), json.load(open(cj, encoding="utf-8")))
    sample = spot_sample(r)
    if "--sample-out" in sys.argv:
        json.dump(sample, open(sys.argv[sys.argv.index("--sample-out") + 1], "w"), ensure_ascii=False)
    if "--redo" in sys.argv:
        apply_redo(r, json.load(open(sys.argv[sys.argv.index("--redo") + 1], encoding="utf-8")))
    if "--spotcheck" in sys.argv:
        r = apply_spotcheck(r, json.load(open(sys.argv[sys.argv.index("--spotcheck") + 1], encoding="utf-8")), sample)
    json.dump(r, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--md" in sys.argv:
        write_md(r, json.load(open(cj, encoding="utf-8")), sys.argv[sys.argv.index("--md") + 1])
    print(f"有效批 {r['valid_batches']}／{len(r['batches'])}；核對細目 {r['fines_checked']}、句 {r['sentences_checked']}；"
          f"全條成立 {r['fines_fully_holding']}；標題不成立 {len(r['titles_failed'])}；句不成立 {len(r['sentences_failed'])}"
          + (f"；抽查推翻 {len(r['spotcheck_overturned'])}（抽查有效 {r['spotcheck']['valid']}）" if "spotcheck" in r else ""))
    for b in r["batches"]:
        if not b["valid"]:
            print("INVALID", b["batch"], b["errors"][:3])
    ok = r["valid_batches"] == len(r["batches"]) and ("spotcheck" not in r or r["spotcheck"]["valid"])
    sys.exit(0 if ok else 1)
