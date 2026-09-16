# Project Agent Instructions

## Purpose

此檔案為統一管理專案內的 AI Agent 定義與工作流程的跨平台共用入口，目前尚未依賴特定平台，且僅提供:  Cursor、Codex 與 GitHub Copilot使用。

本專案採用固定的 Agent Roles，並將 Agent Workflow、Skills、Project Instructions 與 Work Artifacts 分離管理，避免不同平台維護重複規則。

## Agent Roles

角色定義：

- [System Design](./agents/system-design-agent.md)
- [Programmer](./agents/programmer-agent.md)
- [Code Review](./agents/code-review-agent.md)

執行任何角色相關任務前，必須先讀取對應的 Agent Definition。

Agent Definition 是以下內容的 Source of Truth：

- Role
- Responsibilities
- Prohibited Actions
- Workflow
- Task Status Routing
- Handoff
- Completion Conditions

不得因使用不同 AI 平台、Programming Language 或 Framework 而改變 Agent Role。


## Agent Routing

依照使用者目前要求選擇對應角色。

### System Design

以下工作使用： `agents/system-design-agent.md`

例如：

- Requirement Analysis
- Requirement Change Analysis
- Bug / Behavior Analysis
- Existing System Analysis
- System Design
- Impact Analysis
- Implementation Plan
- Plan Update

### Programmer

以下工作使用：`agents/programmer-agent.md`

例如：

- Application Implementation
- Unit Test Implementation
- Regression Fix
- Plan Update Implementation
- Code Review Fix

Programmer 應以最新 Implementation Plan 與 Task Status 作為工作依據。

### Code Review

以下工作使用：`agents/code-review-agent.md`

例如：

- Implementation Review
- Code Quality Review
- Plan Compliance Review
- Test Review
- Regression Risk Review
- Review Fix Validation

## Skills

所有跨平台共用 Skills 位於：`.agents/skills/`

每個 Skill 使用：`.agents/skills/<skill-name>/SKILL.md`

Skills 應根據目前 Task 的 Technology Context 動態選擇。

例如：

### Python Backend

- `python`
- `python-backend`
- `python-testing`
- `git`

### TypeScript Backend

- `typescript`
- `typescript-backend`
- `typescript-testing`
- `git`

### TypeScript Frontend

- `typescript`
- `typescript-frontend`
- `typescript-testing`
- `git`

### Database

- `database`
- `sql`
- `testing`
- `git`

不是所有 Task 都需要載入所有 Skills，只使用與目前 Task 有關的 Skills。


## Skill Boundary

Skills 僅負責提供：

- Technical Standards
- Design Principles
- Implementation Practices
- Review Criteria
- Testing Practices
- Tool-specific Procedures

Skills 不得覆蓋或修改 Agent Definition 中的：

- Role
- Responsibilities
- Workflow
- Task Status Routing
- Handoff
- Completion Conditions

如果 Skill 與 Agent Workflow 發生衝突：

- Agent Definition 負責 Workflow 與 Responsibility。
- Skill 負責 Technical Practice。

## Technology Context

執行 Task 前，必須確認目前 Technology Context。

Technology Context 可以包含：

- Programming Language
- Framework
- Application Layer
- Testing Framework
- Database
- Infrastructure Technology

Technology Context 應優先從以下來源判斷：

1. Implementation Plan
2. Existing Project Structure
3. Existing Source Code
4. File Type / File Extension

例如：

```text
.py
→ Python Skill

.ts
→ TypeScript Skill

.tsx
→ TypeScript + Frontend Skill

.py + FastAPI
→ Python + Backend Skill

.ts + NestJS
→ TypeScript + Backend Skill

.sql
→ SQL / Database Skill
```

Programming Language 或 Framework 只影響 Relevant Skills。

不得因此切換 Agent Role 或改變 Agent Workflow。

## Project Instructions

主要的指令應參考 `instructions/project.md`，將由此文件統一管理。
如果更好管理相關`instructions`，可以將其拆分為多個子文件，並在 `instructions/project.md` 中統一引用。

Project Instructions 用於描述目前 Repository 特有的：

- Architecture
- Git Workflow
- Project Constraints
- Framework Decisions
- Repository Conventions
- Code Standards

