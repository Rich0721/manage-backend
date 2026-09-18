# Authorization Base Objects and Redis Connection Implementation Plan

## I. Plan Status

```text
Plan Status: Awaiting Review
Plan Date: 2026-09-17
```

本階段只規劃 Authorization 基礎 Object 與 Redis Connection。JWT 產生、JWT
驗證、Redis token CRUD/TTL、Controller 整合及其他 feature 的 API contract，
皆待後續需求確認後另行建立細部實作計畫。

## II. Requirement Information

- Feature Name: Authorization Base Objects and Redis Connection
- Requirement Document: `Features/Document/01-Authorization.md`
- Requirement Type: New Requirement
- Requirement Date: 2026-09-17
- Plan Date: 2026-09-17
- Related Scenario: None in current scope
- Other Requirement: None

### Requirement Summary

建立以下 JSON request/response body 所需的基礎 Object：

```json
{
  "header": {},
  "body": {
    "auth": {
      "status": null,
      "message": null,
      "uid": null,
      "authorization": null
    },
    "info": {}
  }
}
```

並建立可供後續 Authorization 功能使用的 async Redis connection。此階段不處理
JWT 內容、不將 token 寫入 Redis，也不實作 authentication behavior。

## III. Requirement Scope

### In Scope

1. `AuthorizationObject`
   - `status`
   - `message`
   - `uid`
   - `authorization`
2. `AuthorizationBody`
   - `auth`
   - `info`
3. `AuthorizationEnvelope`
   - `header`
   - `body`
4. Redis connection environment setting。
5. Async Redis client creation、connection check、client access 與 close lifecycle。
6. Object 與 Redis connection unit tests。

### Deferred Scope

- JWT encode / decode / signature / claims / expiration。
- Bearer Token 格式驗證。
- `<Uid>:Authorization:JWT` key 的 save、get、refresh TTL、delete。
- DEBUG / PRODUCTION authentication policy。
- Authorization Service、Repository、Controller dependency 或 middleware。
- Login、logout、permission 或其他 feature integration。
- Endpoint-specific `info` schema。
- HTTP error、application status/message 與 response mapping。
- Multi-device login behavior。
- PostgreSQL schema 或 data migration。

Deferred Scope 不得由 Programmer Agent 在本計畫中提前實作。

## IV. Existing System Analysis

### Technology Context

| Item | Current Decision |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI 0.141.1 |
| Object Validation | FastAPI bundled Pydantic |
| Redis Server | Redis 8.1.0 |
| Redis Client | redis-py 8.1.0 |
| Test Framework | pytest、pytest-asyncio |
| Database | PostgreSQL 17；本階段不使用 |

### Repository State

- 尚無 `src/`、`tests/`、`requirements.txt` 或 application code。
- 尚無可重用的 schema、settings 或 Redis connection component。
- 尚無既有測試與 logging/error pattern。
- 本需求可直接放入既有 architecture 定義的 `models/schemas` 與 `config`，
  不需要新增 architecture layer。

### Architecture Placement

```text
src/models/schemas/authorization.py
    └── JSON body objects

src/config/settings.py
    └── REDIS_URL environment setting

src/config/redis.py
    └── Async Redis connection lifecycle
```

本階段沒有 Controller、Service、Repository 或 Database dependency。

## V. System Design

### 5.1 Authorization Objects

#### `AuthorizationObject`

| Field | Type | Default | Responsibility |
|---|---|---|---|
| `status` | `str | None` | `None` | 保留 application response status |
| `message` | `str | None` | `None` | 保留 application response message |
| `uid` | `str | None` | `None` | 保留登入後取得的 user identifier |
| `authorization` | `str | None` | `None` | 保留登入後取得的 Bearer Token string |

本階段只定義資料型態，不驗證 status 合法值、Uid 格式、Bearer prefix 或 JWT。

#### `AuthorizationBody`

| Field | Type | Default | Responsibility |
|---|---|---|---|
| `auth` | `AuthorizationObject` | empty object | Authorization metadata |
| `info` | `dict[str, Any]` | empty object | 後續 feature data placeholder |

