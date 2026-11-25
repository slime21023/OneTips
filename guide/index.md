# 認識 OneTips

> 用一份 Markdown 維護技術 Tips：人在 GitHub 上直接讀，Coding Agent 依任務只載入需要的章節。

## OneTips 聚焦解決什麼問題

團隊累積技術慣例、架構規範與局部程式碼樣板時，通常會遇到三個痛點：

1. **文件與 Agent 知識庫分家**：寫給人看的 Wiki／README 篇幅太長，Coding Agent 一次載入耗費大量 context；另外寫給 Agent 的規則檔又常和人類文件脫節。
2. **目錄與範例容易腐壞**：手動維護的索引常漏列或連結失效，文件裡的程式碼範例隨版本演進失效卻沒人發現。
3. **跨專案共用困難**：把規範複製貼上到各個 repo 後難以追蹤版本，且容易誤套用到版本不符或已有既有慣例的專案。

OneTips 透過「**單一 Markdown 來源＋固定結構＋自動索引＋自足 Agent Skill 封裝**」一次解決這三個問題。

---

## 核心特性與提供的功能

| 特性／功能 | 說明 |
| --- | --- |
| **一題一篇、固定四章節** | 每篇 Tip 放在 `references/<id>.md`，固定包含適用情境（`when`）、推薦做法（`approach`）、常見陷阱（`pitfalls`）與可審查的檢查清單（`checklist`）。 |
| **自動產生索引（`onetips index`）** | Markdown 是唯一來源，`INDEX.md` 由 front matter 確定性生成，並附 `Sections` 對照表（支援在地化章節標題）。 |
| **結構與連結驗證（`onetips check`）** | 檢查設定檔、front matter、章節順序、checklist、相對路徑連結、標題錨點、skill 自足性與索引是否過期。 |
| **程式碼片段驗證（`onetips snippets`）** | 依 `status=compiled`／`tested` 執行作者配置的編譯與測試指令，確保薄樣板與範例持續有效。 |
| **自足 Agent Skill 封裝** | `skills/<name>/` 包含 `SKILL.md`、`INDEX.md` 與 `references/`，可直接透過 `bunx skills add` 安裝到其他 repo，不依賴原始專案。 |
| **有／無 CLI 皆可查閱** | 可用 `onetips find` / `onetips show` 結構化查詢；即使目標環境沒有 OneTips CLI、Python 或 `mq`，也能直接讀 `INDEX.md` 與 Markdown 定位章節。 |
| **尊重目標專案優先權** | `SKILL.md` 協定要求 Agent 先檢查目標專案版本與既有規則，不覆蓋專案既定決策。 |

> [!NOTE]
> OneTips 框架本身不綁定或內建特定技術的教學內容；領域、分類、適用版本與驗證指令皆由各 Tips 專案在 `onetips.yaml` 自行定義。

---

## 閱讀與實作順序

1. **[建立與維護 Tips](authoring.md)** — 從 `init`、`new` 到 `index`、`check`、`snippets` 的完整作者流程。
2. **[安裝與查閱（含無 CLI 流程）](installing.md)** — 本機與 Git tag 安裝、查詢實際安裝路徑、`verify`、`find`/`show`，以及無工具純文字查閱。
3. **[格式速查](format-reference.md)** — `onetips.yaml`、front matter、四章節與程式碼片段狀態的快速對照。
4. **[常見問題與排查](troubleshooting.md)** — 索引過期、安裝不完整、連結越界與 `snippets` 安全邊界處理。
