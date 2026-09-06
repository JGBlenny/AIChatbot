"""unit：`scripts/answerability_args.py`（knowledge-outline-and-intent-architecture 任務 1.4｜design 元件 2）。

驗：`build_judge_prompt` 同輸入兩次逐位元相同；候選順序＝輸入順序、數量 39（真材料）；
白名單投影——cell 塞 `score`／候選塞 `similarity` 必 raise（正對照：真格帶 `per_question`／
`coverage` 等已知系統欄位不 raise 且不進 judgePrompt 文字）；prompt 含 rubric 全文／代表問句／
每個候選 id；`--cell-ids` 子集 ⇒ cells 長度縮小、candidates 仍 39。
"""
import copy
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS_DIR = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SCRIPT = os.path.join(_SCRIPTS_DIR, "answerability_args.py")
_RUBRIC = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas", "answerability-rubric.md")
_CELLS = os.path.join(_REPO, ".kiro", "specs", "presales-grounding-gate", "coverage-map", "map-v2.json")
_KB_ROWS = os.path.join(_REPO, ".kiro", "specs", "knowledge-outline-and-intent-architecture",
                         "inputs", "prospect-kb-rows-20260906.json")
_DRAFTS = os.path.join(_REPO, "scripts", "knowledge-batches", "presales-gapmap-batch2-20260904.json")


def _skip_if_missing():
    for p in (_SCRIPT, _RUBRIC, _CELLS, _KB_ROWS, _DRAFTS):
        if not os.path.isfile(p):
            pytest.skip(f"[env] 找不到 {p}——容器需掛 repo 根 .claude/ 與 .kiro/，宿主直跑本檔")


