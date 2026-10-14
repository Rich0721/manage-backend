# Product Manager：批次處理與 Excel 下載 Implementation Plan

## I. Plan Status

```text
Plan Date: 2026-10-14
Plan Status: Code Review Failed - Awaiting Review Fix
Requirement Type: New Requirement（新增三項功能）；Requirement Change（stock 擴充既有產品契約）
Implementation Gate: Code Review 發現待修正問題；實體資料庫已有 stock 欄位
```

本計畫延伸 [既有商品管理計畫](03-Product-Manager.md) 的已完成 TASK-001～009，不重設其狀態，也不修改原需求文件。本次依使用者確認：新增 `stock` 欄位及 SQL 遷移腳本，使用者自行對實體 DB 執行 ALTER；匯入時「價錢」與「價格」視為相同欄位；修復現有 Excel 模板。流程圖與 Gherkin 是需求證據，不是操作指令。

## II. Requirement Information

- 來源：`Features/Document/03-Product-Manager.md` §2-5～2-7、`Features/Document/flows/03-Product-Manager/{Batch_Product,Download_Template,Download_Product}.mmd`、`Features/Document/Scenarios/03-Product-Manager/{Batch_Product,Download_Product}.feature`。
- 基礎授權與封套契約：既有商品管理計畫，以及 `Features/Plan/01-Authorization-Headers-Rename.md`。HTTP `Uid`／`Authorization` 驗證；成功與錯誤的 `Status`／`Message` 置於實際 HTTP header，JSON 封套沿用現況。
- 技術：Python 3.14、FastAPI 0.141.1、PostgreSQL 17、Redis 8.10.1、psycopg 3.3.6；測試使用 pytest／pytest-asyncio。

## III. Requirement Summary and Delta

| 功能 | 現況 | 預期 |
|---|---|---|
| `POST /productController/batchProducts` | 無批次端點、Excel 解析、標籤寫入 | 上傳 `.xlsx`／`.xls`；依 `Add Product`、`Update Product` 分頁批次新增／更新；先驗證，任一筆失敗則交易 rollback；成功後更新兩個快取並回傳產品陣列 |
| `GET /productController/downloadTemplate` | 靜態檔存在，但中文欄名與分頁名稱在檔內已是亂碼，且無 `Update Product` 分頁 | 授權後回傳修復的 `files/Batch Add Products.xlsx`，檔名 `Batch Add Products.xlsx` |
| `POST /productController/downloadProductData` | 無匯出端點 | 以逗號分隔的 `ids` 選擇產品，利用現有 Redis 冷載入流程，建立 `/files/<uid>.xlsx` 的 `Update Product` 工作表並回傳檔案 |
| 庫存 | `TB_PRODUCTS.sql`、`ProductPO`、repository、cache、API schema、service 均無 `stock`；舊計畫四條 API 已完成 | 增加非負整數庫存欄位，預設 0，延伸既有四條 API 與快取格式，避免批次與單筆操作互相覆蓋庫存 |

批次欄位：新增分頁 `商品名稱／商品分類／成本／價錢或價格／庫存`；更新分頁另有 `商品ID`。第一列為欄名，第二列起為資料；其他分頁忽略。`商品ID` 更新時必填且須存在；名稱必填、最多 255 字；分類必填，以逗號分隔，缺少分類時新增 `tb_labels`；成本與價錢必填、數字且不小於 0；庫存空白為 0。依負庫存 Gherkin 情境，庫存非負；實作前要以資料庫整數型別及現有單筆 API schema 保持一致。產品 ID 仍為 13 位 Unix 毫秒字串，批次連續新增須避免同毫秒重複。

## IV. Existing System Analysis

