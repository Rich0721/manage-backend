---
name: programmer-agent
description: Implement approved plans according to the shared Programmer Agent definition.
model: GPT-5.6 Luna
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

# Programmer Agent

請根據跨平台共用的Programmer-Agent定義: `agents/programmer-agent.md`
相關工作流程、職責等也需要根據跨平台定義: `AGENTS.md` 執行相關作業。

此文件僅定義 GitHub Copilot 專用的配置。
