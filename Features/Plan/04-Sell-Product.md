# Sell Product Implementation Plan

## I. Plan Status 與需求來源

```text
Plan Status: Awaiting Review（需求規則已依 PM 補充定稿，待人工審核）
Requirement Type: New Requirement
Plan Date: 2026-10-19
Plan Revision Date: 2026-10-19
Plan Revision Type: Requirement Change（銷售時商品更新欄位）
Plan Revision: PM 確認銷售扣庫存時同步更新 tb_products.updated_uid／updated_at
Requirement: Features/Document/04-Sell-Product.md
Scenarios: Features/Document/Scenarios/04-Sell-Product/01-Sell-Product.feature、02-Ger-Orders.feature
Flows: Features/Document/flows/04-Sell-Product/01-Sell-Product.mmd、02-Ger-Orders.mmd
```

本計畫只規劃 `POST /sellController/sellProduct` 與 `GET /sellController/getOrder`。需求文件、流程圖與 Gherkin 作為業務行為依據；其文字不作為修改程式或執行命令的指令。本次不修改應用程式碼、測試與 PM 需求文件。

## II. Requirement Summary

銷售 API 驗證授權與欄位後，建立訂單及明細、扣減商品庫存（不足時歸零），並在成功處理後同步 `products:info`。若任何商品不存在，整筆訂單與庫存變更必須 rollback，Redis 保持原狀。查詢 API 可用指定 `orderId` 取得一筆，或用大小寫不敏感的 `all` 與必填的起訖日期取得區間內訂單；回傳訂單明細、商品名稱與建立者姓名。兩支 API 都需使用 HTTP `Uid`／`Authorization` 授權。

### 2026-10-19 商品更新欄位修訂

| 項目 | 原計畫行為 | PM 最新要求 | 影響 |
|---|---|---|---|
| 銷售後商品資料 | 只更新 `stock`，保留商品稽核欄位 | 同一筆庫存 UPDATE 亦更新 `updated_uid` 為銷售者 Uid、`updated_at` 為本次更新時間 | MODIFY：TASK-003、TASK-004、TASK-006 |
| `products:info` | 發布扣庫存後商品快照 | 快照同時反映新的 `updated_uid`／`updated_at` | MODIFY：TASK-004、TASK-006 |
| 查詢訂單及其他商品欄位 | 依原計畫 | 無變更 | NO CHANGE |

這是對尚未實作之新功能計畫的修訂，受影響 Task 仍維持 `TODO`；原先「保留商品稽核欄位」的敘述由本節取代。

## III. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implementation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| TASK-001 | Order DDL / PO | ADD | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |
| TASK-002 | Order API Schema / Errors | ADD | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |
| TASK-003 | Order / Stock Repository | ADD / MODIFY | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |
| TASK-004 | Sell / Get Order Service | ADD | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |
| TASK-005 | Sell Controller / Dependency / Router | ADD / MODIFY | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |
| TASK-006 | Unit / Integration Tests | ADD | 2026-10-19 | DONE | 2026-10-19 | 2026-10-19 |

## IV. Requirement Validation 與契約差異

### 4.1 已確認的規則

