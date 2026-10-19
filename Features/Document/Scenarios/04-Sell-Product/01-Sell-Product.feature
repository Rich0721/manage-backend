Feature: 販售商品操作

    Scenario: 成功販售商品
        Given 使用者已經登入並具有有效的授權
          And tb_products 包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_uid | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 5     | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 5     | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
          And tb_orders 包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
          And tb_orders_item 包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
         When 使用者送出以下販賣商品資訊
            | totalAmount | totalDiscount | orderItems |
            | 800.00     | 700.00        | [{"productId": "1790705105001", "quantity": 2, "price": 150.00, "discount": 150.00}, {"productId": "1790705105002", "quantity": 2, "price": 250.00, "discount": 200.00}] |
         Then 產生0000000002的OrderId
         And tb_orders應更新成以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
         And tb_orders_item應更新成以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
         And tb_products應更新成以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_uid | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And Redis中的products:info應根據tb_products進行更新

    Scenario: 成功販售商品，但庫存不足
        Given 使用者已經登入並具有有效的授權
          And tb_products 包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_uid | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 0     | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 5     | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
          And tb_orders 包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
          And tb_orders_item 包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
         When 使用者送出以下販賣商品資訊
            | totalAmount | totalDiscount | orderItems |
            | 800.00     | 700.00        | [{"productId": "1790705105001", "quantity": 2, "price": 150.00, "discount": 150.00}, {"productId": "1790705105002", "quantity": 2, "price": 250.00, "discount": 200.00}] |
         Then 產生0000000002的OrderId
         And tb_orders應更新成以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
            | 0000000002 | 800.00     | 700.00        | uid123      | 2024-06-02 12:00:00 |
         And tb_orders_item應更新成以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000002 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-02 12:00:00 | uid123     |
            | 0000000002 | 1790705105002 | 2        | 250.00   | 200.00        | 2024-06-02 12:00:00 | uid123     |
         And tb_products應更新成以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_uid | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 0     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 3     | false       | userB        | 2024-06-02 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | 5     | false       | userC        | 2024-06-01 12:00:00 |
         And Redis中的products:info應根據tb_products進行更新

    Scenario: 商品不存在
         Given 使用者已經登入並具有有效的授權
          And tb_products 包含以下資訊
            | id            | name  | label_names   | cost | price | stock | delete_flag | updated_uid | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2    | 100  | 150   | 0     | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | 5     | false       | userB        | 2024-06-01 12:00:00 |
          And tb_orders 包含以下資訊
            | orderId    | totalAmount | totalDiscount | created_uid | created_at |
            | 0000000001 | 800.00     | 600.00        | uid123      | 2024-06-01 12:00:00 |
          And tb_orders_item 包含以下資訊
            | orderId    | productId     | quantity | price     | discount | created_at          | created_by |
            | 0000000001 | 1790705105001 | 2        | 150.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
            | 0000000001 | 1790705105002 | 2        | 250.00   | 150.00        | 2024-06-01 12:00:00 | uid123     |
         When 使用者送出以下販賣商品資訊
            | totalAmount | totalDiscount | orderItems |
            | 800.00     | 700.00        | [{"productId": "1790705105001", "quantity": 2, "price": 150.00, "discount": 150.00}, {"productId": "1790705105003", "quantity": 2, "price": 300.00, "discount": 200.00}] |
         Then 系統應回應錯誤訊息 "商品不存在"
          And tb_orders應保持不變
          And tb_orders_item應保持不變
          And tb_products應保持不變
          And Redis中的products:info應保持不變