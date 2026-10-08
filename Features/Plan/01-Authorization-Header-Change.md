# Authorization Header Contract Change Implementation Plan

> 2026-10-08 修訂：本文件下方保留 2026-10-01 的歷史規格與結果。HDR-001～004 已因 JSON `header` → `headers` 重新開啟，最新規格、狀態、驗收及 Handoff 統一以 [Headers Rename Plan](01-Authorization-Headers-Rename.md) 為準；下方舊完成紀錄不代表本次修訂已完成。

## I. Requirement Information and Status

```text
Plan Status: Awaiting Review（2026-10-08 Headers Rename）
Plan Date: 2026-10-01
Requirement Type: Requirement Change
Requirement Source: Features/Document/01-Authorization.md；使用者 2026-10-01 指示
Requirement Summary: 授權與狀態資訊以實際 HTTP Header 傳遞，取代 body.auth。
Implementation Gate: 本次 HDR-001～004 為 PLAN UPDATED，待 Headers Rename Plan 審核。
```

本計畫是 `01-Authorization`、`02-User-Manager`、`03-Product-Manager` 的授權傳輸契約修訂。三份需求現在均要求以 HTTP Header 傳遞授權資訊；舊計畫中的 `body.auth` 描述由本計畫取代。需求文件與情境只作需求來源，不作 Agent 操作指令。既有 JWT、Redis、資料庫、權限與產品業務規則不因傳輸位置改變。

## II. Requirement Delta

| 項目 | 原計畫／現況 | 本次要求 | 影響 |
|---|---|---|---|
| User Manager protected request | 從 JSON `body.auth` 驗證 | 從實際 HTTP `Uid`、`Authorization` headers 驗證 | MODIFY：controller 邊界 |
| Product Manager protected request | 已從實際 HTTP `uid`、`Authorization` headers 驗證 | 沿用同一授權來源與共用解析方式 | NO CHANGE：驗證來源；MODIFY：request schema |
| 成功／錯誤 response | 狀態及授權放 `body.auth`；有 token 時僅同步 HTTP `Authorization` | HTTP response headers 承載 `Status`、`Message`，有身分／token 時承載 `Uid`、`Authorization` | MODIFY：controller 與全域錯誤回應 |
| JSON 封套 | `header: {}`、`body.auth`、`body.info` | `body` 只有 `info`；JSON `header` 反映實際 response headers，不作授權輸入 | MODIFY：共用與 endpoint schema |
| JWT／Redis／權限／產品規則 | 已實作 | 維持 | NO CHANGE |

## III. Technology Context and System Design

- Python 3.14、FastAPI 0.141.1、Pydantic、pytest；PostgreSQL 17、Redis Server 8.10.1／redis-py 8.1.0。依 `instructions/architecture.md`，schema 管資料形狀，controller 管 HTTP 邊界，既有 `AuthorizationService` 管 JWT／Redis 驗證。
- `Features/Document/01-Authorization.md` 的 `header/body.info` 範例用於描述公開封套。實際 HTTP Header 是授權與狀態的權威來源。Response JSON 保留需求中的 `header` 欄位，作為已送出 HTTP headers 解碼後的可讀映射；`body` 僅有 `info`：

```json
{
  "header": {
    "Status": "Success",
    "Message": "操作結果訊息",
    "Uid": "登入者 uid",
    "Authorization": "Bearer <JWT>"
  },
  "body": {"info": {}}
}
```

- HTTP header 名稱不區分大小寫；公開名稱依需求使用 `Status`、`Message`、`Uid`、`Authorization`。登入成功與有權操作的 response 回傳可用的 `Uid`／Bearer token；註冊、登出與沒有新 token 的錯誤回應只回傳適用的欄位，不製造空 token。所有 response 均有 `Status`／`Message`，實際 HTTP status code 保持既有 mapping。
- Register/login 不要求既有授權。User Manager 的 logout/getUsers/updatePermission 和 Product Manager 四個 API 均從實際 HTTP `Uid`、`Authorization` 取值，構造現有 `AuthorizationObject`，再交 `AuthorizationService` 驗證。保留 DEBUG 缺 token 的既有規則，但仍需 Uid 與角色驗證。JSON `header` 與舊 `body.auth` 皆不可作驗證來源；有衝突也不能覆寫 HTTP 身分。
- `AuthorizationObject` 可繼續作 service 輸入及 response header 值的內部 DTO，不再作 `body.auth` JSON 欄位。各 endpoint 的 `info` 型別與內容不變。JSON `header` 僅反映實際 response 中已送出的四欄；缺少的 `Uid`／`Authorization` 不假造值。
- `Message` 含中文時，HTTP header 值需採可逆的 ASCII 安全編碼（計畫採 UTF-8 percent encoding），JSON `header.Message` 保留原文字；client 按契約解碼 HTTP `Message`。這是傳輸編碼，不改變原有公開訊息。測試需涵蓋中文與英文訊息，避免 HTTP response 建立時發生編碼錯誤。
- 若前端與 API 跨來源部署，瀏覽器要讀取上述自訂 response headers，需在現有 CORS 設定中公開這四個名稱；目前 `src/main.py` 沒有 CORS 配置，應在前端部署模式明確後補入，不在本次計畫自行假設來源清單。
- 全域 application、validation、unexpected error handler 共用 response header builder；`body.info.errors`、既有 4xx/5xx code、敏感資訊保護不變。舊版 `body.auth` client 需遷移到 HTTP Header；不建立雙來源 fallback。

