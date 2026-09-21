# TASK-006 Code Review

Status: RESOLVED

Review Fix Validation (2026-09-21): login database/Redis/token failure、force replacement、
TTL/JWT claims 與 error envelope 邊界均已有測試覆蓋，原 Issue 已解決。

## Task ID

TASK-006

## Review Result

Code Review 未通過。Login 主流程存在，但 Plan 指定的 failure-path coverage 不完整。

## Implementation Plan

- 無 session 時建立 token/session；existing non-force 不得 mutation；force login 必須
  transactionally replace session。
- Unknown Email 與 wrong password 對外行為相同。
- Database、Redis 與 token generation failure 不得回傳成功。
- Token response body/header 與 TTL 必須一致。

## Existing Implementation

- Service 已實作 normal、existing session 與 force replace branches。
- Tests 涵蓋三個主要 session branches 與 equivalent credential errors。

## Review Issue

缺少 database lookup failure、Redis get/set/force-replace failure、token generation failure、
REDIS_TTL/claims verification、failure response 空 uid/auth/info，以及 force login 新 session
結果的完整驗證。

## Expected Behavior

Login 所有 infrastructure failure 都應有明確 domain mapping 與 controller response 測試，
且不得產生部分成功或洩漏帳號是否存在。

## Suggested Area To Fix

- `tests/services/test_user_service.py`
- `tests/controllers/test_user_controller.py`

## Resolution

```text
Status: RESOLVED
```

等待 Programmer Agent 完成修正後重新審查。
