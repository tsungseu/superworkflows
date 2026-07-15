# 变更日志

[English](CHANGELOG.md) | [简体中文](CHANGELOG.zh-CN.md)

本文件记录 Superworkflows 的重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。用于刷新 Codex 插件 Cache 的本地 `+codex.<cachebuster>` Build Metadata 不计入语义发布版本。

## [未发布]

### 文档

- 新增持续维护的英文与简体中文 README、Changelog 配对文件。
- 扩展 README，补充快速开始、14 阶段工作流、Skill 与 Agent 清单、Run 产物、CodeGraph/模型/工具分工、安全边界、环境要求和更新说明。

## [0.2.0] - 2026-07-15

### 新增

- 将原始 Mega-skill 拆分为七个显式 Skill：`superworkflows`、`init`、`status`、`run`、`review`、`release`、`learn`。
- 新增持久化受控状态机，包含原子化 `run.json`、Hash 链式 `events.jsonl`、Lineage、暂停/恢复、Finding、证据、审批和外部操作状态协调。
- 新增机器采集命令证据，记录 Commit/Workspace 身份、stdout/stderr Hash、新鲜度以及 Profile 定义的 Complete/Release 门禁。
- 新增 P0/P1/P2 Finding 生命周期、独立修复验证和过期验证检测。
- 新增 Push、PR/MR、Tag、发布、仿真部署、HIL、机器人部署和真机运行的 Action-scoped Authorization。
- 新增 Fail-closed `codegraphctl.py` 生命周期控制器，支持初始化、同步、重建恢复、健康验证和有界收敛。
- 新增 CodeGraph `explore`、`node`、`callers`、`callees`、`impact`、`affected` Checkpoint 和直接源码复核规则。
- 新增十个带 `sw-*` 命名空间的机器人 Agent，覆盖探索、架构、大脑、小脑、数采、数据算法、实现、安全、Sim2Real 和发布。
- 新增可移植 Workflow Asset、Project Profile Schema、Run 模板、JSON Schema、兼容性元数据和仅生成提案的受控学习。
- 新增控制状态完整性、证据篡改、授权幂等、符号链接拒绝、CodeGraph 生命周期失败和事务性 Agent 安装的回归测试。

### 变更

- 将插件内置 `assets/loop-engineering/workflow.md` 设为唯一工作流协议。
- 不再生成、检查或指纹化项目 `.ai/workflow.md`、`.ai/project-profile.md` 和复制的 Workflow 模板。
- 将插件命名空间内的子 Skill 调用名缩短为 `$init`、`$status`、`$run`、`$review`、`$release`、`$learn`。
- 源码探索前必须准备 CodeGraph；代码写入后必须同步索引，之后才能继续审查或图谱查询。
- 明确模型负责查询规划和推理、CodeGraph 负责结构检索、直接源码/Git 负责源码复核、实际命令负责行为证据。
- 架构、探索、安全、Sim2Real 和发布 Agent 改为只读，并与实现保持独立。
- 将按字节同步 Agent 替换为语义校验、带锁、防符号链接、支持备份和回滚的事务安装器。
- 从 Workspace 新鲜度中排除 `.ai/` 和 `.codegraph/`，并从插件运行时 Hash 中排除 `.codegraph/`。

### 安全

- 安装插件和调用 Skill 不再隐含任何外部系统或机器人硬件操作授权。
- 审批与 Action、Target、Commit、授权人和过期时间绑定，并在执行前立即复查。
- 外部操作记录稳定 Operation Intent 和状态协调结果，防止响应丢失后盲目重放。
- 本地证据执行器拒绝硬件、回滚和外部命令。
- P0 Finding 阻塞受控状态；P1 必须独立验证，或带 Owner、Reason 和 Due Condition 显式延期。

### 修复

- 防止 CodeGraph 索引维护使 Workspace 证据或持久化插件运行时身份失效。
- 支持 CodeGraph 先增量同步、再完整重建的多步状态收敛。
- CodeGraph 状态格式错误、陈旧、路径不匹配、不可用、命令失败或超时时统一 Fail-closed。

## [0.1.0]

### 新增

- 引入首个单 Skill、14 阶段机器人 AI Coding Workflow。
- 内置第一版机器人 Agent 角色快照。
