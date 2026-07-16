# Superworkflows

[English](README.md) | [简体中文](README.zh-CN.md)

Superworkflows 是一套面向 Codex 的机器人与具身智能 AI Coding Loop Engineering 方法论。它将一个可发现的顶层路由 Skill、六个显式阶段 Skill、专业 `sw-*` Agent、可选持久化运行状态、对抗性审查、机器采集证据、条件式 CodeGraph 代码探索、发布门禁和审批控制的学习闭环组合在一起。

它适用于机器人 Runtime、大脑与小脑软件、行走控制与强化学习、Sim2Real、真机数采、机器人数据集和生产调试等“代码看起来正确仍然不够”的工程场景。

## 快速开始

复杂机器人任务可以直接用自然语言描述；总入口可通过语义发现并在 Session-only 工作流中执行用户明确要求的仓库源码修改，但不创建持久工作流状态：

```text
为当前机器人 Runtime 增加模型 OTA 和回滚机制，并开启对抗性安全审查。
```

需要确定性触发时，显式调用总入口：

```text
$superworkflows 为当前机器人 Runtime 增加模型 OTA 和回滚机制
```

需要持久化初始化、启动或恢复时，直接调用精确的阶段 Skill：

```text
$init 初始化 CodeGraph 和可选的持久化运行状态
$run 将当前实现作为有证据的闭环启动或恢复
$status 只读检查当前 Run
$review 对当前计划、Diff 和证据进行对抗性审查
$release 评估集成、回滚和发布就绪状态
$learn 从已完成 Run 中提出经过审查的工作流改进
```

只有 `$superworkflows` 可以隐式调用；六个子 Skill 仍须显式调用或由路由器选择。协议将隐式路径限制为 Session-only，并禁止它修改或初始化 CodeGraph、创建或恢复 `.ai` Run、按标题相似度推断 Run，或把 Push、创建 PR/MR、发布、部署、HIL、真机运行与执行器动作视为已授权。显式调用总入口仍不等价于 `$init` 或 `$run`。

## 工作原理

Superworkflows 首先分离三个相互独立的决策：**路由**（适合哪个阶段）、**持久化**（Session-only 或持久 Run）和**权限**（本地分析、仓库写入或需单独审批的外部/硬件操作）。外部动作标记不会覆盖已选择的本地路由，“所需权限”与“当前已有权限”也会分开报告。无副作用的激活评估器以可审计的中英文信号辅助路由器；它不替代模型推理，也不授予权限。

工程闭环先建立仓库事实和明确契约，再挑战计划、在受限 Ownership 中实现、挑战实现、修复 Finding、串行集成、在最高已授权环境中验证，并记录实际观察到的结果。

在持久化模式下，主 Agent 是唯一的 Run Ledger 写入者。子 Agent 只接收边界明确的工作项、允许修改的文件、必需检查和停止条件。Reviewer 独立且只读。实现者可以将 Finding 标记为 `FIXED`，只有独立 Reviewer 才能基于当前证据标记为 `VERIFIED`。

持久任务只能在显式 `$run` 调用后，从精确的 `.ai/runs/<run-id>/` 恢复，并重新验证 Lineage、仓库身份、事件完整性、Workspace 新鲜度、Agent 契约和未完成的外部操作意图。含糊的“继续上次任务”等表达不会自动选择或恢复 Run。

## 基本工作流

1. **仓库探索**——确认范围、入口、调用链、接口、测试和风险。
2. **需求与安全契约**——定义不变量、排除项、验收条件和证据计划。
3. **初始计划**——建立工作项 DAG、Ownership、验证策略和回滚方案。
4. **独立计划审查**——挑战假设并分类 P0/P1/P2 Finding。
5. **最终计划**——在实现前解决或显式跟踪 Finding。
6. **Ownership 与隔离**——每个文件只有一个 Writer，必要时使用 Worktree。
7. **实现**——执行边界明确的修改，只并行不重叠的写集合。
8. **独立代码与安全审查**——检查当前 Commit、Diff、接口、故障路径和证据。
9. **修复**——修复 Finding，但不允许实现者自我验证。
10. **独立修复验证**——重新执行相关检查，并基于新鲜状态验证 Finding。
11. **串行集成**——每次只集成一个变更，重放前先完成状态协调。
12. **最终验证**——按授权执行 Build、Test、Replay、Simulation、HIL 和 Robot 门禁。
13. **发布就绪**——证明制品来源、回滚能力和受控操作意图。
14. **交付与学习**——报告事实，并将改进作为独立审批的提案保存。

小型低风险任务可以合并阶段，但不能删除 Ownership、证据完整性、适用的安全审查或外部授权边界。

## Skills