`info` 暫時保留為 dynamic object；後續 feature 必須另行建立自己的 typed schema，
不得將本 placeholder 當成永久取代 endpoint validation 的設計。

#### `AuthorizationEnvelope`

| Field | Type | Default | Responsibility |
|---|---|---|---|
| `header` | `dict[str, Any]` | empty object | 保留需求中的 header object |
| `body` | `AuthorizationBody` | empty object | 固定包含 auth 與 info |

上述 Object 表達的是 JSON body，不讀取或設定實際 HTTP Authorization header。
所有 object/dict default 必須使用 `default_factory`，避免 mutable default 共用。

### 5.2 Object Validation Boundary

- JSON key 使用需求中的 lowercase：`header`、`body`、`auth`、`info`、`status`、
  `message`、`uid`、`authorization`。
- `AuthorizationObject` 禁止未定義欄位，避免 Authorization metadata 無限制擴張。
- `header` 與 `info` 暫允許 dynamic key，因其內容明確留待其他需求定義。
- Request 與 Response 暫共用同一組 base objects；required field 與不同方向的
  validation 留待 endpoint requirement 決定。
- Object 不執行 Redis I/O 或任何 authentication business logic。

### 5.3 Redis Settings

| Environment Variable | Purpose | Default | Required |
|---|---|---|---|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` | No；Docker/production 必須覆寫 |

- 使用 `os.getenv("REDIS_URL", "redis://localhost:6379/0")`，符合 project
  environment rule。
- Connection URL 可包含 authentication information，但不得寫入 log 或 exception
  message。
- JWT、TTL 與 environment mode setting 不屬本階段，不建立對應 configuration。

### 5.4 Async Redis Connection

`RedisConnectionManager` 負責單一 async Redis client lifecycle，主要使用方式必須為
`async with`：

```text
Settings.REDIS_URL
    ↓
async with RedisConnectionManager(settings) as redis_client
    ↓
RedisConnectionManager.__aenter__()
    ↓
connect()
    ↓
redis.asyncio.Redis.from_url(..., decode_responses=True)
    ↓
await client.ping()
    ↓
yield connected Redis client
    ↓
Redis operations or raised exception
    ↓
RedisConnectionManager.__aexit__()
    ↓
close()
    ↓
await client.aclose() in all exit paths
```

Responsibilities：

- `connect()`：建立 client 並使用 `ping()` 驗證連線；重複呼叫不得建立多個 client。
- `get_client()`：只回傳已成功連線的 client；未連線時明確失敗。
- `close()`：安全關閉 client，重複呼叫應保持 idempotent。
- `__aenter__()`：呼叫 `connect()` 並回傳已驗證的 Redis client。
- `__aexit__()`：無論使用區塊正常完成或拋出例外，都必須 await `close()`；不得
  suppress 原始例外。
- Programmer 使用 connection 時應優先採 `async with RedisConnectionManager(...)`。
  若未使用 context manager，caller 必須使用 `try...finally` 並在 `finally` 中
  await `close()`。
- 不在此 component 實作 Redis key、JWT、TTL 或 repository query。
- 不建立每個 request 各自的新 connection pool。

### 5.5 Error Handling and Logging

- Redis connection/timeout error 保留為 infrastructure error，不轉成 authorization
  error。
- `get_client()` 在 connect 前呼叫時，拋出明確的 connection-not-initialized error。
- `connect()` 建立 client 後若 `ping()` 失敗，必須在重新拋出原始例外前執行
  `await client.aclose()`，避免 partial connection/pool 殘留。
- `__aexit__()` 必須以 `finally` 等同語意確保 `aclose()` 執行；即使 Redis 操作或
  caller code 發生例外也不可跳過釋放。
- 若 caller code 與 `aclose()` 同時失敗，必須保留 caller 原始例外並附帶 close
  failure context；若只有 `aclose()` 失敗，則向上傳遞 close failure。
- Connection error 不得包含含密碼的完整 `REDIS_URL`。
- 不使用 `print()`；若本階段尚未建立 project logging configuration，僅由 caller
  處理 logging，不在 manager 中建立額外 framework。

### 5.6 Dependencies

`requirements.txt` 本階段只納入實作與驗證這兩項能力所需的依賴：

- `fastapi==0.141.1`：提供目前 framework 與 Pydantic integration。
- `redis==8.1.0`：提供 `redis.asyncio` client。
- `pytest`：unit test。
- `pytest-asyncio`：async Redis connection unit test。

不加入 PyJWT、cryptography 或其他 authentication dependency。

## VI. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implentation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| TASK-001 | Authorization Base Objects | ADD | 2026-09-17 | DONE | 2026-09-18 | 2026-09-18 |
| TASK-002 | Redis Settings and Dependencies | ADD | 2026-09-17 | DONE | 2026-09-18 | 2026-09-18 |
| TASK-003 | Async Redis Connection | ADD | 2026-09-17 | DONE | 2026-09-18 | 2026-09-18 |

## VII. Implementation Steps

### TASK-001 Authorization Base Objects

```text
File:
- src/models/schemas/authorization.py
- tests/models/schemas/test_authorization.py

