# TASK-006 Code Review

Status: OPEN

## Task ID

TASK-006

## Review Result

前次測試未涵蓋計畫明列的核心驗收情境。本次已補上多商品、併發與快取故障情境；商品不存在時的資料不變斷言及並行測試的日期選取仍需修正。

## Implementation Plan

TASK-003、TASK-004、TASK-006 要求驗證兩筆商品同步更新、商品不存在時 orders／items／products／cache 全部不變、並行銷售與商品更新、訂單 ID 併發唯一、日期跨午夜、三角色授權及 Redis 發布故障後的 DB／快取狀態。

## Existing Implementation

前次審查時，`tests/integration/test_sell_product_integration.py` 只有單筆商品的成功銷售與單獨不存在商品測試；本次已新增兩商品及獨立 PostgreSQL 連線的併發測試。

## Review Issue

前次審查問題（保留紀錄）：

- `tests/integration/test_sell_product_integration.py:112` 未驗證同一訂單兩筆商品的庫存及稽核欄位更新，也未驗證「第一筆存在、第二筆不存在」時整張訂單、明細、商品與 Redis 保持原狀。現有 `get_orders(order_id="0000000001")` 斷言只檢查原訂單，無法證明沒有產生其他訂單。
- 現有測試沒有以獨立資料庫連線並行下單，無法驗證 `FOR UPDATE`、sequence 唯一性、庫存與產品管理更新的競爭，以及產品快取最後狀態。
- 計畫要求的查詢跨午夜邊界、三角色授權與真實 DB／Redis 發布故障狀態尚未有對應測試；目前快取故障僅由 fake 模擬。

### 2026-10-19 重審仍需修正

- `tests/integration/test_sell_product_integration.py:327-370`：缺商品請求先列出商品 `1790705105001`，但該商品在前次成功銷售後庫存已為 0、`updated_uid` 已是 `seller`。測試只比對這兩欄，沒有比對 `updated_at`。若錯誤實作先更新此商品而未 rollback，現有斷言仍可能通過，無法證明計畫要求的 `products` 保持不變。
- `tests/integration/test_sell_product_integration.py:601-602`：測試以本地 `date.today()` 查詢訂單，但 `SellService.__utc_now()` 使用 UTC 日期。當執行環境位於 Asia/Taipei 且本地時間為 00:00–07:59 時，訂單建立日仍可能是前一個 UTC 日期，`len(orders) == 3` 會因日期選錯而失敗。兩次讀取 `date.today()` 也可能跨本地午夜。

## Expected Behavior

計畫列出的正常、邊界、錯誤與跨服務一致性情境，應有可重現的測試及明確斷言，尤其是整筆 rollback 與併發結果。

## Suggested Area To Fix

補齊 `tests/integration/`、`tests/repositories/`、`tests/services/`、`tests/controllers/` 中上述缺口，並依 TASK-006 執行相關測試與產品快取回歸。

## Resolution

Status: OPEN

2026-10-19 重新審查：已確認兩商品更新、訂單／明細數量、獨立連線並行下單、庫存與商品更新競爭、跨午夜查詢、三角色及 DB 提交後快取失效測試均已加入；全套測試於 Programmer 修正後回報 333 passed。上述兩項新問題仍使缺商品 rollback 與併發驗收結果不穩定，待 Programmer Agent 修正後重新審查。
