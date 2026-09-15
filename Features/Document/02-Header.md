# HTTP Header

## I. 需求簡介

HTTP Header 用於在客戶端與伺服器之間傳遞請求和響應的元數據，包含內容類型、接受類型、授權資訊等。

## II. 需求說明


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
| uid| 指定用戶名稱 | 登入後可獲取 |
| Permission | 指定用戶的權限 | 登入後可獲取 |


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