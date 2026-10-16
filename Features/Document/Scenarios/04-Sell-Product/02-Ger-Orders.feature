Feature: 取得訂單資訊

    Scenario: 成功取得所有訂單
        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00        | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name  | email           | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為all
         And StartDate為"2024-06-01"
         And EndDate為"2024-06-02"
        Then 使用者成功取得所有訂單資訊
        | orderId    | totalAmount | totalDiscount | createdAt | createdBy           | orderItems |
        | 0000000001 | 800.00     | 600.00        | 2024-06-01 12:00:00 | uid123     | [{"productId":"1790705105001","quantity":2,"price":150.00,"discount":150.00},{"productId":"1790705105002","quantity":2,"price":250.00,"discount":150.00}] |
        | 0000000002 | 800.00     | 700.00        | 2024-06-02 12:00:00 | uid123     | [{"productId":"1790705105001","quantity":2,"price":150.00,"discount":150.00},{"productId":"1790705105002","quantity":2,"price":250.00,"discount":200.00}] |

    Scenario: 成功取得指定訂單
        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00        | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name  | email           | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為0000000001
        Then 應該取得訂單0000000001的詳細資訊
            | orderId    | totalAmount | totalDiscount | createdAt | createdBy           | orderItems |
            | 0000000001 | 800.00     | 600.00        | 2024-06-01 12:00:00 | uid123     | [{"productId":"1790705105001","quantity":2,"price":150.00,"discount":150.00},{"productId":"1790705105002","quantity":2,"price":250.00,"discount":150.00}] |
    
    Scenario: 訂單不存在
        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00         | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00         | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00         | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name    | email              | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為0000000004
        Then 系統應回傳錯誤訊息"訂單不存在"

    Scenario: 取得所有訂單，但未使用StartDate
        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00        | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name  | email           | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為all
         And StartDate為空
         And EndDate為"2024-06-02"
        Then 回傳Status Code為400
         And 錯誤訊息為`請輸入查詢起始日期`
        
    Scenario: 取得所有訂單，但未使用EndDate
        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00        | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name  | email           | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為all
         And StartDate為"2024-06-01"
         And EndDate為空
        Then 回傳Status Code為400
         And 錯誤訊息為`請輸入查詢結束日期`
         
    Scenario: 取得所有訂單，查詢日期超出30天

        Given 使用者已經登入並具有有效的授權
         And tb_orders包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
            | 0000000003 | 1200.00    | 800.00        | uid124      | 2024-06-03 12:00:00 |
         And tb_orders_item包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000003 | 1790705105003 | 2        | 300.00   | 200.00        | 2024-06-03 12:00:00 | uid124     |
         And tb_products包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And tb_users包含以下資訊
            | id     | name  | email           | created_at          | updated_at          |
            | uid123 | 使用者A | userA@example.com | 2024-06-01 12:00:00 | 2024-06-01 12:00:00 |
            | uid124 | 使用者B | userB@example.com | 2024-06-02 12:00:00 | 2024-06-02 12:00:00 |
        When orderId為all
         And StartDate為"2024-06-01"
         And EndDate為"2024-07-02"
        Then 回傳Status Code為400
         And 錯誤訊息為`查詢日期區間不得超過30天`


