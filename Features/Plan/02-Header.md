# 02-Header Implementation Plan

## I. Requirement Information

Feature Name: [02-Header.md](../Document/02-Header.md)

Related Requirement:

- [01-User-Manager.md](../Document/01-User-Manager.md)

```text
Requirement Source: Features/Document/02-Header.md
Requirement Date: 未提供
Plan Date: 2026-09-15
Requirement Type: New Requirement
Requirement Summary: 為所有 API 的 JSON header 建立共用 Object，並使
請求與回應採用一致的 header/body envelope。
```

## II. Requirement Analysis

### Functional Requirements

1. API 請求與回應均使用 JSON 格式的 `header` 物件。
2. 建立對應 Header Object，涵蓋 Content-Type、Accept、User-Agent、
   Status Code、Status、Message、Uid、Permission。
3. `Content-Type` 與 `Accept` 預設為 `application/json`。
4. Header Status 支援 200、400、401、403、404、500。
5. 登入後才可取得 Uid 與 Permission。

### Non-functional Requirements

1. Header Object 必須可由 FastAPI request schema 與 response schema
   共用，避免每個 controller 重複定義欄位。
2. 不新增第三方 dependency；現有 FastAPI 與 Pydantic 已可完成 Object
   validation 與 JSON serialization。
3. uid 與 Permission 的防偽不在本次需求範圍，且不得自行新增 token、
   session、signature 或加密機制。

## III. Existing System Analysis

```text
Confirmed source: main.py creates the FastAPI application and includes the
single src.routers.router instance.
Confirmed source: src/routers.py contains an empty APIRouter; no controller,
request schema, response schema, shared JSON envelope, or exception mapping
exists.
Confirmed dependency: FastAPI 0.141.1 is declared in pyproject.toml and
provides Pydantic-based request/response models.
Confirmed related plan: 01-User-Manager.md specifies JSON header/body
envelopes for its future controllers, but no implementation exists yet.
```

## IV. Requirement Information Validation

The following public API details are not defined. They prevent an executable
schema and must be confirmed by PM; this plan does not select defaults for them.

1. JSON key naming: the table uses `Content-Type`, `Status Code`, and `Uid`,
   while User Manager examples use lowercase `content-type`, `status`, and
   `uid`. Define the canonical JSON keys and whether aliases are accepted.
2. Direction and requiredness: define which fields are required, optional, or
   forbidden for request headers and response headers. In particular, Status
   Code, Status, and Message appear response-specific, while User-Agent appears
   request-specific.
3. Status representation: define whether Status Code appears in the JSON
   header, the actual HTTP status, or both, and how mismatched values are
   handled. Define allowed Status values and their casing.
4. Uid and Permission lifecycle: define which successful login response returns
   these values, whether they are returned by registration, and which later
   request types must include them. The current User Manager requirement only
   uses `header.uid` for its interim protected-operation lookup.
5. Envelope rules: define whether `header` and `body` must always be present,
   whether an empty body is `{}` or may be omitted, and the response body type
   for errors.

## V. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implentation Status | Development Date | Code Review Date |
| --- | --- | --- | --- | --- | --- | --- |
| TASK-001 | Shared Header Request and Response Objects | ADD | 2026-09-15 | DOUBLE CHECK |  |  |
| TASK-002 | Shared JSON Envelope Response Builder | ADD | 2026-09-15 | DOUBLE CHECK |  |  |
| TASK-003 | User Manager Header Contract Integration | MODIFY | 2026-09-15 | DOUBLE CHECK |  |  |
| TASK-004 | Header Contract Test Suite | ADD | 2026-09-15 | DOUBLE CHECK |  |  |

## VI. Technical Stack

- Python: 3.14
- Framework: FastAPI 0.141.1
- Schema validation: Pydantic supplied by FastAPI
- Database: No change
- Other Dependencies: No new dependency

## VII. System Design

```text
Incoming JSON envelope
    -> controller request schema
    -> shared Header request object + feature body object
    -> service
    -> controller result mapping
    -> shared response builder
    -> JSON envelope with Header response object
```

- Header Object owns field validation, defaults, and JSON key aliases only.
- Controllers own parsing the feature-specific body, invoking services, and
  selecting the confirmed HTTP and JSON response status.
- Services must not depend on FastAPI or Header Object types.
- The shared response builder owns envelope construction only; it must not
  implement business errors, authorization, or uid/Permission forgery controls.
- Existing User Manager endpoint-specific success and failure messages remain
  the source of truth for that feature. This Header plan does not replace them.

## VIII. Implementation Steps

### TASK-001 Shared Header Request and Response Objects

```text
File: src/objects/header.py (New File)
Target: Header request and response Pydantic models
Plan Type: ADD

Reuse: FastAPI's installed Pydantic integration and src/objects/ package.

Current Behavior: No shared Header Object or JSON envelope schema exists.

Expected Behavior: Controllers can parse the PM-confirmed request header fields
and serialize the PM-confirmed response header fields consistently.

Implementation:
1. Create separate request and response models after PM confirms direction,
   requiredness, canonical key names, and aliases.
2. Set Content-Type and Accept defaults to application/json only when PM
   confirms their JSON names and response behavior.
3. Model Uid and Permission as optional fields until the related feature
   requires them; do not add anti-forgery validation.
4. Restrict response status values and codes only to the PM-confirmed mapping.

Error Handling: Schema validation errors must use the confirmed common error
envelope. Do not silently coerce unsupported header values.

Testing: Cover default values, required/optional fields, canonical keys,
aliases if approved, and invalid field values.
```

