# 01-User-Manager Implementation Plan

## I. Requirement Information

Feature Name: [01-User-Manager.md](../Document/01-User-Manager.md)

Scenario:

- [01-User-Manager_Register.feature](../Document/Scenarios/01-User-Manager_Register.feature)
- [01-User-Manager_Login.feature](../Document/Scenarios/01-User-Manager_Login.feature)
- [01-User-Manager_Permission.feature](../Document/Scenarios/01-User-Manager_Permission.feature)

```text
Requirement Source: Features/Document/01-User-Manager.md
Requirement Date: 未提供
Plan Date: 2026-09-15
Requirement Type: New Requirement
Requirement Summary: 新增使用者註冊、兩階段登入、登出接口與權限管理。
```

## II. Requirement Summary

1. 註冊驗證 Email 格式、確認密碼與 Email 唯一性，以 Email 的 SHA-256
   雜湊產生 uid，儲存 user_name 與前端 SHA-256 雜湊後的密碼，並建立預設
   `user` 角色帳號。
2. 第一階段登入驗證 Email 與前端 SHA-256 雜湊後的密碼；成功時將隨機
   六位英數 Temporary Code 以 Email 為 Redis key 儲存三分鐘，覆蓋舊碼，
   並透過 SMTP 寄送指定 Email 樣板。
3. 第二階段以 Email 與 Temporary Code 驗證登入。
4. 保留登出接口，不實作未定義的登出行為。
5. `admin` 可列出非 admin 使用者並管理 `user`、`manager`；`manager` 只能
   列出及管理目前為 `user` 的帳號；`user` 不可查詢或修改；任何 admin
   帳號不得經此前端 API 查詢或修改。
6. 所有 PostgreSQL SQL 查詢都必須使用 parameterized query。

## III. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implentation Status | Development Date | Code Review Date |
| --- | --- | --- | --- | --- | --- | --- |
| TASK-001 | Backend Foundation and Configuration | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-002 | Users Table DDL | MODIFY | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-003 | User Repository | MODIFY | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-004 | Registration Service and API | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-005 | First-stage Login Service and API | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-006 | Temporary-code Verification and API | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-007 | Logout API Placeholder | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-008 | User Permission Service and APIs | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-009 | User Management Test Suite | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |
| TASK-010 | PostgreSQL and Redis Docker Compose | ADD | 2026-09-15 | DEVELOPED DONE | 2026-09-15 |  |

## IV. Technical Stack

- Python: 3.14
- Framework: FastAPI 0.141.1
- Database: PostgreSQL 17
- Container Runtime: Docker and Docker Compose
- Other Dependencies: asyncpg, redis, aiosmtplib, pydantic-settings, uvicorn,
  pytest, pytest-asyncio, and httpx are declared in pyproject.toml.

## V. Existing System Analysis

```text
Confirmed application source: main.py, config/, src/objects/, and
src/repositories/ exist.
Confirmed unit test: tests/test_foundation.py exists.
Confirmed application configuration: config/settings.py defines PostgreSQL,
Redis, and SMTP environment settings.
Confirmed database DDL: database/01-DDL/01-TB_USERS.sql exists.
Confirmed reusable modules: UserRepository, User, StoredUser, Settings, and
database/Redis connection helpers exist.
Confirmed Docker Compose configuration: docker-compose.yml and .env.example
exist.
Confirmed controller, authentication, and endpoint contract: none exist.
```

The existing foundation files were extended and verified during development.
All tasks are now marked `DEVELOPED DONE`; PostgreSQL integration testing was
explicitly bypassed in the final local regression at PM request, while the
repository integration test had previously passed through the WSL PostgreSQL
service using port 5432.

## VI. System Design

```text
HTTP Request
    -> FastAPI controller/router
    -> request schema validation
    -> user service
    -> user repository -> PostgreSQL
    -> Redis / SMTP where login workflow requires it
    -> HTTP Response
```

```text
Docker Compose network
   -> postgres service (PostgreSQL 17, persistent named volume)
   -> redis service (Redis, health check)

FastAPI application
   -> PostgreSQL and Redis using environment-configured host and port
```

- Controller/router: parse the requirement-defined request envelope, invoke
   services, apply the confirmed response envelope, and map domain errors to the
   PM-defined status/message contract.
