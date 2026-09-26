"""unit：Plan 9.14 S1——真實問句進場（轉換器、`--target-user`、客戶文字守門、`--state-file`）。

Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.14-real-questions-into-outline-curation-20260925.md` §2 S1。

守門語義（唯一實作 `rag-orchestrator/tools/text_containment.py`）：輸入帶 `_meta.text_policy="external"` 或位於
`.text-external` 圍欄內 ⇒ 含文字輸出必須落在圍欄內，且圍欄不得在 rag root 下／有 `.git` 祖先；未觸發 ⇒ 不檢查。
每個測試都用 `tmp_path` 下的 `fence/`（放標記）與 `plain/`（不放）——容器內外同一套語義，不需要假 `.git`。

⛔ fixture 只准用合成字串（security-reviewer P2-5）：下方 `_QS` 全為虛構句，⛔ 不得取自任何真實客服紀錄。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))  # host: <repo>/rag-orchestrator；容器：/app
_REPO = os.path.dirname(_RAG)                                                     # host: <repo>；容器：/
_SKILL = os.path.join(_REPO, ".claude", "skills", "outline-curation")
_SCRIPTS = os.path.join(_SKILL, "scripts")
_COVERAGE_MAP = os.path.join(_RAG, "tools", "gapmap", "coverage_map.py")
_TC_SRC = os.path.join(_RAG, "tools", "text_containment.py")
_ENV_OVERRIDE = "OUTLINE_CURATION_TEST_RAG_ROOT"

if not os.path.isdir(_SCRIPTS):  # pragma: no cover
    pytest.skip(f"[env] 找不到 {_SCRIPTS}——容器需掛 repo 根 .claude/", allow_module_level=True)

sys.path.insert(0, _RAG)
from tools.gapmap import coverage_map as cm  # noqa: E402

#: 合成問句（虛構；每句帶一個 ASCII 唯一記號，掃描時連同 JSON 轉義形一併比對）
_QS = [
    ("R001", "SYNQ-a1f3 合成題：月結提醒能不能改成每兩週寄一次", "property_manager"),
    ("R002", "SYNQ-b2e4 合成題：公共區域的燈泡度數要從哪個畫面登錄", "property_manager"),
    ("R003", "SYNQ-c3d5 合成題：參觀樣品屋的預約可以改到隔天嗎", "prospect"),
]

_RUBRIC = "---\nversion: synthetic-test\n---\n合成 rubric 本文（測試用）。\n"

_SHELF_A = """---
coarse: A
title: 測試粗目
scope: 測試用
version: 2026-09-25.test
reviewers: [owner]
language: zh-TW
---
## 測試粗目 {#A-test}
### 細目一 {#jgb/A/one}
- sources: [kb:1]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
第一句。
### 細目二 {#jgb/A/two}
- sources: [kb:2]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
第二句。
### 細目三 {#jgb/A/three}
- sources: [kb:3]
- target_user: [prospect, property_manager]
- business_types: [system_provider]
- instance_applicability: general
第三句。
"""

_EMPTY_SHELF = """---
coarse: {letter}
title: 空架 {letter}
scope: 測試用空架
version: 2026-09-25.test
reviewers: [owner]
language: zh-TW
---
## 空架 {letter} {{#{letter}-empty}}
"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write(path, obj):
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))
    return str(path)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _env(fake_root=None, **extra):
    env = dict(os.environ)
    env.pop(_ENV_OVERRIDE, None)
    if fake_root is not None:
        env["CLAUDE_PROJECT_DIR"] = str(fake_root)
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _run(script, argv, env=None, cwd=None):
    path = script if os.path.isabs(script) else os.path.join(_SCRIPTS, script)
    return subprocess.run([sys.executable, path, *[str(x) for x in argv]], capture_output=True, text=True,
                          env=env if env is not None else _env(), cwd=cwd)


def _layout(tmp_path):
    fence, plain = tmp_path / "fence", tmp_path / "plain"
    fence.mkdir()
    plain.mkdir()
    (fence / ".text-external").write_text("", encoding="utf-8")
    fake_root = tmp_path / "repo"
    (fake_root / ".claude").mkdir(parents=True)
    _write(fake_root / ".claude" / "settings.json", "{}")
    return fence, plain, fake_root


def _library(dir_path):
    os.makedirs(dir_path, exist_ok=True)
    _write(os.path.join(dir_path, "A.md"), _SHELF_A)
    for letter in "BCDEFGHI":
        _write(os.path.join(dir_path, f"{letter}.md"), _EMPTY_SHELF.format(letter=letter))
    return str(dir_path)


