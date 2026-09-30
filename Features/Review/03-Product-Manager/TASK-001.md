# TASK-001 Code Review

Status: RESOLVED

## Review Result

- P2: The new DDL comments contain replacement characters when read as UTF-8.

## Existing Implementation

`TB_PRODUCTS.sql` and `TB_LABELS.sql` define the required tables and column
types, but their Chinese `COMMENT ON` text is corrupted in the committed file.

## Review Issue

Python `Path.read_text(encoding="utf-8")` returns replacement characters in
the `COMMENT ON` statements. This violates the project UTF-8 source-file
standard and makes database metadata unreadable.

## Expected Behavior

DDL files must be valid UTF-8 and comments must retain their intended text.

## Suggested Area To Fix

Rewrite the comment statements using verified UTF-8 content, then add a DDL
test that reads the files as UTF-8 and verifies representative comments.

## Resolution

```text
Status: RESOLVED
```

## 2026-09-30 複審

兩份 DDL 均可用 UTF-8 嚴格解碼，且不含替代字元；欄位與自動遞增整數標籤 ID 符合計畫。原問題已解決，TASK-001 可標記 DONE。真實 PostgreSQL 驗證由 TASK-009 追蹤。