Target:
- AuthorizationObject
- AuthorizationBody
- AuthorizationEnvelope

Plan Type: ADD
Reuse: Pydantic supplied by FastAPI
Impact: Establishes the common JSON body object shape only

Current Behavior:
No request/response objects exist.

Expected Behavior:
The application can validate and serialize the exact header/body.auth/body.info JSON
structure. Optional Authorization fields default to None; header, auth and info safely
default to independent empty objects.

Implementation:
- Define the three Pydantic models described in section 5.1.
- Use lowercase snake_case field names matching the JSON contract.
- Use Field(default_factory=...) for nested objects and dictionaries.
- Forbid extra fields only on AuthorizationObject.
- Do not add JWT/Bearer validation, aliases, endpoint rules or Redis calls.

Error Handling:
Wrong top-level/nested types produce normal Pydantic validation errors. No application
error mapping is added in this task.

Testing:
- Empty envelope serializes to header/body/auth/info structure.
- Each Authorization field accepts string or None.
- Invalid scalar/object types fail validation.
- Unknown Authorization field fails validation.
- Dynamic header/info content is preserved.
- Separate instances do not share mutable defaults.
```

### TASK-002 Redis Settings and Dependencies

```text
File:
- requirements.txt
- src/config/settings.py
- tests/config/test_settings.py

Target:
- REDIS_URL setting

Plan Type: ADD
Reuse: os.getenv() required by project instructions
Impact: Defines the Redis environment contract and required packages

Current Behavior:
No requirements file or configuration module exists.

Expected Behavior:
Redis connection configuration comes from REDIS_URL, with a local-development default that
can be overridden in Docker and production.

Implementation:
- Add only the dependencies listed in section 5.6.
- Read REDIS_URL using os.getenv with redis://localhost:6379/0 default.
- Keep Redis URL construction in settings, not scattered across callers.
- Do not add JWT, APP_ENV or TTL settings.

Error Handling:
Reject an empty REDIS_URL before creating a client. Do not include credential-bearing URLs
in validation errors.

Testing:
- Default REDIS_URL.
- Environment override.
- Empty value rejection.
- No credential value appears in errors.
```

### TASK-003 Async Redis Connection

```text
File:
- src/config/redis.py
- tests/config/test_redis.py

Target:
- RedisConnectionManager
- __aenter__()
- __aexit__()
- connect()
- get_client()
- close()

Plan Type: ADD
Reuse: Settings.REDIS_URL and redis.asyncio.Redis
Impact: Provides connection infrastructure for a future Redis repository

Current Behavior:
No Redis client or connection lifecycle exists.

Expected Behavior:
One manager owns one async Redis client, verifies it with ping, exposes it only after a
successful connection, and guarantees client/pool closure through async context management.

Implementation:
- Construct client using Redis.from_url with decode_responses=True.
- Implement async context manager protocol; __aenter__ awaits connect and returns the
  connected client, while __aexit__ always awaits close and returns False/None so caller
  exceptions continue propagating.
