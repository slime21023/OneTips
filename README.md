# OneTips

> 用一份 Markdown 維護技術 Tips：人在 GitHub 上直接讀，Coding Agent 依任務只載入需要的章節。

OneTips 是讓開發者建立、驗證與發布技術 Tips 的框架。每篇 Tip 只解決一個問題，用 YAML front matter 描述穩定 ID、摘要、分類、標籤、相關主題與適用版本，並以固定章節呈現適用情境、推薦做法、常見陷阱與檢查清單。

- **給讀者**：不需要建置文件網站。README、自動產生的主題索引與相對連結，讓整個 Tips 專案在 GitHub 上就能瀏覽。
- **給作者**：Markdown 是唯一的內容來源。OneTips 提供初始化範本、結構與連結驗證、程式碼片段驗證，並從 metadata 產生索引，作者不必手動同步多份內容。
- **給 Coding Agent**：每個 Tips 專案可作為自足的 Agent Skill（`SKILL.md` + `INDEX.md` + `references/`），目標是用 `bunx skills add` 完整安裝到另一個 repo。安裝後，Agent 先確認目標專案的版本與慣例，再由索引定位並只讀需要的章節。可選用 OneTips CLI 結構化查詢主題、章節與程式碼；沒有 CLI 或 Python，也能直接讀索引和 Markdown。

OneTips 本身不提供任何特定技術的教學內容。領域、適用版本與範例由各 Tips 專案自行定義。

框架採用 Python + uv 開發，名稱統一為 OneTips：PyPI 發行名稱、Python 匯入套件與 CLI 指令皆為 `onetips`（尚未發布）。查詢核心須通過 mypyc 編譯與行為一致性驗證；這是框架的開發要求，不是 skill 的使用條件。

> **狀態**：MVP 開發版，尚未發布到 PyPI。參考 [格式規格](docs/FORMAT.md)、[結構與設計原理](docs/DESIGN.md)與[設計提案](docs/PROPOSAL.md)。

## 建立第一篇 Tip

從本機 OneTips 原始碼目錄執行 `uv tool install .`，再切到要建立 Tips 專案的位置：

```bash
onetips init my-tips --name my-tips
cd my-tips
onetips new first-tip --category general
```

`init` 建立空索引與 skill 目錄，`new` 把草稿寫到 `skills/my-tips/references/first-tip.md`，不會修改索引。可在 `onetips.yaml` 新增分類與修改章節標題。

填完草稿後，在 Tips 專案根目錄執行：

```bash
onetips index
onetips check
onetips snippets
```

`index --check` 可在不寫檔的情況下檢查索引是否過期。`snippets` 會執行專案配置的命令，請只在信任的專案中執行。

## 安裝與查閱

在目標 repo 執行 `bunx skills add "/path/to/my-tips" --skill my-tips`，用 `bunx skills list --json` 取得實際安裝路徑。將下列 `/actual/installed/my-tips` 換成該路徑：

```bash
onetips verify "/actual/installed/my-tips"
onetips find --skill-dir "/actual/installed/my-tips" --id first-tip --json
onetips show --skill-dir "/actual/installed/my-tips" first-tip --section checklist
```

沒有 OneTips CLI 時，從安裝目錄打開 `SKILL.md` 和 `INDEX.md`，再循相對連結查閱。可直接瀏覽 [Acme 範例索引](fixtures/minimal/skills/acme-tips/INDEX.md)。

## 開發

```bash
uv sync --locked
uv run --locked onetips --version
uv run --locked mypy
uv run --locked pyrefly check
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m unittest discover -s tests -v
```

`uv build --wheel` 預設建置純 Python wheel。需要驗證原生版時，在有 C 編譯器的環境將 `ONETIPS_MYPYC` 設為 `1`，再執行相同指令。

程式碼的分層與模組職責見[結構與設計原理](docs/DESIGN.md#程式碼模組結構與分層)。

端到端驗收：`uv run --locked python scripts/acceptance.py`（需要 Bun、Node.js ≥22.20、Git），會測本機及指定 Git tag 的完整安裝、lock 雜湊與無 CLI 查閱。`uv run --locked python scripts/acceptance.py --build-wheels` 需 C 編譯器，會建置兩種 wheel 並比較查詢輸出。
