"""未映射條款粗切（design.md 元件 7）。需求 7.1–7.3。

「粗切＋去重、⛔ 不求精」（需求 7.1 v2）：OCR 信心度 0.16–0.70 下斷行不可靠，本模組只負責
把 `ocr_raw.text` 切成句段、留下「像條款」的、剔除已被欄位吸收的；LIFF 端可編輯。
⛔ 不摘要、不改寫、不翻譯——輸出必為輸入的逐字子串（只去掉前導編號與首尾空白）。
⛔ 寵物／吸菸／訪客類條款一律進陣列，不映射到 `smoke_detector` 等語義不同的欄位。
"""
from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from services.ocr_mapping.models import DocuMindPage

_CN_NUM = "一二三四五六七八九十百零〇\\d"
#: 段落分隔：換行，或行中出現的「第N條」（同一行塞多條時）
_SPLIT = re.compile(rf"\n|(?=第[{_CN_NUM}]+條)")
#: 前導編號：第N條 ／ N、 ／ （N） ／ (N)
_LEAD = re.compile(rf"^\s*(?:第[{_CN_NUM}]+條|[{_CN_NUM}]+、|（[{_CN_NUM}]+）|\([{_CN_NUM}]+\))\s*")
#: 「像條款」的三類訊號：金額／期間／義務語
_MONEY = re.compile(r"[\d,]{3,}|[壹貳參肆伍陸柒捌玖拾佰仟萬]+\s*元|NT\$")
_PERIOD = re.compile(r"[年月日天期週]")
_OBLIGATION = re.compile(r"不得|應|須|禁止|負擔|得於|同意|保證|付清|付款|給付|逾期|滯納")
_WS = re.compile(r"\s+")


def _squash(s: str) -> str:
    return _WS.sub("", s)


def _is_clause_like(seg: str) -> bool:
    return bool(_MONEY.search(seg) or _PERIOD.search(seg) or _OBLIGATION.search(seg))


def _absorbed(sq: str, absorbed: Sequence[str]) -> bool:
    """整段落在某個已映射 raw 裡 ⇒ 吸收；否則把所有已映射片段挖掉，**剩餘部分若仍像條款就不算吸收**。

    ⚠️ 2026-09-03 對抗驗證 ②-2：舊寫法「raw 是條款子串就整條刪」讓
    「乙方應於每月五日前繳納租金，逾期按日加收滯納金」因 cycle_date 吸收了「每月五日前」而整條消失
    ——違反拍板決策 4（未映射條款 ⛔ 不丟）。寧可多列讓 LIFF 刪，不可少列。
    """
    if any(sq in a for a in absorbed):
        return True
    rem = sq
    for a in absorbed:
        rem = rem.replace(a, "")
    return not _is_clause_like(rem)


def split_clauses(pages: Sequence[DocuMindPage], absorbed_raws: Iterable[str]) -> List[str]:
    absorbed = [_squash(r) for r in absorbed_raws if r and _squash(r)]
    seen: dict[str, None] = {}
    for pg in pages:                                        # 頁序＝輸出序
        for raw_seg in _SPLIT.split(pg.ocr_raw.text or ""):
            seg = _LEAD.sub("", raw_seg or "").strip()
            if not seg or not _is_clause_like(seg):
                continue
            if _absorbed(_squash(seg), absorbed):            # 已被映射欄位的 raw 吸收 ⇒ 不重複列
                continue
            if seg not in seen:
                seen[seg] = None
    return list(seen)


__all__ = ["split_clauses"]
