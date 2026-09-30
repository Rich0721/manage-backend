# TASK-004 Code Review

Status: RESOLVED

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
Status: RESOLVED
```

## 2026-09-30 複審

原本缺少的 `LabelCacheRepository` 已補上，但以下問題仍阻擋驗收：

- **P1／快取一致性：** `ProductCacheRepository.products_lock()` 只設定固定 10 秒 lease，鎖內沒有續租或失鎖檢查；Service 在同一鎖內執行 DB transaction、完整查詢及 Redis 快照替換。若執行超過 10 秒，其他寫入者可取得鎖，舊持有者仍能發布快照，造成過期資料覆蓋。`LabelCacheRepository.lock()` 也有相同固定 lease。計畫 §6.3 要求必要的續租及安全釋放。請確保鎖到期時不會繼續發布或修改共享狀態，並加入超時與競爭測試。
- **P2／快照內容：** `ProductCacheRepository.__product_to_value()` 僅保存 `label_ids`，沒有保存計畫 §6.3 明列的標籤名稱；讀取快照後仍須另取標籤快取才能組成回應。請使快照包含正式標籤名稱並驗證序列化／還原。

## 2026-09-30 再複審

- **P1／失鎖後仍可發布舊快照：** 現在有背景續租，但 `ProductService.__write_product()` 僅在重建前呼叫 `lease.ensure_held()`；`__replace_product_cache()` 隨後查詢產品與標籤，最後呼叫 `ProductCacheRepository.replace_products()` 無條件 `SET`。若 A 在查詢後失鎖，B 取得鎖並發布較新快照，A 仍可把較舊快照覆蓋回去。冷載入及標籤重載的發布也沒有與 lock token 綁定。這仍違反計畫 §6.3 的並行一致性；發布前後的普通檢查也無法消除檢查與寫入之間的競爭窗口。請讓快照發布與持鎖驗證具備原子性，並在失鎖時避免寫入共享 key。
- **P2／標籤名稱未還原：** JSON 現已寫入 `label_names`，但 `get_products()` 將資料還原為只有 `label_ids` 的 `ProductPO`，`ProductService.__to_response()` 每次仍重新查詢 `product:labels`。此外，序列化時若標籤 ID 不在映射中，推導式會直接略過，形成不完整快照而不報錯。計畫 §6.3 要求快照保存並重讀正式標籤名稱及一致型別；請完成讀取路徑及缺漏資料處理。

## 2026-09-30 修正複審

- **已修正：** 產品與標籤快取的 `replace` 現可用 Lua 同時檢查 lock token 並寫入快照；產品快取讀取會還原 `label_names`，缺少 ID 映射時會報錯。失鎖後發布測試已加入。
- **P1／失效舊快取仍有競爭窗口：** `src/services/product_service.py:187-188,211-212` 在 `ensure_held()` 後呼叫 `invalidate_products()`，但 `src/repositories/product_cache_repository.py:132-135` 使用未檢查 lock token 的 Redis `DELETE`。A 可在檢查後失鎖，B 取得鎖並 commit／發布新快照，A 隨後刪掉 B 的快照並繼續 DB 異動。`product:labels` 的重載在 `src/services/product_service.py:291-293` 也以相同方式執行未綁定 token 的 `invalidate()`。計畫 §6.3 要求鎖內失效、異動與發布的並行一致性，且在失效舊 key 前失鎖時不得執行 DB 異動。請讓失效操作與持有權檢查具原子性，並驗證失鎖時不會清除新持有者資料。
- **P1／DB commit 後可能留下過時快取：** 即使最終發布有 token 檢查，A 在 DB transaction 期間失鎖後，B 可能先從 DB 載入並發布快照；A 隨後 commit，於 `ensure_held()` 失敗而回 503，但 B 的快照仍留在 Redis。這違反計畫 §6.3「DB 已 commit 但發布失敗時 key 保持缺失」與下一次讀取重建的要求。需處理 lease 在 DB 異動期間失效的時序，避免留下已知過時快照。
- **P2／快照仍可缺少正式標籤名稱：** `ProductCacheRepository.replace_products()` 的 `label_names_by_id` 仍為選填；`__product_to_value()` 在產品有 `label_ids` 卻未提供映射時寫入空 `label_names`，而 `__product_from_value()` 將數量不符的名稱設為 `None`，使已存在快照的讀取路徑再次依賴標籤快取。計畫 §6.3 要求完整快照保存並重讀標籤名稱；請避免發布這種不完整快照。

結論：Review Status 維持 `OPEN`；TASK-004 交回 Programmer 修正。

## 2026-09-30 最終複審

- 產品與標籤快取的失效操作均以 Lua 同時驗證 lock token 與清除 key；失鎖者無法清除新持有者的快照，失效失敗會在 DB 異動前中止。前次失效競爭問題已解決。
- 產品快取以 version fence 保護快照發布；DB commit 後發布失敗時，Service 透過 `invalidate_after_commit()` 遞增版本並清除快照，防止較早讀取的 writer 發布過時資料。冷載入持相同產品鎖重建。對應 writer／cold loader 交錯及真實 Redis Lua 測試已通過。
- `replace_products()` 要求標籤名稱映射，缺少名稱時拒絕發布；讀取時還原完整 `label_names`，不完整快照會報錯。前次快照內容問題已解決。
- 使用專案 `.venv` 與 `.env` 中的整合連線執行完整 pytest：254 passed、0 skipped、1 個 Starlette deprecation warning。

結論：Review Status 為 `RESOLVED`；TASK-004 標記 `DONE`。
