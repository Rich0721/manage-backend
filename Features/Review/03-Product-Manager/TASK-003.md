# TASK-003 Code Review

Status: OPEN

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
Status: OPEN
```
