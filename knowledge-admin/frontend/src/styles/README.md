# 管理頁樣式架構（2026-09-11 起）

## 為什麼要做

盤查 50 個 `.vue` 檔的實測：

| 指標 | 值 |
|---|---|
| `.vue` 總行數 | 45,530 |
| 其中 `<style>` | 19,512 行（**42%**） |
| 相異色值 | **359 個** |
| `.btn-primary` | 19 個檔、**15 種不同定義** |
| `.badge` | 19 個檔、13 種 |
| `.stat-value` | 16 個檔、14 種 |
| 出現在 ≥3 個檔的類別 | 107 個，合計 559 份定義 |

⇒ 同一個元件在不同頁長得不一樣；改一次按鈕要改十九個地方。

## 現在有什麼

- `tokens.css`——設計 token。⛔ **值全部取自現況最高頻的實際用色／間距，不是重新設計**。
- `components.css`——共用元件樣式。⛔ **每條取自「最多檔案採用」的那個變體**。

匯入順序在 `main.js`：`style.css` → `tokens.css` → `components.css`。

## ⚠️ 為什麼加了共用樣式，畫面卻沒變

單檔 `<style scoped>` 編譯後是 `.btn-primary[data-v-xxx]`，
specificity 高於這裡的裸 `.btn-primary` ⇒ **單檔定義永遠勝出**。

這是刻意的：加入基礎層本身**零視覺風險**。要讓共用定義生效，
必須逐檔刪掉該檔的重複區塊——而那一步**會改變外觀**，
因為該檔原本用的是 15 種變體之一。

## 已完成（外觀零變化）

第一批只刪「與正規定義**完全等價**」的重複區塊——刪掉後渲染結果相同：

| 類別 | 刪除份數 |
|---|---|
| `.form-group` / `.header-actions` | 各 7 |
| `.badge-easy` / `.badge-medium` / `.badge-hard` | 各 6 |
| `.stat-value` / `.stat-label` / `.retired-banner` | 各 2 |
| `.retired-notice` | 1 |

共 18 檔、39 個區塊。build exit 0；產出 CSS 285,268 → 283,144 bytes。

## ⛔ 還沒做的，以及為什麼停在這裡

剩下 19,372 行單檔 CSS、107 個跨檔重複類別（559 份定義）。
**它們不能機械合併**——`.btn-primary` 有 15 種定義，統一就是**選定一個外觀**、
同時改變 18 個頁面的樣子。那是產品／設計決定，⛔ 不是重構技術債。

要往下走，需要先定一件事：**以哪一版為準**。三種選法：

1. **最高頻變體為準**（`components.css` 現在就是這樣寫的）——改動最小，但「最多人用」不等於「最好看」。
2. **重新定義一套**——一致性最好，但 50 個頁面全部要目視驗收。
3. **只統一低風險元件**（badge／empty-state／form-group 這類純間距與狀態色），
   按鈕與彈窗這類佔畫面大的維持現狀。

⚠️ **驗證限制**：本機無 node，build 走 `docker run --rm node:20-alpine`。
build 過 **≠ 外觀正確**——⛔ 沒有任何自動檢查看得出「按鈕變成另一個綠色」。
統一變體那一步**必須有人目視驗收**，或先補視覺回歸測試。

## 怎麼 build

```
cd knowledge-admin/frontend
docker run --rm -v "$PWD":/app -w /app node:20-alpine \
  sh -c "npm install --no-audit --no-fund && npx vite build"
```