- `src/controllers/product_controller.py` 現有四條產品路由與 `result_envelope()`、`synchronize_authorization_headers()`；`src/controllers/dependencies.py` 建立 `ProductService`。
- `src/services/product_service.py` 的 `ProductService` 集中授權、商品操作、`__get_all_products()` 快取冷載入、`__get_labels()`、session refresh；現有單筆寫入會在 Redis product lock 內使快取失效、提交 DB、重建快照。`src/services/product_errors.py` 定義產品錯誤。
- `ProductRepository.transaction()` 已提供 psycopg 交易；`insert()`／`update()` 允許共用 connection；`LabelRepository` 目前只有 `list_all()`，需補標籤查詢／新增。`LabelCacheRepository` 與 `ProductCacheRepository` 各有 lock、原子替換；產品快取保存軟刪除記錄與 label 名稱。
- `database/DDL/tables/TB_PRODUCTS.sql` 無 `stock`。`database/DDL/tables/TB_LABELS.sql` 的名稱沒有唯一約束。`requirements.txt` 無 Excel 讀寫套件及 multipart 上傳依賴。
- `files/Batch Add Products.xlsx` 的 OOXML 內文字本身已是亂碼，不是終端顯示問題；目前只有 `Add Product` 可用分頁。模板須重新製作，不能直接以原檔作為合格範例。

## V. System Design

### 5.1 HTTP 與資料流

1. 三個端點沿用 `ProductService.__authorize()` 的 session／角色驗證與完成後 TTL 更新。上傳採 multipart 檔案欄位；`downloadProductData` 的 `ids` 使用現有 `ProductEnvelope` 的 `body.info`；檔案成功回應需仍同步實際授權 headers。錯誤沿用 `ApplicationError` 封套。下載成功回應為 Excel binary，`Content-Disposition` 使用需求指定檔名。
2. 批次流程：授權 → 副檔名及實際活頁簿格式檢查 → 只解析兩個指定分頁 → 表頭、型別及逐列規則驗證 → 查核更新 ID／分類 → 單一 PostgreSQL transaction 執行所有標籤及商品寫入 → commit 後更新 `product:labels` 和 `products:info` → 回傳本次寫入的產品陣列。驗證失敗或 DB 錯誤不得留下部分商品／分類資料。
3. 匯出流程：授權 → 切割 `ids` → 重用 `__get_all_products()`（key 缺失時從 DB 建立完整快取）→ 依輸入 ID 取得未軟刪除商品 → 使用快取正式分類名稱 → 建立 `Update Product` 工作表及指定六欄 → 寫入 `/files/<uid>.xlsx` → 回傳檔案。不得從 `ids` 組接檔案路徑；檔名僅用已驗證的授權 uid。
4. `/files` 對應 repo 的 `files/`；Docker 部署需確保該路徑存在且可寫，並處理同一 uid 的同時下載。檔案應先產生於同目錄暫存檔、關閉後原子替換 `<uid>.xlsx`；回傳時避免另一請求覆蓋造成傳輸中檔案變動。最終仍符合「舊檔先移除、輸出 `<uid>.xlsx`」的外部行為。

### 5.2 Validation／錯誤契約

- 非 Excel 副檔名：400，HTTP `Message`=`檔案格式不正確，請上傳Excel檔案`；副檔名正確但內容損毀亦不得進入資料庫寫入。
- 指定分頁缺必要欄名：400，分別回 `新增商品欄位缺失，請使用正確的Excel模板`／`修改商品欄位缺失，請使用正確的Excel模板`。`價錢` 與 `價格` 是同一價格欄；不得同時映射兩欄造成歧義。
- 指定分頁資料不完整或型別／範圍錯誤：400，分別回 `新增商品資料錯誤，請檢查Excel內容`／`修改商品資料錯誤，請檢查Excel內容`。實作須涵蓋負庫存、金額資料庫精度、重複更新 ID、Excel 公式／錯誤儲存格及浮點商品 ID 被改寫的風險。
- 更新的商品不存在：404，依需求使用 `<Product Name> Not Found`；若該列只有 ID 而無可用名稱，錯誤文字的選擇留待 Review 確認，不以技術推測改寫需求。DB 寫入失敗分別回 `新增<商品名稱>失敗，請檢查Excel內容`／`修改<商品ID>失敗，請檢查Excel內容`，交易 rollback。
- 無權限：401／`Unauthorized`。下載檔案不存在、IO 失敗、Redis／DB 失敗不得回傳 200；使用現有公開錯誤模式，不洩漏原始例外、檔案絕對路徑或 token。

