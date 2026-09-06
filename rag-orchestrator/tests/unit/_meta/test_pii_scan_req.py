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
#
# 2026-09-06：原本六筆（canon/README.md plate、runs/ 五筆 tax_id/number_label）**已全部消滅**——
# 不是加豁免，是把 hook 判定 4 的三支 regex 邊界收斂掉（見 `.claude/hooks/outline_gate.py`
# 的 `TAX_ID_RE`／`PLATE_RE`／`NUMBER_LABEL_RE` 註解，回歸鎖在 `test_outline_gate_req.py`
# 的「判定 4 誤判收斂」節）。基線因此清空。
# ⚠️ 空 dict ⛔ 不代表這關會自動綠：`test_real_dirs_have_no_new_identifier_hits` 現在對
# 任何一筆命中都紅，`test_baseline_entries_still_reproduce` 的正對照在
# `test_positive_control_email_and_phone_are_flagged`（塞 email／電話必被抓）。
KNOWN_FALSE_POSITIVES = {}


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
# 已結案（任務 2.2 留下的三筆待裁，2026-09-06 收斂）
# ---------------------------------------------------------------------------
# 原六筆基線全部是同三支 regex 的邊界問題，已在 hook 側修掉（⛔ 不是在 CI 側加豁免）：
#   TAX_ID_RE       前後只擋數字 → 改成前後不接**英數**，另在 check_identifiers 排除
#                   `_looks_like_date8` 與計數欄位裸數值（NUMERIC_FIELD_KEY_RE）
#   PLATE_RE        `[A-Z]{2,3}-?\d{3,4}` → 只收真車牌式樣（2–3 字母＋4 數字／4 數字＋2 字母），
#                   3 字母＋3 數字（`DSP-012`）不再命中
#   NUMBER_LABEL_RE `\d{4,}\s*(合約|帳單|編號|號)` → 標籤在前，或 ≥6 位數字**緊貼**標籤
# 影響面同時涵蓋 hook 判定 4 的 PostToolUse 擋寫與本檔 CI 全掃（同一把尺）。
