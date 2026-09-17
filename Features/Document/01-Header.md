# HTTP Header

## I. 需求簡介

HTTP Header 用於在客戶端與伺服器之間傳遞請求和響應的元數據，包含內容類型、接受類型、授權資訊等。

## II. 需求說明

HTTP Header 以標準 HTTP Header Key-Value 格式傳遞。
系統內部應建立對應的 Header Object，用於統一解析與存取 Request / Response Header 資訊。

### 2-1. Header內容

HTTP Header 包含以下欄位，用於描述請求或響應的元數據。請根據以下欄位建立對應的Object:

| Header 欄位 | 說明 | 預設值 |
|-------------|------|---------|
| Content-Type | 指定請求或響應的內容類型 | `application/json` |
| Accept | 指定客戶端可接受的內容類型 | `application/json` |
| User-Agent | 描述客戶端的軟體資訊 | |
| Status Code | 指定響應的狀態碼 | |
| Status | 指定響應的狀態 | |
| Message | 指定響應的訊息 | |
| Uid| 指定用戶名稱 | 登入後可獲取 |
| Authorization | 指定用戶的授權資訊 | 登入後可獲取 |


### 2-2. Header Status

Header Status 用於描述響應的狀態碼及其對應的訊息。常見的狀態碼包括：

| 狀態碼 | 說明 |
|--------|------|
| 200 | 請求成功 |
| 400 | 請求錯誤 |
| 401 | 未授權 |
| 403 | 禁止訪問 |
| 404 | 資源未找到 |
| 500 | 伺服器內部錯誤 |

### 2-3. Authorization

當使用者登入請求時，伺服器會在響應的 Header 中返回 Authorization 欄位，用於後續請求的授權驗證。
Authorization 欄位已JWT（JSON Web Token）格式返回，用於後續請求的授權驗證。
如果開發者啟動後端為`DEBUG`模式，可以不必在每次請求中都提供 Authorization 欄位，提高開發者使用Postman或其他測試工具的便利性。
如果開發者啟動後端為`PRODUCTION`模式，則每次請求都必須提供有效的 Authorization 欄位，以確保安全性。

JWT會透過Redis暫存於伺服器端
- Key: <Uid>:Authorization:JWT
- Value: <JWT Token>
- Expiration: 600秒，如果有進行相關操作，則會延長有效期限
