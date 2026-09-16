# Git Skill

---

name: git-skill
description: 提供 Git 版本控制、分支、Commit、Push、Pull、Merge 與遠端同步的共通操作規範。適用於 System Design、Development 與 Code Review 等需要透過 Git 保存與同步工作成果的流程。

---

## Overview

此 Skill 僅負責定義 Git 的基本操作與版本控制規範。

實際在什麼時機：

- 建立 Branch
- 更新 Implementation Plan
- 開始 Development
- 執行 Code Review
- Handoff 給下一個 Agent

應由各 Agent 的 Workflow 定義。

如果專案已於 `instructions/` 中定義 Git Workflow，必須優先遵循該規範。

如果未定義 Git Workflow，則遵循本 Skill。

## Core Principles

Git 操作必須遵循以下原則：

1. Remote Repository 為多個 Agent 與不同工作環境之間共享工作的主要版本來源。
2. 所有需要跨 Agent、跨電腦保存的工作成果都必須 Commit 並 Push 至 Remote Repository。
3. 每次 Commit 應具有單一且明確的目的。
4. 不得任意覆蓋其他 Agent 已 Push 的 Remote History。
5. 未經人工明確要求，不得使用 Force Push 修改共享歷史。
6. `main` 應保持穩定，Application Code 應透過 Feature / Bugfix Branch 進行修改。
7. Application Code 必須完成 Code Review 後才能 Merge 至 `main`。

## Remote Synchronization

開始修改任何 Git-managed File 前，必須先同步 Remote Repository。

基本流程：

```text
git fetch
    ↓
確認 Remote Branch
    ↓
同步 Local Branch
    ↓
確認 Working Tree
    ↓
開始修改
```

不得假設 Local Repository 為最新狀態。如果 Remote Branch 已存在，應優先同步 Existing Remote Branch，而不是重新建立或覆蓋該 Branch。

## Branch Guidelines

Branch 名稱應清楚表示工作的 Feature 或 Bug。

建議：

```text
feature/<feature-name>
bugfix/<feature-name>
```

需要更細粒度時：

```text
feature/<feature-name>/<task-id>
bugfix/<feature-name>/<task-id>
```

例如：

```text
feature/user-email-validation
feature/user-email-validation/task-001

bugfix/upload-duplicate
bugfix/upload-duplicate/task-003
```

Branch 應代表：

```text
Feature
Bug
Task
```

而不是代表：

```text
System Design Agent
Programmer Agent
Code Review Agent
```

不同 Agent 可以依 Workflow 在同一個 Feature Branch 上依序工作。

## Branch Creation

建立新 Branch 前：

1. 執行 `git fetch`。
2. 確認 Remote 是否已有相同 Branch。
3. 如果 Remote Branch 已存在，使用 Existing Remote Branch。
4. 如果不存在，才從目前專案規定的 Base Branch 建立。

不得因 Local Branch 已存在而直接強制覆蓋 Remote Branch。

## Default Branch Workflow

如果專案的 `instructions/` 或目前 Agent Workflow 沒有特別定義 Git Branch 操作流程，則必須遵循本節的預設流程。

此流程適用於：

- System Design
- Development
- Code Review
- Requirement Change
- Bug Fix
- Plan Update
- Review Fix

Branch 應依照目前 Requirement、Feature、Bug 或 Task 建立與使用。

建議命名：

```text
feature/<feature-name>
bugfix/<feature-name>
```

需要以 Task 區分時：

```text
feature/<feature-name>/<task-id>
bugfix/<feature-name>/<task-id>
```

### I. Branch Preparation

開始任何 Git-managed 工作前：

1. 確認目前 Requirement、Feature、Bug 或 Task 對應的 Branch Name。
2. 執行 `git fetch`，取得 Remote Repository 最新狀態。
3. 確認 Remote Repository 是否已存在對應 Branch。

接著依 Branch 是否存在執行不同流程。

### II. Remote Branch 不存在

如果 Remote Repository 尚未存在對應 Branch：

1. 切換至 `main`。
2. 同步 Remote `main` 最新版本。
3. 確認 Local `main` 已與 Remote `main` 保持一致。
4. 從最新 `main` 建立對應 Feature / Bugfix Branch。
5. 切換至新建立的 Branch。
6. Push Branch 至 Remote Repository。
7. 開始目前 Agent 的工作。

流程：

```text
Fetch Remote
    ↓
Checkout main
    ↓
Pull Remote main
    ↓
Create Feature / Bugfix Branch
    ↓
Push Remote Branch
    ↓
Start Work
```

