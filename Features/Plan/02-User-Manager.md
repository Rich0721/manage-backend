# User Manager Implementation Plan

## I. Plan Status

```text
Plan Status: Awaiting Review
Plan Date: 2026-09-21
Plan Revision Date: 2026-09-21
Implementation Gate: READY FOR REVIEW
```

本計畫已依 2026-09-21 更新後的 Requirement 重新分析。User Manager 將直接實作
`01-Authorization` 先前 deferred 的 JWT、Redis session 與 authentication integration，
不新增或修改 PM Requirement。API、Session、JWT、DEBUG、dependency 與 error mapping
均已完成技術定案，Plan 進入人工審核；審核完成前不得開始 Implementation。

## II. Requirement Information

- Feature Name: User Manager
- Requirement Document: `Features/Document/02-User-Manager.md`
- Related Requirement: `Features/Document/01-Authorization.md`
- Requirement Type: New Requirement
- Plan Revision Type: Requirement Change
- Requirement Date: 未提供
- Plan Date: 2026-09-21
- Related Scenarios:
  - `Features/Document/Scenarios/02-User-Manager/02-User-Manager_Register.feature`
  - `Features/Document/Scenarios/02-User-Manager/02-User-Manager_Login.feature`
  - `Features/Document/Scenarios/02-User-Manager/02-User-Manager_Logout.feature`
  - `Features/Document/Scenarios/02-User-Manager/02-User-Manager_GetUsers.feature`
  - `Features/Document/Scenarios/02-User-Manager/02-User-Manager_Permission.feature`
- Related Flows:
  - `Features/Document/flows/02-User-Manager/02-User-Manager_Register.mmd`
  - `Features/Document/flows/02-User-Manager/02-User-Manager_Login.mmd`
  - `Features/Document/flows/02-User-Manager/02-User-Manager_Logout.mmd`
  - `Features/Document/flows/02-User-Manager/02-User-Manager_GetUsers.mmd`
  - `Features/Document/flows/02-User-Manager/02-User-Manager_Permission.mmd`

`Features/Document/02-User-Manager.md` 已明確引用現有的
`Features/Document/01-Authorization.md`，不再存在 related document path 衝突。

### Requirement Change Delta

| Area | Original Requirement | Updated Requirement | Impact |
|---|---|---|---|
| Related document | `01-Header.md` | `01-Authorization.md` | MODIFY；引用已可追溯 |
| Authorization boundary | 未明確區分 Header/body | Response 同步；validation 以 `body.auth` 為準 | MODIFY；controller/security |
| Email | 未定義 canonicalization | 儲存、查詢及 Uid hash 前 lowercase | MODIFY；schema/service/repository tests |
| Password | 後端 SHA-256 行為不明 | 前端完成加密，後端接收加密值 | MODIFY；移除後端 password hash |
| Login request | `forceLogin` | `isForceLogin` | MODIFY；public JSON contract |
| Existing login response | Success | Failed + 指定 message | MODIFY；login branch/error mapping |
| Login response info | `userName`、`isForceLogin` | 僅 `userName` | REMOVE；response schema |
| Session expiration | 600 seconds | `REDIS_TTL`，default 300 seconds | MODIFY；settings/Redis/JWT/tests |
| JWT settings | 未定義 | `SECRET_KEY`、DEBUG/PRODUCTION policy | ADD；settings/security |
| DEBUG authentication | 未定義 | Token absent 時略過 authentication | ADD；authorization service |
| Permission item | `target_role` | `Permission` | MODIFY；public JSON contract |
| Batch update | 未定義 | 全部成功才 commit，否則不更新 | ADD；transaction/rollback |
| Register error | 未定義 HTTP code | Success 200、business validation 400 | ADD；controller mapping |
| Table | `TB_USERS`、未定義長度 | `tb_users`、password 64，其餘 VARCHAR 256 | MODIFY；DDL/PO/validation |

## III. Requirement Summary

建立 User Manager API，包含：

1. `POST /userController/register`：驗證註冊資料、建立 SHA-256 Uid，保存前端加密後的
   password，並新增預設為 `user` 的使用者。
2. `POST /userController/login`：驗證帳密、處理既有登入與強制登入、建立 Bearer
   Token，並以 Redis session 保存至當下時間加 300 秒。
3. `POST /userController/logout`：驗證 request 中的 Uid 與 Authorization，刪除
   Redis session。
4. `POST /userController/getUsers`：依操作者權限回傳可存取的使用者資料。
5. `PUT /userController/updatePermission`：依權限矩陣批次修改目標使用者角色，
   禁止由 UI/API 修改 admin。
6. 除 register、login 外，受保護操作必須驗證 Redis session；驗證成功後依需求
   更新有效期限。

## IV. Requirement Validation

### 4.1 Confirmed Functional Rules

- Register、login 不需既有 Authorization。
- Email 必須通過格式驗證、轉為 lowercase，且註冊 Email 唯一。
- Uid 使用 lowercase Email 經 SHA-256 產生。
- Password 有大小寫差異；Password 與 confirmPassword 必須相符。
- Password/confirmPassword 由前端完成加密，後端接收加密後字串，不再執行另一層
  password hash；資料庫不保存 confirmPassword。
- 新註冊使用者的 permission 預設為 `user`。
- Login request 對外欄位為 `isForceLogin`；login response info 只包含 `userName`。
- User Manager 定義 login/force login 的 Redis expiration 為當下時間加 300 秒。
- Redis session key 使用 `<uid>:login`，value 使用 Bearer Token。
- Logout 只有在 Redis 中的 token 與 request Authorization 相符時才刪除 session。
- Admin 查詢結果排除所有 admin（包含自己）；可查看 manager 與 user。
- Manager 只可查看 user；user 無查詢權限。
- Admin 可在 user、manager 之間調整角色，但不可修改 admin。
- Manager 只可將 user 調整為 user 或 manager，不可修改 manager 或 admin。
- User 不可修改任何角色。
- Permission update item 對外欄位為 `Permission`。
- Batch permission update 必須全部驗證及更新成功才 commit；任一失敗時整批不更新。
- PostgreSQL table 使用 `tb_users`；password 為 VARCHAR(64)，uid/email/user_name/
  permission 為 VARCHAR(256)，user_name 必須支援中文。

