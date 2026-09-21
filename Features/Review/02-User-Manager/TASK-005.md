# TASK-005 Code Review

Status: RESOLVED

Review Fix Validation (2026-09-21): registration normal、validation、unique race、database
failure、Uid/timestamp payload 與 confirmPassword 邊界均已驗證，原 Issue 已解決。

## Task ID

TASK-005

## Review Result

Code Review 未通過。Registration 主流程正確，但 Plan 指定的 unique-race 與
infrastructure error tests 尚未提供。

## Implementation Plan

- Registration 必須 lowercase Email、產生 deterministic Uid、保存一次 frontend hash、
  預設 user role 並填入 timestamps。
- Pre-check 與 database unique race 必須回傳相同 duplicate Email error。
- Database failure 不得回報成功或洩漏內部資訊。

## Existing Implementation

- Service 已執行 password compare、lowercase、Uid hash、default role 與 repository create。
- `DuplicateUserRecordError` 已映射為 `DuplicateEmailError`。
- Tests 只涵蓋成功、password mismatch 與 pre-existing Email。

## Review Issue

缺少 invalid Email regression、exact UserPO/timestamp payload、Uid expected hash、database
unique-race、一般 database failure，以及 confirmPassword 不保存／不回傳的明確測試。

## Expected Behavior

Registration 的正常、business error、unique race 與 infrastructure error paths 均應有
獨立測試證明，且 response/storage 不得包含 confirmPassword。

## Suggested Area To Fix

- `tests/services/test_user_service.py`

## Resolution

```text
Status: RESOLVED
```

等待 Programmer Agent 完成修正後重新審查。