### 5.3 交易與快取

- 所有指定分頁視為一次匯入；同一 `ProductRepository.transaction()` connection 完成標籤與商品寫入，任何一列失敗即 rollback。`LabelRepository` 新增方法需接受這個 connection，避免另開連線提前 commit。
- 沿用產品 cache lock 與標籤 cache lock，取得順序固定為 **產品 → 標籤**，與現有產品寫入後查標籤路徑相容。標籤讀取／新增須在鎖內重新查 DB，避免同時匯入產生重複標籤；不得用 Redis 的舊快取判定資料庫永遠沒有該分類。若資料庫已有標準化後重名且 ID 不同，沿用既有資料異常處理，不任意選取。
- 產品舊快照應在 DB 寫入前於產品鎖內失效；若 DB rollback，於鎖內從 DB 重建與原先一致的產品／標籤快取，並驗證無新資料殘留。DB commit 後再重建兩個快取；若發布失敗，已提交的 DB 無法藉由 Redis 回滾，應使可能過期的 key 失效、記錄已提交狀態並回 503，後續查詢可冷載入。這是 PostgreSQL／Redis 無共同 transaction 的既有系統限制，不把 503 說成 DB rollback。
- 商品 ID 同毫秒批次生成時應等待下一毫秒或採等價的 13 位時間戳唯一化方式，並保留 DB 主鍵衝突處理；不得改成其他 ID 格式。

## VI. Requirement List

| Task ID | Component | Plan Type | Plan Date | Implementation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| BXL-001 | Stock DDL、PO 與 repository | MODIFY | 2026-10-14 | DONE | 2026-10-14 | 2026-10-14 |
| BXL-002 | Stock schema、cache、單筆 service／API | MODIFY | 2026-10-14 | REVIEW FIX | 2026-10-14 | 2026-10-14 |
| BXL-003 | Excel 解析、模板與相依套件 | MODIFY | 2026-10-14 | REVIEW FIX | 2026-10-14 | 2026-10-14 |
| BXL-004 | 批次交易與標籤新增 | MODIFY | 2026-10-14 | REVIEW FIX | 2026-10-14 | 2026-10-14 |
| BXL-005 | 兩個下載服務與檔案回應 | ADD | 2026-10-14 | DONE | 2026-10-14 | 2026-10-14 |
| BXL-006 | 三條路由、錯誤與 request schema | MODIFY | 2026-10-14 | REVIEW FIX | 2026-10-14 | 2026-10-14 |
| BXL-007 | 單元、API 與整合驗證 | ADD | 2026-10-14 | REVIEW FIX | 2026-10-14 | 2026-10-14 |

## VII. Implementation Steps

### BXL-001 Stock persistence

```text
File: database/DDL/tables/TB_PRODUCTS.sql; database/DDL/tables/ALTER_TB_PRODUCTS_ADD_STOCK.sql（新增檔）；
      src/models/po/product.py; src/repositories/product_repository.py
Target: tb_products.stock, ProductPO, ProductRepository.list_all/get_by_id/insert/update
Plan Type: MODIFY / ADD migration
Current Behavior: DB／PO／SQL 無庫存；現有商品有資料，不能只改 CREATE TABLE。
Expected Behavior: 庫存是非負整數，既有列為 0；新建預設 0，所有讀寫包含 stock。
Implementation: 更新 CREATE TABLE 與 column comment；提供冪等性策略清楚的 ALTER 腳本，先為既有列填 0，再設 NOT NULL／DEFAULT 0；檢查實體 DB 的欄位存在與否後執行，勿自動重建表。擴充 PO 與 SQL mapping／參數。
Reuse: ProductRepository.transaction()、現有參數化 SQL。
Impact: 資料庫 schema 必須先由使用者完成 ALTER，再部署讀寫 stock 的應用程式。
Error Handling: 遷移失敗停止部署；repository 錯誤沿用 ProductRepositoryError。
Testing: 新舊列預設、insert/update/read、rollback、整數與非負邊界。
```