def _cells(dirp, *, meta=True, qs=_QS):
    """轉換器同形的 cells／map（`meta=False` ⇒ 不帶 `_meta`，模擬旗標在某環節掉了）。"""
    m = {"text_policy": "external", "source_sha256": "0" * 64, "audience": "property_manager", "n": len(qs)}
    cells = {"cells": [{"id": i, "questions": [q], "policy": "", "module": "", "topic": "", "g0": {"authority": "none"}}
                       for i, q, _a in qs]}
    mp = {"cells": [{"id": i, "cause_state": "NOT_MEASURED", "entry_state": "", "coverage": ""} for i, _q, _a in qs]}
    if meta:
        cells["_meta"] = dict(m)
        mp["_meta"] = dict(m)
    return _write(os.path.join(dirp, "cells.json"), cells), _write(os.path.join(dirp, "map.json"), mp)


def _kb_inputs(plain):
    kb = _write(plain / "kb.json", {"rows": [{"kb_id": 1, "question_summary": "合成標題", "answer": "合成內容。"}]})
    dr = _write(plain / "drafts.json", {"knowledge": [{"question": "合成草稿題", "answer": "合成草稿答。"}]})
    rb = _write(plain / "rubric.md", _RUBRIC)
    return kb, dr, rb


def _args_argv(cells, plain, out):
    kb, dr, rb = _kb_inputs(plain)
    return ["--cells", cells, "--kb-rows", kb, "--drafts", dr, "--rubric", rb,
            "--frozen-at", "2026-09-25T00:00:00Z", "--slim", "--out", out]


def _write_verdicts(outdir, label="no_source", disagree_first=False):
    m = _load(os.path.join(outdir, "manifest.json"))
    for gi, g in enumerate(m["groups"]):
        for slot in (1, 2):
            vs = []
            for ci, cid in enumerate(g["cell_ids"]):
                lab = label
                if disagree_first and gi == 0 and ci == 0 and slot == 2:
                    lab = "deliberate_no"
                vs.append({"cell_id": cid, "label": lab, "fine_id": None, "evidence_unit": None,
                           "confidence": "high", "provisional": True})
            _write(os.path.join(outdir, "verdicts", f"{g['group']}-s{slot}.json"), vs)


def _answerability(canon, path, qs=_QS):
    labels = [{"cell_id": i, "label": "no_source", "fine_id": None, "evidence_unit": None, "confidence": "high",
               "provisional": True, "verdicts": [{"label": "no_source"}, {"label": "no_source"}]} for i, _q, _a in qs]
    return _write(path, {"step": "answerability", "skill_version": "0.1.0",
                         "inputs_sha": {"canon": cm.parse_canon_dir(canon).canon_sha256},
                         "deterministic": False, "raw_outputs_path": "x", "cost": {},
                         "payload": {"labels": labels, "needs_rubric_revision": False}})


def _needles(qs=_QS):
    out = []
    for _i, q, _a in qs:
        out.append(q)
        out.append(json.dumps(q)[1:-1])  # ensure_ascii 轉義形
    return out


def _files_containing(root, needles):
    hits = []
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh:
                    data = fh.read().decode("utf-8", errors="ignore")
            except OSError:
                continue
            if any(n in data for n in needles):
                hits.append(p)
    return hits


# ---------------------------------------------------------------------------
# 七個呼叫點：輸入在 fence/ ⇒ 輸出在 plain/ 非 0（且不寫檔）；輸出在 fence/ ⇒ 成功
# ---------------------------------------------------------------------------

def _site_args(tmp_path, fence, plain, fake_root, out_base):
    cells, _m = _cells(fence)
    out = out_base / "args.json"
    r = _run("answerability_args.py", _args_argv(cells, plain, out), env=_env(fake_root))
    return r, [out], (0,)


