# TASK-011 Code Review

Status: RESOLVED

Review Fix Validation (2026-09-21): `.env.example` 已分別記錄 host-process 與 future
container-network URLs，失效指向已移除；最新 Plan 要求的 README 操作說明亦已完成。
Compose、真實 integration、credential isolation 與無 application table bootstrap 均驗證通過。

## Task ID

TASK-011

## Review Result

Code Review 未通過。Compose services、health checks、required credential interpolation、named
volumes、localhost port binding、真實 integration tests 與無 application table bootstrap 均已
驗證，但 environment template 尚未完成 Plan 定義的 container-network connection 資訊。

## Implementation Plan

- `.env.example` 必須提供 host-process connection 設定。
- 未來 application container 必須使用 `postgres` / `redis` service DNS，並將兩個
  container-network URL 分開記錄。
- `.env` 必須維持 ignored，且不得加入 production credentials。
- PostgreSQL/Redis Compose 必須可健康啟動，缺少必要 credential 時 config 必須 fail-fast。

## Existing Implementation

- `compose.yaml` 使用 `postgres:17` 與 `redis:8.10.1`，兩個服務皆為 healthy。
- `.env.example` 已包含 localhost host-process 與 integration URLs。
- `.gitignore` 正確忽略 `.env` 並保留 `.env.example`。
- 完整 regression 為 194 passed；真實 PostgreSQL/Redis integration 為 2 passed。
- PostgreSQL persistent schema 未建立 `tb_users`。

## Review Issue

1. **Container-network URL 缺失**：`.env.example:10-12` 只提供 localhost URLs，未記錄
   Plan 指定的 `postgresql://progresql:progresql@postgres:5432/progresql` 與
   `redis://:progresql@redis:6379/0`，因此 target 中的 container-network connection
   configuration 尚未完成。
2. **錯誤文件指向**：`.env.example:10` 宣稱 container URLs 已記錄於 `README.md`，但最新
   Plan 已移除 README scope，且目前 README 為空。此註解會讓使用者無法找到實際設定。

## Expected Behavior

Tracked environment template 應同時清楚區分 host-process 與 future container-network URLs，
不得指向不存在或不在最新 Plan scope 內的文件；localhost defaults 不得改成 service DNS。

## Suggested Area To Fix

- `.env.example`

## Resolution

```text
Status: RESOLVED
```

Code Review Agent 已完成修正驗證。
