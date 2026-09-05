# r11：DSP-028 Verifier 步②變更——security-reviewer（唯讀，2026-09-05）

**判定：BLOCKING**（7 條；1 P1、4 P2、2 P3）。全數處置見 `DECISIONS.md` DSP-028 v3「r11 安全審處置」段。

| # | 優先級 | 發現 | 處置 |
|---|---|---|---|
| F-1 | P1 | 片段×cite 量詞未定義；最鬆讀法重開 r2 #10 | FIX：每 fact 片段須有至少一筆 cite 完整過③④ |
| F-2 | P2 | `assertion_terms` 覆蓋不足（支持／有／是／包含／整合…），單句修辭問句可整筆免引用；既有問題、本案拆掉 47% SCHEMA 牆後流量放大 | 部分 FIX（補產品能力動詞 5 詞）＋監控欄；「有／是／已／將」OPEN（誤殺代價） |
| F-3 | P2 | `self_test` 不比 `expected_reason`，轉換漏改會以 SCHEMA 假綠 | FIX：`_assert_all` 比 reason；尺④改 pytest verifier 測試 |
| F-4 | P2 | `answer` 若 `computed_field` 會被 strict schema 要回模型輸出 | FIX：純 `@property`＋properties 集合測試 |
| F-5 | P2 | `cite` 負索引取到合法 citation | FIX：`idx<0` 判 SCHEMA＋fixture |
| F-6 | P3 | 尾隨 `\n` 切出空片段被降 fact ⇒ 推高 budget_exhausted | FIX：空白片段跳過複核 |
| F-7 | P3 | 步⑥／字面敏感詞未壓空白（既有，非本案） | DEFER → tasks 5.6 |

CONFIRMED-SAFE：拼接後掃①⑤⑥⑦是安全側（掃的字串＝送出的字串；前提：`answer` 單一導出點，現況成立）；消費端無人讀模型端欄位；handoff 文字不外流；prompt 注入防線未鬆動；新契約無新增自由文字出口（`answer`→`sentences[].text` 一對一置換，且每字必屬一筆、每片段必過型別複核）。

r2 第 10 條：**多句變體 FIX（逐片段複核＋fixture）、單句變體 OPEN（F-2）**，⛔ 不得記為整條關閉。
