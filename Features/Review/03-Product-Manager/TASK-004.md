# TASK-004 Code Review

Status: OPEN

## Review Result

- P2: The planned `LabelCacheRepository` is absent.

## Existing Implementation

`ProductCacheRepository` stores both `products:info` and `product:labels`,
and also owns both lock keys.

## Review Issue

The implementation plan defines separate product and label cache repositories.
Keeping both cache contracts in one repository makes the product cache class
responsible for unrelated label loading, normalization and locking.

## Expected Behavior

Provide `LabelCacheRepository` for `product:labels` load, replace,
invalidation and label locking. Keep product snapshot serialization and its
lock in `ProductCacheRepository`.

## Suggested Area To Fix

Extract the label methods and lock into `label_cache_repository.py`, inject it
into `ProductService`, and add lock ownership and cache-reload tests.

## Resolution

```text
Status: OPEN
```
