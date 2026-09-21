# TASK-009 Code Review

Status: OPEN

## Task ID

TASK-009

## Review Result

Code Review 未通過。Permission matrix 實作方向正確，但測試不足以證明完整 matrix 與
all-or-nothing transaction requirement。

## Implementation Plan

- 必須驗證每個 admin/manager/user transition。
- Admin target 永遠不可修改。
- Duplicate/unknown/forbidden/mixed batch 與 mid-transaction failure 都不得留下 partial
  update。
- Multiple valid targets 應在同一 transaction 成功。

## Existing Implementation

- Service 會在 transaction 內鎖定 targets、先驗證全部 transition，再 executemany。
- Tests 僅涵蓋 manager promote user、manager denied manager 與 duplicate target。

## Review Issue

缺少完整角色矩陣、admin target、user operator、unknown target、multiple valid targets、
mixed valid/invalid batch、database failure rollback、updated_at 與 no-write-before-validation
測試。現有 fake transaction 不記錄 commit/rollback，無法證明 all-or-nothing behavior。

## Expected Behavior

每一個允許與拒絕 transition，以及 transaction failure 的資料不變性，都必須有可重現
測試證明。

## Suggested Area To Fix

- `tests/services/test_user_service.py`
- `tests/repositories/test_user_repository.py`

## Resolution

```text
Status: OPEN
```

等待 Programmer Agent 完成修正後重新審查。
