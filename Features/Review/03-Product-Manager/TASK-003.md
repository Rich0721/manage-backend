# TASK-003 Code Review

Status: RESOLVED

## Review Result

- P2: The planned `LabelRepository` is absent.

## Existing Implementation

`ProductRepository` owns both product SQL and `tb_labels` SQL through
`list_labels()`.

## Review Issue

The implementation plan explicitly assigns `LabelRepository.list_all()` to
this task. Combining label access into `ProductRepository` diverges from the
planned repository boundary and prevents the intended independent label data
access contract.

## Expected Behavior

Provide `src/repositories/label_repository.py` for label queries and let the
service depend on it for label loading.

## Suggested Area To Fix

Move `list_labels()` and its PO conversion into `LabelRepository`; keep
product CRUD in `ProductRepository`. Add repository tests for both classes,
including database-error mapping and soft-delete row-count handling.

## Resolution

```text
Status: RESOLVED
```

## 2026-09-30 複審

原本缺少的 `LabelRepository.list_all()` 已補上，Service 也改用獨立 repository。其餘驗收仍未完成：`test_product_repository.py` 只有查詢及更新／軟刪除零筆測試，`test_label_repository.py` 只有正常查詢測試；缺少新增時重複 ID 對應、資料庫異常映射，以及 transaction rollback 的驗證。計畫 TASK-003 的 Testing 明列這些情境。請補齊後再送審。

## 2026-09-30 再複審

已補上 insert 參數化與重複 ID、資料庫例外轉譯、transaction rollback，以及標籤查詢例外測試；前次 review 問題已解決。真實 PostgreSQL 交易驗證仍由 TASK-009 整合測試追蹤。
