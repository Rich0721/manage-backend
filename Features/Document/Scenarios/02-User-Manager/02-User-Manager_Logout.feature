Feature: 使用者登出

   Scenario: 使用者成功登出
      Given 使用者已登入系統
      And "<uid>:login"的Key於Redis中存在
      When 使用者提交登出請求
      Then 系統應移除"<uid>:login"的Key於Redis中
      And 系統不應再保有該使用者的SessionId
    
  Scenario: 使用者登出時尚未登入系統
      Given 使用者尚未登入系統
      And "<uid>:login"的Key未於Redis中存在
      When 使用者提交登出請求
      Then 系統回傳"使用者尚未登入"訊息