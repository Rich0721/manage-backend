# TASK-001 Code Review

Status: OPEN

## Task ID

TASK-001

## Review Result

Code Review 未通過。存在 request type validation problem 與多項 plan-required
schema tests 缺漏。

## Implementation Plan

- 每個 endpoint 必須使用 typed request/response envelope。
- Email、boolean、role、password 與公開 alias 必須符合 contract。
- 測試必須覆蓋每個 endpoint 的有效與無效序列化、boundary、alias、required
  field 與 mutable default。

## Existing Implementation

- 已建立共用 generic envelope、各 endpoint info model、role enum 與 aliases。
- `isForceLogin` 使用一般 `bool`，Pydantic 會將字串等值 coercion 為 boolean。
- 測試目前集中於 register、password pattern 與 permission list 的少數案例。

## Review Issue

1. **Type validation**：`src/models/schemas/user.py:58` 會接受
   `isForceLogin="false"` 並轉換為 `False`，未拒絕非 boolean JSON type，與 Plan 的
   invalid type/boolean rejection 不一致。
2. **Missing tests**：`tests/models/schemas/test_user.py` 未完整涵蓋 login、logout、
   getUsers 與各 response model；亦缺 invalid Email、invalid boolean、invalid role、
   invalid list element、長度 boundary、required field 與 mutable default 測試。
3. Plan target 為 `ValidationErrorItem`，實作提供的是 `ErrorDetail`；應確認並對齊
   Plan 定義的 schema target。

## Expected Behavior

公開 request 應拒絕不符合宣告 JSON type 的值，且所有 endpoint schema 的正常、邊界與
錯誤 contract 均應有獨立測試證明。

## Suggested Area To Fix

- `src/models/schemas/user.py`
- `tests/models/schemas/test_user.py`

## Resolution

```text
Status: OPEN
```

等待 Programmer Agent 完成修正後重新審查。
