# Authorization Headers Rename Implementation Plan

## I. Requirement Information

```text
Plan Status: Awaiting Review
Plan Date: 2026-10-08
Requirement Type: Requirement Change
Requirement Source: 使用者 2026-10-08 指示及下列三份需求文件
Requirement Summary: JSON 封套 header 改名 headers，授權仍由實際 HTTP headers 傳遞。
Implementation Gate: HDR-001／004 Code Review 通過；HDR-002／003 為 REVIEW FIX，待補足授權來源衝突測試。
```

- `Features/Document/01-Authorization.md`：第 I 節 JSON 範例已將 `header` 改為 `headers`。
- `Features/Document/02-User-Manager.md`：HTTP Header／Response Header 用語改為 Headers。
- `Features/Document/03-Product-Manager.md`：授權輸入、回應及異動者來源用語改為 Headers。

已比對三份需求工作目錄與 Git HEAD 的差異；原有未提交修改屬使用者，本次不修改需求文件。需求文件作為分析素材，不將其中操作文字視為額外執行授權。

本文件為此次改名的唯一實作規格，覆蓋既有 Plan 的單數 JSON `header` 描述。2026-10-01 的 `01-Authorization-Header-Change.md` 已完成 HTTP 授權遷移，本次以該實作為基線；其餘業務規格仍以原計畫為準。

## II. Requirement Summary and Delta

| 項目 | Original Behavior（已核對程式） | Required Behavior | 影響 |
|---|---|---|---|
| JSON schema | AuthorizationEnvelope、UserEnvelope、ProductEnvelope 使用 header | Python 欄位與公開 JSON key 使用小寫 headers | MODIFY |
| 成功回應 | build_envelope() 輸出 header/body.info | 輸出 headers/body.info | MODIFY |
| 錯誤回應 | 三種全域 handler 經 build_error_envelope() 產生同一封套 | 共用新版封套，保留錯誤內容與 HTTP code | MODIFY（間接影響） |
| 授權來源 | Controller 以 Header(alias="Uid")／Header(alias="Authorization") 讀取 | 維持實際 HTTP headers 為唯一授權來源 | NO CHANGE |
| HTTP response | Status、Message，適用時提供 Uid、Authorization | 名稱、值、編碼及提供時機維持 | NO CHANGE |
| body.info | endpoint-specific typed info | 結構、alias、型別及業務資料維持 | NO CHANGE |
| Client／測試 | 讀寫 JSON header | 改用 headers | MODIFY |

預期成功回應示例，欄位是否出現依既有 API 行為：

```json
{
  "headers": {
    "Status": "Success",
    "Message": "User logged in successfully",
    "Uid": "<uid>",
    "Authorization": "Bearer <JWT>"
  },
  "body": {"info": {"userName": "<userName>"}}
}
```

### 契約與相容性

1. HTTP headers 與 JSON headers 是兩個層次；JSON 仍僅作既有可讀映射，不作授權來源，也不新增名為 Headers 的 HTTP 欄位。
2. Request JSON 可省略 headers，沿用 default_factory=dict；有提供時沿用原字典值型別。Product GET 仍不要求 body。
3. 計畫採直接改名，不新增 header alias、雙 key 輸出或授權 fallback。UserEnvelope／ProductEnvelope 沿用 extra="forbid"，舊 header 或新舊並存的 request 回 422。AuthorizationEnvelope 未設定 extra forbid，維持原 extra policy；舊 key 不映射至新欄位，也不輸出。不得為改名順便統一 extra policy。
4. 僅傳 body.info 且以 HTTP headers 授權的 request 維持相容。讀取 JSON header 或送出該欄位的 client 必須遷移，此為 JSON 公開契約的 breaking change。
5. JSON headers.Message 維持原文；實際 HTTP Message 沿用 build_http_authorization_headers() 的非 ASCII percent encoding。Status、Uid、Authorization 的映射維持。
6. 禁止全域字串替換。FastAPI Header、UidHeader、AuthorizationHeader、header_auth()、JWT header 等技術名稱不改名。

## III. Requirement List