- 銷售項目必須有有效 `productId`、正整數 `quantity`、非負且非空的 `price`；`discount`、`totalAmount`、`totalDiscount` 為非負，`totalAmount` 不可為空。金額使用十進位數，資料表型別 `NUMERIC(10,2)`。
- PM 確認：每筆 `discount` 是商品折後單價；`totalDiscount` 是整筆訂單的折後總額，在正常計算下為各筆 `quantity × discount` 加總；後端只記錄請求值，不重新計算或驗算兩者是否相等。Gherkin 的 `totalDiscount=700` 對應 `2×150+2×200`。`totalAmount` 與商品 `price` 仍依需求記錄，不新增跨欄位驗算。
- PM 最新確認：銷售扣庫存時同步更新 `tb_products.updated_uid` 為本次銷售者的 `Uid`，`updated_at` 為本次銷售更新時間；商品名稱、標籤、成本、售價等其他欄位不變。此修訂取代先前「兩欄保持原值」的回覆。查無訂單回 HTTP 404。
- PM 確認：訂單 ID 可用資料庫序號產生唯一且遞增的 10 位字串；`orderItems` 至少一筆，單張訂單不可重複 `productId`。
- PM 確認：`delete_flag=true` 的商品不可銷售；現有 `admin`、`manager`、`user` 三種角色皆可呼叫銷售與查詢 API。
- PM 確認：商品不存在回 HTTP 400；銷售與查詢 API 的一般欄位驗證失敗回 HTTP 400。前者訊息依 Gherkin 為「商品不存在」；日期缺失／超區間使用需求指定訊息；其餘錯誤沿用既有 Bad Request 封套。
- 有效商品即使庫存小於銷售數量也完成銷售，庫存以零為下限。商品不存在則整筆 PostgreSQL 交易 rollback，且不得變更產品快取。
- `orderId=all` 不分大小寫，需提供 `startDate`、`endDate`，日期格式為 `YYYY-MM-DD`，區間不得超過 30 天；缺少日期的錯誤訊息依原文。指定訂單 ID 時忽略附帶日期。
- `createdBy` 由 `tb_orders.created_uid` 關聯現有 `tb_users.uid`，輸出使用者姓名欄位；`productName` 由 `tb_products.id` 關聯現有 `tb_products.name`。既有資料庫欄位名稱是 `user_name`，並非需求情境表格中的 `name`。

### 4.2 Open Questions（不阻礙本次設計）

| 問題 | 文件現況 | 影響 |
|---|---|---|
| 查詢歷史訂單時關聯資料缺失 | 文件要求以 `tb_users`／`tb_products` 取得名稱，但未定義後續刪除造成關聯資料不存在的輸出 | 現有商品僅軟刪除、使用者無刪除 API；本次按現存資料查詢，未來若加入物理刪除應另行定義歷史名稱保留策略 |
| Redis 更新失敗 | 要求每筆訂單後更新 Redis，但沒有 DB commit 後失敗時的外部回應 | 沿用既有快取不可用 503 封套及失效流程，log 明確標示 DB 已提交；若 PM 要求不同結果，需另行調整契約 |

以上不新增業務規則；列出日後資料生命週期或錯誤契約變更時需重新檢查的事項。金額語意、商品稽核、配號、明細、權限及狀態碼均已依 PM 2026-10-19 最新回覆定稿。

### 4.3 文件與現有系統差異

| 文件 | 現有系統 | 計畫處理 |
|---|---|---|
| `tb_orders_item`／`tb_orders_items` 兩種拼法 | 目前沒有訂單表 | 依 §3-4 明列 Table Name 及專案複數命名規範，採 `tb_orders_items`；不建立兩張表 |
| 商品 ID 範例 `P123456` | `tb_products.id` 為 13 位數字字串 | 銷售欄位對應現行商品 ID；範例需由 PM 核對，不自行改商品 ID 規格 |
| `tb_users` 情境使用 `id`、`name` | DDL 是 `uid`、`user_name` | 使用實體欄位 join，API 對外仍為 `createdBy` |
| 銷售 Gherkin 的商品 `updated_at` 改變、`updated_user` 維持舊值 | PM 最新確認銷售者應寫入 `updated_uid`，且更新 `updated_at`；實體欄位是 `updated_uid` 而非 `updated_user` | 依最新確認更新兩欄；Gherkin 的 `updated_user` 範例若與銷售者 Uid 不同，需由 PM 更新情境期望 |
| 文件稱訊息在 `Headers` | 既有封套同時回 JSON `headers` 及實際 HTTP `Status`／`Message`，中文 HTTP 訊息會編碼 | 延用現有 `build_envelope`／`synchronize_authorization_headers`／全域錯誤 handler；不改共用契約 |
| 文件以 `Status=200/400/401` 表示結果 | 現有 HTTP status 承載數值，`Status` header 使用 `Success`／`Failed`／`Unauthorized` 等授權狀態 | 訂單 API 依 PM 確認設定 HTTP 200／400／401／404；`Status` header 沿用共用授權狀態，`Message` 使用需求指定的 OK／Bad Request／Unauthorized 或明確中文訊息 |
| 文件標示 400 參數錯誤 | 既有 FastAPI／Pydantic 驗證回 422 | PM 確認兩支訂單 API 的一般欄位錯誤回 400；僅對 `/sellController/` 路徑映射，既有 API 的 422 契約不變 |

