# F2-INPUT／OUTPUT transport audit（唯讀實查，2026-08-30）

> 目的：把 F2-A 五筆暴露的**共同 architecture prerequisite** 一次收掉，
> ⛔ 不要在 F2-B 的 20 筆裡重複寫 15 次「input reachability 未建立」。

## A. round-trip 目前攜帶的是 **row id**，⛔ 不是 responsibility

```text
services/form_manager.py:231／248／256   form session 建立時帶 `knowledge_id: int`
                        :2411           完成時 `knowledge_id = session_state.get('knowledge_id')`
                        :418            `_get_knowledge_answer_sync(knowledge_id)` → 取該列 answer
```

⇒ **現行 round-trip carrier ＝ `form_sessions.knowledge_id`（一個 row）**。
⛔ 沒有 responsibility_id／strategy／capability binding／input contract 的欄位。

⚠️ 依 **F-C2**，session carrier 必須改成攜帶那四項 immutable ⇒ 這是一個**明確且有界的 schema 工作**
（新增欄位，非改語義），且它是 R-05／28／29／31 四筆 input reachability 的**共同前置**。

## B. entity resolution：有歧義通道，但 **first-row authority 仍在**

```text
services/form_manager.py:2435  API 錯誤型別 ['ambiguous_match','no_match','invalid_input']
                               → 要求使用者重新輸入，retry ≤ 2 次後自動取消表單
```

✅ 這條通道正是 **F-C3** 需要的「多筆時不得默默取第一筆」的落點。

⚠️ 但 first-row authority **仍存在於 formatter 層**：

```text
services/jgb/contracts.py:648   contract = matched[0]        ← 只回應第一筆匹配的合約
services/jgb/bills.py:379       return builder(rows[0], ...) ← 非點退意圖時取第一列
```

⇒ 目前**只有點退**那條路徑（`POINT_REFUND_BILL_SELECTION`）真的殺掉了 `data[0]`。
F-C3 要在責任層普遍成立，這兩處是必須處理的對象。

## C. resume 已經是 resume，**但語義 owner 會被重新決定**

```text
✅ 表單完成 ⛔ **不會**重跑 retrieval——走 form_schema 的 on_complete_action
   （show_knowledge／call_api／both）＋ api_config
❌ 但 owner 會被重新決定：
   api_call_handler.py:404  format_jgb_response(api_result, endpoint, user_question, form_data, face)
   jgb_response_formatter   依 **endpoint** 選分支
   bills.py:365             `builder = BILL_FACE_BUILDERS.get(face)`   ← **face（category）選 builder**
   bills.py:377             `if _pr.is_point_refund_intent(user_question)` ← **utterance 分流**
   bills.py:427/contracts.py:681  diagnose_bill／_build_response 的 keyword elif ← **utterance 再判**
```

⇒ **現行 resume 路徑違反 F-C2**：commit 之後，`face` 與 `user_question` 仍會重新挑 semantic owner。
fulfillment binding 必須**繞開整條 `format_jgb_response` 分派**，直接呼叫 reviewed capability。

## D. FINAL_TEXT downstream：已存在且可用

```text
services/api_call_handler.py:339  api_response_text = _format_api_data(...)
                            :343  on_complete_action='both' → f"{api_response_text}\n\n---\n\n{knowledge_answer}"
                            :345  否則直接回 api_response_text
```

⇒ FINAL_TEXT adapter 現成；且**已有「facts ＋ knowledge」串接的既有慣例**（`---` 分隔）。

## E. GROUNDING_FACTS 的真正 consumer

```text
formatter 回傳的 facts 字串 → `formatted_response`
services/conversational_engine.py:1001  「label（哪一筆）＋ formatted_response（formatter 已把碼翻成
                                        中文事實／可否操作），組文字」
                            :1049  result = {**result, "formatted_response": reformatted}
                            :1059  parts = [head, result.get("formatted_response")]
routers/chat.py:4088-4098   formatted_response → answer
```

⇒ **facts → 話術的 adapter 存在，但住在 `conversational_engine`，且由它自己的邏輯 keyed**。
⚠️ 因此 `GROUNDING_FACTS` 的 responsibility adapter **⛔ 尚不能直接抽出**——
需先確認 `conversational_engine` 這段的進入條件是否也依賴 face／utterance（若是，同樣違反 F-C2）。

---

## 收斂：四筆 `INPUT_REACHABILITY_NOT_ESTABLISHED` 的共同前置只有三件

```text
① session carrier 擴充：responsibility_id ／ strategy ／ binding ／ input contract（A）
② entity resolution 契約化：沿用既有 ambiguous_match 通道，並處理 contracts.py:648 與
   bills.py:379 兩處 first-row authority（B ＋ F-C3）
③ fulfillment 執行時**繞開** format_jgb_response 的 endpoint／face／utterance 分派（C ＋ F-C2）
```

⚠️ ③ 是**最大的一項**：它等於在 `api_call_handler` 之前插入一條 responsibility-committed 執行路徑。

## 尚未回答（⛔ 不在本次唯讀盤查範圍）

```text
· conversational_engine 的 facts→話術段落，其進入條件是否依賴 face／utterance？
  （若是 ⇒ GROUNDING_FACTS adapter 也要一起繞開，R-28／R-31 才可能閉合）
· on_complete_action='show_knowledge' 的責任層對應是什麼？
  （現行語義是「顯示該 knowledge row 的 answer」＝ row authority，與 fulfillment 直接衝突）
```