不得從過期的 Local `main` 建立新 Branch。

### III. Remote Branch 已存在

如果 Remote Repository 已存在對應 Branch：

1. 執行 `git fetch`。
2. 切換至對應 Feature / Bugfix Branch。
3. Pull 對應 Remote Branch 最新內容。
4. 確認 Local Branch 已包含其他 Agent 或 Developer 最新 Push 的內容。
5. 同步 Remote `main` 最新版本。
6. 將最新 `main` 的變更整合至目前 Feature / Bugfix Branch。
7. 如果發生 Conflict，依本 Skill 的 Conflict Handling 規範處理。
8. 完成同步後才開始目前 Agent 的工作。

流程：

```text
Fetch Remote
    ↓
Checkout Existing Feature / Bugfix Branch
    ↓
Pull Remote Feature / Bugfix Branch
    ↓
Update main
    ↓
Integrate Latest main Into Current Branch
    ↓
Resolve Conflict If Required
    ↓
Start Work
```

不得只同步 Feature Branch 而忽略最新 `main`。

不得只同步 `main` 而忽略其他 Agent 已 Push 至 Feature Branch 的工作內容。

### IV. Integrate Main

將最新 `main` 整合至目前 Feature / Bugfix Branch 時：

1. 應優先遵循 `instructions/` 定義的 Merge Strategy。
2. 如果 `instructions/` 沒有定義，依 Repository 現有 Git Convention 選擇適當方式。
3. 可以使用：
   - Merge
   - Rebase
4. 不得為了同步 `main` 而 Rewrite 已共享的 Remote History。
5. 不得使用 Force Push 作為一般同步方式。

本 Skill 不強制所有專案使用相同的 Merge Strategy。

### V. Before Commit

目前 Agent 完成工作或需要保存工作狀態時：

1. 使用 Git Skill 檢查 Git 狀態。
2. 確認目前位於正確的 Feature / Bugfix Branch。
3. 再次確認 Remote Branch 是否存在新的變更。
4. 必要時先同步 Remote Branch。
5. 確認 Commit 僅包含目前相關 Task 或 Logical Change。
6. 確認需要保存的 Git-managed Artifact 已包含於 Commit。

可能包含：

```text
Application Code
Tests
Implementation Plan
Implementation Plan Status
Implementation Issue
Review Result
Project Instructions
```

實際需要保存哪些內容，依目前 Agent Workflow 決定。

### VI. Commit and Push

確認修改內容後：

1. 執行必要的 Test 或 Validation。
2. Commit。
3. Push 至目前對應的 Remote Feature / Bugfix Branch。

不得直接將一般 Feature / Bugfix 開發內容 Push 至 `main`。

流程：

```text
Work Complete
    ↓
Check Git Status
    ↓
Sync Remote Branch If Required
    ↓
Validate Changes
    ↓
Commit
    ↓
Push Feature / Bugfix Branch
```

### VII. Existing Branch Is Shared Work

Existing Feature / Bugfix Branch 應視為目前 Requirement 的共享工作空間。

可能依序由：

```text
System Design Agent
        ↓
Python Programmer
        ↓
Code Review Agent
```

或其他 Agent 使用。

因此每個 Agent 開始工作前都必須：

```text
Fetch
↓
Checkout Existing Branch
↓
Pull Latest Remote Branch
↓
Sync Latest main
↓
Start Work
```

Agent 不得因 Local Repository 已存在同名 Branch，就假設 Local Branch 為最新版本。

### VIII. Agent Workflow Priority

Git Workflow 的優先順序：

```text
Project instructions/
        ↓
Agent-specific Git Workflow
        ↓
Git Skill Default Branch Workflow
```

也就是：

1. 如果 `instructions/` 已明確定義 Git Workflow，必須遵循 `instructions/`。
2. 如果 Agent 自己有更具體的 Git Workflow，且不與 `instructions/` 衝突，則遵循 Agent Workflow。
3. 如果以上都沒有定義，必須遵循本節 Default Branch Workflow。

Agent-specific Workflow 可以決定：

```text
何時開始 Git 操作
何時建立或更新 Plan
何時進入 Development
何時進行 Review
何時 Handoff
```

Git Skill 則負責規範：

```text
如何安全建立與同步 Branch
如何同步 main
如何 Pull Remote Branch
如何 Commit
如何 Push
如何避免覆蓋 Shared History
```


## Commit Guidelines

每次 Commit 應只處理：

- 一個 Task ID
- 或一個明確 Logical Change

