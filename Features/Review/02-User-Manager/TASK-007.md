# TASK-007 Code Review

Status: OPEN

## Task ID

TASK-007

## Review Result

Code Review 未通過。Normal logout 存在 session deletion race，可能在 session 已消失時仍
回傳成功，且 Plan 指定測試不完整。

## Implementation Plan

- Normal mode 必須先驗證 matching session，再刪除該 session。
- Missing/expired session 不可視為 idempotent success，必須回傳 401 / ForceLogout。
- DEBUG token-absent path 仍需 valid Uid/database user，並可刪除可能存在的 key。

## Existing Implementation

- Service 會驗證 auth、從 database 取得 trusted userName，再呼叫 session delete。
- `SessionRepository.delete()` 忽略 Redis `DEL` 的刪除筆數並永遠回傳 `None`。

## Review Issue

1. **Functional race**：`src/repositories/session_repository.py:47-51` 未保留 `DEL` 結果，
   `src/services/user_service.py:150-154` 因此無法判斷 session 是否在 validate 後已過期或
   被移除。Normal logout 會錯誤回傳 200 Success，違反 Plan 的 missing/expired session
   行為。
2. **Missing tests**：缺少 missing/mismatched/expired session、Redis delete failure、
   DEBUG token-absent success、missing Uid/user rejection 與 race-delete-zero 測試。

## Expected Behavior

Normal logout 只有在 validated session 確實刪除時才能成功；DEBUG bypass 的 key-absent
策略則應依 Plan 保持獨立。

## Suggested Area To Fix

- `src/repositories/session_repository.py`
- `src/services/user_service.py`
- `tests/repositories/test_session_repository.py`
- `tests/services/test_user_service.py`

## Resolution

```text
Status: OPEN
```

等待 Programmer Agent 完成修正後重新審查。
