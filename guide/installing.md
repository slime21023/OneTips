# 安裝與查閱（含無 CLI 流程）

本頁說明如何在**另一個目標專案 repo** 安裝已建立好的 Tips skill、確認安裝完整性，以及在「有 CLI」與「完全無 CLI／無 Python／無 `mq`」兩種環境下查閱內容。

---

## 步驟 1：安裝 Skill（在目標專案 repo 根目錄執行）

### 方式 A：從本機路徑安裝（開發測試用）

```bash
# 執行位置：目標專案 repo 根目錄
bunx skills add "/path/to/my-tips" --skill my-tips --copy -y
```

### 方式 B：從公開 Git tag 安裝（建議正式使用）

將 `<owner>`、`<repo>`、`<tag>` 與 `<skill-name>` 替換為實際 Tips 專案的公開來源與不可變 tag（請勿假設該專案已發布到 registry）：

```bash
# 執行位置：目標專案 repo 根目錄
bunx skills add "https://github.com/<owner>/<repo>#<tag>" --skill <skill-name> --copy -y
```

> [!TIP]
> 若想立刻用 OneTips 內建的公開範例 tag 實測，可在空的暫存 git repo 執行：
> ```bash
> bunx skills add "https://github.com/slime21023/OneTips#ac4-fixture-v1" --skill acme-tips -a claude-code --copy -y
> ```

---

## 步驟 2：取得實際安裝路徑並驗證（在目標專案 repo 根目錄執行）

不同 Agent 工具會把 skill 放在不同資料夾（例如 `.claude/skills/<name>`）。先用 `skills list --json` 查出實際安裝路徑：

```bash
# 執行位置：目標專案 repo 根目錄
bunx skills list --json
```

確認輸出中該 skill 的 `status` 為 `"tracked"`，並記下 `path` 欄位的值（以下記為 `<installed-skill-dir>`）。接著執行 `onetips verify`：

```bash
# 執行位置：目標專案 repo 根目錄
onetips verify "<installed-skill-dir>"
```

驗證通過時會輸出與 `skills-lock.json`（v2）相容的雜湊值：

```text
computedHash: <64-hex-sha256>
```

確認此雜湊值與 `skills-lock.json` 中對應項目的 `computedHash` 一致，即代表 `SKILL.md`、`INDEX.md` 與整個 `references/` 皆完整複製且無越界連結。

---

## 步驟 3A：使用 OneTips CLI 結構化查詢（選用）

在目標環境有安裝 `onetips` 時，可只讀索引或只擷取單一章節與片段：

```bash
# 依分類、標籤或關鍵字搜尋索引（不掃描 references/）
onetips find --skill-dir "<installed-skill-dir>" --tag retry --json
onetips find --skill-dir "<installed-skill-dir>" --category networking

# 讀取單篇 Tip 的 metadata
onetips show --skill-dir "<installed-skill-dir>" retry-with-backoff --metadata --json

# 只讀取單一章節（例如 checklist，會自動透過 INDEX.md 的 Sections 對照在地化標題）
onetips show --skill-dir "<installed-skill-dir>" retry-with-backoff --section checklist

# 只擷取特定語言與驗證狀態的程式碼片段（不執行程式碼）
onetips show --skill-dir "<installed-skill-dir>" retry-with-backoff --section approach --code --lang python --status tested --json
```

---

## 步驟 3B：無 OneTips CLI、無 Python、無 `mq` 的純文字查閱

OneTips 刻意不要求目標 repo 安裝任何工具。沒有 CLI 時，人類讀者或 Coding Agent 只需直接讀檔案即可：

1. **先讀 `<installed-skill-dir>/SKILL.md`**：確認操作協定（先檢查目標專案版本與既有慣例，再查 Tip，不覆蓋專案決策）。
2. **開啟 `<installed-skill-dir>/INDEX.md`**：
   - 依 `Tags`、`Summary` 或分類標題找到目標列，取得 `ID` 欄的相對路徑（例如 `references/retry-with-backoff.md`）。
   - 比對 `Applies to` 欄，確認目標專案版本落在適用範圍內。
   - 查看檔頭的 `### Sections` 對照表，找出 `checklist` 對應的實際標題，例如：
     ```markdown
     ### Sections

     - `when`: When to Use
     - `approach`: Recommended Approach
     - `pitfalls`: Pitfalls
     - `checklist`: 檢查清單
     ```
3. **只讀需要的章節**：打開 `references/retry-with-backoff.md`，直接跳到對應的真實 H2 標題（例如 `## 檢查清單`，略過程式碼圍欄內看起來像標題的文字），逐項核對 `- [ ]` 項目即可。