避免將多個不相關修改放入同一個 Commit。

Commit 前應確認：

- Working Tree 內容符合預期。
- 沒有 Temporary File。
- 沒有不相關修改。
- 必要 Test 已完成。
- 應保存的 Plan / Status Change 已包含於 Commit。

## Commit Message

建議 Commit Message 包含：

```text
[ROLE][TASK-ID] Description
```

ROLE：

```text
PLAN
DEV
REVIEW
```

例如：

```text
[PLAN][TASK-001] Add email validation implementation plan

[DEV][TASK-001] Implement duplicate email validation

[DEV][TASK-001] Add email validation unit tests

[REVIEW][TASK-001] Complete email validation review
```

Bug Fix：

```text
[PLAN][TASK-003] Plan duplicate upload bug fix

[DEV][TASK-003] Fix duplicate upload handling

[REVIEW][TASK-003] Complete bug fix review
```

如果沒有 Task ID：

```text
[PLAN] Add user export implementation plan
```


## Push Guidelines

Push 前：

1. 確認 Local Branch。
2. 確認 Commit 內容。
3. 確認 Remote Branch 狀態。
4. 必要時先 Fetch / Pull 最新 Remote Change。
5. 解決 Conflict 後再 Push。

一般 Feature Branch 可以在 Code Review 前 Push。

禁止將：

```text
Push Feature Branch
```

與：

```text
Merge Main
```

視為相同操作。

正確流程：

```text
Commit
    ↓
Push Feature Branch
    ↓
Code Review
    ↓
Review Pass
    ↓
Merge Main
```

## Force Push

以下操作預設禁止：

```text
git push --force
git push --force-with-lease
```

除非：

- 使用者明確要求。
- 專案 Git Workflow 明確允許。
- 已確認不會覆蓋其他 Agent 或 Developer 的 Remote History。

Agent 不得自行使用 Force Push 解決同步問題。

## Pull / Update Guidelines

同步 Remote Branch 時，應先：

```text
git fetch
```

確認 Remote 變更後，再依專案 Workflow 使用適當方式：

```text
git pull
git merge
git rebase
```

不得在未知 Remote 狀態下直接修改共享 Branch。

## Merge Guidelines

Application Code 應優先透過 Pull Request Merge。

Merge 前必須確認：

- Required Development 已完成。
- Required Tests 已通過。
- Code Review 已完成。
- Implementation Plan 狀態已更新。
- 沒有未處理的 Review Issue。
- Branch 已與 Base Branch 保持合理同步。

Merge Strategy 應優先遵循 `instructions/` 定義。

如果沒有定義，可以依 Repository 現況選擇：

```text
Merge Commit
Squash Merge
Rebase Merge
```

但不得為了整理歷史而任意 Rewrite 已共享的 Commit。

## Conflict Handling

遇到 Merge Conflict 時：

1. 不得直接選擇其中一方全部覆蓋。
2. 確認兩邊 Change 的目的。
3. 保留符合目前 Requirement 與 Implementation Plan 的內容。
4. 如果無法確認 Business Behavior，停止修改並交由相關 Agent 或使用者確認。

解決 Conflict 後應重新執行必要 Test。

## Protected Files

如果 Repository 中包含：

```text
Features/Document/
Features/Plan/
instructions/
.github/
```

這些文件同樣屬於 Git-managed Artifact。

修改後必須：

```text
Commit
+
Push
```

不得只保留在某一台 Local Computer。

## History Preservation

以下資訊應透過 Git History 保留：

- Requirement Plan Change
- Implementation Plan Change
- Development Change
- Bug Fix
- Review Result
- Agent Status Update
- Project Instruction Change

不得為了讓 Commit History 看起來乾淨，而刪除仍具有追蹤價值的歷史。

## Forbidden Operations

除非使用者或專案 Workflow 明確允許，Agent 不得：

```text
Force Push
Rewrite Shared History
Delete Remote Branch Under Active Development
Reset Remote Work
Overwrite Existing Remote Branch
Commit Unrelated Changes
Commit Secret / Credential
Directly Develop on main
```

## Final Principle

Git Skill 只負責回答：

```text
如何安全地使用 Git？
如何同步 Remote？
如何建立 Branch？
如何 Commit？
如何 Push？
如何 Merge？
如何保存 History？
```

至於：

```text
什麼時候建立 Plan？
什麼時候開始 Development？
什麼時候進入 Code Review？
什麼時候更新 Requirement Status？
什麼時候 Handoff？
```

應由各 Agent 的 Workflow 定義。
