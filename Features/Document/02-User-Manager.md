# 01-User-Manager

## I. 需求簡介

此功能用於管理使用者的相關資訊，例如使用者登入、登出、註冊及權限管理。
Header說明請參考[HTTP Header](02-Header.md)文檔。

## II. 需求說明

### 2-1. 使用者註冊

Flow Chat: [使用者註冊流程圖](flows/01-User-Manager_Register.mmd)
Gherkin: [使用者註冊情境文件](scenarios/01-User-Manager_Register.feature)
METHOD: POST
uri: /userController/register

#### Status與Message說明對照表

| Status Code | Status| Message | 條件|
| --- | --- | --- | --- |
| 200 | Success | User registered successfully | 當後端成功處理使用者註冊請求 |
| 401 | Failed | User registration failed | 當後端處理使用者註冊有錯誤情境發生時 |


#### Request Body

```json
{
    "header":{
        
    },
    "body":{
        "email": "user@example.com",
        "userName": "example_user",
        "password": "SHA-256-hashed-password",
        "confirmPassword": "SHA-256-hashed-password"
    }
}
```

#### Response Body

```json
{
    "header":{

    },
    "body":{
        "uid": "generated-uid",
        "email": "user@example.com",
        "permission": "user",
        "created_at": "2024-06-01T12:00:00Z",
        "updated_at": "2024-06-01T12:00:00Z"
    }
}
```

#### 使用者操作
使用者於前端填寫註冊表單，包含*Email*、*Password*及*ConfirmPassword*欄位，並提交表單以完成註冊操作。

#### Business Rules
- 驗證*Email*格式正確
- 驗證*Password*與*ConfirmPassword*相符
- 驗證*Email*是否已存在

#### Technical Requirements
- 產生使用者的唯一識別碼(Uid)，使用Email進行哈希處理，採用SHA-256演算法。
- 將產生的Uid作為使用者的唯一識別碼與使用者資訊一同存入資料庫


### 2-2. 使用者登入
Flow Chat: [使用者登入流程圖](flows/01-User-Manager_Login.mmd)
Gherkin: [使用者登入情境文件](scenarios/01-User-Manager_Login.feature)
METHOD: POST
uri: /userController/login

#### Status與Message說明對照表

| Status Code | Status| Message | 條件|
| --- | --- | --- | --- |
| 200 | Success | User logged in successfully, Temporary code has been sent to your email | 當後端確認為正確的Email及Password完成第一階段登入 |
| 200 | Success | User logged in successfully | 當後端確認為正確的Email及Temporary Code完成第二階段登入 |
| 401 | Failed | User login failed | 當後端確認為錯誤的Email或Password完成第一階段登入失敗|
| 401 | Failed | Temporary code verification failed | 當後端確認為錯誤的Temporary Code完成第二階段登入失敗 |

#### Request Body I

```json
{
    "header":{
        "content-type": "application/json",
        "accept": "application/json"
    },
    "body":{
        "email": "user@example.com",
        "password": "SHA-256-hashed-password"
    }
}
```

#### Response Body I

```json
{
    "header":{
        "content-type": "application/json",
        "accept": "application/json",
        "status": "success",
        "message": "User logged in successfully, Temporary code has been sent to your email"
    },
    "body":{
        
    }
}
```

#### Request Body II

```json
{
    "header":{
        
    },
    "body":{
        "email": "user@example.com",
        "temporary_code": "generated-temporary-code"
    }
}
```

#### Response Body II

```json
{
    "header":{
        "content-type": "application/json",
        "accept": "application/json",
        "status": "success",
        "message": "User logged in successfully"
    },
    "body":{
    }
}
```


#### 2-2-1. 使用者登入

#### 使用者操作
使用者於前端填寫登入表單，包含*Email*及*Password*欄位，並提交表單以完成第一階段登入，並且系統會產生*Temporary Code*進行第二階段驗證。

#### Business Rules
- 驗證*Email*格式正確
- 驗證*Email*是否已註冊
- 驗證*Password*是否正確
- Temporary Code需在3分鐘內有效
- Temporary Code須可以重新生成，但須要移除舊的Temporary Code
- *Password*會由前端經過SHA-256演算法進行哈希處理後再傳送至後端
- 使用者登入後，除了*register*和*login*接口外，其他操作皆需驗證使用者的登入狀態，目前先透過header的Uid確認是否有登入，如果沒有登入則拒絕訪問

#### Technical Requirements
- Temporary Code 儲存於 Redis
- Temporary Code 使用 Redis TTL 控制有效期限
- Temporary Code為隨機生成的6位數字或英文，並且以*Email*為key存儲於Redis，如果使用者在有效期限內未使用，Redis會自動刪除該臨時編號。
- Email 使用 SMTP 發送
- SQL Query 必須使用 Parameterized Query

### 2-2-2. 臨時編號Email樣板

範例內容如下：

```text
主旨: 您的臨時登入編號

親愛的使用者，您好：

您本次的臨時登入編號為：{{temporary_code}}
此編號有效期限為3分鐘，請在有效期限內使用。

若非您本人操作，請忽略此郵件。

謝謝。
```