- Service: own registration, login, temporary-code, and role workflow.
- Repository: own only parameterized PostgreSQL query execution and row mapping.
- Redis adapter: store temporary codes and PM-approved lock state using TTL.
- SMTP adapter: render and send the requirement-defined temporary-code Email.

The `TB_USERS` DDL must create the requirement-defined uid primary key, unique
Email, non-unique user_name, SHA-256 password value, restricted permission
values, and system-managed `created_at` and `updated_at` fields.

## VII. Implementation Steps

### TASK-001 Backend Foundation and Configuration

```text
File: main.py (Existing File)
Target: FastAPI application composition root
Change Type: Add

File: src/routers.py (Existing File)
Target: application router registration
Change Type: Add

File: config/database.py, config/redis.py, config/smtp.py (Existing Files)
Target: PostgreSQL, Redis, and SMTP configuration
Change Type: Add

Reuse: Settings, create_database_pool(), create_redis_client(), and the empty
application router already exist.

Current Behavior: main.py creates a FastAPI application, uses a lifespan to
create PostgreSQL and Redis clients, and registers src.routers.router. Settings
loads the existing .env.example variable names. SMTP only has a client factory.

Expected Behavior: The application can register user-management routes and
obtain PostgreSQL, Redis, and SMTP dependencies from environment configuration.

Implementation:
1. Retain the existing composition root and environment-variable contract.
2. Verify PostgreSQL and Redis lifecycle behavior against TASK-010 services.
3. Add service/controller package structure only when a PM-approved endpoint
   contract enables TASK-004 through TASK-008.
4. Add SMTP connection and close handling inside the email delivery component
   created by TASK-005; do not create a persistent SMTP dependency.
5. Add route registration and common domain-error mapping for the documented
   methods, paths, JSON header envelope, status codes, and messages. Defer
   login-required route authorization until TASK-007 and TASK-008 are defined.
6. Keep credentials out of source control and logs.

Error Handling: Fail clearly for invalid required configuration and log
infrastructure connection failures without secrets.

Validation: Start FastAPI against the TASK-010 PostgreSQL and Redis containers,
then verify incomplete configuration is handled according to the selected policy.

Testing: Add configuration and router-registration tests.
```

### TASK-002 Users Table DDL

```text
File: database/01-DDL/01-TB_USERS.sql (Existing File)
Target: TB_USERS table definition
Change Type: Modify

Reuse: The table name and column requirements in 01-User-Manager.md.

Current Behavior: 01-TB_USERS.sql creates TB_USERS with a VARCHAR(64) uid
primary key, unique email, SHA-256-sized password column, permission check,
timestamp defaults, and an updated_at trigger.

Expected Behavior: TB_USERS provides uid primary-key, unique Email, non-unique
user_name, three valid permission values, default user role, and automatically
managed timestamps.

Implementation:
1. Add a non-null VARCHAR user_name column to the existing DDL. Do not add a
   uniqueness constraint because the requirement explicitly permits duplicates.
2. Update an existing local database through a migration approved for its data
   state; clean-environment validation may apply the revised DDL directly.
3. Apply the DDL to a clean PostgreSQL 17 service.
4. Verify primary-key, unique Email, non-unique user_name, permission check,
   default user role, and database-managed updated_at behavior.

Error Handling: Preserve unique-constraint failures so the service can map them
to a duplicate-Email domain error.

Validation: Apply DDL to a clean TASK-010 PostgreSQL container and verify
constraints.

Testing: Add database integration tests for constraints and timestamps.
```

### TASK-003 User Repository

