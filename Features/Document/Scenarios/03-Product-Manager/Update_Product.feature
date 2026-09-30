Feature: 更新產品
    使用者需要透過有效的登入資訊並具有相應權限，才可以進行產品更新操作。

    Scenario: 成功更新產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者具有產品更新權限
          And "tb_products"中包含以下產品資訊
            | id  | name  | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2   | 100  | 150   | false       | userB        | 2024-06-01 12:00:00 |
          And Redis中的`products:info`包含以下產品資訊
            | id  | name  | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A | 標籤1,標籤2   | 100  | 150   | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105002 | 產品B | 標籤3         | 200  | 250   | false       | userB        | 2024-06-01 12:00:00 |
            | 1790705105003 | 產品C | 標籤4         | 300  | 350   | true        | userC        | 2024-06-01 12:00:00 |
        When 使用者提交以下產品更新資訊
            | id  | name       | label_names   | cost | price |
            | 1790705105001 | 產品A-更新 | 標籤1,標籤2   | 200  | 150   |
        Then "tb_products"中的產品"1790705105001"應更新為以下資訊
            | id  | name       | label_names   | cost | price | delete_flag | updated_user | updated_at          |
            | 1790705105001 | 產品A-更新 | 標籤1,標籤2   | 200  | 150   | false       | userA        | 2024-06-03 12:00:00 |
          And Redis中的`products:info`應同步為最新資訊
          | id  | name       | label_names   | cost | price | delete_flag | updated_user | updated_at          |
          | 1790705105001 | 產品A-更新 | 標籤1,標籤2   | 200  | 150   | false       | userA        | 2024-06-03 12:00:00 |
          | 1790705105002 | 產品B | 標籤3         | 200  | 250   | false       | userB        | 2024-06-01 12:00:00 |
          | 1790705105003 | 產品C | 標籤4         | 300  | 350   | true        | userC        | 2024-06-01 12:00:00 |
          And 回傳Status為200
          And 回傳Message為"OK"


    Scenario: 更新不存在的產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者具有產品更新權限
          And "tb_products"中不存在產品ID"1790705105004"
          And Redis中的`products:info`不包含產品ID"1790705105004"
        When 使用者提交以下產品更新資訊
            | id  | name  | label_names | cost | price |
            | 1790705105004 | 產品D | 標籤5       | 400  | 450   |
        Then "tb_products"不應新增或更新產品ID"1790705105004"
          And Redis中的`products:info`應保持不變
          And 回傳產品不存在的錯誤訊息


    Scenario Outline: 更新產品時必填欄位不得為空
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者具有產品更新權限
          And "tb_products"中存在產品ID"1790705105001"
          And Redis中的`products:info`包含產品ID"1790705105001"
        When 使用者更新產品ID"1790705105001"
          And 將"<field>"設定為空值
        Then "tb_products"中的產品"1790705105001"資訊不應更新
          And Redis中的`products:info`應保持不變
          And 回傳更新失敗的訊息

        Examples:
            | field       |
            | name        |
            | label_names |
            | cost        |
            | price       |


    Scenario: 使用者沒有權限更新產品
        Given 使用者已登入系統並獲取有效的`Authorization`資訊
          And Header中的`uid`為"userA"
          And 使用者不具有產品更新權限
          And "tb_products"中存在產品ID"1790705105001"
          And Redis中的`products:info`包含產品ID"1790705105001"
        When 使用者提交以下產品更新資訊
            | id  | name       | label_names   | cost | price |
            | 1790705105001 | 產品A-更新 | 標籤1,標籤2   | 200  | 150   |
        Then "tb_products"中的產品"1790705105001"資訊不應更新
          And Redis中的`products:info`應保持不變
          And 回傳Status為401
          And 回傳Message為"Unauthorized"