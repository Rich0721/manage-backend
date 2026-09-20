# 01-Authorization

## I. 需求簡介

基礎的用戶請求資訊格式如下所示：

```json
{
    "header":{},
    "body": {
        "auth":{},
        "info":{}
    }

}
```

- header: 屬於HTTP請求或響應的標頭資訊
- body: 包含請求或響應的主體資訊，其中 auth 用於授權資訊，info 用於用戶資訊
- auth: 包含授權資訊，例如 JWT Token
- info: 根據其他需求會配置不同的資訊，但是key值需統一使用`info`

## II. 需求說明

除了基本的 header 欄位，body 中的 auth 和 info 也需要根據需求進行設置。

### 2-1. Authorization內容

Authorization 包含以下欄位，請根據以下欄位建立對應的Object:

| Authorization欄位 | 說明 | 預設值 |
|-------------|------|---------|
| Status | 指定響應的狀態 | |
| Message | 指定響應的訊息 | |
| Uid| 指定用戶名稱 | 登入後可獲取 |
| Authorization | 指定用戶的授權資訊 | 登入後可獲取使用bearer token |


### 2-2. Authorization

當使用者登入請求時，伺服器會在響應的 Header 中返回 Authorization 欄位，用於後續請求的授權驗證。
Authorization 欄位已JWT（JSON Web Token）格式返回，用於後續請求的授權驗證。
如果開發者啟動後端為`DEBUG`模式，可以不必在每次請求中都提供 Authorization 欄位，提高開發者使用Postman或其他測試工具的便利性。
如果開發者啟動後端為`PRODUCTION`模式，則每次請求都必須提供有效的 Authorization 欄位，以確保安全性。

JWT會透過Redis暫存於伺服器端，如果使用者在不同裝置登入，相關邏輯會由另外的需求處理
- Key: <Uid>:Authorization:JWT
- Value: <JWT Token>
- TTL: Now() + 600秒，如果有進行相關操作，則會延長有效期限
