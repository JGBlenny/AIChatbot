"""任務 2.2：`rag-orchestrator/canon/` 與 `.claude/skills/outline-curation/runs/` 的識別碼全掃（D3）。

判準與 hook（`.claude/hooks/outline_gate.py` 判定 4）**同一份 regex**——CI 這一關與 PostToolUse 那一關
必須是同一把尺，否則 hook 沒開的路徑（腳本直接寫檔，不經 Edit/Write 工具）就成盲區。

⚠️ **基線（`KNOWN_FALSE_POSITIVES`）＝目前已在庫、且經逐行查證為誤判的命中**。基線只允許縮小：
新命中一律紅；基線裡的某筆不再重現也紅（表示那檔清乾淨了，該把基線刪掉）。
⛔ 基線不是豁免——每一筆都附證據與待裁事由，交主 session 裁決（見本檔尾註）。
"""
import importlib.util
import os

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.2")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))      # host: <repo>/rag-orchestrator；容器：/app
_REPO = os.path.dirname(_RAG)                                        # host: <repo>；容器：/

SCAN_ROOTS = (
    ("canon", os.path.join(_RAG, "canon")),
    ("runs", os.path.join(_REPO, ".claude", "skills", "outline-curation", "runs")),
)

SKIP_DIRS = {"__pycache__", ".git"}
SKIP_SUFFIXES = (".pyc", ".png", ".jpg", ".pdf", ".zip")

# (掃描根標籤, 根目錄下相對路徑, 類別) → 誤判理由（逐行查證過）
KNOWN_FALSE_POSITIVES = {
    ("canon", "README.md", "plate"):
        "「DSP-012」被 PLATE_RE `[A-Z]{2,3}-?\\d{3,4}` 當成車牌——是 DECISIONS 編號",
    ("runs", "2026-09-06T00-00-00Z/answerability-trial-b1-4.json", "tax_id"):
        "prompt_tokens 之類的 8 位數計數，以及 sha256 十六進位字串中夾著的 8 位數字串",
    ("runs", "2026-09-06T00-00-00Z/answerability-trial-openai-55.json", "tax_id"):
        "rubric sha256 十六進位字串中夾著的 8 位數字串",
    ("runs", "2026-09-06T00-00-00Z/cost.json", "tax_id"):
        "prompt_tokens=11525555（8 位數的 token 計數，不是統一編號）",
    ("runs", "2026-09-06T00-00-00Z/phrasing-map.json", "tax_id"):
        "inputs_sha.helpcenter_dir 的 sha256 十六進位字串中夾著的 8 位數字串",
    ("runs", "2026-09-06T00-00-00Z/structure-proposal.json", "number_label"):
        "「5380 帳單版面自訂」——5380 是 kb id，被 NUMBER_LABEL_RE `\\d{4,}\\s*帳單` 當成帳單號",
}


def _hook_module():
    """載入 hook 模組（repo 根 `.claude/hooks`；容器內掛在 `/.claude`）。"""
    for base in (_REPO, "/"):
        p = os.path.join(base, ".claude", "hooks", "outline_gate.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("outline_gate", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    pytest.skip("outline_gate.py 不在掛載路徑")


def _scan(hook, root):
    """回 (命中集合 {(rel, category)}, 掃到的檔案數)。"""
    hits = set()
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith(SKIP_SUFFIXES):
                continue
            path = os.path.join(dp, f)
            n += 1
            for category, _line in hook.check_identifiers(path):
                hits.add((os.path.relpath(path, root), category))
    return hits, n


# ---------------------------------------------------------------------------
# 正對照：掃描器真的看得見已知病灶
# ---------------------------------------------------------------------------

def test_positive_control_email_and_phone_are_flagged(tmp_path):
    hook = _hook_module()
    p = tmp_path / "prospect.md"
    p.write_text("### 細目 {#prospect/A/x}\n聯絡 a.b@example.com 或撥 0912345678。\n", encoding="utf-8")
    cats = {c for c, _ in hook.check_identifiers(str(p))}
    assert "email" in cats and "phone" in cats, f"塞了 email 與電話卻沒被抓到：{cats}"


def test_positive_control_clean_file_is_clean(tmp_path):
    hook = _hook_module()
    p = tmp_path / "clean.md"
    p.write_text("### 細目 {#prospect/A/x}\n租金怎麼收、合約怎麼簽，都在系統裡完成。\n", encoding="utf-8")
    assert hook.check_identifiers(str(p)) == []


# ---------------------------------------------------------------------------
# 真實目錄全掃
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,root", SCAN_ROOTS, ids=[s[0] for s in SCAN_ROOTS])
def test_real_dirs_have_no_new_identifier_hits(label, root):
    hook = _hook_module()
    if not os.path.isdir(root):
        pytest.skip(f"{label} 目錄不在掛載路徑：{root}")
    hits, n = _scan(hook, root)
    assert n > 0, f"{label} 目錄一個檔都沒掃到（{root}）——這是掃描壞了，不是『乾淨』"
    new = sorted((rel, cat) for rel, cat in hits if (label, rel, cat) not in KNOWN_FALSE_POSITIVES)
    assert not new, (
        f"{label} 出現基線外的識別碼命中：{new}\n"
        f"（掃了 {n} 個檔；若確認是誤判，附逐行證據後才可加進 KNOWN_FALSE_POSITIVES）")


def test_baseline_entries_still_reproduce():
    """基線只准縮小：某筆不再重現＝那個檔清乾淨了，請把該筆從基線刪掉（⛔ 不留殭屍豁免）。"""
    hook = _hook_module()
    seen = set()
    for label, root in SCAN_ROOTS:
        if not os.path.isdir(root):
            pytest.skip(f"{label} 目錄不在掛載路徑：{root}")
        hits, _ = _scan(hook, root)
        seen |= {(label, rel, cat) for rel, cat in hits}
    stale = sorted(set(KNOWN_FALSE_POSITIVES) - seen)
    assert not stale, f"基線這幾筆已不再重現，請刪除：{stale}"


# ---------------------------------------------------------------------------
# 待裁（任務 2.2 交回主 session）
# ---------------------------------------------------------------------------
# 上面六筆基線全部是同三個 regex 的邊界問題，⛔ 本任務不得改 hook：
#   TAX_ID_RE `(?<!\d)\d{8}(?!\d)`      → 前後只擋數字，字母相鄰的十六進位 sha 與 token 計數都會命中
#   PLATE_RE  `[A-Z]{2,3}-?\d{3,4}`     → 「DSP-012」「R2-1234」這類文件編號會命中
#   NUMBER_LABEL_RE `\d{4,}\s*帳單`     → 「<kb id> 帳單…」這類引用會命中
# 影響不只 CI：hook 判定 4 會在 PostToolUse 擋掉這些檔的 Edit/Write。要收斂就得改 hook 的邊界
# （例如統編改成前後不接英數），那是另一個 slice 的事——這裡只把證據留住。
