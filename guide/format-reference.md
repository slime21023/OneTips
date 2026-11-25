# 格式速查

本頁整理撰寫 OneTips（format 1）最常查閱的設定與 Markdown 欄位規則。所有檔案皆使用 UTF-8 編碼與 LF 換行。

---

## 1. `onetips.yaml`

放在 Tips 專案根目錄（**不會隨 skill 安裝**）：

```yaml
format: 1
name: acme-tips
domain: Acme SDK
subjects:
  acme-sdk: Acme SDK
categories:
  - id: networking
    title: Networking
sections:
  when: When to Use
  approach: Recommended Approach
  pitfalls: Pitfalls
  checklist: 檢查清單
snippets:
  python:
    ext: py
    compile: python -m py_compile {file}
    test: python {file}
    timeout: 120
```

| 欄位 | 必填 | 規則 |
| --- | :-: | --- |
| `format` | 是 | 固定為整數 `1`。 |
| `name` | 是 | 必須與 `skills/<name>/` 目錄名相同；小寫 kebab-case，長度 1–64，不可為 Windows 保留名。 |
| `domain` | 是 | 非空單行字串（無前後空白）。 |
| `subjects` | 是 | 版本主體 ID（kebab-case）→ 顯示名稱的映射，可為空 `{}`。 |
| `categories` | 是 | 非空清單，每項含唯一 `id`（kebab-case）與非空單行 `title`；索引將依此順序輸出。 |
| `sections` | 是 | 必須剛好包含 `when`、`approach`、`pitfalls`、`checklist` 四個鍵；標題互異、單行、不可 `#` 開頭或結尾。 |
| `snippets` | 否 | 以程式碼語言標籤為鍵；`ext` 僅限英數字（不含點），`compile`／`test` 可用 `{file}` 與 `{dir}` 佔位符，`timeout` 預設 `120` 秒。 |

---

## 2. 單篇 Tip（`skills/<name>/references/<id>.md`）

````markdown
---
id: retry-with-backoff
summary: Cap retry attempts and delay for transient failures.
category: networking
tags: [retry, timeout]
related: []
applies_to:
  acme-sdk: '>=2.0 <3.0'
---

# Limit transient retries

## When to Use

The operation can safely be retried after a transient failure.

## Recommended Approach

```python status=tested
limit = 4
assert limit > 0
```

## Pitfalls

Do not retry failures that are permanent.

## 檢查清單

- [ ] Limit both attempts and delay.
````

### Front matter 欄位

- `id`（必填）：須與檔名 `<id>.md` 一致、全專案唯一、kebab-case（1–64 字元，發布後不可重用）。
- `summary`（必填）：1–200 字元的單行摘要。
- `category`（必填）：必須存在於 `onetips.yaml` 的 `categories`。
- `tags`（必填）：非空 kebab-case 清單（每項最多 64 字元）。
- `applies_to`（必填）：版本主體（須定義於 `subjects`）→ 非空單行版本字串的映射（可為 `{}`；`*` 表示不限版本）。
- `related`（選填）：其他存在的 Tip ID 清單，不可指向自身。
- `x-*`（選填）：供作者自訂擴充資料的前綴。

### 本文與程式碼片段規則

- **唯一 H1**：第一個非空區塊必須是唯一的頂層 `# 標題`（標題不寫在 front matter）。
- **四個固定順序的 H2**：依序為 `when` → `approach` → `pitfalls` → `checklist`，文字須完全符合 `onetips.yaml` 的 `sections`。
- **檢查清單**：`checklist` 章節內至少要有一個有文字的 `- [ ] ...` 項目。
- **程式碼片段**：
  - Info string 第一個詞必須是語言標籤（否則報 `E-CODE-LANG`）。
  - 選填 `status=unverified|compiled|tested`（省略視為 `unverified`）。
  - 單段超過 60 行會產生 `W-SNIPPET-LONG` 警告（不阻斷驗證）。
- **連結限制**：相對連結必須存在且不得逃出 `skills/<name>/` 範圍；`#anchor` 必須對應目標 Markdown 的標題錨點或明確 `<a>` 標籤。
