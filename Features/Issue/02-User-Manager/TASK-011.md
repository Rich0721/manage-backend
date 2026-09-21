# TASK-011 Implementation Issue

Status: RESOLVED

## Task ID

TASK-011

## Issue

Implementation Plan 指定的 official Docker image `redis:8.1.0` 無法由 Docker Hub
registry resolve。

## Existing Behavior

`docker compose config --quiet` 成功，但執行
`docker compose up -d --wait postgres redis` 時，Docker daemon 回傳：

```text
failed to resolve reference "docker.io/library/redis:8.1.0":
docker.io/library/redis:8.1.0: not found
```

因此 Redis container 未建立，PostgreSQL/Redis integration validation 無法繼續。

## Plan Definition

Implementation Plan section 7.10 與 TASK-011 指定 Redis service 必須使用 exact image
`redis:8.1.0`，且兩個 services 均健康後才能完成 TASK-011。

## Why Implementation Cannot Continue

Programmer 不得自行將 Plan 指定版本替換成其他 tag。必須先由 System Design 確認
Project Instruction 中的 `Redis 8.1.0` 是 server version、client dependency version，
或應改採哪一個實際存在且相容的 official Redis image。

## Suggested Area To Review

- Redis official image 可用 stable tag。
- `instructions/project.md` 的 Redis server version 與 `requirements.txt` 中
  `redis==8.1.0` Python client version 是否被混用。
- Implementation Plan section 6.1、7.9、7.10、TASK-011 及 integration version assertion。

## Resolution

官方 Docker image 清單確認 `redis:8.1.0` 不存在；`requirements.txt` 的
`redis==8.1.0` 是 Python client，而非 Redis server。System Design 已將 Project
Instruction 與 Implementation Plan 明確拆分為：

- Redis Server：official image `redis:8.10.1`。
- Redis Python Client：`redis==8.1.0`，維持不變。
- Integration version assertion：維持驗證 Redis major version 8，並由 Compose image
  pin 確保實際 server artifact 為 8.10.1。

TASK-011 更新為 `PLAN UPDATED`，Programmer 可依修正版 Plan 繼續實作。