def _fenced_args(fence, plain, fake_root):
    cells, _m = _cells(fence)
    args = fence / "args.json"
    r = _run("answerability_args.py", _args_argv(cells, plain, args), env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    return str(args)


def _site_prepare(tmp_path, fence, plain, fake_root, out_base):
    args = _fenced_args(fence, plain, fake_root)
    od = out_base / "judge"
    r = _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", od, "--cells-per-agent", "2"], env=_env(fake_root))
    return r, [od], (0,)


def _site_collect(tmp_path, fence, plain, fake_root, out_base):
    args = _fenced_args(fence, plain, fake_root)
    src = fence / "judge"
    r = _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", src, "--cells-per-agent", "2"], env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    _write_verdicts(str(src), disagree_first=True)
    od = src
    if out_base != fence:
        # 把不含文字的 manifest 與判決搬到圍欄外（prompts/ 含問句，⛔ 不搬）；collect 仍因 args 在圍欄內而觸發
        od = out_base / "judge"
        (od / "prompts").mkdir(parents=True)
        shutil.copyfile(src / "manifest.json", od / "manifest.json")
        shutil.copytree(src / "verdicts", od / "verdicts")
    r = _run("answerability_agents.py", ["collect", "--args", args, "--out-dir", od, "--out", out_base / "res.json"],
             env=_env(fake_root))
    return r, [od / "prompts" / "third.prompt.md", od / "third-cells.json", out_base / "res.json"], (4,)


def _fenced_cm(fence, plain, fake_root):
    canon = _library(plain / "canon")
    cells, mp = _cells(fence)
    ans = _answerability(canon, fence / "answerability.json")
    return canon, cells, mp, ans


def _site_reweigh_cov(tmp_path, fence, plain, fake_root, out_base):
    canon, cells, mp, ans = _fenced_cm(fence, plain, fake_root)
    cov, env_out = out_base / "cm.json", fence / "env.json"
    r = _run("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                            "--coverage-out", cov, "--out", env_out, "--state-file", fence / "state.json"], env=_env(fake_root))
    return r, [cov, env_out], (0,)


def _site_reweigh_out(tmp_path, fence, plain, fake_root, out_base):
    canon, cells, mp, ans = _fenced_cm(fence, plain, fake_root)
    cov, env_out = fence / "cm.json", out_base / "env.json"
    r = _run("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                            "--coverage-out", cov, "--out", env_out, "--state-file", fence / "state.json"], env=_env(fake_root))
    return r, [cov, env_out], (0,)


def _site_coverage_map(tmp_path, fence, plain, fake_root, out_base):
    canon, cells, mp, ans = _fenced_cm(fence, plain, fake_root)
    out = out_base / "cm.json"
    r = _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans, "--out", out],
             env=_env(fake_root))
    return r, [out], (0,)


def _site_worklist(tmp_path, fence, plain, fake_root, out_base):
    canon, cells, mp, ans = _fenced_cm(fence, plain, fake_root)
    cov = fence / "cm.json"
    r = _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans, "--out", cov],
             env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    out = out_base / "wl.json"
    r = _run("source_audit.py", ["worklist", "--coverage", cov, "--out", out, "--authority", "code:synthetic"], env=_env(fake_root))
    return r, [out], (0,)


_SITES = {
    "answerability_args--out": _site_args,
    "prepare--out-dir": _site_prepare,
    "collect--out-dir": _site_collect,
    "reweigh--coverage-out": _site_reweigh_cov,
    "reweigh--out": _site_reweigh_out,
    "coverage_map--out": _site_coverage_map,
    "source_audit-worklist--out": _site_worklist,
}


@pytest.mark.parametrize("site", sorted(_SITES))
def test_call_site_output_outside_fence_is_refused(tmp_path, site):
    fence, plain, fake_root = _layout(tmp_path)
    r, outs, _ok = _SITES[site](tmp_path, fence, plain, fake_root, plain)
    assert r.returncode != 0, (site, r.stdout, r.stderr)
    assert "text-external" in r.stderr or "圍欄" in r.stderr, r.stderr
    for o in outs:
        assert not os.path.exists(o), (site, o)
    assert not _files_containing(str(plain), _needles()), site  # ⛔ 沒有任何合成問句落進 plain/


@pytest.mark.parametrize("site", sorted(_SITES))
def test_call_site_output_inside_fence_succeeds(tmp_path, site):
    fence, plain, fake_root = _layout(tmp_path)
    r, outs, ok = _SITES[site](tmp_path, fence, plain, fake_root, fence)
    assert r.returncode in ok, (site, r.stdout, r.stderr)
    assert os.path.exists(outs[0]), (site, outs[0])


# ---------------------------------------------------------------------------
# 觸發條件的兩條腿、symlink、舊流程
# ---------------------------------------------------------------------------

def test_meta_absent_but_inside_fence_still_triggers(tmp_path):
    fence, plain, fake_root = _layout(tmp_path)
    cells, mp = _cells(fence, meta=False)
    out = plain / "args.json"
    r = _run("answerability_args.py", _args_argv(cells, plain, out), env=_env(fake_root))
    assert r.returncode != 0 and not out.exists(), r.stderr
    # coverage_map 直接 CLI 同理
    canon = _library(plain / "canon")
    ans = _answerability(canon, fence / "answerability.json")
    r = _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                             "--out", plain / "cm.json"], env=_env(fake_root))
    assert r.returncode != 0 and not (plain / "cm.json").exists(), r.stderr


