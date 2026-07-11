"""
JGB 修繕面向：槽位預填 Prefill（薄模組）

spec conversational-repair 元件 3（R2.1–2.5）。目標形態「系統知道的事不要再問」：
- estate：身份雙證 → get_tenant_contracts → 1 筆帶入確認型槽位／N 筆轉候選（插點 A）／
  0 筆或 API 失敗 → 誠實降級文案（「請與管理師確認租約狀態」）。
- 分類三槽＋急迫性：Vision 辨識結果（呼叫端做完傳入，本模組不打 Vision）——信心 ≥ 門檻
  → 推斷為確認型槽位（source='inferred'）；不足 → 退化為 2-3 候選讓使用者選一輪，
  不退回三層下拉；無圖/None → 槽位留空（變詢問型，由 brain 開口問）。

槽位形態（整合缺口修復，全數扁平標量——api_call_handler `{form.<slot>}` 不吃點號、
confirm_template placeholder 也需標量）：
- estate 拆為 `estate_id`／`contract_id`／`estate_display`（各自獨立 SlotValue，不再產 dict）。
- 分類名稱經修繕分類樹解析為 id：`category_id`／`item_id`（int，source='inferred'）＋
  `broken_reason`（字串，對齊 create_repair 期待）；並產顯示槽 `category`／`item`
  （confirm_template 用 {category}/{item} 呈現；broken_reason 字串本身即顯示）。
- 急迫性槽名為 `emergency_status`（對齊 required_slots/execute_params/confirm_template）。
- 名稱在分類樹對不到 → 該 id 槽不產出（不硬塞，留空變詢問型或候選）；
  分類樹查詢失敗／無 jgb_api → 全部降級為顯示名候選（不拋錯）。

分型只做，不決定呈現：candidates 形狀對齊引擎插點 A（{id, label}）；slots 每槽
{value, source, confirmed:False}。門檻/候選上限/降級文案全從傳入 config（grounding_scope
dict）讀，帶預設值——不硬編 vendor 或修繕專屬字樣在邏輯裡。
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)

# 配置預設值（config 未帶對應鍵時使用）——決策 3 沿用 0.7 門檻前例。
_DEFAULT_INFERENCE_CONFIDENCE = 0.7
_DEFAULT_CANDIDATE_MAX = 3
_DEFAULT_DEGRADED_NO_CONTRACT = "請與管理師確認租約狀態"


class SlotValue(TypedDict):
    value: Any
    source: str      # 'prefill' | 'inferred'（本模組只產這兩種來源）
    confirmed: bool  # 預填/推斷階段恆 False，確認 gate 同意後才轉 True


class PrefillResult(TypedDict):
    slots: Dict[str, SlotValue]
    candidates: Optional[List[Dict[str, Any]]]  # 插點 A 形狀 {id, label}（多租約或分類候選）
    degraded: Optional[str]                     # 降級文案（0 筆/API 失敗）


class RepairClassification(TypedDict, total=False):
    """名稱→id 解析結果（分類樹查詢命中的部分）。缺鍵＝該層對不到，不硬塞。"""
    category_id: int
    category_name: str
    item_id: int
    item_name: str
    broken_reason: str


def _slot(value: Any, source: str) -> SlotValue:
    return {"value": value, "source": source, "confirmed": False}


def _degraded_message(config: Dict[str, Any]) -> str:
    messages = config.get("degraded_messages") or {}
    return messages.get("no_contract") or _DEFAULT_DEGRADED_NO_CONTRACT


def _estate_display(row: Dict[str, Any]) -> str:
    """組物件顯示字串供確認摘要呈現（不出口個資紅線欄位，僅用契約既有欄位）。"""
    parts = [str(row.get(k)).strip() for k in ("estate_title", "display_address", "room")
             if row.get(k)]
    return "／".join(parts)


def _estate_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    """多租約 → 插點 A 候選（id=estate_id，label=顯示字串）。"""
    return {"id": row.get("estate_id"), "label": _estate_display(row)}


def _classification_candidates(recognition: Dict[str, Any],
                               cap: int) -> List[Dict[str, Any]]:
    """信心不足 → 退化候選（決策 4，不退三層下拉）。

    來源＝主推斷 suggested_category ＋ Vision secondary_damages；去重後截斷至 cap。
    候選形狀對齊插點 A（{id, label}）：分類候選 id 即 label（無獨立編號）。
    """
    labels: List[str] = []
    primary = (recognition.get("suggested_category") or "").strip()
    if primary:
        labels.append(primary)
    for extra in recognition.get("secondary_damages") or []:
        extra = (extra or "").strip()
        if extra and extra not in labels:
            labels.append(extra)
    labels = labels[:cap]
    return [{"id": label, "label": label} for label in labels]


async def resolve_repair_classification(
    recognition: Optional[Dict[str, Any]],
    jgb_api: Any,
) -> Optional[RepairClassification]:
    """用修繕分類樹把 Vision 名稱字串解析為 id（category_id/item_id/broken_reason）。

    Gap B：Vision suggested_category/suggested_item 是名稱，create_repair 要 int id；
    broken_reason 對齊分類樹 broken_reasons 的字串（create_repair mock 直接透傳字串）。

    回傳（單一真源，prefill 與 ingest 共用）：
      - dict（RepairClassification）：命中部分的 id/名稱；對不到的層不放（不硬塞）。
      - None：無 jgb_api／無辨識／分類樹查詢失敗／異常 → 呼叫端全數降級為顯示名候選（不拋錯）。

    名稱→id 匹配寬鬆化（含子字串雙向）：Vision 名稱（如「冷氣」）對分類樹（如「冷氣機」）
    仍能命中；對不到不硬塞。
    """
    if not recognition or jgb_api is None:
        return None
    try:
        resp = await jgb_api.get_repair_categories()
    except Exception:  # noqa: BLE001 — 面向可用性優先，分類樹失敗降級為候選、不阻斷對話
        logger.warning("[repair_prefill] get_repair_categories 例外，降級為顯示名候選",
                       exc_info=True)
        return None
    if not resp or not resp.get("success"):
        return None
    tree = resp.get("data")
    if not isinstance(tree, list):
        return None

    result: RepairClassification = {}
    cat_name = (recognition.get("suggested_category") or "").strip()
    item_name = (recognition.get("suggested_item") or "").strip()
    reason_name = (recognition.get("suggested_reason") or "").strip()

    category = _match_named(tree, cat_name)
    if category is None:
        return result  # 分類都對不到 → 無 id 可產（呼叫端留空/候選）
    result["category_id"] = category.get("id")
    result["category_name"] = category.get("name")

    item = _match_named(category.get("items") or [], item_name)
    if item is None:
        return result  # 只解到分類層
    result["item_id"] = item.get("id")
    result["item_name"] = item.get("name")

    reason = _match_reason(item.get("broken_reasons") or [], reason_name)
    if reason is not None:
        result["broken_reason"] = reason
    return result


def _match_named(rows: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """在具 name 欄位的節點清單中比對名稱（完全相等優先，其次子字串雙向）。"""
    if not name:
        return None
    for row in rows:
        if (row.get("name") or "").strip() == name:
            return row
    for row in rows:
        rn = (row.get("name") or "").strip()
        if rn and (rn in name or name in rn):
            return row
    return None


def _match_reason(reasons: List[str], name: str) -> Optional[str]:
    """broken_reasons 為字串清單；回符合的原字串（完全相等優先，其次子字串雙向）。"""
    if not name:
        return None
    for r in reasons:
        if (r or "").strip() == name:
            return r
    for r in reasons:
        rr = (r or "").strip()
        if rr and (rr in name or name in rr):
            return r
    return None


async def prefill_repair_slots(
    role_id: Optional[str],
    user_id: Optional[str],
    vendor_id: Any,
    image_recognition: Optional[Dict[str, Any]],
    config: Dict[str, Any],
    jgb_api: Any,
) -> PrefillResult:
    """修繕面向啟動時執行槽位預填。

    Args:
        role_id/user_id: 身份雙證（缺一由 API 層降級）。
        vendor_id: 業者識別（透傳，暫不參與分型；保留供未來業者差異化預填）。
        image_recognition: Vision 辨識結果（RecognitionResult dict）或 None（無圖/辨識失敗）；
            本模組不自己打 Vision，辨識由呼叫端做完傳入。
        config: 面向配置 grounding_scope dict——讀 inference_confidence/candidate_max/
            degraded_messages，均帶預設值。
        jgb_api: JGBSystemAPI 實例（get_tenant_contracts + get_repair_categories）。

    Returns:
        PrefillResult：slots（扁平標量 {value,source,confirmed}）、candidates（插點 A 形狀）、degraded。
    """
    config = config or {}
    slots: Dict[str, SlotValue] = {}
    candidates: Optional[List[Dict[str, Any]]] = None
    degraded: Optional[str] = None

    # ---- estate 預填（租約筆數分型）——扁平標量槽位 ----
    contracts = await _fetch_contracts(jgb_api, role_id, user_id)
    if not contracts:
        # 0 筆 / API 失敗 / 異常 → 同一降級路徑（面向仍可用，只是少預填）。
        degraded = _degraded_message(config)
    elif len(contracts) == 1:
        row = contracts[0]
        slots["estate_id"] = _slot(row.get("estate_id"), source="prefill")
        slots["contract_id"] = _slot(row.get("contract_id"), source="prefill")
        slots["estate_display"] = _slot(_estate_display(row), source="prefill")
    else:
        # N 筆 → 候選（插點 A 呈現讓使用者選一輪）。
        candidates = [_estate_candidate(r) for r in contracts]

    # ---- 分類三槽 + 急迫性推斷（Vision 信心分型，名稱→id 解析）----
    # 無圖/None → 分類槽位留空（詢問型，由 brain 開口問）；不覆蓋 estate 候選。
    resolved = await resolve_repair_classification(image_recognition, jgb_api)
    class_slots, class_candidates = classify_recognition(image_recognition, config,
                                                         resolved=resolved)
    slots.update(class_slots)
    if class_candidates:
        # estate 多租約與分類候選不會同時存在於單輪呈現（estate 先行選擇）；
        # 若已有 estate 候選則以其優先（多租約需先定位物件），分類候選讓引擎續輪處理。
        candidates = candidates or class_candidates

    return {"slots": slots, "candidates": candidates, "degraded": degraded}


def classify_recognition(
    image_recognition: Optional[Dict[str, Any]],
    config: Dict[str, Any],
    resolved: Optional[RepairClassification] = None,
) -> "Tuple[Dict[str, SlotValue], Optional[List[Dict[str, Any]]]]":
    """Vision 辨識結果 →（分類槽位, 候選）（門檻/分型的單一真源）。

    信心 ≥ inference_confidence（配置，預設 0.7）→ 分類槽位（source='inferred'）：
      - `resolved` 有 id（分類樹解析命中）→ 產 id 槽 `category_id`/`item_id`＋顯示槽
        `category`/`item`（confirm_template 用）＋ `broken_reason`（字串）。
      - `resolved` 對某層對不到 → 該 id 槽不產（不硬塞）；顯示槽仍以 Vision 名稱帶入
        （供 brain 開口確認）。
      - `resolved` 為 None（無 jgb_api／分類樹查詢失敗）→ 全數降級為顯示名候選（不硬塞 id）。
      - 急迫性推斷為 `emergency_status` 槽（對齊 required_slots/execute_params）。
    不足 → 退化為 ≤ candidate_max 候選（插點 A 形狀，不退三層下拉）；
    無圖/None → 空槽位、無候選（槽位轉詢問型）。

    prefill 面向啟動與續跑補圖（2.4）共用此函式——門檻邏輯不複製第二份。ingest 路徑若
    拿不到 jgb_api（resolved=None）則退化為顯示名候選，如實處理（不硬塞 id 進交易槽）。
    """
    config = config or {}
    slots: Dict[str, SlotValue] = {}
    if not image_recognition:
        return slots, None
    threshold = _as_float(config.get("inference_confidence"),
                          _DEFAULT_INFERENCE_CONFIDENCE)
    confidence = _as_float(image_recognition.get("confidence"), 0.0)
    cap = _as_int(config.get("candidate_max"), _DEFAULT_CANDIDATE_MAX)

    if confidence < threshold:
        class_candidates = _classification_candidates(image_recognition, cap)
        return slots, (class_candidates or None)

    # 信心足——但無分類樹解析（resolved=None）則不硬塞 id，降級為顯示名候選。
    if resolved is None:
        class_candidates = _classification_candidates(image_recognition, cap)
        return slots, (class_candidates or None)

    cat_name = image_recognition.get("suggested_category")
    item_name = image_recognition.get("suggested_item")

    # 分類 id 槽（對不到不產）；顯示槽 category 供 confirm_template {category}。
    if resolved.get("category_id") is not None:
        slots["category_id"] = _slot(resolved["category_id"], source="inferred")
        slots["category"] = _slot(resolved.get("category_name") or cat_name,
                                  source="inferred")
    # 損壞項目 id 槽 + 顯示槽 item。
    if resolved.get("item_id") is not None:
        slots["item_id"] = _slot(resolved["item_id"], source="inferred")
        slots["item"] = _slot(resolved.get("item_name") or item_name,
                              source="inferred")
    # broken_reason（字串本身即 create_repair 期待值＋ confirm_template 顯示）。
    if resolved.get("broken_reason"):
        slots["broken_reason"] = _slot(resolved["broken_reason"], source="inferred")

    emergency = image_recognition.get("suggested_emergency")
    if emergency is not None:
        slots["emergency_status"] = _slot(emergency, source="inferred")

    # 完全解不出任何 id（分類都對不到）→ 無交易槽可用，退化為顯示名候選讓使用者選。
    if not any(k in slots for k in ("category_id", "item_id")):
        class_candidates = _classification_candidates(image_recognition, cap)
        return slots, (class_candidates or None)
    return slots, None


async def _fetch_contracts(jgb_api: Any, role_id: Optional[str],
                           user_id: Optional[str]) -> List[Dict[str, Any]]:
    """呼 get_tenant_contracts，任何失敗（success=False/異常）→ 回空清單（視同 0 筆降級）。"""
    try:
        resp = await jgb_api.get_tenant_contracts(role_id=role_id, user_id=user_id)
    except Exception:  # noqa: BLE001 — 面向可用性優先，預填失敗不阻斷對話
        logger.warning("[repair_prefill] get_tenant_contracts 例外，降級為無預填",
                       exc_info=True)
        return []
    if not resp or not resp.get("success"):
        return []
    data = resp.get("data")
    return data if isinstance(data, list) else []


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
