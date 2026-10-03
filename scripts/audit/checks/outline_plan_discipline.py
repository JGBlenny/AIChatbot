#!/usr/bin/env python3
"""不變量 43：**知識大綱線的計畫與 commit 紀律 ⛔ 靠人記得**（v4：檢查做了什麼，不檢查寫了什麼）。

源起（2026-10-03，業主）：記憶裡的三條規則——「終點指標優先、預期 +0 須業主明示同意」
「寫入驗收全數逐句核對、⛔ 抽樣」「⛔ 自判免驗」——沒有強制力，主 session 一再略過。
業主：「沒有強制 你不用遵守」「省小成本 要損失就一次全損失」。
v1／v2 掃計畫文字被打穿兩輪 ⇒ v3 改驗證據；第三輪反證再找到 4 個 P2（取出時覆寫 base 可重用舊結論、
未 commit 改檢查器＋指紋即轉綠、已審細目改內容不重驗、+0 換寫法繞過）⇒ v4 逐項結構性修補。

## 不變量陳述

W（任何會變成可引用內容的寫入＝全數逐句核對）：錨點 `ANCHOR` 之後，凡 commit 使
   `rag-orchestrator/canon/jgb.json` 中「新增已審」或「已審細目的標題／content_units 有變」，
   該 commit 須附同 commit 內的證據檔（`<SPEC_DIR>/verification/*.json`，`kind: write`）：
   證據細目集合＝上述細目集合；每條 `title`＝"成立"；`sentences` 長度＝本 commit 正本句數、全為 "成立"；
   每條另須帶代理讀到的 `content_sha256` 與 `title_text`，且＝本 commit 正本的值（⛔ 驗完再改內容／標題、⛔ 同句數互換）。
   未 commit 的工作樹同理：工作樹 jgb.json 相對 HEAD 有上述變動 ⇒ 須有 `base`＝HEAD 的 write 證據，否則 audit FAIL。
B（⛔ 自判免驗）：錨點之後碰本線路徑的 commit，訊息須有 `Verified-by: <SPEC_DIR>/verification/<檔>.json CONFIRMED`；
   證據在該 commit 樹裡、`verdict` CONFIRMED、`base`＝第一個父 commit、`claim` 非空；
   有 W 變動的 commit 證據須 `kind: write`。`--extract` 只接受**代理自己寫的 base**＝指定 base（⛔ 重用舊結論）。
   本線路徑＝正本、outline-curation runs、本 spec 目錄、本檢查器、`.githooks/`。別條工作線不受影響。
   ⚠️ 不要用 `git commit --amend`（hook 以 HEAD 為父，amend 時對不上）——改動一律開新 commit。
P（防失焦）：錨點後新增／改動的本 spec 計畫檔（檔名含 plan／plans／planning／計畫／提案／roadmap，.md／.markdown／.txt）須有 `<!-- plan-meta -->`（code fence 內的不算）：
   `endpoint_from: pm 519/533, prospect 116/120`、`endpoint_to:` 同格式同鍵（嚴格格式）；
   鍵必須恰為 pm 與 prospect；任一鍵分子不升（相同或下降）且無一鍵上升＝不推進 ⇒ `consent_zero:` 須為業主原文
   （⛔ 空白、整段是「待…」／TBD／N/A、含「尚未」）。內文不掃。
G（守門自保）：audit 與 hook 一律執行**已 commit 的**檢查器（`git show HEAD:<SELF>`）；
   audit 另驗：工作樹檢查器與 `.githooks/commit-msg` 和 HEAD 相同（⛔ 未 commit 的改動）、
   `check_invariants.sh` 的 `# >>> 不變量 43`～`# <<< 不變量 43` 區塊 sha256＝`BLOCK_SHA`、結尾「稽核記帳」段 sha256＝`TAIL_SHA`、
   全檔只有一處把 FAIL 設成非 1 的值、`CODE_REGRESSIONS=(`／`PRODUCT_BLOCKERS=(` 各一處、沒有 `exit 0`；Makefile 的 audit 目標仍是 `scripts/audit/check_invariants.sh`。
   檔案層另有 Claude Code 權限規則禁止主 session 編輯這三檔（業主 2026-10-03 核可）。
豁免：`LEGACY_EXEMPT`（機制前即存在、未追蹤的 9.11 計畫檔），以 sha256 釘住內容（commit 與 audit 皆驗）。

已知限制（接受、寫進 HANDOFF）：證據的「成立」由代理判、主 session 機械取出；蓄意偽造整份證據擋不住。
hook 可被 `--no-verify`／清空 hooksPath 繞過，由 audit 逐筆事後抓到。

用法（REPO 由檔案位置推得；以 stdin 執行時用環境變數 OPD_REPO）：
  outline_plan_discipline.py                     # audit：G＋W＋B＋P＋工作樹 W／P
  outline_plan_discipline.py --self-test
  outline_plan_discipline.py --commit-msg <檔>    # hook：檢查暫存區
  outline_plan_discipline.py --extract <代理輸出 jsonl> <out.json> --base <sha>
"""
import hashlib
import json
import os
import re
import subprocess
import sys