| Skill | 用途 |
|---|---|
| `$superworkflows` | 可发现的总入口，评估是否激活并选择会话内阶段；持久启动或按精确 ID 恢复仍须显式调用。 |
| `$init` | 准备 CodeGraph，并可选创建 `.ai/project-profile.json` 和持久化目录。 |
| `$status` | 只读检查 Run、证据、Finding、审批、完整性和下一门禁。 |
| `$run` | 启动或恢复实现、委派、审查、修复、集成与验证。 |
| `$review` | 独立对抗性审查计划、Diff、Run、安全声明和发布候选。 |
| `$release` | 管控串行集成、回滚证明以及单独授权的外部或硬件操作；仅由路由器选中时只做就绪评估。 |
| `$learn` | 生成人工审查的改进提案；没有精确调用或已验证持久来源时，路由器选中的学习只在回复中总结。 |

## 插件内含能力

### 持久化控制面

[`scripts/loopctl.py`](scripts/loopctl.py) 提供 Fail-closed 本地状态机：

- 原子化 `run.json` Checkpoint；
- 只追加、Hash 链式 `events.jsonl` Journal；
- 可恢复的 `ACTIVE`、`PAUSED`、`BLOCKED`、`COMPLETE`、`CANCELLED` 状态；
- P0/P1/P2 Finding 生命周期和独立验证；
- 带 Commit、Workspace Digest、退出码、stdout/stderr 和 SHA-256 元数据的白名单命令证据；
- 与 Action、Target、Commit、授权人和过期时间绑定的审批；
- 幂等外部操作意图和状态协调。

### CodeGraph 生命周期

[`scripts/codegraphctl.py`](scripts/codegraphctl.py) 负责保持结构化代码检索最新：

```bash
python3 scripts/codegraphctl.py prepare --root <repo>
python3 scripts/codegraphctl.py sync --root <repo>
python3 scripts/codegraphctl.py status --root <repo>
```

只有仓库指令要求、已有 `.codegraph/` 索引或用户明确要求初始化时才使用 CodeGraph，并先读取仓库 `AGENTS.md`。`prepare` 可以初始化缺失索引、同步待处理变更、重建不兼容或 Worktree 不匹配的索引，并验证最终收敛。隐式路径、总入口确认态、`$status` 和 `$review` 只读查询已有且健康的索引；只有精确的可写子 Skill 才按需执行 `prepare`/`sync`。只读路径发生源码写入后，图谱视图立即视为陈旧。

模型负责提出和解释问题；`codegraph_explore`、`codegraph_node` MCP 工具或等价 CLI 负责检索 Symbol、源码、调用链、影响范围和受影响测试。直接读取源码与 Git 是最终源码复核；实际执行 Build、Test、Replay、Simulation、HIL 和 Robot 命令才是行为证据。

`.codegraph/` 是生成的工具状态，不参与 Workspace 新鲜度或插件运行时 Hash。

### 专业 Agents

插件包含十个带命名空间的 Agent：

| Agent | 职责 |
|---|---|
| `sw-explorer` | CodeGraph-first 的只读仓库探索和影响范围分析。 |
| `sw-robot-system-architect` | 只读分析大脑、小脑、数据、Runtime、部署和安全的系统边界。 |
| `sw-robot-brain-engineer` | 规划、导航、感知到决策链、命令仲裁和下游契约。 |
| `sw-biped-cerebellum-engineer` | 行走控制、RL Policy 契约、关节映射、控制频率、增益和 Sim2Real 安全。 |
| `sw-robot-data-collector` | 真机遥操与规模化自主数采、同步、存储和质量门禁。 |
| `sw-robot-data-algorithm` | 大脑数据集、预处理、清洗、标注、指标和训练反馈。 |
| `sw-worker` | 在指定文件和 Worktree 中进行受限实现。 |
| `sw-robot-safety-reviewer` | 独立只读的安全与生产就绪审查。 |
| `sw-robot-sim2real-validator` | 独立审查 Replay、Simulation、HIL、Sim2Real 和真机证据。 |
| `sw-robot-release-engineer` | 只读评估来源、集成、回滚、灰度和操作员就绪状态。 |

事务性安装或检查 Agent：

```bash
python3 scripts/sync_agents.py --check
python3 scripts/sync_agents.py --install
```

安装器会校验 TOML 和角色契约、拒绝符号链接目标、使用文件锁、备份替换文件、原子提交，并支持按 Transaction ID 回滚。

## Run 产物

持久化模式创建：

```text
.ai/
├── project-profile.json          可选的机器命令与门禁
├── improvements/pending/         需要审批的学习提案
└── runs/<run-id>/
    ├── run.json                  原子化当前 Checkpoint
    ├── events.jsonl              Hash 链式事件 Journal
    ├── evidence/<evidence-id>/   元数据、stdout、stderr 和 Hash
    ├── 00-repository-exploration.md
    ├── 01-requirements-contract.md
    ├── 02-initial-plan.md
    ├── 03-plan-review.md
    ├── 04-final-plan.md
    ├── 05-ownership.md
    ├── 06-implementation-log.md
    ├── 07-integration-log.md
    ├── 08-final-verification.md
    ├── 09-delivery-report.md
    └── 10-lessons-learned.md
```

插件内置的 [`assets/loop-engineering/workflow.md`](assets/loop-engineering/workflow.md) 是唯一工作流协议。

Session-only 任务（包括所有隐式激活）不创建 `.ai/`。持久化机器证据需要显式开启持久模式，并提供 `.ai/project-profile.json`。

