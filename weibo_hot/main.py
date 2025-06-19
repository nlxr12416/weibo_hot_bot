import asyncio
import os
import argparse
import signal
from logger import setup_module_logger
import crawler
import analysis

logger = setup_module_logger('main')

def get_max_analysis_workers():
    """从环境变量中获取分析程序的最大并发任务数。"""
    try:
        max_workers = int(os.environ.get('MAX_ANALYSIS_WORKERS', 10))
        logger.info(f"分析程序将使用 {max_workers} 个并发任务。")
        return max_workers
    except (ValueError, TypeError):
        logger.warning("环境变量 MAX_ANALYSIS_WORKERS 的值无效，将使用默认值 10。")
        return 10

async def main():
    """异步主函数，用于运行整个应用。"""
    parser = argparse.ArgumentParser(description="微博热搜分析系统 - 异步版")
    parser.add_argument(
        '--init', 
        action='store_true', 
        help="初始化数据库，爬取初始数据并完成分析，然后退出。"
    )
    parser.add_argument(
        '--one-time-analysis',
        action='store_true',
        help="对所有未处理的话题运行一次分析，然后退出。"
    )
    
    args = parser.parse_args()
    max_workers = get_max_analysis_workers()

    try:
        if args.init:
            logger.info("启动系统初始化程序...")
            if await crawler.initialize_system():
                logger.info("初始数据爬取完成。现在开始分析所有话题...")
                await analysis.wait_for_initialization(max_workers)
                logger.info("系统初始化完成。")
            else:
                logger.error("在爬取阶段，系统初始化失败。")
            return

        if args.one_time_analysis:
            logger.info("启动一次性分析程序...")
            await analysis.one_time_analysis_mode(max_workers)
            logger.info("一次性分析执行完毕。")
            return

        # 默认模式：持续运行
        logger.info("启动持续运行模式...")
        print("系统已启动，爬虫和分析程序正在后台持续运行。按 Ctrl+C 退出。")
        
        loop = asyncio.get_running_loop()
        stop = loop.create_future()
        
        # 在Windows上，信号处理需要特殊设置
        if os.name == 'nt':
            def on_signal():
                if not stop.done():
                    stop.set_result(True)
            signal.signal(signal.SIGINT, lambda s, f: on_signal())
            signal.signal(signal.SIGTERM, lambda s, f: on_signal())
        else:
            loop.add_signal_handler(signal.SIGINT, stop.set_result, True)
            loop.add_signal_handler(signal.SIGTERM, stop.set_result, True)

        crawler_task = asyncio.create_task(crawler.continuous_crawling_mode())
        analyzer_task = asyncio.create_task(analysis.continuous_analysis_mode(max_workers))
        
        tasks = [crawler_task, analyzer_task]
        
        try:
            await stop
            logger.info("接收到停止信号...")
        except asyncio.CancelledError:
            logger.info("主任务被取消。")
        finally:
            logger.info("正在取消所有后台任务...")
            for task in tasks:
                task.cancel()
            
            # 等待所有任务完成取消操作
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("所有任务已安全取消。程序即将关闭。")
            
    except Exception as e:
        logger.critical(f"主程序遇到无法恢复的错误: {e}", exc_info=True)
    finally:
        # 这是关闭数据库连接池的唯一、可靠的地方。
        logger.info("正在安全关闭数据库连接池...")
        await crawler.db.async_engine.dispose()

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("微博热搜爬取与分析系统启动")
    logger.info("=" * 50)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断。")
    finally:
        logger.info("=" * 50)
        logger.info("系统已关闭。")
        logger.info("=" * 50) 