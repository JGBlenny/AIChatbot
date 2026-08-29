#!/usr/bin/env python3
"""不變量 11：routing authority 的 **producer-consumer transport contract**。

**源起**（2026-08-29，A03 抓到的 integration false-green）：
P1f 的 gate 讀 knowledge 的 applicability 宣告來決定是否抑制面向進場，
consumer 已接線、契約已存在——但 `VendorKnowledgeRetrieverV2` 回傳的知識列
**根本沒有那個欄位**。⇒ production 上 109/109 案例一律讀到 UNKNOWN、一律 suppress。

⚠️ 而 P1f 的 **23 條單元測試全過**，因為它們餵的是手寫
`{"generation_metadata": {...}}`——**production 從不產生的形狀**。

```text
nomination ≠ authority｜select=api ≠ capability equivalence
有資料流 ≠ 流到正確語義槽位｜**fixture 有資料 ≠ production 有資料**
共同形狀：**形式上有接線，不等於語義上接對。**
```

## 不變量陳述（產品層，與欄位名解耦）

> **任何 routing authority consumer 所需的 semantic contract，
> 必須由其 production producer shape 明示提供；
> ⛔ fixture 不得擁有 production producer 不可能提供的 authority 欄位。**

## 機器判定（一般化，⛔ 不只守單一欄位）

```text
consumer  services/instance_applicability.py 內從「知識列」讀取的鍵
          （AST 取 `row.get("...")` / `knowledge.get("...")` 的字面鍵）
producer  VendorKnowledgeRetrieverV2._format_result 回傳 dict 的鍵集合
不變量    consumer 讀取的鍵 ⊆ producer 提供的鍵
豁免      `generation_metadata` —— 明文標記為**非 production transport shape**
          的相容備援（見契約模組註解），⛔ 不得作為 wiring 證明
```

用法：python3 scripts/audit/checks/authority_transport_contract.py [--self-test]
"""
import ast
import os
import sys
import textwrap

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CONSUMER = "rag-orchestrator/services/instance_applicability.py"
PRODUCER = "rag-orchestrator/services/vendor_knowledge_retriever_v2.py"
PRODUCER_FUNC = "_format_result"
#: 明文豁免：相容備援，⛔ 不得作為 production wiring 證明
COMPAT_ONLY = {"generation_metadata"}


def _module_str_constants(tree) -> dict:
    """模組層 `NAME = "literal"` 的對照表。

    ⚠️ 沒有這一段，`row.get(TRANSPORT_FIELD)` 這種**常數間接**會被整個漏掉——
    本檢查器第一版就是這樣讓正對照失敗的（同不變量 8 記過的「變數間接」規避型）。
    """
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node.value.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and isinstance(node.target, ast.Name):
            out[node.target.id] = node.value.value
    return out


def consumer_row_keys(src: str) -> set:
    """AST 取 consumer 從知識列讀取的鍵——**含常數間接**。"""
    tree = ast.parse(src)
    consts = _module_str_constants(tree)
    keys = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args):
            base = node.func.value
            if not (isinstance(base, ast.Name) and base.id in ("row", "knowledge")):
                continue          # 只收「從知識列讀」，⛔ 不收 scope/config 等其他物件
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.add(arg.value)
            elif isinstance(arg, ast.Name) and arg.id in consts:
                keys.add(consts[arg.id])
    return keys


def producer_row_keys(src: str, func_name: str) -> set:
    """AST 取 producer 回傳 dict 的鍵集合。"""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            keys = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    for k in sub.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
            return keys
    return set()


def violations(consumer_keys, producer_keys):
    return sorted((consumer_keys - COMPAT_ONLY) - producer_keys)


def self_test() -> int:
    cases = []
    c = consumer_row_keys('def f(row):\n    return row.get("a"), row.get("b")\n')
    cases.append(("consumer 鍵抽取（字面）", c == {"a", "b"}))
    ci = consumer_row_keys('K = "kk"\ndef f(row):\n    return row.get(K)\n')
    cases.append(("consumer 鍵抽取（**常數間接**）", ci == {"kk"}))
    p = producer_row_keys('def _format_result(self, row):\n    return {"a": 1, "c": 2}\n',
                          "_format_result")
    cases.append(("producer 鍵抽取", p == {"a", "c"}))
    cases.append(("缺鍵必須紅", violations({"a", "b"}, {"a"}) == ["b"]))
    cases.append(("齊備不得誤報", violations({"a"}, {"a", "c"}) == []))
    cases.append(("相容備援鍵豁免", violations({"generation_metadata"}, set()) == []))
    # ⚠️ 正對照：把真實 consumer 的 transport 欄位從 producer 拿掉，必須被抓到
    real_c = consumer_row_keys(open(os.path.join(REPO, CONSUMER), encoding="utf-8").read())
    real_p = producer_row_keys(open(os.path.join(REPO, PRODUCER), encoding="utf-8").read(),
                               PRODUCER_FUNC)
    planted = violations(real_c, real_p - {"knowledge_instance_applicability"})
    cases.append(("植入缺漏（移除 transport 欄位）必須被抓到",
                  "knowledge_instance_applicability" in planted))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    c = consumer_row_keys(open(os.path.join(REPO, CONSUMER), encoding="utf-8").read())
    p = producer_row_keys(open(os.path.join(REPO, PRODUCER), encoding="utf-8").read(),
                          PRODUCER_FUNC)
    if not c or not p:
        print("❌ FAIL：consumer 或 producer 鍵集合為空——大聲失敗，不當成「沒有違規」")
        return 1
    bad = violations(c, p)
    if bad:
        print("❌ FAIL：authority consumer 讀取的鍵，production producer **沒有提供**：")
        for k in bad:
            print(f"   {k}")
        print("   ⇒ contract 存在但 transport 斷了；⛔ fixture 過關不代表 production 過關")
        return 1
    print(f"（consumer 讀 {sorted(c - COMPAT_ONLY)}；producer 提供 {len(p)} 個鍵；"
          f"相容備援豁免 {sorted(COMPAT_ONLY)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
