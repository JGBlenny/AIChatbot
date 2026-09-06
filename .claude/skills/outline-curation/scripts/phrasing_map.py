#!/usr/bin/env python3
"""步 3 phrasing：講法提案與去識別（knowledge-outline-and-intent-architecture 任務 2.2｜design 元件 1／元件 4／D3）。

輸入三種講法來源 → 掛到 `structure-proposal.json` 的細目 → `phrasing-map.json`（StepEnvelope）：
  question_summary  F2 的 21 列 prospect kb 列，`question_summary` 是**關鍵字串**：以空白切成短主題詞，
                    每詞一筆講法，來源 `question_summary:<kb_id>`；掛法＝細目 `merge_of` 含 `tmp:kb:<kb_id>`（⛔ 不算分）。
  helpcenter        幫助中心 HTML 的 `<title>`（缺則 `<h1>`），來源 `helpcenter:<slug>`（slug＝檔名去 `_zh-Hant.html`）。
  koyu              問法正本 `koyu-v2-phrasings.json`，來源 `koyu:<slug>#<n>`；**只取 直接／口語／情境／俗稱**，
                    ⛔ 不取 操作（找按鈕路徑，屬業者操作受眾）與 邊界（＝文章本來就沒寫的延伸問題，掛上去等於承諾沒有的內容）。

helpcenter／koyu 以**字元 bigram Jaccard**（決定性、無模型）對細目 profile 算分，profile＝細目 title
＋該細目 `merge_of` 所含 kb 列的 question_summary 詞；只掛 top-1 且分數 ≥ `--min-score`，否則進
`payload.unassigned[]` 交人審（⛔ 不硬掛、⛔ 不合併）。

⛔ **去識別在任何 agent 呼叫之前、且在任何字元寫進 `--out`／`runs/` 之前執行**（D3）。
原句（未去識別）只落 `--raw-dir`（`.gitignore` 已含 `.claude/skills/outline-curation/raw/`，
以 `git check-ignore -v .claude/skills/outline-curation/raw/x.json` 查證；90 天後由 `raw_purge.py` 依檔名日期刪）。

識別碼 regex **不在本檔複製**：email／電話／LINE id／統編／車牌／編號／金額＋日期一律 import
`.claude/hooks/outline_gate.py` 的同一份（skill 與 hook 必須是同一把尺）。人名／地址／房號戶名／
社區與物件名 hook 沒有（hook 掃的是「檔案裡有沒有」，這四類需要中文語境切詞），在本檔補齊、⛔ 不回頭改 hook。

決定性：同輸入（含 `--frozen-at`）兩次執行逐位元相同；⛔ 全檔無 `datetime.now()`、⛔ 不讀網路、⛔ 不讀 `.env`。
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_VERSION = "0.1.0"


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_env = _load_sibling("_envelope")


def _load_hook():
    """載入 `.claude/hooks/outline_gate.py`（識別碼 regex 的唯一正本）。

    scripts/ 往上四層＝repo 根（容器內 `.claude` 掛在 `/.claude`，四層往上剛好是 `/`）；
    再補一個 `/` 候選，形狀同 `tests/unit/agent/test_canon_parser_req.py::_hook_module`。"""
    up4 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))
    for base in (up4, "/"):
        p = os.path.join(base, ".claude", "hooks", "outline_gate.py")
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location("outline_gate", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    raise RuntimeError("找不到 .claude/hooks/outline_gate.py——識別碼 regex ⛔ 不得在本檔另寫一份")


_hook = _load_hook()


# ---------------------------------------------------------------------------
# 去識別（D3：十類；hook 七類直接 import，四類中文語境類在此補）
# ---------------------------------------------------------------------------

PLACEHOLDER = {
    "person_name": "〈人名〉",
    "address": "〈地址〉",
    "number_label": "〈編號〉",
    "phone": "〈電話〉",
    "email": "〈EMAIL〉",
    "line_id": "〈LINEID〉",
    "tax_id": "〈統編〉",
    "room": "〈房號〉",
    "community": "〈社區名〉",
    "plate": "〈車牌〉",
    "amount_date": "〈金額日期〉",
}

# 人名：常見單姓（封閉表）＋0–3 中文字＋稱謂。
# ⛔ 不用「任意 2–4 中文字＋稱謂」——那會把「請問老師」「我們的老師」整段吃掉（誤殺可查證）。
_SURNAMES = (
    "趙錢孫李周吳鄭王馮陳褚衛蔣沈韓楊朱秦尤許何呂施張孔曹嚴華金魏陶姜"
    "戚謝鄒喻柏水竇章雲蘇潘葛奚范彭郎魯韋昌馬苗鳳花方俞任袁柳酆鮑史唐"
    "費廉岑薛雷賀倪湯滕殷羅畢郝鄔安常樂于時傅皮卞齊康伍余元卜顧孟平黃"
    "和穆蕭尹姚邵湛汪祁毛禹狄米貝明臧計伏成戴談宋茅龐熊紀舒屈項祝董梁"
    "杜阮藍閔席季麻強賈路婁危江童顏郭林刁鍾徐邱駱高夏蔡田樊胡凌霍虞萬"
    "支柯昝管盧莫房繆干解應宗丁宣賁鄧郁單杭洪包諸左石崔吉鈕龔程嵇邢滑裴陸榮翁荀羊"
)
_TITLES = "先生|小姐|太太|女士|老師|經理|專員|主任|董事長|總經理|課長|店長"
PERSON_NAME_RE = re.compile(
    r'[' + _SURNAMES + r'](?:(?!的|和|與|跟|及)[一-鿿]){0,3}(?:' + _TITLES + r')'
)

# 地址：縣市（＋可選 區/鄉/鎮/市）＋ 路|街|巷|弄 ＋ 後續門牌片段。
# ⛔ 不把「縣市＋號」算地址——「新北市…幾號」會誤殺；門牌的判準是有 路／街／巷／弄。
ADDRESS_RE = re.compile(
    r'[一-鿿]{2}[市縣]'
    r'(?:[一-鿿]{1,4}[區鄉鎮市])?'
    r'[一-鿿0-9]{0,10}?[路街巷弄]'
    r'[一-鿿0-9之\-]{0,12}'
)

# 房號戶名：棟／樓／室／號房 ＋ 數字，或「戶名：<中文>」。
# ⛔ 單獨的「數字＋戶」是計數量詞（如「約10戶」＝規模），不是門牌，不在本類；
#    這是刻意的取捨，改成吃 `\d+戶` 會把售前的規模講法整批打掉。
ROOM_RE = re.compile(
    r'(?:[0-9A-Za-z]{1,4}\s*棟)'
    r'|(?:[0-9]{1,3}\s*樓(?:\s*之\s*[0-9]{1,3})?)'
    r'|(?:[0-9A-Za-z]{1,4}\s*室)'
    r'|(?:[0-9A-Za-z]{1,4}\s*號房)'
    r'|(?:戶名\s*[:：]?\s*[一-鿿]{2,4})'
)

# 社區與物件名：<專名>＋社區|大樓|華廈|大廈|花園|山莊。專名以「往回走」取，遇停用字即止（見 _walk_back_sub）。
COMMUNITY_SUFFIX_RE = re.compile(r'(?:社區|大樓|華廈|大廈|花園|山莊)')
# 停用字＝功能詞＋動詞。動詞字（建／創／設…）刻意在內：實測 koyu 有「先建社區」「創建社區」，
# 不擋會把動詞當成專名一起吃掉（量過的誤殺）；代價是「建國社區」這類以動詞字開頭的專名會漏，
# 兩害相權取誤殺低者。⚠️ 以「一類」維護，⛔ 不為單句加字。
_STOP_CHARS = set(
    "的們這那我你他她它是在有和與請謝很就都也不會要可以個些其該本貴整全各同每幾多兩一某任何"
    "棟樓層間戶位為所以及但或又更再從對於把被讓做"
    "建創設增蓋選填找查看改刪開關管報繳綁解"
)

# 合約號／帳單號：hook 的 `\d{4,}\s*(合約|帳單|編號|號)`（數字在前）**外加**標籤在前的寫法，
# 兩者聯集⊇hook，方向只會更嚴（skill 產物永遠不會比 hook 寬）。
LABEL_NUMBER_RE = re.compile(r'(?:合約|帳單)(?:編號|號碼|序號|號)?\s*[:：#＃]?\s*\d{4,}')


def _walk_back_sub(text: str, suffix_re, token: str, min_len: int, max_len: int):
    """從 suffix（如「社區」）往回收專名：最多 max_len 個中文字，遇停用字／非中文即止。

    回 (新字串, 命中次數)。往回走而不用 `[一-鿿]{2,6}社區`，是因為後者在
    「我住在陽光社區」會貪婪吃到「我住在陽光」——含停用字就整段不算，變成漏掉。"""
    out = []
    idx = 0
    hits = 0
    for m in suffix_re.finditer(text):
        start = m.start()
        j = start
        n = 0
        while j > idx and n < max_len:
            ch = text[j - 1]
            if ch in _STOP_CHARS or not ("一" <= ch <= "鿿"):
                break
            j -= 1
            n += 1
        if n < min_len:
            continue
        out.append(text[idx:j])
        out.append(token)
        idx = m.end()
        hits += 1
    out.append(text[idx:])
    return "".join(out), hits


def _sub_count(pattern, token: str, text: str):
    new, n = pattern.subn(token, text)
    return new, n


def _sub_tax_id(text: str):
    """統編＝獨立 8 位數；⛔ 排除像日期的 8 位數（19xx／20xx＋合法月日），與 hook `_looks_like_date8` 同一判準。"""
    hits = 0
    out = []
    last = 0
    for m in _hook.TAX_ID_RE.finditer(text):
        if _hook._looks_like_date8(m.group(0)):
            continue
        out.append(text[last:m.start()])
        out.append(PLACEHOLDER["tax_id"])
        last = m.end()
        hits += 1
    out.append(text[last:])
    return "".join(out), hits


# 套用順序固定（決定性，且避免互相咬字）：email→LINE id→金額+日期→電話→車牌→編號→統編→地址→社區→人名→房號。
def deidentify(text: str):
    """回 (去識別後字串, {類別: 命中數})。⛔ 這是任何字元進 `--out`／`runs/` 前的唯一入口。"""
    counts = {}

    def rec(cat, n):
        if n:
            counts[cat] = counts.get(cat, 0) + n

    text, n = _sub_count(_hook.EMAIL_RE, PLACEHOLDER["email"], text); rec("email", n)
    text, n = _sub_count(_hook.LINE_ID_RE, PLACEHOLDER["line_id"], text); rec("line_id", n)
    text, n = _sub_count(_hook.AMOUNT_DATE_RE, PLACEHOLDER["amount_date"], text); rec("amount_date", n)
    text, n = _sub_count(_hook.PHONE_RE, PLACEHOLDER["phone"], text); rec("phone", n)
    text, n = _sub_count(_hook.PLATE_RE, PLACEHOLDER["plate"], text); rec("plate", n)
    text, n = _sub_count(_hook.NUMBER_LABEL_RE, PLACEHOLDER["number_label"], text); rec("number_label", n)
    text, n = _sub_count(LABEL_NUMBER_RE, PLACEHOLDER["number_label"], text); rec("number_label", n)
    text, n = _sub_tax_id(text); rec("tax_id", n)
    text, n = _sub_count(ADDRESS_RE, PLACEHOLDER["address"], text); rec("address", n)
    text, n = _walk_back_sub(text, COMMUNITY_SUFFIX_RE, PLACEHOLDER["community"], 2, 6); rec("community", n)
    text, n = _sub_count(PERSON_NAME_RE, PLACEHOLDER["person_name"], text); rec("person_name", n)
    text, n = _sub_count(ROOM_RE, PLACEHOLDER["room"], text); rec("room", n)
    return text, counts


_PLACEHOLDER_RE = re.compile("|".join(re.escape(v) for v in PLACEHOLDER.values()))


def is_only_placeholders(text: str) -> bool:
    """去識別後只剩佔位符（＋標點空白）＝這句話沒有講法價值，丟棄。"""
    rest = _PLACEHOLDER_RE.sub("", text)
    rest = re.sub(r'[\s，。、？！：；,.?!:;（）()「」【】\-—_/]+', "", rest)
    return rest == ""


# ---------------------------------------------------------------------------
# 正規化與相似度
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r'\s+')


def norm(text: str) -> str:
    """NFKC ＋ 去掉所有空白（去重與凍結題比對的唯一正規化）。"""
    return _WS_RE.sub("", unicodedata.normalize("NFKC", text))


def bigrams(text: str) -> frozenset:
    s = norm(text).lower()
    if len(s) < 2:
        return frozenset([s]) if s else frozenset()
    return frozenset(s[i:i + 2] for i in range(len(s) - 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    """字元 bigram Jaccard：|A∩B| / |A∪B|。決定性、零依賴、對中文短句夠用（步 3 只做提案，人審才定案）。"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


