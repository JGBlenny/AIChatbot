# b2b 檢索盤查：選題規則（**凍結**）

> 2026-09-01｜⚠️ 抽題前寫定，⛔ 抽完不得修改｜**業主定案：範圍只做 b2b**
> 取代先前的 T1 batch-01（那批 13/19 是 b2c 情境，已不在範圍內）

## 為什麼只做 b2b

```text
實際非內部流量（usage_events）
  b2b / property_manager   1,321   ← 現役主力
  b2c / tenant                21   ← 幾乎無流量
⇒ b2c 側的缺口影響一條幾乎沒人走的路（見 b2b-b2c-pool-audit.md）
```

## b2b 的真實工作母體

```text
適格母體                        773
b2b 業者（property_manager）可見  285   ← **這是 b2b 的分母**
b2b 看不到的                     488
  其中 445 筆 source=loop／target_user=tenant
  ＝租客生活知識（社會住宅、租屋保險、包租代管差異、分租糾紛…）
  ⇒ 對業者問 JGB 系統操作**本來就不該可見**，⛔ 不計為 b2b 缺口
prospect 可見                     18   （presales-kb）⚠️ 極薄，另案
```

## 母體與抽法

```text
母體    test_scenarios｜is_active｜source='user_question'｜request_target_user='property_manager'
        ＝ 228 筆真實業者問句
抽數    35 題
排除    ⛔ 非問句（純數字／測試字樣／無語義）
        ⛔ T2（含 ≥4 位數編號且指涉那一筆記錄：多少｜是多少｜查｜看一下｜狀態｜繳費了嗎｜這張｜這筆）
        ⛔ T3（以 那／它／這個／再／然後／所以／就是 起頭，或片段無疑問詞）
        ⚠️ ⛔ 不以長度、難易或任何檢索結果排除
排序    md5("b2b-batch-20260901" || ':' || id) 升冪，取前 35，被排除者順延
```

## 執行情境（依契約 `docs/jgb2-chat-integration.md` §1）

```text
mode=b2b｜target_user=property_manager｜vendor_id=0（chat.py:4808 JGB System）
⚠️ b2b **不走 SOP**（契約明文）⇒ 知識庫即唯一答案來源
   ⇒ ⛔ 沒有 b2c 那個「我沒量 SOP」的量測缺口
```

## 成因分類（跑完逐題歸一類）

```text
V  可見性擋    語義最相關那筆被 business_types／target_user 濾掉
T  門檻擋      可見但融合分數未過門檻
S  語義召不回  語義 top1 本身就不對題（表示法／知識寫法問題）
N  庫裡沒有    語義 top15 全不對題 ⇒ 知識缺口
R  排序輸      正解在結果內但名次落後
```

⚠️ 每題的「正解是哪筆」由我提名、**業主確認**；⛔ 未確認前所有比率只是診斷。
