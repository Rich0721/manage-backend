# Authorization Header Contract Change Implementation Plan

## I. Requirement Information and Status

```text
Plan Status: Awaiting Review
Plan Date: 2026-10-01
Requirement Type: Requirement Change
Requirement Source: Features/Document/01-Authorization.md；使用者 2026-10-01 指示
Requirement Summary: 將客製化授權資訊放在封套的 header，不再使用 body.auth。
Implementation Gate: 待本計畫審核；本次僅調整計畫。
```

本計畫是已完成的 `01-Authorization`、`02-User-Manager`、`03-Product-Manager` 計畫之公開封套契約修訂。這三份計畫中關於 `body.auth` 的描述以本計畫為準，原本已完成的 Redis、JWT、資料庫與業務功能紀錄保留。`Features/Document/02-User-Manager.md` 仍寫 `body.auth`，與本次使用者指示衝突；需求文件由 PM 管理，本計畫不修改該文件。

## II. Requirement Delta

| 項目 | 原計畫／現況 | 本次要求 | 影響 |
|---|---|---|---|
| JSON 封套 | `header: {}`；`body.auth` 放 status/message/uid/authorization；`body.info` 放業務資料 | `header` 放 `Status`、`Message`、`Uid`、`Authorization`；`body` 僅有 `info` | MODIFY：共用與各 endpoint schema |
| User Manager protected request | 從 JSON `body.auth` 驗證 | 從 JSON `header` 取 Uid/Authorization | MODIFY：controller 邊界 |
| Product Manager protected request | 從實際 HTTP `uid`／`Authorization` headers 驗證 | 保留此已確認來源；JSON body 不再定義 `auth` | MODIFY：封套；授權來源 NO CHANGE |
| 成功／錯誤 response | 狀態及授權放 `body.auth`；有 token 時同步 HTTP `Authorization` header | 狀態及授權放 JSON `header`；保留 HTTP token 同步 | MODIFY：共用 builder、錯誤封套 |
| JWT／Redis／權限／產品規則 | 已實作 | 維持 | NO CHANGE |

## III. Technology Context and System Design

- Python 3.14、FastAPI 0.141.1、Pydantic、pytest；PostgreSQL 17、Redis Server 8.10.1／redis-py 8.1.0。依 `instructions/architecture.md`，schema 管資料形狀，controller 管 HTTP 邊界，既有 `AuthorizationService` 管 JWT／Redis 驗證。
- JSON 契約以 `Features/Document/01-Authorization.md` 範例為準：

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

- 四個客製化 key 對外使用範例所示大小寫。內部可保留 snake_case 屬性，以 Pydantic alias 序列化。沒有值時依需求範例輸出空字串；不能把空值視為有效授權。`header` 可有其他需求允許的資訊，但只有這四欄參與本次授權／狀態契約。
- `body` 僅包含 `info`；endpoint 原有 typed info 與 HTTP status、公開訊息不變。Register/login 不要求既有 token；logout/getUsers/updatePermission 從 JSON `header` 取 Uid/Authorization，交現有 service 驗證。
- JSON `header` 與實際 HTTP headers 是不同載體。Product Manager 仍以實際 HTTP `uid`／`Authorization` request headers 為授權來源，不接受 JSON `header` 或舊 `body.auth` 覆寫已驗證身分。Response 有 token 時，實際 HTTP `Authorization` header 與 JSON `header.Authorization` 相同。需求未明確要求 `Status`／`Message`／`Uid` 也複寫到實際 HTTP response headers，本次不新增。
- 全域 application、validation、unexpected error 仍使用共用錯誤 builder；`body.info.errors`、既有 4xx/5xx code、敏感資訊保護不變。
- 這是公開 JSON 契約變更：舊版 `body.auth` client 需改為 `header`。不設雙來源 fallback，避免兩處身分不一致。

## IV. Requirement List

| Task ID | Component Name | Plan Type | Plan Date | Implementation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| HDR-001 | Authorization base schema | MODIFY | 2026-10-01 | PLAN UPDATED |  |  |
| HDR-002 | User Manager envelope and authorization boundary | MODIFY | 2026-10-01 | TODO |  |  |
| HDR-003 | Product Manager envelope | MODIFY | 2026-10-01 | TODO |  |  |
| HDR-004 | Global error envelope and API regression | MODIFY | 2026-10-01 | TODO |  |  |

HDR-001 對應已完成的 `01-Authorization` TASK-001，因需求變更重設為 `PLAN UPDATED` 並清除舊開發／審查日期；其餘三項是本次新增工作。`01-Authorization` TASK-002/003 與 User／Product 的其他已完成業務任務不重設。

## V. Implementation Steps

### HDR-001 Authorization base schema

```text
File: src/models/schemas/authorization.py; tests/models/schemas/test_authorization.py
Target: AuthorizationObject, AuthorizationBody, AuthorizationEnvelope
Plan Type: MODIFY
Reuse: 現有 Pydantic models、Field(default_factory=...)
Current Behavior: AuthorizationObject 在 body.auth；header 是 dict；body 含 auth/info。
Expected Behavior: AuthorizationObject 是 JSON header 四欄模型；body 僅有 info。
Implementation: 四欄對外 alias 為 Status/Message/Uid/Authorization；調整空值與
  serialization；允許其他 header 資訊但不覆寫已知四欄；移除 AuthorizationBody.auth；
  AuthorizationEnvelope.header 使用共用模型，巢狀預設使用 default_factory。
Impact: 所有引用共用封套的 API schema。
Error Handling: 非物件 header/body、錯誤欄位型別產生 Pydantic validation error。
Testing: 空／完整封套、大小寫、額外 header、只有 body.info、非法型別、
  不輸出 body.auth、mutable default 隔離。
```