### 2-3. 使用者登出
METHOD: POST
uri: /userController/logout
暫未實作，請先保留對應接口即可

#### Status與Message說明對照表

| Status Code | Status| Message | 條件|
| --- | --- | --- | --- |
| 200 | Success | User logged out successfully | 當使用者登出成功時 |

#### Request Body

```json
{
    "header":{
        
    },
    "body":{
        "email": "user@example.com",
    }
}
```

#### Response Body

```json
{
    "header":{
        "content-type": "application/json",
        "accept": "application/json",
        "status": "success",
        "message": "User logged out successfully"
    },
    "body":{
    }
}
```


### 2-4. 使用者權限管理
Flow Chat: [使用者權限管理流程圖](flows/01-User-Manager_Permission.mmd)
Gherkin: [使用者權限管理情境文件](scenarios/01-User-Manager_Permission.feature)
| Description | Method | URI |
| --- | --- | --- |
| 拿取使用者資料 | GET | /userController/getUsers?uid=<user-uid> |
| 更新使用者權限 | PUT | /userController/updatePermission |

#### Status與Message說明對照表 - 拿取使用者資料

| Status Code | Status| Message | 條件|
| --- | --- | --- | --- |
| 200 | Success | User data retrieved successfully | 當使用者有權限獲取資料且資料成功返回 |
| 401 | Failed | Unauthorized | 使用者無權限訪問該資源|

#### Status與Message說明對照表 - 更新使用者權限

| Status Code | Status| Message | 條件|
| --- | --- | --- | --- |
| 200 | Success | User permission updated successfully | 當使用者權限更新成功時 |
| 401 | Failed | Unauthorized | 使用者無權限訪問該資源|

#### Request Body - 拿取使用者資料

```json
{
    "header":{
        
    }
}
```

#### Response Body - 拿取使用者資料

```json
{
    "header":{
        
    },
    "body": [
        {
            "uid": "user-uid",
            "user_name": "user-name",
            "permission": "user"
        }
    ]
}
```

#### Request Body - 更新使用者權限

```json
{
    "header":{
        "uid": "admin-uid"
    },
    "body":{
        "uid": "user-uid",
        "target_role": "manager"
    }
}
```

#### Response Body - 更新使用者權限

```json
{
    "header":{
        "content-type": "application/json",
        "accept": "application/json",
        "status": "success",
        "message": "User permission updated successfully"
    },
    "body":{
    }
}
```

#### 使用者操作

使用者於前端進入使用者權限管理頁面，系統會顯示所有使用者的資料及其當前角色。

使用者權限管理功能允許系統管理員更新使用者的權限。管理員可以為使用者分配不同的角色
- 角色類別:
    1. *admin*: 系統管理員，擁有最高權限
    2. *manager*: 管理者，擁有部分管理權限
    3. *user*: 一般使用者，註冊後的預設角色，具備基本瀏覽權限

- 獲取所有使用者資料: 僅有*admin*角色和*manager*角色的使用者可以獲取其他使用者的資料，需排除*自己*
    1. *admin*: 可以獲取除了其他*admin*使用者的使用者的資料
    2. *manager*: 僅能獲取一般使用者的資料
    3. *user*: 無法獲取其他使用者的資料
- 更新使用者權限請參照下表

| Operator | Target current role | Allowed target role |
|----------|-------------------|-------------------|
| admin    | user              | user / manager     |
| admin    | manager           | user / manager     |
| admin    | admin             | 不可修改或另行定義 |
| manager  | user              | user / manager     |
| manager  | manager           | 不可修改           |
| manager  | admin             | 不可修改           |
| user     | 任意              | 不可修改           |

- 根據*getUsers*的uid進行資料庫辨別權限程度後，根據*獲取所有使用者資料*規則返回相應的使用者資料列表


## III. 其他資訊

### 3-1. 系統版本規格:
- Python: 3.14
- PostgreSQL: 17
- FastAPI: 0.141.1

### 3-2. Table Structure

#### 3-2-1. Users Table
Table Name: TB_USERS

| Column Name | Data Type | Description | Details |
|-------------|-----------|-------------|---------|
| uid         | VARCHAR   | 使用者ID，主鍵 | 根據Email進行Uid編碼 |
| email       | VARCHAR   | 使用者Email，唯一 | 需確認格式正確且唯一 |
| user_name   | VARCHAR   | 使用者名稱 | 前端顯示用，非唯一 |
| password    | VARCHAR   | 使用者密碼，需經過哈希處理 | 使用SHA-256演算法 |
| permission    | VARCHAR   | 使用者權限| 僅有 admin, manager和user, 預設為user |
| created_at  | TIMESTAMP | 創建時間 | 系統自動生成 |
| updated_at  | TIMESTAMP | 更新時間 | 系統自動更新 |

### 3-3. Admin設定
Admin權限將由網管人員設定，並無法透過前端使用者介面進行修改。
已透過條件排除可查詢其他Admin的資料，包括自己，如果修改到其他Admin的權限，前後端都直接拒絕操作。