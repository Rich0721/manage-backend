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
Plan Date: 2026-09-14
Requirement Type: New Requirement
Requirement Summary: 新增使用者註冊、兩階段登入、登出接口與權限管理。
```

## II. Requirement Summary

1. 註冊驗證 Email 格式、確認密碼與 Email 唯一性，以 Email 的 SHA-256雜湊產生 uid，並以 SHA-256 雜湊密碼後建立預設 `user` 角色帳號。
2. 第一階段登入驗證 Email 與密碼；失敗超過五次鎖定 15 分鐘。成功時將臨時編號以三分鐘 Redis TTL 儲存，並透過 SMTP 寄送指定 Email 樣板。
3. 第二階段驗證臨時編號；錯誤超過五次鎖定五分鐘。
4. 保留登出接口，不實作未定義的登出行為。
5. `admin` 可列出所有使用者並管理 `user`、`manager`；`manager` 只能列出及管理目前為 `user` 的帳號；`user` 不可查詢或修改。
6. 所有 PostgreSQL SQL 查詢都必須使用 parameterized query。

## III. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implentation Status | Development Date | Code Review Date |
| --- | --- | --- | --- | --- | --- | --- |
| TASK-001 | Backend Foundation and Configuration | ADD | 2026-09-14 | TODO |  |  |
| TASK-002 | Users Table DDL | ADD | 2026-09-14 | TODO |  |  |
| TASK-003 | User Repository | ADD | 2026-09-14 | TODO |  |  |
| TASK-004 | Registration Service and API | ADD | 2026-09-14 | TODO |  |  |
| TASK-005 | First-stage Login Service and API | ADD | 2026-09-14 | TODO |  |  |
| TASK-006 | Temporary-code Verification and API | ADD | 2026-09-14 | TODO |  |  |
| TASK-007 | Logout API Placeholder | ADD | 2026-09-14 | TODO |  |  |
| TASK-008 | User Permission Service and APIs | ADD | 2026-09-14 | TODO |  |  |
| TASK-009 | User Management Test Suite | ADD | 2026-09-14 | TODO |  |  |
| TASK-010 | PostgreSQL and Redis Docker Compose | ADD | 2026-09-14 | TODO |  |  |

## IV. Technical Stack

- Python: 3.14
- Framework: FastAPI 0.141.1
- Database: PostgreSQL 17
- Container Runtime: Docker and Docker Compose
- Other Dependencies: Redis client, PostgreSQL driver, SMTP client, and test framework require selection because no dependency manifest currently exists.

## V. Existing System Analysis

```text
Confirmed existing application source: none.
Confirmed existing unit tests: none.
Confirmed existing application configuration: none.
Confirmed database DDL: database/01-DDL/ is empty.
Confirmed reusable application modules: none.
Confirmed Docker Compose configuration: none.
```

All `src/`, `config/`, `tests/`, and `main.py` paths below are proposed new files. They follow the repository backend skill reference structure and are not described as pre-existing implementation paths.

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

- Controller/router: parse requests, invoke services, perform authentication hooks, and map domain errors to the PM-approved HTTP error contract.
- Service: own registration, login, temporary-code, lockout, and role workflow.
- Repository: own only parameterized PostgreSQL query execution and row mapping.
- Redis adapter: store temporary codes and PM-approved lock state using TTL.
- SMTP adapter: render and send the requirement-defined temporary-code Email.

The new `TB_USERS` DDL must create the requirement-defined uid primary key, unique Email, SHA-256 password value, restricted permission values, and system-managed `created_at` and `updated_at` fields.

## VII. Implementation Steps

### TASK-001 Backend Foundation and Configuration

```text
File: main.py (New File)
Target: FastAPI application composition root
Change Type: Add

File: src/routers.py (New File)
Target: application router registration
Change Type: Add

File: config/database.py, config/redis.py, config/smtp.py (New Files)
Target: PostgreSQL, Redis, and SMTP configuration
Change Type: Add

Reuse: No reusable application component exists.

Current Behavior: The repository has no runnable FastAPI application,
configuration module, dependency manifest, or package structure.

Expected Behavior: The application can register user-management routes and
obtain PostgreSQL, Redis, and SMTP dependencies from environment configuration.

Implementation:
1. Create the backend-skill reference structure: src/controllers, src/services,
   src/repositories, src/objects, config, and tests.
2. Reuse TASK-010 environment-variable contract to configure PostgreSQL and
   Redis connections for host-run and Docker Compose-run application modes.
3. Create settings and dependency lifecycle management for PostgreSQL and Redis.
4. Create SMTP connections only for sending, then close them reliably.
5. Register user-management routes and a common domain-error mapping point.
6. Keep credentials out of source control and logs.

Error Handling: Fail clearly for invalid required configuration and log
infrastructure connection failures without secrets.