```text
File: src/repositories/user_repository.py (Existing File)
Target: UserRepository
Change Type: Modify

Reuse: TB_USERS DDL, User, StoredUser, and DuplicateEmailError already exist.

Current Behavior: UserRepository implements get_by_email(), get_by_uid(),
create(), list_all(), list_by_permission(), and update_permission() using
asyncpg positional parameters, but its queries and objects do not include the
newly required user_name field. Public response objects exclude password.

Expected Behavior: Services can get users by Email and uid, create users with
user_name, list users by role scope, and update permission without raw
request-value SQL.

Implementation:
1. Extend User and StoredUser with user_name and update every SELECT, INSERT,
   RETURNING clause, and row mapper in UserRepository to include it.
2. Extend create() to accept user_name; retain asyncpg positional parameter
   binding for every query value.
3. Add a repository query for admin listings that excludes permission=admin and
   the operator uid. Extend manager listings to exclude the operator uid.
4. Verify each query against PostgreSQL using the TASK-002 schema.
5. Verify the result mapping excludes password from User list and update
   results, while StoredUser remains restricted to authentication services.
6. Confirm unique email conflicts map to DuplicateEmailError and document any
   unexpected database error behavior found by integration tests.

Error Handling: Repository must not create HTTP responses; it logs and propagates
unexpected database failures with context.

Validation: Test executed repository queries to ensure values are parameterized.

Testing: Add repository unit and PostgreSQL integration tests for every query.
```

### TASK-004 Registration Service and API

```text
File: src/services/user_registration_service.py (New File)
Target: UserRegistrationService.register()
Change Type: Add

File: src/controllers/user_registration_controller.py (New File)
Target: registration handler and request/response schemas
Change Type: Add

Reuse: UserRepository.get_by_email() and UserRepository.create().

Current Behavior: No registration workflow exists.

Expected Behavior: POST /userController/register accepts the documented JSON
header/body envelope and creates one TB_USERS record with Email-derived
SHA-256 uid, userName, the client-supplied SHA-256 password value, and user
role.

Implementation:
1. Define the POST /userController/register request and response envelopes with
   email, userName, password, and confirmPassword in body.
2. Validate Email format and password-confirmation equality.
3. Use get_by_email before creation and reject existing Email.
4. Generate uid from Email SHA-256 and persist the client-supplied SHA-256
   password value without a second server hash.
5. Persist the account and userName through the repository with default user
   permission.
6. Map success to 200 Success/User registered successfully. Map all documented
   registration failures to 401 Failed/User registration failed.

Error Handling: Map database uniqueness races to duplicate Email; never log
plaintext passwords.

Validation: Run all success, invalid Email, duplicate Email, and mismatch cases
from the registration scenario file.

Testing: Add controller and service tests, including persistence uniqueness race.
```

### TASK-005 First-stage Login Service and API

```text
File: src/services/user_login_service.py (New File)
Target: UserLoginService.request_temporary_code()
Change Type: Add

File: src/controllers/user_login_controller.py (New File)
Target: first-stage login handler and request schema
Change Type: Add

File: src/services/temporary_code_store.py (New File)
Target: Redis code and lock-state adapter
Change Type: Add

File: src/services/temporary_code_email_service.py (New File)
Target: SMTP template rendering and delivery
Change Type: Add

Reuse: UserRepository.get_by_email() and configuration from TASK-001.

Current Behavior: No login, Redis, or SMTP implementation exists.

Expected Behavior: POST /userController/login accepts both documented login
body variants. Valid registered credentials create a random six-character
alphanumeric Temporary Code, overwrite the Redis value keyed by Email with a
three-minute TTL, and deliver the required Email. Unknown Email and wrong
password produce the same login-failure response.

Implementation:
1. Route the first-stage request by its body fields: email plus password; route
   the second-stage request by email plus temporary_code.
2. Retrieve the user and compare the SHA-256 hash of supplied password to stored
   password.
3. On credential failure return the documented 401 Failed login response;
   do not add lockout counters because the updated requirement removed them.
4. On success, generate a random six-character alphanumeric code, replace the
   Email-scoped Redis value with a three-minute TTL, and send the specified
   subject and body through SMTP.
5. Do not expose Temporary Codes or password hashes in responses or logs.

Error Handling: Do not return success when Redis storage or SMTP delivery fails;
log database, Redis, and SMTP failures without secret values.

Validation: Verify valid, wrong-password, unregistered-Email, resend-replaces-
code, TTL, and Email-template behavior.

Testing: Mock repository, Redis, and SMTP in service tests; add Redis TTL,
overwrite, and rendered-Email integration tests.
```

### TASK-006 Temporary-code Verification and API

