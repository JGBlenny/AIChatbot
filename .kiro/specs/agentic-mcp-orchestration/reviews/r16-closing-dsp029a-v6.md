# r16：DSP-029a v6 closing（fresh plan-verifier，2026-09-05）

**判定：REVISE**（第二次 ⇒ 處置後記 epoch 2、只開一次 closing；再 REVISE 即暫停交業主）。

| # | 級 | 阻斷 | 處置（v7） |
|---|---|---|---|
| 1 | P1 | 標記格式字面仍兩段式（契約段、fixture 模板），與解析段三段式矛盾 | FIX：全列統一 `[{nonce}:{tool_call_id}:{source}§{i}]`；`wrap_provenance_data` 簽名、`UNIT_MARKER_SEP` 註解、`output_schema`／`_agent_rules_text` 說明、`_UNIT_MARKER_RE` 同步 |

其餘六條 r15 處置經 closing 確認通過；schema_cause 八值、驗收①四子成因、DSP-028 相容皆自洽。