def _mod():
    sys.path.insert(0, _SCRIPTS_DIR)
    import importlib
    return importlib.import_module("answerability_args")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _run(tmp_path, out_path, cell_ids=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    cmd = [
        sys.executable, _SCRIPT,
        "--cells", _CELLS,
        "--kb-rows", _KB_ROWS,
        "--drafts", _DRAFTS,
        "--rubric", _RUBRIC,
        "--frozen-at", "2026-09-06T00:00:00Z",
        "--out", out_path,
    ]
    if cell_ids:
        cmd += ["--cell-ids", cell_ids]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


# ---------- 真材料：候選數量／順序 ----------

def test_real_materials_39_candidates_kb_then_draft_order(tmp_path):
    _skip_if_missing()
    out = tmp_path / "args.json"
    _run(tmp_path, str(out))
    data = _load(str(out))
    assert len(data["candidates"]) == 39
    assert len(data["fineIdEnum"]) == 39
    assert data["fineIdEnum"] == [c["id"] for c in data["candidates"]]

    kb_ids = [c["id"] for c in data["candidates"] if c["id"].startswith("tmp:kb:")]
    draft_ids = [c["id"] for c in data["candidates"] if c["id"].startswith("tmp:draft:")]
    assert len(kb_ids) == 21
    assert len(draft_ids) == 18
    # kb 依 kb_id 升冪
    kb_nums = [int(i.split(":")[-1]) for i in kb_ids]
    assert kb_nums == sorted(kb_nums)
    # draft 依原序 1..18
    assert draft_ids == [f"tmp:draft:{n}" for n in range(1, 19)]
    # kb 候選排在 draft 候選之前（原序＝輸入順序）
    assert [c["id"] for c in data["candidates"]] == kb_ids + draft_ids


def test_cell_ids_subset_narrows_cells_not_candidates(tmp_path):
    _skip_if_missing()
    out = tmp_path / "args.json"
    _run(tmp_path, str(out), cell_ids="C01,C02")
    data = _load(str(out))
    assert len(data["cells"]) == 2
    assert {c["cellId"] for c in data["cells"]} == {"C01", "C02"}
    assert len(data["candidates"]) == 39


def test_deterministic_byte_identical_cli(tmp_path):
    _skip_if_missing()
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    _run(tmp_path, str(out1), cell_ids="C01,C02")
    _run(tmp_path, str(out2), cell_ids="C01,C02")
    assert out1.read_bytes() == out2.read_bytes()


def test_judge_prompt_contains_rubric_question_and_all_candidate_ids(tmp_path):
    _skip_if_missing()
    out = tmp_path / "args.json"
    _run(tmp_path, str(out), cell_ids="C01")
    data = _load(str(out))
    prompt = data["cells"][0]["judgePrompt"]
    rubric_text = open(_RUBRIC, encoding="utf-8").read().strip()
    assert rubric_text in prompt
    assert data["cells"][0]["question"] in prompt
    for c in data["candidates"]:
        assert c["id"] in prompt


# ---------- build_judge_prompt：白名單投影 ----------

def _real_cell():
    cells = _load(_CELLS)["cells"]
    for c in cells:
        if c["id"] == "C01":
            return copy.deepcopy(c)
    raise AssertionError("C01 not found in map-v2.json fixture")


def _valid_candidates():
    return [
        {"id": "tmp:kb:1", "title": "問句一", "content": "答案一"},
        {"id": "tmp:draft:1", "title": "問句二", "content": "答案二"},
    ]


def test_build_judge_prompt_deterministic(tmp_path):
    _skip_if_missing()
    mod = _mod()
    cell = _real_cell()
    candidates = _valid_candidates()
    rubric = open(_RUBRIC, encoding="utf-8").read()
    p1 = mod.build_judge_prompt(cell, candidates, rubric)
    p2 = mod.build_judge_prompt(cell, candidates, rubric)
    assert p1 == p2


def test_cell_forbidden_field_score_raises(tmp_path):
    """正對照：cell 塞 `score` 鍵——未列在 KNOWN_SYSTEM_FIELDS，必 raise。"""
    _skip_if_missing()
    mod = _mod()
    cell = _real_cell()
    cell["score"] = 0.9
    with pytest.raises(mod.ForbiddenFieldError):
        mod.build_judge_prompt(cell, _valid_candidates(), "rubric")


def test_candidate_forbidden_field_similarity_raises(tmp_path):
    """正對照：候選塞 `similarity` 鍵——不在候選白名單 id/title/content，必 raise。"""
    _skip_if_missing()
    mod = _mod()
    cell = _real_cell()
    candidates = _valid_candidates()
    candidates[0]["similarity"] = 0.83
    with pytest.raises(mod.ForbiddenFieldError):
        mod.build_judge_prompt(cell, candidates, "rubric")


def test_real_cell_known_system_fields_no_raise_and_absent_from_prompt(tmp_path):
    """反例：map-v2 真格帶 per_question／coverage／cause_state／entry_state／g0／rubric 等——
    這些是已知系統欄位，投影允許丟棄、⛔ 不 raise，且不得出現在 judgePrompt 文字。"""
    _skip_if_missing()
    mod = _mod()
    cell = _real_cell()
    assert "per_question" in cell  # 正對照：確認材料真的帶這個欄位（不是巧合通過）
    rubric = open(_RUBRIC, encoding="utf-8").read()
    prompt = mod.build_judge_prompt(cell, _valid_candidates(), rubric)  # 不應 raise
    for forbidden_key in ("per_question", "coverage", "cause_state", "entry_state", "g0", "similarity", "score", "top3"):
        assert forbidden_key not in prompt


def test_kb_row_known_extra_fields_dropped_no_raise():
    """kb 列本身帶 business_types／categories／outline_approved_by／target_user——已知系統欄位。"""
    mod = _mod()
    row = {
        "kb_id": 3584, "question_summary": "問句", "answer": "答案",
        "business_types": ["system_provider"], "categories": ["售前顧問"],
        "outline_approved_by": "owner-20260905", "target_user": ["prospect"],
    }
    c = mod.candidate_from_kb_row(row)
    assert c == {"id": "tmp:kb:3584", "title": "問句", "content": "答案"}


def test_kb_row_unknown_field_raises():
    mod = _mod()
    row = {"kb_id": 1, "question_summary": "q", "answer": "a", "embedding": [0.1, 0.2]}
    with pytest.raises(mod.ForbiddenFieldError):
        mod.candidate_from_kb_row(row)


def test_draft_known_extra_fields_dropped_no_raise():
    mod = _mod()
    draft = {
        "question": "問句", "answer": "答案", "cell": "C02", "facet": "售前顧問",
        "target_user": ["prospect"], "business_types": ["system_provider"],
        "categories": ["售前顧問"], "keywords": ["k"], "instance_applicability": "general",
        "g0": "note",
    }
    c = mod.candidate_from_draft(draft, 3)
    assert c == {"id": "tmp:draft:3", "title": "問句", "content": "答案"}


def test_draft_unknown_field_raises():
    mod = _mod()
    draft = {"question": "q", "answer": "a", "unexpected_field": 1}
    with pytest.raises(mod.ForbiddenFieldError):
        mod.candidate_from_draft(draft, 1)


def test_output_passes_no_llm_and_json_serializable(tmp_path):
    """乾跑材料本身必須是純 JSON、可被 answerability.json schema 之外的檔案序列化——防呆。"""
    _skip_if_missing()
    out = tmp_path / "args.json"
    _run(tmp_path, str(out), cell_ids="C01,C02")
    # 若能被 json.load 讀回即代表 write_json 輸出正確
    data = _load(str(out))
    assert data["step"] == "answerability"
    assert isinstance(data["rubricSha"], str) and len(data["rubricSha"]) == 64
