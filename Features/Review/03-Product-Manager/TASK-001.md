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
