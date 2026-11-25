# Tips 文件的結構與設計原理

本文說明 format 1 的結構為何如此設計。欄位與規則的正式定義見 [FORMAT.md](FORMAT.md)。

## 專案層級結構

```text
README.md                          給人看的入口
onetips.yaml                      專案設定，不會被安裝
skills/<name>/
  SKILL.md                         Agent 入口與使用協定
  INDEX.md                         由 metadata 產生的索引
  references/<id>.md               每篇 Tip 一個檔案
```

只有 `skills/<name>/` 會被 `skills add` 安裝。因此 Agent 需要的內容都放在這個資料夾內，且資料夾內的連結不得指向外部。這是「安裝後不需要原始 repo」的前提。

## 單篇 Tip 的結構

1. **YAML front matter**：`id`、`summary`、`category`、`tags`、`applies_to` 必填，`related` 選填，`x-*` 供擴充。
2. **唯一的 H1**：Tip 的標題。標題不放在 front matter，避免同一檔案有兩處標題需要同步。
3. **四個固定 H2，依序出現**：
   - `when`：適用情境
   - `approach`：推薦做法
   - `pitfalls`：常見陷阱
   - `checklist`：檢查清單，至少一個 `- [ ]` 項目
4. **程式碼片段**：fence 的第一個詞是語言；可加 `status=unverified|compiled|tested`，省略視為 `unverified`。

## 設計原理

| 設計 | 原因 |
| --- | --- |
| 一篇一個問題 | 檢索粒度小，Agent 只需載入一篇。無法用一句 summary 說完，就拆成兩篇並用 `related` 連結。 |
| `id` 等於檔名且不可重用 | 穩定識別；索引、`related`、查詢都以它為鍵。 |
| 固定章節順序 | Agent 不必讀全文就能定位「檢查清單」。章節標題可在地化，但穩定鍵（`when`…`checklist`）不變，對照表寫在 `INDEX.md`。 |
| 章節由真正的 H2 判定 | 程式碼圍欄內看起來像標題的文字不會被誤判。 |
| `applies_to` 只是字串 | OneTips 不解析版本語意，各生態系自行定義；由 Agent 比對目標專案版本。 |
| 片段狀態寫在 info string | 與程式碼貼在一起，GitHub 仍依語言上色；`snippets` 只執行 `compiled`／`tested`，其餘不執行。 |
| checklist 是可判定的陳述 | Agent 可把它當審查依據，逐項回報符合、不符合或不適用。 |
| `INDEX.md` 是產生物 | Markdown 是唯一來源；`check` 會偵測索引過期，作者不必手動同步。 |
| 索引含 `Sections` 對照與固定欄位 | 沒有 CLI 時，Agent 仍可搜尋索引，再用對照找到實際 H2，只讀需要的章節。 |
| `SKILL.md` 規定先查專案再查 Tip | 範例是參考、checklist 是審查依據，不覆蓋專案既有決策。 |

## 程式碼模組結構與分層

上面是 Tips 文件的結構；下面是 `src/onetips/` 的結構。依賴只往內：

```text
cli → commands → adapters → core
```

```text
src/onetips/
  cli/            參數定義、分派、輸出格式、exit code 對應
  commands/       scaffold（init／new）, index, check, snippets, verify, find, show；project.py 載入並驗證專案
  adapters/       fs, yamlio, config, markdown, tips, index_file, links, hashing, runner
  core/           errors, diagnostic, snippet, tip, section, config, index
    rules/        metadata, body, anchors, links, skill
```

| 層 | 職責 | 不做的事 |
| --- | --- | --- |
| `core` | Tip、索引、設定的資料型別；索引解析與渲染；查詢篩選；驗證規則。輸入是已讀入的資料，輸出是值或 `Diagnostic`。 | 不讀寫檔案、不解析 YAML 或 Markdown、不啟動子行程。 |
| `adapters` | 所有與外界的接觸：檔案系統與符號連結判斷、YAML、Markdown（markdown-it）、連結與錨點的存在性檢查、lock 雜湊、片段執行。把外界資料轉成 `core` 的型別。 | 不決定規則；規則判斷交給 `core`。 |
| `commands` | 每個指令一個函式，組合 adapters 與 core，回傳 `CommandResult`（診斷加輸出文字）或查詢結果字串。 | 不印出任何內容。 |
| `cli` | 唯一碰 stdout 與 stderr 的層；把例外與診斷轉成 exit code。 | 不含業務邏輯。 |

### 設計原理

