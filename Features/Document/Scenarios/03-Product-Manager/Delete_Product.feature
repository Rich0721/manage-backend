Feature: 刪除產品
    使用者需要透過有效的登入資訊並具有相應權限，才可以進行產品更新操作。

    Scenario: 刪除產品成功
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者具有產品更新權限
          And "tb_products"中包含以下產品資訊
            | id  | name  | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 001 | 產品A | 標籤1,標籤2   | 100  | 150   | false       | userB        | 2024-06-01 12:00:00 |
          And Redis中的`products:info`包含以下產品資訊
            | id  | name  | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 001 | 產品A | 標籤1,標籤2   | 100  | 150   | false       | userB        | 2024-06-01 12:00:00 |
            | 002 | 產品B | 標籤3         | 200  | 250   | false       | userB        | 2024-06-01 12:00:00 |
            | 003 | 產品C | 標籤4         | 300  | 350   | true        | userC        | 2024-06-01 12:00:00 |
        When 使用者發送刪除產品的請求，產品ID為"001"
        Then "tb_products"中的產品"001"應更新為以下資訊
            | id  | name       | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 001 | 產品A | 標籤1,標籤2   | 200  | 150   | true       | userA        | 2024-06-01 12:00:00 |
         And Redis中的`products:info`應同步為最新資訊
         | id  | name       | label_names   | cost | price | delete_flag | updated_user | updated_at          |
         | 001 | 產品A | 標籤1,標籤2   | 200  | 150   | true       | userA        | 2024-06-01 12:00:00 |
         | 002 | 產品B | 標籤3         | 200  | 250   | false       | userB        | 2024-06-01 12:00:00 |
         | 003 | 產品C | 標籤4         | 300  | 350   | true        | userC        | 2024-06-01 12:00:00 |
         And 回傳Status為200
         And 回傳Message為"OK"
    
    
    Scenario: 刪除不存在的產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者具有產品更新權限
          And "tb_products"中不存在產品ID"004"
          And Redis中的`products:info`不包含產品ID"004"
        When 使用者發送刪除產品的請求，產品ID為"004"
        Then "tb_products"不應新增或更新產品ID"004"
          And Redis中的`products:info`應保持不變
          And 回傳產品不存在的錯誤訊息
    
    Scenario: 使用者沒有權限刪除產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者不具有產品更新權限
          And "tb_products"中存在產品ID"001"
          And Redis中的`products:info`包含產品ID"001"
        When 使用者發送刪除產品的請求，產品ID為"001"
        Then "tb_products"中的產品"001"資訊不應更新
          And Redis中的`products:info`應保持不變
          And 回傳Status為401
          And 回傳Message為"Unauthorized"