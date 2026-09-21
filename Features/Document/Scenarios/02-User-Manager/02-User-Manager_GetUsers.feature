Feature: 取得使用者資料

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

    Scenario: 使用者未登入，取得使用者資料失敗
        Given 使用者未登入
        When 使用者請求取得使用者資料
        Then 回傳登入錯誤訊息
    
    