### HDR-002 User Manager envelope and authorization boundary

```text
File: src/models/schemas/user.py; src/controllers/user_controller.py;
      tests/models/schemas/test_user.py; tests/controllers/test_user_controller.py
Target: UserBody, UserEnvelope, typed request/response aliases, build_envelope(),
        build_error_envelope(), logout(), get_users(), update_permissions()
Plan Type: MODIFY
Reuse: AuthorizationObject、UserService、AuthorizationService 既有流程。
Current Behavior: UserBody.auth 承載授權；controller 傳 payload.body.auth 給 service；
  build_envelope() 將狀態與授權放 body.auth。
Expected Behavior: UserEnvelope.header 承載四欄；UserBody 僅有 info；protected
  requests 從 payload.header 取 Uid/Authorization；所有回應採新封套。
Implementation: 遷移 generic schema 與 typed aliases；controller 做邊界轉換並沿用
  現有 service；build_envelope() 建立 JSON header。有 token 時維持實際 HTTP
  Authorization response header 同步。register/login 不要求既有 token。
Impact: 五個 User Manager API 的 JSON request/response contract。
Error Handling: 沿用現有 HTTP code、ApplicationError 與 DEBUG/session 規則。
Testing: 各 API 成功／錯誤封套、protected request 僅取 JSON header、舊
  body.auth 不作授權來源、DEBUG 有／無 token、HTTP token 同步。
```

### HDR-003 Product Manager envelope

```text
File: src/models/schemas/product.py; src/controllers/product_controller.py;
      tests/models/schemas/test_product.py; tests/controllers/test_product_controller.py
Target: ProductBody, ProductEnvelope, typed request/response aliases, result_envelope()
Plan Type: MODIFY
Reuse: product_controller.header_auth()、AuthorizationService、
  user_controller.build_envelope()／synchronize_authorization_header()
Current Behavior: ProductBody.auth 存在；JSON response 的 body.auth 含狀態與 token；
  授權從實際 HTTP request headers 取得。
Expected Behavior: JSON response header 含四欄、body 僅含 info；實際 HTTP
  request headers 仍是產品授權來源。
Implementation: 移除 ProductBody.auth；調整 ProductEnvelope.header 為共用
  header 模型／相同 alias 序列化；四條 route 沿用 header_auth() 與 builder。
  JSON header/body.auth 不得覆寫 HTTP 授權身分。
Impact: 四個 Product Manager API 的 JSON 封套；HTTP 授權來源不變。
Error Handling: 保留產品專用 401／404／409 與既有 422／503 mapping。
Testing: 四條 route response、GET 不要求 body、HTTP uid/token 驗證、
  JSON header/body.auth 不覆寫身分、HTTP response token 同步。
```

### HDR-004 Global error envelope and API regression

```text
File: src/main.py; tests/test_main.py; tests/controllers/test_user_controller.py;
      tests/controllers/test_product_controller.py
Target: create_app() 的 application／validation／unexpected exception handlers
Plan Type: MODIFY
Reuse: build_error_envelope()、既有 ApplicationError hierarchy。
Current Behavior: 全域錯誤的狀態與訊息在 body.auth。
Expected Behavior: 全部公開錯誤回應以 JSON header 四欄與 body.info 表示；
  HTTP code、公開訊息與 info.errors 不變。
Implementation: 確認共用 builder 涵蓋三種 handler；只有必要時才修改 main；
  更新回歸測試與 OpenAPI response schema 斷言。
Impact: User Manager、Product Manager 與全域錯誤回應。
Error Handling: 不外洩原始例外、token、secret 或 DB/Redis credential。
Testing: 三種 handler、各 endpoint 2xx 與主要 4xx/5xx、無 body.auth、
  header casing、body.info 保持既有資料。
```

## VI. Impact, Validation and Handoff

| Area | Impact | Details |
|---|---|---|
| Public JSON API | MODIFY | User／Product request/response envelope；舊 client 需遷移 |
| Actual HTTP headers | LIMITED | 產品 request HTTP 授權與 response Authorization 同步保留 |
| Authorization service／JWT／Redis | NO CHANGE | token/session/DEBUG/TTL 邏輯沿用 |
| PostgreSQL／DDL | NO CHANGE | 無 migration |
| Configuration／Dependencies | NO CHANGE | 無新增設定或套件 |

- [x] 已核對需求範例、現有三份計畫、共用 schema、User／Product controller、全域錯誤處理與對應測試檔。
- [x] 已標示需求變更、API 相容性、每個 Task 的檔案、目標、錯誤與測試。
- [x] 未加入無關的資料庫、JWT、Redis 或產品規則變更。
- [ ] 待 PM／Reviewer 審核本次公開 JSON 契約變更。

Open Question：若 PM 要求 `Status`、`Message`、`Uid` 也出現在實際 HTTP response headers，須補充該契約。本計畫目前依需求 JSON 範例與既有 HTTP Authorization 同步行為執行。

Handoff：審核通過後交 Programmer 依 HDR-001～004 實作。只改公開封套與 HTTP 邊界；保留已完成的 Redis 連線、JWT/session、資料庫及產品業務規則。
