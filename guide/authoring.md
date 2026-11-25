# 建立與維護 Tips

本頁提供從零建立一個 Tips 專案、撰寫第一篇 Tip 到驗證完成的完整可複製流程。每個步驟都會標示**應在哪一個 repo／目錄執行**。

> [!IMPORTANT]
> OneTips 目前為開發版，**尚未發布到 PyPI**，請先從本機原始碼安裝 CLI。

---

## 步驟 1：安裝 OneTips CLI（在 OneTips 原始碼目錄執行）

```bash
# 執行位置：OneTips 框架原始碼根目錄
uv tool install .
onetips --version
```

若不想全域安裝，也可改用 `uv run --project /path/to/OneTips --locked onetips ...` 執行。

---

## 步驟 2：初始化 Tips 專案（在要建立專案的上層目錄執行）

```bash
# 執行位置：欲建立新 Tips 專案的上層目錄
onetips init my-tips --name my-tips
cd my-tips
```

`init` 會建立以下結構：

```text
my-tips/
├── README.md
├── onetips.yaml
└── skills/my-tips/
    ├── SKILL.md
    ├── INDEX.md
    └── references/
```

建立後，可編輯 `onetips.yaml` 調整：
- `domain`：領域顯示名稱
- `subjects`：版本主體 ID 與顯示名稱（例如 `acme-sdk: Acme SDK`）
- `categories`：分類清單（至少一個）
- `sections`：四個固定章節的顯示標題（可在地化，如將 `checklist` 設為 `檢查清單`）
- `snippets`（選填）：各語言的 `ext`、`compile`、`test` 指令與 `timeout`

---

## 步驟 3：建立草稿並撰寫 Tip（在你的 Tips 專案根目錄執行）

```bash
# 執行位置：你的 Tips 專案根目錄（my-tips/）
onetips new first-tip --category general
```

`new` 會在 `skills/my-tips/references/first-tip.md` 建立草稿，**不會修改 `INDEX.md`**。

打開 `skills/my-tips/references/first-tip.md`，補齊以下內容（欄位規格見[格式速查](format-reference.md)）：
1. YAML front matter 的 `summary`、`tags`、`applies_to`（與選填 `related`）。
2. 唯一的 H1 標題（`# ...`）。
3. 四個固定順序的 H2 章節，並在最後的 checklist 至少寫入一個 `- [ ] ...` 項目。
4. 程式碼區塊的第一個詞必須是語言標籤，可選擇加上 `status=compiled` 或 `status=tested`（省略視為 `unverified`）。

---

## 步驟 4：產生索引並執行驗證（在你的 Tips 專案根目錄執行）

```bash
# 執行位置：你的 Tips 專案根目錄（my-tips/）
onetips index
onetips index --check
onetips check
onetips snippets
```

各指令用途：
- `onetips index`：依所有 Tip 的 metadata 確定性重建 `skills/<name>/INDEX.md`（請勿手動編輯 `INDEX.md`）。
- `onetips index --check`：不寫檔，檢查 `INDEX.md` 是否過期並輸出 unified diff（適合放在 CI）。
- `onetips check`：檢查設定、front matter、章節結構、相對連結、標題錨點、skill 自足性與索引新鮮度。
- `onetips snippets`：依 `onetips.yaml` 的設定執行標記為 `compiled` 與 `tested` 的程式碼片段；也可用 `onetips snippets --id first-tip` 只驗證單篇。

> [!WARNING]
> **`snippets` 的信任邊界**：`onetips snippets` 會以你的系統權限直接執行 `onetips.yaml` 設定的 shell 指令與擷取出的程式碼（**無沙箱隔離**）。**請只在你信任的 Tips 專案執行 `snippets`**。相對地，`check`、`verify`、`find` 與 `show` 永遠不會執行任何範例程式碼。

---

## 步驟 5：推送與標記版本（在你的 Tips 專案根目錄執行）

確認所有檢查回報 `0 errors` 後，提交所有檔案（包含產生的 `INDEX.md`），並以不可變的 Git tag 發布版本供下游 repo 安裝：

```bash
# 執行位置：你的 Tips 專案根目錄（my-tips/）
git add .
git commit -m "feat: add first-tip"
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main --tags
```

接下來可至[安裝與查閱](installing.md)了解如何在另一個目標 repo 安裝並使用這套 skill。
