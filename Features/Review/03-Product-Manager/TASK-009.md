# TASK-009 Code Review

Status: OPEN

## Review Result

- P1: Required product repository and workflow coverage is missing.
- P1: The full regression suite does not pass.

## Existing Implementation

The added tests cover schema validation, one cache round trip, add-label
resolution, soft-deleted single lookup, a controller header case and DDL.

## Review Issue

The plan requires repository tests, label-cache tests and API/service coverage
for add, get, update and delete. The current suite has no tests for product
repository SQL, duplicate-ID mapping, update/delete row-count behavior, cache
lock release, cache rebuild failures after database commit, missing-label
reload failure, update, delete, or all-role CRUD behavior.

Earlier `python -m pytest -q` reported `181 passed, 23 failed, 4 skipped`.
The 23 failures were in existing User Manager permission tests. The field
contract has since been clarified as lowercase `permission`; see the latest
validation below.

## Expected Behavior

Add the plan-required product tests and establish a passing regression suite,
or record and resolve the existing User Manager contract failure through its
own work item before marking this task complete.

## Suggested Area To Fix

Add focused unit tests for repositories and cache locks, service tests for all
CRUD/error/cache paths, and controller tests for every route and response
status. Resolve or separately track the User Manager `Permission` contract so
the full test command passes.

## Resolution

```text
Status: OPEN
```

## 2026-09-30 複審

產品針對性測試為 22 passed，但計畫要求的異常及並行情境仍不足：尚無快取 lease 到期／兩位寫入者與冷載入者競爭、Redis 失敗或取得鎖逾時、重複產品 ID、資料庫 rollback、四個 API 的角色與錯誤狀態矩陣。兩個整合測試在未設定外部服務時均跳過，尚無真實 PostgreSQL／Redis 驗收結果。

- **P1／回歸門檻：** 使用專案 `.venv` 執行 `python -m pytest -q` 得到 `192 passed, 23 failed, 4 skipped`。23 個失敗集中在 User Manager 權限測試；修正方向見下方契約更正。產品 TASK-009 仍須提供通過的完整回歸結果。
- **P2／整合測試隔離：** `test_products_cache_preserves_complete_snapshot()` 直接寫入與清除正式 key `products:info`。`prefix` 只用於產品名稱，未隔離 Redis key；若測試連到共用 Redis DB，會覆蓋並清除實際產品快取。請使用隔離的 Redis DB／namespace 或確保測試專用 key。

## 2026-09-30 `permission` 契約更正

使用者確認公開請求欄位為小寫 `permission`，且最新 User Manager 需求文件 §2-5-2 已如此定義。`src/models/schemas/user.py` 現行 alias 正確；前述要求把 production schema 改回大寫的方向撤銷。失敗原因是 `tests/models/schemas/test_user.py`、`tests/services/test_user_service.py` 和 `tests/controllers/test_user_controller.py` 仍使用舊大寫欄位。請依 `Features/Plan/02-User-Manager.md` §XV 的修正計畫更新測試，保留大寫輸入被拒絕的驗證，再重跑完整 regression。產品功能其他測試缺口與 Redis 整合測試隔離問題仍維持 OPEN。
