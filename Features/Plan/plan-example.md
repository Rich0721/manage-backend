# <Feature Name> Implementation Plan

## I. Requirement Information

Feature Name: FeatureName1.md, FeatureName2.md
Scenario: Scenario1.feature, Scenario2.feature, ...

Other Requirements:
PM口頭敘述需求，僅請SD參考需求來源，僅有Bug修復和需求修改

```text
Requirement Source: PM口頭敘述
Requirement Date: YYYY-MM-DD
Requirement Summary: PM口頭敘述的需求摘要
```

例如:

```text
Requirement Source: FeatureName1.md的Example Component需要新增XXX功能
Requirement Date: 2024-06-01
Requirement Summary: 原本僅能執行YYY功能，現在需要新增XXX功能
```

## II. Requirement Summary

描述需求的摘要。

```text
根據Feature, Scenario和Other Requirements整理需求摘要
```

## III. Requirement List

主要與*Implementation Steps*數量相應，但*Implementation Steps*是相關實作的細節，而*Requirement List*則是對需求的概括與分類，提供給不同角色快速參考作業進度，相關修改細節需要在*Implementation Steps*中詳細記錄。

| Task ID  | Component Name      | Plan Type | Plan Date  | Implentation Status | Development Date | Code Review Date |
| -------- | ------------------- | --------- | ---------- | ------------------- | ---------------- | ---------------- |
| TASK-001 | ExampleComponent    | ADD       | YYYY-MM-DD | TODO                | YYYY-MM-DD       | YYYY-MM-DD       |
| TASK-002 | AnotherComponent    | MODIFY    | YYYY-MM-DD | TODO                | YYYY-MM-DD       | YYYY-MM-DD       |
| TASK-003 | YetAnotherComponent | REMOVE    | YYYY-MM-DD | DEVELOPED DONE      | YYYY-MM-DD       | YYYY-MM-DD       |

```text
填寫此表格的規則如下:
- Component Name: 填寫元件或功能名稱
- Plan Type: 填寫計畫類型 (ADD, MODIFY, REMOVE)
- Plan Date: 填寫計畫日期 (YYYY-MM-DD)，System-design-agent再提出計畫時就必須填寫
- Implentation Status: 填寫實作計畫的進度 (TODO, DEVELOPED DONE, DOUBLE CHECK, PLAN UPDATED, REVIEW FIX, DONE)
- Development Date: 填寫開發日期 (YYYY-MM-DD)，當Programer完成開發後必須填寫
- Code Review Date: 填寫程式碼審查日期 (YYYY-MM-DD)，當Code Reviewer完成審查後必須填寫
```

```text
Plan Change Type: 需求變更類型，ADD、MODIFY、REMOVE，只有**system-design-agent**可以進行修改，開發人員不能修改。
- ADD: 代表為新增需求
- MODIFY: 代表為修改需求
- REMOVE: 代表為刪除需求

可以從ADD變成MODIFY或REMOVE，也可以從MODIFY變成REMOVE，但REMOVE也可以變回ADD，只要 SD 修改已完成 Task 的 Implementation Specification，就必須 Reset。
```

```text
Implentation Status: 說明實作計畫的進度，不同的代理人僅可以設定自己的進度，且當SD修改Plan Change Type時，需要將Implentation Status變更為TODO。
- system-design-agent:
    - 如果計畫是從Requirement List新增的Task，無論是ADD、MODIFY或REMOVE，都需要將Implentation Status設定成TODO
    - 如果該計畫是因為PG提出疑惑，會以DOUBLE CHECK的方式回報，並待SD確認後，將Implentation Status更新為PLAN UPDATED。
- programer: 
    - 如果Implentation Status為TODO, PLAN UPDATED與REVIEW FIX，則根據實作計畫進行開發，完成後更新相應的Implementation Status。
    - 如果實作過程中需要與SD進行討論，則應將Implentation Status更新為DOUBLE CHECK，待SD確認後再繼續開發。
- code-reviewer: 
    - 如果Implementation Status為DEVELOPED DONE，則將其作為需要審查的依據，其餘狀態不需要審查。
    - 進行Review審查時，有需要請PG進行調整時，需要將Implementation Status更新為REVIEW FIX，待PG修正重新Reivew。
    - 假設沒有需要修改的地方，則直接將Implementation Status更新為DONE。
```

## IV. Technical Stack

- Python:
- Framework:
- Database:
- Other Dependencies:

## V. Implementation Steps

### TASK-001 ExampleComponent

```text
File: ...
Target: ...

Reuse: ...
Impact: ...

Current Behavior: ...

Expected Behavior: ...

Implementation: ...

Error Handling: ...

Testing: ...
```

範例:

```text
File: src/service/manage_user_service.py
Target: manage_user_service.get_user
Reuse: ExistingClass / ExistingFunction
Impact:
- manage_user_controller.get_user: 不須修改
- manage_user_registry.get_user: 需調整SQL邏輯

Current Behavior: manage_user_service.get_user 直接呼叫 manage_user_registry.get_user，未考慮 SQL 調整後的影響

Expected Behavior: manage_user_service.get_user 需根據調整後的 SQL 邏輯正確取得使用者資料

Implementation: manage_user_service.get_user 需先調整 SQL 查詢邏輯，確保取得正確的使用者資料

Error Handling: 若 SQL 查詢失敗，需回傳適當的錯誤訊息

Testing: 撰寫單元測試，模擬 SQL 調整後的情境，驗證 manage_user_service.get_user 是否正確取得使用者資料

```

### TASK-002 AnotherComponent

```text
File: src/...
Target: Class / Method / Function
Reuse: ExistingClass / ExistingFunction
Current Behavior:
...

Change Behavior:

1. ...
2. ...
3. ...

Error Handling:
...

```

### TASK-003 YetAnotherComponent

```text
File: src/...
Target: Class / Method / Function
Reuse: ExistingClass / ExistingFunction
Behavior:
...

Error Handling:
...

```

## VI. Review Status

- [ ] Implementation Plan 已完成人工審核
- [ ] Development 完成
- [ ] Code Review 通過
