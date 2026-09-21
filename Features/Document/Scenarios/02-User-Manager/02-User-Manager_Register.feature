Feature: 使用者註冊

  Scenario: 使用有效的註冊資訊成功註冊
    Given 使用者尚未註冊
    And 使用者輸入以下註冊資訊
      | Email            | UserName    | Password    | ConfirmPassword |
      | user@example.com | testuser    | Test123456! | Test123456!     |
    When 使用者提交註冊資訊
    Then 系統應成功建立使用者帳號


  Rule: Email 驗證

    Scenario Outline: Email 格式不正確
      Given 使用者輸入以下註冊資訊
        | Email   | UserName    | Password    | ConfirmPassword |
        | <Email> | testuser    | Test123456! | Test123456!     |
      When 使用者提交註冊資訊
      Then 系統應拒絕建立使用者帳號
      And 系統應回傳 Email 格式不正確的錯誤訊息

      Examples:
        | Email        |
        | user         |
        | user@        |
        | @example.com |
        | user@example |


    Scenario: Email 已存在
      Given 系統已存在以下使用者
        | Email            |
        | user@example.com |
      And 使用者輸入以下註冊資訊
        | Email            | UserName    | Password    | ConfirmPassword |
        | user@example.com | testuser    | Test123456! | Test123456!     |
      When 使用者提交註冊資訊
      Then 系統應拒絕建立使用者帳號
      And 系統應回傳 Email 已存在的錯誤訊息


  Rule: 密碼驗證

    Scenario: 密碼與確認密碼不相符
      Given 使用者輸入以下註冊資訊
        | Email            | UserName    | Password    | ConfirmPassword |
        | user@example.com | testuser    | Test123456! | Test654321!     |
      When 使用者提交註冊資訊
      Then 系統應拒絕建立使用者帳號
      And 系統應回傳密碼與確認密碼不相符的錯誤訊息