def test_args_with_external_meta_in_plain_dir_blocks_prepare(tmp_path):
    fence, plain, fake_root = _layout(tmp_path)
    fenced = _fenced_args(fence, plain, fake_root)
    doc = _load(fenced)
    assert doc["_meta"] == {"text_policy": "external"}
    args = _write(plain / "args.json", doc)          # 帶旗標、但不在圍欄內
    r = _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", plain / "o"], env=_env(fake_root))
    assert r.returncode != 0 and not (plain / "o").exists(), r.stderr
    # 正對照：同一份 args 拿掉 _meta ⇒ 未觸發、照舊可寫 plain/
    doc.pop("_meta")
    args2 = _write(plain / "args2.json", doc)
    r = _run("answerability_agents.py", ["prepare", "--args", args2, "--out-dir", plain / "o2"], env=_env(fake_root))
    assert r.returncode == 0, r.stderr


def test_symlinks_are_judged_by_realpath(tmp_path):
    fence, plain, fake_root = _layout(tmp_path)
    cells, _m = _cells(fence)
    # (a) 字面上在 fence/ 內、實際指向 plain/ ⇒ 拒
    os.symlink(plain, fence / "escape")
    out_a = fence / "escape" / "args-a.json"
    r = _run("answerability_args.py", _args_argv(cells, plain, out_a), env=_env(fake_root))
    assert r.returncode != 0 and not (plain / "args-a.json").exists(), r.stderr
    # (b) 字面上在 plain/ 內、實際指向 fence/ 內 ⇒ 放行
    (fence / "sub").mkdir()
    os.symlink(fence / "sub", plain / "into")
    out_b = plain / "into" / "args-b.json"
    r = _run("answerability_args.py", _args_argv(cells, plain, out_b), env=_env(fake_root))
    assert r.returncode == 0 and (fence / "sub" / "args-b.json").exists(), r.stderr
    # (c) 輸入是 plain/ 內的 symlink、指向 fence/ 內無 _meta 的檔 ⇒ 依 realpath 仍觸發
    nometa, _ = _cells(fence / "nometa", meta=False)
    os.symlink(nometa, plain / "cells-link.json")
    out_c = plain / "args-c.json"
    r = _run("answerability_args.py", _args_argv(str(plain / "cells-link.json"), plain, out_c), env=_env(fake_root))
    assert r.returncode != 0 and not out_c.exists(), r.stderr


