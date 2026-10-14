Feature: 下載商品資料成Excel

    Scenario: 成功下載商品資料成Excel且Redis中存在商品資料
      Given 使用者已登入系統並獲取Authorization資訊
        And Redis 中的 "products:info" 包含以下產品
            | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
        And Redis 中的 "product:labels" 包含以下標籤
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
       When 使用者傳入"1710000000123,1710000000124"的商品ID
        And 移除<uid>.xlsx的檔案於指定目錄下
       Then 建立一個<uid>.xlsx的檔案於指定目錄下
        And 建立"Update Product"分頁
        And 將以下商品資料填入"Update Product"分頁中
            | 商品ID       | 商品名稱         | 商品分類       | 成本 | 價格 | 庫存 |
            | 1710000000123 | test product   | label1        | 100  | 150   | 5  |
            | 1710000000124 | test product 2 | label1,label2 | 100  | 150   | 5  |
        And 儲存Excel檔案
        And 關閉Excel檔案
        And 回傳<uid>.xlsx的檔案於使用者端
    
    Scenario: 成功下載商品資料成Excel且Redis中不存在商品資料
      Given 使用者已登入系統並獲取Authorization資訊
        And Redis沒有 "products:info" 這個Key值
        And Redis 中的 "product:labels" 包含以下標籤
            | id | name   |
            | 1  | label1 |
            | 2  | label2 |
            | 3  | label3 |
        And tb_products 有以下商品資料
            | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
       When 使用者傳入"1710000000123,1710000000124"的商品ID
        And 移除<uid>.xlsx的檔案於指定目錄下
       Then 新增"products:info"給Redis，並將以下資料放入
            | id            | name           | label_ids | cost | price | stock | created_uid | created_at          | updated_uid | updated_at          |
            | 1710000000123 | test product   | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000124 | test product 2 | 1,2       | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000125 | test product 3 | 3         | 100  | 150   | 5     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
            | 1710000000126 | test product 4 | 2         | 100  | 160   | 2     | user-001    | 2024-04-02 12:00:00 | user-001    | 2024-04-02 12:00:00 |
        And 建立一個<uid>.xlsx的檔案於指定目錄下
        And 建立"Update Product"分頁
        And 將以下商品資料填入"Update Product"分頁中
            | 商品ID       | 商品名稱 | 商品分類 | 成本 | 價格 | 庫存 |
            | 1710000000123 | test product   | label1        | 100  | 150   | 5  |
            | 1710000000124 | test product 2 | label1,label2 | 100  | 150   | 5  |
        And 儲存Excel檔案
        And 關閉Excel檔案
        And 回傳<uid>.xlsx的檔案於使用者端
    
    