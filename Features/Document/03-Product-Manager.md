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

此物件需要透過`Header`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-1-2. Request Body Information Object

此物件包含新增產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |

### 2-1-3. Response Body Authorization 
根據登入後資訊將使用者相關資訊透過`Header`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 產品新增成功 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |

### 2-1-4. Response Body Information Object
此物件包含新增產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 新增的產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |

### 2-1-5. 使用者操作
使用者在新增產品時，需要先登入系統，並且具有相應的權限。操作流程如下：
1. 使用者登入系統，獲取`Authorization`資訊。
2. 使用者填寫新增產品的相關資訊，包括產品名稱、標籤名稱列表、成本和價格。
3. 系統驗證使用者的`Authorization`資訊。
4. 驗證通過後，系統新增產品，並返回新增產品的詳細資訊。
5. 若使用者沒有權限，系統返回`Unauthorized`訊息。

### 2-1-6. Business Rules
1. 須將`tb_lables`的id, name先載入到Redis中，以`product:labels`作為key。
2. Lable_names必須先透過","切割成陣列後，先查詢Redis中`product:labels`的對應ID，並將ID join成字串(例如: "1,2,3")，存入`label_ids`欄位。
- 如果`product:labels`Key不存在，則需要先從`tb_labels`表中載入標籤資料到Redis中，然後再進行查詢。
- 如果Redis中`product:labels`查詢不到對應的ID，則需要先清空Redis中的`product:labels`，然後重新從`tb_labels`表中載入標籤資料到Redis中，再進行查詢。
- 如果Redis重新載入標籤後仍找不到對應的ID，則新增產品將失敗，並返回錯誤訊息。
3. Product的ID使用Unix Timestamp生成，並且取得當前時間的毫秒數作為唯一標識。
4. 新增產品時，系統應自動記錄創建用戶和創建時間，更新產品時，系統應自動記錄更新用戶和更新時間。
5. 當完成產品的新增或更新操作後，系統應更新Redis中的`products:info`，以確保緩存中的產品資訊與資料庫保持一致。
6. 新增產品的更新者資訊應自動記錄在資料庫中，包括創建用戶、創建時間、更新用戶和更新時間，時間由程式自動生成，用戶則會從`Header`中的`uid`資訊中獲取。

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

此物件需要透過`Header`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-2-2. Request Parameters

此部分描述取得產品所需的請求參數，透過URL中的查詢參數傳遞。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| productId | string | 產品ID |

### 2-2-3. Response Authorization
根據登入後資訊將使用者相關資訊透過`Header`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 取得產品成功 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |

### 2-2-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |
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
- 如果使用者取得所有產品資訊時，須將`delete_flag`為`false`的產品資訊返回，已刪除的產品不應包含在返回結果中。
- `Response Body`因以陣列為主，確保取得`單一產品`或`多個產品`時的結構一致性。


### 2-3. 編輯產品
Flow Chart: [更新產品流程圖](flows/03-Product-Manager/Update_Product.mmd)
Gherkin: [更新產品Gherkin範例](Scenarios/03-Product-Manager/Update_Product.feature)
METHOD: PUT
uri: /productController/updateProduct

### 2-3-1. Request Body Authorization

此物件需要透過`Header`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 2-3-2. Request Body Information Object

此物件包含取得產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |

### 2-3-3. Response Body Authorization

根據登入後資訊將使用者相關資訊透過`Header`中的`uid`和`Authorization`資訊返回。
需繼承自`authorization`物件，以利Response Body的結構化，根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 更新產品成功 |
| 401 | Unauthorized | 使用者沒有權限更新該資源 |

### 2-3-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位         | 型別      | 說明 |
| ------------ | -------- | --- |
| id           | string   | 產品ID |
| name         | string   | 產品名稱 |
| label_names  | string   | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost         | number   | 產品成本 |
| price        | number   | 產品價格 |
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
5. DB的更新使用者須從`Header`中的`uid`資訊中獲取，更新時間由程式自動生成。
6. 更新產品時，`name`, `label_names`, `cost` 和 `price` 等欄位不得為空，否則更新失敗。

### 2-4. 刪除產品
Flow Chart:
Gherkin:
METHOD: DELETE
uri: /productController/deleteProduct

### 2-4-1. Request Body Authorization

此物件包含取得產品所需的授權資訊，需繼承自`authorization`物件，以利Request Body的結構化。
根據登入後獲得的`Authorization`資訊填寫。

### 2-4-2. Request Body Information Object

此物件包含取得產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |

### 2-4-3. Response Body Authorization

此物件包含取得使用者登入資料後返回的授權資訊，需繼承自`authorization`物件，以利Response Body的結構化。
根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| 200 | OK | 刪除產品成功 |
| 401 | Unauthorized | 使用者沒有權限訪問該資源 |

### 2-4-4. Response Body Information Object

此物件包含取得產品後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化，通常會以陣列的形式返回多個產品資訊。

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| id | string | 產品ID |
| name | string | 產品名稱 |
| label_names | string | 產品標籤名稱列表, 多個標籤名稱以逗號分隔 |
| cost | number | 產品成本 |
| price | number | 產品價格 |


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