def test_legacy_untriggered_flow_unchecked_and_unchanged(tmp_path):
    """輸入全在 plain/、無 _meta ⇒ 七個呼叫點都不檢查、輸出不多任何鍵。"""
    _fence, plain, fake_root = _layout(tmp_path)
    cells, mp = _cells(plain, meta=False)
    args = plain / "args.json"
    assert _run("answerability_args.py", _args_argv(cells, plain, args), env=_env(fake_root)).returncode == 0
    assert "_meta" not in _load(args) and "candidateFilter" not in _load(args)["inputsSha"]
    od = plain / "judge"
    assert _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", od, "--cells-per-agent", "2"],
                env=_env(fake_root)).returncode == 0
    assert "_meta" not in _load(od / "manifest.json")
    _write_verdicts(str(od), disagree_first=True)
    r = _run("answerability_agents.py", ["collect", "--args", args, "--out-dir", od, "--out", plain / "res.json"], env=_env(fake_root))
    assert r.returncode == 4 and (od / "prompts" / "third.prompt.md").exists(), r.stderr
    canon = _library(plain / "canon")
    ans = _answerability(canon, plain / "answerability.json")
    r = _run("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                            "--coverage-out", plain / "cm1.json", "--out", plain / "env.json"], env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    r = _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                             "--out", plain / "cm.json"], env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    assert "text_policy" not in _load(plain / "cm.json")["_meta"]
    r = _run("source_audit.py", ["worklist", "--coverage", plain / "cm.json", "--out", plain / "wl.json"], env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    assert "_meta" not in _load(plain / "wl.json")


def _expected_manifest(args_path, out_dir, per_agent):
    """獨立重算舊版 manifest（改動前的欄位集合，⛔ 無 `_meta`）的逐位元內容。"""
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("_aa_ref", os.path.join(_SCRIPTS, "answerability_agents.py"))
    aa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aa)
    args = _load(args_path)
    cells = args["cells"]
    by_id = {c["cellId"]: c for c in cells}
    groups = []
    for g in aa.group_cells(cells, per_agent):
        text = aa.build_group_prompt(args, [by_id[c] for c in g["cell_ids"]])
        paths = {str(s): os.path.join(str(out_dir), "prompts", f"{g['group']}-s{s}.prompt.md") for s in (1, 2)}
        groups.append({**g, "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "prompts": paths, "chars": len(text)})
    m = {"step": "answerability", "frozenAt": args["frozenAt"], "rubricSha": args["rubricSha"], "inputsSha": args["inputsSha"],
         "fineIdEnum": args["fineIdEnum"], "cellsPerAgent": per_agent, "groups": groups}
    return json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True)


def test_legacy_prepare_from_arbitrary_cwd_without_project_dir(tmp_path):
    _fence, plain, fake_root = _layout(tmp_path)
    cells, _m = _cells(plain, meta=False)
    args = plain / "args.json"
    assert _run("answerability_args.py", _args_argv(cells, plain, args), env=_env(fake_root)).returncode == 0
    env = _env()
    env.pop("CLAUDE_PROJECT_DIR", None)
    od = plain / "judge"
    r = _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", od, "--cells-per-agent", "2"], env=env, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (od / "manifest.json").read_text(encoding="utf-8") == _expected_manifest(args, od, 2)


def _skill_site_argvs(tmp_path, plain, fake_root):
    """舊流程（plain/、無 _meta）下各 skill 呼叫點可成功執行的 argv（供「模組缺席即失敗」與正對照）。"""
    cells, mp = _cells(plain, meta=False)
    args = plain / "args.json"
    assert _run("answerability_args.py", _args_argv(cells, plain, args), env=_env(fake_root)).returncode == 0
    od = plain / "judge"
    assert _run("answerability_agents.py", ["prepare", "--args", args, "--out-dir", od], env=_env(fake_root)).returncode == 0
    _write_verdicts(str(od))
    canon = _library(plain / "canon")
    ans = _answerability(canon, plain / "answerability.json")
    assert _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                                "--out", plain / "cm.json"], env=_env(fake_root)).returncode == 0
    qs = _write(tmp_path / "src" / "in.json", [{"id": i, "q": q, "audience": a} for i, q, a in _QS])
    return {
        "answerability_args": ("answerability_args.py", _args_argv(cells, plain, plain / "args-x.json")),
        "prepare": ("answerability_agents.py", ["prepare", "--args", args, "--out-dir", plain / "judge-x"]),
        "collect": ("answerability_agents.py", ["collect", "--args", args, "--out-dir", od, "--out", plain / "res-x.json"]),
        "reweigh": ("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                                   "--coverage-out", plain / "cm-x.json", "--out", plain / "env-x.json",
                                   "--state-file", plain / "state.json"]),
        "worklist": ("source_audit.py", ["worklist", "--coverage", plain / "cm.json", "--out", plain / "wl-x.json"]),
        "converter": ("real_questions_to_cells.py", ["--in", qs, "--out-dir", tmp_path / "run-x"]),
    }


@pytest.mark.parametrize("site", ["answerability_args", "prepare", "collect", "reweigh", "worklist", "converter"])
def test_missing_containment_module_fails_every_skill_site(tmp_path, site):
    _fence, plain, fake_root = _layout(tmp_path)
    script, argv = _skill_site_argvs(tmp_path, plain, fake_root)[site]
    empty_rag = tmp_path / "empty-rag"
    (empty_rag / "tools").mkdir(parents=True)
    r = _run(script, argv, env=_env(fake_root, **{_ENV_OVERRIDE: empty_rag}))
    assert r.returncode != 0 and "text_containment.py" in r.stderr, (site, r.stderr)
    # 正對照：同一指令、定位器正常 ⇒ 成功
    r = _run(script, argv, env=_env(fake_root))
    assert r.returncode == 0, (site, r.stderr)


