---
name: code-review-agent
description: 針對專案進行程式碼審查。從 Features/Plan/ 中尋找對應的Review Code。此 Agent 僅負責程式碼審查，不負責撰寫程式碼。
model: GPT-5.6 Terra
tools:
  - execute
  - read
  - edit
  - search
  - agent
  - todo
disable-model-invocation: true
user-invocable: true
---

# Code Review Agent

請根據跨平台共用的Code Review Agent定義: `agents/code-review-agent.md`
相關工作流程、職責等也需要根據跨平台定義: `AGENTS.md` 執行相關作業。

此文件僅定義 GitHub Copilot 專用的配置。
