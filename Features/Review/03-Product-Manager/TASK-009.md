# TASK-009 Code Review

Status: OPEN

## Review Result

- P1: Required product repository and workflow coverage is missing.
- P1: The full regression suite does not pass.

## Existing Implementation

The added tests cover schema validation, one cache round trip, add-label
resolution, soft-deleted single lookup, a controller header case and DDL.

## Review Issue

The plan requires repository tests, label-cache tests and API/service coverage
for add, get, update and delete. The current suite has no tests for product
repository SQL, duplicate-ID mapping, update/delete row-count behavior, cache
lock release, cache rebuild failures after database commit, missing-label
reload failure, update, delete, or all-role CRUD behavior.

`python -m pytest -q` currently reports `181 passed, 23 failed, 4 skipped`.
The 23 failures are in existing User Manager permission tests: they send the
documented `Permission` field while `PermissionUpdateItem` currently accepts
only `permission`. This is outside the new product code, but prevents the
plan's required regression gate from passing.

## Expected Behavior

Add the plan-required product tests and establish a passing regression suite,
or record and resolve the existing User Manager contract failure through its
own work item before marking this task complete.

## Suggested Area To Fix

Add focused unit tests for repositories and cache locks, service tests for all
CRUD/error/cache paths, and controller tests for every route and response
status. Resolve or separately track the User Manager `Permission` contract so
the full test command passes.

## Resolution

```text
Status: OPEN
```
