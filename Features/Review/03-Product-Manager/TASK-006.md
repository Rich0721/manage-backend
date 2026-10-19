# TASK-006 Code Review

Status: RESOLVED

## 2026-10-19 新增商品標籤缺漏修訂審查

### Review Result

- P2／提交後快取故障缺少已提交狀態紀錄。

### Implementation Plan

最新修訂計畫第 28 行要求 DB commit 後 Redis 更新失敗時，經既有 503 路徑並以 logging 記錄已提交狀態。

### Existing Implementation

`src/services/product_service.py:185-218` 在交易後設定 `committed=True`，Redis 錯誤轉為 `ProductCacheUnavailableError`，最後使兩份快取失效；只有失效動作自身失敗時才記錄例外（第 223-230、798-807 行）。

### Review Issue

當標籤快取 `replace()` 或後續 `get()` 失敗，而失效動作成功時，服務回 503 且 DB 已提交，卻沒有記錄該已提交事實。營運人員無法從此路徑的日誌判斷商品及標籤已寫入，可能重試造成重複資料。

### Expected Behavior

提交後的發布失敗須記錄已提交狀態及必要產品 ID／操作脈絡，且維持快取失效與 503 行為；不得記錄敏感資料。

### Suggested Area To Fix

檢查新增專用流程的 `committed and not published` 錯誤處理及相關回歸測試。

### Resolution

```text
Status: RESOLVED
```

### 2026-10-19 複審

`src/services/product_service.py:217-225` 已在 `committed and not published` 路徑記錄產品 ID、操作及已提交狀態，再使快取失效；`tests/services/test_product_service.py` 已驗證標籤快取發布失敗時仍有已提交資料與對應日誌。原 Issue 已解決，TASK-006 通過。