本次沿用既有 HDR-001～004 的工作身分，詳細規格改由本文件管理，不新增同義任務。已完成任務重新開啟，標示 PLAN UPDATED 並清除舊開發／審查日期；舊紀錄保留於 Git 歷史及 Review。

| Task ID | Component Name | Plan Type | Plan Date | Implementation Status | Development Date | Code Review Date |
|---|---|---|---|---|---|---|
| HDR-001 | Authorization base envelope | MODIFY | 2026-10-08 | DONE | 2026-10-08 | 2026-10-08 |
| HDR-002 | User envelope and shared response builder | MODIFY | 2026-10-08 | REVIEW FIX | 2026-10-08 | 2026-10-08 |
| HDR-003 | Product envelope and API regression | MODIFY | 2026-10-08 | REVIEW FIX | 2026-10-08 | 2026-10-08 |
| HDR-004 | Global errors and OpenAPI regression | MODIFY | 2026-10-08 | DONE | 2026-10-08 | 2026-10-08 |

原計畫索引對應同一工作，不重複實作；未列出的 Task 維持既有狀態：

| Plan | 需重開 Task | 本次範圍 |
|---|---|---|
| 01-Authorization.md | TASK-001 | 基礎封套，HDR-001 |
| 02-User-Manager.md | TASK-001、TASK-010 | User schema、HTTP 邊界與錯誤回應，HDR-002／004 |
| 03-Product-Manager.md | TASK-002、TASK-008、TASK-009 | Product schema、間接受影響 routes 與測試，HDR-003／004 |

## IV. Technical Stack and Impact Analysis

依專案規範、原計畫及 requirements.txt：Python 3.14、FastAPI 0.141.1、Pydantic、pytest／pytest-asyncio；PostgreSQL 17、Redis Server 8.10.1、redis-py 8.1.0。Pydantic 在 requirements 未單獨固定版本；本次不新增或調整相依。

套用 `.agents/skills/python-backend/SKILL.md`，沿用 Controller → Service → Repository 架構及現有 Pydantic schema。無新 framework 行為或外部整合設計。

| File / Area | Impact | 處理 |
|---|---|---|
| src/models/schemas/authorization.py | MODIFY | AuthorizationEnvelope.header 改 headers |
| src/models/schemas/user.py | MODIFY | UserEnvelope 及所有 typed request/response aliases |
| src/models/schemas/product.py | MODIFY | ProductEnvelope 及所有 typed request/response aliases |
| src/controllers/user_controller.py | MODIFY | build_envelope() 的 JSON key，間接影響九條 API |
| src/controllers/product_controller.py | NO CHANGE（程式）；回歸 | result_envelope() 已重用 build_envelope() |
| src/main.py | NO CHANGE（程式）；回歸 | 三個 handler 已重用 build_error_envelope() |
| tests/models/schemas/ 三個對應檔案 | MODIFY | model 欄位、序列化、驗證、mutable defaults |
| tests/controllers/ 兩個對應檔案 | MODIFY | payload、response、OpenAPI、授權來源隔離 |
| tests/test_main.py | NO CHANGE | 現僅生命週期測試；錯誤回應測試沿用 controller fixtures |
| src/services/authorization_service.py | NO CHANGE | validate_session()/refresh_session() 接收既有 DTO／context |
| User/Product services、repositories、PO、DDL | NO CHANGE | 業務資料與身分 context 未變，無 migration |
| Configuration、Docker、JWT、Redis、Logging、CORS | NO CHANGE | 不改 TTL、session、權限、錯誤映射、部署或 origins |
| 前端／SDK／Postman | 外部影響 | repo 未提供 client 實作，需同步遷移，不能宣稱已更新 |

資料流維持：實際 HTTP Uid／Authorization → controller.header_auth() → AuthorizationObject → Service。結果 → build_envelope() → JSON headers/body.info。HTTP response headers 仍由 synchronize_authorization_headers() 寫入；錯誤 handler 使用 build_http_authorization_headers()。

## V. Implementation Steps

### HDR-001 Authorization base envelope