| 設計 | 原因 |
| --- | --- |
| `core` 完全無 I/O | 規則可用記憶體中的資料直接測試（見 `tests/test_core_rules.py`）；也因此整個 `core` 可交給 mypyc 編譯，不必擔心檔案系統與平台差異。 |
| 規則與讀取分離 | 連結檢查拆成兩半：`core/rules/links.py` 只做詞法判斷（是否遠端、是否越界），`adapters/links.py` 才解析路徑並檢查檔案是否存在。 |
| 單一錯誤通道 | 內容問題一律是 `Diagnostic`（碼、路徑、行號，全部收集後一起回報）；只有用法與設定錯誤才拋例外：`UsageError`（exit 2）、`ConfigError`（顯示為 `E-CONFIG`，exit 2）、`DataError`（查詢類失敗，exit 1）。 |
| 輸出集中於 `cli` | 指令函式回傳資料而非印出，因此輸出格式與 exit code 只有一處定義，並用快照測試凍結。 |
| `Project` 作為共同起點 | `index`、`check`、`snippets` 都先 `load_project`，讀取與驗證只寫一次；「專案目錄本身不可用」以 `ready=False` 明確表達，而不是藏在條件式裡。 |
| 不留相容層 | 重構時舊模組路徑直接刪除，沒有轉接檔，避免兩套匯入並存。 |

### 編譯與測試的約束

- `setup.py` 遞迴編譯 `core/` 下所有模組（`__init__.py` 除外）；`adapters`、`commands`、`cli` 維持純 Python。編譯失敗就讓建置失敗，不回退成純 Python wheel。
- mypyc 的 dataclass 無法解析型別為 `object` 的欄位，所以 `Document.metadata` 標為 `Any`；新增 `core` 欄位時要留意。
- 行為由三層測試守住：`tests/test_snapshots.py` 凍結所有指令對 fixture 的 exit code、stdout、stderr（訊息文字與行號屬於對外契約，不得為了重構而更新快照）；`tests/test_mvp.py` 涵蓋各驗收條件；`scripts/acceptance.py` 驗證安裝與純 Python／原生 wheel 的輸出逐位元組一致。

### 複雜度規則與函式拆分原則

`pyproject.toml` 啟用 ruff 的 `C901`（mccabe 圈複雜度），門檻為 **10**，CI 以 `ruff check` 強制。新增或修改函式時，超過門檻就要拆，不用 `noqa` 掩蓋。

拆分時遵守下列原則，現有程式碼（`core/rules/metadata.py`、`core/rules/body.py`、`core/index.py`、`core/config.py`、`adapters/markdown.py`、`adapters/links.py`、`adapters/hashing.py`）都照此處理：

| 原則 | 做法 |
| --- | --- |
| 一個函式一個關注點 | 驗證多個欄位或多個區段時，每個欄位或區段一個函式（`_check_tags`、`_parse_sections`），主函式只負責依序組合。 |
| 組裝函式保持扁平 | 主函式只呼叫子函式並累加結果，不放判斷細節；目標 30 行內、巢狀不超過 2 層。 |
| 順序是契約 | 診斷與錯誤的先後順序屬於對外行為（快照測試鎖定），子函式的呼叫順序要與原本的檢查順序一致。 |
| 檢查函式回傳資料，不直接輸出 | 規則類函式回傳值與 `(code, message)` 問題清單，由組裝函式一次轉成 `Diagnostic`，因此可用記憶體資料單獨測試。 |
| 用提早回傳取代 `if/elif` 串連 | 例如 `_load_catalog`：符號連結先處理並回傳，其餘情況就是一條直線。 |
| 「略過」的語意寫在函式說明 | `config` 或 `ids` 為 `None` 代表略過與專案相關的檢查，在 docstring 說明一次，不靠讀條件式推斷。 |
| 共用簽名的處理函式用對照表分派 | `read_document` 以 token 類型查表呼叫處理方法，取代長的 `if/elif`；這些方法因簽名一致而有未使用參數，僅對該檔關閉 `ARG002`。 |
| 遞迴與閉包改成模組層級函式 | `computed_hash` 的巢狀 `visit` 改為 `_collect`，參數明確，可單獨閱讀與測試。 |

重構的安全網：`tests/test_snapshots.py` 凍結所有指令的輸出，`tests/test_core_rules.py` 與 `tests/test_markdown_document.py` 以記憶體資料或暫存檔直接驗證規則。拆分前先確認這些測試通過，拆完後輸出不得有任何差異。

## 總結

同一份 Markdown 同時滿足三件事：人在 GitHub 直接閱讀；工具能驗證並產生索引；Agent 只載入一篇 Tip 的一個章節或片段，且在沒有任何工具時也能靠索引與固定標題定位。