### BXL-002 Stock end-to-end contract

```text
File: src/models/schemas/product.py; src/repositories/product_cache_repository.py;
      src/services/product_service.py; tests/models/schemas/test_product.py;
      tests/services/test_product_service.py; tests/repositories/test_product_cache_repository.py
Target: ProductCreateInfo／ProductUpdateInfo／ProductResponseInfo、ProductPO cache JSON、ProductService.add/get/update/delete
Plan Type: MODIFY
Current Behavior: 單筆 API／快取沒有 stock；單筆更新會遺失新欄位語意。
Expected Behavior: 新增可帶 stock，空缺時預設 0；更新可帶 stock，舊客戶端未提供時保留原值；查詢與回應帶庫存；刪除保留原庫存。
Implementation: 擴充 schema、cache 序列化、service 建立與轉換；兼容部署期舊快取缺 stock 時須從 DB 重新建立，不默默當成真實 0。更新請求以「未提供」與明確傳入 0 區分，避免既有客戶端更新其他欄位時清除庫存。
Reuse: 現有欄位驗證、__get_all_products()、__write_product()。
Impact: 四條既有端點的 JSON response 增欄位；舊 request 仍可送出。
Error Handling: 受損舊 cache 走既有 cache 異常／失效重建策略。
Testing: 單筆新增／更新／查詢／軟刪除與快取冷載入 regression。
```

### BXL-003 Excel handling and static template

```text
File: requirements.txt; files/Batch Add Products.xlsx;
      src/services/product_excel_service.py（新增檔）
Target: .xlsx/.xls parser、.xlsx writer、既有模板
Plan Type: MODIFY
Current Behavior: 無 Excel 依賴；模板文字亂碼且缺更新分頁。
Expected Behavior: 解析兩種上傳格式，輸出 xlsx；模板有可讀的 Add Product／Update Product 分頁及規定欄名。
Implementation: 選用並鎖定經 Python 3.14 環境驗證的最小套件；建議以 openpyxl 處理 xlsx 讀寫、xlrd 處理傳統 xls 唯讀，另補 FastAPI multipart 依賴。解析器只產生已驗證的列資料，不做 DB 操作。修復模板並保留指定檔名；正式表頭使用「價錢」，上傳另接受「價格」。
Reuse: 現有 ProductWriteInfo 的名稱／金額限制概念，不將 Excel 業務規則放在通用 utils。
Impact: requirements 與 Docker build；Excel 檔案需可在容器讀取。
Error Handling: 非法檔案、受損活頁簿、格式不符轉成需求的 400 Message。
Testing: 兩格式、兩分頁、忽略其他分頁、亂碼模板修復、表頭別名與錯誤檔。
```

### BXL-004 Batch write

```text
File: src/services/product_service.py; src/repositories/label_repository.py;
      src/repositories/product_repository.py; src/services/product_errors.py;
      src/constants/product.py
Target: ProductService.batch_products（新增）, LabelRepository 的 connection-scoped 查詢／新增
Plan Type: MODIFY
Current Behavior: 只支援單筆寫入；分類不存在即拒絕。
Expected Behavior: 批次可建立分類，所有指定分頁在一次交易中新增／更新並產出結果。
Implementation: 先驗證全檔；鎖內以同一 DB connection 再查更新目標與分類，新增缺少分類，組合 label_ids，依列處理商品；保留 created 欄位並更新 updated 欄位。對已軟刪除商品沿用既有「不存在」規則；完成後刷新兩個 Redis key。鎖／回滾／發布失敗依 §5.3。
Reuse: __authorize()、__get_all_products()、ProductRepository.transaction/insert/update、兩個 cache repository lock。
Impact: tb_labels 寫入與兩個快取；不改單筆商品的「標籤必須已存在」規則。
Error Handling: 400／404／401／503 與指定 Message；不得吞掉 DB duplicate 或半途成功。
Testing: 混合分頁成功、多列失敗全回滾、標籤新增、同毫秒 ID、鎖競爭、快取一致性。
```

