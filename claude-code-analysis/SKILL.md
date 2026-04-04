---
name: claude-code-analysis
description: Claude Code 源码深度分析技能。内置本地化分析知识库（不依赖外部仓库），包含架构解读、Memory 系统拆解、同类对比框架、OpenClaw 适配建议。支持快速摘要和深度分析两种模式。
---

# 🔍 Claude Code 源码深度分析

> 内置 Claude Code 泄露源码的分析知识库，不完全依赖外部仓库。涵盖架构设计、核心机制、同类对比、以及针对 OpenClaw 的具体适配建议。

## 触发方式

- `分析claude code`
- `claude code源码分析`
- `/cc-analysis`
- `claude code快速总结`（快速摘要模式）

## 分类

开发辅助 / IT/互联网

## 标签

Claude Code / 源码分析 / Agent架构 / Memory / 安全 / MCP

---

## 技能说明

本技能提供两种分析模式：

### 快速摘要模式（默认）
当用户说"分析claude code"或"claude code快速总结"时，直接输出下方「本地知识库」中的核心内容，不抓取外部仓库。适用于快速了解 Claude Code 的架构要点。

### 深度分析模式
当用户需要深入某个具体维度时，从 GitHub 仓库 `liuup/claude-code-analysis` 抓取对应章节，结合本地知识库进行交叉分析。同时提供外部仓库的更新内容（如果有新章节）。

---

## 📚 本地知识库

> 以下内容已从 GitHub 仓库 `liuup/claude-code-analysis` 提取并本地化，即使外部仓库不可访问也可正常使用。

### 一、项目概览

| 项目 | 信息 |
|------|------|
| 项目定位 | 面向代码工作流的本地 Agent 平台（非命令行聊天工具） |
| 代码规模 | 1902 个源文件，513,237 行 TypeScript |
| 泄露时间 | 2026年3月31日 |
| 泄露原因 | npm 包未删除 source map 文件 |
| 一句话总结 | "能力极强、平台感很重、长期协作属性明显"的本地代码 agent 系统 |

### 二、六层分层架构

```
+------------------------------+
| CLI 引导层                   |
| entrypoints/cli.tsx          |
| main.tsx                     |
+------------------------------+
               ↓
+------------------------------+
| 初始化层                     |
| entrypoints/init.ts          |
| setup.ts                     |
+------------------------------+
      ↓                  ↓
+------------------+   +------------------------------+
| 控制面 / 命令层  |   | TUI / REPL 层                |
| commands.ts      |-->| replLauncher.tsx / REPL.tsx  |
| slash/menu       |   +------------------------------+
+------------------+                  ↓
                         +------------------------------+
                         | 执行内核                     |
                         | query.ts / QueryEngine.ts    |
                         +------------------------------+
                           ↓            ↓            ↓
                 +---------------+ +-----------------+ +------------------+
                 | Tool/Perm 层  | | Memory/Persist  | | 扩展层           |
                 | Tool.ts       | | sessionStorage  | | MCP/Plugin/      |
                 | orchestration | | memdir/SM       | | Remote/Swarm     |
                 +---------------+ +-----------------+ +------------------+
```

**核心设计**：所有运行形态（REPL、headless、subagent、background、bridge/remote）复用同一套 `query()` 主循环，不存在两套实现的行为差异风险。

### 三、Memory 系统深度拆解

#### 3.1 四层记忆架构