## V. Existing System / Technology Context

- Python 3.14、FastAPI 0.141.1、Pydantic、pytest；PostgreSQL 17 由 psycopg async pool 存取，Redis 8 經 `redis.asyncio`。依 `instructions/architecture.md` 採 Controller → Service → Repository → Database。
- `src/main.py` 註冊 router 並統一處理 `ApplicationError`、`RequestValidationError`；`src/controllers/user_controller.py` 提供成功／失敗封套與 HTTP headers helper。`src/controllers/dependencies.py` 組裝授權、資料庫與 Redis 依賴。
- `src/services/authorization_service.py` 的 `validate_session()` 驗證 JWT、uid、Redis session，`refresh_session()` 延長到期時間；現有 DEBUG 缺 token 旁路行為需沿用，不可為訂單功能自行更改。
- `src/repositories/product_repository.py` 有 `transaction()` 與產品查詢，但沒有庫存扣減方法；`src/repositories/product_cache_repository.py` 有 `products_lock()`、`invalidate_products()`、`replace_products()`、`invalidate_after_commit()`；`src/services/product_service.py` 的快取發布流程可作設計範例。`src/repositories/user_repository.py` 可按 uid 查使用者。
- 已確認 DDL 僅有 `TB_USERS.sql`、`TB_PRODUCTS.sql`、`TB_LABELS.sql`；沒有訂單 controller、service、repository、PO、schema、DDL 或測試。`tb_products.stock` 為 `INTEGER NOT NULL DEFAULT 0`；`products:info` 是完整產品快照，含軟刪除商品。現有 Product 更新與銷售更新必須遵守相同鎖序，避免快取覆蓋。
- 本需求不需新增第三方套件、環境變數或外部服務。Docker／WSL 執行方式與現有專案一致。

## VI. System Design

### 6.1 銷售資料流與交易

`Controller → SellService → OrderRepository / ProductRepository → PostgreSQL`。先驗證授權與請求（至少一筆且商品 ID 不重複），取得 `products:info` 的現有 Redis lock，於單一 PostgreSQL transaction 中依固定商品 ID 順序鎖定庫存列，確認每項商品存在且 `delete_flag=false`。**確認所有商品有效後、第一筆 DB 寫入前** 才使舊產品快照失效，以滿足商品不存在時 Redis 保持原狀。其後以 PostgreSQL sequence 配號、補零為 10 位字串，寫入 `tb_orders` 與 `tb_orders_items`，把每項庫存更新為 `max(0, stock − quantity)`，並在同一 UPDATE 中把 `updated_uid` 設為銷售者 Uid、`updated_at` 設為本次更新時間；不得覆寫其他商品欄位。不採 `COUNT(*)+1`；sequence 由資料庫保證併發唯一，交易 rollback 後可能有缺號，不影響後續 ID。任何商品不存在或 DB 寫入失敗均 rollback；後者若已使快取失效，可由既有冷載入流程重建，但不得發布未提交的變更。序號超出 10 位時拒絕寫入並記錄服務錯誤，不截斷或重用 ID。

DB commit 後、仍持有產品 lock 時，由資料庫重新讀取完整商品清單並以現有 label mapping 更新 `products:info`。若 commit 後 Redis 發布失敗，呼叫既有 `invalidate_after_commit()` 防止陳舊快照，記錄訂單 ID、操作階段與「DB 已提交」狀態，絕不可回報訂單已 rollback。成功後依現有保護 API 模式 `refresh_session()`。Redis 寫入與 PostgreSQL 交易無跨系統原子性；此風險需在驗收中測試。

### 6.2 查詢資料流

`orderId=all` 時先檢查缺日期與日期格式、順序及 30 日上限；使用參數化查詢依 `tb_orders.created_at` 篩選，再批次取得對應明細、使用者與商品名稱，組成每張訂單的 `orderItems`。日期邊界須包含 `endDate` 當日完整時間，避免 `created_at` 的時間部分被漏掉。指定訂單 ID 時不使用日期參數。查詢結果需固定排序，避免整合測試與前端顯示不穩；排序方向由 PM 若有要求再定。避免每張訂單／每筆明細個別查詢造成 N+1。查詢不讀產品快取，商品名稱來源是需求指定的 `tb_products`。

### 6.3 API、錯誤與安全

