# TASK-003 Code Review

Status: OPEN

Review Fix Validation (2026-09-21): Repository methods、PO mapping、error mapping、transaction
commit/rollback，以及 PostgreSQL 17 integration 已補強；但原 Review Issue 的 constraint
coverage 尚未全部完成，因此維持 `OPEN`。

## Task ID

TASK-003

## Review Result

Code Review 未通過。DDL 與 Repository 基本結構符合分層，但 Plan 明定的 repository、
rollback 與 PostgreSQL integration tests 大量缺漏。

## Implementation Plan

- `tb_users` 必須具備 required constraints、comments 與 application-managed timestamps。
- Repository 每個 method 均需 parameterized query、row mapping 與錯誤映射測試。
- Batch permission update 必須在 transaction 中整批 rollback。
- DDL 必須以 PostgreSQL 17 驗證 constraints。

## Existing Implementation

- 已建立 DDL、UserPO、parameterized queries 與 transaction context。
- 現有 repository tests 只涵蓋 get_by_email、create、單一 role filter、
  executemany 與一般 database error。
- DDL test 僅檢查 SQL 文字片段，未實際套用 PostgreSQL。

## Review Issue

1. `tests/models/po/test_user.py` 未建立。
2. `get_by_uid()`、`get_by_emails()`、not-found、UniqueViolation mapping、admin/manager
   filter、transaction commit/rollback 與 mid-update failure 未測試。
3. DDL 未依 Plan 在 PostgreSQL 17 執行並驗證 primary key、unique Email、password
   pattern、permission check 與 NOT NULL constraints。

## Remaining Issue After Review Fix

`tests/integration/test_user_manager_integration.py:52-94` 已驗證 unique Email、password
pattern、permission check 與 `user_name` NOT NULL，但仍未驗證 duplicate primary key，亦未
涵蓋 `uid`、`email`、`password`、`permission`、`created_at`、`updated_at` 的 NOT NULL
constraints。這些項目屬於原 Review Issue 與 TASK-003 Testing 定義的 DDL constraint
regression coverage。

## Expected Behavior

每個 Repository method、錯誤分類與 batch rollback 均應有可重現測試，且 DDL 應證明可在
目標 PostgreSQL 版本執行並實際拒絕 invalid rows。

## Suggested Area To Fix

- `tests/models/po/test_user.py`
- `tests/repositories/test_user_repository.py`
- PostgreSQL integration tests for `database/DDL/tables/TB_USERS.sql`

## Resolution

```text
Status: OPEN
```

等待 Programmer Agent 完成修正後重新審查。