| 层级 | 作用域 | 存储位置 | 生命周期 | 特点 |
|------|--------|----------|----------|------|
| Auto Memory | 整个用户/项目协作 | MEMORY.md + topic memories/*.md | 永久 | 长期记忆索引，200行/25KB 硬截断 |
| Session Memory | 当前会话 | 会话摘要 markdown | 会话级 | 辅助 compact，10000 token 初始化，5000 token 更新间隔 |
| Agent Memory | 某个 agent 类型 | user/project/local scope | 永久 | 与 agent 定义直接绑定，注入 system prompt |
| Team Memory | 团队共享 | repo 级 | 永久 | 团队同步的共享记忆 |

#### 3.2 关键实现细节

**MEMORY.md 索引机制**：
- 硬限制：200 行或 25KB，超过则截断
- `findRelevantMemories()` 轻量检索策略：不是向量搜索，而是基于关键词匹配的轻量检索
- 文件权限：0o700（目录）/ 0o600（文件），严格控制访问

**Session Memory 触发阈值**：
- 初始化阈值：10000 token
- 更新间隔：5000 token
- 不是每次对话都写入，而是累积到阈值才触发

**设计哲学**：不把 memory 做成单一数据库或黑盒 KV，而是"多层文件化记忆系统"——不同生命周期、不同作用域、不同可见性的内容分开保存，所有记忆都是 Markdown 文件，可读、可审计、可分发。

### 四、执行内核设计

**query.ts 主循环**（简化骨架）：
```
while (true):
  1. 调用模型 API，流式输出
  2. 检查是否有 tool_use 需要执行
  3. 执行工具，按并发安全性分批
  4. 工具结果追加到 messages → 下一轮循环
  5. 会话管理：compact 检查、hook 执行、memory 更新
```

**Context 管理**：
- 默认上下文窗口：200k
- 为 Summary API 预留：最高 20k
- 有效可用窗口：180k
- 输出 token 优化：默认 cap 在 8000（实际 p99 输出仅 4911 tokens），截断时重试到 64k

### 五、同类产品对比

| 维度 | Claude Code | Codex | Gemini CLI | Aider | Cursor |
|------|-------------|-------|------------|-------|--------|
| 定位 | 本地 agent 平台 | 统一 coding agent 产品线 | 开源 CLI agent 基线 | 轻量终端 pair programming | IDE 主导 |
| Memory | 文件化四层分层 | 云端+本地分层 | checkpoint/context file | 无深度记忆 | IDE 内置 |
| 扩展 | MCP + teammate + swarm | CLI/IDE/SDK/Slack 全入口 | MCP + tools | git-based | IDE plugins |
| 核心优势 | 本地可审计 + 长期记忆 | 产品面最广 | 开源透明 | 轻量快速 | 深度 IDE 集成 |
| 一句话 | 长期协作属性最强 | 覆盖面最广 | 高标准基线 | 最轻量 | IDE 体验最好 |

### 六、三大核心特征

1. **统一的 query/agent/tool/permission 内核** — 所有运行形态复用同一套代码路径
2. **文件化、可审计、分层的 memory 系统** — 不是黑盒数据库，是 Markdown 文件
3. **local-first，可扩展到 remote/bridge/swarm** — 从本地独立运行平滑扩展到多 agent 协作

---

## 🛠️ OpenClaw 适配建议

> 基于 Claude Code 的设计思路，针对 OpenClaw 当前环境的具体改进建议。每项说明：是什么 → 当前状态 → 如何应用 → 预期收益。

### 建议 1：Memory 系统规范化

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | MEMORY.md 索引 + topic memories 分主题存储 + findRelevantMemories 轻量检索 |
| OpenClaw 当前状态 | 有 MEMORY.md 和 memory/ 目录，但缺少分主题存储和检索机制 |
| 建议操作 | ① 在 MEMORY.md 中建立清晰的主题索引（项目/人物/偏好/经验教训）<br>② 在 memory/ 下按主题建立子文件（如 memory/projects.md、memory/people.md）<br>③ AGENTS.md 中加入"启动时按主题加载相关记忆"的流程 |
| 预期收益 | 记忆检索更精准，减少 token 浪费，长期记忆更可维护 |

### 建议 2：Session Memory 阈值控制

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | 10000 token 初始化，5000 token 更新间隔，不每次对话都写入 |
| OpenClaw 当前状态 | 每次对话结束可能都写入 memory，没有阈值控制 |
| 建议操作 | 在 AGENTS.md 中规定：只有对话中产生了重要决策、新信息或经验教训时才写入 memory/，日常闲聊不写入 |
| 预期收益 | 减少 memory 文件膨胀，提高重要信息的信噪比 |

### 建议 3：Context 窗口优化

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | 动态计算有效窗口，为摘要预留空间，默认 cap 输出 token |
| OpenClaw 当前状态 | 依赖默认配置，没有主动的上下文管理策略 |
| 建议操作 | ① 在 AGENTS.md 中加入"长对话自动摘要"策略：对话超过 50 轮时主动总结并存入 memory<br>② 避免在单次对话中加载过多文件内容，按需分批读取 |
| 预期收益 | 避免上下文溢出，提高长对话的连贯性 |

### 建议 4：项目结构规范化

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | 六层清晰分层，每层有明确职责边界 |
| OpenClaw 当前状态 | 工作区文件（AGENTS.md/SOUL.md/TOOLS.md 等）职责有交叉 |
| 建议操作 | ① 明确各文件职责：SOUL.md=人格、AGENTS.md=行为规范、TOOLS.md=工具配置、USER.md=用户信息<br>② 避免在多个文件中重复定义相同规则<br>③ 如果项目有代码，创建 PROJECT.md 记录项目上下文 |
| 预期收益 | 文件结构更清晰，减少规则冲突，新人（或新 session）更容易理解 |

### 建议 5：Skills 使用策略

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | Skills 与 agent memory、tool permission 深度绑定 |
| OpenClaw 当前状态 | Skills 通过 SKILL.md 独立加载，与 memory 系统弱耦合 |
| 建议操作 | ① 在 MEMORY.md 中记录已安装 Skills 的使用心得和最佳实践<br>② 定期检查 Skills 更新（通过 clawhub/skillhub）<br>③ 对于高频使用的 Skills，在 AGENTS.md 中建立使用优先级 |
| 预期收益 | Skills 使用更高效，避免重复安装或遗忘已装 Skills |

### 建议 6：安全与隐私治理

| 项目 | 内容 |
|------|------|
| Claude Code 做法 | 三类数据面管控：模型上下文 / 本地持久化 / 外部同步 |
| OpenClaw 当前状态 | 有基本安全协议，但缺少系统化的数据面分类管控 |
| 建议操作 | ① 在 AGENTS.md 中明确三类数据的处理规则：哪些可以进 context、哪些可以持久化、哪些禁止外发<br>② 定期清理 memory/ 中的敏感信息<br>③ 对于包含敏感内容的对话，不写入 memory |
| 预期收益 | 降低敏感信息泄露风险，建立系统化的隐私治理框架 |

---

## 执行流程

### 快速摘要模式

用户触发后，直接输出「本地知识库」中的核心内容，格式：

```
## Claude Code 源码分析 — 快速摘要

**一句话定位**：面向代码工作流的本地 Agent 平台

**三大核心特征**：
1. 统一的 query/agent/tool/permission 内核
2. 文件化、可审计、分层的 memory 系统
3. local-first，可扩展到 remote/bridge/swarm

**Memory 四层架构**：
• Auto Memory（永久）→ MEMORY.md + topic memories
• Session Memory（会话级）→ 摘要文件，10000/5000 token 阈值
• Agent Memory（永久）→ 与 agent 定义绑定
• Team Memory（永久）→ 团队共享

**与 OpenClaw 最大的差异**：
Claude Code 的 Memory 是文件化+可审计的，OpenClaw 当前更依赖 session 记忆。
建议：规范化 MEMORY.md 结构，建立主题索引和分文件存储。

如需深入某个维度（Memory/架构/对比/适配），请告诉我具体方向。
```

### 深度分析模式

当用户指定具体维度时：
1. 从本地知识库提取该维度的核心内容
2. 从 GitHub 仓库抓取最新的详细章节（如有新内容）
3. 结合 OpenClaw 环境给出具体的适配建议
4. 输出结构化报告

---

## 关键参考数据

- 泄露时间：2026年3月31日
- 代码规模：1902 个源文件，513,237 行 TypeScript
- 泄露原因：npm 包未删除 source map 文件
- 数据来源：GitHub 仓库 `liuup/claude-code-analysis`（已本地化关键内容）

---

## 声明

本技能仅用于技术学习与架构参考。Claude Code 所有权利归 Anthropic 所有。
源码分析仓库地址：https://github.com/liuup/claude-code-analysis
