#!/usr/bin/env python3
"""
Agent Memory System - 核心记忆管理器
管理四类记忆的读写、检索与遗忘
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .storage import MemoryStorage, Memory, MemoryType


@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    agent_id: str = "default"
    started_at: Optional[str] = None
    system_prompt: str = ""
    current_task: str = ""
    user_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.started_at = self.started_at or datetime.now().isoformat()


class AgentMemory:
    """
    Agent 记忆系统
    
    四类记忆：
    - working: 当前会话的工作记忆，快过期
    - episodic: 会话情景记忆，保存会话摘要
    - semantic: 语义记忆，长期重要事实
    - procedural: 程序记忆，Agent技能和偏好
    """
    
    def __init__(self, 
                 agent_id: str = "default",
                 db_path: str = "~/.agent_memory/memory.db",
                 config: Optional[Dict] = None):
        self.agent_id = agent_id
        self.storage = MemoryStorage(db_path)
        self.config = config or {}
        
        # 配置项
        self.max_working_age_hours = self.config.get("max_working_age_hours", 24)
        self.forget_threshold = self.config.get("forget_threshold", 0.2)
        self.max_memories = self.config.get("max_memories", 1000)
        self.importance_decay_rate = self.config.get("importance_decay_rate", 0.01)
        
        # 当前会话
        self.current_session: Optional[SessionContext] = None
    
    # === 核心API ===
    
    def remember(self, key: str, content: str,
                 memory_type: str = "semantic",
                 importance: float = 0.5,
                 tags: Optional[List[str]] = None,
                 session_id: Optional[str] = None,
                 **metadata) -> int:
        """
        存储记忆
        
        Args:
            key: 记忆的唯一标识（如 "user_name", "project_architecture"）
            content: 记忆内容
            memory_type: 记忆类型 (working/episodic/semantic/procedural)
            importance: 重要性 0.0-1.0
            tags: 标签列表，方便检索
            session_id: 关联的会话ID
            **metadata: 额外元数据
        
        Returns:
            memory id
        """
        memory = Memory(
            key=key,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
            agent_id=self.agent_id,
            session_id=session_id or (self.current_session.session_id if self.current_session else None),
            metadata=metadata
        )
        
        # WORKING记忆自动设置过期时间
        if memory_type == "working":
            expires = datetime.now() + timedelta(hours=self.max_working_age_hours)
            memory.expires_at = expires.isoformat()
        
        return self.storage.store(memory)
    
    def recall(self, key: str, 
               memory_type: Optional[str] = None) -> Optional[str]:
        """
        根据key精确回忆
        
        Returns:
            记忆内容，未找到返回None
        """
        memory = self.storage.retrieve(key, self.agent_id, memory_type)
        return memory.content if memory else None
    
    def search(self, query: str,
               memory_type: Optional[str] = None,
               limit: int = 10) -> List[Memory]:
        """
        根据语义/关键词搜索记忆
        
        Returns:
            匹配的记忆列表
        """
        return self.storage.search(query, self.agent_id, memory_type, limit)
    
    def forget(self, key: str, memory_type: Optional[str] = None) -> bool:
        """
        主动遗忘某条记忆
        """
        return self.storage.delete(key, self.agent_id)
    
    # === 会话管理 ===
    
    def start_session(self, session_id: str, **kwargs) -> SessionContext:
        """开始新会话"""
        self.current_session = SessionContext(
            session_id=session_id,
            agent_id=self.agent_id,
            **kwargs
        )
        # 清理过期WORKING记忆
        self.storage.forget_old_working(self.agent_id, self.max_working_age_hours)
        return self.current_session
    
    def end_session(self, summary: Optional[str] = None):
        """结束当前会话"""
        if not self.current_session:
            return
        
        # 保存会话摘要为EPISODIC记忆
        if summary:
            self.remember(
                key=f"session_summary_{self.current_session.session_id}",
                content=summary,
                memory_type="episodic",
                importance=0.7,
                tags=["会话摘要", "历史"]
            )
        
        self.current_session = None
    
    def get_session_history(self, limit: int = 10) -> List[Memory]:
        """获取历史会话摘要"""
        return self.storage.get_all(
            self.agent_id, 
            memory_type="episodic",
            limit=limit
        )
    
    # === 便捷方法 ===
    
    def remember_user(self, key: str, value: str, importance: float = 0.8):
        """记住用户相关信息"""
        return self.remember(key, value, "semantic", importance, tags=["用户"])
    
    def remember_preference(self, key: str, value: str, importance: float = 0.9):
        """记住Agent偏好设置"""
        return self.remember(key, value, "procedural", importance, tags=["偏好", "设置"])
    
    def remember_fact(self, key: str, fact: str, importance: float = 0.7):
        """记住客观事实"""
        return self.remember(key, fact, "semantic", importance, tags=["事实", "知识"])
    
    def remember_skill(self, skill_name: str, description: str):
        """记住一项技能"""
        return self.remember(
            key=f"skill_{skill_name}",
            content=description,
            memory_type="procedural",
            importance=0.9,
            tags=["技能", skill_name]
        )
    
    def update_importance(self, key: str, delta: float):
        """调整记忆重要性（每次访问后自动调用）"""
        memory = self.storage.retrieve(key, self.agent_id)
        if memory:
            memory.importance = min(1.0, max(0.0, memory.importance + delta))
            self.storage.store(memory)
    
    # === 遗忘机制 ===
    
    def auto_forget(self) -> Dict[str, int]:
        """
        自动遗忘：清理低价值记忆
        
        Returns:
            清理统计
        """
        results = {}
        
        # 遗忘低重要性记忆
        low_count = self.storage.forget_low_importance(
            self.forget_threshold, self.agent_id
        )
        results["low_importance"] = low_count
        
        # 遗忘过期WORKING记忆
        expired_count = self.storage.forget_old_working(
            self.agent_id, self.max_working_age_hours
        )
        results["expired_working"] = expired_count
        
        return results
    
    def decay_importance(self):
        """重要性衰减（定期调用）"""
        all_memories = self.storage.get_all(self.agent_id, limit=self.max_memories)
        for memory in all_memories:
            if memory.memory_type not in ["procedural"]:  # 程序记忆不衰减
                memory.importance = max(0.0, memory.importance - self.importance_decay_rate)
                self.storage.store(memory)
    
    # === 上下文构建 ===
    
    def build_context(self, current_task: str = "", max_memories: int = 20) -> str:
        """
        构建用于注入Agent上下文的记忆字符串
        
        Returns:
            格式化的记忆上下文
        """
        parts = []
        
        # 1. 相关历史会话
        if current_task:
            related = self.search(current_task, limit=5)
            episodic = [m for m in related if m.memory_type == "episodic"]
            if episodic:
                parts.append("## 相关历史会话")
                for m in episodic[:3]:
                    parts.append(f"- {m.content}")
        
        # 2. 重要事实和偏好
        semantic = self.storage.get_all(
            self.agent_id, 
            memory_type="semantic",
            limit=10
        )
        if semantic:
            parts.append("## 重要记忆")
            for m in semantic[:10]:
                if m.importance >= 0.6:
                    parts.append(f"- **{m.key}**: {m.content}")
        
        # 3. 当前会话WORKING记忆
        working = self.storage.get_all(
            self.agent_id,
            memory_type="working",
            limit=10
        )
        if working:
            parts.append("## 当前会话")
            for m in working:
                parts.append(f"- {m.key}: {m.content}")
        
        # 4. 技能记忆
        procedural = self.storage.get_all(
            self.agent_id,
            memory_type="procedural",
            limit=10
        )
        if procedural:
            parts.append("## Agent技能/偏好")
            for m in procedural[:5]:
                parts.append(f"- {m.key}: {m.content}")
        
        return "\n".join(parts) if parts else ""
    
    def get_stats(self) -> dict:
        """获取记忆系统统计"""
        return self.storage.get_stats(self.agent_id)


# === Agent 集成辅助 ===

class MemoryAwareAgent:
    """
    记忆感知的 Agent 包装器
    将 AgentMemory 集成到任意 Agent 框架
    """
    
    def __init__(self, agent_id: str = "default", **memory_config):
        self.memory = AgentMemory(agent_id, config=memory_config)
        self.agent_id = agent_id
    
    def inject_context(self, prompt: str, current_task: str = "") -> str:
        """将记忆注入到 prompt"""
        context = self.memory.build_context(current_task)
        if context:
            return f"{prompt}\n\n## 记忆上下文\n{context}\n## /记忆上下文"
        return prompt
    
    def on_message(self, role: str, content: str):
        """处理消息，自动记忆重要信息"""
        if role == "user":
            # 提取可能的用户信息
            if "我叫" in content or "我的名字是" in content:
                name = content.split("叫")[-1].split("是")[-1].strip()
                self.memory.remember_user("user_name", name)
            
            # 记住任务相关
            if "要" in content or "做" in content or "开发" in content:
                self.memory.remember(
                    key="current_task",
                    content=content[:200],
                    memory_type="working",
                    importance=0.6
                )
    
    def on_response(self, content: str):
        """处理响应，提取关键信息"""
        pass


if __name__ == "__main__":
    # 演示用法
    agent = AgentMemory("demo_agent")
    
    # 开一个新会话
    agent.start_session("session_001")
    
    # 记住一些东西
    agent.remember_user("name", "张三")
    agent.remember_preference("coding_style", "简洁直接，不要过度封装")
    agent.remember_fact("project", "正在开发一个AI代码评审工具")
    agent.remember_skill("python", "精通Python，擅长异步编程")
    
    # 搜索
    results = agent.search("用户")
    print("搜索'用户'结果:", [r.content for r in results])
    
    # 回忆
    name = agent.recall("name")
    print("我叫:", name)
    
    # 构建上下文
    ctx = agent.build_context("开发代码评审工具")
    print("\n记忆上下文:\n", ctx)
    
    # 结束会话
    agent.end_session("讨论了代码评审工具的核心功能和实现方案")
    
    # 统计
    print("\n记忆统计:", agent.get_stats())
