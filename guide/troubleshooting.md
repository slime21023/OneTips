# 常見問題與排查

本頁整理使用 OneTips 建立、驗證、安裝與執行片段時最常遇到的錯誤碼與排查方式。

---

## 1. 索引過期（`E-INDEX-STALE`）

**症狀**：執行 `onetips check` 或 `onetips index --check` 失敗並回報 `E-INDEX-STALE`。

**原因**：新增、刪除或修改了任一篇 Tip 的 front matter、H1 標題、程式碼片段數量，或修改了 `onetips.yaml` 的分類／章節標題，但尚未重新產生 `INDEX.md`。

**解法**：在 Tips 專案根目錄執行：

```bash
onetips index --check   # 先檢視差異（不寫檔）
onetips index           # 重新產生 INDEX.md
onetips check           # 確認回到 0 errors
```

> 請勿手動編輯 `INDEX.md`；每次修改 Tip 後都應交由 `onetips index` 確定性重建。

---

## 2. 遺失 `references/` 或安裝不完整（`E-LINK-BROKEN`、`E-INDEX-MISSING-ENTRY`）

**症狀**：
- 在目標 repo 執行 `onetips verify "<installed-skill-dir>"` 時出現 `E-LINK-BROKEN`（例如 `missing indexed reference: ...`）或 `E-INDEX-MISSING-ENTRY`。
- 或是 `onetips show` 回報找不到對應的參考檔。

**常見原因與排查**：
1. **安裝時未完整複製整個 skill 目錄**：只複製了 `SKILL.md` 而遺漏 `INDEX.md` 或 `references/`。
   - **解法**：使用 `bunx skills add <source> --skill <name> --copy -y` 重新安裝，並以 `bunx skills list --json` 確認 `status` 為 `"tracked"` 後重跑 `onetips verify`。
2. **來源專案本身索引與檔案不同步**：作者新增或刪除了 `references/*.md` 但忘記執行 `onetips index`。
   - **解法**：回到來源 Tips 專案執行 `onetips index && onetips check`，重新提交並打新 tag。
3. **在 `references/` 下建了子目錄或非小寫 `.md` 檔**：OneTips 要求所有 Tip 都是 `references/` 下的直屬一般 `.md` 檔案。

---

## 3. 連結逃出 Skill 範圍（`E-LINK-ESCAPES-SKILL`）與無效錨點（`E-LINK-ANCHOR`）

**症狀**：`onetips check` 或 `onetips verify` 回報 `E-LINK-ESCAPES-SKILL` 或 `E-LINK-ANCHOR`。

**原因與解法**：
- **`E-LINK-ESCAPES-SKILL`**：`skills/<name>/` 內的檔案使用了 `../../README.md`、絕對路徑或指向外部的符號連結。因為下游安裝時只會複製 `skills/<name>/`，外部檔案安裝後必成死鏈。請將必要參考內容移入 `skills/<name>/` 內，或改用外部 `https://` 連結。
- **`E-LINK-ANCHOR`**：`#fragment` 無法對應目標 Markdown 的 GitHub 標題 slug 或 `<a id="...">` 標籤。請核對目標標題文字（特別留意標點與大小寫）。

---

## 4. 符號連結遭拒（`E-INDEX-FORMAT`、`E-READ`）

**症狀**：回報 `index must not be a symbolic link` 或 `expected a plain project directory`。

**原因**：為避免 `skills` 複製或雜湊比對時發生路徑逃逸，`skills/`、`skills/<name>/`、`references/`、`INDEX.md` 與每篇 Tip 都必須是一般目錄或一般檔案，不可為 symlink／junction。請改為實體檔案後重跑檢查。

---

## 5. 程式碼片段驗證失敗與信任邊界（`E-SNIPPET-FAILED`、`E-SNIPPET-NO-COMMAND`）

- **`E-SNIPPET-NO-COMMAND`**：某段程式碼標記了 `status=compiled` 或 `status=tested`，但 `onetips.yaml` 的 `snippets.<lang>` 未設定對應的 `compile` 或 `test` 指令。請補上指令，或將該片段改為預設（省略 `status=` 即 `unverified`）。
- **`E-SNIPPET-FAILED`**：每個 fence 會被**獨立擷取**到暫存檔並在專案根目錄執行。請確認片段本身自足（不依賴同一篇 Tip 裡其他 fence 的變數或 `import`），且本機環境已安裝對應語言工具鏈。
- **安全提醒**：`onetips snippets` **沒有沙箱**，會直接執行 `onetips.yaml` 指定的命令與擷取程式碼；**切勿對不信任的第三方 Tips 專案執行 `onetips snippets`**（請僅對不信任來源執行唯讀的 `check`、`verify`、`find`、`show`）。
