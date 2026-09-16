# Project Architecture

## Overview

此文件簡單說明本專案的程式碼架構與各主要目錄的責任。*System Design*、*Programmer* 與 *Code Review Agent* 在進行設計、實作與審查時，應依照此架構決定程式碼分類與放置位置。


## Application Structure

```text
src/
├── main.py
├── config/
├── controllers/
├── services/
├── repositories/
├── models/
│   ├── bo/
│   ├── schemas/
│   └── po/
└── utils/
```

## Architecture Layers

```text
Client
  ↓
Controller
  ↓
Service
  ↓
Repository
  ↓
Database
```

主要 Dependency Direction：

```text
Controller → Service → Repository → Database
```

原則上不應建立反向依賴。


## Folder Responsibility

| Path | Responsibility | Example |
|---|---|---|
| `src/main.py` | Application Entry Point | 建立 FastAPI Application、註冊 Controller |
| `src/config/` | Application Configuration | Settings、Environment Configuration |
| `src/controllers/` | API / HTTP Entry Layer | Request、Response、呼叫 Service |
| `src/services/` | Business Logic Layer | Business Rule、Application Workflow |
| `src/repositories/` | Data Access Layer | Database Query、CRUD、Persistence |
| `src/models/bo/` | Business Object | `UserBO`、`OrderBO` |
| `src/models/po/` | Persistence Object | ORM Model、Database Table Mapping |
| `src/models/schemas/` | API Data Schema | Request、Response、Validation Schema |
| `src/utils/` | Shared Utility | Parser、Formatter、Converter |


## Model Classification

### BO(Business Object)

Path: `src/models/bo/`，用於表達 Business Layer 所使用的資料。

### PO(Persistence Object)

Path: `src/models/po/` 用於 Database / ORM Mapping。

### Schema(API Data Schema)

Path: `src/models/schemas/` 用於 API Request、Response 與資料驗證。



## Basic Data Flow

```text
Request
  ↓
Schema
  ↓
Controller
  ↓
Service
  ↓
Repository
  ↓
PO
  ↓
Database
```

Response 則依相反方向返回。


## Tests

測試目錄原則上對應 Production Code：

```text
src/controllers/   → tests/controllers/
src/services/      → tests/services/
src/repositories/  → tests/repositories/
src/models/        → tests/models/
src/schemas/       → tests/schemas/
src/utils/         → tests/utils/
```

## Architecture Rule

建立或修改程式碼時，應先依 Responsibility 判斷放置位置。

```text
HTTP / API
→ controllers

Business Logic
→ services

Database Access
→ repositories

Business Object
→ models/bo

Persistence Object
→ models/po

Request / Response
→ schemas

Shared Utility
→ utils
```

如果現有架構無法滿足 Requirement，應由 *System Design Agent* 先與相關人員確認是否需要調整 Project Architecture。*Programmer* 不應自行新增新的 Architecture Layer。
