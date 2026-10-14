# 03-Product-Manager

## I. 需求簡介
這一個文件主要是用來描述產品管理的相關API，但需要先登入後，才能使用，所以前置條件是用戶必須具有有效的登入狀態。
相關驗證請參考`Features/Document/02-User-Manager.md`的`3-4. Authorization辨別與更新到期期限`

## II. 需求說明

### 2-1. 新增產品
Flow Chart: [新增產品流程圖](flows/03-Product-Manager/Add_Product.mmd)
Gherkin: [新增產品Gherkin範例](Scenarios/03-Product-Manager/Add_Product.feature)
METHOD: POST
uri: /productController/addProduct

### 2-1-1. Request Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-1-2. Request Body Information Object

此物件包含新增產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存, default 0 |

### 2-1-3. Response Body Authorization 
根據登入後資訊將使用者相關資訊透過`Headers`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 產品新增成功 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |
| 409 | Conflict | 產品ID發生衝突 |

### 2-1-4. Response Body Information Object
此物件包含新增產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 新增的產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存, default 0 |

### 2-1-5. 使用者操作
使用者在新增產品時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者填寫新增產品的相關資訊，包括產品名稱、標籤名稱列表、成本和價格。
3. 系統驗證使用者的`Authorization`資訊。
4. 驗證通過後，系統新增產品，並返回新增產品的詳細資訊。
5. 若使用者沒有權限，系統返回`Unauthorized`訊息。

### 2-1-6. Business Rules
1. 須將`tb_labels`的id, name先載入到Redis中，以`product:labels`作為key。
2. Lable_names必須先透過","切割成陣列後，先查詢Redis中`product:labels`的對應ID，並將ID join成字串(例如: "1,2,3")，存入`label_ids`欄位。
- 如果`product:labels`Key不存在，則需要先從`tb_labels`表中載入標籤資料到Redis中，然後再進行查詢。
- 如果Redis中`product:labels`查詢不到對應的ID，則需要先清空Redis中的`product:labels`，然後重新從`tb_labels`表中載入標籤資料到Redis中，再進行查詢。
- 如果Redis重新載入標籤後仍找不到對應的ID，則新增產品將失敗，並返回錯誤訊息。
3. Product的ID使用Unix Timestamp生成，並且取得當前時間的毫秒數作為唯一標識。
4. 新增產品時，系統應自動記錄創建用戶和創建時間，更新產品時，系統應自動記錄更新用戶和更新時間。
5. 當完成產品的新增或更新操作後，系統應更新Redis中的`products:info`，以確保緩存中的產品資訊與資料庫保持一致。
6. 新增產品的更新者資訊應自動記錄在資料庫中，包括創建用戶、創建時間、更新用戶和更新時間，時間由程式自動生成，用戶則會從`Headers`中的`uid`資訊中獲取。

### 2-1-7. Technical Requirements
- `product:labels`沒有過期時間，但須要避免多人使用時出現資料不一致的情況，建議在更新Redis時使用分布式鎖。
- `products:info`的更新也應使用分布式鎖，以避免多人同時更新時出現資料不一致的情況。
- 需更新Redis中的`<uid>:login`到期時間。

### 2-2. 取得產品
Flow Chart: [取得產品流程圖](flows/03-Product-Manager/Get_Products.mmd)
Gherkin: [取得產品Gherkin範例](Scenarios/03-Product-Manager/Get_Products.feature)
METHOD: GET
uri: /productController/getProducts?productId={id}

### 2-2-1. Request Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-2-2. Request Parameters

此部分描述取得產品所需的請求參數，透過URL中的查詢參數傳遞。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| productId | string | 產品ID |

### 2-2-3. Response Authorization
根據登入後資訊將使用者相關資訊透過`Headers`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 取得產品成功 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |
| 404 | Not Found | 產品不存在 |

### 2-2-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存 |
| delete_flag | boolean | 刪除標誌, default false |
| updated_user | string | 更新用戶 |
| updated_at | datetime | 更新時間 |

### 2-2-5. 使用者操作
使用者在取得產品時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者透過API請求取得產品資訊，需在URL中傳遞產品ID。
3. 系統驗證使用者的`Authorization`資訊。
4. 驗證通過後，系統返回對應的產品資訊。
5. 若使用者沒有權限，系統返回`Unauthorized`訊息。

