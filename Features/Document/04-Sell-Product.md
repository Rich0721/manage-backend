# 04-Sell Product


## I. 需求簡介
本需求主要需求為使用者會透過前端進行商品銷售的操作，商品販賣與訂單的價格調整等功能，前端會根據不同需求讓使用者呼叫對應的後端操作，而後端則負責處理這些請求並進行相應的業務邏輯處理。

## II. 需求說明

### 2-1. 販賣商品
Flow Chart:[訂單流程圖](./flows/04-Sell-Product/01-Sell-Product.mmd)
Gherkin:
METHOD: POST
URI: `/sellController/sellProduct`

#### 2-1-1. Request Body
此物件包含新增產品所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。相關格式請參考:
```json
    {
        "headers":...,
        "body": { "info": {
            "totalAmount": 1000.00,
            "totalDiscount": 100.00,
            "orderItems": [
                {
                    "productId": "P123456",
                    "quantity": 2,
                    "price": 500.00,
                    "discount": 50.00
                }
            ]
        } }
    }
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| productId | String | 商品ID |
| quantity | Integer | 銷售數量 |
| price | Decimal | 銷售價格 |
| discount | Decimal | 折扣價格 |
| totalAmount | Decimal | 總金額 |
| totalDiscount | Decimal | 總折扣金額 |

#### 2-1-2. Response Message
回傳相關訊息應放入`Headers`中的`Status`與`Message`欄位。
| Status | Message | 條件 |
|--------|---------|------|
| 200    | OK    | 請求成功 |
| 400    | Bad Request    | 請求參數錯誤 |
| 401    | Unauthorized  | Authorization失效或缺失 |

#### 2-1-3. Response Body

此物件包含回傳的相關訊息，需繼承自`Response Information`物件，以利Response Body的結構化。相關格式請參考:
```json
    {
        "headers":...,
        "body": { "info": {
            "orderId": "1234567890",
            "totalAmount": 1000.00,
            "totalDiscount": 100.00,
            "orderItems": [
                {
                    "productId": "P123456",
                    "quantity": 2,
                    "price": 500.00,
                    "discount": 50.00
                }
            ]
        } }
    }
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| orderId | String | 訂單ID |
| totalAmount | Decimal | 總金額 |
| totalDiscount | Decimal | 總折扣金額 |
| productId | String | 商品ID |
| quantity | Integer | 銷售數量 |
| price | Decimal | 銷售價格 |
| discount | Decimal | 折扣價格 |


#### 2-1-4. 使用者操作
- 使用者在前端將相關商品資訊填寫完成後，點擊「送出」按鈕，前端會將商品資訊以`Request Body`的形式發送至後端的`/sellController/sellProduct`接口。
- 後端需確認`Uid`與`Authorization`的有效性，才能根據資訊進行邏輯處理，若沒有通過驗證，後端應回傳相應的錯誤訊息。

#### 2-1-5. Business Rules
- 欄位檢查
    - `productId`：不可為空，且需為有效的商品ID。
    - `quantity`：需為正整數且不能為零。
    - `price`：需為非負數，且不能為空。
    - `discount`：需為非負數。
    - `totalAmount`：需為非負數，且不能為空。
    - `totalDiscount`：需為非負數。
- `orderId`: 根據`tb_orders`數量生成一個唯一的訂單ID，長度固定為10，不足的話前面補零。
- `tb_orders`：需要讓入相關資訊，包括`orderId`、`totalAmount`、`totalDiscount`以及其他基本欄位。
- `tb_orders_item`：需要將每個商品的詳細資訊存入，包括`orderId`、`productId`、`quantity`、`price`、`discount`等欄位。
- `tb_orders_item`的`orderId`需對應`tb_orders`中的`orderId`，以確保訂單與訂單項目的關聯性。
- 根據`productId`查詢`tb_products`中的商品資訊的stock，並且需要扣除相應的銷售數量。
  - 若扣除庫存小於零，則庫存數量歸零。
  - 如果productId對應的商品不存在於`tb_products`中，則需返回相應的錯誤訊息，並且需要進行Rollback操作，資料庫不能有任何變更，包含`tb_orders`與`tb_orders_item`中的資料。
  - 每筆訂單處理完後，需要同步更新Redis中的`products:info`。
    - 如果`products:info`不存在於Redis中，則需要寫入相應的商品資訊。
    - 如果`products:info`已存在於Redis中，則需要更新相應的商品資訊。
- created_by: 來源為`Headers`中的`uid`

