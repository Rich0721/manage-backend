# 01-User-Manager

## I. 需求簡介

此功能用於管理使用者的相關資訊，例如使用者登入、登出、註冊及權限管理。

## II. 需求說明

### 2-1. 使用者註冊

Flow Chat: [使用者註冊流程圖](flows/01-User-Manager_Register.mmd)
Gherkin: [使用者註冊情境文件](scenarios/01-User-Manager_Register.feature)
METHOD: POST

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
#### 2-2-1. 使用者登入

#### 使用者操作
使用者於前端填寫登入表單，包含*Email*及*Password*欄位，並提交表單以完成第一階段登入，並且系統會產生*臨時編號*進行第二階段驗證。

#### Business Rules
- 驗證*Email*格式正確
- 驗證*Email*是否已註冊
- 驗證*Password*是否正確
- 登入失敗超過五次鎖定15分鐘
- 臨時編號需在3分鐘內有效
- 臨時編號錯誤超過五次鎖定 5 分鐘

#### Technical Requirements
- Temporary Code 儲存於 Redis
- Temporary Code 使用 Redis TTL 控制有效期限
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
暫未實作，請先保留對應接口即可

### 2-4. 使用者權限管理
Flow Chat: [使用者權限管理流程圖](flows/01-User-Manager_Permission.mmd)
Gherkin: [使用者權限管理情境文件](scenarios/01-User-Manager_Permission.feature)
拿取使用者資料 METHOD: POST
更新使用者權限 METHOD: PUT

#### 使用者操作

使用者於前端進入使用者權限管理頁面，系統會顯示所有使用者的資料及其當前角色。

使用者權限管理功能允許系統管理員更新使用者的權限。管理員可以為使用者分配不同的角色
- 角色類別:
    1. *admin*: 系統管理員，擁有最高權限
    2. *manager*: 管理者，擁有部分管理權限
    3. *user*: 一般使用者，註冊後的預設角色，具備基本瀏覽權限

- 獲取所有使用者資料: 僅有*admin*角色和*manager*角色的使用者可以獲取其他使用者的資料
    1. *admin*: 可以獲取所有使用者的資料
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
| password    | VARCHAR   | 使用者密碼，需經過哈希處理 | 使用SHA-256演算法 |
| permission    | VARCHAR   | 使用者權限| 僅有 admin, manager和user, 預設為user |
| created_at  | TIMESTAMP | 創建時間 | 系統自動生成 |
| updated_at  | TIMESTAMP | 更新時間 | 系統自動更新 |