### 2-2-6. Business Rules
- Product ID檢查與處理:
    - 一律轉換為大寫，確保`ALL`不會被誤判為小寫，導致需要用過多的情境判斷。
    - 需檢查長度，確保符合系統要求，如果不符合，則返回錯誤訊息。
    - 當Product ID查詢不到對應的產品時，系統應返回錯誤訊息。
- Redis僅會判斷`products:info`是否存在
    - 不存在，則需要從資料庫中取得產品資訊，並更新Redis中的`products:info`。
    - 存在，則直接從Redis中取得產品資訊。
    - 如果因使用者`新增`, `更新`或`刪除`操作導致Redis中的`products:info`與資料庫不一致，則因由指定的操作重新更新Redis中的`products:info`，而非透過此功能進行更新。
- Redis的`products:info`會包含已刪除的產品資訊，但回傳給使用者時應過濾掉已刪除的產品。
- `Response Body`因以陣列為主，確保取得`單一產品`或`多個產品`時的結構一致性。


### 2-3. 編輯產品
Flow Chart: [更新產品流程圖](flows/03-Product-Manager/Update_Product.mmd)
Gherkin: [更新產品Gherkin範例](Scenarios/03-Product-Manager/Update_Product.feature)
METHOD: PUT
uri: /productController/updateProduct

### 2-3-1. Request Body Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-3-2. Request Body Information Object

此物件包含更新產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存, default 0 |

### 2-3-3. Response Body Authorization

根據登入後資訊將使用者相關資訊透過`Headers`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 更新產品成功 |
| 401 | Unauthorized | 使用者沒有權限更新該資源 |
| 404 | Not Found | 產品不存在 |

### 2-3-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位         | 型別      | 說明 |
| ------------ | -------- | --- |
| id           | string   | 產品ID |
| name         | string   | 產品名稱 |
| label_names  | string   | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost         | number   | 產品成本 |
| price        | number   | 產品價格 |
| stock        | number   | 產品庫存 |
| delete_flag  | boolean  | 刪除標誌, default false |
| updated_user | string   | 更新用戶 |
| updated_at   | datetime | 更新時間 |

### 2-3-5. 使用者操作
使用者在更新產品時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者於進入前端產品管理頁面，會先透過`getProducts?productId=all`取得所有產品的資訊。
3. 並且根據使用者自身需求，點擊指定產品進行編輯，會透過`getProducts?productId=<PRODUCT_ID>`取得該產品的詳細資訊。
4. 使用者於前端進行產品資訊的編輯，並提交更新請求。
5. 驗證通過後，系統更新對應的產品資訊，並同步更新Redis中的`products:info`。
6. 若使用者沒有權限，系統返回`Unauthorized`訊息。

### 2-3-6. Business Rules

1. 使用者必須登入系統並具有相應的權限才能更新產品。
2. 更新產品時，若產品ID不存在，系統應返回錯誤訊息。
3. 更新產品成功後，需同步更新Redis中的`products:info`。
4. 若使用者沒有權限，系統返回`Unauthorized`訊息。
5. DB的更新使用者須從`Headers`中的`uid`資訊中獲取，更新時間由程式自動生成。
6. 更新產品時，`name`, `label_names`, `cost` 和 `price` 等欄位不得為空，否則更新失敗。

### 2-4. 刪除產品
Flow Chart: [刪除產品流程圖](flows/03-Product-Manager/Delete_Product.mmd)
Gherkin: [刪除產品Gherkin範例](Scenarios/03-Product-Manager/Delete_Product.feature)
METHOD: DELETE
uri: /productController/deleteProduct

### 2-4-1. Request Body Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-4-2. Request Body Information Object

此物件包含取得產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |

### 2-4-3. Response Body Authorization

根據登入後資訊將使用者相關資訊透過`Headers`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 刪除產品成功 |
| 401 | Unauthorized | 使用者沒有權限刪除該資源 |
| 404 | Not Found | 產品不存在 |
    

### 2-4-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化，通常會以陣列的形式返回多個產品資訊。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存 |
| delete_flag | boolean | 刪除標誌, default false |
| updated_user | string | 更新用戶 |
| updated_at   | datetime | 更新時間 |

### 2-4-5. 使用者操作
使用者在刪除產品時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者於進入前端產品管理頁面，會先透過`getProducts?productId=all`取得所有產品的資訊。
3. 根據使用者指定的產品ID點選`刪除`按鈕。
4. 系統會根據使用者的操作，發送刪除產品的請求至後端API。
5. 若刪除成功，系統會更新前端顯示，並同步更新Redis中的`products:info`。

