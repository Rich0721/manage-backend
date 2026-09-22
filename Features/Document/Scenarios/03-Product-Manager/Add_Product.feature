Feature: 新增產品
  使用者必須具有有效的 Authorization 與新增產品權限。
  系統應解析產品標籤、建立產品資料，並更新產品資訊快取。

  Rule: 新增產品授權

    Scenario: 未提供 Authorization 時新增產品失敗
      Given 使用者的請求未包含 Authorization
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label1,label2 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 回應狀態碼應為 401
      And 回應訊息應為 "Unauthorized"
      And 系統不應新增資料至 "tb_products"
      And 系統不應更新 Redis 中的 "product:info"


    Scenario Outline: Authorization 無效時新增產品失敗
      Given 使用者的 Authorization 狀態為 "<authorization_status>"
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label1,label2 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 回應狀態碼應為 401
      And 回應訊息應為 "Unauthorized"
      And 系統不應新增資料至 "tb_products"
      And 系統不應更新 Redis 中的 "product:info"

      Examples:
        | authorization_status |
        | 無效                 |
        | 已過期               |


  Rule: 使用 Redis 解析產品標籤

    Scenario: Redis 已存在所有指定標籤時成功解析標籤
      Given UID 為 "user-001" 的使用者具有有效的 Authorization
      And 該使用者具有新增產品的權限
      And Redis 中的 "product:labels" 包含以下標籤
        | id | name   |
        | 1  | label1 |
        | 2  | label2 |
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label1,label2 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 系統應使用 Redis 中的標籤資料解析 "label_names"
      And 新增至 "tb_products" 的產品其 "label_ids" 應為 "1,2"
      And 回應狀態碼應為 200


    Scenario: product labels Key 不存在時從資料庫載入標籤
      Given UID 為 "user-001" 的使用者具有有效的 Authorization
      And 該使用者具有新增產品的權限
      And Redis 中不存在 "product:labels"
      And "tb_labels" 存在以下標籤
        | id | name   |
        | 1  | label1 |
        | 2  | label2 |
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label1,label2 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 系統應從 "tb_labels" 載入標籤資料
      And Redis 中的 "product:labels" 應包含以下標籤
        | id | name   |
        | 1  | label1 |
        | 2  | label2 |
      And 新增至 "tb_products" 的產品其 "label_ids" 應為 "1,2"
      And 回應狀態碼應為 200
      And Redis 中的 "product:info" 應包含新增的產品


    Scenario: Redis 找不到指定標籤時重新載入標籤
      Given UID 為 "user-001" 的使用者具有有效的 Authorization
      And 該使用者具有新增產品的權限
      And Redis 中的 "product:labels" 不包含 "label3" 與 "label4"
      And "tb_labels" 存在以下標籤
        | id | name   |
        | 3  | label3 |
        | 4  | label4 |
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label3,label4 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 系統應清除 Redis 中原有的 "product:labels"
      And 系統應從 "tb_labels" 重新載入標籤資料
      And Redis 中的 "product:labels" 應包含以下標籤
        | id | name   |
        | 3  | label3 |
        | 4  | label4 |
      And 新增至 "tb_products" 的產品其 "label_ids" 應為 "3,4"
      And 回應狀態碼應為 200
      And Redis 中的 "product:info" 應包含新增的產品


    Scenario: 重新載入標籤後仍找不到指定標籤時新增產品失敗
      Given UID 為 "user-001" 的使用者具有有效的 Authorization
      And 該使用者具有新增產品的權限
      And Redis 中的 "product:labels" 不包含 "unknown-label"
      And "tb_labels" 中不存在名稱為 "unknown-label" 的標籤
      And 使用者輸入以下產品資訊
        | name         | label_names  | cost | price |
        | test product | unknown-label | 100 | 150   |
      When 使用者提交新增產品請求
      Then 系統應重新載入 "product:labels"
      And 系統應拒絕新增產品
      And 回應狀態碼應為 400
      And 回應訊息應為 "Product label does not exist"
      And 系統不應新增資料至 "tb_products"
      And 系統不應更新 Redis 中的 "product:info"


  Rule: 成功建立產品

    Scenario: 使用有效產品資料成功新增產品
      Given UID 為 "user-001" 的使用者具有有效的 Authorization
      And 該使用者具有新增產品的權限
      And 目前的 Unix 毫秒時間為 "1710000000123"
      And Redis 中的 "product:labels" 包含以下標籤
        | id | name   |
        | 1  | label1 |
        | 2  | label2 |
      And 使用者輸入以下產品資訊
        | name         | label_names   | cost | price |
        | test product | label1,label2 | 100  | 150   |
      When 使用者提交新增產品請求
      Then 系統應新增以下產品至 "tb_products"
        | id            | name         | label_ids | cost | price | created_uid | created_at          | updated_uid | updated_at          |
        | 1710000000123 | test product | 1,2       | 100  | 150   | user-001    | 2024-04-01 12:00:00 | user-001    | 2024-04-01 12:00:00 |
      And 新增產品的 "created_at" 應為目前系統時間
      And 回應狀態碼應為 200
      And 回應訊息應為 "OK"
      And 回應應包含以下產品資訊
        | id            | name         | label_names   | cost | price |
        | 1710000000123 | test product | label1,label2 | 100  | 150   |
      And Redis 中的 "product:info" 應包含產品 "1710000000123"
      And Redis 中產品 "1710000000123" 的資料應與 "tb_products" 一致