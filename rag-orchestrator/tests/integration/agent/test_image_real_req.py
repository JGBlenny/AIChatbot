"""integration（真線路）：`/mcp` 照片進場對**真 OpenAI Vision** 跑一輪（W8 (2)）。

⛔ **預設不跑**：`RUN_REAL_OPENAI=1` 才跑（沒設 ⇒ `[gate]` skip）。它會真的花錢。

⚠️ **只有辨識是真的**：
  - 抓檔那一段以本檔自己的入口餵 bytes（`_image_fetch_one` 替身讀本機檔）——
    素材不進 repo、⛔ 不需要 relay、⛔ 不對外連線抓檔；
  - 縮圖（`downscale_image`：≤1024px、去 EXIF）與分類封閉映射走**產線同一支**；
  - 分類樹用本檔的固定樹（這台機器沒有真 JGB API），⛔ 不從文件補值。

素材＝六張照片（`IMAGE_TEST_PHOTOS_DIR`，預設 scratchpad 的 `photos/`）：
`leak`／`breaker`／`lock`／`mold` 各應辨識出損壞、`plain` 應「看不出損壞」、
`two_damages` 應出一張卡（低信心時附候選）。

模型：`gpt-4o` 與 `gpt-5-mini` **各跑一輪並排**（表格印在 stdout 供人核）。
費用上限＝12 次辨識（Plan §6 預算），實際 token 由 log 觀察。
"""
from __future__ import annotations

import os

import pytest

from services.agent import image_fetch
from services.agent import mcp_facade as F

pytestmark = pytest.mark.integration

_REQ = "agentic-mcp-orchestration:R10"

_DEFAULT_PHOTOS = (
    "/private/tmp/claude-501/-Users-chenqinghuang-dev-work-AIChatbot/"
    "ca06740e-4c34-4999-985f-2b6922de5436/scratchpad/photos"
)

#: 固定分類樹（形狀＝`JGBSystemAPI.get_repair_categories` 的 `data`）。
#: ⚠️ 名稱是 JGB 既有大類的**近似值**，僅供真線路觀察分類是否落在封閉值域內；
#: ⛔ 不當成 jgb2 正本（真值以 API 為準）。
_TREE = [
    {"id": 1, "name": "水電類", "items": [
        {"id": 11, "name": "漏水", "broken_reasons": []},
        {"id": 12, "name": "電力", "broken_reasons": []},
    ]},
    {"id": 2, "name": "門窗類", "items": [{"id": 21, "name": "門鎖", "broken_reasons": []}]},
    {"id": 3, "name": "土木類", "items": [{"id": 31, "name": "牆面", "broken_reasons": []}]},
    {"id": 4, "name": "設備類", "items": []},
    {"id": 5, "name": "其他", "items": []},
]

_PHOTOS = ("leak", "breaker", "lock", "plain", "mold", "two_damages")
_MODELS = ("gpt-4o", "gpt-5-mini")


def _photos_dir() -> str:
    return os.getenv("IMAGE_TEST_PHOTOS_DIR", _DEFAULT_PHOTOS)


@pytest.mark.req(_REQ)
async def test_real_vision_on_six_photos_across_two_models(monkeypatch):
    if os.getenv("RUN_REAL_OPENAI") != "1":
        pytest.skip("[gate] 需真實 OpenAI（RUN_REAL_OPENAI=1）")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("[env] 缺 OPENAI_API_KEY")
    photos = _photos_dir()
    missing = [n for n in _PHOTOS if not os.path.exists(os.path.join(photos, f"{n}.jpg"))]
    assert not missing, f"素材缺檔：{missing}（目錄 {photos}）"

    def _install_fetcher(name: str):
        path = os.path.join(photos, f"{name}.jpg")

        async def _fetch(url, *, timeout_s):
            with open(path, "rb") as fh:
                return image_fetch.FetchedImage(data=fh.read(), content_type="image/jpeg")

        monkeypatch.setattr(F, "_image_fetch_one", _fetch)

    rows = []
    for model in _MODELS:
        monkeypatch.setenv("IMAGE_RECOGNITION_MODEL", model)
        for name in _PHOTOS:
            _install_fetcher(name)
            turn, elapsed = await F.prepare_image_turn(
                ["https://relay.jgbsmart.com/real/%s.jpg" % name],
                category_tree=_TREE, budget_s=60.0,
            )
            rows.append({
                "model": model, "photo": name, "status": turn.status,
                "category": turn.suggested_category,
                "emergency": turn.suggested_emergency,
                "candidates": turn.candidates,
                "no_damage": "看不出損壞" in turn.facts,
                "elapsed_s": round(elapsed, 2),
            })

    print("\n=== W8 (2) 真線路並排（辨識 %d 次）===" % len(rows))
    for row in rows:
        print(
            "%-10s %-12s %-8s cat=%-6s emg=%-4s cand=%-14s no_damage=%s %.2fs"
            % (row["model"], row["photo"], row["status"], row["category"],
               row["emergency"], ",".join(row["candidates"]) or "-",
               row["no_damage"], row["elapsed_s"])
        )

    assert len(rows) == len(_MODELS) * len(_PHOTOS) <= 12   # 費用上限

    for row in rows:
        # 每一輪都要跑完（⛔ 沒有靜默降級）
        assert row["status"] in ("ok", "partial"), row
        # 分類只能是封閉值域內的名字（或缺值）
        tree_names = {n["name"] for n in _TREE} | {
            i["name"] for n in _TREE for i in n["items"]
        }
        assert row["category"] is None or row["category"] in tree_names, row
        assert row["emergency"] in (None, 1, 2), row
        assert all(c in tree_names for c in row["candidates"]), row

    by_photo = {(r["model"], r["photo"]): r for r in rows}
    for model in _MODELS:
        # `plain`＝非損壞照片：應該說「看不出損壞」
        assert by_photo[(model, "plain")]["no_damage"] is True, by_photo[(model, "plain")]
        # 正對照組：四張損壞照至少有三張被判為損壞（單張模型判讀有雜訊）
        damaged = sum(
            0 if by_photo[(model, n)]["no_damage"] else 1
            for n in ("leak", "breaker", "lock", "mold")
        )
        assert damaged >= 3, f"{model}: 四張損壞照只判出 {damaged} 張"