### 2-4-6. Business Rules
1. 需檢查product ID是否存在，若不存在，系統應返回錯誤訊息。
2. 使用者必須登入系統並具有相應的權限才能刪除產品。
3. 刪除產品成功後，需同步更新Redis中的`products:info`。
4. 若使用者沒有權限，系統返回`Unauthorized`訊息。
5. 刪除產品僅將`delete_flag`設置為`true`，實際資料仍保留於資料庫中，不能使用`DELETE`語句直接刪除。


### 2-5. 批次新增和修改商品資訊
Flow Chart: [批次新增和修改商品資訊](./flows/03-Product-Manager/Batch_Product.mmd)
Gherkin: [批次新增和修改商品資訊](./scenarios/03-Product-Manager/Batch_Product.feature)
METHOD: POST
uri: /productController/batchProducts

#### 2-5-1. Request Body Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

#### 2-5-2. Request Body Information Object
使用者會上傳Excel資料，後端會解析該資料並進行批次新增或修改操作。

#### 2-5-3. Response Body Authorization

此物件包含批次新增和修改產品後返回的授權資訊，需繼承自`authorization`物件，以利Response Body的結構化。根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 批次新增或修改產品成功 |
| 400 | 根據請求內容返回錯誤訊息 | 請求的資料格式不正確或缺少必要欄位 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |
| 404 | <Product Name> Not Found | 批次新增或修改的產品不存在 |

#### 2-5-4. Response Body Information Object

此物件包含批次新增和修改產品後返回的產品資訊，需繼承自`Response Information`物件，以利Response Body的結構化，通常會以陣列的形式返回多個產品資訊。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
| stock | number | 產品庫存 |
| delete_flag | boolean | 刪除標誌, default false |
| updated_user | string | 更新用戶 |
| updated_at   | datetime | 更新時間 |

#### 2-5-5. 使用者操作

使用者在批次新增和修改產品資訊時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者於進入前端產品管理頁面，會選擇批次上傳Excel檔案。
3. 系統會將Excel資料傳至後端API進行批次新增或修改操作。
4. 若操作成功，系統會更新前端顯示，並同步更新Redis中的`products:info`。

#### 2-5-6. Business Rules
- 需要確認副檔名是否為`.xlsx`或`.xls`，如果不是，則於Headers的Message返回`檔案格式不正確，請上傳Excel檔案`。
- 使用者會傳入Excel檔案，由後端進行解析後進行`新增`或`修改`操作。
  - 查詢Excel分頁，如果該分頁名稱為`Add Product`，則進行新增操作。
  - 查詢Excel分頁，如果該分頁名稱為`Update Product`，則進行修改操作。
  - 其他分頁則忽略，不進行任何操作。
- 新增商品分頁檢查內容資料:
    - 第一列資料為欄位名稱，需要檢查是否為`商品名稱`、`商品分類`、`成本`、`價錢`、`庫存`，如果欄位缺少，則於Headers的Message返回`新增商品欄位缺失，請使用正確的Excel模板`
    - 第二列開始為實際資料，需要檢查每一列的資料是否完整且符合格式要求，若有錯誤，則於Headers的Message返回`新增商品資料錯誤，請檢查Excel內容`
- 修改商品分頁檢查內容資料:
    - 第一列資料為欄位名稱，需要檢查是否為`商品ID`、`商品名稱`、`商品分類`、`成本`、`價錢`、`庫存`，如果欄位缺少，則於Headers的Message返回`修改商品欄位缺失，請使用正確的Excel模板`
    - 第二列開始為實際資料，需要檢查每一列的資料是否完整且符合格式要求，若有錯誤，則於Headers的Message返回`修改商品資料錯誤，請檢查Excel內容`
- 需要先進行欄位檢查，確認內容無誤才可以執行`Insert`或`Update`操作，欄位規則如下:
    - `商品ID`: 必填，且需為存在的商品ID，`新增`操作時不需要此欄位。
    - `商品名稱`: 必填，且長度不得超過255個字元。
    - `商品分類`: 必填，分類名稱，並且透過`,`分隔多個分類名稱，如果分類名稱不存在，則自動新增該分類至`tb_labels`。
    - `成本`: 必填，且需為數字，且不得小於0。
    - `價錢`: 必填，且需為數字，且不得小於0。
    - `庫存`: 如果為空，則預設為0。