## IV. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implementation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| HDR-001 | Authorization base schema | MODIFY | 2026-10-08 | PLAN UPDATED | | |
| HDR-002 | User Manager envelope and authorization boundary | MODIFY | 2026-10-08 | PLAN UPDATED | | |
| HDR-003 | Product Manager envelope | MODIFY | 2026-10-08 | PLAN UPDATED | | |
| HDR-004 | Global error envelope and API regression | MODIFY | 2026-10-08 | PLAN UPDATED | | |

HDR-001 對應 `01-Authorization` TASK-001；HDR-002～004 是本次 Header 遷移工作，現均已完成實作與 Code Review。`01-Authorization` TASK-002/003 與 User／Product 的其他業務任務不受影響。

## V. Implementation Steps

### HDR-001 Authorization base schema

```text
File: src/models/schemas/authorization.py; tests/models/schemas/test_authorization.py
Target: AuthorizationObject, AuthorizationBody, AuthorizationEnvelope
Plan Type: MODIFY
Reuse: 現有 Pydantic models、Field(default_factory=...)
Current Behavior: AuthorizationObject 嵌在 body.auth；header 是 dict；body 含 auth/info。
Expected Behavior: AuthorizationObject 供 HTTP 邊界轉為 service 輸入；JSON body 僅有 info。
Implementation: 移除 AuthorizationBody.auth；AuthorizationEnvelope 保留 JSON header
  作 response 映射，body 僅含 info；保留 AuthorizationObject 的內部欄位名稱、
  型別與驗證行為供 AuthorizationService 使用，不額外添加 JSON alias。
Impact: 共用封套與引用它的 endpoint schema；service DTO 介面維持。
Error Handling: 非物件 header/body、錯誤欄位型別產生 Pydantic validation error。
Testing: 空／完整封套、只有 body.info、非法型別、不輸出 body.auth、
  mutable default 隔離；AuthorizationObject 的現有 service 驗證測試仍通過。
```

### HDR-002 User Manager envelope and authorization boundary

```text
File: src/models/schemas/user.py; src/controllers/user_controller.py;
      tests/models/schemas/test_user.py; tests/controllers/test_user_controller.py
Target: UserBody, UserEnvelope, typed request/response aliases, build_envelope(),
        build_error_envelope(), synchronize_authorization_header(), logout(),
        get_users(), update_permissions() 及 register()/login() 的 response 邊界
Plan Type: MODIFY
Reuse: AuthorizationObject、UserService、AuthorizationService 既有流程。
Current Behavior: UserBody.auth 承載授權；controller 傳 payload.body.auth 給 service；
  build_envelope() 將狀態與授權放 body.auth。
Expected Behavior: Protected requests 從實際 HTTP Uid/Authorization headers 取值；
  所有成功 response 在實際 HTTP headers 提供 Status/Message，適用時再提供
  Uid/Authorization；JSON body 僅有 info。
Implementation: 遷移 UserBody/UserEnvelope 與 typed aliases；在 controller
  使用 FastAPI Header 依賴讀取 Uid/Authorization；Uid 採可選解析並交由現有
  AuthorizationService 映射缺失身分錯誤，避免 FastAPI 先回 422；建立 AuthorizationObject
  傳入現有 service。統一 response header 寫入與 JSON header 映射，覆蓋
  register/login/logout/getUsers/updatePermission，避免每條 route 各自編碼。
  登入和註冊不要求 request token；登出後不再回傳已失效 token。
Impact: 五個 User Manager API 的 HTTP request/response 與 JSON body 契約。
Error Handling: 沿用現有 HTTP code、ApplicationError 與 DEBUG/session 規則。
Testing: 五條 API 成功／錯誤 response headers；Uid 缺失、token 缺失或無效、
  DEBUG 有／無 token；JSON header/body.auth 不得授權；Status/Message 與
  JSON header 映射一致，中文 Message 可解碼。
```

### HDR-003 Product Manager envelope