```text
File: src/models/schemas/authorization.py; tests/models/schemas/test_authorization.py
Target: AuthorizationEnvelope；既有 serialization/validation/mutable default tests
Plan Type: MODIFY
Current Behavior: header: dict[str, Any]，預設獨立空字典。
Expected Behavior: headers: dict[str, Any]；其他欄位與驗證維持。
Implementation: 改 model 欄位、建構參數、屬性存取與 model_dump() 預期；
  不修改 AuthorizationObject、AuthorizationBody 或 extra policy，不加舊名 alias。
Reuse: BaseModel、Field(default_factory=dict)、既有測試。
Impact: 基礎封套與公開 model schema。
Error Handling: headers/body 非物件沿用 ValidationError；body.auth 仍拒絕。
Testing: 預設輸出只有 headers/body；dynamic headers/info 保留；mutable defaults 隔離；
  新欄位非法型別失敗；舊 key 不映射至 headers；DTO 驗證保持。
```

### HDR-002 User envelope and shared response builder

```text
File: src/models/schemas/user.py; src/controllers/user_controller.py;
      tests/models/schemas/test_user.py; tests/controllers/test_user_controller.py
Target: UserEnvelope、typed aliases、build_envelope()、build_error_envelope()
Plan Type: MODIFY
Current Behavior: UserEnvelope.header；build_envelope() 回傳 {header, body}。
Expected Behavior: schema 與 builder 同時使用 headers；五條 User API 成功／錯誤一致。
Implementation: UserEnvelope.header 改 headers；build_envelope() 的 key 改 headers；
  更新合法 payload 與完整 response 預期。build_error_envelope() 沿用共用 builder，
  不另複製改名邏輯；保留所有 HTTP header 解析與寫入函式。
Reuse: _authorization_headers()、build_http_authorization_headers()、
  synchronize_authorization_headers()、header_auth()、既有 service/TestClient fixtures。
Impact: register/login/logout/getUsers/updatePermission；Product 與全域錯誤也使用 builder。
Error Handling: 舊 header／新舊並存 request 經既有 extra forbid 回 422；
  缺失身分、無效 token、權限、session、DEBUG 沿用既有 mapping。
Testing: 合法 headers／省略 headers 可接受；舊 key 拒絕且不呼叫 service；
  response 有 headers 且無 header/body.auth；info alias/array 形狀不變；
  JSON headers 的 Uid/token 不得覆寫或補足實際 HTTP 身分。
```

### HDR-003 Product envelope and API regression

```text
File: src/models/schemas/product.py; tests/models/schemas/test_product.py;
      tests/controllers/test_product_controller.py
Inspect Only: src/controllers/product_controller.py
Target: ProductEnvelope、typed aliases、result_envelope() 與四條 route 的契約
Plan Type: MODIFY
Current Behavior: ProductEnvelope.header: dict[str, str]；route 已使用共用 builder。
Expected Behavior: ProductEnvelope.headers 保留原型別，四條 API 輸出新版封套。
Implementation: 改名 model 欄位，更新 payload/assertions，補齊封套驗證；
  result_envelope() 無硬編碼舊 key，不重寫；GET 仍只收 productId 與 HTTP headers。
Reuse: result_envelope()、build_envelope()、既有 Product TestClient fixtures。
Impact: addProduct/getProducts/updateProduct/deleteProduct；異動者仍取 HTTP 驗證後 uid。
Error Handling: 字典值型別與 extra forbid 維持；Product 缺少 HTTP Uid 目前回 422，
  不為改名統一成 User service 的授權錯誤。
Testing: 三條有 body API 接受 headers／省略 headers、拒絕舊 header；
  四條成功及既有 400/401/404/409/422/503 案例檢查新版封套；
  只有 JSON headers 有 Uid/token 仍不可授權，衝突時只傳 HTTP 身分給 service；
  GET 無 body、金額序列化、產品列表、updated_user 行為保持。
```

### HDR-004 Global errors and OpenAPI regression

