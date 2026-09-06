"""大綱人審 dump（spec agentic-mcp-orchestration・任務 3.5）。

**組裝＝程式，⛔ 無 LLM**——本檔只呼叫 `services/agent/outline.py:
build_prospect_outline`（3.2 已定案的決定性組裝）取得 `OutlineDoc`，
再對每個 section 的 `source_ids` 補查逐列後設資料（`question_summary`／
`categories`／`target_user`／`business_types`／`outline_approved_by`／
`generation_metadata`），渲染成一份可人審的 markdown。

## 用法
```
docker compose -f docker-compose.prod.yml run --rm --no-deps -w /app \\
  -e PYTHONPATH=/app --entrypoint python3 rag-orchestrator \\
  tools/agent_outline_dump.py --out .kiro/specs/agentic-mcp-orchestration/eval/outline-<date>.md
```
只讀：全程只 `SELECT`，⛔ 不寫 `knowledge_base`（取消 `outline_approved_by`
標記由主 session 在業主人審後另案以 SQL 執行，需授權）。

## 「疑似講法列」判準（tasks.md 3.5：31 筆逐一判 `kind ∈ {topic, alias,
unknown}`）——**判準即程式常數，執行時原樣印在檔尾**，⛔ 不藏在 docstring：

1. **marker**：`generation_metadata` 命中 `_ALIAS_METADATA_MARKER_KEYS`
   任一鍵且值為真（例：`entry_alias`、`retrieval_representation_proposal`）。
   ⚠️ 2026-09-05 實查：目前 31 筆皆無此鍵——判準保留給未來標記用，
   ⛔ 不代表「查無此鍵＝判準寫錯」，是現況尚未有人這樣標。
2. **batch_file**：`question_summary` 命中
   `scripts/knowledge-batches/presales-phrasing-batch-20260904.json`
   的 `knowledge[].question` 集合（該批次 6 筆講法列，5375 已刪，
   5376–5380 現存於池內）。
3. **duplicate_answer**：`answer` 與池內另一筆逐字相同，或前綴 ≥90%
   字元相同（`_prefix_similarity`）——「一種講法一筆」錨點常見特徵是
   `answer` 抄自來源列全文。

三者任一命中 ⇒ `kind="alias"`。三者皆未命中且 `categories` 為空
（`NULL`／`{}`，見 3335–3358 這批舊列——無 `categories`／`target_user`，
不落在六大模組或四類非模組小節、只落兜底桶）⇒ `kind="unknown"`——
無法從既有欄位判斷它是主題頁還是缺分類的講法列，留人審裁定。
其餘（有 `categories`、三判準皆未命中）⇒ `kind="topic"`。

## 決定性
同一批**內容已審**列（判準見 `services/agent/canon/review_state.py:
content_reviewed_predicate`；⚠️ 2026-09-07 起 ⛔ 不再是 `IS NOT NULL`）
+ 同一份講法批次檔 ⇒ 同一份
`sha256`（`OutlineDoc.sha256` 直接沿用 3.2 的組裝雜湊，未另外摻入 dump
產出時間）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.agent.canon.review_state import COLUMN  # noqa: E402
from services.agent.mcp_facade import LazyPsycopg2Pool  # noqa: E402
from services.agent.outline import OutlineDoc, build_prospect_outline  # noqa: E402

#: 講法批次檔（brief 指名的來源；`question` 欄位＝ import 時寫入的
#: `question_summary` 逐字值，見 `presales-phrasing-batch-20260904.rollback.sql`
#: 用同一組字串做 rollback 比對，兩者互證）。
#:
#: ⚠️ **此檔在 repo 根目錄 `scripts/knowledge-batches/`，不在
#: `rag-orchestrator/` 底下**——`docker-compose.prod.yml` 的 build context
#: 只有 `rag-orchestrator/`，image 內看不到它。容器內跑本工具時必須把它
#: mount 進去（或改用 `--batch-file` 指到掛載路徑），否則判準②會**靜默**
#: 用空集合，把講法批次列誤判成 `topic`——2026-09-05 實跑撞過：5378–5380
#: 三筆因此漏標，改用「mount + 找不到就報錯」後才正確全數判 `alias`
#: （見 `AGENT_OUTLINE_DUMP_BATCH_FILE_REQUIRED`：預設 required=True，
#: 找不到即中止，⛔ 不靜默略過）。
PHRASING_BATCH_FILE_DEFAULT = (
    _REPO_ROOT.parent / "scripts" / "knowledge-batches" / "presales-phrasing-batch-20260904.json"
)

#: `generation_metadata` 講法列標記鍵（見檔頭判準①）。
_ALIAS_METADATA_MARKER_KEYS: tuple[str, ...] = (
    "entry_alias",
    "retrieval_representation_proposal",
)

#: 前綴相似度門檻（判準③）。
_PREFIX_SIMILARITY_THRESHOLD = 0.9

#: 取消標記建議 SQL 樣板（只印，⛔ 本檔不執行）。
#: 欄位名由 `review_state.COLUMN` 組出——⛔ 不得在本檔寫死字面（不變量 32）。
_UNMARK_SQL_TEMPLATE = (
    f"UPDATE knowledge_base SET {COLUMN}=NULL, outline_approved_at=NULL "
    "WHERE id IN ({ids});"
)


@dataclass
class RowMeta:
    id: int
    question_summary: str
    answer: str
    categories: Optional[list]
    target_user: Optional[list]
    business_types: Optional[list]
    outline_approved_by: Optional[str]
    generation_metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# DB 讀取（只讀）
# ---------------------------------------------------------------------------


def fetch_row_meta(db_pool, ids: list[int]) -> dict[int, RowMeta]:
    """依 id 清單補查逐列後設資料。⛔ 只 SELECT。"""
    if not ids:
        return {}
    sql = (
        "SELECT id, question_summary, answer, categories, target_user, "
        f"business_types, {COLUMN}, generation_metadata "
        "FROM knowledge_base WHERE id = ANY(%s) ORDER BY id"
    )
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, [ids])
        rows = cursor.fetchall()
        cursor.close()
    finally:
        db_pool.putconn(conn)
    out: dict[int, RowMeta] = {}
    for row_id, qs, answer, categories, target_user, business_types, approved_by, meta in rows:
        out[row_id] = RowMeta(
            id=row_id,
            question_summary=qs or "",
            answer=answer or "",
            categories=list(categories) if categories else None,
            target_user=list(target_user) if target_user else None,
            business_types=list(business_types) if business_types else None,
            outline_approved_by=approved_by,
            generation_metadata=dict(meta) if meta else {},
        )
    return out


class BatchFileMissing(Exception):
    """判準②的講法批次檔找不到——⛔ 不靜默降級為空集合（見檔頭〈警告〉）。"""


def load_batch_question_summaries(batch_path: Path, *, required: bool = True) -> set[str]:
    """讀講法批次檔的 `knowledge[].question` 集合。

    `required=True`（預設）且檔不存在 ⇒ 丟 `BatchFileMissing`——判準②失效會讓
    講法列誤判為 `topic`（比誤判為 `alias`更危險：漏掉的講法列會被人審誤以
    為是獨立主題頁保留），故預設「找不到就中止」而非「找不到就當沒有」。
    `required=False` 僅供不需要判準②的呼叫端（如目前無批次檔的單元測試）
    明確選擇跳過。
    """
    if not batch_path.exists():
        if required:
            raise BatchFileMissing(
                f"講法批次檔不存在：{batch_path}（判準②會被靜默略過——"
                "容器內執行請確認已把 repo 根目錄 scripts/knowledge-batches/ "
                "掛載進來，或用 --batch-file 指到正確路徑）"
            )
        return set()
    data = json.loads(batch_path.read_text(encoding="utf-8"))
    return {item.get("question", "") for item in data.get("knowledge", []) if item.get("question")}


# ---------------------------------------------------------------------------
# 疑似講法列判準（純函式，⛔ 無 LLM）
# ---------------------------------------------------------------------------


def _prefix_similarity(a: str, b: str) -> float:
    """兩字串前綴逐字比對相同比例（分母＝較短者長度；空字串 ⇒ 0.0）。"""
    shortest = min(len(a), len(b))
    if shortest == 0:
        return 0.0
    match = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        match += 1
    return match / shortest


def classify_alias(
    row: RowMeta, all_rows: dict[int, RowMeta], batch_question_summaries: set[str]
) -> tuple[str, str]:
    """回傳 `(kind, reason)`，`kind ∈ {topic, alias, unknown}`。"""
    for key in _ALIAS_METADATA_MARKER_KEYS:
        if row.generation_metadata.get(key):
            return "alias", f"marker:{key}"

    if row.question_summary in batch_question_summaries:
        return "alias", "batch_file"

    for other_id, other in all_rows.items():
        if other_id == row.id:
            continue
        if not row.answer or not other.answer:
            continue
        if row.answer == other.answer:
            return "alias", f"duplicate_answer:{other_id}(exact)"
        similarity = _prefix_similarity(row.answer, other.answer)
        if similarity >= _PREFIX_SIMILARITY_THRESHOLD:
            return "alias", f"duplicate_answer:{other_id}(prefix={similarity:.2f})"

    if not row.categories:
        return "unknown", "no_categories"

    return "topic", "none"


# ---------------------------------------------------------------------------
# 渲染（純函式，供 unit 測試不接觸 DB）
# ---------------------------------------------------------------------------


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT), text=True
        ).strip()
    except Exception:  # noqa: BLE001 — dump 允許在非 git 環境跑，只是欄位留空
        return "unknown"


def render_markdown(
    doc: OutlineDoc,
    row_meta: dict[int, RowMeta],
    *,
    git_head: str,
    generated_at: str,
    batch_question_summaries: set[str],
) -> str:
    lines: list[str] = []
    lines.append(f"# 售前大綱人審 dump（audience={doc.audience}）")
    lines.append("")
    lines.append(f"- version: {doc.version}")
    lines.append(f"- sha256: {doc.sha256}")
    lines.append(f"- token_count: {doc.token_count}（approx={doc.token_count_approx}）")
    lines.append(f"- sections: {len(doc.sections)}")
    lines.append(f"- git_head: {git_head}")
    lines.append(f"- generated_at: {generated_at}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for section in doc.sections:
        section_tokens = max(1, len(section.text) // 2)
        lines.append(f"## {section.id} {section.title}")
        lines.append(
            f"citable={section.citable}；source_ids={section.source_ids}；"
            f"節 token 數估算≈{section_tokens}"
        )
        lines.append("")
        for source_id in section.source_ids:
            meta = row_meta.get(source_id)
            lines.append(f"### kb {source_id}")
            if meta is None:
                lines.append("（查無此 id 的後設資料——已在大綱組裝之後被刪除或改標？）")
                lines.append("")
                continue
            lines.append(f"- question_summary: {meta.question_summary}")
            lines.append(f"- categories: {meta.categories}")
            lines.append(f"- target_user: {meta.target_user}")
            lines.append(f"- business_types: {meta.business_types}")
            lines.append(f"- {COLUMN}: {meta.outline_approved_by}")
            lines.append("")
            lines.append(meta.answer)
            lines.append("")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 疑似講法列")
    lines.append("")
    lines.append(
        "判準（程式常數，見 `tools/agent_outline_dump.py` 檔頭）："
        f"①marker∈{_ALIAS_METADATA_MARKER_KEYS} ②batch_file="
        f"`{PHRASING_BATCH_FILE_DEFAULT.name}` ③duplicate_answer（前綴相似度≥"
        f"{_PREFIX_SIMILARITY_THRESHOLD}）。三者皆未命中且 categories 為空 ⇒ unknown；"
        "否則 topic。"
    )
    lines.append("")
    lines.append("| id | kind | reason | question_summary |")
    lines.append("|---|---|---|---|")

    alias_ids: list[int] = []
    for row_id in sorted(row_meta):
        row = row_meta[row_id]
        kind, reason = classify_alias(row, row_meta, batch_question_summaries)
        if kind == "alias":
            alias_ids.append(row_id)
        lines.append(f"| {row_id} | {kind} | {reason} | {row.question_summary} |")

    lines.append("")
    if alias_ids:
        lines.append("### 建議取消標記 SQL（只印，⛔ 本檔不執行；需業主人審後由主 session 執行）")
        lines.append("")
        lines.append("```sql")
        lines.append(_UNMARK_SQL_TEMPLATE.format(ids=", ".join(str(i) for i in alias_ids)))
        lines.append("```")
    else:
        lines.append("（本輪無 `kind=alias` 列，無建議取消標記 SQL。）")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def _run(out_path: Path, batch_file: Path) -> None:
    db_pool = LazyPsycopg2Pool()
    doc = await build_prospect_outline(db_pool)
    all_ids = sorted({sid for section in doc.sections for sid in section.source_ids})
    row_meta = fetch_row_meta(db_pool, all_ids)
    batch_question_summaries = load_batch_question_summaries(batch_file, required=True)
    markdown = render_markdown(
        doc,
        row_meta,
        git_head=_git_head(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        batch_question_summaries=batch_question_summaries,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"wrote {out_path} (sha256={doc.sha256}, sections={len(doc.sections)}, ids={len(all_ids)})")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="輸出 markdown 路徑")
    parser.add_argument(
        "--audience",
        default="prospect",
        choices=["prospect"],
        help="目前只支援 prospect（build_prospect_outline）",
    )
    parser.add_argument(
        "--batch-file",
        default=str(PHRASING_BATCH_FILE_DEFAULT),
        help=(
            "講法批次檔路徑（判準②）。預設指向 repo 根目錄 "
            "scripts/knowledge-batches/presales-phrasing-batch-20260904.json——"
            "容器內執行時該路徑不在 build context 內，需另外 mount 進去，"
            "或用本參數指到掛載後的路徑；找不到即中止（⛔ 不靜默略過）。"
        ),
    )
    args = parser.parse_args(argv)
    asyncio.run(_run(Path(args.out), Path(args.batch_file)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