def test_fence_under_rag_root_is_refused(tmp_path):
    _fence, plain, fake_root = _layout(tmp_path)
    fake_rag = tmp_path / "fake-rag"
    (fake_rag / "tools").mkdir(parents=True)
    shutil.copyfile(_TC_SRC, fake_rag / "tools" / "text_containment.py")
    env = _env(fake_root, **{_ENV_OVERRIDE: fake_rag})
    qs = _write(tmp_path / "src" / "in.json", [{"id": i, "q": q, "audience": a} for i, q, a in _QS])
    # 轉換器：--out-dir 在 rag root 下 ⇒ 拒、⛔ 不建標記
    r = _run("real_questions_to_cells.py", ["--in", qs, "--out-dir", fake_rag / "run"], env=env)
    assert r.returncode != 0 and not (fake_rag / "run" / ".text-external").exists(), r.stderr
    # 呼叫點：圍欄（手放標記）在 rag root 下 ⇒ 拒
    inner = fake_rag / "fence"
    inner.mkdir()
    (inner / ".text-external").write_text("", encoding="utf-8")
    cells, _m = _cells(inner)
    r = _run("answerability_args.py", _args_argv(cells, plain, inner / "args.json"), env=env)
    assert r.returncode != 0 and not (inner / "args.json").exists(), r.stderr
    # 正對照：同一個覆寫的 rag root，轉換器與呼叫點改在 rag root 外 ⇒ 放行
    r = _run("real_questions_to_cells.py", ["--in", qs, "--out-dir", tmp_path / "run-ok"], env=env)
    assert r.returncode == 0, r.stderr
    r = _run("answerability_args.py", _args_argv(str(tmp_path / "run-ok" / "cells-prospect.json"), plain,
                                                 tmp_path / "run-ok" / "args.json"), env=env)
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# 轉換器
# ---------------------------------------------------------------------------

def test_converter_shape_marker_and_quiet_stdout(tmp_path):
    src = _write(tmp_path / "src" / "in.json", [{"id": i, "q": q, "audience": a} for i, q, a in _QS])
    run = tmp_path / "run"
    r = _run("real_questions_to_cells.py", ["--in", src, "--out-dir", run])
    assert r.returncode == 0, r.stderr
    assert (run / ".text-external").is_file()
    import hashlib
    sha = hashlib.sha256(open(src, "rb").read()).hexdigest()
    pm = _load(run / "cells-property_manager.json")
    assert pm == {"_meta": {"text_policy": "external", "source_sha256": sha, "audience": "property_manager", "n": 2},
                  "cells": [{"id": "R001", "questions": [_QS[0][1]], "policy": "", "module": "", "topic": "", "g0": {"authority": "none"}},
                            {"id": "R002", "questions": [_QS[1][1]], "policy": "", "module": "", "topic": "", "g0": {"authority": "none"}}]}
    mp = _load(run / "map-prospect.json")
    assert mp["cells"] == [{"id": "R003", "cause_state": "NOT_MEASURED", "entry_state": "", "coverage": ""}]
    assert mp["_meta"]["text_policy"] == "external" and mp["_meta"]["n"] == 1
    assert sorted(os.listdir(run)) == [".text-external", "cells-property_manager.json", "cells-prospect.json",
                                       "map-property_manager.json", "map-prospect.json"]
    assert sha in r.stdout and not any(n in r.stdout + r.stderr for n in _needles())


