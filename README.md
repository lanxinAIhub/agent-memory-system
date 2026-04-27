# 🤖 Agent Memory System

> AI Agent 持久记忆系统：跨会话记忆存储、检索与遗忘机制

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/lanxinAIhub/agent-memory-system/actions/workflows/ci.yml/badge.svg)](https://github.com/lanxinAIhub/agent-memory-system/actions/workflows)

## 核心概念

AI Agent 拥有持久记忆，能够跨会话记住重要信息。

本系统实现四类记忆：

| 类型 | 说明 | 生命周期 |
|------|------|---------|
| ⚡ **Working** | 当前会话工作记忆 | 短期，自动过期 |
| 📖 **Episodic** | 会话情景记忆 | 中期，保存摘要 |
| 🧠 **Semantic** | 语义记忆（事实/知识） | 长期 |
| 🔧 **Procedural** | 程序记忆（技能/偏好） | 长期 |

## 功能特性

- 💾 **持久化存储** — SQLite，本地存储，保护隐私
- 🔍 **语义检索** — 关键词搜索相关记忆
- 🧹 **自动遗忘** — 低价值记忆自动清理
- ⚙️ **简单API** — 轻松集成到各类Agent框架
- 🐙 **GitHub Actions** — 可作为CI/CD的一部分

## 快速开始

### 安装

```bash
pip install agent-memory-system
# 或直接从源码安装
git clone https://github.com/lanxinAIhub/agent-memory-system.git
cd agent-memory-system
pip install -e .
```

### CLI 使用

```bash
# 记住一条信息
memory remember user_name "张三" --type semantic --importance 0.9

# 回忆
memory recall user_name

# 搜索
memory search "用户"

# 查看统计
memory stats

# 列出所有记忆
memory list

# 搜索特定类型
memory list --type semantic
```

### Python API

```python
from agent_memory import AgentMemory

# 初始化
agent = AgentMemory("my_agent")

# 记住信息
agent.remember_user("name", "张三")
agent.remember_preference("style", "简洁直接")
agent.remember_fact("project", "正在开发AI代码评审工具")

# 搜索记忆
results = agent.search("项目")
print(results[0].content)

# 构建上下文（注入到prompt）
context = agent.build_context("开发AI工具")
# 输出：
# ## 重要记忆
# - project: 正在开发AI代码评审工具
# - name: 张三
```

### 在 Agent 中集成

```python
from agent_memory import MemoryAwareAgent

agent = MemoryAwareAgent("coding_assistant")

# 自动处理消息
agent.on_message("user", "我叫李四，做后端开发")
agent.on_message("user", "要开发一个API网关项目")

# 构建带记忆的prompt
prompt = "帮我写一个API网关的代码"
enhanced_prompt = agent.inject_context(prompt, "开发API网关")
```

## 工作原理

```
用户消息
    ↓
MemoryAwareAgent.on_message()
    ↓
关键信息提取 → AgentMemory.remember()
    ↓
SQLite 持久化
    ↓
Agent 执行任务时
    ↓
AgentMemory.build_context() → 上下文字符串
    ↓
注入到 prompt
```

## 遗忘机制

记忆不是越多越好。本系统实现了智能遗忘：

1. **访问衰减** — 每次访问增加重要性
2. **时间衰减** — 定期降低长期未访问记忆的重要性
3. **自动清理** — 重要性低于阈值时自动遗忘

```python
# 手动触发遗忘
agent.auto_forget()

# 或配置自动遗忘
agent = AgentMemory("my_agent", config={
    "forget_threshold": 0.2,      # 低于此值被遗忘
    "max_working_age_hours": 24  # WORKING记忆24小时后过期
})
```

## 项目结构

```
agent-memory-system/
├── src/
│   ├── memory.py     # 核心记忆管理器
│   ├── storage.py   # SQLite持久化层
│   └── cli.py        # 命令行工具
├── README.md
└── LICENSE
```

## 适用场景

- **个人AI助手** — 记住用户偏好、项目背景
- **代码评审Agent** — 记住代码规范、评审历史
- **客服机器人** — 跨会话记住用户信息和历史问题
- **研究Agent** — 记住论文摘要、实验结果

## License

MIT License
