# ⛔ 本 spec 已封存（HALTED）—— 不是主線,⛔ 不得當成主線引用

```text
封存於    2026-09-01（業主指示）
狀態      implementation-blocked（2026-08-19）｜tag rdl-20260822-halt
封存理由  與主線 conversational-routing-execution 的「面向進出」範圍重疊,
          反覆被誤認成主線。
```

## 主線是哪一支

```text
conversational-routing-execution   ← 唯一主線
  範圍:Knowledge retrieval 勝出**之後**的 Face routing／Direct answer 接縫,
        以及 Face execution 的可驗證性、對話品質可量測（R10）
```

## ⚠️ 本 spec 已交付且**仍在生產環境運行**的部分（⛔ 勿因封存而誤刪）

```text
任務 1.3   services/decision_layer.DecisionConfig —— 門檻唯一讀值點 ＋ 六 case 仲裁
           主線 design.md:157 明文依賴它（R7.4）；散讀值點=0 已進 make audit 不變量
           唯一被標記「✅ 有效」的驗收
任務 0.1   決策快照唯一組裝出口（R8.3、D-19）—— chat.py:2607／2622
引用處     chat.py:24／1238／2607／2622
```

## ⛔ 未開工的部分（封存前後皆未實作,⛔ 不在任何現行計畫內）

```text
P1  逃生門 EscapeState／識別碼訊號 IdentifierSignal／再進場抑制
P2  knowledge_variants 變體表／對話歷史層／省略補全／複合句拆解／錨點分型遷移
P3  詞面通道 RRF／偏差雷達
P0' 0.8 基線重測（量尺已修好但未重測）→ 0.9 → 0.10 重驗 V0
```

## 若要復活

先讀 `README.md` 的「一分鐘現況」與 `decisions/DECISIONS.md`,
並確認與主線的「面向進出」範圍如何切分——⛔ 兩支同時改同一接縫會互相踩。