### TASK-002 Shared JSON Envelope Response Builder

```text
File: src/controllers/header_response.py (New File)
Target: response-envelope builder
Plan Type: ADD

Reuse: Header response Object from TASK-001 and FastAPI response support.

Current Behavior: No controller or shared response construction exists.

Expected Behavior: Controllers can produce a JSON object containing the
confirmed header and body shape while preserving the selected HTTP status.

Implementation:
1. Build one narrow helper that accepts a validated Header response Object and
   the feature response body.
2. Serialize the JSON envelope with the PM-confirmed empty-body rule.
3. Preserve the controller-selected HTTP status and include JSON Status Code
   only when PM confirms it is required.

Impact: Future controllers in 01-User-Manager.md use this builder; no service,
repository, database, Redis, SMTP, or configuration change is required.

Error Handling: Do not mask controller/service failures. The controller maps
each failure to the PM-confirmed status and message before calling the builder.

Testing: Verify success and error envelope serialization and HTTP/JSON status
consistency after PM defines the status rule.
```

### TASK-003 User Manager Header Contract Integration

```text
File: Features/Plan/01-User-Manager.md (Existing File)
Target: TASK-004 through TASK-008 controller specifications
Plan Type: MODIFY

File: src/controllers/user_registration_controller.py (Planned in
01-User-Manager TASK-004)
Target: request and response envelope usage
Plan Type: MODIFY

File: src/controllers/user_login_controller.py (Planned in
01-User-Manager TASK-005)
Target: request and response envelope usage
Plan Type: MODIFY

File: src/controllers/user_logout_controller.py (Planned in
01-User-Manager TASK-007)
Target: request and response envelope usage
Plan Type: MODIFY

File: src/controllers/user_permission_controller.py (Planned in
01-User-Manager TASK-008)
Target: request and response envelope usage
Plan Type: MODIFY

Reuse: TASK-001 models, TASK-002 response builder, and endpoint-specific
messages/statuses in 01-User-Manager.md.

Current Behavior: User Manager has a planned JSON envelope but no controller
implementation or common Header Object.

Expected Behavior: Every User Manager request and response follows the
PM-confirmed common Header contract, while retaining its documented endpoint
body, HTTP status, status, and message values.

Implementation:
1. Replace endpoint-local Header definitions with TASK-001 models.
2. Use TASK-002 to construct every endpoint response.
3. For logout, getUsers, and updatePermission, retain the approved interim
header.uid account lookup in 01-User-Manager TASK-007 and TASK-008.
4. Ignore client-provided Permission during authorization; use the role loaded
from TB_USERS as already planned.

Testing: Update User Manager controller tests only after TASK-004 confirms the
global contract; cover each endpoint's documented header/body envelope.
```

### TASK-004 Header Contract Test Suite

```text
File: tests/controllers/test_header_contract.py (New File)
Target: shared Header Object and response-envelope tests
Plan Type: ADD

Reuse: TASK-001 and TASK-002.

Current Behavior: No API header contract tests exist.

Expected Behavior: Tests prevent incompatible header field names, defaults,
requiredness, envelope shapes, and HTTP/JSON status behavior from regressing.

Implementation:
1. Add request model validation tests for each confirmed request field.
2. Add response serialization tests for every confirmed response field and
status code.
3. Add controller integration tests after TASK-003 for one success and one
failure response per User Manager endpoint.

Error Handling: Assert the PM-confirmed validation-error response envelope; do
not assert an error contract before PM defines it.

Testing: Run this focused test module, then the User Manager controller tests.
```

## IX. Impact Analysis

- API: ADD common JSON Header Object and envelope behavior. All future API
  controllers must adopt the confirmed contract.
- Database: NO CHANGE.
- Configuration: NO CHANGE.
- Dependencies: NO CHANGE.
- External Integration: NO CHANGE.
- Backward Compatibility: No implemented public API exists. Once endpoints are
  released, changing canonical JSON key names or field requiredness is a
  breaking API change.
- Security: UID and Permission forgery prevention is explicitly deferred. This
  plan must not claim that JSON header fields are HTTP transport headers or
  that they prove an authenticated identity.

## X. Plan Validation

- [x] Requirement type identified as New Requirement.
- [x] Existing FastAPI composition root, router, dependencies, tests, and
  related User Manager plan reviewed.
- [x] Reusable FastAPI/Pydantic schema support identified.
- [x] Database, configuration, dependency, compatibility, and security impacts
  recorded.
- [x] No production code, test code, or PM requirement document was changed.
- [ ] PM has defined canonical JSON keys, request/response requiredness, status
  representation, Uid/Permission lifecycle, and envelope rules.
- [x] Implementation Plan has completed human review.

## XI. Review Status

- [x] Implementation Plan 已完成人工審核
- [ ] Development 完成
- [ ] Code Review 通過

Plan Status: Awaiting PM Clarification and Review