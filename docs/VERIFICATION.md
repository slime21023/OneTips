# OneTips MVP 驗收狀態與證據

本文件獨立記錄 OneTips MVP（format 1）各項驗收條件（AC-1～AC-9）的實際驗證進度與可重現證據；規格定義維持於 [PROPOSAL.md](PROPOSAL.md) 與 [FORMAT.md](FORMAT.md)。

- **最後更新**：2026-11-25
- **基準 Commit**：`3fdcfb8`（CI [Run #45586460006](https://github.com/slime21023/OneTips/actions/runs/45586460006)，`python-312`、`framework (ubuntu-latest)`、`framework (windows-latest)` 全數通過）

## AC-1～AC-9 驗收總表

| 編號 | 驗收項目 | 狀態 | 證據與重現方式 |
| --- | --- | --- | --- |
| **AC-1** | GitHub 能正常閱讀 | **部分驗證** | 自動化代理檢查 `onetips check` 已於 CI 通過；公開 repo 已驗證 README → `INDEX.md` 點擊，以及 Tip 與錨點 URL 直接開啟（詳見下方說明，完整點擊鏈尚待補記）。 |
| **AC-2** | 索引與文件一致 | **已驗** | [test_mvp.py](../tests/test_mvp.py)（`test_index_reproducible_and_stale_with_diff`）與 [test_snapshots.py](../tests/test_snapshots.py)；CI Run [#45586460006](https://github.com/slime21023/OneTips/actions/runs/45586460006)。 |
| **AC-3** | 格式錯誤可診斷 | **已驗** | [test_mvp.py](../tests/test_mvp.py)（`test_invalid_fixture_recipes`）、[test_snapshots.py](../tests/test_snapshots.py) 覆蓋全部 `fixtures/invalid-*.json` 變體與快照契約。 |
| **AC-4** | 安裝後參考文件完整 | **已驗** | 1. **本機／模擬 tag**：CI 執行 `uv run --locked python scripts/acceptance.py`（Run [#45586460006](https://github.com/slime21023/OneTips/actions/runs/45586460006)）。<br>2. **公開遠端 GitHub tag**：已對公開不可變 tag `ac4-fixture-v1`（commit `9bfa824bf292b10788d40d67f43a9ab972569667`）執行 `uv run --locked python scripts/acceptance.py --remote-source "https://github.com/slime21023/OneTips#ac4-fixture-v1"`（`skills@1.9.0`），來源、安裝副本與 `skills-lock.json` v2 三方 `computedHash` 均為 `13296f4c85669969dfc87866fe844d3663e431ca8e9a1794073077ae3b8fdfc8`（紀錄見 [Issue #3](https://github.com/slime21023/OneTips/issues/3)）。 |
| **AC-5** | 無 OneTips CLI／Python 仍可查閱 | **已驗** | 1. **腳本驗證**：`scripts/acceptance.py` 內 `no_cli_lookup` 於移除 `python`/`uv`/`onetips`/`jq`/`yq` 的環境執行通過。<br>2. **真實 Agent 實測**：唯讀 Agent（僅使用 `read_file`）完成標籤查找與在地化 `Sections` 對照，去識別化紀錄見 [ac5-ac8-transcripts.md](verification/ac5-ac8-transcripts.md#scenario-1--ac-5-no-cli-tag-lookup--localized-checklist)。 |
| **AC-6** | 查詢有結構、只讀必要檔案 | **已驗** | [test_mvp.py](../tests/test_mvp.py) 全部 `test_query_*` 案例與 [test_snapshots.py](../tests/test_snapshots.py)（含 `references/` 不可讀時 `find` 仍正常、圍欄內同名 H2 不誤判）。 |
| **AC-7** | 片段狀態可信 | **已驗** | [test_mvp.py](../tests/test_mvp.py) 全部 `test_snippets_*` 案例，以及 CI 新增的 `examples/typescript-tips` `onetips snippets` 驗證（Run [#45586460006](https://github.com/slime21023/OneTips/actions/runs/45586460006)）。 |
| **AC-8** | Agent 尊重專案決策 | **已驗** | 真實唯讀 Agent 分別實測「目標 SDK 版本不適用（`1.5.0` vs `>=2.0 <3.0`）」與「`AGENTS.md` 規則和 `idempotency-keys` 衝突」，均依 `SKILL.md` 拒絕不適用範例並遵照目標 repo 決策；去識別化紀錄見 [ac5-ac8-transcripts.md](verification/ac5-ac8-transcripts.md#scenario-2--ac-8a-target-version-mismatch-acme-sdk-150)。 |
| **AC-9** | mypyc 編譯與行為一致 | **已驗** | CI 於 Linux 與 Windows 皆執行 `uv run --locked python scripts/acceptance.py --build-wheels`，驗證純 Python 與 mypyc 原生 wheel 查詢輸出逐位元組一致（Run [#45586460006](https://github.com/slime21023/OneTips/actions/runs/45586460006)）；另於 `python-312` job 驗證 Python 3.12 最低支援版本與純 Python wheel 安裝執行。 |

## AC-1 GitHub 渲染與導覽紀錄

依實測範圍如實區分：

- **已驗證**：
  - 自動化代理檢查：`onetips check` 對 `fixtures/minimal` 回報 `0 errors, 0 warnings`。
  - 公開 GitHub repo（`slime21023/OneTips`）已點擊確認 README → `INDEX.md` 連結有效。
  - 已直接開啟 Tip 與章節錨點 URL 確認 GitHub front matter 表格渲染與含 `status=` 程式碼區塊語法高亮正常。
- **待補記（尚未當成完整點擊路徑）**：
  - 尚待在 GitHub 網頁介面從 `fixtures/minimal/README.md` → `INDEX.md` → 每篇 Tip → Tip 內 `related`／跨檔章節錨點逐一完成端到端人工點擊並留存紀錄。