```text
File: src/models/schemas/product.py; src/controllers/product_controller.py;
      tests/models/schemas/test_product.py; tests/controllers/test_product_controller.py
Target: ProductBody, ProductEnvelope, typed request/response aliases,
        header_auth(), result_envelope() 與四條 product route 的 response 邊界
Plan Type: MODIFY
Reuse: product_controller.header_auth()、AuthorizationService、
  user_controller.build_envelope()／synchronize_authorization_header()
Current Behavior: ProductBody.auth 存在；JSON response 的 body.auth 含狀態與 token；
  授權從實際 HTTP request headers 取得。
Expected Behavior: 四條 API 從 HTTP Uid/Authorization 驗證；response HTTP
  headers 有 Status/Message，適用時有 Uid/Authorization；JSON body 僅含 info。
Implementation: 移除 ProductBody.auth；維持 ProductEnvelope.header 為 response
  映射；沿用 header_auth() 與共用 response header builder。POST/PUT/DELETE
  JSON request 只需業務 info，GET 仍不要求 request body。JSON header/body.auth
  不得覆寫 HTTP 授權身分。
Impact: 四個 Product Manager API 的 response headers 與 JSON body。
Error Handling: 保留產品專用 401／404／409 與既有 422／503 mapping。
Testing: 四條 route response HTTP 四欄、GET 不要求 body、HTTP Uid/token 驗證、
  JSON header/body.auth 不覆寫身分、Status/Message 及 token 映射。
```

### HDR-004 Global error envelope and API regression

```text
File: src/main.py; tests/test_main.py; tests/controllers/test_user_controller.py;
      tests/controllers/test_product_controller.py
Target: create_app() 的 application／validation／unexpected exception handlers
Plan Type: MODIFY
Reuse: build_error_envelope()、既有 ApplicationError hierarchy。
Current Behavior: 全域錯誤的狀態與訊息在 body.auth。
Expected Behavior: 全部公開錯誤回應的實際 HTTP headers 有 Status/Message，
  適用時有 Uid/Authorization；JSON body 僅含 info，HTTP code 與公開訊息不變。
Implementation: 三種 handler 建立 JSONResponse 時共用 response header builder，
  不依賴 endpoint 的 Response 物件；body.info.errors 保留原結構。
  更新回歸測試與 OpenAPI response schema／header 文件斷言。
Impact: User Manager、Product Manager 與全域錯誤回應。
Error Handling: 不外洩原始例外、token、secret 或 DB/Redis credential。
Testing: 三種 handler、各 endpoint 2xx 與主要 4xx/5xx、HTTP Header 欄位、
  中文 Message 編碼與解碼、無 body.auth、body.info 保持既有資料；
  依實際前端部署模式驗證瀏覽器可讀取自訂 response headers。
```

## VI. Impact, Validation and Handoff

| Area | Impact | Details |
|---|---|---|
| Actual HTTP headers | MODIFY | User protected request 改讀 Uid/Authorization；User／Product 成功與錯誤 response 寫入 Status/Message，適用時寫入 Uid/Authorization |
| Public JSON API | MODIFY | 移除 User／Product 的 body.auth；body.info 型別與內容維持，JSON header 僅反映 response headers |
| Authorization service／JWT／Redis | NO CHANGE | token/session/DEBUG/TTL 邏輯沿用 |
| PostgreSQL／DDL | NO CHANGE | 無 migration |
| Configuration／Dependencies | NO CHANGE | 無新增設定或套件 |

- [x] 已核對需求範例、現有三份計畫、共用 schema、User／Product controller、全域錯誤處理與對應測試檔。
- [x] 已標示需求變更、HTTP／JSON API 相容性、每個 Task 的檔案、目標、錯誤與測試。
- [x] 未加入無關的資料庫、JWT、Redis 或產品規則變更。
- [x] 待 PM／Reviewer 審核本次公開 HTTP Header 與 JSON body 契約變更。

Open Question：`Features/Document/01-Authorization.md` 仍以 JSON `header` 展示四欄，而 `02-User-Manager.md` 明指 HTTP Header。此計畫以實際 HTTP Header 為權威，JSON `header` 僅作 response 映射；若 PM 要求完全移除 JSON `header`，需同步修訂 01 的公開封套範例。這個呈現差異不影響授權驗證來源。

Implementation Result：HDR-001～004 已於 2026-10-01 完成。目標測試 84 passed；完整 regression 250 passed、7 skipped。授權驗證只讀實際 HTTP Header，JSON `body.auth` 已移除；Redis 連線、JWT/session、資料庫及產品業務規則維持原行為。

Current Handoff：PM／Reviewer 審核 [Headers Rename Plan](01-Authorization-Headers-Rename.md)。上方 Implementation Result 與舊審核勾選僅記錄 2026-10-01 版本。