# ---------------------------------------------------------------------------
# 輸入讀取
# ---------------------------------------------------------------------------

def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_fines(structure_path: str):
    """`structure-proposal.json`（envelope）→ [{id,title,merge_of}]，依 id 升冪（決定性）。"""
    doc = _load_json(structure_path)
    payload = doc["payload"] if "payload" in doc else doc
    syn = payload["synthesis"] if "synthesis" in payload else payload
    fines = [{"id": f["id"], "title": f["title"], "merge_of": list(f.get("merge_of", []))} for f in syn["fines"]]
    return sorted(fines, key=lambda f: f["id"])


def load_kb_terms(kb_rows_path: str):
    """kb 列 → {kb_id: [關鍵詞]}；question_summary 是關鍵字串，以空白切詞、每詞 ≤20 字、≥2 字。"""
    doc = _load_json(kb_rows_path)
    rows = doc["rows"] if isinstance(doc, dict) else doc
    terms = {}
    too_long = 0
    for r in sorted(rows, key=lambda x: x["kb_id"]):
        picked = []
        for t in str(r["question_summary"]).split():
            t = t.strip()
            if len(t) < 2:
                continue
            if len(t) > 20:
                too_long += 1
                continue
            picked.append(t)
        terms[int(r["kb_id"])] = picked
    return terms, too_long


_TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')
HELPCENTER_SUFFIX = "_zh-Hant.html"


def _clean_html_text(raw: str) -> str:
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub("", raw))).strip()


def load_helpcenter(helpcenter_dir: str):
    """扁平目錄下的 `*_zh-Hant.html` → [(slug, 標題)]，依 slug 升冪；回傳同時附檔數。"""
    names = sorted(n for n in os.listdir(helpcenter_dir) if n.endswith(HELPCENTER_SUFFIX))
    out = []
    for n in names:
        with open(os.path.join(helpcenter_dir, n), encoding="utf-8", errors="replace") as f:
            raw = f.read()
        m = _TITLE_RE.search(raw)
        text = _clean_html_text(m.group(1)) if m else ""
        if not text:
            m = _H1_RE.search(raw)
            text = _clean_html_text(m.group(1)) if m else ""
        if not text:
            continue
        out.append((n[:-len(HELPCENTER_SUFFIX)], text))
    return out, len(names)


KOYU_INCLUDE_TYPES = ("直接", "口語", "情境", "俗稱")
KOYU_EXCLUDE_TYPES = ("操作", "邊界")


def load_koyu(koyu_path: str):
    """問法正本 → [(source, q)]，只取 KOYU_INCLUDE_TYPES；回傳同時附被排除筆數（分型別）。"""
    doc = _load_json(koyu_path)
    arts = doc["articles"]
    out = []
    excluded = {}
    for slug in sorted(arts):
        for p in arts[slug].get("phrasings", []):
            t = p.get("type")
            if t not in KOYU_INCLUDE_TYPES:
                excluded[t] = excluded.get(t, 0) + 1
                continue
            out.append((f"koyu:{slug}#{p['n']}", str(p["q"])))
    return out, excluded


