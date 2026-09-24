# H 架草稿（jgb2 master @ b2ee2ac382ce；粗目 1、細目 5、句 19）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 幫助中心（分類、文章、搜尋）（5 條；頁：web:/help/{any?}/{slug?}、listings.helpCenter、listings.helpCenter.group、listings.helpCenter.post、listings.helpCenter.search）

### 幫助中心首頁長什麼樣？（分類卡片顯示圖示、篇數、更新日期）
- 講法：幫助中心首頁有什麼／幫助中心分類怎麼看／幫助中心怎麼進去／幫助中心有哪些分類
- 給誰看：property_manager、prospect
- 幫助中心首頁會列出所有分類卡片，每張卡片顯示分類圖示、標題、這個分類底下有幾篇文章，以及最後更新日期。〔src/pages/help-center/Index.vue〕
- 點一張分類卡片會進入該分類頁面。〔src/pages/help-center/Index.vue〕
- 頁面最上方可以切換語系，也有一個連結可以直接返回 JGB Smart Property 首頁。〔src/pages/help-center/template-parts/Top.vue〕

### 幫助中心分類頁怎麼排文章？（分類底下先分次分類，各次分類再列出文章卡片）
- 講法：幫助中心分類頁長怎樣／幫助中心文章怎麼分組／幫助中心次分類是什麼
- 給誰看：property_manager、prospect
- 分類頁最上面重複顯示這個分類的圖示、篇數與更新日期，下面再依次分類分組列出文章。〔src/pages/help-center/Group.vue〕
- 每個次分類會顯示標題，底下才是這個次分類的文章卡片列表；一篇文章只會出現在它所屬的那個次分類底下。〔src/pages/help-center/Group.vue〕
- 沒有任何文章的次分類不會顯示出來。〔src/pages/help-center/Group.vue〕
- 每張文章卡片顯示標題、摘要與更新日期，點了會進入該篇文章內頁。〔src/pages/help-center/Group.vue〕
- 否定查證：`{'grep': 'grep -cF "v-show=\\"!isEmpty(subGroup.posts)\\"" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/help-center/Group.vue)', 'expected_zero': False, 'result': 1, 'control': 'grep -cF "v-html=\\"post.excerpt\\"" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/help-center/Group.vue) 命中，證明檔案裡文章卡片與 v-show 判斷式在同一份模板中對得起來'}`

### 幫助中心文章內頁有什麼？（麵包屑、分享到 Facebook／LINE、上下篇導覽、相關文章）
- 講法：幫助中心文章怎麼分享／文章頁有上一篇下一篇嗎／文章內頁長什麼樣／怎麼回到分類列表
- 給誰看：property_manager、prospect
- 文章內頁上方有麵包屑，依序是所有系列、這篇文章所屬的分類、文章標題，點分類名稱可以直接跳回該分類頁。〔src/pages/help-center/Post.vue〕
- 標題旁邊有分享到 Facebook 跟分享到 LINE 兩個按鈕。〔src/pages/help-center/Post.vue〕
- 文章內容下方有上一篇、下一篇的導覽，沒有上一篇或下一篇時該側就不會顯示連結。〔src/pages/help-center/Post.vue〕
- 文章最下面會列出相關文章主題，點了會換頁到另一篇文章。〔src/pages/help-center/Post.vue〕
- 否定查證：`{'grep': 'grep -cF "v-if=\\"state?.next_post?.slug\\"" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/help-center/Post.vue)', 'expected_zero': False, 'result': 1, 'control': 'grep -cF "v-if=\\"state?.prev_post?.slug\\"" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/help-center/Post.vue) 命中 1 筆，確認上一篇／下一篇連結都各自有條件式控制顯示'}`

### 幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類）
- 講法：幫助中心搜尋規則／幫助中心搜不到文章怎麼辦／幫助中心可以打多個關鍵字嗎／幫助中心搜尋能限定分類嗎
- 給誰看：property_manager、prospect
- 在幫助中心首頁上方的搜尋框輸入關鍵字並選擇分類（可留空），送出後會跳到搜尋結果頁。〔src/pages/help-center/template-parts/Top.vue〕
- 搜尋是比對文章的標題加內文，如果輸入的關鍵字之間有空格，會被拆成多個關鍵字，一篇文章要同時包含全部關鍵字才算符合。〔app/Http/Controllers/IndexController.php〕
- 有選分類時，只會在該分類底下的文章找；沒有輸入任何關鍵字就送出搜尋，會直接被導回幫助中心首頁。〔src/pages/help-center/Search.vue〕
- 搜尋不到結果時會顯示找不到任何關於此項目的文章，並附上返回幫助中心首頁的連結。〔app/Http/Controllers/IndexController.php〕
- 否定查證：`{'grep': 'grep -n "^\\s*//.*我們找不到任何關於此項目的文章" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/IndexController.php)', 'expected_zero': False, 'result': 1, 'control': 'grep -nF "\\$result[\'message\'] = ___(\'我們找不到任何關於此項目的文章\');" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/IndexController.php) 命中第 928 行，確認引用的是真的會被執行的那一行，不是第 799 行被註解掉的舊碼'}`

### 幫助中心的「立即免費試用」視窗是什麼時候跳出來的？（首頁停留 60 秒自動彈出，四個欄位都要填）
- 講法：幫助中心會跳出試用視窗嗎／免費試用視窗要填什麼／怎麼關掉試用彈窗／免費試用天數
- 給誰看：property_manager、prospect
- 在幫助中心首頁停留滿 60 秒沒有離開這個頁面，就會自動彈出「立即免費試用 JGB Smart Property」的視窗，寫著現在註冊享有免費試用 30 天。〔src/pages/help-center/Index.vue〕
- 這個 60 秒計時只有在網址名稱完全等於幫助中心首頁時才會啟動；進到某個分類頁、文章頁或搜尋結果頁之後，都不會觸發這個彈窗。〔src/entry/listings.js〕
- 視窗要求填公司名/姓名、電話、Email、簡述您有興趣的原因四個欄位，四個都填了才能送出。〔src/pages/help-center/Index.vue〕
- 視窗右上角有一個關閉按鈕可以直接關掉，不強制填寫。〔src/pages/help-center/Index.vue〕
- 否定查證：`{'grep': 'grep -n "listings.helpCenter\\." <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/entry/listings.js)', 'expected_zero': True, 'result': 0, 'control': 'grep -nF "1000 * 60 * 1" <(git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/entry/listings.js) 命中 1 筆，確認計時是 60 秒'}`
- ⚠️ 待查：`if ('listings.helpCenter'.includes(route.name))` 這個判斷式是固定字串 'listings.helpCenter'.includes(變數)，只有 route.name 完全等於 'listings.helpCenter'（或是它的子字串）時才會成立；'listings.helpCenter.group'／'.post'／'.search' 這些子頁面的路由名稱反而不會命中。這看起來像是原本想寫成 route.name.includes('listings.helpCenter')（涵蓋所有幫助中心子頁）卻寫反了，還是刻意只在首頁觸發，需業主確認，關係到這句話要不要修正成『所有幫助中心頁面都會倒數』。
