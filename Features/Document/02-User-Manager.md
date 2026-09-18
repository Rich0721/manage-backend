# 01-User-Manager

## I. 需求簡介

此功能用於管理使用者的相關資訊，例如使用者登入、登出、註冊及權限管理。
Header說明請參考[HTTP Header](01-Header.md)文檔。

## II. 需求說明

### 2-1. 使用者註冊

Flow Chat: [使用者註冊流程圖](flows/01-User-Manager_Register.mmd)
Gherkin: [使用者註冊情境文件](scenarios/01-User-Manager_Register.feature)
METHOD: POST
uri: /userController/register

#### 2-1-1. Request Body Authorization
此接口不需要額外的授權資訊，使用者僅需提供註冊所需的資訊即可。

#### 2-1-2. Request Body Information Object

此物件包含使用者註冊所需資本物件，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| email | string | 使用者的電子郵件 |
| userName | string | 使用者名稱 |
| password | string | 使用者密碼 |
| confirmPassword | string | 確認密碼 |

#### 2-1-3. Response Body Authorization
註冊成功或失敗的授權資訊。
| Status | Message | 條件 |
| --- | --- | --- |
| Success | 註冊成功 | 註冊成功時返回 |
| Failed | 註冊失敗 | 註冊失敗時返回 |

#### 2-1-4. Response Body Information Object

此物件包含使用者註冊成功後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| uid | string | 使用者的唯一識別碼 |
| email | string | 使用者的電子郵件 |
| userName | string | 使用者名稱 |


#### 2-1-5. 使用者操作
使用者於前端填寫註冊表單，包含*Email*、*UserName*、*Password*及*ConfirmPassword*欄位，並提交表單以完成註冊操作。

#### 2-1-6. Business Rules
- 驗證*Email*格式正確
- 驗證*Password*與*ConfirmPassword*相符
- 驗證*Email*是否已存在

#### 2-1-7. Technical Requirements
- 產生使用者的唯一識別碼(Uid)，使用Email進行哈希處理，採用SHA-256演算法。
- 將產生的Uid作為使用者的唯一識別碼與使用者資訊一同存入資料庫


### 2-2. 使用者登入
Flow Chat: [使用者登入流程圖](flows/01-User-Manager_Login.mmd)
Gherkin: [使用者登入情境文件](scenarios/01-User-Manager_Login.feature)
METHOD: POST
uri: /userController/login


#### 2-2-1. Request Body Authorization
此接口不需要額外的授權資訊，使用者僅需提供登入所需的資訊即可。

#### 2-2-2. Request Body Information Object

此物件包含使用者登入所需資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| email | string | 使用者的電子郵件 |
| password | string | 使用者密碼 |
| forceLogin | boolean | 是否強制使用者重新登入 |

#### 2-2-3. Response Body Authorization
根據使用者操作會有三種情境:
1. 使用者登入成功且該帳號未在其他裝置登入
2. 使用者登入成功但該帳號已在其他裝置登入
3. 使用者登入失敗


如果是`情境1`，則根據下表資訊返回:
| Authorization欄位 | 回傳值 |
| --- | --- |
| Status | Success |
| Message | User logged in successfully |
| Uid | 使用者的唯一識別碼 |
| Authorization | 由後端透過Bearer Token返回的授權資訊 |

---
如果是`情境2`，則根據下表資訊返回:
| Authorization欄位 | 回傳值 |
| --- | --- |
| Status | Success |
| Message | User logged in successfully, but already logged in on another device |
| Uid | 使用者的唯一識別碼 |
| Authorization | 由後端透過Bearer Token返回的授權資訊 |
---

如果是`情境3`，則根據下表資訊返回:
| Authorization欄位 | 回傳值 |
| --- | --- |
| Status | Failed |
| Message | User login failed |
| Uid | 使用者的唯一識別碼 |
| Authorization | 由後端透過Bearer Token返回的授權資訊 |
---

#### 2-2-4. Response Body Information Object

此物件包含使用者登入成功後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| userName | string | 使用者名稱 |
| needForceLogin | boolean | 是否需要使用者強制重新登入 |

#### 2-2-5. 使用者操作
使用者於前端填寫登入表單，包含*Email*及*Password*欄位，並提交表單以完成登入操作。

#### 2-2-6. Business Rules
- 驗證*Email*格式正確
- 驗證*Email*是否已註冊
- 驗證*Password*是否正確
- 登入成功後都需要檢查Redis中是否存在對應的`<uid>:login` key，確認屬於`情境1`或`情境2`。
- `情境1`時，系統直接於Redis配置`<uid>:login` key，並將`Authorization`資訊作為value，TTL為600秒。
- `情境2`時，則表示該使用者已在其他裝置登入，如果使用者選擇強制登入，則需要於對應的`<uid>:login` key，放入新的`Authorization`資訊，並重新設定TTL為600秒。


#### 2-2-7. Technical Requirements
- Redis 用於存儲使用者登入資訊，並以 `<uid>:login` 作為 key，`Authorization` 資訊作為 value，TTL 為 600 秒。
- TTL重新設定標準會根據後續操作而定，例如使用者選擇強制登入時，TTL會重新設定為600秒。


### 2-3. 使用者登出
METHOD: POST
uri: /userController/logout

#### 2-3-1. Request Body Authorization

此物件包含使用者登出所需的授權資訊，需繼承自`authorization`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| Uid | string | 使用者的唯一識別碼 |
| Authorization | string | 由後端透過Bearer Token返回的授權資訊 |

#### 2-3-2. Request Body Information Object

此物件包含使用者登出所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| userName | string | 使用者的名稱 |

#### 2-3-3. Response Body Authorization

