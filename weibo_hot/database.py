import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    update,
    delete,
    func,
    text
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from logger import setup_module_logger

logger = setup_module_logger('database_async')

# --- 数据库配置 ---
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASS', '123456')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'weibo_hot')

# 连接MySQL服务器的连接字符串（不指定数据库）
SERVER_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
# 连接应用数据库的连接字符串
ASYNC_DATABASE_URL = f"{SERVER_URL}/{DB_NAME}?charset=utf8mb4"

# --- 引擎和会话设置 ---
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_recycle=3600)
AsyncSessionFactory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


# --- ORM模型定义 ---
class HotTopicMixin:
    """热搜主题表的通用字段"""
    id = Column(Integer, primary_key=True, autoincrement=True)
    rank_num = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    hot_value = Column(String(255))
    link = Column(String(255))
    fetch_time = Column(DateTime, default=datetime.now)
    analysis_content = Column(Text)
    analysis_time = Column(DateTime)

class HotTop50(HotTopicMixin, Base):
    __tablename__ = 'hot_top50'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

class HotTop50Final(Base):
    __tablename__ = 'hot_top50_final'
    # 明确定义所有列以保证顺序
    id = Column(Integer, primary_key=True, autoincrement=True)
    rank_num = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    hot_value = Column(String(255))
    link = Column(String(255))
    fetch_time = Column(DateTime)
    analysis_content = Column(Text)
    analysis_time = Column(DateTime)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = {'mysql_charset': 'utf8mb4'}

class HotChanges(Base):
    __tablename__ = 'hot_changes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    rank_num = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    hot_value = Column(String(255))
    link = Column(String(255))
    fetch_time = Column(DateTime, default=datetime.now)
    is_processed = Column(Boolean, default=False, index=True)
    process_time = Column(DateTime)
    __table_args__ = {'mysql_charset': 'utf8mb4'}

class SystemStatus(Base):
    __tablename__ = 'system_status'
    id = Column(Integer, primary_key=True)
    is_updating = Column(Boolean, default=False)
    is_analyzing = Column(Boolean, default=False)
    last_update_time = Column(DateTime)
    last_analysis_time = Column(DateTime)
    __table_args__ = {'mysql_charset': 'utf8mb4'}


# --- 会话管理 ---
@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """提供一个围绕一系列操作的事务作用域。"""
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"数据库会话错误: {e}", exc_info=True)
        raise
    finally:
        await session.close()


# --- 数据库初始化与状态 ---
async def init_db():
    """初始化数据库，如果数据库或表不存在则创建它们。"""
    engine = create_async_engine(SERVER_URL, echo=False)
    async with engine.connect() as conn:
        await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    await engine.dispose()
    logger.info(f"数据库 '{DB_NAME}' 已检查或创建。")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with get_session() as session:
        result = await session.execute(select(SystemStatus).filter_by(id=1))
        if not result.scalar_one_or_none():
            session.add(SystemStatus(id=1))
            logger.info("已初始化 system_status 表的默认值。")

async def clear_all_tables():
    """清空所有相关表的数据并重置系统状态。"""
    async with get_session() as session:
        for table in [HotTop50, HotChanges, HotTop50Final]:
            await session.execute(delete(table))

        status = await session.get(SystemStatus, 1)
        if status:
            status.is_updating = False
            status.is_analyzing = False
        else:
            session.add(SystemStatus(id=1))
        
        logger.info("所有表已被清空，系统状态已重置。")


# --- 锁管理 ---
async def _acquire_lock(is_updating: bool, is_analyzing: bool):
    """获取锁的内部函数。"""
    async with get_session() as session:
        stmt = (
            update(SystemStatus)
            .where(SystemStatus.id == 1, SystemStatus.is_updating == False, SystemStatus.is_analyzing == False)
            .values(is_updating=is_updating, is_analyzing=is_analyzing, last_update_time=func.now() if is_updating else None, last_analysis_time=func.now() if is_analyzing else None)
            .execution_options(synchronize_session=False)
        )
        result = await session.execute(stmt)
        return result.rowcount > 0

async def acquire_crawler_lock():
    """如果分析器未运行，则获取爬虫锁。"""
    if await _acquire_lock(is_updating=True, is_analyzing=False):
        logger.info("爬虫锁获取成功。")
        return True
    logger.info("无法获取爬虫锁，另一个进程可能正在运行。")
    return False

async def acquire_analyzer_lock():
    """如果爬虫未运行，则获取分析器锁。"""
    if await _acquire_lock(is_updating=False, is_analyzing=True):
        logger.info("分析器锁获取成功。")
        return True
    logger.info("无法获取分析器锁，另一个进程可能正在运行。")
    return False