_f = globals().get("__file__", "")
_here = os.path.dirname(os.path.abspath(_f)) if _f and os.path.isfile(_f) else None
REPO = os.environ.get("OPD_REPO") or (os.path.abspath(os.path.join(_here, "..", "..", "..")) if _here else os.getcwd())
SPEC_DIR = ".kiro/specs/knowledge-outline-and-intent-architecture"
EVIDENCE_DIR = SPEC_DIR + "/verification/"
CANON_JSON = "rag-orchestrator/canon/jgb.json"
ANCHOR = "1a255bb7"
SELF = "scripts/audit/checks/outline_plan_discipline.py"
HOOK = ".githooks/commit-msg"
INVARIANTS = "scripts/audit/check_invariants.sh"
TAIL_SHA = "a01b6f8ac9a04b418dcd0ffe4cae6819492215c6e1c72d95d0bd0185e160476c"
MAKEFILE_AUDIT_RECIPE = "\tscripts/audit/check_invariants.sh"
BLOCK_SHA = "39c2beb79f5b1c40036acbe1efc8fadbb17522fdc94e3359646a6d04773b3372"
OWNED_PREFIXES = (
    "rag-orchestrator/canon/",
    ".claude/skills/outline-curation/runs/",
    SPEC_DIR + "/",
    SELF,
    ".githooks/",
)
PLAN_WORD_RE = re.compile(r"(?i)(?:^|[^a-z])(?:plan|plans|planning|roadmap)(?:[^a-z]|$)|計畫|提案")
LEGACY_EXEMPT = {
    SPEC_DIR + "/inputs/plan-9.11-zero-lookup-navigation-20260924.md":
        "c7938c198ae9500b9eb8e4d3d705eb85a2af7805aa8c65f7cf856319080b408f",
}
TRAILER_RE = re.compile(r"^Verified-by:\s*(?P<p>\S+\.json)\s+CONFIRMED\s*$", re.M)
META_RE = re.compile(r"<!--\s*plan-meta\s*\n(?P<b>.*?)-->", re.S)
ENDPOINT_RE = re.compile(r"^[A-Za-z]+ \d+/\d+(?:, [A-Za-z]+ \d+/\d+)*$")
CONSENT_BAD = re.compile(r"^\s*(?:待\S*|TBD|N/?A)?\s*$|尚未", re.I)


# ---------- 純函式（self-test 對象） ----------
def _fines(jgb) -> dict:
    return {f["id"]: f for c in (jgb or {}).get("coarses", []) for f in c.get("fines", [])}


def _rev(f) -> bool:
    return bool(str(f.get("reviewed_by") or "").strip())


def citable_change_ids(old, new) -> set:
    """新增已審 ∪ 已審細目的標題或 content_units 有變。"""
    o, n = _fines(old), _fines(new)
    out = set()
    for fid, f in n.items():
        if not _rev(f):
            continue
        g = o.get(fid)
        if g is None or not _rev(g) or g.get("title") != f.get("title") or (g.get("content_units") or []) != (f.get("content_units") or []):
            out.add(fid)
    return out


