Feature: 使用者登入

  Rule: 帳號密碼驗證

    Scenario: 使用有效的帳號密碼登入成功
      Given 系統存在以下使用者
        | Email            | Password    |
        | user@example.com | Test123456! |
      And 使用者輸入以下登入資訊
        | Email            | Password    |
        | user@example.com | Test123456! |
      When 使用者提交登入資訊
      Then 系統應成功產生臨時編號


    Scenario: 使用未註冊的 Email 登入失敗
      Given 系統不存在 Email "unknown@example.com" 的使用者
      And 使用者輸入以下登入資訊
        | Email               | Password    |
        | unknown@example.com | Test123456! |
      When 使用者提交登入資訊
      Then 系統應拒絕登入驗證
      And 系統應回傳登入失敗訊息

    Scenario: 使用錯誤的密碼登入失敗
      Given 系統存在以下使用者
        | Email            | Password    |
        | user@example.com | Test123456! |
      And 使用者輸入以下登入資訊
        | Email            | Password    |
        | user@example.com | WrongPass123! |
      When 使用者提交登入資訊
      Then 系統應拒絕登入驗證
      And 系統應回傳登入失敗訊息
    