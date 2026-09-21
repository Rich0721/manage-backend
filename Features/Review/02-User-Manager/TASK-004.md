# TASK-004 Code Review

Status: OPEN

## Task ID

TASK-004

## Review Result

Code Review 未通過。Session refresh 的 missing-key error mapping 與 Plan 不一致，且
security/session 測試未覆蓋指定邊界。

## Implementation Plan

- Missing/mismatched Redis session 必須回傳 HTTP 401 / ForceLogout。
- Redis infrastructure failure 才回傳 HTTP 503。
- JWT 測試必須涵蓋 tampered、expired、missing claim、wrong key 與 wrong algorithm。
- DEBUG token-absent 與 token-present paths 必須分別驗證。

## Existing Implementation

- JWT 使用 HS256 與 required claims，session equality 使用 constant-time compare。
- `SessionRepository.refresh()` 將 missing key 與 Redis failure 都轉成同一
  `SessionRepositoryError`。
- `AuthorizationService.refresh_session()` 將上述所有錯誤映射為 503。

## Review Issue

1. **Functional error mapping**：`src/repositories/session_repository.py:58-59` 在 session
   消失時產生一般 repository error，而 `src/services/authorization_service.py:66-69`
   將其映射為 ServiceUnavailable。依 Plan，session missing 應是 401 / ForceLogout；
   race condition（validate 後、refresh 前過期）目前會錯誤回傳 503。
2. **Missing tests**：未測 tampered JWT、wrong key、wrong algorithm、production missing
   token、DEBUG token-present normal validation、successful refresh、refresh missing session
   mapping，以及各 Redis command failure。
3. **Code Standard**：`src/services/authorization_service.py:58` 超過 79 字元。

## Expected Behavior

Session state loss 與 Redis infrastructure failure 必須保持不同 domain error；JWT 與 DEBUG
各條 validation path 應由明確測試覆蓋。

## Suggested Area To Fix

- `src/repositories/session_repository.py`
- `src/services/authorization_service.py`
- `tests/utils/test_security.py`
- `tests/repositories/test_session_repository.py`
- `tests/services/test_authorization_service.py`

## Resolution

```text
Status: OPEN
```

等待 Programmer Agent 完成修正後重新審查。
