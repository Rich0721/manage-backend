# TASK-004 Code Review

Status: OPEN

## Review Result

- P2: The planned `LabelCacheRepository` is absent.

## Existing Implementation

`ProductCacheRepository` stores both `products:info` and `product:labels`,
and also owns both lock keys.

## Review Issue

The implementation plan defines separate product and label cache repositories.
Keeping both cache contracts in one repository makes the product cache class
responsible for unrelated label loading, normalization and locking.

## Expected Behavior

Provide `LabelCacheRepository` for `product:labels` load, replace,
invalidation and label locking. Keep product snapshot serialization and its
lock in `ProductCacheRepository`.

## Suggested Area To Fix

Extract the label methods and lock into `label_cache_repository.py`, inject it
into `ProductService`, and add lock ownership and cache-reload tests.

## Resolution

```text
Status: OPEN
```

## 2026-09-30 複審

原本缺少的 `LabelCacheRepository` 已補上，但以下問題仍阻擋驗收：

- **P1／快取一致性：** `ProductCacheRepository.products_lock()` 只設定固定 10 秒 lease，鎖內沒有續租或失鎖檢查；Service 在同一鎖內執行 DB transaction、完整查詢及 Redis 快照替換。若執行超過 10 秒，其他寫入者可取得鎖，舊持有者仍能發布快照，造成過期資料覆蓋。`LabelCacheRepository.lock()` 也有相同固定 lease。計畫 §6.3 要求必要的續租及安全釋放。請確保鎖到期時不會繼續發布或修改共享狀態，並加入超時與競爭測試。
- **P2／快照內容：** `ProductCacheRepository.__product_to_value()` 僅保存 `label_ids`，沒有保存計畫 §6.3 明列的標籤名稱；讀取快照後仍須另取標籤快取才能組成回應。請使快照包含正式標籤名稱並驗證序列化／還原。