### 4.2 Resolved System Design Decisions

使用者已授權 System Design Agent 決定由 02 直接實作 01，以下決策不新增 Business
Rule，只補足實作所需的 security、configuration 與 HTTP boundary：

1. **Authorization boundary**
   - 任何 response 的 `body.auth.authorization` 有值時，HTTP response
     `Authorization` header 同步相同 Bearer Token。
   - Protected request 僅以 JSON `body.auth.uid` 與 `body.auth.authorization` 驗證，
     不讀取 request HTTP Authorization header。
   - Register、logout、login failure 不回傳 Authorization header。
2. **Existing session response**
   - `isForceLogin=false` 且 key 已存在時回傳 Failed/documented message。
   - `uid`、`authorization` 與 response info 均為 `null`/empty default；不洩漏既有
     token、不建立新 token、不修改 Redis。
3. **JWT**
   - 使用 HS256，固定允許演算法清單 `['HS256']`，不信任 token header 指定演算法。
   - Required claims：`sub`（Uid）、`iat`、`exp`。
   - `exp = iat + REDIS_TTL`；JWT 與 Redis expiration 使用同一秒數。
   - Response/Redis value 格式皆為 `Bearer <JWT>`；decode 前嚴格驗證 Bearer prefix。
4. **Settings**
   - `REDIS_TTL = int(os.getenv("REDIS_TTL", "300"))`，必須大於 0。
   - `DEBUG = os.getenv("DEBUG", "false")`，只接受明確 true/false 值。
   - DEBUG 可使用 requirement 提供的固定 SECRET_KEY default；PRODUCTION 的
     `SECRET_KEY` 必須由 environment 提供，missing/blank 時 application startup fail。
   - `DATABASE_URL` 必須由 environment 提供，missing/blank 時 startup fail。
5. **DEBUG authentication**
   - Authorization token 缺少且 DEBUG=true 時，只略過 JWT/Redis authentication。
   - Protected use case 仍必須提供 `body.auth.uid`、從 `tb_users` 載入 operator，並
     執行 role/permission authorization；DEBUG 不可繞過 admin/manager/user 規則。
   - DEBUG token-absent path 不讀寫或 refresh Redis session；logout 以 Uid 刪除可能
     存在的 `<uid>:login` key。
   - Token 一旦存在，即使 DEBUG=true 也走完整 JWT/Redis validation。
6. **Password input**
   - Password/confirmPassword 必須符合 64-character hexadecimal regex
     `^[0-9A-Fa-f]{64}$`，比較時 case-sensitive，後端不再次 hash。
7. **Trusted identity and timestamps**
   - `userName` 不參與授權；response 使用 Uid 查得的資料庫 user_name。
   - DDL 使用 requirement 指定的 timestamp without time zone；application 以 UTC
     產生 created_at/updated_at。
   - Register required fields 與 permission 均設為 NOT NULL。

### 4.3 HTTP and Error Mapping

| Scenario | HTTP Status | `body.auth.status` | Message |
|---|---:|---|---|
| Register success | 200 | Success | 註冊成功 |
| Duplicate Email | 400 | Failed | 帳號已存在 |
| Password mismatch | 400 | Failed | 密碼不一致 |
| Schema/type/format validation | 422 | Failed | Validation error；field detail 由 FastAPI/Pydantic 提供 |
| Login success / force login success | 200 | Success | Requirement-defined login success message |
| Existing session, no force | 409 | Failed | User login failed because already logged in on another device |
| Unknown Email / wrong password | 401 | Failed | User login failed |
| Missing/invalid/expired Authorization | 401 | Unauthorized | 非法使用者 |
| Redis session missing/mismatch | 401 | ForceLogout | Authorization資訊不一致，操作被拒絕 |
| Role transition/list permission denied | 403 | Unauthorized | User Permission Denied |
| Permission target not found | 404 | Failed | User not found |
| Duplicate target in one batch | 400 | Failed | Duplicate permission target |
| Logout success | 200 | Success | 登出成功 |
| Database/Redis unavailable | 503 | Failed | Service unavailable |
| Unexpected server error | 500 | Failed | Internal server error |

對外 error response 不包含 SQL、driver exception、token、secret、credential 或 stack trace。

## V. Requirement Scope

### In Scope

- 五個 User Manager endpoint 及 typed request/response schema。
- `tb_users` DDL、PO 與 data access。
- PostgreSQL connection/settings/lifecycle。
- Lowercase Email Uid hash、前端加密 password 比對與 JWT/Bearer Token utility。
- Redis session CRUD、TTL 及授權驗證。
- Register、login、logout、user list、permission update business rules。
- FastAPI application bootstrap、router registration、dependency wiring。
- Unit tests；Database/Redis boundary 使用 mock，並規劃必要的 integration tests。

### Out of Scope

- 前端頁面與 UI 行為。
- Admin 建立或後台維運工具。
- Password reset、Email verification、account lock、refresh token。
- 使用者資料新增欄位、刪除使用者或修改個人資料。
- 與本需求無關的 Authorization framework 重構。
- 未由需求定義的 pagination、sorting、search 或 audit history。

## VI. Existing System Analysis

### 6.1 Technology Context

