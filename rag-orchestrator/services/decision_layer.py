"""C1 DecisionLayer 決策中樞（spec retrieval-decision-layer 任務 1.3｜R7.4、R8.3）。

**這一步只做「搬移不重構」**：把散落在 chat.py／conversational_engine.py 的門檻讀值
（KB_SIMILARITY_THRESHOLD ×4、FORM_TRIGGER_THRESHOLD ×2）與六 case 答題仲裁的硬編碼
常數（0.15／0.55／0.6）收進唯一讀值點，仲裁判定邏輯**逐分支原樣搬入** `decide_arbitration()`
——六 case 結構不動（171 條整合測試護欄；gap-analysis G6 選項 A 定案）。

等價契約（審查修訂 1 第①層）：本模組的決定性子決策（門檻比對、分類路由 gate、六 case
仲裁）對任意輸入必須與搬移前的 inline 邏輯**嚴格同輸出**——unit 以逐字複製的參考實作
全域對拍（tests/unit/decision/）。調參、灰帶、識別碼訊號都是 P1 的事，不在此檔此版。

快照（R8.3）：`decide_arbitration()` 產出可歸因快照 dict，由呼叫端經
`usage_metering.set_decision()` 貢獻，最終由 `chat._finalize_decision_snapshot()`
在 dispatcher **唯一出口**組裝落地（任務 0.1）。仲裁只是其中一個貢獻者——
面向進場/續輪/退出、b2b 短路、快取命中各自貢獻；未貢獻的路徑落最小快照
（帶 `path` 與 `incomplete: true`），使覆蓋缺口成為可查事實而非靜默缺席。
（本檔頭原寫「從此每輪記下」，實測僅 54.8%、面向續輪 0%——D-19 已修正。）
"""
import hashlib
import json
import os
from dataclasses import dataclass, fields
from typing import Any, Dict, Optional

# 仲裁規則版本（快照歸因用）：判定結構或門檻語義改變時升版；
# 純搬移＝v1（與搬移前 inline 邏輯同構）。
DECISION_RULE_VERSION = "dl-v1"


@dataclass(frozen=True)
class DecisionConfig:
    """決策層唯一讀值點（R7.4）。

    值與預設**一字不改**沿自散落讀值點：
    - kb_threshold        ── KB_SIMILARITY_THRESHOLD（檢索過濾／Brain kb_search 同源）
    - form_trigger_threshold ── FORM_TRIGGER_THRESHOLD（面向進場＋表單觸發同一顆）
    - sop_min / knowledge_min / score_gap ── 六 case 仲裁硬編碼（原 chat.py 常數）
    """
    kb_threshold: float = 0.55
    form_trigger_threshold: float = 0.75
    sop_min: float = 0.55
    knowledge_min: float = 0.6
    score_gap: float = 0.15

    @classmethod
    def load(cls) -> "DecisionConfig":
        """讀 env 組出設定。每次呼叫即時讀（與原散落 os.getenv 同語義——
        原碼每請求讀一次 env，搬移後不得引入跨請求快取改變行為）。"""
        return cls(
            kb_threshold=float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.55")),
            form_trigger_threshold=float(os.getenv("FORM_TRIGGER_THRESHOLD", "0.75")),
            # 六 case 常數原為硬編碼、無 env——保留無 env 狀態（調參是 P1 任務 2.4，
            # 提前開 env 旋鈕會讓「等價驗證」失去對照意義）
        )

    def config_hash(self) -> str:
        """設定值雜湊（快照歸因用；任務 2.3 再納入 _generate_config_version）。"""
        body = json.dumps({f.name: getattr(self, f.name) for f in fields(self)},
                          sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:8]


# ════════════════════════════════════════════════════════════════════
# 六 case 答題仲裁（自 chat.py _smart_retrieval_with_comparison 原樣搬入）
# ════════════════════════════════════════════════════════════════════

