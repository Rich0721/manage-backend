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

---

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

---

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
