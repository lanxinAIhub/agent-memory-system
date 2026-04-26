#!/usr/bin/env python3
"""
Agent Memory System - CLI 工具
命令行接口，方便直接使用
"""

import sys
import argparse
import json
import os
from datetime import datetime

# 导入记忆系统
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.memory import AgentMemory, MemoryType
from src.storage import MemoryStorage


def cmd_remember(args):
    """记住一条信息"""
    memory = AgentMemory(args.agent)
    memory.remember(
        key=args.key,
        content=args.content,
        memory_type=args.type,
        importance=args.importance,
        tags=args.tags.split(",") if args.tags else []
    )
    print(f"✅ 已记住: {args.key}")


def cmd_recall(args):
    """回忆信息"""
    memory = AgentMemory(args.agent)
    result = memory.recall(args.key, args.type)
    if result:
        print(result)
    else:
        print(f"未找到记忆: {args.key}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    """搜索记忆"""
    memory = AgentMemory(args.agent)
    results = memory.search(args.query, args.type, args.limit)
    if not results:
        print("未找到匹配的记忆")
        return
    
    print(f"找到 {len(results)} 条记忆:\n")
    for m in results:
        print(f"🔑 {m.key} [{m.memory_type}] ⭐{m.importance:.1f}")
        print(f"   {m.content[:100]}{'...' if len(m.content) > 100 else ''}")
        print()


def cmd_forget(args):
    """遗忘信息"""
    memory = AgentMemory(args.agent)
    if memory.forget(args.key, args.type):
        print(f"✅ 已遗忘: {args.key}")
    else:
        print(f"未找到记忆: {args.key}")


def cmd_list(args):
    """列出所有记忆"""
    storage = MemoryStorage()
    memories = storage.get_all(args.agent, args.type, args.limit)
    
    if not memories:
        print("暂无记忆")
        return
    
    print(f"共 {len(memories)} 条记忆:\n")
    for m in memories:
        icon = {"working": "⚡", "episodic": "📖", "semantic": "🧠", "procedural": "🔧"}.get(m.memory_type, "📝")
        print(f"{icon} {m.key} [{m.memory_type}] ⭐{m.importance:.1f} 访问:{m.access_count}")
        print(f"   {m.content[:80]}{'...' if len(m.content) > 80 else ''}")
        print()


def cmd_stats(args):
    """显示统计信息"""
    memory = AgentMemory(args.agent)
    stats = memory.get_stats()
    
    print(f"📊 Agent Memory 统计")
    print(f"=" * 40)
    print(f"总记忆数: {stats['total']}")
    print(f"平均重要性: {stats['avg_importance']}")
    print(f"\n按类型分布:")
    for mtype, count in stats['by_type'].items():
        icon = {"working": "⚡", "episodic": "📖", "semantic": "🧠", "procedural": "🔧"}.get(mtype, "📝")
        print(f"  {icon} {mtype}: {count}")
    print(f"\n数据库: {stats['db_path']}")


def cmd_context(args):
    """构建上下文"""
    memory = AgentMemory(args.agent)
    ctx = memory.build_context(args.task, args.limit)
    print(ctx or "(无相关记忆)")


def cmd_session(args):
    """会话管理"""
    memory = AgentMemory(args.agent)
    
    if args.action == "start":
        session = memory.start_session(args.session_id)
        print(f"✅ 会话已开始: {session.session_id}")
        print(f"   Agent: {session.agent_id}")
        print(f"   启动时间: {session.started_at}")
    
    elif args.action == "end":
        memory.end_session(args.summary)
        print("✅ 会话已结束")
        if args.summary:
            print(f"   摘要: {args.summary[:50]}...")
    
    elif args.action == "history":
        sessions = memory.get_session_history(args.limit)
        if not sessions:
            print("暂无历史会话")
            return
        print(f"历史会话 ({len(sessions)} 条):\n")
        for s in sessions:
            print(f"📖 {s.key}")
            print(f"   {s.content[:80]}...")
            print()


def cmd_forget_auto(args):
    """自动遗忘"""
    memory = AgentMemory(args.agent)
    results = memory.auto_forget()
    print("🧹 自动遗忘完成:")
    for k, v in results.items():
        print(f"   {k}: {v} 条被遗忘")


def main():
    parser = argparse.ArgumentParser(
        description="🤖 Agent Memory System - AI Agent 持久记忆工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    # remember
    p_remember = sub.add_parser("remember", help="存储记忆")
    p_remember.add_argument("key", help="记忆key")
    p_remember.add_argument("content", help="记忆内容")
    p_remember.add_argument("--type", "-t", default="semantic",
                              choices=["working","episodic","semantic","procedural"],
                              help="记忆类型")
    p_remember.add_argument("--importance", "-i", type=float, default=0.5,
                              help="重要性 0.0-1.0")
    p_remember.add_argument("--tags", help="标签，逗号分隔")
    p_remember.add_argument("--agent", default="default", help="Agent ID")
    p_remember.set_defaults(func=cmd_remember)
    
    # recall
    p_recall = sub.add_parser("recall", help="回忆（精确查找）")
    p_recall.add_argument("key", help="记忆key")
    p_recall.add_argument("--type", help="记忆类型")
    p_recall.add_argument("--agent", default="default", help="Agent ID")
    p_recall.set_defaults(func=cmd_recall)
    
    # search
    p_search = sub.add_parser("search", help="搜索记忆")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--type", help="记忆类型")
    p_search.add_argument("--limit", "-n", type=int, default=10, help="结果数量")
    p_search.add_argument("--agent", default="default", help="Agent ID")
    p_search.set_defaults(func=cmd_search)
    
    # forget
    p_forget = sub.add_parser("forget", help="遗忘记忆")
    p_forget.add_argument("key", help="记忆key")
    p_forget.add_argument("--type", help="记忆类型")
    p_forget.add_argument("--agent", default="default", help="Agent ID")
    p_forget.set_defaults(func=cmd_forget)
    
    # list
    p_list = sub.add_parser("list", help="列出所有记忆")
    p_list.add_argument("--type", help="记忆类型")
    p_list.add_argument("--limit", "-n", type=int, default=100)
    p_list.add_argument("--agent", default="default", help="Agent ID")
    p_list.set_defaults(func=cmd_list)
    
    # stats
    p_stats = sub.add_parser("stats", help="显示统计")
    p_stats.add_argument("--agent", default="default", help="Agent ID")
    p_stats.set_defaults(func=cmd_stats)
    
    # context
    p_ctx = sub.add_parser("context", help="构建记忆上下文")
    p_ctx.add_argument("--task", "-t", default="", help="当前任务")
    p_ctx.add_argument("--limit", "-n", type=int, default=20)
    p_ctx.add_argument("--agent", default="default", help="Agent ID")
    p_ctx.set_defaults(func=cmd_context)
    
    # session
    p_sess = sub.add_parser("session", help="会话管理")
    p_sess.add_argument("action", choices=["start","end","history"])
    p_sess.add_argument("--session-id", "-s", default=None, help="会话ID")
    p_sess.add_argument("--summary", help="会话摘要")
    p_sess.add_argument("--limit", "-n", type=int, default=10)
    p_sess.add_argument("--agent", default="default", help="Agent ID")
    p_sess.set_defaults(func=cmd_session)
    
    # forget-auto
    p_fa = sub.add_parser("forget-auto", help="自动遗忘低价值记忆")
    p_fa.add_argument("--agent", default="default", help="Agent ID")
    p_fa.set_defaults(func=cmd_forget_auto)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
