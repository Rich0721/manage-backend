# Backend Skill

---

name: backend-skill
description: 提供 Python Backend 開發共通規範，適用於 Flask、Django、FastAPI 等後端專案。協助 System Design、Programmer 與 Code Reviewer 在分析、實作與審查後端功能時，遵循既有專案架構、分層責任、資料存取、錯誤處理、Logging、Validation、Dependency 與 Unit Test 規範。

---

## Overview

此 Skill 提供 Python Backend 開發時的共通技術規範。可應用於：

- Flask
- Django
- FastAPI
- 其他 Python Backend Framework

如果使用者已於**instructions/**中提供明確的專案架構規範，則必須優先遵循使用者定義的專案架構。
如果使用者未於**instructions/**中提供專案架構規範，則必須遵循**Skill**所定義的專案架構與共通技術規範。
使用者提供的專案架構規範僅覆蓋與其衝突的架構規則，本**Skill**中其他未衝突的**Backend**技術規範仍然適用。

## Core Principles

Backend 開發應遵循以下原則：

```text
Reuse > Duplication
Simple Design > Over Engineering
Minimal Change > Unrelated Refactoring
Explicit > Implicit
```

實作 Requirement 時：

- 優先修改 Existing Component。
- 優先 Reuse Existing Function / Class / Module。
- 不建立與 Requirement 無關的抽象層。
- 不進行與 Requirement 無關的 Refactoring。
- 不因為存在新的 Framework Pattern 就修改 Existing Architecture。
- 不重複建立 Existing Project 已有的功能。
- 新增 Dependency 前必須確認 Existing Dependency 是否已經可以完成需求。

## Reference Project Structure

如果為 New Project 或專案尚未定義 Backend Structure，可以參考：

```text
backend_project/
├── src/
│   ├── __init__.py
│   ├── routers.py
│   │
│   ├── constants/
│   │   ├── __init__.py
│   │   └── example_constant.py
│   │
│   ├── objects/
│   │   ├── ro/
│   │   │   ├── __init__.py
│   │   │   └── example_ro.py
│   │   ├── bo/
│   │   │   ├── __init__.py
│   │   │   └── example_bo.py
│   │   └── __init__.py
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── example_controller.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── example_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── example_repository.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── example_util.py
│
├── tests/
│   ├── controllers/
│   ├── services/
│   ├── repositories/
│   └── utils/
│
├── config/
│   ├── __init__.py
│   └── database.py
│
├── requirements.txt
└── main.py
```

## Layer Responsibilities

### Controller / Router

Controller / Router 負責處理 Application Boundary。

主要責任：

- 接收 Request。
- Request Parameter Parsing。
- Request Validation。
- Authentication / Authorization Hook。
- 呼叫 Service。
- 將 Service Result 轉換成 Response。
- 設定 HTTP Status。
- 設定 Response Header。

Controller 不應負責：

- Business Logic。
- Database Query。
- Transaction Control。
- 複雜資料轉換。
- 重複 Service 已經提供的 Validation。

建議流程：

```text
HTTP Request
    ↓
Controller
    ↓
Validation
    ↓
Service
    ↓
Response
```

禁止：

```text
Controller
    ↓
直接執行 SQL
```

或：

```text
Controller
    ↓
直接操作 ORM
```

除非 Existing Project Architecture 明確採用不同設計。

### Service

Service 負責 Business Logic 與 Application Workflow。

主要責任：

- Business Rule。
- Workflow Control。
- 呼叫 Repository。
- 呼叫其他 Service。
- Business Validation。
- Transaction Boundary（依 Existing Architecture）。
- Domain Error 處理。

例如：

```python
class UserService:

    def create_user(self, user_data):
        existing_user = self.user_repository.get_by_email(
            user_data.email
        )

        if existing_user:
            raise DuplicateUserError()

        return self.user_repository.create(user_data)
```

Service 不應：

- 直接建立 HTTP Response。
- 依賴 Flask `request`。
- 依賴 FastAPI `Request`。
- 依賴 Django HttpRequest，除非 Existing Architecture 明確如此設計。
- 在多個 Service 重複相同 Business Rule。

建議：

```text
Controller
    ↓
Service
    ↓
Repository
```

而不是：

```text
Controller
    ↓
Repository
```

### Repository

Repository 負責 Data Access。

主要責任：

- Database Query。
- Insert。
- Update。
- Delete。
- ORM Query。
- Query Result Mapping。
- Database-specific Operation。

Repository 不應負責：

- HTTP Status。
- HTTP Response。
- Business Workflow。
- 與 Database 無關的 Business Rule。

例如：

```python
class UserRepository:

    def get_by_email(self, email):
        ...

    def create(self, user):
        ...
```

如果 Existing Repository 已經存在：

```text
get_by_email()
```

不得新增：

```text
find_user_by_email()
```

來完成完全相同的行為。

應優先 Reuse Existing Repository Method。

### Object / DTO / Schema

資料物件應依照 Existing Project Convention 使用。

可能包含：

- Request Object
- Response Object
- DTO
- Schema
- Business Object
- Read Object
- ORM Model

資料物件應具有明確責任。

避免一個 Object 同時負責：

```text
HTTP Request
+
Business Logic
+
Database Model
```

除非 Framework 或 Existing Architecture 本身如此設計。

### Utility

Utility 僅用於：

- 通用 Formatter。
- Parser。
- Converter。
- Stateless Helper。
- 可被多個 Feature 重複使用的 Common Function。

Utility 不應包含：

```text
Feature-specific Business Logic
```

例如：

不建議：

```python
utils/user_util.py

def create_user():
    ...
```

應優先：

```text
UserService.create_user()
```

### Dependency Direction

建議 Dependency Direction：

```text
Controller
    ↓
Service
    ↓
Repository
    ↓
Database
```

Object / DTO 可以依 Existing Architecture 被各 Layer 使用。

應避免：

```text
Repository
    ↓
Controller
```

或：

```text
Repository
    ↓
HTTP Response
```

### Reuse Rules

實作新功能或 Requirement Change 前，必須先搜尋：

- Existing Module
- Existing Class
- Existing Function
- Existing Repository Query
- Existing Validation
- Existing Error
- Existing Utility
- Existing Configuration

如果 Existing Component 已經能完成 Requirement：

```text
Reuse Existing Component
```

不得重新建立相同功能。

例如 Existing Project 已存在：

```python
UserRepository.get_by_email()
```

不得新增：

```python
UserRepository.find_email()
```

除非兩者 Behavior 明確不同。

Implementation Plan 應清楚標示：

```text
Reuse:
UserRepository.get_by_email()
```

### Validation

Validation 分為不同責任。

#### Request Validation

例如：

- Required Field。
- Data Type。
- String Length。
- Format。
- Enum Value。

通常位於：

```text
Controller / Schema / DTO
```

依 Framework Convention 決定。

#### Business Validation

例如：

```text
Email 是否已被使用
User 是否有權執行此操作
Order 是否可以取消
```

應位於：

```text
Service
或
Domain Layer
```

不得只因為方便，把所有 Validation 都集中在 Controller。

### Error Handling

應優先使用 Existing Project 的 Error Handling Pattern。

例如：

```text
Repository Error
      ↓
Service / Domain Error
      ↓
Controller Error Mapping
      ↓
HTTP Response
```

Business Error 應使用明確 Exception。

例如：

```python
class DuplicateUserError(Exception):
    pass
```

避免：

```python
raise Exception("user error")
```

如果 Existing Project 已經有：

```text
BaseApplicationError
BusinessError
NotFoundError
ValidationError
```

應優先使用 Existing Error Hierarchy。

### Logging

Logging 應使用 Existing Project Logging Framework。

禁止使用：

```python
print()
```

處理正式系統 Logging。

Logging 應包含必要 Context。

例如：

```text
user_id
request_id
job_id
task_id
operation
```

避免記錄：

- Password
- Access Token
- Secret
- Personal Sensitive Data
- 完整 Credential

Error Logging 應保留足夠資訊協助 Debug，但不得洩漏 Sensitive Data。

### Database

Database 操作應透過 Existing Data Access Pattern。

例如：

```text
Repository
ORM
DAO
Query Service
```

依 Existing Architecture 決定。

不得因 Requirement 很小就直接在 Controller 執行 SQL。

### Transaction

需要多筆 Database Operation 保持一致性時，必須考慮 Transaction。

例如：

```text
Create Order
    ↓
Create Order Items
    ↓
Update Inventory
```

如果其中任何一個步驟失敗：

```text
Rollback
```

Transaction Boundary 應依 Existing Project Convention 設計。

通常優先位於：

```text
Service Layer
```

但如果 Existing Framework / Architecture 已經有明確 Transaction Pattern，應沿用 Existing Pattern。

### Query Rules

Query 設計時應考慮：

- Existing Index。
- Query Count。
- N+1 Query。
- Pagination。
- Large Dataset。
- Batch Query。
- Transaction。
- Lock。

不要為了理論上的 Performance 提前進行無需求依據的 Optimization。

只有 Requirement 或 Existing Performance Problem 需要時，才進行額外 Optimization。

### Configuration

Configuration 應優先使用 Existing Project Configuration Pattern。

例如：

```text
Environment Variable
Config File
Settings Module
Secret Manager
```

禁止：

```python
DATABASE_PASSWORD = "password123"
```

Sensitive Configuration 不得 Hard Code。

新增 Environment Variable 時：

Implementation Plan 應說明：

```text
Configuration:
NEW_VARIABLE_NAME

Purpose:
...

Default:
...

Required:
Yes / No
```

### Dependency Management

新增 Dependency 前應確認：

1. Existing Dependency 是否已能完成 Requirement。
2. Dependency 是否與目前 Python Version 相容。
3. Dependency 是否與 Framework Version 相容。
4. 是否真的需要 External Dependency。
5. 是否會增加 Maintenance Cost。

禁止因為一個簡單功能就加入大型 Dependency。

例如單純：

```text
Parse Date
```

如果 Python Standard Library 已可完成，就不需要新增額外 Package。

## Framework Rules

### Flask

優先遵循 Existing Flask Project Structure。

常見 Responsibility：

```text
Blueprint / Route
    ↓
Service
    ↓
Repository
```

Route 不應承擔大型 Business Logic。

### FastAPI

優先使用 Existing：

- Router
- Pydantic Model
- Dependency Injection
- Service
- Repository

Request / Response Schema 應優先使用 Existing Pydantic Convention。

避免將 Business Logic 全部寫在：

```python
@router.post(...)
```

function 中。

### Django

優先遵循 Existing Django Application Structure。

可能包含：

- View
- ViewSet
- Serializer
- Model
- Manager
- Service
- Repository

如果 Existing Django Project 沒有 Repository Pattern：

不得因為本 Skill 而強制加入 Repository Layer。

應遵循 Existing Django Architecture。

## Unit Test

使用 Existing Project Testing Framework。

如果 Project 沒有其他定義，預設使用：

```text
pytest
```

測試檔案應與 Source Code 有清楚對應關係。

例如：

```text
src/
└── services/
    └── user_service.py

tests/
└── services/
    └── test_user_service.py
```

Test File：

```text
test_<module>.py
```

Test Function：

```text
test_<behavior>()
```

例如：

```python
def test_create_user_success():
    ...


def test_create_user_duplicate_email():
    ...
```

### Test Coverage

每一項主要 Behavior 應考慮：

```text
Normal Case
Boundary Case
Error Case
```

例如：

```text
create_user()

Normal:
合法資料成功建立

Boundary:
最大字串長度

Error:
Duplicate Email
Invalid Email
Database Error
```

### Unit Test Isolation

Unit Test 應盡可能獨立。

不得：

```text
Test A
    ↓
建立資料

Test B
    ↓
依賴 Test A 的資料
```

Test 不應依賴執行順序。

### Mock Rules

Mock 應使用於 External Boundary。

例如：

```text
Database
External API
File Storage
Message Queue
Email Service
```

不應為了讓測試通過而過度 Mock 被測試本身的 Business Logic。

### Regression Test

Requirement Change 或 Bug Fix 時：

除了新增 Test，還必須確認 Existing Test。

例如：

```text
New Requirement:
增加 XLSX Export

Regression:
CSV Export Test 必須繼續通過
```

Implementation Plan 應標示：

```text
Testing:

Add:
- test_export_xlsx()

Regression:
- test_export_csv()
```