| Item | Current Decision |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI 0.141.1 |
| Validation | FastAPI bundled Pydantic |
| Database | PostgreSQL 17；尚無 client/connection implementation |
| Redis | Redis 8.1.0 / redis-py 8.1.0 async client |
| Test | pytest、pytest-asyncio |

### 6.2 Existing Reusable Components

- `src/models/schemas/authorization.py`
  - `AuthorizationObject`
  - `AuthorizationBody`
  - `AuthorizationEnvelope`
- `src/config/settings.py`
  - `Settings.REDIS_URL`
- `src/config/redis.py`
  - `RedisConnectionManager`
  - `connect()` / `get_client()` / `close()`
- `Features/Plan/01-Authorization.md`
  - 已完成 base object/Redis connection。
  - JWT、Redis token CRUD/TTL 與 feature integration 原列為 deferred scope；本 Plan
    是其正式 follow-up implementation plan。
- 既有 tests 已驗證 Authorization 基礎結構、Redis 設定與 client lifecycle。

### 6.3 Missing Components

- `src/main.py`、Controller、Service、Repository。
- User endpoint typed schemas、business object 與 persistence object。
- PostgreSQL settings、connection lifecycle、transaction pattern。
- User table DDL。
- JWT、Uid hashing、encrypted password compare 與 Redis session operations。
- Application error hierarchy、HTTP error mapping 與 logging configuration。

既有 architecture 可支援需求，不需建立新 layer：

```text
Client
  ↓
UserController / Pydantic Schema
  ↓
UserService + AuthorizationService
  ↓
UserRepository + SessionRepository
  ↓
PostgreSQL + Redis
```

## VII. System Design

本節是 Programmer 必須遵循的已定案設計邊界；不得自行更換 token contract、dependency、
HTTP mapping 或 architecture placement。

### 7.1 Module Responsibility

| Path | Responsibility |
|---|---|
| `src/models/schemas/user.py` | 五個 endpoint 的 typed `info` 與 envelope schema |
| `src/models/po/user.py` | `tb_users` row mapping，不包含 business workflow |
| `src/constants/user.py` | Role、session TTL 與已確認的 response constants |
| `src/config/database.py` | PostgreSQL client/pool lifecycle |
| `src/utils/security.py` | Stateless Uid hash、encrypted password compare 與 JWT encode/decode |
| `src/repositories/user_repository.py` | User select/insert/permission update query |
| `src/repositories/session_repository.py` | `<uid>` session key的 get/set/delete/expire |
| `src/services/errors.py` | Application/domain error types for centralized HTTP mapping |
| `src/services/authorization_service.py` | Token/session 驗證與成功操作 TTL refresh |
| `src/services/user_service.py` | 五個 use case 與 permission business rules |
| `src/controllers/user_controller.py` | FastAPI routes、schema binding、service result mapping |
| `src/controllers/dependencies.py` | 由 application state 取得共用連線並組合 service |
| `src/main.py` | FastAPI app、lifespan、router registration |

### 7.2 Request and Response Boundary

- 保留既有 JSON envelope：`header`、`body.auth`、`body.info`。
- Reuse `AuthorizationObject`，不在 user schema 重複定義 auth fields。
- 每個 endpoint 的 `info` 使用獨立 Pydantic model，禁止直接以
  `dict[str, Any]` 接受業務資料。
- Request JSON 使用 requirement 已確認的 `isForceLogin` 與 `Permission`；內部 Python
  attribute 使用 `is_force_login` 與 `permission`，透過 Pydantic serialization alias
  維持對外 contract。
- Email format 與 role enum 在 schema boundary 驗證；duplicate email、credential、
  permission matrix 等 business validation 位於 Service。
- Controller 不直接執行 SQL、Redis command、hash 或 permission 判斷。
- Response 不得回傳 password/hash；login error 不得透露 Email 是否存在。

### 7.3 Database Design

建立 requirement 指定的單一 `tb_users` table：

| Column | Requirement | Constraint to Implement |
|---|---|---|
| `uid` | `VARCHAR(256)` | Lowercase Email 的 SHA-256 hex、primary key、not null |
| `email` | `VARCHAR(256)` | Lowercase Email、unique、not null |
| `user_name` | `VARCHAR(256)` | Unicode display name、not null |
| `password` | `VARCHAR(64)` | 64-character hex、case-sensitive、not null |
| `permission` | `VARCHAR(256)` | Not null、default user、CHECK admin/manager/user |
| `created_at` | `TIMESTAMP` | Application assigns UTC insert time |
| `updated_at` | `TIMESTAMP` | Application assigns UTC insert/update time |

- Email lookup 與 permission update 透過 `UserRepository`。
- User list 使用單次 filtered query，避免先取全部資料再於 Service 過濾。
- Batch permission update 使用單一 database transaction；所有 targets 驗證通過後才
  執行 update，任一 validation/database failure 都 rollback，禁止 partial update。
- Repository 將 driver/database errors 向上轉換為明確 infrastructure errors，不建立
  HTTP response。

### 7.4 Session and Authorization Flow

```text
Request body.auth(uid, authorization)
    ↓
AuthorizationService.validate_session()
    ├── validate required auth fields / Bearer token
    ├── DEBUG + token absent: require Uid, skip JWT/Redis authentication
    ├── otherwise validate HS256 JWT sub/iat/exp
    ├── SessionRepository.get("<uid>:login")
    └── constant-time compare stored Bearer Token and request token
            ↓
        UserService operation
            ↓
    reset Redis expiration to now + REDIS_TTL
            ↓
        typed response envelope
```

- Login 成功時使用 Redis atomic set-with-expiry，TTL 取自 `Settings.REDIS_TTL`，避免先
  set 再 expire 造成無 expiry key。
- Force login 依 requirement 執行 DELETE 後重新產生資訊；使用 Redis transaction
  pipeline 將 DELETE 與 SET-with-expiry 作為單一原子操作，避免中間狀態。
