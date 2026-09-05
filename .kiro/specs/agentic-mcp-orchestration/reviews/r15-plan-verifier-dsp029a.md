# r15：DSP-029a（refs 照抄標記）——plan-verifier（fresh，2026-09-05）

**判定：REVISE**（1 P1、6 P2；替代方案 (a) 標籤模糊匹配＝業主禁止的特例修改、(b) 去 nonce 較弱，皆否決）。

| # | 級 | 阻斷 | 處置（v6） |
|---|---|---|---|
| 1 | P1 | 去掉 tool_call_id 後 `kb.search`／`kb.get` 同 `kb:{id}` 異文必撞 `ref_ambiguous` | FIX：標記改 `[{nonce}:{tool_call_id}:{source}§{i}]`，模型仍只照抄 |
| 2 | P2 | 步③ citable 失去輸入 | FIX：解析結果攜帶 `(quote, citable)`，沿用 SOURCE_NOT_CITABLE |
| 3 | P2 | refs 空的 fact 片段拒因自相矛盾 | FIX：UNCITED_ASSERTION，留在逐片段迴圈 |
| 4 | P2 | 任一 ref 失敗致命推翻 v4「只看被引用到的」 | FIX：只在 fact 筆的 refs 上致命 |
| 5 | P2 | runtime 三處回饋未列範圖、`len(out.citations)` 會炸 | FIX：三處改寫＋值域一致測試 |
| 6 | P2 | 漏列受影響測試與 DSP-021 兩案 | FIX：列出；兩案改判 ref_source_not_found 進 fabrications |
| 7 | P2 | 驗收只卡單一子成因 | FIX：四子成因合計 ≤5/162 |