def decide_arbitration(*, sop_score: float, knowledge_score: float,
                       has_sop: bool, sop_cancelled: bool,
                       sop_action_executed: bool, sop_has_response: bool,
                       sop_has_action: bool, sop_next_action: Optional[str],
                       config: DecisionConfig) -> Dict[str, Any]:
    """答題去向仲裁——判定分支、比較運算、reason 字串皆與搬移前逐字等價。

    輸入（全部決定性，呼叫端自 sop_result/knowledge_list 提取）：
    - has_sop            ── sop_result 存在且 has_sop
    - sop_cancelled      ── trigger_result.cancelled（特殊情況 0A）
    - sop_action_executed ── action_result 存在且 trigger_result.matched（特殊情況 0B）
    - sop_has_response   ── sop_result.response is not None
    - sop_has_action     ── next_action ∈ {form_fill, api_call, form_then_api}
    回傳：{'type', 'reason', 'decision_case', 'gap', 'snapshot'}；呼叫端負責組
    knowledge_list／sop_result 外殼與 comparison dict（結構不動）。
    """
    SCORE_GAP_THRESHOLD = config.score_gap
    SOP_MIN_THRESHOLD = config.sop_min
    KNOWLEDGE_MIN_THRESHOLD = config.knowledge_min

    def _out(rtype, reason, case, gap):
        return {"type": rtype, "reason": reason, "decision_case": case, "gap": gap,
                "snapshot": {
                    "rule_version": DECISION_RULE_VERSION,
                    "config_hash": config.config_hash(),
                    "sop_top1_final": sop_score,
                    "kb_top1_final": knowledge_score,
                    "sop_min": SOP_MIN_THRESHOLD,
                    "knowledge_min": KNOWLEDGE_MIN_THRESHOLD,
                    "score_gap": SCORE_GAP_THRESHOLD,
                    "has_sop": has_sop,
                    "sop_has_action": sop_has_action,
                    "sop_has_response": sop_has_response,
                    "verdict": rtype,
                    "decision_case": case,
                }}

    # 🆕 特殊情況 0A：SOP 被用戶取消（cancelled）
    if has_sop and sop_cancelled:
        print(f"🚫 [特殊情況] 用戶取消 SOP 動作，返回禮貌回應")
        return _out('sop', '用戶取消 SOP 動作', 'sop_cancelled_by_user',
                    abs(sop_score - knowledge_score))

    # 🆕 特殊情況 0B：SOP 已觸發並執行後續動作（action_result 存在）
    # 這種情況下，無論 similarity 分數如何，都應該優先返回 SOP 的結果（包括錯誤訊息）
    if has_sop and sop_action_executed:
        print(f"⚡ [特殊情況] SOP 已觸發並執行後續動作，優先返回 SOP 結果")
        return _out('sop', 'SOP 關鍵詞匹配並已執行後續動作',
                    'sop_triggered_action_executed', abs(sop_score - knowledge_score))

    # 特殊情況：SOP 等待關鍵詞（response 為 None）
    if has_sop and not sop_has_response:
        print(f"⏸️  [特殊情況] SOP 等待關鍵詞中，繼續其他流程")
        # 這種情況下，即使 SOP 分數高，也應該讓知識庫回答
        gap = abs(knowledge_score - sop_score)
        if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
            return _out('knowledge',
                        f'SOP 等待關鍵詞，使用知識庫 ({knowledge_score:.3f})',
                        'sop_waiting_for_keyword_use_knowledge', gap)
        else:
            return _out('none', 'SOP 等待關鍵詞且知識庫未達標',
                        'sop_waiting_both_below_threshold', gap)

    # Case 1: SOP 顯著更高
    if (sop_score >= SOP_MIN_THRESHOLD and
            sop_score > knowledge_score + SCORE_GAP_THRESHOLD):
        print(f"✅ [決策] SOP 顯著更相關 ({sop_score:.3f} > {knowledge_score:.3f} + 0.15)")
        return _out('sop', f'SOP 分數顯著更高 ({sop_score:.3f} vs {knowledge_score:.3f})',
                    'sop_significantly_higher', sop_score - knowledge_score)

    # Case 2: 知識庫顯著更高
    if (knowledge_score >= KNOWLEDGE_MIN_THRESHOLD and
            knowledge_score > sop_score + SCORE_GAP_THRESHOLD):
        print(f"✅ [決策] 知識庫顯著更相關 ({knowledge_score:.3f} > {sop_score:.3f} + 0.15)")
        return _out('knowledge',
                    f'知識庫分數顯著更高 ({knowledge_score:.3f} vs {sop_score:.3f})',
                    'knowledge_significantly_higher', knowledge_score - sop_score)

    # Case 3: 分數接近（差距 < 0.15）
    if (sop_score >= SOP_MIN_THRESHOLD and
            knowledge_score >= KNOWLEDGE_MIN_THRESHOLD):
        gap = abs(sop_score - knowledge_score)
        print(f"⚖️  [決策] 分數接近 (差距: {gap:.3f} < 0.15)")

        # 3.1: SOP 有後續動作 → 優先 SOP
        if sop_has_action:
            print(f"✅ [優先級] SOP 有後續動作，優先處理 ({sop_next_action})")
            return _out('sop', f'SOP 有後續動作 ({sop_next_action})',
                        'close_scores_sop_has_action', gap)

        # 3.2: SOP 無動作 → 選分數更高的
        if sop_score > knowledge_score:
            print(f"✅ [比較] SOP 分數略高 ({sop_score:.3f} > {knowledge_score:.3f})")
            return _out('sop',
                        f'分數接近但 SOP 略高 ({sop_score:.3f} vs {knowledge_score:.3f})',
                        'close_scores_sop_slightly_higher', gap)
        else:
            print(f"✅ [比較] 知識庫分數略高 ({knowledge_score:.3f} > {sop_score:.3f})")
            return _out('knowledge',
                        f'分數接近但知識庫略高 ({knowledge_score:.3f} vs {sop_score:.3f})',
                        'close_scores_knowledge_slightly_higher', gap)

    # Case 4: 只有 SOP 達標
    if sop_score >= SOP_MIN_THRESHOLD:
        print(f"✅ [決策] 只有 SOP 達標 ({sop_score:.3f} >= 0.55)")
        return _out('sop', f'只有 SOP 達標 ({sop_score:.3f})', 'only_sop_qualified',
                    abs(sop_score - knowledge_score))

    # Case 5: 只有知識庫達標
    if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
        print(f"✅ [決策] 只有知識庫達標 ({knowledge_score:.3f} >= 0.6)")
        return _out('knowledge', f'只有知識庫達標 ({knowledge_score:.3f})',
                    'only_knowledge_qualified', abs(knowledge_score - sop_score))

    # Case 6: 都不達標
    print(f"⚠️  [決策] SOP ({sop_score:.3f}) 和知識庫 ({knowledge_score:.3f}) 都未達標")
    return _out('none', '都未達到最低閾值', 'both_below_threshold',
                abs(sop_score - knowledge_score))