- 如果`新增`或`修改`部分商品失敗時，需要進行Rollback操作，確保資料的一致性，並於根據下列規則將錯誤訊息返回Headers的Message。
    - `新增商品`: 返回`新增<商品名稱>失敗，請檢查Excel內容`
    - `修改商品`: 返回`修改<商品ID>失敗，請檢查Excel內容`
- 當完成批次新增或修改操作後，會自動更新Redis中的`products:info`。
- `商品ID`根據unix timestamp自動生成，確保唯一性，須避免重複。


### 2-6. 下載Excel模板
Flow Chart: 
Gherkin: 
METHOD: GET
uri: /productController/downloadTemplate

#### 2-6-1. Request Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

#### 2-6-2. Response Body Authorization

根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。

| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 成功下載Excel模板 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |

#### 2-6-3. 使用者操作
使用者在批次新增和修改產品資訊時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者於進入前端產品管理頁面，會選擇下載Excel模板。
3. 系統會將Excel模板返回給前端，供使用者填寫商品資料。

#### 2-6-5. Business Rules
- Excel Path: `/files/Batch Add Products.xlsx`
- Excel File Name: `Batch Add Products.xlsx`
- 使用者需要有登入狀態，才可以進行下載Excel模板的操作。

### 2-7. 下載商品資料成Excel

Flow Chart: 
Gherkin: 
METHOD: POST
uri: /productController/downloadProductData

#### 2-7-1. Request Authorization

此物件需要透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

#### 2-7-2. Request Body Information Object

此物件包含取得產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化，以下資料以List形式傳入，並且使用`,`分隔。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| ids | string | 產品ID列表, 多個ID以逗號分隔 |

#### 2-7-3. Response Body Authorization

根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。

| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 成功下載商品資料Excel |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |

#### 2-7-4. 使用者操作
使用者在下載商品資料成Excel時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者於進入前端產品管理頁面，會選擇下載商品資料成Excel。
3. 前端會傳入使用者過濾後的產品ID列表，後端根據該列表生成查詢Redis或資料庫的請求，並將結果生成Excel返回給前端。

#### 2-7-5. Business Rules
- file path: `/files/<uid>.xlsx`
- file name: `<uid>.xlsx`
- 使用者需要有登入狀態，才可以進行下載商品資料成Excel的操作。
- 如果Redis中不存在`products:info`的資料，則會需要從資料庫產生對應的資料，並更新到Redis中，以便後續查詢。
- 如果`file path`存在對應的Excel檔案，則會先進行刪除，然後生成新的Excel檔案。
- Excel產生格式:
    - 分頁名稱: `Update Product`
    - 欄位名稱會產生在第一列，名稱如下:`商品ID`、`商品名稱`、`商品分類`、`成本`、`價錢`、`庫存`
    - 資料從第二列開始填寫，對應每個產品的詳細資訊。
        - 商品ID：對應 `id`
        - 商品名稱：對應 `name`
        - 商品分類：會跟`tb_labels`中的標籤名稱對應，並且透過`,`分隔多個分類名稱
        - 成本：對應 `cost`
        - 價錢：對應 `price`
        - 庫存：對應 `stock`



## III. 其他資訊

### 3-1. Table Structure

#### 3-1-1. Product Table
Table Name: tb_products

| Column Name | Data Type       | Description |
|-------------|---------------- |-------------|
| id          | varchar(13)     | 產品ID      |
| name        | varchar(255)    | 產品名稱    |
| label_ids   | text            | 產品標籤ID列表, 多個標籤ID以逗號分隔   |
| cost        | numeric(10,2)   | 產品成本    |
| price       | numeric(10,2)   | 產品價格    |
| delete_flag | boolean         | 刪除標誌, default false    |
| stock       | number          | 產品庫存, default 0   |
| created_uid | varchar(255)    | 創建用戶    |
| created_at  | datetime        | 創建時間    |
| updated_uid | varchar(255)    | 更新用戶    |
| updated_at  | datetime        | 更新時間    |

#### 3-1-2. Label Table

Table Name: tb_labels

| Column Name | Data Type      | Description |
|-------------|----------------|-------------|
| id          | int            | 標籤ID      |
| name        | varchar(255)   | 標籤名稱    |
| created_uid | varchar(255)   | 創建用戶    |
| created_at  | datetime       | 創建時間    |
| updated_uid | varchar(255)   | 更新用戶    |
| updated_at  | datetime       | 更新時間    |

### 3-2. Authorization辨別與更新到期期限
相關驗證請參考`Features/Document/02-User-Manager.md`的`3-4. Authorization辨別與更新到期期限`