"""
微博热搜格式化模块
负责将热搜数据格式化为消息文本

主要功能：
1. 格式化前10条热搜
2. 格式化前5条热搜
3. 格式化所有热搜（最多50条）
4. 格式化单条热搜
"""
import time


def format_top_hot_searches(hot_searches):
    """
    格式化前10热搜，包含完整信息
    
    将前10条热搜数据格式化为美观的文本消息，包含排名、标题、热度、链接和AI总结
    
    Args:
        hot_searches: 热搜列表，每项为包含热搜信息的字典
        
    Returns:
        str: 格式化后的热搜文本
        
    格式示例：
    ```
    📊 微博热搜榜 Top10 📊
    ==============================
    
    【1】热搜标题
    热度：12345678
    链接：https://example.com
    AI总结：这是一条AI总结内容...
    ------------------------------
    
    更新时间：2025-06-13 12:34:56
    ```
    """
    if not hot_searches:
        return "暂无热搜数据"
    
    result_text = "📊 微博热搜榜 Top10 📊\n"
    result_text += "=" * 30 + "\n\n"
    
    # 遍历每条热搜，添加到结果文本中
    for hot in hot_searches:
        result_text += f"【{hot['rank_num']}】{hot['title']}\n"
        result_text += f"热度：{hot['hot_value']}\n"
        result_text += f"链接：{hot['link']}\n"
        if hot['analysis_content']:
            result_text += f"AI总结：{hot['analysis_content']}\n"
        result_text += "-" * 30 + "\n\n"
    
    # 添加更新时间
    update_time = hot_searches[0]['update_time'] if hot_searches[0]['update_time'] else time.strftime('%Y-%m-%d %H:%M:%S')
    result_text += f"更新时间：{update_time}"
    
    return result_text


def format_all_hot_searches(hot_searches):
    """
    格式化所有热搜，包含排名、标题和热度
    
    将热搜数据（最多50条）格式化为简洁的文本消息，只包含排名、标题和热度
    适用于快速浏览大量热搜
    
    Args:
        hot_searches: 热搜列表，每项为包含热搜信息的字典
        
    Returns:
        str: 格式化后的热搜文本
        
    格式示例：
    ```
    📊 微博热搜榜 Top50 📊
    ==============================
    
    1. 热搜标题1 - 热度: 12345678
    2. 热搜标题2 - 热度: 9876543
    ...
    
    更新时间：2025-06-13 12:34:56
    ```
    """
    if not hot_searches:
        return "暂无热搜数据"
    
    result_text = "📊 微博热搜榜 Top50 📊\n"
    result_text += "=" * 30 + "\n\n"
    
    # 遍历每条热搜，只添加排名、标题和热度
    for hot in hot_searches:
        result_text += f"{hot['rank_num']}. {hot['title']} - 热度: {hot['hot_value']}\n"
    
    # 添加更新时间
    update_time = hot_searches[0]['update_time'] if hot_searches[0]['update_time'] else time.strftime('%Y-%m-%d %H:%M:%S')
    result_text += f"\n更新时间：{update_time}"
    
    return result_text


def format_single_hot_search(hot):
    """
    格式化单条热搜，包含完整信息
    
    将单条热搜数据格式化为详细的文本消息，包含排名、标题、热度、链接和AI总结
    适用于查看特定热搜的详细信息
    
    Args:
        hot: 单条热搜数据，包含热搜信息的字典
        
    Returns:
        str: 格式化后的热搜文本
        
    格式示例：
    ```
    📊 微博热搜榜 第5名 📊
    ==============================
    
    【5】热搜标题
    热度：12345678
    链接：https://example.com
    AI总结：这是一条AI总结内容...
    
    更新时间：2025-06-13 12:34:56
    ```
    """
    if not hot:
        return "未找到该排名的热搜"
    
    result_text = f"📊 微博热搜榜 第{hot['rank_num']}名 📊\n"
    result_text += "=" * 30 + "\n\n"
    
    # 添加热搜详细信息
    result_text += f"【{hot['rank_num']}】{hot['title']}\n"
    result_text += f"热度：{hot['hot_value']}\n"
    result_text += f"链接：{hot['link']}\n"
    if hot['analysis_content']:
        result_text += f"AI总结：{hot['analysis_content']}\n"
    
    # 添加更新时间
    update_time = hot['update_time'] if hot['update_time'] else time.strftime('%Y-%m-%d %H:%M:%S')
    result_text += f"\n更新时间：{update_time}"
    
    return result_text


def format_top_five_hot_searches(hot_searches):
    """
    格式化前5热搜，包含完整信息
    
    将前5条热搜数据格式化为美观的文本消息，包含排名、标题、热度、链接和AI总结
    适用于自动推送或快速查看热点
    
    Args:
        hot_searches: 热搜列表，每项为包含热搜信息的字典
        
    Returns:
        str: 格式化后的热搜文本
        
    格式示例：
    ```
    📊 微博热搜榜 Top5 📊
    ==============================
    
    【1】热搜标题1
    热度：12345678
    链接：https://example.com
    AI总结：这是一条AI总结内容...
    ------------------------------
    
    【2】热搜标题2
    ...
    
    更新时间：2025-06-13 12:34:56
    ```
    """
    if not hot_searches:
        return "暂无热搜数据"
    
    result_text = "📊 微博热搜榜 Top5 📊\n"
    result_text += "=" * 30 + "\n\n"
    
    # 只取前5条
    top_five = hot_searches[:5]
    
    # 遍历前5条热搜，添加到结果文本中
    for hot in top_five:
        result_text += f"【{hot['rank_num']}】{hot['title']}\n"
        result_text += f"热度：{hot['hot_value']}\n"
        result_text += f"链接：{hot['link']}\n"
        if hot['analysis_content']:
            result_text += f"AI总结：{hot['analysis_content']}\n"
        result_text += "-" * 30 + "\n\n"
    
    # 添加更新时间
    update_time = hot_searches[0]['update_time'] if hot_searches[0]['update_time'] else time.strftime('%Y-%m-%d %H:%M:%S')
    result_text += f"更新时间：{update_time}"
    
    return result_text 