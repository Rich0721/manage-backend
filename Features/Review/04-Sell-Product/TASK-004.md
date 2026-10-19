# TASK-004 Code Review

Status: OPEN

## Task ID

TASK-004

## Review Result

日期上界處理有未捕捉的例外，合法格式的查詢可能回 HTTP 500。

## Implementation Plan

§VI.2、§VI.3 與 TASK-004 要求 `orderId=all` 驗證日期，日期欄位錯誤回 HTTP 400，並以半開區間包含 `endDate` 全日。

## Existing Implementation

`src/services/sell_service.py` 的 `get_order()` 以 `datetime.strptime()` 解析日期，再計算 `end + timedelta(days=1)` 傳給 repository。

## Review Issue

- `src/services/sell_service.py:200`：`endDate=9999-12-31` 且 `startDate=9999-12-31` 通過格式、順序與 30 日驗證，但隔日計算會拋出 `OverflowError`。該例外沒有轉為 `OrderBadRequestError`，最後由全域未預期錯誤處理回 HTTP 500，與欄位錯誤 400 契約不符。
- `src/services/sell_service.py:45`、`:205`：`\d{10}` 接受全形等 Unicode 數字；例如 `１２３４５６７８９０` 通過格式檢查後會查無訂單而回 404，但計畫要求非法訂單 ID 回 400，資料表也只允許 ASCII 數字。

## Expected Behavior

合法格式但無法形成查詢上界的日期及非 10 位 ASCII 數字的訂單 ID 應回 HTTP 400；正常日期仍須包含結束日的完整時間。

## Suggested Area To Fix

檢查 `get_order()` 的日期上界計算與訂單 ID 格式驗證，並補上對應的 service／HTTP 測試。

## Resolution

Status: OPEN

待 Programmer Agent 修正後重新審查。
