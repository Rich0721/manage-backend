Feature: 批次處理產品

    Scenario: 批次新增產品
        Given 使用者已登入
          And 目前於tb_products有以下產品
           | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
           | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
          And tb_labels 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
          And Redis 中的 "product:labels" 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
          And Redis 中的 "products:info" 包含以下產品
           | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
           | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
          And 使用者提供的檔案放在"Add Product"分頁中且包含以下內容
           | 商品名稱 | 商品分類 | 成本 | 價錢 | 庫存 |
           | test product 2 | label1,label2 | 100  | 150   | 5 |
           | test product 3 | label3 | 100  | 150   | 5 |
           | test product 4 | label2 | 100  | 160   | 2 |
        When 使用者上傳檔案
         And 檔案為Excel的副檔名
         And 檔案內容符合相關規範
         And 檔案上傳成功，且僅執行Add Product分頁中進行產品新增
        Then tb_labels 應包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
           | 3  | label3 |
         And tb_products 應包含以下產品
           | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
           | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
           | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
           | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
           | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
         And Redis的"product:labels"和"products:info"應更新最新資訊
         And 回傳200的狀態
    
    Scenario: 批次更新產品
        Given 使用者已登入
          And 目前於tb_products有以下產品
            | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
          And tb_labels 包含以下標籤
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
          And Redis 中的 "product:labels" 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
           | 3  | label3 |
          And Redis 中的 "products:info" 包含以下產品
            | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
          And 使用者提供的檔案放在"Update Product"分頁中且包含以下內容
            | 商品ID       | 商品名稱         | 商品分類       | 成本 | 價格 | 庫存 |
            | 1710000000123 | test product   | label1        | 130  | 150   | 5  |
            | 1710000000124 | test product 2 | label1,label2 | 100  | 150   | 7  |
            | 1710000000126 | test product 4 | label4        | 100  | 160   | 2  |
         When 使用者上傳檔案
          And 檔案為Excel的副檔名
          And 檔案內容符合相關規範
          And 檔案上傳成功，且僅執行Update Product分頁中進行產品更新
         Then tb_labels應更新成下列
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
            | 4  | label4 |
          And tb_products應更新成下列
            | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product | 1         | 130  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-03 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 7     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-03 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
            | 1710000000126 | test product 4 | 4         | 100  | 160   | 2     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-03 12:00:00 |
          And Redis的"product:labels"和"products:info"應更新最新資訊
          And 回傳200的狀態
    
    Scenario: 批次新增產品失敗 - Excel內容不符合規範
         Given 使用者已登入
          And 目前於tb_products有以下產品
           | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
           | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
          And tb_labels 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
          And Redis 中的 "product:labels" 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
          And Redis 中的 "products:info" 包含以下產品
           | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
           | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
          And 使用者提供的檔案放在"Add Product"分頁中且包含以下內容
           | 商品名稱 | 商品分類 | 成本 | 價錢 | 庫存 |
           | test product 2 | label1,label2 | test  | 150   | 5 |
           | test product 3 | label3 | 100  | 150   | 5 |
           | test product 4 | label2 | 100  | 160   | 2 |
        When 使用者上傳檔案
         And 檔案為Excel的副檔名
         And 檔案內容不符合相關規範
        Then 回傳400
         And 回傳訊息為"新增商品資料錯誤，請檢查Excel內容"
         And tb_products應維持原本資料
            | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
         And tb_labels應維持原本資料
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
         And Redis 中的"product:labels"和"products:info"應維持原本資料
    
    Scenario: 批次更新產品失敗 - Excel檔案格式錯誤
        Given 使用者已登入
          And 目前於tb_products有以下產品
            | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
          And tb_labels 包含以下標籤
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
          And Redis 中的 "product:labels" 包含以下標籤
           | id | name   |
           | 1  | label1 |
           | 2  | label2 |
           | 3  | label3 |
          And Redis 中的 "products:info" 包含以下產品
            | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
          And 使用者提供的檔案放在"Update Product"分頁中且包含以下內容
            | 商品ID       | 商品名稱         | 商品分類       | 成本 | 價格 | 庫存 |
            | 1710000000123 | test product   | label1        | 130  | 150   | -1  |
            | 1710000000124 | test product 2 | label1,label2 | 100  | -150   | 7  |
            | 1710000000126 | test product 4 | label4        | 100  | 160   | 2  |
        Then 回傳400
         And 回傳訊息為"新增商品資料錯誤，請檢查Excel內容"
         And tb_products應維持以下資料
            | id            | name         | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
          And tb_labels應維持以下標籤
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
          And Redis 的 "product:labels" 和 "products:info" 應維持原本資料