def write_violations(ids: set, new, ev) -> list:
    if not ids:
        return []
    if not isinstance(ev, dict) or ev.get("kind") != "write":
        return [f"W 有 {len(ids)} 條細目新增已審或已審內容變動，證據卻不是 kind=write"]
    nf = _fines(new)
    units = {k: len(v.get("content_units") or []) for k, v in nf.items()}
    errs, fines = [], ev.get("fines") or []
    got = {f.get("id") for f in fines}
    if got != ids:
        errs.append(f"W 證據細目 ≠ 需核細目：少 {sorted(ids - got)[:5]}，多 {sorted(got - ids)[:5]}")
    for f in fines:
        fid = f.get("id")
        if fid not in ids:
            continue
        if f.get("title") != "成立":
            errs.append(f"W {fid} 標題未判成立")
        s = f.get("sentences") or []
        if len(s) != units.get(fid, -1):
            errs.append(f"W {fid} 證據 {len(s)} 句 ≠ 正本 {units.get(fid)} 句（⛔ 抽樣／漏句）")
        if any(x != "成立" for x in s):
            errs.append(f"W {fid} 有句子未判成立")
        g = nf.get(fid, {})
        if f.get("content_sha256") != g.get("content_sha256"):
            errs.append(f"W {fid} 證據 content_sha256 ≠ 本 commit 正本（⛔ 驗完再改內容）")
        if f.get("title_text") != g.get("title"):
            errs.append(f"W {fid} 證據 title_text ≠ 本 commit 正本標題（⛔ 驗完再改標題）")
    return errs


def evidence_violations(ev, parent: str) -> list:
    if not isinstance(ev, dict):
        return ["B 證據檔不是 JSON 物件"]
    errs = []
    if ev.get("verdict") != "CONFIRMED":
        errs.append("B 證據 verdict ≠ CONFIRMED")
    base = str(ev.get("base") or "")
    if len(base) < 7 or not parent.startswith(base):
        errs.append(f"B 證據 base「{base[:12]}」≠ 父 commit {parent[:8]}（⛔ 重用舊證據）")
    if not str(ev.get("claim") or "").strip():
        errs.append("B 證據缺 claim")
    return errs


def trailer_path(msg: str):
    m = TRAILER_RE.search(msg)
    if not m:
        return None
    p = m.group("p")
    return p if p.startswith(EVIDENCE_DIR) and ".." not in p else None


def touches_owned(paths) -> bool:
    return any(p.startswith(OWNED_PREFIXES) for p in paths)


def _pairs(s: str):
    s = (s or "").strip()
    if not ENDPOINT_RE.match(s):
        return None
    return {k: (int(a), int(b)) for k, a, b in re.findall(r"([A-Za-z]+) (\d+)/(\d+)", s)}


def plan_meta_violations(text: str) -> list:
    m = META_RE.search(re.sub(r"```.*?```", "", text, flags=re.S))
    if not m:
        return ["P 缺 `<!-- plan-meta … -->` 區塊（endpoint_from／endpoint_to／consent_zero）"]
    kv = {}
    for line in m.group("b").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip()
    a, b = _pairs(kv.get("endpoint_from")), _pairs(kv.get("endpoint_to"))
    if a is None or b is None:
        return ["P endpoint_from／endpoint_to 須為嚴格格式 `pm 519/533, prospect 116/120`（⛔ 箭頭、括號、說明文字）"]
    if set(a) != {"pm", "prospect"} or set(b) != {"pm", "prospect"}:
        return [f"P endpoint_from／endpoint_to 的鍵須恰為 pm 與 prospect：{sorted(a)} / {sorted(b)}"]
    if not any(b[k][0] > a[k][0] for k in a):
        c = kv.get("consent_zero", "").strip().strip('"「」').strip()
        if CONSENT_BAD.search(c):
            return ["P 預期 +0 卻沒有有效的業主原文 consent_zero（⛔ 空白／待／TBD／N/A）"]
    return []


def is_plan(path: str) -> bool:
    b = os.path.basename(path)
    return path.startswith(SPEC_DIR + "/") and b.lower().endswith((".md", ".markdown", ".txt")) and bool(PLAN_WORD_RE.search(b))


def block_sha(text: str):
    m = re.search(r"^# >>> 不變量 43.*?^# <<< 不變量 43[^\n]*\n", text, re.S | re.M)
    return hashlib.sha256(m.group(0).encode("utf-8")).hexdigest() if m else None


# ---------- git ----------
def _git(*args, check=True) -> str:
    return subprocess.run(["git", "-C", REPO, "-c", "core.quotepath=off", *args],
                          capture_output=True, text=True, check=check).stdout


def _ok(*args) -> bool:
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True).returncode == 0