async def _release_lock(for_crawler: bool):
    """释放锁的内部函数。"""
    async with get_session() as session:
        values = {'is_updating': False} if for_crawler else {'is_analyzing': False}
        stmt = update(SystemStatus).where(SystemStatus.id == 1).values(**values)
        await session.execute(stmt)

async def release_crawler_lock():
    """释放爬虫锁。"""
    await _release_lock(for_crawler=True)
    logger.info("爬虫锁已释放。")

async def release_analyzer_lock():
    """释放分析器锁。"""
    await _release_lock(for_crawler=False)
    logger.info("分析器锁已释放。")

async def get_system_status():
    """获取当前系统状态。"""
    async with get_session() as session:
        result = await session.execute(select(SystemStatus).filter_by(id=1))
        return result.scalar_one_or_none()

# --- 数据操作 ---

async def get_hot_topics_map():
    """获取现有热搜话题及其分析内容的映射。"""
    async with get_session() as session:
        stmt = select(HotTop50.title, HotTop50.analysis_content, HotTop50.analysis_time)
        result = await session.execute(stmt)
        return {
            row.title: {
                'analysis_content': row.analysis_content,
                'analysis_time': row.analysis_time
            } for row in result.all()
        }

async def atomic_resync_hot_topics(topics_to_insert: list, changes_to_log: list):
    """以原子方式将数据库与最新的热搜话题同步。"""
    async with get_session() as session:
        # 使用 TRUNCATE 来重置自增ID，保持id在1-50之间
        await session.execute(text(f"TRUNCATE TABLE {HotTop50.__tablename__}"))
        
        if topics_to_insert:
            session.add_all([HotTop50(**data) for data in topics_to_insert])
            logger.info(f"已准备 {len(topics_to_insert)} 条话题用于主表。")

        if changes_to_log:
            session.add_all([HotChanges(**data) for data in changes_to_log])
            logger.info(f"已准备 {len(changes_to_log)} 条新变更用于分析。")
        return True

async def get_unanalyzed_topics():
    """从变更表中获取所有未处理的话题。"""
    async with get_session() as session:
        stmt = select(HotChanges).where(HotChanges.is_processed == False).order_by(HotChanges.id)
        result = await session.execute(stmt)
        return result.scalars().all()

async def mark_change_processed(change_id: int, analysis: str):
    """将变更标记为已处理，并更新主表中的相应分析。"""
    async with get_session() as session:
        change = await session.get(HotChanges, change_id)
        if not change:
            logger.error(f"无法找到ID为 {change_id} 的变更以标记为已处理。")
            return False
            
        change.is_processed = True
        change.process_time = datetime.now()

        # 同时更新主表中的分析结果
        stmt = (
            update(HotTop50)
            .where(HotTop50.title == change.title)
            .values(analysis_content=analysis, analysis_time=datetime.now())
            .execution_options(synchronize_session=False)
        )
        await session.execute(stmt)
        logger.info(f"变更ID {change_id} (话题: '{change.title}') 已标记为已处理。")
        return True

async def get_unprocessed_changes_count():
    """计算未处理的变更数量。"""
    async with get_session() as session:
        stmt = select(func.count()).select_from(HotChanges).where(HotChanges.is_processed == False)
        result = await session.execute(stmt)
        return result.scalar_one()

async def get_hot_topics_count():
    """计算主表 `hot_top50` 中的话题数量。"""
    async with get_session() as session:
        stmt = select(func.count()).select_from(HotTop50)
        result = await session.execute(stmt)
        return result.scalar_one()

async def update_final_table():
    """将 `hot_top50` 的当前状态复制到 `hot_top50_final`。"""
    async with get_session() as session:
        # 使用 TRUNCATE 来重置自增ID
        await session.execute(text(f"TRUNCATE TABLE {HotTop50Final.__tablename__}"))
        
        topics = await session.execute(select(HotTop50).order_by(HotTop50.rank_num).limit(50))
        
        final_topics = []
        for topic in topics.scalars().all():
            final_topics.append(HotTop50Final(
                id=None,  # 让数据库自动处理自增ID
                rank_num=topic.rank_num,
                title=topic.title,
                hot_value=topic.hot_value,
                link=topic.link,
                fetch_time=topic.fetch_time,
                analysis_content=topic.analysis_content,
                analysis_time=topic.analysis_time,
                # update_time 会自动设置
            ))

        if final_topics:
            session.add_all(final_topics)
            logger.info(f"成功更新最终表，包含 {len(final_topics)} 条话题。")
        else:
            logger.info("最终表已更新，没有需要复制的话题。")
        return True