- Await ping before marking the manager connected.
- Avoid duplicate client creation on repeated connect calls.
- Return the initialized client from get_client.
- Await aclose and clear the stored client in close.
- Make close safe when no client exists or after a previous close.
- Treat async with as the primary supported usage. Any direct connect call must be paired
  with await close in caller try...finally.
- Do not implement application lifespan wiring, Redis commands, key construction or TTL.

Error Handling:
- If ping fails, close the partially created client and preserve the original Redis error.
- If code inside async with raises, __aexit__ must still close the client and must not
  suppress or replace the original exception; a close-only failure must still propagate.
- If get_client is called before successful connect, raise a clear RuntimeError or a
  project-specific configuration error if one is introduced within this task.
- Never expose the full REDIS_URL.

Testing:
- from_url receives the configured URL and decode_responses=True.
- Successful ping enables get_client.
- Ping failure closes the partial client and leaves manager disconnected.
- Normal async with exit calls aclose exactly once.
- Exceptional async with exit calls aclose exactly once and propagates the original error.
- __aenter__ connection failure does not leave an open client/pool.
- Repeated connect does not create another client.
- get_client before connect fails.
- close calls aclose once, clears state and is idempotent.
```

## VIII. Impact Analysis

| Area | Impact | Details |
|---|---|---|
| API objects | ADD | Common JSON envelope and Authorization Object |
| Actual HTTP headers | NO CHANGE | No HTTP Authorization header handling |
| Redis | ADD | Connection only; no data operations |
| Configuration | ADD | REDIS_URL only |
| Dependencies | ADD | FastAPI, redis-py and test packages |
| Controller | NO CHANGE | Deferred |
| Service | NO CHANGE | Deferred |
| Repository | NO CHANGE | Deferred |
| PostgreSQL | NO CHANGE | No schema or migration |
| Other features | NO CHANGE | Not analyzed or modified in this phase |

## IX. Testing Strategy

- Object normal cases：empty/default and populated serialization。
- Object validation cases：wrong types、unknown Authorization fields。
- Object isolation：mutable defaults are not shared。
- Redis normal cases：connect、ping、get client、close。
- Redis lifecycle：normal/exceptional `async with` exit 都執行 `aclose()`。
- Redis error cases：ping failure、context entry failure、get before connect、repeated close。
- Redis boundary 使用 mock；unit tests 不依賴實際 Redis container 或執行順序。

## X. Open Questions

本階段沒有阻擋 Object 與 Redis connection 實作的 Open Question。

以下議題保留給後續細部需求與 Implementation Plan，不在本階段回答：

- `header` 與 endpoint-specific `info` 的正式 typed schema。
- Authorization request/response required fields。
- JWT、Bearer validation、Redis key/value/TTL behavior。
- Authentication environment policy、error contract 與 feature integration。

## XI. Plan Validation

- [x] Requirement Type 已確認為 New Requirement。
- [x] Scope 僅包含 base objects 與 Redis connection。
- [x] 所有 Implementation Step 有明確 File、Target、Behavior 與 Testing。
- [x] File placement 遵循 project architecture。
- [x] 沒有不必要的 Controller、Service、Repository 或 Database change。
- [x] 沒有加入 PyJWT 或其他超出範圍的 dependency。
- [x] Redis connection error handling 與 resource close 已定義。
- [x] Redis connection 優先使用 async context manager，正常與例外路徑皆保證
  `aclose()`。
- [x] Object validation 與 mutable default safety 已定義。
- [x] 未參考或修改其他 feature requirement。
- [x] Deferred Scope 已明確禁止提前實作。
- [x] Implementation Plan 已完成人工審核。

## XII. Review Status

- [x] Implementation Plan 已完成人工審核
- [x] Development 完成
- [x] Code Review 通過

```text
Current Handoff: None
Next Handoff: None
Implementation Scope: Authorization base objects and async Redis connection only
Do Not Implement: JWT, Redis token operations, authentication flow, feature integration
```