def _show(rev_path: str):
    r = subprocess.run(["git", "-C", REPO, "show", rev_path], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def _json_text(t):
    try:
        return json.loads(t) if t is not None else None
    except Exception:
        return None


def _sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def check_commit(parent: str, msg: str, files: list, rev: str) -> list:
    """rev＝讀樹用的前綴（'<sha>:' 或暫存區 ':'）。"""
    if not touches_owned(files):
        return []
    p = trailer_path(msg)
    if not p:
        return [f"B 碰本線路徑卻沒有 `Verified-by: {EVIDENCE_DIR}<檔>.json CONFIRMED`"]
    ev = _json_text(_show(f"{rev}{p}"))
    if ev is None:
        return [f"B 證據檔 {p} 不在本 commit 的樹裡或不是合法 JSON"]
    errs = evidence_violations(ev, parent)
    if CANON_JSON in files:
        new, old = _json_text(_show(f"{rev}{CANON_JSON}")), _json_text(_show(f"{parent}:{CANON_JSON}"))
        if new is None:
            errs.append("W 讀不到本 commit 的 jgb.json")
        else:
            errs += write_violations(citable_change_ids(old or {}, new), new, ev)
    for f in files:
        if not is_plan(f):
            continue
        t = _show(f"{rev}{f}")
        if t is None:
            continue
        if f in LEGACY_EXEMPT and _sha256_text(t) == LEGACY_EXEMPT[f]:
            continue
        errs += [f"{f}：{e}" for e in plan_meta_violations(t)]
    return errs


def check_commits() -> list:
    if not _ok("merge-base", "--is-ancestor", ANCHOR, "HEAD"):
        return [f"❌ 錨點 {ANCHOR} 不是 HEAD 的祖先——無法界定範圍，⛔ 不是 PASS"]
    out = []
    for sha in _git("rev-list", f"{ANCHOR}..HEAD").split():
        parent = _git("rev-parse", f"{sha}^1").strip()
        msg = _git("log", "-1", "--format=%B", sha)
        files = [x for x in _git("diff", "--name-only", "--no-renames", "-z", parent, sha).split("\0") if x]
        out += [f"commit {sha[:8]}：{e}" for e in check_commit(parent, msg, files, f"{sha}:")]
    return out


def check_guard() -> list:
    out = []
    if _ok("cat-file", "-e", f"HEAD:{SELF}"):
        for f in (SELF, HOOK):
            if not _ok("diff", "--quiet", "HEAD", "--", f):
                out.append(f"G {f} 有未 commit 的改動（⛔ 先改守門再補驗證）")
    else:
        out.append(f"G（引導期）{SELF} 尚未 commit——commit 後此項轉為嚴格檢查")
    try:
        t = open(os.path.join(REPO, INVARIANTS), encoding="utf-8").read()
    except Exception as e:
        return out + [f"G 讀不到 {INVARIANTS}（{e}）"]
    if block_sha(t) != BLOCK_SHA:
        out.append(f"G {INVARIANTS} 的不變量 43 區塊被改過（sha256 {str(block_sha(t))[:12]} ≠ 釘住值）")
    out += [f"G {INVARIANTS}：{e}" for e in audit_script_violations(t)]
    try:
        mk = open(os.path.join(REPO, "Makefile"), encoding="utf-8").read()
        rec = re.search(r"^audit:[^\n]*\n(\t[^\n]*)", mk, re.M)
        if not rec or rec.group(1) != MAKEFILE_AUDIT_RECIPE:
            out.append("G Makefile 的 audit 目標不再是 scripts/audit/check_invariants.sh")
    except Exception as e:
        out.append(f"G 讀不到 Makefile（{e}）")
    return out


def audit_script_violations(t: str) -> list:
    """防在鎖定區塊外把整份 audit 洗成 PASS。"""
    errs = []
    i = t.find('echo "──────────────── 稽核記帳')
    if i < 0 or hashlib.sha256(t[i:].encode("utf-8")).hexdigest() != TAIL_SHA:
        errs.append("結尾「稽核記帳」段被改過或不存在")
    if len(re.findall(r"(?<![A-Za-z0-9_])FAIL=(?!1\b)", t)) != 1:
        errs.append("FAIL 被設成非 1 的值不只一處（⛔ 中途歸零）")
    for v in ("CODE_REGRESSIONS", "PRODUCT_BLOCKERS"):
        if len(re.findall(rf"(?<![A-Za-z0-9_]){v}=\(", t)) != 1:
            errs.append(f"{v} 被重設不只一處")
    if re.search(r"\bexit\s+0\b", t):
        errs.append("出現 exit 0（⛔ 提早以通過結束）")
    return errs


def check_worktree() -> list:
    out = []
    head_j = _json_text(_show(f"HEAD:{CANON_JSON}"))
    try:
        wt_j = json.load(open(os.path.join(REPO, CANON_JSON), encoding="utf-8"))
    except Exception as e:
        return [f"W 讀不到工作樹 jgb.json（{e}）"]
    ids = citable_change_ids(head_j or {}, wt_j)
    if ids:
        head = _git("rev-parse", "HEAD").strip()
        d = os.path.join(REPO, EVIDENCE_DIR)
        ok = False
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".json"):
                ev = _json_text(open(os.path.join(d, f), encoding="utf-8").read())
                if not evidence_violations(ev, head) and not write_violations(ids, wt_j, ev):
                    ok = True
        if not ok:
            out.append(f"W 工作樹有 {len(ids)} 條細目新增已審或已審內容變動，卻沒有 base＝HEAD 的全數逐句核對證據（⛔ 未驗先過 audit）")
    for root, _, fs in os.walk(os.path.join(REPO, SPEC_DIR)):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), REPO)
            if not is_plan(rel):
                continue
            t = open(os.path.join(REPO, rel), encoding="utf-8").read()
            if rel in LEGACY_EXEMPT and _sha256_text(t) == LEGACY_EXEMPT[rel]:
                continue
            if _show(f"{ANCHOR}:{rel}") == t:
                continue
            out += [f"{rel}：{e}" for e in plan_meta_violations(t)]
    return out