維持需求 URI、POST／GET 方法與 `headers`／`body.info` 封套。HTTP `Uid`／`Authorization` 經既有 `AuthorizationObject`、`AuthorizationService`；現有 `admin`、`manager`、`user` 均可使用兩支 API。授權失敗沿用現有 401／session mismatch 契約。兩支訂單 API 的欄位驗證、空／重複項目、非法日期或 ID 均回 400；缺日期及超區間使用需求指定中文訊息。商品不存在或已軟刪除回 400／「商品不存在」，且不寫任何資料；查無訂單回 404／「訂單不存在」。DB／Redis 故障沿用現有 service unavailable 503 路徑；不記錄 token、密碼或完整 request body。

## VII. Implementation Steps

### TASK-001 Order DDL / PO

```text
File: database/DDL/tables/TB_ORDERS.sql、database/DDL/tables/TB_ORDERS_ITEMS.sql（新增）；src/models/po/order.py（新增）
Target: tb_orders、tb_orders_items；OrderPO / OrderItemPO（新元件，名稱於新增時採用）
Plan Type: ADD
Current Behavior: 訂單表與 PO 均不存在。
Expected Behavior: 訂單主表保存 10 碼 id、total_amount、total_discount、created_uid、created_at；明細保存 order_id、product_id、quantity、price、discount、created_at、created_by。
Implementation: 依需求 §3-3/3-4 建 PostgreSQL NUMERIC(10,2)、TIMESTAMP、VARCHAR 欄位，order_id 建 FK 參照 tb_orders.id；主表 id 為 PK。明細增設技術性 `id BIGINT GENERATED BY DEFAULT AS IDENTITY` 作為 PK，另以 UNIQUE(order_id, product_id) 保證同單不可重複商品，且允許一單多品；該 id 不對外回傳。`TB_ORDERS.sql` 同時建立 `seq_tb_orders_id`，從 1 遞增；order ID 由應用程式取 nextval 後補零到 10 位，主表 id 仍為 VARCHAR(10)。created_uid/created_by 長度應與既有 tb_users.uid 的 VARCHAR(256) 一致；product_id 與 tb_products.id 的 VARCHAR(13) 一致。表／欄位加 COMMENT。同步建立 PO 欄位 mapping。
Reuse: src/models/po/product.py、src/models/po/user.py 的 dataclass 模式；現有 DDL 風格。
Impact: 新增兩張表；既有 tb_products、tb_users DDL 不變。
Error Handling: DB 約束阻止孤兒明細、同單重複商品與重複訂單 ID；資料庫錯誤由 repository 轉換。
Testing: DDL 實際建表、FK、UNIQUE(order_id, product_id)、一單多筆明細、金額精度、序號補零與 rollback 測試。
```

### TASK-002 Order API Schema / Errors

```text
File: src/models/schemas/order.py、src/services/order_errors.py、src/constants/order.py（新增）
Target: Sell / GetOrder request、response schema；訂單專用錯誤與訊息常數
Plan Type: ADD
Current Behavior: 無訂單 API schema 或錯誤類型。
Expected Behavior: JSON headers + body.info 及現有 HTTP response headers 契約；欄位輸出為需求 camelCase。
Implementation: 參照 ProductEnvelope，定義銷售 info 與每筆項目、銷售 response、查詢 response 列表；Pydantic 驗證 13 位商品 ID、正整數、非負 Decimal、必填欄位、資料表精度，以及 orderItems 至少一筆且 productId 不重複。`discount` 與 `totalDiscount` 按 PM 確認分別記錄商品折後單價及訂單折後總額，不進行跨欄位驗算。`createdAt` 輸出 YYYY-MM-DD HH:MM:SS。金額 JSON 表示沿用現有 Decimal serializer。日期缺失、過長及商品／訂單不存在以 ApplicationError 子類表達；商品不存在固定 HTTP 400／「商品不存在」，訂單不存在固定 HTTP 404／「訂單不存在」。
Reuse: src/models/schemas/product.py 的封套、Money 類型設計；src/services/errors.py 的 ApplicationError；既有 response helper。
Impact: 只新增訂單 schema、error、constant；不改產品 request／response。
Error Handling: all 日期錯誤、一般欄位錯誤及商品不存在回 400；訂單不存在回 404。
Testing: schema 正常、零／負數、缺欄、空項目、重複商品、金額精度與日期序列化；確認不做跨欄位加總驗算。
```

