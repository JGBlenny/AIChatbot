# `/meters` 與團隊成員兩支端點盤查（jgb2 原始碼逐條對照）

> 2026-08-25｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> 來源：`MeterApiController.php`（208 行）／`TeamMemberApiController.php`（203 行）
> `transport-migration-inventory.md` §7 六步協議；§8 第 6、7 項。

## 一、`/meters`（`jgb_meters`）

### 契約

```text
恆定 where  iots.role_id = role_id、iots.active = 1、**iots.type = 'power_meter'**（:118-129）
篩選        estate_id（whereExists iot_estate，:31-39）
            keyword（iots.name LIKE **或** 綁定 estates.title LIKE，estates 需 active=1，:41-56）
排序        iots.id desc｜分頁 50／200、total_pages 在 total=0 時為 0
投影        formatMeter() 15 鍵（:152-172）
衍生        meter_type = manufacturer ∈ {Miezo, DAE, SkyWatch} ? 'cloud' : 'manual'
            is_online = (is_online == 1)｜balance／available_meter／current_reading 皆 (float)
            **is_poweron 三態**：-1（從未連線）→ null；0/1 → false/true（:167）
            estate_id／estate_name 來自 iot_estate join（未綁定 → 皆 null）
mapping     meter_type: {cloud: 雲端電表, manual: 手動抄表}
```

### 抓到的偏差

```text
M1  adapter docstring 寫「**端點無 keyword 參數**」——**是錯的**，:41-56 就有。
    改走 client 端 token 化過濾的真正理由是「整串 LIKE 對口語多詞配不中」（真資料 e2e 逼出），
    不是端點沒有。已改寫註解，行為維持（拉 per_page=200，正好等於 MAX_PER_PAGE）。
M2  替身只有一列、且只有 cloud／is_poweron=True 一種組合 ⇒ 兩條**衍生規則**
    （meter_type 白名單、is_poweron 三態）在替身上從未被走到，而 builder 對三態有專門防護。
    已補為三列：DAE(cloud)／Panasonic(manual)／SkyWatch(cloud，未綁物件 → estate_* 皆 null)，
    is_poweron 覆蓋 True／None／False。
M3  替身完全忽略 estate_id ⇒ 已實作（未綁定物件者查不到，對齊 iot_estate 過濾）。
✅  投影 15 鍵與 mapping 值本來就對。
```

## 二、`/roles/{id}/members` 與 `.../permissions`（`jgb_team_members`／`jgb_member_permissions`）

### 契約

```text
members      keyword **必填**（缺→400，:117-119）；role 不存在→404
             比對 **email 先、name 後**，皆 mb_strtolower + contains（:161-170）
             候選 = 擁有者（character_id=0）＋ role_user；同一人只回一次
             回 {member_user_id, character_id, character_name, is_owner, match_field}
             **不回 email／phone 明文**（:112）
permissions  data = {role_id, user_id, is_member, is_owner,
                     **character: {id, name, display}**, abilities}（:88-96）
             abilities = ABILITY_WHITELIST **32 鍵**（:17-32），成員取
             Role::getPermissionByCharacter，**擁有者全 true**（:64-69）
             非成員 → 404（:57-59）
```

### 抓到的偏差

```text
A1  members 替身**不論 keyword 一律回同一列** ⇒「查無此成員」分支測不到。已實作比對。
A2  替身只有一般成員一種形狀；**擁有者**（is_owner=true／character_id=0）與
    **character_name 為 None**（pivot 無 character_id）兩種都沒有，而 builder
    對前者有專門分支、對後者有 fallback。已補為三列涵蓋。
A3  permissions 替身只回 **6 個 abilities**；production 一律回滿 **32 鍵**——
    6 鍵是 production 產不出來的形狀。已改為 32 鍵。
A4  **憑空多出的鍵**：替身回 `character_name`，production **沒有這個鍵**（它回
    `character` 物件）。而 `services/jgb/accounts.py` 正是讀 `character_name`
    ⇒ 線上永遠取不到值，只能退回 T1 成員列的名稱。
    已修 accounts.py：**先讀 `character.name`**，保留舊鍵作相容。
```

## 三、仍未涵蓋

```text
· email／name 是加密欄位，production 在 PHP 端解密後比對——替身以明文近似，
  真實資料的大小寫／全半形／空白分佈只有真 API 會現形
· Role::getPermissionByCharacter 的 Redis 快取與 config('character') 範本 fallback
· iots.type 除 'power_meter' 外的裝置（本端點一律排除）
· 404（查無團隊／查無成員）與 400（缺 keyword）的區分：我方一律折疊為 success:False