### BXL-005 Downloads

```text
File: src/services/product_service.py; src/services/product_excel_service.py;
      files/Batch Add Products.xlsx
Target: ProductService.download_template/download_product_data（新增）
Plan Type: ADD
Current Behavior: 無檔案下載功能。
Expected Behavior: 授權後下載模板或指定商品資料的 xlsx，並延長 session TTL。
Implementation: 模板用既有靜態檔；商品匯出使用 __get_all_products() 及已快取的 label_names，建立 Update Product 六欄，安全寫入 <uid>.xlsx 並提供下載。確認空 ids、未知 ID、已刪除 ID 的行為與現有商品查詢 404 邏輯一致。
Reuse: __authorize()、__get_all_products()、__refresh_session()、ProductResponseInfo 的分類轉換。
Impact: /files 需可寫；同 uid 下載需避免互相覆蓋傳輸中的檔案。
Error Handling: 檔案／DB／Redis 失敗採現有 ApplicationError 慣例並清理暫存檔。
Testing: 模板 bytes／檔名；Redis 命中與缺失；多 ID 順序、分類名稱、舊檔替換、並行下載。
```

### BXL-006 API boundary

```text
File: src/controllers/product_controller.py; src/models/schemas/product.py;
      src/constants/product.py; src/services/product_errors.py
Target: 三條新增路由、batch request／download ids schema、HTTP headers 與錯誤對應
Plan Type: MODIFY
Current Behavior: 只有四條商品路由，成功回 JSON。
Expected Behavior: batch 回既有 ProductListResponse；兩條下載成功回 xlsx binary，錯誤回既有 JSON 封套。
Implementation: 使用 ProductServiceDependency；上傳由 UploadFile 接收；binary response 設 Excel MIME、Content-Disposition 與授權 headers。POST 匯出解析 body.info.ids；FastAPI request validation 與需求 400 Message 的差別須在此邊界明確處理。
Reuse: header_auth()、synchronize_authorization_headers()、result_envelope()、error_responses()。
Impact: OpenAPI 新增端點；不改既有授權路由與全域 exception handler。
Error Handling: 依 §5.2；不要讓預設 422 取代已指定的 Excel 400。
Testing: method/path、multipart、binary header、401、400、404、現有 JSON 封套 regression。
```

### BXL-007 Verification

```text
File: tests/controllers/test_product_controller.py; tests/services/test_product_service.py;
      tests/repositories/test_product_repository.py; tests/repositories/test_label_repository.py;
      tests/repositories/test_product_cache_repository.py; tests/repositories/test_label_cache_repository.py;
      tests/integration/test_product_manager_integration.py; tests/models/schemas/test_product.py
Target: 三項需求及 stock 對既有流程的影響
Plan Type: MODIFY
Current Behavior: 測試只覆蓋原四條商品 API。
Expected Behavior: 正常／邊界／錯誤／交易／並行情境可驗證。
Implementation: 單元測試隔離 DB／Redis；整合測試用實際 PostgreSQL／Redis 驗證 migration、rollback、快取及檔案回應。依 Gherkin 驗證指定中文 Message，另納入使用者確認的價格別名。
Reuse: 既有 fixtures 與 integration skip／配置慣例。
Impact: 既有商品、User Manager 測試須維持通過。
Error Handling: 測試失敗須辨別需求文件示例與已確認規則的差異，不修改 PM 情境以掩蓋差異。
Testing: 目標測試及完整 pytest regression。
```

## VIII. Impact and Deployment