### TASK-003 Order / Stock Repository

```text
File: src/repositories/order_repository.py（新增）；src/repositories/product_repository.py（修改）；src/repositories/user_repository.py（視批次查詢需要修改）
Target: OrderRepository；ProductRepository 的交易內鎖列與扣庫存方法；UserRepository 批次 uid 查詢
Plan Type: ADD / MODIFY
Current Behavior: 無訂單存取；現有 ProductRepository 只支援商品建立／查詢／整筆更新／軟刪除。
Expected Behavior: 同一 connection/transaction 寫訂單、明細與庫存；查詢可一次取得訂單及關聯資料。
Implementation: OrderRepository 使用既有 psycopg async pool；新增交易內 sequence nextval、主表／明細 INSERT、依 ID／日期查詢及批次明細查詢。銷售時商品讀取應使用 `FOR UPDATE` 或等價行鎖；以 DB 中最新 stock 計算，並以同一 SQL UPDATE 更新 stock、updated_uid、updated_at；updated_uid 由已驗證的本次銷售者 Uid 提供，updated_at 使用本次銷售更新時間。不覆寫 label、cost、price、delete_flag 等其他資料。多商品按固定 product_id 順序取得鎖，避免死鎖；缺商品或 delete_flag=true 時拋明確 domain error 供 service rollback。序號不超過 9999999999，超限拒絕寫入；不讀 COUNT(*) 配號。SQL 參數化、查詢日期使用半開區間。
Reuse: ProductRepository.transaction()、get_by_id_in_transaction() 的 connection 模式；UserRepository 的 PO mapping。
Impact: 既有商品管理路由與商品資料欄位保持；庫存競爭與產品快取寫入需回歸。
Error Handling: psycopg error 轉 repository error；unique/FK/lock 失敗不能留下部分資料。
Testing: 交易 rollback、兩筆商品的 stock／updated_uid／updated_at 同步更新、重複項目被拒、軟刪除商品被拒、並行銷售／商品更新、ID 併發與日期邊界。
```

### TASK-004 Sell / Get Order Service

```text
File: src/services/sell_service.py（新增）
Target: SellService.sell()、SellService.get_order()（新方法）
Plan Type: ADD
Current Behavior: 無銷售／訂單查詢流程。
Expected Behavior: 依 VI 節完成授權、單一 DB 交易、商品快取發布及訂單資料組裝。
Implementation: 將 Controller 輸入轉為 service 參數；授權後查使用者且允許 admin、manager、user。銷售先檢查所有商品存在且未軟刪除，再以同一筆交易提交訂單、庫存與商品 updated_uid／updated_at；updated_uid 使用已驗證的銷售者 Uid，updated_at 使用本次更新時間，失敗時一併 rollback。DB commit 後沿用 ProductCacheRepository 的鎖／失效／重建流程，並使用 LabelCacheRepository／LabelRepository 供既有 replace_products() 取得名稱。查詢時將 user_name、product.name 映射 createdBy、productName。成功後刷新登入 session。金額只記錄、不驗算。
Reuse: AuthorizationService、UserRepository、ProductCacheRepository、ProductService 的快取一致性處理模式（僅參考流程，避免複製整個 ProductService）。
Impact: 需要與現有 ProductService 共用 products:info lock 規約，防止商品管理操作覆蓋銷售後庫存。
Error Handling: 商品不存在不提交 DB；commit 後 Redis 失敗明確記錄已提交並失效快取；refresh_session 失敗不得誤稱訂單已回滾。
Testing: 成功、庫存不足歸零、商品不存在全部 rollback、快取冷載入／既存更新／發布失敗、查詢 all／單筆、授權錯誤。
```

### TASK-005 Sell Controller / Dependency / Router