# ════════════════════════════════════════════════════════════════════
# 面向進場／表單觸發 gate（決定性子決策；DB 查詢留在呼叫端）
# ════════════════════════════════════════════════════════════════════

def facet_entry_eligible(best_knowledge: Optional[dict],
                         config: DecisionConfig) -> bool:
    """分類路由進場的門檻 gate（原 chat.py `_diagnosis_config_for_knowledge` 首行判定）。

    top-1 知識 final 分數 ≥ form_trigger_threshold 才有資格進面向；
    分類是否命中面向設定（DB 查詢）仍由呼叫端處理——本函式只管決定性部分。
    """
    return bool(best_knowledge) and \
        best_knowledge.get('similarity', 0) >= config.form_trigger_threshold


def form_trigger_eligible(best_knowledge: Optional[dict],
                          config: DecisionConfig) -> bool:
    """表單觸發 gate（原 chat.py `_build_knowledge_response` 步驟 1 判定）。

    最高順位知識是表單類型（action_type=form_fill 或帶 form_id）且
    final 分數 ≥ form_trigger_threshold → 觸發表單。
    """
    if not best_knowledge:
        return False
    action_type = best_knowledge.get('action_type', 'direct_answer')
    form_id = best_knowledge.get('form_id')
    return (action_type == 'form_fill' or bool(form_id)) and \
        best_knowledge.get('similarity', 0) >= config.form_trigger_threshold
