"""unit：**erratum 01 的 falsifier**（spec routing-disambiguation 任務 2.0｜R4.2, R1.3）。

1.6 的裁定建立在一個**可反證的前提**上：

```text
gate 只在「無正向證據 ＋ 有反向證據」時 block（design 決策 4，雙條件）
  ↓
Req.4 兩筆未決問句帶 possessive 正向證據 → allow → 從不進入抑制路徑
  ↓
∴ Face membership 與 utterance facet ownership 可分離
```

**若 extractor 對這兩句判出 `block`，本前提即被推翻——
1.6 裁定立即失效，SHALL 停止 Task 2 並重開 erratum，不准靠修改測試繼續。**

⚠️ **本檔 SHALL NOT 反過來決定 extractor 的規則集**：
規則集依 research.md 主題 1 的實測特徵表實作，**不得看本檔結果再補 pattern**——
那會讓 falsifier 自我實現（為這兩句補到會 positive → 2.0 PASS → 什麼也沒證明）。

⚠️ **2.0 PASS 不代表它們應去哪個 facet**：
SHALL NOT 據此宣稱 `billing_anomaly` 或 `bill_diagnosis` 正確。**Req.4 continues undecided.**
"""
import pytest

pytestmark = pytest.mark.unit

#: Req.4 兩筆產品歸屬未決問句（凍結於 protocol v1 的 UNDECIDED 案例集）
UNDECIDED_UTTERANCES = ["我的收據在哪", "我這筆點退的錢怎麼怪怪的"]


@pytest.mark.req("routing-disambiguation:4.2")
@pytest.mark.parametrize("utterance", UNDECIDED_UTTERANCES)
def test_undecided_utterances_carry_positive_instance_evidence(utterance):
    """extractor 層：正向證據 SHALL 非空。"""
    from services.instance_evidence import InstanceEvidenceExtractor

    evidence = InstanceEvidenceExtractor().extract(utterance)
    assert evidence.positive, (
        f"「{utterance}」沒有任何正向 instance 證據（spans={evidence.spans}）——"
        "1.6 裁定的前提『它們不進 block path』失去依據，SHALL 停止 Task 2 並重開 erratum")


@pytest.mark.req("routing-disambiguation:4.2")
@pytest.mark.parametrize("utterance", UNDECIDED_UTTERANCES)
def test_undecided_utterances_are_never_blocked(utterance):
    """gate 層：`verdict` SHALL NOT 為 `block`。

    ⚠️ 本條在 gate 實作前**自動略過、實作後自動生效**（`importorskip`）——
    寫成註解或待辦會被忘記，寫成自動上膛的斷言不會。
    """
    gate = pytest.importorskip(
        "services.instance_reference_gate",
        reason="[env] gate 尚未實作（任務 3.1）——本條於 gate 落地後自動生效")
    from services.instance_evidence import InstanceEvidenceExtractor

    evidence = InstanceEvidenceExtractor().extract(utterance)
    decision = gate.instance_reference_gate(evidence, face_requires_instance=True)
    assert decision.verdict != "block", (
        f"「{utterance}」被判 block——1.6「membership 與 facet ownership 可分離」的前提被推翻")
