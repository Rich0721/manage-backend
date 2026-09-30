Feature: 更新產品
    使用者需要透過有效的登入資訊才可以進行產品更新操作。

    Scenario: 成功更新產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
         And 使用者選擇以下產品進行更新
           | id | name | label_names | cost | price |
           | 001 | 產品A | 標籤1,標籤2 | 100 | 150 |
         And Redis中的`products:info`包含以下產品資訊
           | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
        When 使用者將name更新為"產品A-更新"
         And 使用者將cost更新為200
        Then "tb_products"中的該產品資訊應更新為最新值
         And Redis中的`products:info`應更新為最新值
         | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
         | 1  | 產品A-更新 | 標籤1,標籤2 | 200  | 150   | false | userA | 2024-06-03 12:00:00 |
         | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
         | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
         And 回傳更新成功的訊息
    
    Scenario: 更新產品失敗
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
         And 使用者選擇以下產品進行更新
           | id | name | label_names | cost | price |
           | 004 | 產品D | 標籤5       | 400 | 450 |
        When 使用者將name更新為""
        Then "tb_products"中的該產品資訊不應更新
         And Redis中的`products:info`應保持不變
         And 回傳更新失敗的訊息