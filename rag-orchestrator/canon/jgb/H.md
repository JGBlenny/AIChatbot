---
coarse: H
title: 幫助中心
scope: 幫助中心入口與使用方式、教學文件位置；⛔ 各功能怎麼用歸該功能所在架（目前空架，存廢另裁）
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 幫助中心（分類、文章、搜尋） {#H-help-center}
### 幫助中心首頁長什麼樣？（分類卡片顯示圖示、篇數、更新日期） {#jgb/H/help-center-home-groups}
- phrasings:
  - {text: "幫助中心首頁有什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心分類怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心怎麼進去", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心有哪些分類", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/help-center/Index.vue, code:src/pages/help-center/template-parts/Top.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
幫助中心首頁會列出所有分類卡片，每張卡片顯示分類圖示、標題、這個分類底下有幾篇文章，以及最後更新日期。
點一張分類卡片會進入該分類頁面。
頁面最上方可以切換語系，也有一個連結可以直接返回 JGB Smart Property 首頁。
### 幫助中心分類頁怎麼排文章？（分類底下先分次分類，各次分類再列出文章卡片） {#jgb/H/help-center-group-structure}
- phrasings:
  - {text: "幫助中心分類頁長怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心文章怎麼分組", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心次分類是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/help-center/Group.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
分類頁最上面重複顯示這個分類的圖示、篇數與更新日期，下面再依次分類分組列出文章。
每個次分類會顯示標題，底下才是這個次分類的文章卡片列表；一篇文章只會出現在它所屬的那個次分類底下。
沒有任何文章的次分類不會顯示出來。
每張文章卡片顯示標題、摘要與更新日期，點了會進入該篇文章內頁。
### 幫助中心文章內頁有什麼？（麵包屑、分享到 Facebook／LINE、上下篇導覽、相關文章） {#jgb/H/help-center-post-detail}
- phrasings:
  - {text: "幫助中心文章怎麼分享", source: "draft:outline-20260920", status: proposed}
  - {text: "文章頁有上一篇下一篇嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "文章內頁長什麼樣", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼回到分類列表", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/help-center/Post.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
文章內頁上方有麵包屑，依序是所有系列、這篇文章所屬的分類、文章標題，點分類名稱可以直接跳回該分類頁。
標題旁邊有分享到 Facebook 跟分享到 LINE 兩個按鈕。
文章內容下方有上一篇、下一篇的導覽，沒有上一篇或下一篇時該側就不會顯示連結。
文章最下面會列出相關文章主題，點了會換頁到另一篇文章。
### 幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類） {#jgb/H/help-center-search}
- phrasings:
  - {text: "幫助中心搜尋規則", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心搜不到文章怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心可以打多個關鍵字嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "幫助中心搜尋能限定分類嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/help-center/template-parts/Top.vue, code:src/pages/help-center/Search.vue, code:app/Http/Controllers/IndexController.php]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
在幫助中心首頁上方的搜尋框輸入關鍵字並選擇分類（可留空），送出後會跳到搜尋結果頁。
搜尋是比對文章的標題加內文，如果輸入的關鍵字之間有空格，會被拆成多個關鍵字，一篇文章要同時包含全部關鍵字才算符合。
有選分類時，只會在該分類底下的文章找；沒有輸入任何關鍵字就送出搜尋，會直接被導回幫助中心首頁。
搜尋不到結果時會顯示找不到任何關於此項目的文章，並附上返回幫助中心首頁的連結。
### 幫助中心的「立即免費試用」視窗是什麼時候跳出來的？（首頁停留 60 秒自動彈出，四個欄位都要填） {#jgb/H/help-center-trial-form}
- phrasings:
  - {text: "幫助中心會跳出試用視窗嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "免費試用視窗要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼關掉試用彈窗", source: "draft:outline-20260920", status: proposed}
  - {text: "免費試用天數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/entry/listings.js, code:src/pages/help-center/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
在幫助中心首頁停留滿 60 秒沒有離開這個頁面，就會自動彈出「立即免費試用 JGB Smart Property」的視窗，寫著現在註冊享有免費試用 30 天。
這個 60 秒計時只有在網址名稱完全等於幫助中心首頁時才會啟動；進到某個分類頁、文章頁或搜尋結果頁之後，都不會觸發這個彈窗。
視窗要求填公司名/姓名、電話、Email、簡述您有興趣的原因四個欄位，四個都填了才能送出。
視窗右上角有一個關閉按鈕可以直接關掉，不強制填寫。