此物件包含使用者登出後返回登出資訊，因已登出不再需要使用者授權，仍需繼承自`authorization`物件，以利Response Body的結構化。
| Status | Message | 條件 |
| --- | --- | --- |
| Success | 登出成功 | 登出成功時返回 |
| Failed | 登出失敗 | 登出失敗時返回 |

#### 2-3-4. Response Body Information Object

此物件包含使用者登出後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| userName | string | 使用者的名稱 |

#### 2-3-5. 使用者操作
使用者在登入狀態下，點擊登出按鈕以完成登出操作。

#### 2-3-6. Business Rules
- 需先檢查`uid`是否有在`Authorization`中存在，如果不存在代表非合法使用者，登出操作將失敗。
- 需於Redis中找尋對應的`<uid>:login`key，取出對應的Value並且跟`Authorization`中的資訊進行比對，如果一致則刪除該key，完成登出操作，否則登出失敗。

### 2-4. 取得使用者資料
Flow Chat:
Gherkin: 
METHOD: POST
uri: /userController/getUsers

#### 2-4-1. Request Body Authorization

此物件包含取得使用者資料所需的授權資訊，需繼承自`authorization`物件，以利Request Body的結構化。
根據登入後獲得的`Authorization`資訊填寫。

#### 2-4-2. Request Body Information Object

此物件包含取得使用者資料所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。

| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| userName | string | 使用者的名稱 |

#### 2-4-3. Response Body Authorization

此物件包含取得使用者資料後返回的授權資訊，需繼承自`authorization`物件，以利Response Body的結構化。
根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| Success | User data retrieved successfully | 當使用者有權限獲取資料且資料成功返回 |
| Unauthorized | User Permission Denied | 使用者無權限訪問該資源 |

#### 2-4-4. Response Body Information Object

此物件包含取得使用者資料後返回的資訊，需繼承自`Response Information`物件，以利Response Body的結構化。
下列結構以`List`形式返回多個使用者的資料。
| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| email | string | 使用者的電子郵件地址 |
| userName | string | 使用者的名稱 |
| permission | string | 使用者的權限 |

#### 2-4-5. 使用者操作
使用者於前端進入取得使用者資料頁面，系統會根據使用者的權限顯示可訪問的使用者資料列表。

#### 2-4-6. Business Rules
- 需先檢查`uid`是否有在`Authorization`中存在，如果不存在代表非合法使用者，取得使用者資料操作將失敗。
- 需於Redis中找尋對應的`<uid>:login`key，取出對應的Value並且跟`Authorization`中的資訊進行比對，如果一致則允許取得使用者資料，否則操作失敗。
- 取得使用者資料時，先透過uid查詢使用者的基本權限，並根據權限決定可訪問的資料範圍。
  - *admin*: 可以取得所有使用者的資料，並且需要排除其他*admin*的使用者及自己
  - *manager*: 可以取得所有*user*的資料，並且需要排除其他*manager*及*admin*的使用者
  - *user*: 無權限訪問
- 若使用者的權限不足以訪問任何資料，系統將返回空列表。


### 2-5. 使用者權限管理
Flow Chat: [使用者權限管理流程圖](flows/01-User-Manager_Permission.mmd)
Gherkin: [使用者權限管理情境文件](scenarios/01-User-Manager_Permission.feature)
Method: PUT
uri: /userController/updatePermission


#### 2-5-1. Request Body Authorization

此物件包含更新使用者權限所需的授權資訊，需繼承自`authorization`物件，以利Request Body的結構化。
根據登入後獲得的`Authorization`資訊填寫。

#### 2-5-2. Request Body Information Object

此物件包含更新使用者權限所需的資訊，需繼承自`Request Information`物件，以利Request Body的結構化。
以下透過List形式提供給後端，表示可以一次更新多個使用者的權限
| 欄位 | 型別 | 說明 | 
| --- | --- | --- |
| email | string | 目標使用者的電子郵件地址 |
| target_role | string | 目標使用者的角色，僅允許`admin`、`manager`、`user` |

#### 2-5-3. Response Body Authorization

此物件包含更新使用者權限後返回的授權資訊，需繼承自`authorization`物件，以利Response Body的結構化。
根據登入後獲得的`Authorization`資訊填寫，但如果辨別使用者沒有權限訪問該資源，則返回`Unauthorized`訊息。
| Status | Message | 條件 |
| --- | --- | --- |
| Success | User permission updated successfully | 當使用者有權限更新資料且資料成功返回 |
| Unauthorized | User Permission Denied | 使用者無權限訪問該資源 |

#### 2-5-4. 使用者操作
使用者於權限管理頁面進行更新操作，系統會根據使用者的權限決定可操作的範圍。

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

### 3-4. Authorization辨別與更新到期期限
除了`註冊`與`登入`操作外，所有需要授權的操作都必須在Request Body攜帶有效的`Authorization`資訊，請根據以下步驟進行檢查與處理：
1. 需先檢查`uid`是否有在`Authorization`中存在，如果不存在代表非合法使用者，操作將被拒絕。
2. 需於Redis中找尋對應的`<uid>:login`key，取出對應的Value並且跟`Authorization`中的資訊進行比對，如果不一致則操作將被拒絕。
3. 若比對成功，操作將被允許，並可根據需要更新`Authorization`的到期期限，更新期限為當下時間加上300秒。
| 情境 | Status | Message |
| --- | --- | --- |
| 如果於`Step 1`檢查失敗 | Unauthorized | 非法使用者 |
| 如果於`Step 2`比對失敗 | ForceLogout | `Authorization`資訊不一致，操作被拒絕 |
| 如果於`Step 3`比對成功 | 根據後續操作結果 | 操作被允許，`Authorization`到期期限更新，操作結果將依據後續操作而定 |