### 2-2. Get Order
Flow Chart:[取得訂單資訊](./flows/04-Sell-Product/02-Ger-Orders.mmd)
Gherkin:
METHOD: GET
URI: `/sellController/getOrder?orderId={orderId}&startDate={startDate}&endDate={endDate}`

#### 2-2-1. Request Parameters
| 欄位 | 型別 | 說明 |
|------|------|------|
| orderId | String | 訂單ID |
| startDate | String | 查詢起始日期，格式為YYYY-MM-DD，非必填 |
| endDate | String | 查詢結束日期，格式為YYYY-MM-DD，非必填 |

#### 2-2-2. Response Message
回傳相關訊息應放入`Headers`中的`Status`與`Message`欄位。
| Status | Message | 條件 |
|--------|---------|------|
| 200    | OK    | 請求成功 |
| 400    | Bad Request    | 請求參數錯誤 |
| 401    | Unauthorized  | Authorization失效或缺失 |

#### 2-2-3. Response Body
此物件包含回傳的相關訊息，需繼承自`Response Information`物件，以利Response Body的結構化。相關格式請參考:
```json
    {
        "headers":...,
        "body": { "info": [
            {
                "orderId": "1234567890",
                "totalAmount": 1000.00,
                "totalDiscount": 100.00,
                "createdAt": "2024-06-01 12:00:00",
                "createdBy": "admin",
                "orderItems": [
                    {
                        "productId": "P123456",
                        "productName": "Sample Product",
                        "quantity": 2,
                        "price": 500.00,
                        "discount": 50.00
                    }
                ]
            }
        ] }
    }
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| orderId | String | 訂單ID |
| totalAmount | Decimal | 總金額 |
| totalDiscount | Decimal | 總折扣金額 |
| productId | String | 商品ID |
| productName | String | 商品名稱 |
| quantity | Integer | 銷售數量 |
| price | Decimal | 銷售價格 |
| discount | Decimal | 折扣價格 |
| createdAt | String | 訂單建立時間，格式為YYYY-MM-DD HH:MM:SS |
| createdBy | String | 訂單建立者 |

#### 2-2-4. 使用者操作
- 使用者於前端操作查詢訂單資訊，系統會將查詢請求以`Request Parameters`的形式發送至後端的`/sellController/getOrder`接口，後端根據查詢條件返回相應的訂單資訊。

#### 2-2-5. Business Rules
- `orderId`相關規定如下：
    - `all`: 不區分大小寫，表示需要查詢所有區間，`startDate`與`endDate`必須提供；且`startDate`與`endDate`區間最多為一個月，需檢查區間長度與合法性，發生錯誤請回傳Status Code-`400`且Message-`請檢查查詢日期區間正確或完整`
    - 其他情況下，`orderId`不得為空，且需為有效的訂單ID，`startDate`與`endDate`則不需要提供，若提供也不需要使用，避免引起混淆。
- `createdBy`需要透過`tb_users`一表中的`uid`欄位進行關聯，以獲取訂單建立者的姓名。
- `productName`需要透過`tb_products`一表中的`id`欄位進行關聯，以獲取商品名稱。

## III. 其他資訊

### 3-1. Request Authorization
此需求內的API皆需透過`Headers`中的`uid`和`Authorization`資訊確認API授權情況，並確保使用者具有訪問該資源的權限。

### 3-2. Authorization辨別與更新到期期限
相關驗證請參考`Features/Document/02-User-Manager.md`的`3-4. Authorization辨別與更新到期期限`。

### 3-3. Order Table
Table Name: tb_orders

| Column Name    | Data Type      | Description |
|----------------|----------------|-------------|
| id             | varchar(10)    | 訂單ID      |
| total_amount   | decimal(10,2)  | 總金額      |
| total_discount | decimal(10,2)  | 總折扣金額   |
| created_uid    | varchar(255)   | 創建用戶     |
| created_at     | datetime       | 創建時間     |


### 3-4. Order Items Table
Table Name: tb_orders_items

| Column Name    | Data Type      | Description |
|----------------|----------------|-------------|
| order_id       | varchar(10)    | 訂單ID      |
| product_id     | varchar(13)    | 商品ID      |
| quantity       | int            | 銷售數量    |
| price          | decimal(10,2)  | 銷售價格    |
| discount       | decimal(10,2)  | 折扣價格    |
| created_at     | datetime       | 訂單商品建立時間 |
| created_by     | varchar(255)   | 訂單商品建立者 |