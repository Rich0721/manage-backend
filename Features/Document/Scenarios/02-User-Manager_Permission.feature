Feature: 使用者權限管理

  Rule: 使用者列表查詢權限

    Scenario: Admin 可以查詢所有使用者列表
      Given 使用者已登入
      And 使用者權限為 "admin"
      And 系統存在以下使用者
        | Email                | Permission |
        | admin2@example.com   | admin      |
        | manager@example.com  | manager    |
        | normal1@example.com  | user       |
        | normal2@example.com  | user       |
      When 使用者請求查詢使用者列表
      Then 系統應返回以下使用者資訊
        | Email                | Permission |
        | admin2@example.com   | admin      |
        | manager@example.com  | manager    |
        | normal1@example.com  | user       |
        | normal2@example.com  | user       |


    Scenario: Manager 只能查詢 User 使用者列表
      Given 使用者已登入
      And 使用者權限為 "manager"
      And 系統存在以下使用者
        | Email                | Permission |
        | admin@example.com    | admin      |
        | manager2@example.com | manager    |
        | normal1@example.com  | user       |
        | normal2@example.com  | user       |
      When 使用者請求查詢使用者列表
      Then 系統應只返回權限為 "user" 的使用者資訊
        | Email               | Permission |
        | normal1@example.com | user       |
        | normal2@example.com | user       |


    Scenario: User 無權限查詢使用者列表
      Given 使用者已登入
      And 使用者權限為 "user"
      When 使用者請求查詢使用者列表
      Then 系統應拒絕查詢使用者列表
      And 系統應返回 "無權限"

  Rule: 使用者權限更新

    Scenario: Admin 將 User 權限更新為 Manager
      Given 使用者已登入
      And 使用者權限為 "admin"
      And 系統存在以下使用者
        | Email              | Permission |
        | normal@example.com | user       |
      When 使用者更新以下使用者權限
        | Email              | Permission |
        | normal@example.com | manager    |
      Then 系統應成功更新使用者權限
      And 系統中的使用者權限應為
        | Email              | Permission |
        | normal@example.com | manager    |


    Scenario: Admin 將 Manager 權限更新為 User
      Given 使用者已登入
      And 使用者權限為 "admin"
      And 系統存在以下使用者
        | Email               | Permission |
        | manager@example.com | manager    |
      When 使用者更新以下使用者權限
        | Email               | Permission |
        | manager@example.com | user       |
      Then 系統應成功更新使用者權限
      And 系統中的使用者權限應為
        | Email               | Permission |
        | manager@example.com | user       |


    Scenario: Manager 將 User 權限更新為 Manager
      Given 使用者已登入
      And 使用者權限為 "manager"
      And 系統存在以下使用者
        | Email              | Permission |
        | normal@example.com | user       |
      When 使用者更新以下使用者權限
        | Email              | Permission |
        | normal@example.com | manager    |
      Then 系統應成功更新使用者權限
      And 系統中的使用者權限應為
        | Email              | Permission |
        | normal@example.com | manager    |


    Scenario: Manager 無法更新 Manager 的權限
      Given 使用者已登入
      And 使用者權限為 "manager"
      And 系統存在以下使用者
        | Email                | Permission |
        | manager2@example.com | manager    |
      When 使用者更新以下使用者權限
        | Email                | Permission |
        | manager2@example.com | user       |
      Then 系統應拒絕更新使用者權限
      And 系統應返回 "無權限"
      And 系統中的使用者權限應維持為
        | Email                | Permission |
        | manager2@example.com | manager    |


    Scenario: Manager 無法更新 Admin 的權限
      Given 使用者已登入
      And 使用者權限為 "manager"
      And 系統存在以下使用者
        | Email             | Permission |
        | admin@example.com | admin      |
      When 使用者更新以下使用者權限
        | Email             | Permission |
        | admin@example.com | user       |
      Then 系統應拒絕更新使用者權限
      And 系統應返回 "無權限"
      And 系統中的使用者權限應維持為
        | Email             | Permission |
        | admin@example.com | admin      |


    Scenario: User 無法更新其他使用者的權限
      Given 使用者已登入
      And 使用者權限為 "user"
      And 系統存在以下使用者
        | Email               | Permission |
        | normal2@example.com | user       |
      When 使用者更新以下使用者權限
        | Email               | Permission |
        | normal2@example.com | manager    |
      Then 系統應拒絕更新使用者權限
      And 系統應返回 "無權限"
      And 系統中的使用者權限應維持為
        | Email               | Permission |
        | normal2@example.com | user       |
