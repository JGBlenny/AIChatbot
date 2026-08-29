# Authorization execution record #01 —— 阻斷解除，implementation 重新凍結

日期：2026-08-29

⚠️ 本檔是 **successor execution record**，⛔ **未修改** `authorization-protocol-frozen.md`
的任何參數。protocol 的 source／sampling／labels／coverage precondition／
PASS-FAIL-INCONCLUSIVE 判準**逐字沿用、未動一字**，
⇒ provenance 保持乾淨：參數凍結在前，實作凍結在後，兩者可分別追溯。

## 阻斷條件解除

```text
原阻斷   凍結的 implementation（c35b2e4）的 gate 讀 query 詞彙證據，
         ⛔ 不是 applicability cross-product ⇒ 執行會量到舊 lexical gate
解除     P1f 完成 authority 換手（commit f8986125）
```

## 重新凍結的 implementation

```text
implementation SHA        f89861250d9cd01f4585fc9624a629b75bbcc7d5
authority input           knowledge_instance_applicability × face_instance_requirement
                          → instance_applicability_decision
lexical evidence          **已卸任**——僅供 telemetry 對照，⛔ 無 fallback 路徑
gate                      **OFF**（INSTANCE_REFERENCE_GATE 未設）
LEVEL_A_INSTANCE_GATE_SCOPE  {bill_diagnosis}（未變）
```

## 沿用且**經重新驗證未變**的凍結物

```text
Level-A population digest   57413ee8a4068f73bc4e0c2c0512967e   ✅ 與凍結時相同
face requirement digest     bde00b206c9c8b7d4b1328e7440d754f   （P1f 未動宣告）
protocol parameters         source=剩餘 sealed 456 全量 census
                            n_match=可判定 AND top1 ∈ frozen Level-A 10 rows
                            C1≥30／C2 instance≥10／C3 general≥10
```

## P1f 交付的授權證據

```text
deterministic matrix      7 形狀（instance/general/unknown × Level-A REQUIRED／
                          NOT_REQUIRED／非 Level-A）
mutation controls         general↔instance 翻轉結果；Face requirement 翻轉亦翻轉結果
lexical 死亡證明          lexical block 不得抑制已宣告 instance 的 row；
                          lexical 放行不得救回已宣告 general 的 row
gate-OFF 等價             3 applicability × 2 face，全部不抑制
非 Level-A 等價           其餘 15 個 REQUIRED Face 不受控
結構鎖                    抑制述詞的可執行語句不得引用 lexical 抽取器；
                          正對照要求真正使用的名稱看得見（尺不得為空）
接線範圍鎖                只有 routers/chat.py 得消費新判定；
                          conversational_engine／instance_reference_gate ⛔ 不得
全層測試                  1586 passed / 0 failed｜稽核十條全綠｜容器已重建同步
```

## ⛔ 本記錄**不**授權的事

```text
⛔ 未動用那 456 句（尚未抽樣、未標註、未執行 retrieval）
⛔ 未開啟 gate（仍需 gate_requested ∧ gate_authorized）
⛔ 未擴大 LEVEL_A_INSTANCE_GATE_SCOPE
⏸ 3.4 持續 PAUSED
```

## 下一步（依 frozen protocol 第 5 節，順序不可調換）

```text
2. 456 固定為本輪 corpus ＋ digest
3. blind truth labeling ＋ integrity check
4. freeze labels ＋ digest
5. 才第一次跑 frozen implementation
6. 計算 Level-A matching support
7. 先判 coverage precondition（C1／C2／C3）
8. coverage PASS 才計 authorization PASS／FAIL
```

⚠️ 一致率門檻仍待業主在 **coverage 判定通過後、看結果之前**補登。