```text
File: src/services/user_login_service.py (Created in TASK-005)
Target: UserLoginService.verify_temporary_code()
Change Type: Add

File: src/controllers/user_login_controller.py (Created in TASK-005)
Target: temporary-code verification handler and schemas
Change Type: Add

Reuse: Redis temporary-code adapter from TASK-005.

Current Behavior: No second-stage login workflow exists.

Expected Behavior: A valid, unexpired Email-scoped Temporary Code completes
login; invalid or expired codes return the documented verification-failed
response. The response body is empty as defined by the requirement.

Implementation:
1. Accept email and temporary_code in the documented request body.
2. Read the Email-scoped Redis value and retain the three-minute TTL behavior.
3. Compare the supplied code to the stored value and return the documented
   200 Success or 401 Failed status/message.
4. Do not add failure counters, lockouts, single-use deletion, or a new
   credential because the updated requirement does not define those behaviors.

Error Handling: Redis failures must never become successful authentication.

Validation: Verify Gherkin valid/invalid cases, Email correlation, expiry, and
resend replacement behavior.

Testing: Add service/controller tests for valid, wrong, expired, replaced, and
storage-failure cases.
```

### TASK-007 Logout API Placeholder

```text
File: src/controllers/user_logout_controller.py (New File)
Target: logout route handler
Change Type: Add

Reuse: Router registration from TASK-001.

Current Behavior: No logout interface exists.

Expected Behavior: POST /userController/logout accepts email in the documented
JSON header/body envelope and returns the documented 200 success envelope
without inventing token revocation, session deletion, or other behavior.

Implementation:
1. Require header.uid and use UserRepository.get_by_uid() to confirm that the
   current operator exists before returning the documented placeholder success
   contract.
2. Do not add token revocation, session deletion, or other logout state because
   the requirement does not define those behaviors.

Error Handling: Use the PM-confirmed response contract.

Validation: Confirm route registration and agreed placeholder response.

Testing: Add route test once the endpoint contract is approved.
```

### TASK-008 User Permission Service and APIs

```text
File: src/services/user_permission_service.py (New File)
Target: UserPermissionService.list_users() and update_permission()
Change Type: Add

File: src/controllers/user_permission_controller.py (New File)
Target: list and update handlers and schemas
Change Type: Add

Reuse: UserRepository methods from TASK-003 and JSON header parsing from the
controllers created in TASK-004 through TASK-006.

Current Behavior: No header.uid-based operator lookup, user list, or permission
update workflow exists.

Expected Behavior: Enforce the role matrix in the requirement. admin lists only
non-admin users and changes user/manager to user/manager. manager lists user
only and changes a user to user/manager. user is denied. Every admin target,
including the current operator, is excluded from listing and denied for update.

Implementation:
1. Read the operator uid from the JSON header envelope and load the current
   role from TB_USERS. Reject the request when header.uid is missing or does
   not identify a stored user. Do not authorize from client-provided Permission.
2. Use the TASK-003 repository operation that excludes non-admin users and the
   operator for admin; use the manager user-only listing excluding the operator;
   deny user.
3. Validate requested role before loading the target user.
4. Enforce the complete operator/current-role/target-role matrix before update.
5. Deny every admin target update, as required.
6. Exclude password values from all list and update responses.

Error Handling: Return the documented 401 Failed/Unauthorized response for a
forbidden action or a missing target user.

Validation: Execute every permission Gherkin scenario plus missing-target and
invalid-requested-role cases.

Testing: Add service matrix tests and controller tests for missing, unknown,
and valid header.uid values plus response contracts.
```

### TASK-009 User Management Test Suite

```text
File: tests/services/test_user_registration_service.py (New File)
Target: registration service tests
Change Type: Add

File: tests/services/test_user_login_service.py (New File)
Target: both login-stage service tests
Change Type: Add

File: tests/services/test_user_permission_service.py (New File)
Target: role matrix tests
Change Type: Add

File: tests/repositories/test_user_repository.py (New File)
Target: PostgreSQL repository tests
Change Type: Add

File: tests/controllers/test_user_management_controllers.py (New File)
Target: FastAPI route contract tests
Change Type: Add

Reuse: tests/test_foundation.py, the existing settings/application factory, and
the three requirement Gherkin files as test scenario sources.

Current Behavior: tests/test_foundation.py tests settings URL construction and
application factory route initialization. Feature-specific tests do not exist.

Expected Behavior: Tests cover every Gherkin scenario and technical requirement.

Implementation:
1. Translate all registration, login, temporary-code, listing, and role-update
   scenarios to automated tests, including the required header.uid account
   lookup for logout and permission operations.
2. Add TTL and replacement tests for Temporary Codes; do not add lockout tests
   because the updated requirement no longer specifies lockout behavior.
3. Run PostgreSQL and Redis integration tests against TASK-010 Docker Compose
   services, including user_name DDL constraints and parameterized queries.
4. Assert rendered SMTP subject/body without external Email delivery.
5. Assert that passwords and temporary codes never appear in logs or user lists.

Error Handling: Cover explicit domain and infrastructure failures at boundaries.

Validation: Run focused user-management tests, then full project tests after a
test command is established.
```

