"""S1-A：R10P sealed artifact validator 的鑑別力驗收。

⚠️ 本檔的重點**不是**「validator 會不會拋例外」，而是
**每一種破壞方式都被判成對應的那一類**——只要有一個變異被誤判成別類，
或被放行，validator 就沒有鑑別力，`R2_RUNTIME_PACKAGING = CONFIRMED` 不成立。

⚠️ 所有變異一律作用在 tmp 複本上，⛔ 絕不觸碰 repo 內的正式 artifact。
"""
import json
import os
import shutil

import pytest

from services import responsibility_artifacts as ra

pytestmark = pytest.mark.unit

ART = ra.DEFAULT_ARTIFACT_DIR


@pytest.fixture()
def sandbox(tmp_path):
    """把正式 artifact 複製到 tmp，供各變異就地破壞。"""
    dst = tmp_path / "artifacts"
    shutil.copytree(ART, dst)
    return str(dst)


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 正對照：沒有它，下面所有 RED 都沒有意義 ──────────────────────────
def test_positive_control_real_artifacts_validate():
    report = ra.validate(ART)
    assert report["reviewed_active"] == 30
    assert report["embedding_count"] == 30
    assert report["embedding_dimension"] == 1536
    assert report["provider_model_id"] == "text-embedding-3-small"
    assert len(report["registry_digest"]) == 64


def test_positive_control_sandbox_copy_validates(sandbox):
    """複本未經破壞時必須 GREEN——否則後面的 RED 可能只是複製壞了。"""
    assert ra.validate(sandbox)["embedding_count"] == 30


# ── 缺檔 ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("rel", ra.REQUIRED_FILES)
def test_missing_artifact_is_red(sandbox, rel):
    os.remove(os.path.join(sandbox, rel))
    with pytest.raises(ra.ArtifactMissing):
        ra.validate(sandbox)


# ── 竄改 ────────────────────────────────────────────────────────────
def test_tampered_registry_is_epoch_mismatch(sandbox):
    """改 registry 一個位元 ⇒ 其 digest 改變 ⇒ derived 綁的 epoch 立刻對不上。"""
    p = os.path.join(sandbox, ra.REGISTRY_FILE)
    reg = _read(p)
    reg["_tamper"] = "x"
    _write(p, reg)
    with pytest.raises(ra.ArtifactEpochMismatch):
        ra.validate(sandbox)


def test_tampered_embeddings_is_digest_mismatch(sandbox):
    p = os.path.join(sandbox, ra.EMBEDDINGS_FILE)
    emb = _read(p)
    emb["entries"][0]["embedding"][0] += 0.5
    _write(p, emb)
    with pytest.raises(ra.ArtifactDigestMismatch):
        ra.validate(sandbox)


# ── epoch 不符 ──────────────────────────────────────────────────────
def test_manifest_epoch_mismatch_is_red(sandbox):
    p = os.path.join(sandbox, ra.MANIFEST_FILE)
    man = _read(p)
    man["registry_v2_digest"] = "0" * 64
    _write(p, man)
    with pytest.raises(ra.ArtifactEpochMismatch):
        ra.validate(sandbox)


def test_embeddings_epoch_mismatch_is_red(sandbox):
    p = os.path.join(sandbox, ra.EMBEDDINGS_FILE)
    emb = _read(p)
    emb["registry_v2_digest"] = "0" * 64
    _write(p, emb)
    with pytest.raises(ra.ArtifactEpochMismatch):
        ra.validate(sandbox)


def test_stale_manifest_without_embeddings_digest_is_red(sandbox):
    """⚠️ 這正是 2026-09-01 在容器 /spec 實際發現的舊 manifest 形狀
    （11 keys、無 embeddings_file_digest）——必須被擋下。"""
    p = os.path.join(sandbox, ra.MANIFEST_FILE)
    man = _read(p)
    man.pop("embeddings_file_digest", None)
    _write(p, man)
    with pytest.raises(ra.ArtifactDigestMismatch):
        ra.validate(sandbox)


# ── population ─────────────────────────────────────────────────────
def test_embedding_count_mismatch_is_red(sandbox):
    p = os.path.join(sandbox, ra.EMBEDDINGS_FILE)
    emb = _read(p)
    emb["entries"] = emb["entries"][:-1]      # 少一筆，但 count 仍寫 30
    _write(p, emb)
    _sync_manifest_digest(sandbox)
    with pytest.raises(ra.ArtifactPopulationMismatch):
        ra.validate(sandbox)


def test_embedding_dimension_mismatch_is_red(sandbox):
    p = os.path.join(sandbox, ra.EMBEDDINGS_FILE)
    emb = _read(p)
    emb["entries"][3]["embedding"] = emb["entries"][3]["embedding"][:100]
    _write(p, emb)
    _sync_manifest_digest(sandbox)
    with pytest.raises(ra.ArtifactPopulationMismatch):
        ra.validate(sandbox)


def test_uncovered_responsibility_is_red(sandbox):
    """數量對得上、但覆蓋的責任不對——⛔ 只比 count 會假綠。"""
    p = os.path.join(sandbox, ra.EMBEDDINGS_FILE)
    emb = _read(p)
    emb["entries"][0]["responsibility_id"] = "R-999"
    _write(p, emb)
    _sync_manifest_digest(sandbox)
    with pytest.raises(ra.ArtifactPopulationMismatch):
        ra.validate(sandbox)


# ── 供應鏈釘選 ──────────────────────────────────────────────────────
def test_pinned_digest_mismatch_is_red(sandbox):
    with pytest.raises(ra.ArtifactDigestMismatch):
        ra.validate(sandbox, expected_registry_digest="f" * 64)


def test_pinned_digest_match_is_green(sandbox):
    real = ra.sha256_file(os.path.join(sandbox, ra.REGISTRY_FILE))
    assert ra.validate(sandbox, expected_registry_digest=real)["embedding_count"] == 30


# ── helper ─────────────────────────────────────────────────────────
def _sync_manifest_digest(sandbox):
    """population 類變異要先讓 digest 一致，否則會提早被 digest 檢查攔下，
    ⚠️ 那樣就測不到 population 這一關（會誤以為有覆蓋，其實沒有）。"""
    p = os.path.join(sandbox, ra.MANIFEST_FILE)
    man = _read(p)
    man["embeddings_file_digest"] = ra.sha256_file(
        os.path.join(sandbox, ra.EMBEDDINGS_FILE))
    _write(p, man)