Validation: Start FastAPI against the TASK-010 PostgreSQL and Redis containers,
then verify incomplete configuration is handled according to the selected policy.

Testing: Add configuration and router-registration tests.
```

### TASK-002 Users Table DDL

```text
File: database/01-DDL/01-TB_USERS.sql (New File)
Target: TB_USERS table definition
Change Type: Add

Reuse: The table name and column requirements in 01-User-Manager.md.

Current Behavior: database/01-DDL/ contains no DDL.

Expected Behavior: TB_USERS provides uid primary-key, unique Email, three valid
permission values, default user role, and automatically managed timestamps.

Implementation:
1. Create the uid, email, password, permission, created_at, and updated_at
   columns using PostgreSQL 17-compatible syntax.
2. Add primary-key, unique Email, and permission check constraints.
3. Add user as the permission default and define timestamp defaults.
4. Add the selected database-side updated_at mechanism.

Error Handling: Preserve unique-constraint failures so the service can map them
to a duplicate-Email domain error.

Validation: Apply DDL to a clean TASK-010 PostgreSQL container and verify
constraints.

Testing: Add database integration tests for constraints and timestamps.
```

### TASK-003 User Repository

```text
File: src/repositories/user_repository.py (New File)
Target: UserRepository
Change Type: Add

Reuse: TB_USERS DDL from TASK-002.

Current Behavior: No data-access code exists.

Expected Behavior: Services can get users by Email and uid, create users, list
users by role scope, and update permission without raw request-value SQL.

Implementation:
1. Add get_by_email, get_by_uid, create, list_all, list_by_permission, and
   update_permission operations.
2. Use only driver-supported parameter binding for all query values.
3. Map rows to a user object that excludes password from list responses.
4. Surface expected unique conflicts separately from unexpected database errors.

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

Expected Behavior: Valid Email, Password, ConfirmPassword input creates one
TB_USERS record with Email-derived SHA-256 uid, SHA-256 password, and user role.

Implementation:
1. Define the registration request schema with Email, Password, ConfirmPassword.
2. Validate Email format and password-confirmation equality.
3. Use get_by_email before creation and reject existing Email.
4. Generate uid from Email SHA-256 and hash the password with requirement-
   specified SHA-256.
5. Persist the account through the repository with default user permission.
6. Map invalid Email, duplicate Email, and mismatch errors to the approved API
   error contract.

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

Current Behavior: No login, Redis, lockout, or SMTP implementation exists.

Expected Behavior: Valid registered credentials cause temporary-code creation,
three-minute Redis storage, and delivery of the required Email; unknown Email
and wrong password produce the same login-failure response.

Implementation:
1. Validate Email format and check the confirmed credential lock state.
2. Retrieve the user and compare the SHA-256 hash of supplied password to stored
   password.
3. On failure, increment the confirmed counter and apply a 15-minute lock after
   more than five failures.
4. On success, generate a temporary code, write it with a 3-minute Redis TTL,
   and send the specified subject and body through SMTP.
5. Do not expose temporary codes or plaintext passwords in responses or logs.

Error Handling: Do not return success when Redis storage or SMTP delivery fails;
log database, Redis, and SMTP failures without secret values.

Validation: Verify valid, wrong-password, unregistered-Email, lockout, TTL, and
Email-template behavior.

Testing: Mock repository, Redis, and SMTP in service tests; add Redis TTL and
rendered-Email integration tests.
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

Expected Behavior: A valid, unexpired temporary code completes login; invalid
codes return a temporary-code error, and more than five failures lock for five
minutes.

Implementation:
1. Accept TempNumber plus the PM-confirmed user or transaction correlation data.
2. Check the temporary-code lock state before comparison.
3. Read the scoped Redis value and retain the three-minute TTL behavior.
4. Increment failed-code count and apply the five-minute lock at the confirmed
   threshold.
5. On valid code, consume the code and issue the PM-confirmed authenticated
   state or credential.

Error Handling: Redis failures must never become successful authentication.

Validation: Verify Gherkin valid/invalid cases, expiry, lockout, and confirmed
single-use semantics.

Testing: Add service/controller tests for valid, wrong, expired, locked, and
storage-failure cases.
```

### TASK-007 Logout API Placeholder

```text
File: src/controllers/user_logout_controller.py (New File)
Target: logout route handler
Change Type: Add

Reuse: Router registration from TASK-001.

Current Behavior: No logout interface exists.

Expected Behavior: A logout interface exists without inventing token revocation,
session deletion, or other unapproved behavior.

Implementation: Register the PM-confirmed endpoint and implement only approved
placeholder semantics after the authentication contract is defined.

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

Reuse: UserRepository methods from TASK-003 and authenticated user context from
TASK-006.