@pytest.mark.parametrize("git_kind", ["dir", "file"])
def test_converter_refuses_out_dir_with_git_ancestor(tmp_path, git_kind):
    src = _write(tmp_path / "src" / "in.json", [{"id": i, "q": q, "audience": a} for i, q, a in _QS])
    fake_repo = tmp_path / "fakerepo"
    fake_repo.mkdir()
    if git_kind == "dir":
        (fake_repo / ".git").mkdir()
    else:
        (fake_repo / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    run = fake_repo / "sub" / "run"
    r = _run("real_questions_to_cells.py", ["--in", src, "--out-dir", run])
    assert r.returncode != 0 and ".git" in r.stderr, r.stderr
    assert not run.exists()
    # 正對照：同一份輸入、沒有 .git 祖先 ⇒ 建立標記
    r = _run("real_questions_to_cells.py", ["--in", src, "--out-dir", tmp_path / "ok" / "run"])
    assert r.returncode == 0 and (tmp_path / "ok" / "run" / ".text-external").is_file(), r.stderr


def test_converter_rejects_path_like_audience(tmp_path):
    src = _write(tmp_path / "src" / "in.json", [{"id": "R001", "q": "SYNQ-d4 合成題", "audience": "../escape"}])
    r = _run("real_questions_to_cells.py", ["--in", src, "--out-dir", tmp_path / "run"])
    assert r.returncode != 0 and not (tmp_path / "escape").exists() and not (tmp_path / "run").exists()


# ---------------------------------------------------------------------------
# --target-user
# ---------------------------------------------------------------------------

def _canon_args(tmp_path, plain, fake_root, target_user=None, name="args"):
    canon = _library(plain / "canon")
    cells, _m = _cells(plain, meta=False)
    rb = _write(plain / "rubric.md", _RUBRIC)
    out = plain / f"{name}.json"
    argv = ["--cells", cells, "--canon", canon, "--rubric", rb, "--frozen-at", "2026-09-25T00:00:00Z", "--slim", "--out", out]
    if target_user:
        argv += ["--target-user", target_user]
    r = _run("answerability_args.py", argv, env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    return _load(out)


@pytest.mark.parametrize("aud,expected", [
    ("prospect", ["jgb/A/one", "jgb/A/three"]),
    ("property_manager", ["jgb/A/two", "jgb/A/three"]),
])
def test_target_user_filters_candidates_in_original_order(tmp_path, aud, expected):
    _fence, plain, fake_root = _layout(tmp_path)
    a = _canon_args(tmp_path, plain, fake_root, target_user=aud)
    assert a["fineIdEnum"] == expected
    assert a["inputsSha"]["candidateFilter"] == f"target_user={aud}"
    header = a["candidatesBlock"].split("\n", 1)[0]
    assert header == f"## 候選（{len(expected)} 筆，依受眾篩選（target_user={aud}）、原序列舉、未排序）"
    assert "未篩選" not in a["candidatesBlock"]
    for fid in {"jgb/A/one", "jgb/A/two", "jgb/A/three"} - set(expected):
        assert f"### {fid}\n" not in a["candidatesBlock"]


def test_target_user_absent_keeps_all_candidates_and_legacy_header(tmp_path):
    _fence, plain, fake_root = _layout(tmp_path)
    a = _canon_args(tmp_path, plain, fake_root)
    assert a["fineIdEnum"] == ["jgb/A/one", "jgb/A/two", "jgb/A/three"]
    assert "candidateFilter" not in a["inputsSha"]
    assert a["candidatesBlock"].split("\n", 1)[0] == "## 候選（3 筆，原序列舉，未排序未篩選）"


def test_target_user_requires_canon(tmp_path):
    _fence, plain, fake_root = _layout(tmp_path)
    cells, _m = _cells(plain, meta=False)
    r = _run("answerability_args.py", _args_argv(cells, plain, plain / "a.json") + ["--target-user", "prospect"], env=_env(fake_root))
    assert r.returncode == 2 and not (plain / "a.json").exists()


# ---------------------------------------------------------------------------
# --state-file
# ---------------------------------------------------------------------------

_MAIN_STATE = '{\n  "answerability": {"path": "MAIN-LINE"},\n  "reweigh": {"path": "MAIN-LINE"},\n  "source_audit": {"path": "MAIN-LINE"}\n}\n'


def _state_cases(tmp_path, plain):
    cells, mp = _cells(plain, meta=False)
    canon = _library(plain / "canon")
    ans = _answerability(canon, plain / "answerability.json")
    rr = _write(plain / "run-result.json", {"frozenAt": "2026-09-25T00:00:00Z", "inputsSha": {"canon": "x"},
                                            "agentsUsed": 2, "needs_rubric_revision": False,
                                            "labels": [{"cell_id": "R001", "label": "no_source", "fine_id": None,
                                                        "evidence_unit": None, "confidence": "high", "provisional": True}]})
    assert _run(_COVERAGE_MAP, ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                                "--out", plain / "cm.json"]).returncode == 0
    cov_sha = __import__("hashlib").sha256(open(plain / "cm.json", "rb").read()).hexdigest()
    need = [c["cell_id"] for c in _load(plain / "cm.json")["cells"] if c["disposition"] in ("not_available", "owner_decision")]
    audit = _write(plain / "sa.json", {"step": "source_audit", "coverage_map_sha": cov_sha, "authority_sources": ["code:x"],
                                       "records": [{"cell_id": c, "status": "owner_needed", "why_unresolvable": "合成測試"} for c in need]})
    ledger = _write(plain / "ledger.md", "# 合成帳本\n")
    return {
        "answerability": ("finalize_answerability.py", ["--run-result", rr, "--out", plain / "a-env.json", "--journal-dir", plain / "journal"]),
        "reweigh": ("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", ans,
                                   "--coverage-out", plain / "cm2.json", "--out", plain / "r-env.json"]),
        "source_audit": ("source_audit.py", ["check", "--coverage", plain / "cm.json", "--audit", audit, "--ledger", ledger]),
    }