如果 Project Instruction 與 Skill 的 Default Technical Rule 衝突：`Project Instruction` 優先。
如果 Project Instruction 沒有定義相關規則： `使用 Relevant Skill 的規範`。


## Work Artifacts

### Requirement

PM或Developer需將 Business Requirement 保存於 `Features/Document/`，作為`system-design-agent`分析並生成 Implementation Plan 的依據，且將相關生成文件統一保存於 `Features/Plan/`。

### Implementation Plan

`Features/Plan/`為`system-design-agent`分析 Business Requirement 後生成的 Implementation Plan 的保存位置，且`programmer-agent`應依此 Implementation Plan 進行實作。`code-review-agent`應依此 Implementation Plan 進行程式碼審查。

### Implementation Issue

`Features/Issue/`主要放置跨Agent之間的討論。
- `programmer-agent`於開發上有疑問可以撰寫 Implementation Issue，請`system-design-agent`確認需求後回覆。
- `system-design-agent`若排查需求後，無法處理問題將由PM調整需求說明後，重新進行分析並生成新的 Implementation Plan。

不得將 Implementation Issue 自動視為新的 Business Requirement。

### Implementation Review

`Features/Review/`主要放置跨Agent之間的程式碼審查討論。
- `code-review-agent`應依 Implementation Plan 進行程式碼審查，並將審查結果保存於此。
- `programmer-agent`應根據 Implementation Review 的反饋進行程式碼修改。


## Source of Truth

各資訊的主要 Source of Truth：

```text
Business Requirement
→ Features/Document/

Agent Role / Workflow
→ agents/

Technical Skills
→ .agents/skills/

Project-specific Rules
→ instructions/

Implementation Plan
→ Features/Plan/

Implementation Discussion
→ Features/Issue/
```

同一規則應只保留一個主要 Source of Truth。

不得在不同平台的設定檔中複製完整 Agent Workflow 或 Skill。


## Platform Integration

此檔案與 `agents/`、`.agents/skills/` 為跨平台 Canonical Core。

平台專屬設定只能作為 Adapter。

### Cursor

Cursor 應以本檔案作為 Project Agent Instructions 的主要入口。
如需 Cursor-specific Rules，可放於：`.cursor/rules/`
Cursor-specific Rules 不得重新複製完整 Agent Workflow 或 Skills。

### Codex

Codex 應以本檔案作為 Repository Agent Instructions 的主要入口。

Agent Role、Workflow 與 Skills 仍以：

- `agents/`
- `.agents/skills/`

為 Source of Truth。

### GitHub Copilot

GitHub Copilot Custom Agents 可放於：

`.github/agents/`

`.github/agents/` 僅保存 GitHub Copilot-specific metadata，例如：

- model
- tools
- handoffs
- target

完整 Role 與 Workflow 應引用：`agents/`

不得在 `.github/agents/` 再維護一份完整且獨立的 Workflow。


## Platform Adapter Rule

平台專屬檔案只允許處理：

- Platform Metadata
- Tool Configuration
- Model Configuration
- Platform-specific Handoff Configuration
- Platform-specific Routing

不得成為以下內容的第二份 Source of Truth：

- Agent Workflow
- Programming Standards
- Architecture Rules
- Git Rules
- Testing Rules


## General Execution Order

執行工作時，依照以下順序取得 Context：

```text
User Request
    ↓
AGENTS.md
    ↓
Relevant Agent Definition
    ↓
Project Instructions
    ↓
Relevant Skills
    ↓
Requirement / Plan / Issue
    ↓
Existing Project
    ↓
Execute Agent Workflow
```

Agent Workflow 不因 Skill 或 Platform 不同而改變。


## Final Principle

本專案採用：

```text
Agent = Role + Workflow

Skill = Technical Capability

Project Instruction = Repository-specific Rule

Work Artifact = Requirement / Plan / Issue / Review

Platform Adapter = Platform-specific Configuration
```

核心目標：

> Cursor、Codex 與 GitHub Copilot 可以使用不同的平台能力，但共同遵循同一份 Agent Workflow、Skills 與 Project Rules。

任何跨平台整合都應優先避免 Duplicate Rules 與 Configuration Drift。
