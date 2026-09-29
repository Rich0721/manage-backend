Feature: 取得產品
  使用者需要透過有效的登入資訊來取得產品列表

  Rule: 取得產品列表
    Scenario: 成功取得所有產品且Redis中存在產品資訊
       Given 使用者已登入並擁有有效的登入資訊
        And Redis中存在"products:info"且包含以下產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       When API productId 被設定為"ALL"
       Then 回傳取得的所有產品
          | id | name | label_names | cost | price| updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | userB | 2024-06-01 12:00:00 |
    
    Scenario: 成功取得所有產品且Redis中不存在產品資訊
       Given 使用者已登入並擁有有效的登入資訊
        And Redis中不存在"products:info"
        And "tb_products"資料表中存在產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       When API productId 被設定為 "ALL"
       Then 從"tb_products"資料表中取得所有產品並更新Redis中的"products:info"
        And Redis中已更新"products:info"且包含以下產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
        And 回傳取得的所有產品
          | id | name | label_names | cost | price| updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | userB | 2024-06-01 12:00:00 |
    
    Scenario: 成功取得單一產品且Redis中存在該產品資訊
       Given 使用者已登入並擁有有效的登入資訊
        And Redis中存在"products:info"且包含以下產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       When API productId 被設定為 "2"
       Then 回傳取得的單一產品
          | id | name | label_names | cost | price| updated_user | updated_at |
          | 2  | 產品B | 標籤3       | 200  | 250   | userB | 2024-06-01 12:00:00 |
    
    Scenario: 成功取得單一產品且Redis中不存在該產品資訊
       Given 使用者已登入並擁有有效的登入資訊
        And Redis中不存在"products:info"
        And "tb_products"資料表中存在產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       When API productId 被設定為 "2"
       Then 從"tb_products"資料表中取得所有產品並更新Redis中的"products:info"
        And Redis中已更新"products:info"且包含以下產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       And 回傳取得的單一產品
          | id | name | label_names | cost | price| updated_user | updated_at |
          | 2  | 產品B | 標籤3       | 200  | 250   | userB | 2024-06-01 12:00:00 |

    Scenario: ID不存在的產品
       Given 使用者已登入並擁有有效的登入資訊
        And Redis中存在"products:info"且包含以下產品資訊
          | id | name | label_names | cost | price| delete_flag | updated_user | updated_at |
          | 1  | 產品A | 標籤1,標籤2 | 100  | 150   | false | userA | 2024-06-01 12:00:00 |
          | 2  | 產品B | 標籤3       | 200  | 250   | false | userB | 2024-06-01 12:00:00 |
          | 3  | 產品C | 標籤4       | 300  | 350   | true | userC | 2024-06-01 12:00:00 |
       When API productId 被設定為 "4"
       Then 回傳錯誤訊息 "產品不存在"