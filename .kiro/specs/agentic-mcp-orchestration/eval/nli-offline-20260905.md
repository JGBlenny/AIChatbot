# 4.4c NLI 接地檢查——離線量測結果（2026-09-05；計畫 `nli-offline-plan.md` 判準凍結於量測前）

- 環境：`aichatbot-semantic-model` 容器（py3.9、torch 2.8 cpu、transformers 4.57、8 核；VM MemAvailable 1.68 GB ⇒ mDeBERTa-base 未跑，記憶體風險）。⛔ 未接線上、未動 Verifier。
- 資料：4.4b 同一批——第七輪 54 句 agent 鏈旁路 → 136 標籤句（fact 且有解析來源者 133：有據 84／無據 49；無據＝partial＋unsupported）。前提＝DSP-029 解析出的來源句、假設＝回答句片段；F-1 量詞取來源句中最大 p_ent。繁中原文直接輸入（OpenCC 未裝，t2s 變體未跑）。
- 模型：`IDEA-CCNL/Erlangshen-Roberta-110M-NLI`（簡中原生 NLI）、`MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`。

## τ 掃描（NLI 單獨；抓到率＝無據被拒，誤殺率＝有據被拒）
| τ | Erlangshen 抓到／誤殺 | MiniLM 抓到／誤殺 |
|---|---|---|
| 0.4 | 65%／11% | 61%／18% |
| **0.5** | **69%／11%** | 65%／20% |
| 0.6 | 78%／15% | 67%／21% |
| 0.7 | 80%／19% | 71%／23% |
| 現行規則 | 53%／13%（同批重算 49%／13%） | — |

聯合閘（現行 ∧ NLI，任一拒即拒）：Erlangshen τ0.5 抓 76%／誤殺 18%——誤殺超門檻 ⇒ 若接線應為**取代**覆蓋尺而非疊加（待更多資料確認）。

## 延遲（暖機、max_length 256、8 threads、30 對）
Erlangshen p50 155 ms／p95 **242 ms**；MiniLM p50 26／p95 **66 ms**。冷跑 max_len 512 Erlangshen p95 1062 ms。

## 尺自證（R4 三捏造句，known_open）
Erlangshen 2/3（「上傳既有合約…作為參考」p_ent 0.92 未抓；「作為參考／存檔」變體 0.44 抓到；「需要管理者權限」0.36 抓到）；MiniLM 0/3。

## 判定（依凍結門檻：抓到 > 現行且誤殺 ≤ 現行、p95 ≤ 100 ms、自證 3/3）
- **MiniLM：不採用**（準確度不過、自證 0/3）。
- **Erlangshen-110M：準確度兩尺過、延遲與自證不過 ⇒ 依凍結判準不接線**；狀態＝「留作抽審輔助」。它是目前唯一在抓到率與誤殺率上同時優於現行規則的候選（69%／11% vs 53%／13%）。
- 業主可裁的兩個放寬項（⛔ 由業主裁、非主 session 自改）：① 延遲門檻 100 ms→300 ms（每回合約 2–3 句對 ⇒ p95 加 0.5–0.7 s，現行 agent p95 4.5 s）；② 自證 3/3→2/3。若兩項放寬，Erlangshen τ=0.5 可立提案接為**取代**覆蓋尺的追加閘（仍決定性：固定權重、固定 τ）。
- 未做：mDeBERTa-base（需 VM 可用記憶體 ≥ 2.5 GB）、OpenCC t2s 變體、ONNX／量化降延遲。三者都可能改變結論，列為 4.4c 後續。

## 方法限制
單一判者標籤（同 4.4b）；136 句單主題；自證 3 句依 README 重建非逐字；延遲在共用容器量、非目標部署機。
