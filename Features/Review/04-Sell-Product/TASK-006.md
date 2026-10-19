# TASK-006 Code Review

Status: OPEN

## Task ID

TASK-006

## Review Result

測試尚未涵蓋計畫明列的核心驗收情境，特別是多商品交易與併發一致性。

## Implementation Plan

TASK-003、TASK-004、TASK-006 要求驗證兩筆商品同步更新、商品不存在時 orders／items／products／cache 全部不變、並行銷售與商品更新、訂單 ID 併發唯一、日期跨午夜、三角色授權及 Redis 發布故障後的 DB／快取狀態。

## Existing Implementation

`tests/integration/test_sell_product_integration.py` 目前只有一筆商品的成功銷售與單獨不存在商品測試；`tests/repositories/test_order_repository.py` 以單一 connection 驗證建立與重複明細。其餘測試多以單元 fake 或 controller mock 驗證。

## Review Issue

- `tests/integration/test_sell_product_integration.py:112` 未驗證同一訂單兩筆商品的庫存及稽核欄位更新，也未驗證「第一筆存在、第二筆不存在」時整張訂單、明細、商品與 Redis 保持原狀。現有 `get_orders(order_id="0000000001")` 斷言只檢查原訂單，無法證明沒有產生其他訂單。
- 現有測試沒有以獨立資料庫連線並行下單，無法驗證 `FOR UPDATE`、sequence 唯一性、庫存與產品管理更新的競爭，以及產品快取最後狀態。
- 計畫要求的查詢跨午夜邊界、三角色授權與真實 DB／Redis 發布故障狀態尚未有對應測試；目前快取故障僅由 fake 模擬。

## Expected Behavior

計畫列出的正常、邊界、錯誤與跨服務一致性情境，應有可重現的測試及明確斷言，尤其是整筆 rollback 與併發結果。

## Suggested Area To Fix

補齊 `tests/integration/`、`tests/repositories/`、`tests/services/`、`tests/controllers/` 中上述缺口，並依 TASK-006 執行相關測試與產品快取回歸。

## Resolution

Status: OPEN

待 Programmer Agent 補測後重新審查。
