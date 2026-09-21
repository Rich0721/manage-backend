# TASK-010 Code Review

Status: RESOLVED

Review Fix Validation (2026-09-21): 五個 route 均已套用 endpoint-specific response model，
success/error envelope、Authorization header 同步及 lifespan cleanup 均已驗證。

## Task ID

TASK-010

## Review Result

Code Review 未通過。HTTP routes 與 lifespan 已建立，但 response schema 並未實際套用，
且 centralized error mapping tests 未達 Plan 要求。

## Implementation Plan

- 五個 endpoint 必須接受並回傳 typed envelope。
- Response token 必須同步 body 與 HTTP Authorization header。
- Section 4.3 每種 application error 與 422 都必須使用 standard envelope。
- Tests 必須覆蓋所有 success response、error mapping 與 lifecycle cleanup。

## Existing Implementation

- 五個 path/method、dependency injection、lifespan 與 exception handlers 已存在。
- Route return annotation 均為 `dict[str, Any]`，未指定任何 response model。
- OpenAPI 的五個 200 response 都顯示 unrestricted object
  (`additionalProperties: true`)，TASK-001 宣告的 response aliases 未被使用。
- Controller tests 只驗證部分 success、existing-session 409 與一個 422 case。

## Review Issue

1. **Typed response contract 未套用**：`src/controllers/user_controller.py:56-139` 未使用
   endpoint-specific response schema，framework 不會驗證輸出，OpenAPI 也無法呈現實際
   envelope contract。
2. **Missing error tests**：未覆蓋 duplicate/mismatch 400、invalid credential/auth/session
   401、permission 403、not-found 404、service unavailable 503、unexpected 500，以及各錯誤
   response header absence與標準 envelope。
3. **Missing success contract assertions**：未逐 endpoint 驗證 exact status/message、uid、
   info shape、HTTP status 與 header/body synchronization。

## Expected Behavior

FastAPI 應以 typed response schema 驗證並文件化所有 endpoint output；Section 4.3 的每個
HTTP/application mapping 都應有 controller-level regression test。

## Suggested Area To Fix

- `src/controllers/user_controller.py`
- `src/models/schemas/user.py`
- `tests/controllers/test_user_controller.py`
- `tests/test_main.py`

## Resolution

```text
Status: RESOLVED
```

等待 Programmer Agent 完成修正後重新審查。