## 安全与授权

Superworkflows 将“就绪”与“执行”分离。按照协议，隐式激活或拒绝持久化都不会获得外部或硬件权限。以下操作需要与精确 Action、Target 和 Commit 绑定的独立显式授权：

- Push 和创建 PR/MR；
- 发布 Tag、软件包或模型；
- 部署仿真服务；
- 执行 HIL；
- 部署到机器人；
- 真机运行或执行器动作。

低级环境不能证明高级环境。源码检查不能证明 Build；Build 不能证明 Replay；Simulation 不能证明 HIL；HIL 不能证明真机行为。缺失证据只能标记为 `UNVERIFIED` 或 `BLOCKED`，不能默认通过。

完整边界见 [`SECURITY.md`](SECURITY.md) 和[可移植工作流](assets/loop-engineering/workflow.md)。

## 安装

Superworkflows 以 Codex 插件 Marketplace 的形式发布在 GitHub 上。先从远程仓库注册 Marketplace：

```bash
codex plugin marketplace add tsungseu/superworkflows
```

随后在该 Marketplace 中启用 `superworkflows` 插件——在 Codex TUI 的 `/plugins` 选择器中启用，它会把 `[plugins."superworkflows@<marketplace>"]`（`enabled = true`）写入 `~/.codex/config.toml`。

在本仓库的检出目录中检查或安装运行时 Agent：

```bash
python3 scripts/sync_agents.py --check
python3 scripts/sync_agents.py --install
```

安装或更新后需要开启新的 Codex 对话，让 Skill Catalog 和插件 Cache 重新加载。

## 环境要求

- 支持本地插件的 Codex；
- Python 3.10 或更高版本；
- Python 3.10 需要 `tomli>=2.0`，Python 3.11+ 仅使用标准库；
- 目标仓库使用 CodeGraph 时所需的 CodeGraph CLI；
- 当前 Codex 模型目录中存在：`gpt-5.4-mini`、`gpt-5.4`、`gpt-5.5`、`gpt-5.6-sol`。

## 更新与验证

本地开发验证：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_agents.py --check
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
```

使用 plugin-creator Helper 更新 Codex Cachebuster，从 `personal` Marketplace 重新安装并开启新对话。`0.2.0+codex.<timestamp>` 形式的 Build Metadata 只刷新本地插件 Cache，不代表新的语义版本。

版本历史见[英文 Changelog](CHANGELOG.md)或[中文 Changelog](CHANGELOG.zh-CN.md)。

## 参考 Hermes 的优化

Superworkflows 吸收了小而稳定的主循环、渐进式 Skill 披露、新鲜且有界的 Reviewer/Worker 上下文、可恢复状态、通过持久证据压缩上下文，以及从重复成功、用户纠正和失败路径中受控学习等思想。这些设计参考 Hermes Agent 官方的[架构](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)、[主循环](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop/)、[Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)、[委派](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)、[上下文压缩](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching/)和[安全](https://hermes-agent.nousresearch.com/docs/user-guide/security)说明。

插件有意不引入 Skill 自修改、递归委派、通用记忆采集、Provider Fallback、消息/定时任务或不受约束的工具循环。在同一用户的本地机器上，触发、持久化、CodeGraph、Reviewer 身份和尝试次数规则属于编排与本地控制面约束，不是 OS 级或密码学隔离。硬隔离仍由 Codex Sandbox、工具审批、仓库权限和外部系统负责；只有未来的 Dispatch Broker 能将资源预留、输入 Capsule、结果和身份原子绑定后，才可宣称硬性调度执行。

## 设计理念

- **证据优先于声明**——只报告源码和实际检查能够支持的结论。
- **独立审查优先于自我认证**——实现者负责修复，Reviewer 负责验证。
- **显式持久状态优先于对话记忆**——经过授权的持久任务从精确且已验证的 Checkpoint 恢复。
- **边界明确的 Ownership 优先于失控并行**——每个文件一个 Writer，串行集成。
- **Fail-closed 优先于乐观继续**——陈旧证据、损坏索引和缺失授权都会阻塞流程。
- **尊重更高环境的证据门槛**——不把低环境证据升级为生产或真机结论。
- **通过提案学习，而不是自修改**——改进需要审查、审批、验证和回滚。

## 许可协议

版权所有 (c) 2026 Tsung Xu。**双协议授权——二选一：**

- **GNU AGPL-3.0-only**——[`LICENSE`](LICENSE) 中的开源协议。你可以使用、修改和分发本软件（含商用），**前提是：基于本软件构建并通过网络对外提供的任何衍生软件，也必须以 AGPL-3.0 开源**（强 copyleft）。
- **商业许可**——若无法满足 AGPL-3.0 的要求（例如嵌入闭源/专有产品而不愿开源自有代码），可获取单独的商业许可。

这是双协议（open-core）模式：项目是真正的 OSI 认证开源软件，商业授权为需要闭源自有代码的用户提供 funding 通道。

商业许可条款请在 <https://github.com/tsungseu/superworkflows/issues> 提交 issue，或联系维护者。
