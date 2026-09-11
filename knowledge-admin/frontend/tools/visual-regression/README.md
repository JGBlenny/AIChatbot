# 管理頁視覺回歸

## 為什麼需要它

2026-09-11 做樣式收斂時，我用「宣告層等價檢查」證明了外觀不會變——
**230 組全部等價、0 例外，還附了突變正對照**。然後用瀏覽器實跑，
**10 頁裡 6 頁真的變了**，最嚴重一頁差 5.77% 像素。

根因：把共用規則放進**全域** stylesheet，會影響那些**從未定義該類別**的檔案。
宣告層檢查只比對「有定義的檔案」，看不到這種外溢。
具體例：`.page-header` 的 `display` 從 `block` 變成 `flex`，
因為某個檔案根本沒設 `.page-header`，卻被全域規則接管。

⛔ **教訓：CSS 的正確性在「渲染結果」，不在「宣告集合」。靜態比對證明不了外觀不變。**

## 怎麼用

```bash
cd knowledge-admin/frontend
# 1) 基準：把改動前的版本 build 到別處
git archive <改動前的 commit> knowledge-admin/frontend | tar -x -C /tmp/base --strip-components=2
ln -s "$PWD/node_modules" /tmp/base/node_modules
docker run --rm -v /tmp/base:/app -v "$PWD/node_modules":/app/node_modules -w /app \
  node:20-alpine npx vite build

# 2) 現況
docker run --rm -v "$PWD":/app -w /app node:20-alpine npx vite build

# 3) 兩版各截圖，再像素比對
docker run --rm -v "$PWD/tools/visual-regression":/vis \
  -v "$PWD/dist":/cur:ro -v /tmp/base/dist":/base:ro -w /vis \
  mcr.microsoft.com/playwright:v1.49.1-jammy sh -c \
  "node shot.mjs /base /vis/shots-base 5011 /vis/routes.json && \
   node shot.mjs /cur  /vis/shots-cur  5012 /vis/routes.json"
```

`computed.mjs` 是定位工具：兩版各 dump 一頁所有元素的 computed style ＋ boundingRect，
比對後直接指出「哪個元素的哪個屬性變了」。⚠️ 像素比對告訴你**有沒有變**，
computed 比對告訴你**變在哪**，兩個都要。

## ⚠️ 已知限制

- `routes.json` 只列 10 條路由，⛔ **不是全覆蓋**（管理頁有 41 條路由）。
  ⚠️ 路由是 `createWebHistory`（⛔ 不是 hash 模式），路徑直接接在 host 後面。
- 截圖時 `localStorage.auth_token` 塞假值過路由守衛（守衛只看 `!!token`）。
  部分頁另有權限檢查，仍會導去登入頁——**截圖大小全都一樣就是這個症狀**。
- 後端 API 不在時頁面會是空狀態；**這對樣式比對無妨**（兩版條件相同），
  但⛔ 驗不到有資料時的版面。