# ---------- 證據取出 ----------
def extract(src: str, dst: str, base: str) -> int:
    last = None
    for line in open(src, encoding="utf-8"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        m = o.get("message", {})
        if m.get("role") != "assistant":
            continue
        cs = m.get("content")
        texts = [cs] if isinstance(cs, str) else []
        for c in ([] if isinstance(cs, str) else cs or []):
            if c.get("type") == "text":
                texts.append(c.get("text", ""))
            elif c.get("type") == "tool_use":  # 代理以 SubagentHandback 交件：結論在 input 字串裡
                texts += [v for v in (c.get("input") or {}).values() if isinstance(v, str)]
        for t in texts:
            for blk in re.findall(r"```json[ \t]*\n(.*?)\n[ \t]*```", t, re.S):  # 結尾須單獨成行（內文字串可含 ```）
                j = _json_text(blk)
                if isinstance(j, dict) and "verdict" in j:
                    last = j
    if last is None:
        print("❌ 代理輸出裡找不到含 verdict 的 ```json 證據區塊"); return 1
    own = str(last.get("base") or "")
    if len(own) < 7 or not (base.startswith(own) or own.startswith(base)):
        print(f"❌ 代理證據的 base「{own[:12]}」≠ 指定 {base[:12]}——⛔ 拿別次驗證的結論充數"); return 1
    last["source_transcript"] = os.path.basename(src)
    json.dump(last, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {dst}: verdict {last.get('verdict')}, kind {last.get('kind')}, fines {len(last.get('fines') or [])}")
    return 0


# ---------- self-test ----------
def self_test() -> int:
    bad = []
    def jg(rev):  # {id: (units, reviewed, title)}
        return {"coarses": [{"fines": [{"id": k, "title": t, "content_units": [f"{k}{i}" for i in range(u)],
                                        "content_sha256": _sha256_text("\n".join(f"{k}{i}" for i in range(u))),
                                        "reviewed_by": "owner" if r else None}
                                       for k, (u, r, t) in rev.items()]}]}
    old = jg({"a": (3, False, "A"), "b": (2, False, "B"), "c": (1, True, "C"), "d": (2, True, "D")})
    def sha(j, fid):
        return _fines(j)[fid]["content_sha256"]
    new = jg({"a": (3, True, "A"), "b": (2, True, "B"), "c": (1, True, "C"), "d": (2, True, "D")})
    ids = citable_change_ids(old, new)
    if ids != {"a", "b"}:
        bad.append(f"citable_change_ids 新增已審 {ids}")
    if citable_change_ids(old, jg({"a": (3, False, "A"), "b": (2, False, "B"), "c": (1, True, "C"), "d": (4, True, "D")})) != {"d"}:
        bad.append("已審細目改內容（句數變）應需重核")
    if citable_change_ids(old, jg({"a": (3, False, "A"), "b": (2, False, "B"), "c": (1, True, "C2"), "d": (2, True, "D")})) != {"c"}:
        bad.append("已審細目改標題應需重核")
    if citable_change_ids(old, jg({"a": (3, False, "A"), "b": (2, False, "B"), "c": (1, False, "C"), "d": (2, True, "D")})):
        bad.append("撤回已審（還原）不應需要 write 證據")
    fa = {"id": "a", "title": "成立", "sentences": ["成立"] * 3, "content_sha256": sha(new, "a"), "title_text": "A"}
    fb = {"id": "b", "title": "成立", "sentences": ["成立"] * 2, "content_sha256": sha(new, "b"), "title_text": "B"}
    full = {"kind": "write", "verdict": "CONFIRMED", "base": "abcdef12", "claim": "x", "fines": [fa, fb]}
    W = [("全數核對", full, 0),
         ("少一條（抽樣）", {**full, "fines": full["fines"][:1]}, 1),
         ("少一句", {**full, "fines": [{**fa, "sentences": ["成立"] * 2}, fb]}, 1),
         ("灌水多一句", {**full, "fines": [{**fa, "sentences": ["成立"] * 4}, fb]}, 1),
         ("一句不成立", {**full, "fines": [{**fa, "sentences": ["成立", "不成立", "成立"]}, fb]}, 1),
         ("標題未判", {**full, "fines": [{k: v for k, v in fa.items() if k != "title"}, fb]}, 1),
         ("驗完改內容（sha 不符）", {**full, "fines": [{**fa, "content_sha256": "0" * 64}, fb]}, 1),
         ("驗完改標題", {**full, "fines": [{**fa, "title_text": "A2"}, fb]}, 1),
         ("同句數互換內容", {**full, "fines": [{**fa, "content_sha256": sha(new, "b")}, {**fb, "content_sha256": sha(new, "a")}]}, 1),
         ("缺 content_sha256", {**full, "fines": [{k: v for k, v in fa.items() if k != "content_sha256"}, fb]}, 1),
         ("多列一條", {**full, "fines": [fa, fb, {"id": "c", "title": "成立", "sentences": ["成立"]}]}, 1),
         ("kind=change", {**full, "kind": "change"}, 1)]
    for name, ev, want in W:
        if (1 if write_violations(ids, new, ev) else 0) != want:
            bad.append(f"W「{name}」")
    split2 = jg({"a": (3, False, "A"), "b": (2, False, "B"), "c": (1, True, "C"), "d": (6, True, "D")})
    if not write_violations(citable_change_ids(old, split2), split2, {"kind": "change", "verdict": "CONFIRMED"}):
        bad.append("分兩次（先縮句標已審、再補句）第二次須重核")
    B = [("正確", {"verdict": "CONFIRMED", "base": "abcdef12", "claim": "x"}, "abcdef1234567890", 0),
         ("REFUTED", {"verdict": "REFUTED", "base": "abcdef12", "claim": "x"}, "abcdef1234567890", 1),
         ("舊證據重用", {"verdict": "CONFIRMED", "base": "1111111", "claim": "x"}, "abcdef1234567890", 1),
         ("base 太短", {"verdict": "CONFIRMED", "base": "abc", "claim": "x"}, "abcdef1234567890", 1),
         ("缺 claim", {"verdict": "CONFIRMED", "base": "abcdef12"}, "abcdef1234567890", 1)]
    for name, ev, par, want in B:
        if (1 if evidence_violations(ev, par) else 0) != want:
            bad.append(f"B「{name}」")
    T = [("正確", f"x\n\nVerified-by: {EVIDENCE_DIR}v.json CONFIRMED\n", True),
         ("非證據目錄", "x\n\nVerified-by: scratch/v.json CONFIRMED\n", False),
         ("路徑穿越", f"x\n\nVerified-by: {EVIDENCE_DIR}../../x.json CONFIRMED\n", False),
         ("not", f"x\n\nVerified-by: {EVIDENCE_DIR}v.json not CONFIRMED\n", False),
         ("小寫", f"x\n\nverified-by: {EVIDENCE_DIR}v.json CONFIRMED\n", False)]
    for name, msg, want in T:
        if (trailer_path(msg) is not None) != want:
            bad.append(f"trailer「{name}」")
    for p, want in (("rag-orchestrator/canon/jgb/中文.md", True), (SELF, True), (HOOK, True),
                    ("rag-orchestrator/services/agent/runtime.py", False), (INVARIANTS, False)):
        if touches_owned([p]) != want:
            bad.append(f"owned「{p}」")
    meta = "<!-- plan-meta\nendpoint_from: pm 519/533, prospect 116/120\nendpoint_to: pm 529/533, prospect 120/120\nconsent_zero:\n-->\n# 計畫\n抽 12 條\n"
    down = meta.replace("pm 529/533, prospect 120/120", "pm 514/533, prospect 116/120")
    zero = meta.replace("pm 529/533, prospect 120/120", "pm 519/533, prospect 116/120")
    P = [("正確（內文不掃）", meta, 0), ("缺區塊", "# 計畫\n", 1),
         ("預期 待定", meta.replace("pm 529/533, prospect 120/120", "待定"), 1),
         ("箭頭寫法", meta.replace("pm 529/533, prospect 120/120", "pm 519→519/533, prospect 116→116/120"), 1),
         ("括號 +0", meta.replace("pm 529/533, prospect 120/120", "pm 519/533（+0）, prospect 116/120"), 1),
         ("鍵不同", meta.replace("pm 529/533, prospect 120/120", "pm 529/533"), 1),
         ("對調順序仍是 +0", zero.replace("endpoint_to: pm 519/533, prospect 116/120", "endpoint_to: prospect 116/120, pm 519/533"), 1),
         ("+0 無同意", zero, 1), ("+0 待確認", zero.replace("consent_zero:", "consent_zero: 待確認"), 1),
         ("+0 TBD", zero.replace("consent_zero:", "consent_zero: TBD"), 1),
         ("+0 n/a", zero.replace("consent_zero:", "consent_zero: n/a"), 1),
         ("+0 有同意", zero.replace("consent_zero:", "consent_zero: 「a」"), 0),
         ("下降無同意", down, 1), ("下降有同意", down.replace("consent_zero:", "consent_zero: 「撤回錯句」"), 0),
         ("假鍵", meta.replace("pm 519/533, prospect 116/120", "x 0/1, y 0/1").replace("pm 529/533, prospect 120/120", "x 1/1, y 1/1"), 1),
         ("少 prospect 鍵", meta.replace(", prospect 116/120", "").replace(", prospect 120/120", ""), 1),
         ("同意含 期待 不誤擋", zero.replace("consent_zero:", "consent_zero: 「我期待先修好」"), 0),
         ("同意含 final 不誤擋", zero.replace("consent_zero:", "consent_zero: 「final 版先停」"), 0),
         ("同意 尚未", zero.replace("consent_zero:", "consent_zero: 「尚未決定」"), 1),
         ("code fence 內的 meta 不算", "```\n" + meta + "```\n", 1)]
    for name, t, want in P:
        if (1 if plan_meta_violations(t) else 0) != want:
            bad.append(f"P「{name}」")
    for n, want in ((SPEC_DIR + "/inputs/plan-9.23-x.md", True), (SPEC_DIR + "/Plan-x.markdown", True),
                    (SPEC_DIR + "/inputs/計畫-9.23.md", True), (SPEC_DIR + "/inputs/9.23-plan.md", True),
                    (SPEC_DIR + "/plan.md", True), (SPEC_DIR + "/計畫9.23.md", True), (SPEC_DIR + "/Plan9.23.md", True),
                    (SPEC_DIR + "/plans-9.md", True), (SPEC_DIR + "/planning-9.md", True), (SPEC_DIR + "/plan-9.txt", True),
                    (SPEC_DIR + "/提案-9.md", True), (SPEC_DIR + "/roadmap-9.md", True),
                    (SPEC_DIR + "/inputs/fix-log-9.22.md", False), (SPEC_DIR + "/explanation.md", False), ("docs/plan-x.md", False)):
        if is_plan(n) != want:
            bad.append(f"is_plan「{n}」")
    good_sh = 'FAIL=0\nCODE_REGRESSIONS=()\nPRODUCT_BLOCKERS=()\nx\nFAIL=1\n'
    for name, t, want in (("正常", good_sh, 0), ("中途歸零", good_sh + "FAIL=0\n", 1),
                          ("重設 CODE_REGRESSIONS", good_sh + "FAIL=1; CODE_REGRESSIONS=()\n", 1),
                          ("exit 0", good_sh + "exit 0\n", 1), ("INV24_FAIL=0 不誤判", good_sh + "INV24_FAIL=0\n", 0)):
        got = [e for e in audit_script_violations(t) if "稽核記帳" not in e]
        if (1 if got else 0) != want:
            bad.append(f"audit 腳本「{name}」")
    hb = json.dumps({"message": {"role": "assistant", "content": [{"type": "tool_use", "name": "SubagentHandback",
                     "input": {"message": "x\n```json\n{\"verdict\": \"CONFIRMED\", \"base\": \"abcdef12\", \"kind\": \"change\", \"claim\": \"c\", \"findings\": [\"N7 ``` fence fixed\"]}\n```"}}]}})
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src, dst = os.path.join(td, "a.jsonl"), os.path.join(td, "e.json")
        open(src, "w").write(hb + "\n")
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            ok = extract(src, dst, "abcdef1234") == 0
            bad_base = extract(src, dst, "1111111") != 0
        if not ok:
            bad.append("extract 讀不到 SubagentHandback 交件")
        if not bad_base:
            bad.append("extract 應拒絕 base 不符")
    blk = "x\n# >>> 不變量 43（a）\necho hi\n# <<< 不變量 43\ny\n"
    if block_sha(blk) is None or block_sha(blk) == block_sha(blk.replace("echo hi", "echo bye")):
        bad.append("block_sha 未能偵測區塊改動")
    try:  # 正對照（真實歷史）：d7c805d9＝9.21 W1-S3 抽樣寫入、無證據 ⇒ 必須抓到
        sha = _git("rev-parse", "d7c805d9").strip()
        par = _git("rev-parse", f"{sha}^1").strip()
        files = [x for x in _git("diff", "--name-only", "--no-renames", "-z", par, sha).split("\0") if x]
        if not check_commit(par, _git("log", "-1", "--format=%B", sha), files, f"{sha}:"):
            bad.append("正對照：d7c805d9 應被抓到卻 PASS")
    except Exception as e:
        bad.append(f"正對照：讀不到 d7c805d9（{e}）")
    if bad:
        print("❌ self-test FAIL：", bad); return 1
    print(f"✅ self-test PASS（W 已審變動 4＋證據 {len(W)}＋分次 1、B {len(B)}、trailer {len(T)}、owned 5、plan-meta {len(P)}、is_plan 15、audit 腳本 5、extract 2、區塊指紋 1、真實歷史正對照 1）")
    return 0


def main(argv) -> int:
    if "--self-test" in argv:
        return self_test()
    if "--extract" in argv:
        i = argv.index("--extract")
        return extract(argv[i + 1], argv[i + 2], argv[argv.index("--base") + 1])
    if "--commit-msg" in argv:
        msg = open(argv[argv.index("--commit-msg") + 1], encoding="utf-8").read()
        try:
            head = _git("rev-parse", "HEAD").strip()
            files = [x for x in _git("diff", "--cached", "--name-only", "--no-renames", "-z").split("\0") if x]
        except Exception as e:
            print(f"❌ 不變量 43：讀不到 HEAD／暫存區（{e}），拒絕 commit"); return 1
        errs = check_commit(head, msg, files, ":")
        if errs:
            print("❌ 不變量 43：拒絕 commit（⛔ 自判免驗／抽樣／未全數核對）："); [print("   ", e) for e in errs]; return 1
        return 0
    guard = check_guard()
    hard = [g for g in guard if not g.startswith("G（引導期）")]
    errs = hard + check_commits() + check_worktree()
    for g in guard:
        if g.startswith("G（引導期）"):
            print("⚠️", g)
    if errs:
        print("❌ FAIL：知識大綱線紀律違規："); [print("   ", e) for e in errs]; return 1
    print(f"✅ PASS（錨點 {ANCHOR} 之後：可引用內容的寫入皆附全數逐句核對證據、本線 commit 皆附同 commit 證據、計畫有 plan-meta；守門未被改動）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
