Feature: 使用者登入

  Rule: 使用者登入驗證

    Scenario: 使用有效的帳號密碼登入成功且該帳號未在其他裝置登入
      Given 系統存在以下使用者
        | Email            | Password    |
        | user@example.com | Test123456! |
      And 使用者輸入以下登入資訊
        | Email            | Password    | isForceLogin |
        | user@example.com | Test123456! | false |
      And "<uid>:login"的Key未於Redis中存在
      When 使用者提交登入資訊
      Then 產生SessionId並存於Redis，key為"<uid>:login"
    
    Scenario: 登入時發現該帳號已在其他裝置登入
      Given 系統存在以下使用者
        | Email            | Password    |
        | user@example.com | Test123456! |
      And 使用者輸入以下登入資訊
        | Email            | Password    | isForceLogin |
        | user@example.com | Test123456! | false |
      And "<uid>:login"的Key於Redis中存在
      When 使用者提交登入資訊
      Then 系統回傳"該帳號已在其他裝置登入，是否強制登入"訊息
       And 系統不應產生SessionId

    Scenario: 登入時發現該帳號已在其他裝置登入，選擇強制登入
      Given 系統存在以下使用者
        | Email            | Password    |
        | user@example.com | Test123456! |
      And 使用者輸入以下登入資訊
        | Email            | Password    | isForceLogin |
        | user@example.com | Test123456! | true |
      And "<uid>:login"的Key於Redis中存在
      When 使用者提交登入資訊
       And 系統移除"<uid>:login"的Key於Redis中
      Then 產生SessionId並存於Redis，key為"<uid>:login"

    Scenario: 使用未註冊的 Email 登入失敗
      Given 系統不存在 Email "unknown@example.com" 的使用者
      And 使用者輸入以下登入資訊
        | Email               | Password    |
        | unknown@example.com | Test123456! |
      When 使用者提交登入資訊
      Then 系統應拒絕登入驗證
      And 系統應回傳登入失敗訊息
      And 系統不應產生SessionId

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
      And 系統不應產生SessionId
    