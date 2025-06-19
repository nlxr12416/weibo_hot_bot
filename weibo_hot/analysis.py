import os
import time
import httpx
import asyncio
from logger import setup_module_logger
import database as db

# 创建日志记录器 - 用于记录分析模块的日志信息
logger = setup_module_logger('analysis_async')

# 从环境变量获取DeepSeek API密钥 - 用于调用AI分析热搜
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    logger.error("缺少DeepSeek API密钥，请设置环境变量DEEPSEEK_API_KEY")
    raise ValueError("缺少DeepSeek API密钥，请设置环境变量DEEPSEEK_API_KEY")
else:
    logger.info("成功读取DeepSeek API密钥")

# DeepSeek API配置 - 设置API端点和认证头
API_URL = "https://api.deepseek.com/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
}

async def analyze_hot_topic(topic: str, hot_value: str, client: httpx.AsyncClient):
    """
    使用DeepSeek API异步分析单个热搜话题。

    参数:
        topic (str): 热搜话题标题。
        hot_value (str): 热搜热度值。
        client (httpx.AsyncClient): 用于发送请求的HTTP客户端。

    返回值:
        str: 分析结果，如果失败则返回错误信息。
    """
    logger.info(f"开始分析热搜话题: {topic}，热度: {hot_value}")
    
    prompt = f"""请对以下微博热搜话题进行分析，简要解释该话题的背景、关注原因以及社会影响。
请控制在100字左右，不要有开头问候或结尾总结，直接给出分析内容。

热搜话题：{topic}
热度值：{hot_value}

请简明扼要地分析这个话题："""

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }

    start_time = time.time()
    try:
        # 增加超时以避免长时间等待
        response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=60.0)
        elapsed = time.time() - start_time
        
        logger.debug(f"话题 '{topic}' API响应状态码: {response.status_code}，耗时: {elapsed:.2f}秒")
        response.raise_for_status()
        
        result = response.json()
        analysis = result['choices'][0]['message']['content'].strip()
        
        logger.info(f"话题 '{topic}' 分析完成，内容长度: {len(analysis)}字符")
        return analysis
    except httpx.RequestError as e:
        logger.error(f"API调用失败 (话题: {topic}): {e}", exc_info=True)
        return f"分析失败: {str(e)}"
    except (KeyError, IndexError) as e:
        logger.error(f"解析API响应失败 (话题: {topic}): {e}", exc_info=True)
        logger.error(f"失败的响应内容: {response.text}")
        return "分析失败: 无法解析API响应"

async def process_unanalyzed_topics(max_concurrent_tasks=10):
    """
    使用asyncio并发处理所有未分析的热搜话题。

    参数:
        max_concurrent_tasks (int): 最大并发任务数。

    返回值:
        int: 成功处理的热搜话题数量。
    """
    logger.info(f"开始处理未分析的热搜话题，最大并发数: {max_concurrent_tasks}")
    
    if not await db.acquire_analyzer_lock():
        logger.info("无法获取分析锁，爬虫程序可能正在运行，跳过本次分析")
        return 0

    processed_count = 0
    try:
        topics_to_analyze = await db.get_unanalyzed_topics()
        
        if not topics_to_analyze:
            logger.info("没有需要分析的新热搜话题")
            return 0
        
        topic_count = len(topics_to_analyze)
        logger.info(f"找到 {topic_count} 条需要分析的热搜话题")
        
        # 使用信号量控制并发数量
        semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        async def analyze_and_update(change, client):
            """获取信号量，执行分析并更新数据库。"""
            async with semaphore:
                logger.info(f"工作协程开始分析排名 {change.rank_num} 的话题: {change.title}")
                start_time = time.time()
                analysis_result = await analyze_hot_topic(change.title, change.hot_value, client)
                await db.mark_change_processed(change.id, analysis_result)
                elapsed = time.time() - start_time
                logger.info(f"话题 '{change.title}' 处理完成，用时: {elapsed:.2f}秒")

        async with httpx.AsyncClient() as client:
            tasks = [analyze_and_update(change, client) for change in topics_to_analyze]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"处理话题 {topics_to_analyze[i].title} 时发生异常: {result}", exc_info=result)
                else:
                    processed_count += 1
        
        logger.info(f"并发分析完成，成功处理 {processed_count}/{topic_count} 条热搜话题")

    finally:
        await db.release_analyzer_lock()
        
    return processed_count

async def continuous_analysis_mode(max_concurrent_tasks=10):
    """
    以持续模式运行，定期检查并分析新的热搜话题。
    """
    logger.info(f"启动连续分析模式，最大并发数: {max_concurrent_tasks}")
    
    while True:
        try:
            status = await db.get_system_status()
            if status and status.is_updating:
                logger.info("爬虫程序正在运行，等待其完成后再分析...")
                await asyncio.sleep(3)
                continue
                
            processed_count = await process_unanalyzed_topics(max_concurrent_tasks)
            
            if processed_count > 0:
                logger.info(f"本轮分析完成，共处理 {processed_count} 条热搜话题")
            
            check_interval = 5  # 每5秒检查一次
            logger.debug(f"等待 {check_interval} 秒后再次检查...")
            await asyncio.sleep(check_interval)
            
        except asyncio.CancelledError:
            logger.info("分析任务被用户中断")
            break
        except Exception as e:
            logger.error(f"分析循环中发生错误: {e}", exc_info=True)
            logger.info("等待30秒后重试...")
            await asyncio.sleep(30)

async def one_time_analysis_mode(max_concurrent_tasks=10):
    """
    一次性分析所有未处理的热搜话题，然后退出。
    """
    logger.info(f"启动一次性分析模式，最大并发数: {max_concurrent_tasks}")
    try:
        processed_count = await process_unanalyzed_topics(max_concurrent_tasks)
        logger.info(f"分析完成，共处理 {processed_count} 条热搜话题")
        
        if processed_count > 0:
            if await db.update_final_table():
                logger.info("一次性分析模式：成功更新最终结果表")
            else:
                logger.error("一次性分析模式：更新最终结果表失败")
                
        return processed_count
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}", exc_info=True)
        return 0

async def wait_for_initialization(max_concurrent_tasks=10):
    """
    持续分析，直到所有初始化时爬取的热搜都已处理完毕。
    """
    logger.info(f"等待热搜初始化分析完成，最大并发数: {max_concurrent_tasks}")
    
    while True:
        unprocessed_count = await db.get_unprocessed_changes_count()
        if unprocessed_count == 0:
            logger.info("所有热搜初始化分析完成")
            if await db.update_final_table():
                logger.info("初始化阶段：成功更新最终结果表")
            else:
                logger.error("初始化阶段：更新最终结果表失败")
            return True
        
        logger.info(f"还有 {unprocessed_count} 条热搜等待分析...")
        
        processed_this_round = await process_unanalyzed_topics(max_concurrent_tasks)
        if processed_this_round == 0:
            logger.warning("本轮未处理任何热搜，但仍有未处理项，等待10秒后重试")
            await asyncio.sleep(10)

# __main__ 块已被移除，由新的中央异步入口点处理。 