| Area | Impact |
|---|---|
| API | 三條新端點；原四條產品端點增加 `stock` 欄位，保留既有授權與封套 |
| Database | `tb_products.stock` schema／資料遷移；`tb_labels` 新增寫入方法，暫不加需求未定義的 unique constraint |
| Redis | `products:info` 增 `stock`；批次成功後同步 `product:labels`、`products:info`；沿用 lock／cache key |
| Configuration | 不新增 secret；Docker 需把 `files/` 安裝到應用並設為可寫 |
| Dependencies | 需 Excel xlsx 讀寫、xls 讀取及 multipart；鎖定版本前在 Python 3.14 venv 與 Docker 驗證 |
| Deployment order | 使用者先執行 ALTER 並核對資料，再部署新應用；不能只變更 CREATE TABLE SQL |
| Compatibility | 舊商品 request 可不帶 stock；舊快取格式需遷移／失效；新增商品回應含庫存，前端需接受增欄位 |

Excel 套件選擇依官方文件：openpyxl 提供 xlsx 處理，xlrd 2.x 僅讀取 xls；實作時應以專案 Python 3.14 實測版本相容性，避免把 `.xls` 交給 openpyxl。參考：[openpyxl PyPI](https://pypi.org/project/openpyxl/)、[xlrd 文件](https://xlrd.readthedocs.io/en/latest/)。

## IX. Open Questions and Documentation Sync

- 需求正文與匯出規格用「價錢」，`Batch_Product.feature` 更新情境用「價格」；使用者已確認匯入兩者等價。模板正式表頭用需求正文的「價錢」，PM 情境可保留別名示例。
- 更新失敗需求的 404 文字為 `<Product Name> Not Found`，但辨識主鍵為商品 ID；若檔案名稱欄也缺失，會先落入 400 格式錯誤。對存在合法名稱但 ID 不存在的情況，可使用該列名稱組訊息；請 Review 確認此對外訊息與既有 `Not Found` 一致性。
- `Batch_Product.feature` 的負庫存／負價錢情境，最後寫成「新增商品資料錯誤」而分頁是 `Update Product`；計畫依需求正文採「修改商品資料錯誤」。PM 文件由需求維護者同步。
- `Download_Product.feature` 的成功範例將兩個 `label_ids=1,2` 商品輸出成第一個僅 `label1`；計畫依需求正文及來源 ID 映射輸出 `label1,label2`。PM 文件由需求維護者同步。
- 模板目前有亂碼、缺更新分頁，使用者已確認本次修復。模板樣例資料不得在匯入後造成意外商品新增；可保留說明分頁，但只讓指定兩分頁進入處理。

## X. Plan Validation and Review

開發驗證：載入 `.env` 的整合測試連線後，`.venv\Scripts\python.exe -m pytest -q` 結果為 **277 passed**；商品管理整合測試 5 項全數通過。唯讀檢查確認實體資料庫已有 `tb_products.stock`，Redis `PING` 成功。`git diff --check` 通過。

- [x] 三項需求、流程、兩份 Gherkin、既有 Plan 與實作已核對。
- [x] 檔案／類別／方法僅引用已確認者；新增方法與檔案均明示為預計新增。
- [x] API、DB、Redis、部署、相依套件、授權、錯誤、測試與回滾邊界已分析。
- [x] 使用者對 SQL ALTER、價格別名及模板修復的決定已納入。
- [x] BXL-001～007 已完成實作、自我檢查與完整 pytest regression.
- [x] Code Review Agent 已審查並依結果設為 DONE 或 REVIEW FIX；待修正項目記錄於 `Features/Review/03-Product-Manager-Batch-Excel/`。
- [x] 唯讀檢查確認實體 DB 已有 `tb_products.stock` 欄位。

```text
Current Handoff: Review Issues OPEN
Next Handoff: Programmer Agent（修正 REVIEW FIX 後交回 Code Review）
Implementation Scope: BXL-001～007；三條 Excel API 與 stock 對既有產品流程的必要擴充
Important Constraints: DB 批次交易、兩個 Redis key 一致性、原四條 API regression、實體 DB stock 欄位已確認
Do Not Modify: Features/Document/ PM 原始需求、無關的 User Manager 行為、原商品管理 Plan 的 DONE 紀錄
```