- Logout 驗證成功後刪除 key，且不執行 TTL refresh。
- Token、password、Redis URL credential 不得寫入 log 或 error response。
- Redis unavailable 不得被誤報為 invalid credential；依第 4.3 節回傳 HTTP 503。

### 7.5 Business Workflows

#### Register

```text
Validate schema/email/password confirmation
    ↓
Lowercase Email
    ↓
UserRepository.get_by_email()
    ↓
SHA-256 Uid + retain validated frontend-encrypted password
    ↓
UserRepository.create(permission="user")
    ↓
Register response (uid/email/userName)
```

Database unique constraint 是 duplicate email race condition 的最終保護；Service 的
pre-check 用於回傳 business error。

#### Login

```text
Validate schema/email
    ↓
UserRepository.get_by_email()
    ↓
Constant-time compare received encrypted password
    ↓
SessionRepository.get()
    ├── absent: issue HS256 token and set REDIS_TTL
    ├── present + isForceLogin=false: return Failed without Redis mutation
    └── present + isForceLogin=true: transaction DELETE + SET new token/REDIS_TTL
```

#### Logout

```text
Validate auth/token/session
    ↓
SessionRepository.delete()
    ↓
Return stored database userName
```

#### Get Users

```text
Validate auth/token/session
    ↓
UserRepository.get_by_uid() for operator role
    ├── admin: query permission IN (manager, user)
    ├── manager: query permission = user
    └── user: permission denied
    ↓
Reset session TTL to Settings.REDIS_TTL
    ↓
Return email/userName/permission list
```

若合法 admin/manager 查無可見資料，回傳成功與空列表；user 則依需求回傳
`Unauthorized`，不可將兩者混為相同結果。

#### Update Permission

```text
Validate auth/token/session + target role enum
    ↓
Load operator and all target users in batch
    ↓
Validate every operator/current-role/target-role tuple
    ↓
Apply all updates in one transaction; any failure rolls back all rows
    ↓
Reset session TTL to Settings.REDIS_TTL
    ↓
Return typed response
```

所有 permission 判斷使用資料庫中目前角色，不信任 request 所提供的角色。任何 admin
target 一律拒絕。

### 7.6 Error Handling

需建立最小且明確的 application error hierarchy，供 Controller 統一 mapping：

- Request/schema validation error。
- Duplicate email / password confirmation mismatch。
- Invalid credentials（未註冊 Email 與錯誤 password 使用相同對外結果）。
- Invalid/missing Authorization。
- Session mismatch / force logout。
- Permission denied。
- Target user not found / invalid role。
- Database unavailable / Redis unavailable / unexpected infrastructure failure。

Controller 依第 4.3 節統一 mapping；Repository 不建立 HTTP response，Service 只拋出
明確 application/domain error。Programmer 不得在各 endpoint 內建立不同 error shape。

### 7.7 Logging

- 使用 Python `logging`，不使用 `print()`。
- 可記錄 operation、Uid、operator role、target count 與 exception type。
- 不記錄 password、前端加密後 password、JWT/Bearer Token、Redis URL credential。
- Email 屬個資，預設不完整記錄；若需追蹤，使用 Uid 或遮罩值。

### 7.8 Dependencies and Configuration

`requirements.txt` 新增下列 pinned dependencies：

- `psycopg[binary]==3.3.6`：PostgreSQL 17 async driver。
- `psycopg-pool==3.3.2`：`AsyncConnectionPool`。
- `PyJWT==2.14.0`：HS256 JWT encode/decode。
- `email-validator==2.3.0`：Email syntax validation；不執行 DNS deliverability check。

官方資料確認 Psycopg 3.3.6/Pool 3.3.2 與 PyJWT 支援 Python 3.14；上述套件不建立
新 architecture layer，只補足現有 dependency 無法完成的 PostgreSQL/JWT/Email 能力。

新增或擴充的 environment variables：

| Variable | Purpose | Default / Validation |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection URL | Required、non-empty、無 default |
| `REDIS_TTL` | Redis/JWT expiration seconds | `300`、integer > 0 |
| `SECRET_KEY` | HS256 signing/verifying | DEBUG 可用 requirement default；PRODUCTION required |
| `DEBUG` | Authentication debug policy | `false`、strict boolean parsing |

`JWT_ALGORITHM = "HS256"` 為 code constant，不允許透過 environment 或 token header
動態改變。

### 7.9 External Compatibility Verification