def load_frozen_questions(manifest_path: str):
    """`samples-manifest.json` 的各 available set → 凍結題集合（norm 後）。

    set 的 `path` 先對 manifest 所在目錄解析、再對 repo 根解析（真檔是 repo 相對路徑，
    測試用的 tmp manifest 則與樣本檔同目錄）；⛔ 不讀網路。
    收 `q` 鍵的遞迴走訪直接用 hook 的 `_collect_q`（與判定 3 同一份）。"""
    manifest = _load_json(manifest_path)
    base_dirs = [os.path.dirname(os.path.abspath(manifest_path))]
    try:
        base_dirs.append(_env.find_repo_root())
    except RuntimeError:
        pass
    qs = []
    for _, spec in sorted((manifest.get("sets") or {}).items()):
        if not isinstance(spec, dict) or not spec.get("available"):
            continue
        rel = spec.get("path")
        if not rel:
            continue
        full = None
        if os.path.isabs(rel) and os.path.isfile(rel):
            full = rel
        else:
            for b in base_dirs:
                cand = os.path.join(b, rel)
                if os.path.isfile(cand):
                    full = cand
                    break
        if full is None:
            continue
        _hook._collect_q(_load_json(full), qs)
    return {norm(q) for q in qs if q}


def dir_digest(path: str, suffix: str) -> str:
    """目錄摘要＝每個 `<檔名>:<sha256>` 一行、依檔名升冪，再取整體 sha256。"""
    lines = []
    for n in sorted(x for x in os.listdir(path) if x.endswith(suffix)):
        lines.append(f"{n}:{_env.sha256_file(os.path.join(path, n))}")
    return _env.sha256_bytes("\n".join(lines).encode("utf-8"))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

