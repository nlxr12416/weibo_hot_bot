import httpx
from bs4 import BeautifulSoup
import time
import asyncio
from datetime import datetime, timedelta
from logger import setup_module_logger
import database as db

# 创建日志记录器 - 用于记录爬虫模块的日志信息
logger = setup_module_logger('crawler_async')

async def crawl_weibo_hot():
    """
    异步爬取微博热搜页面并返回解析结果。

    返回值:
        dict: 一个包含热搜话题的字典，如果爬取失败则为None。
    """
    # 注意：此处的Cookie是硬编码的，可能会过期。
    # 为了长期使用，建议采用更健壮的Cookie管理方案。
    url = 'https://s.weibo.com/top/summary/'
    cookie = ''
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    logger.info(f"正在请求微博热搜: {url}")
    start_time = time.time()
    
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.get(url, headers=headers)
            elapsed = time.time() - start_time
            logger.info(f"请求状态码: {response.status_code}, 耗时: {elapsed:.2f}秒")
            response.raise_for_status()
            html = response.text
            logger.info(f"获取HTML内容长度: {len(html)}")
        except httpx.RequestError as e:
            logger.error(f"请求微博热搜页面失败: {e}", exc_info=True)
            return None

    # 解析逻辑是CPU密集型的，同步执行即可
    logger.debug("正在解析HTML内容...")
    soup = BeautifulSoup(html, 'html.parser')
    all_news = {}
    items = soup.find_all('td', class_='td-02')
    logger.debug(f"找到 {len(items) - 1} 个热搜项目。")

    for news in items[1:]:  # 跳过表头
        try:
            text = news.text.split('\n')[1].strip()
            link = news.find('a')['href'] if news.find('a') else ''
            if not link.startswith('http'):
                link = 'https://s.weibo.com' + link
            
            hot_parts = news.text.split('\n')
            if len(hot_parts) < 3 or not hot_parts[2].strip():
                continue
            
            hot_text = hot_parts[2].strip()
            hot = hot_text if hot_text[0].isdigit() else hot_text[2:]

            all_news[text] = {'热度': hot, '链接': link}
        except (IndexError, KeyError) as e:
            logger.warning(f"解析某个热搜项失败: {e}。 原始文本: {news.text.strip()}")
            continue

    logger.info(f"成功解析 {len(all_news)} 条热搜。")
    return all_news


async def initialize_system():
    """初始化系统：初始化数据库、清空数据表并使用最新的爬取数据填充。"""
    logger.info("正在初始化系统...")
    
    await db.init_db()
    await db.clear_all_tables()
    
    all_news = await crawl_weibo_hot()
    if not all_news:
        logger.error("爬取热搜失败，系统初始化失败。")
        return False

    current_time = datetime.now()
    topics_to_insert = []
    changes_to_log = []

    for i, (news, info) in enumerate(all_news.items(), 1):
        topic_data = {
            'rank_num': i,
            'title': news,
            'hot_value': info['热度'],
            'link': info['链接'],
            'fetch_time': current_time,
        }
        # 初始化时，所有话题都是新话题
        topics_to_insert.append(topic_data)
        changes_to_log.append(topic_data)

    await db.atomic_resync_hot_topics(topics_to_insert, changes_to_log)
    await db.update_final_table()

    logger.info(f"初始化完成。已向主表和变更表插入 {len(topics_to_insert)} 条话题。")
    return True
    

async def continuous_crawling_mode():
    """连续爬取微博热搜的异步主循环。"""
    logger.info("启动连续爬取模式...")
    cycle_minutes = 1

    while True:
        try:
            logger.info(f"\n--- 新一轮爬取周期开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            status = await db.get_system_status()
            if status and status.is_analyzing:
                logger.info("分析器正在运行，等待其完成...")
                await asyncio.sleep(3)
                continue

            # 在获取锁之前，记录当前有多少未处理的话题
            initial_unprocessed_count = await db.get_unprocessed_changes_count()
            changes_to_log = []

            if not await db.acquire_crawler_lock():
                logger.info("无法获取爬虫锁，跳过本轮周期。")
                await asyncio.sleep(3)
                continue

            try:
                # 1. 爬取新话题
                all_news = await crawl_weibo_hot()
                if not all_news:
                    logger.error("爬取热搜失败，跳过本轮周期。")
                    continue

                # 2. 获取旧话题的快照以复用分析结果
                old_topics_map = await db.get_hot_topics_map()
                
                # 3. 在内存中准备数据
                current_time = datetime.now()
                topics_to_insert = []
                
                hot_news_items = list(all_news.items())

                for i, (title, info) in enumerate(hot_news_items, 1):
                    base_topic_data = {
                        'rank_num': i,
                        'title': title,
                        'hot_value': info['热度'],
                        'link': info['链接'],
                        'fetch_time': current_time,
                    }

                    topic_to_insert_data = base_topic_data.copy()
                    topic_to_insert_data['analysis_content'] = None
                    topic_to_insert_data['analysis_time'] = None

                    if title in old_topics_map:
                        existing_analysis = old_topics_map[title]
                        topic_to_insert_data['analysis_content'] = existing_analysis.get('analysis_content')
                        topic_to_insert_data['analysis_time'] = existing_analysis.get('analysis_time')
                    else:
                        changes_to_log.append(base_topic_data)

                    topics_to_insert.append(topic_to_insert_data)
                
                # 4. 原子化同步到数据库
                await db.atomic_resync_hot_topics(topics_to_insert, changes_to_log)
                logger.info(f"成功同步 {len(topics_to_insert)} 条话题，发现 {len(changes_to_log)} 条新话题待分析。")

            finally:
                # 5. 关键：完成数据库操作后立即释放锁
                await db.release_crawler_lock()

            # 6. 在锁已释放的情况下，决定如何更新最终表
            if not changes_to_log:
                logger.info("本轮无新话题，立即更新最终结果表。")
                await db.update_final_table()
            else:
                logger.info(f"发现 {len(changes_to_log)} 个新话题，等待分析完成以更新最终表...")
                wait_timeout = 45  # 最长等待45秒
                start_wait = time.time()

                while (await db.get_unprocessed_changes_count()) > initial_unprocessed_count:
                    if time.time() - start_wait > wait_timeout:
                        logger.warning(f"等待分析超时（超过 {wait_timeout} 秒），将使用当前数据更新最终表。")
                        break
                    await asyncio.sleep(2)  # 每2秒检查一次
                
                logger.info("分析完成或等待超时，开始更新最终结果表。")
                await db.update_final_table()

            # 7. 等待下一个周期
            next_run_time = datetime.now() + timedelta(minutes=cycle_minutes)
            logger.info(f"爬取周期完成。等待 {cycle_minutes} 分钟。下一次运行时间: {next_run_time.strftime('%H:%M:%S')}")
            await asyncio.sleep(cycle_minutes * 60)

        except asyncio.CancelledError:
            logger.info("爬取任务被取消。")
            break
        except Exception as e:
            logger.error(f"爬取循环中发生错误: {e}", exc_info=True)
            logger.info("等待60秒后重试...")
            await asyncio.sleep(60)

# The __main__ block has been removed.
# A new central script (e.g., main.py) will be created to run the async tasks.