| Technology | Version | Verification | Design Use |
|---|---:|---|---|
| [Psycopg](https://pypi.org/project/psycopg/) | 3.3.6 | Python 3.10-3.15、PostgreSQL 10-18 | Async PostgreSQL driver |
| [psycopg-pool](https://pypi.org/project/psycopg-pool/) | 3.3.2 | Python 3.14 classifier | AsyncConnectionPool |
| [PyJWT](https://pyjwt.readthedocs.io/en/stable/) | 2.14.0 | Python 3.14 classifier | HS256 encode/decode |
| [email-validator](https://pypi.org/project/email-validator/) | 2.3.0 | Universal Python 3 wheel、Python >=3.8 | Syntax-only Email validation |

Psycopg official guidance requires explicit async pool open (`open=False` + `await pool.open()`)
to avoid constructor auto-open warnings/future incompatibility。Programmer 仍需在 project venv
執行 dependency install 與完整 test suite，確認實際 Windows/Docker build artifacts。

## VIII. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implentation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| TASK-001 | User API Schemas and Constants | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-002 | PostgreSQL Settings and Lifecycle | ADD/MODIFY | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-003 | Users Table and Repository | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-004 | Security and Session Authorization | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-005 | User Registration | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-006 | User Login | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-007 | User Logout | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-008 | User Data Query | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-009 | Permission Management | ADD | 2026-09-21 | PLAN UPDATED |  |  |
| TASK-010 | FastAPI Routes and Application Wiring | ADD | 2026-09-21 | PLAN UPDATED |  |  |

所有 Task 已依最新 Requirement 調整為 `PLAN UPDATED`，Plan 目前為
`READY FOR REVIEW`；人工審核完成前仍不得開始開發。

## IX. Implementation Steps

### TASK-001 User API Schemas and Constants

```text
File:
- src/models/schemas/user.py
- src/constants/user.py
- tests/models/schemas/test_user.py

Target:
- RegisterRequestInfo / RegisterResponseInfo
- LoginRequestInfo / LoginResponseInfo
- LogoutRequestInfo / LogoutResponseInfo
- GetUsersRequestInfo / UserSummary / GetUsersResponseInfo
- PermissionUpdateItem / UpdatePermissionRequestInfo
- ValidationErrorItem / ErrorResponseInfo
- Endpoint-specific request/response envelope models
- UserRole and response/session constants

Plan Type: ADD
Reuse: src.models.schemas.authorization.AuthorizationObject
Impact: Defines the public JSON contract for all User Manager endpoints

Current Behavior:
Only a dynamic AuthorizationEnvelope with dict info exists; no endpoint validation exists.

Expected Behavior:
Each endpoint accepts and emits the required header/body.auth/body.info shape with typed info,
Email/boolean/role/password validation, and the exact external field names.

Implementation:
- Reuse AuthorizationObject instead of duplicating auth fields.
- Define distinct request and response info models.
- Use exact aliases `userName`、`confirmPassword`、`isForceLogin` and `Permission`; Python
  attributes remain snake_case.
- Normalize Email with lowercase before length and format validation; enforce the requirement
  VARCHAR(256) boundaries for Email and userName.
- Validate encrypted password with `^[0-9A-Fa-f]{64}$` and exact length 64.
- Forbid unknown fields on endpoint business info.
- Do not place duplicate-email, credential or permission business checks in schemas.

Error Handling:
Invalid type/Email/role/password/missing required field maps to the HTTP 422 response defined in
section 4.3.

Testing:
- Valid and invalid request/response serialization for every endpoint.
- Exact alias round trip and required/optional field behavior.
- Invalid Email, boolean, role and list element rejection.
- Independent mutable list/dict defaults.
- Regression: existing Authorization schema tests remain passing.
```

### TASK-002 PostgreSQL Settings and Lifecycle

```text
File:
- requirements.txt
- src/config/settings.py
- src/config/database.py
- tests/config/test_settings.py
- tests/config/test_database.py

Target:
- Settings.DATABASE_URL / REDIS_TTL / SECRET_KEY / DEBUG
- DatabaseConnectionManager
- connect() / get_pool() / close()

Plan Type: ADD/MODIFY
Reuse: Existing Settings validation pattern and async context-management pattern from
       RedisConnectionManager
Impact: Adds application database configuration and reusable connection/pool lifecycle

Current Behavior:
Settings only exposes REDIS_URL; no PostgreSQL client or lifecycle exists.

Expected Behavior:
Configuration is read from environment, credentials are never logged, connection/pool startup
is validated once, callers acquire/release connections safely, and shutdown closes resources.

Implementation:
- Add only the four pinned dependencies listed in section 7.8.
- Read configuration with os.getenv according to project instructions.
- Create async PostgreSQL connection/pool lifecycle; do not open a connection for each repository
  operation without pooling.
- Construct `AsyncConnectionPool(DATABASE_URL, open=False)`，`connect()` explicitly awaits
  `pool.open()` and `pool.wait()` before serving traffic.
- Expose transaction-capable connection acquisition to repositories/services.
- `get_pool()` before successful connect raises a clear RuntimeError；`close()` awaits pool close,
  clears state and is idempotent.
- Integrate close behavior with TASK-010 lifespan.

Error Handling:
- Empty required settings fail before application serves traffic.
- Startup failure cleans partial resources and propagates an infrastructure error.
- Never include DATABASE_URL/JWT secret values in errors or logs.

Testing:
- DATABASE_URL required behavior, REDIS_TTL default/positive integer validation, DEBUG strict
  boolean parsing and DEBUG/PRODUCTION SECRET_KEY policy.
- Connection/pool startup, acquisition, transaction, cleanup and idempotent close with mocks.
- `open=False` construction、explicit open/wait、get-before-connect and repeated-connect behavior.
- Startup and close failure behavior.
- Regression: existing Redis settings/connection tests remain passing.
```

### TASK-003 Users Table and Repository

```text
File:
- database/DDL/tables/TB_USERS.sql
- src/models/po/user.py
- src/repositories/user_repository.py
- tests/models/po/test_user.py
- tests/repositories/test_user_repository.py

Target:
- UserPO
- UserRepository.get_by_uid()
- UserRepository.get_by_email()
- UserRepository.create()
- UserRepository.list_visible_users()
- UserRepository.get_by_emails()
- UserRepository.update_permissions()

Plan Type: ADD
Reuse: DatabaseConnectionManager from TASK-002
Impact: Adds tb_users persistence and all database access needed by this feature

Current Behavior:
No DDL, user model, database repository or query exists.

Expected Behavior:
The table enforces primary key, unique Email and valid permission; repository provides bounded,
parameterized queries without HTTP or business logic.

Implementation:
- Create table/column comments per SQL Standard.
- Rely on primary-key and unique-constraint indexes; do not add a low-selectivity permission index
  without a measured performance requirement.
- Define `tb_users` with VARCHAR(256), required NOT NULL fields, Email unique constraint,
  permission default/check constraint and application-managed TIMESTAMP fields.
- Use parameterized SQL/selected data-access API; never interpolate request values.
- Map rows to UserPO without exposing password in list responses.
- Make list_visible_users perform role-derived filtering supplied by Service in one query.
- Fetch batch targets in one query and update within caller transaction.
- Handle duplicate Email race through the database unique constraint.

Error Handling:
- Distinguish not-found, unique violation and infrastructure errors for Service mapping.
- Roll back the whole transaction on any validation/update failure; never persist a partial batch.

Testing:
- Query parameters and row mapping for every method.
- Unique violation and database error propagation/mapping.
- Admin-visible and manager-visible filters do not return forbidden roles.
- Batch target fetch/update and rollback behavior.
- Integration: DDL applies to PostgreSQL 17 and constraints reject invalid rows.
```

### TASK-004 Security and Session Authorization

```text
File:
- src/utils/security.py
- src/repositories/session_repository.py
- src/services/authorization_service.py
- tests/utils/test_security.py
- tests/repositories/test_session_repository.py
- tests/services/test_authorization_service.py

Target:
- hash_uid()
- verify_encrypted_password()
- issue_access_token() / decode_access_token()
- SessionRepository.get()/set()/delete()/refresh()
- AuthorizationService.validate_session()/refresh_session()

Plan Type: ADD
Reuse:
- RedisConnectionManager client
- AuthorizationObject
- Settings and constants from TASK-001/TASK-002
Impact: Shared security/session behavior for login and all protected endpoints

Current Behavior:
Redis connection exists, but token, key, CRUD, TTL and authorization behavior were explicitly
deferred by the prior Authorization plan.

Expected Behavior:
Uid/token behavior follows section 4.2; Redis operations use `<uid>:login` and atomic expiry;
protected calls reject missing/mismatched/invalid sessions and safely refresh expiration.

Implementation:
- Use hashlib SHA-256 only to derive Uid from lowercase Email. Do not hash the frontend-encrypted
  password again; compare the received encrypted value with the stored value using
  hmac.compare_digest or equivalent constant-time behavior.
- Encode/decode HS256 JWT with required `sub`、`iat`、`exp` claims and the configured SECRET_KEY;
  decode accepts only `algorithms=["HS256"]`.
- Require exact `Bearer <JWT>` format in response body/header, protected body.auth and Redis value.
- Set token with `Settings.REDIS_TTL` atomically; force login uses a Redis transaction pipeline
  containing DELETE followed by SET-with-expiry.
- Validate token and Redis equality before authorized business operations.
- Reset Redis expiration to `Settings.REDIS_TTL` after protected operations; logout does not
  refresh before delete.
- Implement DEBUG token-absent path exactly as section 4.2: Uid and role authorization remain
  mandatory, while JWT/Redis authentication and expiration refresh are skipped.

Error Handling:
- Separate malformed/expired token, missing session, mismatched session and Redis unavailable.
- Never log or return token, encrypted password or key material.

Testing:
- Stable lowercase-Email Uid SHA-256 output and constant-time encrypted-password compare.
- JWT valid, tampered, expired, missing claim, wrong key and wrong algorithm cases.
- Exact `<uid>:login` Redis key generation.
- Atomic set expiration, force replacement, get, delete and refresh behavior.
- Missing/mismatched session and Redis error paths.
- DEBUG token absent + Uid present success path、Uid absent rejection、token present normal
  validation and no Redis refresh in bypass path.
```

### TASK-005 User Registration

```text
File:
- src/services/user_service.py
- tests/services/test_user_service.py

Target: UserService.register()
Plan Type: ADD
Reuse: UserRepository, Uid hash/password compare functions, register schemas/constants
Impact: Implements register business workflow without HTTP/database details in Service

Current Behavior:
No registration workflow exists.

Expected Behavior:
Valid unique Email creates one user with deterministic Uid, frontend-encrypted password, default
user role and timestamps; response contains only uid/email/userName.

Implementation:
- Validate password confirmation as a business rule.
- Lowercase Email before lookup and Uid hashing.
- Verify password/confirmPassword equality without normalizing case, compute Uid hash, and call
  UserRepository.create() with only the encrypted password value.
- Map unique constraint race to the same duplicate Email business error.

Error Handling:
- Invalid Email remains schema error.
- Password mismatch and duplicate Email use confirmed response contract.
- Database failure does not expose SQL/credentials or report false success.

Testing:
- Valid registration and exact repository payload.
- Invalid Email regression through schema.
- Password mismatch, pre-existing Email and unique-race cases.
- Uid hash and one encrypted password value are stored; confirmPassword is not persisted or
  returned, and the backend does not hash the password again.
```

### TASK-006 User Login

```text
File:
- src/services/user_service.py
- tests/services/test_user_service.py

Target: UserService.login()
Plan Type: ADD
Reuse: UserRepository, SessionRepository, security token/password functions
Impact: Implements login, existing-session detection and force login

Current Behavior:
No credential or login session workflow exists.

Expected Behavior:
Valid credentials create a session with `Settings.REDIS_TTL` when absent; an existing
session with `isForceLogin=false` returns the documented Failed response without Redis mutation;
force login atomically replaces the session.

Implementation:
- Load user by lowercase Email and compare encrypted password in constant time.
- Use one external invalid-credential result for unknown Email and wrong password.
- Check canonical session key only after credentials are valid.
- Issue/store a new token only for absent-session and force-login success cases.
- Populate uid/userName and auth fields exactly as section 4.2; response info does not contain
  isForceLogin.
- Existing-session/invalid-credential failures keep uid、authorization and info empty/default and
  do not set the HTTP Authorization header.

Error Handling:
- Invalid credentials do not disclose account existence.
- Redis/token-generation failure does not return login success.

Testing:
- No session: successful token creation, body/header synchronization and REDIS_TTL.
- Existing session + isForceLogin=false: Failed response and no Redis mutation/new token.
- Existing session + isForceLogin=true: transaction DELETE + SET and REDIS_TTL reset.
- Unknown Email and wrong password have equivalent external behavior.
- Database, Redis and token errors.
```

### TASK-007 User Logout

```text
File:
- src/services/user_service.py
- tests/services/test_user_service.py

Target: UserService.logout()
Plan Type: ADD
Reuse: AuthorizationService, SessionRepository, UserRepository
Impact: Implements protected logout and session deletion

Current Behavior:
No logout workflow exists.

Expected Behavior:
Normal mode/token-present request requires a valid matching Uid/token/session；DEBUG token-absent
request requires a valid Uid and database user. Success deletes the key if present and returns the
trusted stored userName from `tb_users`.

Implementation:
- Validate auth through AuthorizationService.
- Load database user for response rather than trusting request userName.
- Normal path deletes the validated session without refreshing TTL；DEBUG token-absent path deletes
  the Uid key without attempting JWT/Redis comparison.
- Missing/expired session is not a successful idempotent logout; map it to ForceLogout/HTTP 401.

Error Handling:
- Missing Uid/token maps to Unauthorized/HTTP 401；missing session or mismatch maps to
  ForceLogout/HTTP 401.
- Redis deletion failure returns failure and must not claim logout success.

Testing:
- Matching session deletes once and returns expected info.
- Missing, mismatched and already-expired session behavior.
- Request userName cannot impersonate or alter response identity.
- Redis failure.
- DEBUG token-absent success with valid Uid and rejection when Uid/user is missing.
```

### TASK-008 User Data Query

```text
File:
- src/services/user_service.py
- tests/services/test_user_service.py

Target: UserService.get_users()
Plan Type: ADD
Reuse: AuthorizationService and UserRepository list query
Impact: Implements permission-filtered user listing

Current Behavior:
No user list or permission filtering exists.

Expected Behavior:
Admin receives manager/user rows and no admin; manager receives only user rows; user is denied;
an authorized empty result returns an empty list.

Implementation:
- Validate session, then derive operator role from database by Uid.
- Reject user role before list query.
- Pass an explicit allowed-role filter to UserRepository.
- Map only email, userName and permission; never password/hash.
- Reset session expiration to `Settings.REDIS_TTL` after the authorized operation.

Error Handling:
- Missing operator record/session is not treated as an empty successful list.
- User permission denied remains distinct from authorized empty results.

Testing:
- Admin, manager and user scenarios from Gherkin.
- Admin excludes all admins including caller.
- Manager excludes manager/admin.
- Authorized empty list, missing operator, session mismatch and repository failure.
- Expiration refresh only on successful authorization path.
```

### TASK-009 Permission Management

```text
File:
- src/services/user_service.py
- tests/services/test_user_service.py

Target: UserService.update_permissions()
Plan Type: ADD
Reuse: AuthorizationService, UserRepository batch methods, UserRole constants
Impact: Implements batch role transition rules and transaction control

Current Behavior:
No permission update workflow exists.

Expected Behavior:
Every requested transition satisfies the documented role matrix; admin targets cannot change;
database writes are all-or-nothing.

Implementation:
- Validate session and load operator role from database.
- Lowercase all target Emails, reject duplicate entries, and fetch all targets in one query.
- Validate every current-role/target-role tuple before writing.
- If any target is unknown or unauthorized, perform no update.
- Perform all parameterized updates in one transaction and roll back the full batch on error.
- Update updated_at and reset caller session expiration after authorized completion.

Error Handling:
- Invalid role is schema error.
- Forbidden transition returns Unauthorized and must not silently skip a target.
- Unknown target, duplicate target and mid-transaction database failure all leave every row
  unchanged; the exact external error mapping remains part of 第 XI 節確認。

Testing:
- Every allowed and denied row in the requirement matrix.
- Admin target always denied.
- Multiple valid targets.
- Mixed valid/invalid targets and database failure roll back every update.
- No writes occur when validation fails before transaction.
```

### TASK-010 FastAPI Routes and Application Wiring

```text
File:
- src/controllers/dependencies.py
- src/controllers/user_controller.py
- src/services/errors.py
- src/main.py
- tests/controllers/test_user_controller.py
- tests/test_main.py

Target:
- POST /userController/register
- POST /userController/login
- POST /userController/logout
- POST /userController/getUsers
- PUT /userController/updatePermission
- FastAPI lifespan and router registration
- Application/domain errors and global exception handlers

Plan Type: ADD
Reuse:
- RedisConnectionManager
- DatabaseConnectionManager
- UserService / AuthorizationService
- typed schemas from TASK-001
Impact: Exposes the complete feature through HTTP and owns resource startup/shutdown

Current Behavior:
No FastAPI application entry point or routes exist.

Expected Behavior:
All five exact paths accept/return the requirement envelope, use shared application resources,
synchronize response Authorization header when a token exists, and map errors per section 4.3
without business logic in Controller.

Implementation:
- Create FastAPI application with lifespan that initializes PostgreSQL and Redis once and closes
  both on shutdown, including partial-startup cleanup.
- Register one router with the exact requirement paths and methods.
- Use FastAPI dependency injection to build/request services from application state.
- Controller binds schema, calls one Service use case and maps result/error only.
- Define explicit application/domain error types in `src/services/errors.py`; map them centrally
  to section 4.3 HTTP status and the standard envelope.
- Override FastAPI `RequestValidationError` handling so HTTP 422 also uses the standard envelope
  and places field details in typed error info.
- Validate protected requests only from body.auth; do not use request HTTP Authorization header.
- When body.auth.authorization contains a token in a response, set the same string in the HTTP
  `Authorization` response header. Do not set it for register/logout/login failure.

Error Handling:
- Add centralized mapping for all section 4.3 HTTP/application errors.
- Infrastructure details are logged safely and returned as non-sensitive errors.

Testing:
- Route existence, method and exact request/response JSON for all success scenarios.
- Schema validation and every section 4.3 application error mapping.
- Authorization header/body equality on token responses and absence on non-token responses.
- Dependency override isolates Controller tests from PostgreSQL/Redis.
- Lifespan startup/shutdown and partial-startup cleanup.
- Regression: all existing tests remain passing.
```

## X. Impact Analysis

| Area | Impact | Details |
|---|---|---|
| API | ADD | Five `/userController/*` endpoints |
| Schema | ADD | Typed endpoint info/envelope models |
| Existing Authorization schema | REUSE | Reuse body.auth models without changing base behavior |
| Controller | ADD | User router and dependency wiring |
| Service | ADD | User and authorization workflows |
| Repository | ADD | PostgreSQL user data and Redis session operations |
| Database | ADD | Users table/constraints and PostgreSQL lifecycle |
| Redis | ADD | Session CRUD/TTL over existing client |
| Configuration | MODIFY | DATABASE_URL、REDIS_TTL、SECRET_KEY、DEBUG |
| Dependencies | MODIFY | Pinned Psycopg/Pool、PyJWT、email-validator |
| Application entry | ADD | FastAPI app/lifespan/router registration |
| Existing tests | NO CHANGE | Must remain passing; only add regression coverage |
| External service | NO CHANGE | PostgreSQL and Redis only |

### Backward Compatibility

- Existing Authorization model serialization and RedisConnectionManager behavior must remain
  compatible with the completed `01-Authorization` plan and tests.
- New endpoint schemas wrap/reuse `AuthorizationObject`; they must not silently change the dynamic
  base object's existing behavior.
- Redis key is now consistently `<uid>:login`; implementation must not create the previously
  documented `<Uid>:Authorization:JWT` namespace.
- API is new, so there is no existing User Manager endpoint compatibility burden；public request
  aliases must use the newly confirmed `isForceLogin` and `Permission` names only.

## XI. Open Questions

本計畫沒有阻擋 Implementation 的 Open Question。

已依使用者授權由 System Design 定案的項目：

- 02 直接實作 01 deferred 的 JWT/Redis/authentication scope，不修改 Requirement 文件。
- Response Header/body token 同步；protected request 只驗證 body.auth。
- REDIS_TTL default 300，JWT exp 與 Redis TTL 同步。
- HS256 + SECRET_KEY + required `sub/iat/exp` claims。
- DEBUG 只略過 token/Redis authentication，不略過 Uid 與 role authorization。
- Failed existing-session login 不回傳 Uid/token、不修改 Redis。
- 64-character hex password validation、case-sensitive compare、no backend re-hash。
- HTTP/application error mapping 使用第 4.3 節。

## XII. Testing Strategy

- Schema：normal、boundary、invalid type/format/enum、serialization alias。
- Service：逐一覆蓋五份 Gherkin 的正常、拒絕與錯誤情境。
- Security：lowercase Email Uid hash、encrypted password compare、JWT tamper/expiry/claim、
  敏感資訊不洩漏。
- Redis：session absent/present/mismatch、atomic set、transaction force replacement、
  REDIS_TTL refresh、delete、failure。
- Repository：parameterized query、role filtering、unique violation、batch transaction rollback。
- Controller：exact path/method/envelope、error mapping、dependency override。
- Lifecycle：PostgreSQL/Redis 正常與部分啟動失敗都會釋放資源。
- Integration：PostgreSQL 17 DDL/constraints 與 Redis 8.1.0 TTL behavior。
- Regression：現有 `tests/models/schemas/test_authorization.py`、
  `tests/config/test_settings.py`、`tests/config/test_redis.py` 全數通過。
- 測試互相獨立，不依賴執行順序；Database/Redis unit tests mock external boundary。

## XIII. Plan Validation

- [x] Requirement Type 已確認為 New Requirement。
- [x] Requirement Change Delta 與 Impact Analysis 已完成。
- [x] 已讀取 Requirement、五份 Scenario 與五份 Flow。
- [x] Existing architecture、source、tests、configuration 與前一份 plan 已分析。
- [x] Existing Authorization schema、Settings 與 Redis manager 已優先 Reuse。
- [x] 每個 Implementation Step 有明確 File、Target、Behavior 與 Testing。
- [x] API、Database、Redis、Configuration、Dependency 與 Backward Compatibility impact 已分析。
- [x] Error Handling、Logging、Validation、Security 與 Testing boundary 已定義。
- [x] 未加入與需求無關的 Refactoring 或 architecture layer。
- [x] 未自行補充缺失的 Business Rule。
- [x] Requirement conflict 已由更新文件或 System Design decision 解決。
- [x] Email lowercase、request fields、batch atomicity、table name/length 已由 PM 確認。
- [x] Authorization 傳輸位置、session expiration 與 JWT contract 已定義。
- [x] HTTP/error response contract 已定義。
- [x] Frontend-encrypted password format 已確認為 64-character hex。
- [x] DEBUG authentication/authorization boundary 已定義。
- [x] Dependency 與 Python 3.14 compatibility 已確認並 pin version。
- [x] Implementation Plan 已完成人工審核。

## XIV. Review Status and Handoff

- [x] Implementation Plan 已完成人工審核
- [ ] Development 完成
- [ ] Code Review 通過

```text
Current Handoff: PM / Reviewer for Implementation Plan review
Next Handoff: Programmer Agent after review approval
Implementation Scope: User Manager register/login/logout/list/permission APIs
Do Not Implement: Any task before Implementation Plan review approval
Do Not Modify: Features/Document requirements, completed Authorization behavior, unrelated code
```