CAP_PER_FINE = 12
DEFAULT_MIN_SCORE = 0.12


def build(structure_path, kb_rows_path, helpcenter_dir, koyu_path, frozen_manifest,
          raw_dir, frozen_at, min_score=DEFAULT_MIN_SCORE, cap=CAP_PER_FINE):
    fines = load_fines(structure_path)
    kb_terms, term_too_long = load_kb_terms(kb_rows_path)
    hc, hc_files = load_helpcenter(helpcenter_dir)
    koyu, koyu_excluded = load_koyu(koyu_path)
    frozen = load_frozen_questions(frozen_manifest)

    # 細目 profile＝title ＋ merge_of 所含 kb 列的 question_summary 詞
    kb_by_fine = {}
    profiles = {}
    for f in fines:
        ids = []
        for ref in f["merge_of"]:
            if ref.startswith("tmp:kb:"):
                try:
                    ids.append(int(ref.split(":")[2]))
                except (IndexError, ValueError):
                    continue
        kb_by_fine[f["id"]] = ids
        prof = f["title"] + " " + " ".join(t for i in ids for t in kb_terms.get(i, []))
        profiles[f["id"]] = bigrams(prof)

    # ---- 候選列舉（原句，⛔ 尚未去識別；只准落 raw/）----
    raw_candidates = []          # {source, text, attach:{kind, fine_ids|None}}
    for kb_id in sorted(kb_terms):
        fids = sorted(fid for fid, ids in kb_by_fine.items() if kb_id in ids)
        for t in kb_terms[kb_id]:
            raw_candidates.append({"source": f"question_summary:{kb_id}", "text": t,
                                   "attach": "by_kb_id", "fine_ids": fids})
    for slug, title in hc:
        raw_candidates.append({"source": f"helpcenter:{slug}", "text": title,
                               "attach": "by_score", "fine_ids": None})
    for src, q in koyu:
        raw_candidates.append({"source": src, "text": q, "attach": "by_score", "fine_ids": None})

    # ---- 篩選：凍結題 → 去識別 → 只剩佔位符 ----
    dropped_frozen = []
    dropped_deid = []
    redaction_counts = {}
    kept = []
    for c in raw_candidates:
        if norm(c["text"]) in frozen:
            dropped_frozen.append(c)
            continue
        clean, counts = deidentify(c["text"])
        for k, v in counts.items():
            redaction_counts[k] = redaction_counts.get(k, 0) + v
        if is_only_placeholders(clean):
            dropped_deid.append(dict(c, deidentified=clean))
            continue
        if norm(clean) in frozen:          # 去識別後才與凍結題相同者同樣不得進索引
            dropped_frozen.append(c)
            continue
        kept.append(dict(c, text=clean))

    # ---- 掛載 ----
    per_fine = {f["id"]: [] for f in fines}
    unassigned = []
    for c in kept:
        if c["attach"] == "by_kb_id":
            for fid in c["fine_ids"]:
                per_fine[fid].append({"text": c["text"], "source": c["source"], "score": 1.0})
            continue
        bg = bigrams(c["text"])
        best_id, best = None, 0.0
        for f in fines:                      # fines 已依 id 升冪 ⇒ 平手取 id 較小者
            s = jaccard(bg, profiles[f["id"]])
            if s > best:
                best, best_id = s, f["id"]
        if best_id is not None and best >= min_score:
            per_fine[best_id].append({"text": c["text"], "source": c["source"], "score": round(best, 4)})
        else:
            unassigned.append({"text": c["text"], "source": c["source"],
                               "best_fine_id": best_id, "score": round(best, 4)})

    # ---- 去重（NFKC＋去空白）與每細目上限 ----
    dropped_dup = 0
    dropped_cap = 0
    phrasings = []
    for fid in sorted(per_fine):
        items = sorted(per_fine[fid], key=lambda p: (-p["score"], p["source"], p["text"]))
        seen = set()
        deduped = []
        for p in items:
            k = norm(p["text"])
            if k in seen:
                dropped_dup += 1
                continue
            seen.add(k)
            deduped.append(p)
        if len(deduped) > cap:
            dropped_cap += len(deduped) - cap
            deduped = deduped[:cap]
        for p in deduped:
            phrasings.append({"fine_id": fid, "text": p["text"], "source": p["source"],
                              "status": "proposed", "score": p["score"]})

    unassigned.sort(key=lambda u: (u["source"], u["text"]))

    payload = {
        "phrasings": phrasings,
        "similar_pairs": [],                       # 步 3 的相似細目由 similar_items.py 填（⛔ 不在此合併）
        "unassigned": unassigned,
        "helpcenter_files": hc_files,
        "redaction_counts": dict(sorted(redaction_counts.items())),
        "counts": {
            "fines": len(fines),
            "candidates_total": len(raw_candidates),
            "candidates_question_summary": sum(1 for c in raw_candidates if c["attach"] == "by_kb_id"),
            "candidates_helpcenter": sum(1 for c in raw_candidates if c["source"].startswith("helpcenter:")),
            "candidates_koyu": sum(1 for c in raw_candidates if c["source"].startswith("koyu:")),
            "assigned": len(phrasings),
            "unassigned": len(unassigned),
            "dropped_frozen": len(dropped_frozen),
            "dropped_deidentified_empty": len(dropped_deid),
            "dropped_duplicate": dropped_dup,
            "dropped_over_cap": dropped_cap,
            "dropped_term_too_long": term_too_long,
            "koyu_excluded_by_type": dict(sorted(koyu_excluded.items())),
            "frozen_questions": len(frozen),
        },
        "params": {"min_score": min_score, "cap_per_fine": cap, "method": "char_bigram_jaccard",
                   "frozen_at": frozen_at},
    }
    raw = {"candidates": raw_candidates, "dropped_frozen": dropped_frozen, "dropped_deidentified": dropped_deid}
    return payload, raw