### TASK-010 PostgreSQL and Redis Docker Compose

```text
File: docker-compose.yml (Existing File)
Target: PostgreSQL and Redis local development service definitions
Change Type: Add

File: .env.example (Existing File)
Target: Non-secret Docker Compose and application connection variable template
Change Type: Add

Reuse: PostgreSQL 17 requirement and Redis temporary-code storage requirement.

Current Behavior: docker-compose.yml defines PostgreSQL 17 and Redis 7.4 with
configurable ports, PostgreSQL persistent storage, and health checks.
.env.example defines the application and Compose environment variables.

Expected Behavior: Docker Compose starts a PostgreSQL 17 container and a Redis
container on an isolated Compose network. The containers expose configurable
host ports for local development, use persistent storage for PostgreSQL, and
report health before dependent local workflows run.

Implementation:
1. Retain PostgreSQL 17 and Redis 7.4 images, environment variables, ports,
   named volume, and health checks in the existing Compose definition.
2. Verify the .env.example variables are compatible with Settings and Compose.
3. Add no FastAPI or SMTP containers because this task only requires PostgreSQL
   and Redis connectivity.

Error Handling: Health checks must make unavailable or unready services visible.
Application configuration must fail clearly when a selected host, port, or
credential cannot connect. No actual credentials may appear in source, logs, or
committed environment files.

Validation:
1. Run docker compose config to validate the Compose definition.
2. Run docker compose up -d and wait for both services to be healthy.
3. Connect to PostgreSQL with the configured database, user, and password.
4. Connect to Redis and verify a set/get operation plus a TTL.
5. Run TASK-002 DDL and PostgreSQL/Redis integration tests against containers.

Testing: Add or update integration-test fixtures to read the same environment
contract and skip with a clear reason when Docker services are unavailable.
```

## VIII. Security Follow-up

PM confirms that current functionality may use JSON header.uid to look up the
operator in TB_USERS. All routes except register and login must reject missing
or unknown UIDs. Authorization must use the role loaded from TB_USERS and must
ignore client-provided Permission. This is an interim functional rule, not a
claim that UID proves a non-forgeable authenticated session.

UID and Permission forgery prevention, server-side session state, expiry, and
token revocation remain deferred security improvements. They are outside this
plan and require a future PM requirement change before implementation.

## IX. Plan Validation

- [x] Requirement type identified as New Requirement.
- [x] Feature, flows, and all Gherkin scenarios reviewed.
- [x] Existing architecture, source, tests, configuration, DDL, and reusable
  components checked.
- [x] Every requirement has a corresponding implementation task.
- [x] Database, configuration, integration, validation, logging, error,
  compatibility, and test impacts are recorded.
- [x] API request, response, status, and JSON header-envelope contracts are
   defined for all feature tasks.
- [x] Registration Gherkin scenarios match the latest request contract.
- [x] No production code, test code, or unconfirmed business rule is added.
- [x] PM approved interim header.uid account lookup for logout and permission
   operations; database-loaded roles are used for authorization.
- [x] Updated implementation plan has completed human review.
- [x] Focused controller tests and service regression tests pass in `.venv`.
- [x] PostgreSQL DDL, Redis TTL, and Docker health checks were verified in WSL.
- [x] PostgreSQL integration test bypass was explicitly approved for the final
   regression run.

## X. Review Status

- [x] Implementation Plan 已完成人工審核
- [x] Development 完成
- [ ] Code Review 通過

Plan Status: Awaiting Code Review