```text
File: src/controllers/sell_controller.py（新增）；src/controllers/dependencies.py、src/main.py（修改）
Target: POST /sellController/sellProduct、GET /sellController/getOrder；get_sell_service()；router 註冊
Plan Type: ADD / MODIFY
Current Behavior: 現有 main 只註冊 user/product router。
Expected Behavior: 接收 HTTP Uid／Authorization，回應需求封套與授權後資料；Query 依 orderId 分支驗證。
Implementation: 用 Depends 組裝 PostgreSQL、Redis、授權與 repository；controller 只負責 parsing、呼叫 service、套用 build_envelope 及 synchronize_authorization_headers；實際業務與交易留在 service。src/main.py 的 RequestValidationError handler 僅對 `/sellController/sellProduct` 與 `/sellController/getOrder` 兩支 API 回 400／Bad Request，其他路由維持既有 422，保持原有 JSON／HTTP headers 同步。OpenAPI responses 宣告 200／400／401／404／503 等已確認狀態。
Reuse: src/controllers/product_controller.py 的 Header/Response 接線；src/controllers/user_controller.py 的封套與 header helper。
Impact: 新增兩個 endpoint，現有 API 不變。
Error Handling: 使用 src/main.py 既有全域 ApplicationError／RequestValidationError handler，新增路由限定的驗證狀態映射。
Testing: TestClient/ASGI request、OpenAPI route、HTTP headers、JSON envelope、授權失敗、欄位錯誤 400、既有產品欄位錯誤仍為 422，以及中文錯誤訊息編碼。
```

### TASK-006 Unit / Integration Tests

```text
File: tests/models/schemas/test_order.py、tests/repositories/test_order_repository.py、tests/services/test_sell_service.py、tests/controllers/test_sell_controller.py、tests/integration/test_sell_product_integration.py（新增）
Target: 對應 TASK-001～005 與兩份 Gherkin
Plan Type: ADD
Current Behavior: 無訂單測試；現有測試涵蓋產品／使用者功能。
Expected Behavior: 正常、邊界、錯誤及跨服務一致性均有可重現驗證。
Implementation: Unit test mock DB/Redis 邊界；integration test 使用 PostgreSQL 17、Redis 並隔離測試資料，檢查資料表、快取與 HTTP 回應。將銷售 Gherkin 三情境與查詢 Gherkin 六情境映射為測試；商品銷售後斷言 stock、updated_uid、updated_at 均已更新，且 Redis `products:info` 反映相同值；Gherkin 的 updated_user 舊值範例與 PM 最新確認衝突時，依最新確認驗收，不修改 PM 情境檔。增測 30 天邊界、錯誤日期、跨午夜、同時下單 ID 唯一、同時扣庫存、空／重複商品項目 400、軟刪除商品 400、三角色授權、一般欄位錯誤 400 及 Redis 發布故障。回歸 tests/integration/test_product_manager_integration.py 及產品快取相關單元測試。
Reuse: tests/integration/test_product_manager_integration.py 的 fixture/隔離方式及現有 pytest 設定。
Impact: 不更改現有測試的業務預期。
Error Handling: 明確驗證 missing product 時 orders/items/products/cache 均無變更；commit 後快取故障時驗證 DB 已提交與失效處理。
Testing: venv 中執行相關 pytest；若 Docker 整合環境可用，再執行 PostgreSQL/Redis integration 與全套回歸。
```

## VIII. Plan Validation / Review

- [x] 判定為 New Requirement；兩支 API、兩份流程與九個 Gherkin 情境已納入。
- [x] 現有架構、授權、DB／Redis、快取、錯誤、測試模式與實際檔案路徑已檢查。
- [x] 新增檔案以「新增」標明，既有 class／method 名稱已由專案驗證。
- [x] API、DB、Redis、交易、回滾、安全、回歸測試與相容性影響已列出；無新套件或環境變數。
- [x] 查無訂單 HTTP 404 已由 PM 確認。
- [x] 金額語意與只記錄不驗算、商品銷售時更新 updated_uid／updated_at 已由 PM 最新回覆確認。
- [x] ID 配號、明細邊界、軟刪除、角色與 400 錯誤契約已由 PM 確認並反映於 Task。
- [x] 已重新檢查規則與 Task、測試及回歸範圍的一致性。
- [ ] Implementation Plan 人工審核；Development；Code Review。

Review Status: **Awaiting Review**。本計畫可供 PM／Reviewer 逐項核對；人工審核完成後 handoff Programmer Agent。Handoff 範圍僅此兩支 API、新訂單表、商品庫存與產品快取更新；不得修改其他產品／使用者業務規則或需求文件。