@pytest.mark.parametrize("key", ["answerability", "reweigh", "source_audit"])
def test_state_file_isolates_default_session_state(tmp_path, key):
    _fence, plain, fake_root = _layout(tmp_path)
    session = fake_root / ".claude" / "hooks" / "state" / "outline-gate" / "session.json"
    _write(session, _MAIN_STATE)
    script, argv = _state_cases(tmp_path, plain)[key]
    alt = tmp_path / "run" / "state.json"
    r = _run(script, argv + ["--state-file", alt], env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    assert session.read_bytes() == _MAIN_STATE.encode("utf-8")          # 預設狀態檔逐位元不變
    st = _load(alt)
    assert set(st) == {key} and st[key]["path"] != "MAIN-LINE" and not os.path.isabs(st[key]["path"])
    # 負對照：不給 --state-file ⇒ 照舊寫預設檔
    r = _run(script, argv, env=_env(fake_root))
    assert r.returncode == 0, r.stderr
    assert _load(session)[key]["path"] != "MAIN-LINE"


# ---------------------------------------------------------------------------
# 端到端：合成問句跑完整條線，repo 內 ⛔ 不得出現任何一句
# ---------------------------------------------------------------------------

def _snapshot(roots):
    snap = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                snap[p] = (st.st_mtime_ns, st.st_size)
    return snap


def test_end_to_end_synthetic_questions_never_land_in_repo(tmp_path):
    _fence, plain, fake_root = _layout(tmp_path)
    roots = [_RAG, _SKILL, os.path.join(_REPO, ".claude", "hooks", "state")]
    before = _snapshot(roots)
    env = _env(fake_root)

    src = _write(tmp_path / "src" / "in.json", [{"id": i, "q": q, "audience": a} for i, q, a in _QS])
    run = tmp_path / "run"
    r = _run("real_questions_to_cells.py", ["--in", src, "--out-dir", run], env=env)
    assert r.returncode == 0, r.stderr
    canon = _library(plain / "canon")
    rb = _write(plain / "rubric.md", _RUBRIC)
    aud = "property_manager"
    cells, mp = run / f"cells-{aud}.json", run / f"map-{aud}.json"
    steps = [
        ("answerability_args.py", ["--cells", cells, "--canon", canon, "--target-user", aud, "--rubric", rb,
                                   "--frozen-at", "2026-09-25T00:00:00Z", "--slim", "--out", run / "args.json"], 0),
        ("answerability_agents.py", ["prepare", "--args", run / "args.json", "--out-dir", run / "judge"], 0),
    ]
    for script, argv, rc in steps:
        r = _run(script, argv, env=env)
        assert r.returncode == rc, (script, r.stderr)
    _write_verdicts(str(run / "judge"))
    # 不含文字的寫出點（collect --out／finalize --out／journal／狀態檔）刻意放 plain/：驗證它們真的不含問句
    steps = [
        ("answerability_agents.py", ["collect", "--args", run / "args.json", "--out-dir", run / "judge", "--out", plain / "result.json"], 0),
        ("finalize_answerability.py", ["--run-result", plain / "result.json", "--out", plain / "answerability.json",
                                       "--journal-dir", plain / "journal", "--state-file", plain / "state.json"], 0),
        ("reweigh.py", ["--canon", canon, "--demand", cells, "--map", mp, "--answerability", plain / "answerability.json",
                        "--coverage-out", run / "cm.json", "--out", run / "env.json", "--state-file", plain / "state.json"], 0),
        ("source_audit.py", ["worklist", "--coverage", run / "cm.json", "--out", run / "wl.json", "--authority", "code:synthetic"], 0),
    ]
    for script, argv, rc in steps:
        r = _run(script, argv, env=env)
        assert r.returncode == rc, (script, r.stderr)
        assert not any(n in r.stdout + r.stderr for n in _needles()), script

    # 單一旗標鍵一路帶下去
    assert _load(run / "args.json")["_meta"] == {"text_policy": "external"}
    assert _load(run / "judge" / "manifest.json")["_meta"] == {"text_policy": "external"}
    assert _load(run / "cm.json")["_meta"]["text_policy"] == "external"
    assert _load(run / "wl.json")["_meta"] == {"text_policy": "external"}
    assert _load(run / "args.json")["inputsSha"]["candidateFilter"] == f"target_user={aud}"

    # 正對照：掃描器看得見——圍欄內的 worklist 一定含合成問句
    pm_needles = _needles([q for q in _QS if q[2] == aud])
    assert str(run / "wl.json") in _files_containing(str(run), pm_needles)
    # plain/ 內不含文字的寫出點與狀態檔 ⛔ 不得含任何一句
    assert _files_containing(str(plain), _needles()) == []
    # repo 內每個新寫或改動的檔 ⛔ 不得含任何一句
    after = _snapshot(roots)
    changed = [p for p, v in after.items() if before.get(p) != v]
    leaked = [p for p in changed if _files_containing_one(p, _needles())]
    assert leaked == [], leaked


def _files_containing_one(path, needles):
    try:
        with open(path, "rb") as fh:
            data = fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return False
    return any(n in data for n in needles)
