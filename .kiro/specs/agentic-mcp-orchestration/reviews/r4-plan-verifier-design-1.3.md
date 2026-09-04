# r4 plan-verifier（業主指示再審）— design 1.3（2026-09-04）

READY

P2（不擋，tasks 生成時納入）：
①條件表第 7 列只定義 b2c 的 `$bt`；b2b 的 `$bt = ['system_provider']`（`vendor_knowledge_retriever_v2.py` `vendor_business_types`）未列，實作時補一列避免誤取 `param_resolver`。
②「transport 出向參數斷言鉤子」現況無可掛符號（`transport.py` 只有 `Transport.send`、`JGBMockTransport.send`／`_bills_index`／`_contracts_index`）；可行縫線＝包一層 recording `Transport`，tasks 列為新增項。
③元件 5 `build_prospect_outline` 是 `build_visibility_predicate` 第四個消費點；tasks 註明以呼叫方式共用、不另寫 SQL。

## r3 兩條 P1 核對
- P1-a 謂詞第 4 條：已處置（與 `target_user_filter_sql` 兩處逐字同式；`KNOWN_TARGET_USERS` 含 `prospect`，售前大綱不會降級 tenant；矩陣含 `kb.target_user` 維）。
- P1-b mock：已處置（`UnsupportedMockParameterError` 保留；只驗出向轉發；語義本機不可驗明寫）。
- C3 八條 P2 各有落點；1.3 無新矛盾。
