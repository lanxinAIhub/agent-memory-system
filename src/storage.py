#!/usr/bin/env python3
"""
Agent Memory System - 持久化存储层
基于 SQLite 实现记忆的持久化存储
"""

import sqlite3
import json
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

class MemoryType(Enum):
    WORKING = "working"       # 当前会话工作记忆
    EPISODIC = "episodic"    # 情景记忆（会话摘要）
    SEMANTIC = "semantic"     # 语义记忆（事实/知识）
    PROCEDURAL = "procedural" # 程序记忆（技能/偏好）

@dataclass
class Memory:
    id: Optional[int] = None
    key: str = ""
    content: str = ""
    memory_type: str = "semantic"  # working/episodic/semantic/procedural
    importance: float = 0.5        # 0.0-1.0，重要性评分
    access_count: int = 0          # 访问次数
    last_accessed: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None  # 过期时间
    tags: List[str] = []            # 标签，便于检索
    agent_id: str = "default"       # 所属Agent标识
    session_id: Optional[str] = None # 关联的会话ID
    metadata: Dict[str, Any] = {}     # 额外元数据

    def to_dict(self) -> dict:
        d = asdict(self)
        d['memory_type'] = self.memory_type
        return d

    @classmethod
    def from_row(cls, row: tuple) -> 'Memory':
        return cls(
            id=row[0], key=row[1], content=row[2], memory_type=row[3],
            importance=row[4], access_count=row[5],
            last_accessed=row[6], created_at=row[7],
            expires_at=row[8], tags=json.loads(row[9]) if row[9] else [],
            agent_id=row[10], session_id=row[11],
            metadata=json.loads(row[12]) if row[12] else {}
        )


class MemoryStorage:
    """SQLite 记忆存储"""
    
    def __init__(self, db_path: str = "~/.agent_memory/memory.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'semantic',
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    tags TEXT DEFAULT '[]',
                    agent_id TEXT DEFAULT 'default',
                    session_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(key, agent_id, memory_type)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type 
                ON memories(memory_type, agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance 
                ON memories(importance DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_key 
                ON memories(key, agent_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT DEFAULT 'default',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    summary TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.commit()
    
    def store(self, memory: Memory) -> int:
        """存储记忆，返回ID"""
        now = datetime.now().isoformat()
        memory.created_at = memory.created_at or now
        memory.last_accessed = now
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (key, content, memory_type, importance, access_count, last_accessed,
                 created_at, expires_at, tags, agent_id, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.key, memory.content, memory.memory_type,
                memory.importance, memory.access_count, memory.last_accessed,
                memory.created_at, memory.expires_at,
                json.dumps(memory.tags), memory.agent_id,
                memory.session_id, json.dumps(memory.metadata)
            ))
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def retrieve(self, key: str, agent_id: str = "default", 
                 memory_type: Optional[str] = None) -> Optional[Memory]:
        """根据key检索记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM memories WHERE key = ? AND agent_id = ?"
            params = [key, agent_id]
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
            
            row = conn.execute(query, params).fetchone()
            if row:
                m = Memory.from_row(tuple(row))
                # 更新访问计数
                conn.execute(
                    "UPDATE memories SET access_count = access_count + 1, last_accessed = ? "
                    "WHERE id = ?",
                    (datetime.now().isoformat(), m.id)
                )
                return m
        return None
    
    def search(self, query: str, agent_id: str = "default",
               memory_type: Optional[str] = None,
               limit: int = 10) -> List[Memory]:
        """全文搜索记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            q = f"%{query}%"
            sql = "SELECT * FROM memories WHERE agent_id = ? AND (content LIKE ? OR key LIKE ? OR tags LIKE ?)"
            params = [agent_id, q, q, q]
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            sql += " ORDER BY importance DESC, access_count DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [Memory.from_row(tuple(row)) for row in rows]
    
    def get_all(self, agent_id: str = "default",
                memory_type: Optional[str] = None,
                limit: int = 100) -> List[Memory]:
        """获取所有记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM memories WHERE agent_id = ?"
            params = [agent_id]
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [Memory.from_row(tuple(row)) for row in rows]
    
    def delete(self, key: str, agent_id: str = "default") -> bool:
        """删除记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM memories WHERE key = ? AND agent_id = ?",
                (key, agent_id)
            )
            return cur.rowcount > 0
    
    def forget_low_importance(self, threshold: float = 0.2,
                              agent_id: str = "default") -> int:
        """遗忘低重要性记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM memories WHERE agent_id = ? AND importance < ? AND access_count < 3",
                (agent_id, threshold)
            )
            conn.commit()
            return cur.rowcount
    
    def forget_old_working(self, agent_id: str = "default", 
                           max_age_hours: int = 24) -> int:
        """遗忘过期的WORKING记忆"""
        import time
        cutoff = datetime.fromtimestamp(
            time.time() - max_age_hours * 3600
        ).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM memories WHERE agent_id = ? AND memory_type = 'working' AND created_at < ?",
                (agent_id, cutoff)
            )
            conn.commit()
            return cur.rowcount
    
    def count(self, agent_id: str = "default",
              memory_type: Optional[str] = None) -> int:
        """统计记忆数量"""
        with sqlite3.connect(self.db_path) as conn:
            sql = "SELECT COUNT(*) FROM memories WHERE agent_id = ?"
            params = [agent_id]
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            return conn.execute(sql, params).fetchone()[0]
    
    def get_stats(self, agent_id: str = "default") -> dict:
        """获取记忆统计"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id = ?", (agent_id,)
            ).fetchone()[0]
            
            by_type = {}
            for mtype in MemoryType:
                count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE agent_id = ? AND memory_type = ?",
                    (agent_id, mtype.value)
                ).fetchone()[0]
                by_type[mtype.value] = count
            
            avg_importance = conn.execute(
                "SELECT AVG(importance) FROM memories WHERE agent_id = ?", (agent_id,)
            ).fetchone()[0] or 0
            
            return {
                "total": total,
                "by_type": by_type,
                "avg_importance": round(avg_importance, 3),
                "db_path": self.db_path
            }


if __name__ == "__main__":
    # 简单测试
    store = MemoryStorage("~/.test_memory.db")
    
    # 存入一条记忆
    m = Memory(
        key="user_name",
        content="用户叫张三，喜欢简洁的代码风格",
        memory_type="semantic",
        importance=0.9,
        tags=["用户", "偏好"]
    )
    store.store(m)
    
    # 检索
    result = store.retrieve("user_name")
    print("检索结果:", result.content if result else "未找到")
    
    # 搜索
    results = store.search("用户")
    print("搜索结果:", [r.key for r in results])
    
    # 统计
    print("统计:", store.get_stats())