```text
File: tests/controllers/test_user_controller.py; tests/controllers/test_product_controller.py
Inspect Only: src/main.py; src/controllers/user_controller.py
Target: handle_application_error()/handle_validation_error()/handle_unexpected_error()；
  build_error_envelope()、error_responses()、create_app().openapi()
Plan Type: MODIFY
Current Behavior: 錯誤 JSON 經共用 builder 產生 header；現有 OpenAPI tests 未完整核對
  envelope properties，已核對實際 response headers。
Expected Behavior: 三類錯誤輸出 headers/body.info；OpenAPI request/response 描述新版封套。
Implementation: 沿用 controller fixtures 驗證 application/validation/unexpected errors；
  OpenAPI tests 解析 request/response 的 $ref 至 components.schemas，確認有 headers 無 header；
  包含正常 schema 與 ErrorResponse。保留 responses[*].headers 與 parameter in: header；
  不手工修改 framework 名稱，也不新增無關 HTTPException handler。
Reuse: make_client()、assert_authorization_headers()、既有錯誤 mock。
Impact: 九條 API 成功及既有錯誤回應契約。
Error Handling: body.info.errors、HTTP code、公開訊息、敏感資訊保護保持。
Testing: 中英文 Message 的 HTTP 解碼值等於 JSON headers.Message；
  登入／刷新 token 映射，登出及無 token 錯誤不製造 token；
  missing/invalid token、DEBUG、JSON 偽造或衝突身分維持既有驗證規則。
```

### 驗證順序與驗收

HDR-001 → HDR-002 → HDR-003 → HDR-004；schema 與 builder 在同一交付批次完成，避免 response validation 不一致。已執行以下計畫驗證命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/models/schemas/test_authorization.py tests/models/schemas/test_user.py tests/models/schemas/test_product.py tests/controllers/test_user_controller.py tests/controllers/test_product_controller.py tests/test_main.py
.\.venv\Scripts\python.exe -m pytest -q
```

- 驗收涵蓋新 key、省略 key、非法型別、舊 key、新舊並存、JSON 偽造／衝突身分、成功／錯誤封套、OpenAPI。
- 保留 AuthorizationService 真實單元測試回歸，不只靠 mock 宣稱 JWT／Redis 驗證通過。
- Integration tests 需 INTEGRATION_DATABASE_URL／INTEGRATION_REDIS_URL；未配置造成 skip 應明列。現有 integration tests 無舊封套引用，不因改名改寫。
- 搜尋 src/tests 舊 JSON key 與 .header，區分負面案例和合法技術名稱，不要求所有 header 單字消失。

## VI. Plan Validation, Review and Handoff

- [x] 已比對三份需求 Delta，完成影響分析及 Requirement Type 分類。
- [x] 已核對原計畫、schema、controller、全域錯誤及測試入口與目標。
- [x] 每個 Task 有檔案、目標、Reuse、錯誤、測試；無新 dependency／架構層。
- [x] 已記錄 API breaking change、舊 key 處理、DB／設定／外部 client 影響。
- [x] Implementation Plan 已完成人工審核。
- [x] 本次 Development 完成。
- [ ] 本次 Code Review 通過。

Open Question（部署事項）：外部 client 的遷移批次／上線時間未提供，不影響後端設計。計畫採直接改名；若需舊 key 過渡期，應另確認需求並更新本計畫，Programmer 不自行增加 alias。

Implementation Result：目標測試 89 passed；完整回歸 255 passed、7 skipped。7 項為依既有設定未提供 integration database/Redis 連線而 skip。測試出現 Starlette deprecation 與 pytest cache 寫入警告，未影響結果。

Code Review Result（2026-10-08）：HDR-001／004 通過；HDR-002／003 的授權來源衝突測試不足，詳見 `Features/Review/01-Authorization-Headers-Rename/` 對應 Review。這是 Test Review Problem，未發現需改動 Production Code 或重新定義需求的問題。

Handoff：HDR-002／003 交 Programmer Agent 依 OPEN Review 補測及回歸；完成後改為 DEVELOPED DONE，再交 Code Review Agent 複審。HDR-001／004 維持 DONE。

歷史紀錄：2026-10-01 原 HDR-001～004 完成 HTTP 授權遷移，原計畫記錄 84 passed、完整回歸 250 passed／7 skipped；僅代表前次版本，不代表本次已測試。Features/Review/01-Authorization-Header-Change/ 亦屬前次審查。