def write_raw(raw_dir: str, raw: dict) -> None:
    """原句（未去識別）只落 raw/。⛔ 不得指到 runs/（那是要進版控／被掃描的地方）。"""
    ap = os.path.abspath(raw_dir)
    if os.sep + "runs" + os.sep in ap + os.sep or ap.endswith(os.sep + "runs"):
        raise ValueError(f"--raw-dir ⛔ 不得位於 runs/ 之下：{raw_dir}")
    os.makedirs(ap, exist_ok=True)
    _env.write_json(os.path.join(ap, "candidates-raw.json"), raw["candidates"])
    _env.write_json(os.path.join(ap, "dropped-frozen.json"), raw["dropped_frozen"])
    _env.write_json(os.path.join(ap, "dropped-deidentified.json"), raw["dropped_deidentified"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--structure", required=True, help="runs/<run>/structure-proposal.json")
    p.add_argument("--kb-rows", required=True, help="inputs/prospect-kb-rows-*.json")
    p.add_argument("--helpcenter-dir", required=True, help="幫助中心 HTML 扁平目錄（*_zh-Hant.html）")
    p.add_argument("--koyu", required=True, help="koyu-v2-phrasings.json")
    p.add_argument("--frozen-manifest", required=True, help="eval/samples-manifest.json（凍結題）")
    p.add_argument("--raw-dir", required=True, help="原句落地目錄（gitignored；raw/phrasing-<YYYYMMDD>/）")
    p.add_argument("--frozen-at", required=True, help="ISO 時間戳，⛔ 不用 datetime.now()")
    p.add_argument("--out", required=True)
    p.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                   help=f"helpcenter／koyu 掛載門檻（bigram Jaccard），預設 {DEFAULT_MIN_SCORE}")
    p.add_argument("--cap", type=int, default=CAP_PER_FINE, help=f"每細目講法上限，預設 {CAP_PER_FINE}")
    p.add_argument("--skill-version", default=SKILL_VERSION)
    a = p.parse_args()

    payload, raw = build(a.structure, a.kb_rows, a.helpcenter_dir, a.koyu, a.frozen_manifest,
                         a.raw_dir, a.frozen_at, min_score=a.min_score, cap=a.cap)
    write_raw(a.raw_dir, raw)

    inputs_sha = {
        "structure": _env.sha256_file(a.structure),
        "kb_rows": _env.sha256_file(a.kb_rows),
        "koyu": _env.sha256_file(a.koyu),
        "frozen_manifest": _env.sha256_file(a.frozen_manifest),
        "helpcenter_dir": dir_digest(a.helpcenter_dir, HELPCENTER_SUFFIX),
    }
    env = _env.make_envelope(step="phrasing", skill_version=a.skill_version, inputs_sha=inputs_sha,
                             deterministic=True, payload=payload,
                             raw_outputs_path=a.raw_dir)
    schema_path = os.path.join(os.path.dirname(_HERE), "schemas", "phrasing-map.json")
    _env.validate(env, _env.load_schema(schema_path))
    _env.write_json(a.out, env)
    c = payload["counts"]
    print(f"phrasing-map: 細目 {c['fines']}｜候選 {c['candidates_total']}"
          f"（question_summary {c['candidates_question_summary']}／helpcenter {c['candidates_helpcenter']}"
          f"／koyu {c['candidates_koyu']}）｜掛上 {c['assigned']}｜待審 {c['unassigned']}"
          f"｜丟凍結題 {c['dropped_frozen']}｜丟去識別後空 {c['dropped_deidentified_empty']}"
          f"｜丟重複 {c['dropped_duplicate']}｜丟超上限 {c['dropped_over_cap']}")
    print(f"去識別命中：{payload['redaction_counts'] or '無'}｜幫助中心檔數 {payload['helpcenter_files']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
