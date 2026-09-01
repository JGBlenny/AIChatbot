"""R10P sealed artifact 的 runtime 載入與身分驗證（S1-A／R2）。

```text
authority   registry-v2.json           —— responsibility identity 的唯一權威來源
derived     canonical-embeddings.json  —— C2-SCORE 的向量分量（⛔ 無 authority）
            canonical-embeddings-manifest.json —— 上二者的 epoch 綁定憑證
```

⚠️ **一律 fail loud**：缺檔、digest 不符、epoch 不符、數量／維度不符，全部 raise。
⛔ 不得 fallback 到 DB mapping、⛔ 不得以 row id 猜 responsibility、⛔ 不得以零向量帶過。
（業主裁定 2026-09-01：Registry V2 仍是 authority source，⛔ 不改由 DB 供應。）

⚠️ 驗證鏈**錨定在 registry-v2.json 自身的 sha256**，⛔ 不硬編任何期望值——
硬編會在正本合法更新時製造假紅，且讓「誰是正本」變得模糊。
外部若需供應鏈釘選，另用 `expected_registry_digest` 參數，⛔ 不寫死在本模組。
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

#: image 內的正式位置（Dockerfile `COPY . .` 帶入）。⛔ 不得改讀 /spec——
#: 那是 2026-08-30 手動 docker cp 的殘留，2026-09-01 已證實與正本 drift。
DEFAULT_ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "artifacts", "responsibility")

REGISTRY_FILE = "registry-v2.json"
EMBEDDINGS_FILE = os.path.join("derived", "canonical-embeddings.json")
MANIFEST_FILE = os.path.join("derived", "canonical-embeddings-manifest.json")
REQUIRED_FILES = (REGISTRY_FILE, EMBEDDINGS_FILE, MANIFEST_FILE)


class ResponsibilityArtifactError(RuntimeError):
    """artifact 契約違反——⚠️ 一律大聲失敗，⛔ 不得默默降級。"""


class ArtifactMissing(ResponsibilityArtifactError):
    """必要 artifact 不存在。"""


class ArtifactDigestMismatch(ResponsibilityArtifactError):
    """檔案內容與 manifest 記載的 digest 不符（竄改／未同步）。"""


class ArtifactEpochMismatch(ResponsibilityArtifactError):
    """derived artifact 綁的 registry epoch 與實際 registry 不符。"""


class ArtifactPopulationMismatch(ResponsibilityArtifactError):
    """數量／維度／覆蓋率不符。"""


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def validate(artifact_dir: str = DEFAULT_ARTIFACT_DIR,
             expected_registry_digest: Optional[str] = None) -> Dict[str, Any]:
    """驗證整組 artifact，回傳 report。任何一項不符即 raise。

    ⚠️ 檢查順序刻意由「身分」到「內容」：先確認在看哪一份 registry，
    再談 derived 是否綁在同一份上——順序顛倒會讓錯誤訊息指錯地方。
    """
    # ── ① 存在性 ────────────────────────────────────────────────────
    missing = [p for p in REQUIRED_FILES
               if not os.path.isfile(os.path.join(artifact_dir, p))]
    if missing:
        raise ArtifactMissing(
            f"缺少必要 artifact：{missing}（dir={artifact_dir}）"
            f"——⛔ 不得 fallback DB mapping、⛔ 不得以 row id 猜 responsibility")

    reg_path = os.path.join(artifact_dir, REGISTRY_FILE)
    emb_path = os.path.join(artifact_dir, EMBEDDINGS_FILE)
    man_path = os.path.join(artifact_dir, MANIFEST_FILE)

    registry_digest = sha256_file(reg_path)
    embeddings_digest = sha256_file(emb_path)

    # ── ② 供應鏈釘選（可選）────────────────────────────────────────
    if expected_registry_digest and expected_registry_digest != registry_digest:
        raise ArtifactDigestMismatch(
            f"registry digest 與釘選值不符：實際 {registry_digest[:16]}…"
            f" 期望 {expected_registry_digest[:16]}…")

    with open(reg_path, encoding="utf-8") as f:
        registry = json.load(f)
    with open(emb_path, encoding="utf-8") as f:
        embeddings = json.load(f)
    with open(man_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # ── ③ epoch 綁定：derived 必須綁在**這一份** registry 上 ────────
    for name, obj in (("manifest", manifest), ("embeddings", embeddings)):
        bound = obj.get("registry_v2_digest")
        if not bound:
            raise ArtifactEpochMismatch(
                f"{name} 缺 registry_v2_digest——⛔ 無法證明它綁在哪一份 registry 上")
        if bound != registry_digest:
            raise ArtifactEpochMismatch(
                f"{name} 綁的 registry epoch 不符：{bound[:16]}… "
                f"vs 實際 registry {registry_digest[:16]}…"
                f"——⚠️ derived artifact 需重建，⛔ 不得混用")

    # ── ④ 內容 digest：manifest 對 embeddings 的竄改偵測 ────────────
    declared = manifest.get("embeddings_file_digest")
    if not declared:
        raise ArtifactDigestMismatch(
            "manifest 缺 embeddings_file_digest——⛔ 無法偵測 embeddings 竄改"
            "（⚠️ 2026-08-30 之前的舊 manifest 沒有此欄位，屬過期版本）")
    if declared != embeddings_digest:
        raise ArtifactDigestMismatch(
            f"embeddings 內容與 manifest 記載不符：實際 {embeddings_digest[:16]}… "
            f"manifest {declared[:16]}…")

    # ── ⑤ population：數量／維度／覆蓋率 ────────────────────────────
    entries = embeddings.get("entries") or []
    dim = embeddings.get("embedding_dimension")
    active = [r for r in registry.get("responsibilities", [])
              if r.get("status") == "reviewed_active"]
    reg_count = (registry.get("counts") or {}).get("reviewed_active")

    if len(entries) != embeddings.get("count"):
        raise ArtifactPopulationMismatch(
            f"embeddings entries={len(entries)} 與自述 count={embeddings.get('count')} 不符")
    if manifest.get("count") != len(entries):
        raise ArtifactPopulationMismatch(
            f"manifest count={manifest.get('count')} 與 entries={len(entries)} 不符")
    if reg_count is not None and reg_count != len(entries):
        raise ArtifactPopulationMismatch(
            f"registry reviewed_active={reg_count} 與 canonical embeddings={len(entries)} 不符"
            f"——⚠️ 有責任沒有向量，⛔ 不得以 alias vector 或零向量補")
    if len(active) != len(entries):
        raise ArtifactPopulationMismatch(
            f"registry 實際 reviewed_active={len(active)} 與 embeddings={len(entries)} 不符")

    bad_dim = [e["responsibility_id"] for e in entries
               if len(e.get("embedding") or []) != dim]
    if bad_dim:
        raise ArtifactPopulationMismatch(
            f"embedding 維度不符（宣告 {dim}）：{bad_dim[:5]}——⛔ 不得以零向量帶過")

    have = {e.get("responsibility_id") for e in entries}
    uncovered = sorted({r["responsibility_id"] for r in active} - have)
    if uncovered:
        raise ArtifactPopulationMismatch(
            f"下列 reviewed_active responsibility 缺 canonical embedding：{uncovered}")

    return {"artifact_dir": artifact_dir,
            "registry_digest": registry_digest,
            "embeddings_digest": embeddings_digest,
            "manifest_digest": sha256_file(man_path),
            "reviewed_active": len(active),
            "embedding_count": len(entries),
            "embedding_dimension": dim,
            "provider_model_id": manifest.get("provider_model_id"),
            "embedding_contract_version": manifest.get("embedding_contract_version"),
            "registry_sealed_at": registry.get("sealed_at")}


def load(artifact_dir: str = DEFAULT_ARTIFACT_DIR,
         expected_registry_digest: Optional[str] = None
         ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """驗證後回傳 (registry, embeddings, report)。⚠️ 驗證失敗即 raise，⛔ 不回半套。"""
    report = validate(artifact_dir, expected_registry_digest)
    with open(os.path.join(artifact_dir, REGISTRY_FILE), encoding="utf-8") as f:
        registry = json.load(f)
    with open(os.path.join(artifact_dir, EMBEDDINGS_FILE), encoding="utf-8") as f:
        embeddings = json.load(f)
    return registry, embeddings, report
