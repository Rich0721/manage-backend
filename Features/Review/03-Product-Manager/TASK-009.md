# TASK-009 Code Review

Status: RESOLVED

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
Status: RESOLVED
```

## 2026-09-30 複審

產品針對性測試為 22 passed，但計畫要求的異常及並行情境仍不足：尚無快取 lease 到期／兩位寫入者與冷載入者競爭、Redis 失敗或取得鎖逾時、重複產品 ID、資料庫 rollback、四個 API 的角色與錯誤狀態矩陣。兩個整合測試在未設定外部服務時均跳過，尚無真實 PostgreSQL／Redis 驗收結果。

- **P1／回歸門檻：** 使用專案 `.venv` 執行 `python -m pytest -q` 得到 `192 passed, 23 failed, 4 skipped`。23 個失敗集中在 User Manager 權限測試；修正方向見下方契約更正。產品 TASK-009 仍須提供通過的完整回歸結果。
- **P2／整合測試隔離：** `test_products_cache_preserves_complete_snapshot()` 直接寫入與清除正式 key `products:info`。`prefix` 只用於產品名稱，未隔離 Redis key；若測試連到共用 Redis DB，會覆蓋並清除實際產品快取。請使用隔離的 Redis DB／namespace 或確保測試專用 key。

## 2026-09-30 `permission` 契約更正

使用者確認公開請求欄位為小寫 `permission`，且最新 User Manager 需求文件 §2-5-2 已如此定義。`src/models/schemas/user.py` 現行 alias 正確；前述要求把 production schema 改回大寫的方向撤銷。失敗原因是 `tests/models/schemas/test_user.py`、`tests/services/test_user_service.py` 和 `tests/controllers/test_user_controller.py` 仍使用舊大寫欄位。請依 `Features/Plan/02-User-Manager.md` §XV 的修正計畫更新測試，保留大寫輸入被拒絕的驗證，再重跑完整 regression。產品功能其他測試缺口與 Redis 整合測試隔離問題仍維持 OPEN。

## 2026-09-30 再複審

完整 pytest 為 `224 passed, 4 skipped`；`permission` 回歸及 Redis 整合測試 key 隔離已修正。下列計畫要求仍缺驗證：

- **P1／並行一致性測試不足：** 現有 cache 測試只模擬單一 lease 的續租、失鎖檢查及取得逾時，沒有兩個寫入者與冷載入者交錯時的快照結果；因此未揭露 TASK-004 所述的失鎖後舊資料覆蓋。
- **P2／API 與整合測試缺口：** Controller 僅測新增 header、非法 ID 與三條路由的成功回應，尚未覆蓋四項操作的角色及 400／401／404／409／503 錯誤。產品 PostgreSQL 整合測試僅驗證 DDL 和一筆軟刪除資料，Redis 整合測試僅驗證 round trip；沒有驗證真實 transaction rollback、lock／lease 與快取失效後重建。兩個產品整合測試本輪均因未設定外部連線而跳過，故尚無真實 PostgreSQL／Redis 驗收結果。

## 2026-09-30 修正複審

- **已修正：** 完整 pytest 為 235 passed、6 skipped；Controller 新增 400／401／404／409／503／500 envelope 測試，Service 新增三角色查詢測試，並新增 PostgreSQL rollback 與 Redis 失鎖整合測試。整合連線未設定，因此 6 項整合測試均依既有政策跳過；這不是實際 PostgreSQL／Redis 執行通過的證據。
- **P1／並行情境仍未覆蓋：** `tests/repositories/test_product_cache_repository.py` 與新增 Redis 整合測試僅以單一 lease 人為替換 lock token，驗證失鎖後 `replace_products()` 不覆寫；沒有兩位 writer 與 cold loader 交錯、失鎖後 `invalidate_products()`、DB commit 後發布失敗但新快照已存在的時序。計畫 TASK-004 Testing 與 TASK-009 的並行／快取一致性驗收仍缺。請加入能重現 TASK-004 本次發現時序的測試。
- **P2／產品操作與整合覆蓋仍不足：** `tests/services/test_product_service.py` 的角色參數化只測 `get(ALL)`，沒有驗證三種角色各自執行新增、更新、刪除；Controller 的新增錯誤表格由 `AsyncMock` 直接拋錯，只證明全域 handler，未驗證 Service 分支。新增整合測試雖涵蓋 rollback 與單一 lease 失效，仍未驗證計畫 §X 所列真實 Redis lock 競爭、快取失效後重建與 DB commit 後發布失敗保持 key 缺失。請補足與計畫相應的行為測試；外部服務缺席可依既有 skip 政策記錄。

結論：Review Status 維持 `OPEN`；TASK-009 交回 Programmer 修正。

## 2026-09-30 最終複審

- Repository 測試新增失鎖後不得失效新快照、兩位 writer 與等待中的 cold loader 交錯、commit 後版本失效及下一次重建；Service 測試已涵蓋三種角色各自新增、更新、軟刪除。前次 P1／P2 缺口已補足。
- 真實 Redis 整合測試使用獨立 key，驗證 lease 競爭、版本 fence 與 commit 後冷載入；PostgreSQL 整合測試驗證 transaction rollback。
- 使用專案 `.venv` 與 `.env` 中的整合連線執行 `python -m pytest -q`：254 passed、0 skipped、1 個 Starlette deprecation warning；整合測試實際執行，無 skip。

結論：Review Status 為 `RESOLVED`；TASK-009 標記 `DONE`。

## 2026-10-19 Docker 整合測試複審

```text
Status: OPEN
```

- **P1／真實 DB 提交後快取失敗情境未驗證：** `test_add_product_label_cache_failure_keeps_committed_rows_and_invalidates_caches` 使用 PostgreSQL `TEMP TABLE`，但此測試的 `DirectConnectionPool` 固定重用原始連線，交易結束後 `list_all()` 仍未讀到新增資料（0 筆）；因此該斷言無法證明 DB commit 後資料保留。需要使用符合 Windows selector loop 的測試 pool／schema 設定，或以其他方式在獨立連線可見的隔離 schema 中驗證提交結果。
- **P2／快取 snapshot 比較漏掉衍生欄位：** `test_add_product_creates_missing_label_and_refreshes_both_caches` 將 Redis 解碼後含 `label_names` 的 ProductPO 與 DB `list_all()` 回傳的 `label_names=None` 物件直接比較。產品快取依計畫應包含 label 名稱；請將斷言改為比較 DB 欄位並分別驗證快取衍生標籤名稱。
- Windows host 測試的 PostgreSQL URL 設為 `localhost` 時，psycopg async 連線停滯；使用相同服務的 `127.0.0.1` 可以連線。README 目前 instruction 建議先載入 `.env` 全部變數，而 `.env.example` 已提供 INTEGRATION_DATABASE_URL／INTEGRATION_REDIS_URL，之後將驗證文件建議的載入方式。

真實 PostgreSQL 17／Redis 8 目標服務可用；以 `127.0.0.1` 執行產品與使用者整合測試第一次得到 `14 passed, 2 failed`（一項為快取衍生欄位斷言，已修正；另一項為 TEMP TABLE 提交結果不可驗證）。修正快取斷言後，針對 Redis fencing 與 Add cache-refresh 的測試為 `2 passed`；完整整合測試的 Redis fencing 假失敗亦已由恢復 `dataclasses.replace` import 修正。完整 pytest 未載入整合 URL 為 `290 passed, 16 skipped`。

結論：Review Status 為 `OPEN`；TASK-009 標記 `REVIEW FIX`。

## 2026-10-19 新增商品標籤缺漏修訂審查

```text
Status: OPEN
```

- **P1／同名併發未驗證：** 最新計畫第 38 行明列「同名併發」。`tests/services/test_product_service.py:438-510` 只驗證單次新增與混合既有標籤；`tests/integration/test_product_manager_integration.py:602-742` 的新 Add 測試亦只驗證單次成功、rollback 與快取故障，沒有兩個同名 Add 並行後只建立一筆標籤的斷言。請補足兩個請求交錯的回歸驗證，確認標籤及產品交易與快取結果。
- **P2／新增路徑 ID 衝突未驗證：** 最新計畫第 37 行要求保留產品 ID 衝突 409。新缺漏標籤路徑在 `src/services/product_service.py:143-185` 先插標籤再插產品，產品重複 ID 時須 rollback 標籤且回 409；現有新增測試以一般 DB 失敗模擬 rollback（整合測試第 652-681 行），沒有此衝突案例。請驗證新路徑的 409 與標籤 rollback。

完整 pytest 結果為 288 passed、15 skipped；整合測試因未設定 PostgreSQL／Redis URL 而略過，本輪無真實服務驗收證據。`Features/Plan/03-Product-Manager-Batch-Excel.md` 與兩個 DDL 測試移除獨立 stock 遷移腳本依賴，符合 PM 已完成 ALTER 的現況；未見相關新問題。

結論：Review Status 為 `OPEN`；TASK-009 標記 `REVIEW FIX`。

## 2026-10-19 修正複審

```text
Status: RESOLVED
```

- `tests/services/test_product_service.py:518-594` 以兩個並行 Add 從相同舊標籤快照起跑，驗證僅一筆同名標籤、兩筆產品共用其 ID，且產品快取包含兩筆資料。原 P1 已解決。
- `tests/integration/test_product_manager_integration.py:696-757` 以重複產品 ID 觸發新標籤路徑衝突，斷言 `ProductConflictError`、新增標籤 rollback 及原產品不變。原 P2 已解決。
- 本輪針對性測試為 `21 passed, 14 skipped`；完整 pytest 由 Programmer 回報 `290 passed, 16 skipped`。整合測試因未設定 PostgreSQL／Redis URL 略過，未取得本輪真實服務執行通過的證據。

結論：Review Status 為 `RESOLVED`；TASK-009 標記 `DONE`。