Current Behavior: No authenticated context, user list, or permission update
workflow exists.

Expected Behavior: Enforce the role matrix in the requirement. admin lists all
and changes user/manager to user/manager. manager lists user only and changes a
user to user/manager. user is denied. Admin-to-admin remains unresolved.

Implementation:
1. Obtain operator identity and role from the confirmed authentication mechanism.
2. Use list_all for admin, list_by_permission(user) for manager, and deny user.
3. Validate requested role before loading the target user.
4. Enforce the complete operator/current-role/target-role matrix before update.
5. Do not implement admin-to-admin modification until PM decides its behavior.
6. Exclude password values from all list and update responses.

Error Handling: Return authorization denial for forbidden actions and a distinct
domain error for a missing target user.

Validation: Execute every permission Gherkin scenario plus missing-target and
invalid-requested-role cases.

Testing: Add service matrix tests and controller authentication/response tests.
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

Reuse: Three requirement Gherkin files as test scenario sources.

Current Behavior: No test suite exists.

Expected Behavior: Tests cover every Gherkin scenario and technical requirement.

Implementation:
1. Translate all registration, login, temporary-code, listing, and role-update
   scenarios to automated tests.
2. Add threshold tests for credential/code failures and TTL tests for all locks
   and temporary codes.
3. Run PostgreSQL and Redis integration tests against TASK-010 Docker Compose
   services, including DDL constraints and parameterized query operations.
4. Assert rendered SMTP subject/body without external Email delivery.
5. Assert that passwords and temporary codes never appear in logs or user lists.

Error Handling: Cover explicit domain and infrastructure failures at boundaries.

Validation: Run focused user-management tests, then full project tests after a
test command is established.
```

### TASK-010 PostgreSQL and Redis Docker Compose

```text
File: docker-compose.yml (New File)
Target: PostgreSQL and Redis local development service definitions
Change Type: Add

File: .env.example (New File)
Target: Non-secret Docker Compose and application connection variable template
Change Type: Add

Reuse: PostgreSQL 17 requirement and Redis temporary-code storage requirement.

Current Behavior: No Docker Compose file, container configuration, environment
template, or local PostgreSQL/Redis service exists in the repository.

Expected Behavior: Docker Compose starts a PostgreSQL 17 container and a Redis
container on an isolated Compose network. The containers expose configurable
host ports for local development, use persistent storage for PostgreSQL, and
report health before dependent local workflows run.

Implementation:
1. Define a postgres service using PostgreSQL 17 and a redis service using an
   explicitly selected Redis image version.
2. Configure POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD through Docker
   Compose environment variables; do not commit actual credentials.
3. Create named volume storage for PostgreSQL data and health checks for both
   services.
4. Publish configurable host ports for local tools, while documenting that an
   application inside the Compose network uses postgres and redis as host names.
5. Add .env.example with placeholders and host/port variables required by
   config/database.py and config/redis.py; add real .env to .gitignore when it
   is created by the implementation agent.
6. Do not add FastAPI or SMTP containers because this task only requires
   PostgreSQL and Redis connectivity.

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

## VIII. Open Questions

1. API methods, paths, response bodies, HTTP statuses, and error format are not defined. This blocks exact controller contracts for TASK-004 to TASK-008.
2. The post-verification authentication mechanism is undefined. It is required to identify operators for TASK-008 and to define TASK-007 behavior.
3. The Gherkin temporary-code request has only TempNumber. Its user or first-stage transaction correlation field is required for safe verification.
4. Code digit count, randomness, resending, one-time use, and Redis key scope are undefined.
5. Lock counter scope, reset timing, storage location, and whether the sixth failure triggers the phrase "超過五次" require PM confirmation.
6. Admin changing an admin is explicitly unresolved in the requirement.
7. Connection details, environment-variable names, and dependency choices for PostgreSQL, Redis, and SMTP are undefined.
8. The requirement mandates SHA-256 password hashing. The plan preserves this wording, but PM should confirm because no salt or work factor is specified.
9. No initial admin-account provisioning method is defined, while registration always gives the user role.

## IX. Plan Validation

- [x] Requirement type identified as New Requirement.
- [x] Feature, flows, and all Gherkin scenarios reviewed.
- [x] Existing architecture, source, tests, configuration, DDL, and reusable
  components checked.
- [x] Every requirement has a corresponding implementation task.
- [x] Database, API, configuration, integration, validation, logging, error,
  compatibility, and test impacts are recorded.
- [x] No production code, test code, or unconfirmed business rule is added.
- [x] PM has resolved the listed core open questions.
- [x] Implementation Plan has completed human review.

## X. Review Status

- [x] Implementation Plan 已完成人工審核
- [ ] Development 完成
- [ ] Code Review 通過

Plan Status: Awaiting Review