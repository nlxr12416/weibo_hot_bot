"""
微博热搜数据访问模块
专门用于访问hot_top50_final表的只读操作

主要功能：
1. 提供数据库连接
2. 查询热搜数据
3. 按排名获取热搜
4. 检查热搜更新
"""
import pymysql  # MySQL数据库连接库
import datetime


def get_db_connection():
    """
    获取数据库连接
    
    创建并返回一个到MySQL数据库的连接对象
    所有数据库操作都通过此连接进行
    
    Returns:
        pymysql.Connection: MySQL数据库连接对象
    """
    return pymysql.connect(
        host='localhost',  # 数据库服务器地址
        user='root',       # 数据库用户名
        password='123456', # 数据库密码
        database='weibo_hot', # 数据库名称
        port=3306,         # 数据库端口
        charset='utf8mb4', # 字符集，支持表情符号
    )


def get_top_hot_searches(limit=10):
    """
    获取排名前N的热搜
    
    按排名顺序获取指定数量的热搜数据
    
    Args:
        limit: 获取的热搜数量，默认10条
        
    Returns:
        list: 热搜列表，每项为包含热搜信息的字典
    
    字典字段说明：
    - rank_num: 排名
    - title: 标题
    - hot_value: 热度值
    - link: 链接
    - analysis_content: AI分析内容
    - fetch_time: 抓取时间
    - analysis_time: 分析时间
    - update_time: 更新时间
    """
    conn = get_db_connection()
    try:
        # 使用DictCursor，结果会以字典形式返回，而不是元组
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT rank_num, title, hot_value, link, 
                   analysis_content, fetch_time, analysis_time, update_time
            FROM hot_top50_final
            WHERE rank_num <= %s
            ORDER BY rank_num
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        # 确保连接被关闭
        conn.close()


def get_all_hot_searches(limit=50):
    """
    获取所有热搜（最多50条）
    
    获取热搜榜上的所有热搜，最多返回指定的数量
    
    Args:
        limit: 获取的热搜数量上限，默认50条
        
    Returns:
        list: 热搜列表，每项为包含热搜信息的字典
    """
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT rank_num, title, hot_value, link, 
                   analysis_content, fetch_time, analysis_time, update_time
            FROM hot_top50_final
            WHERE rank_num <= %s
            ORDER BY rank_num
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        conn.close()


def get_hot_search_by_rank(rank):
    """
    根据排名获取单条热搜
    
    获取指定排名的热搜详细信息
    
    Args:
        rank: 热搜排名
        
    Returns:
        dict: 热搜数据，如果不存在则返回None
    """
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT rank_num, title, hot_value, link, 
                   analysis_content, fetch_time, analysis_time, update_time
            FROM hot_top50_final
            WHERE rank_num = %s
            """
            cursor.execute(sql, (rank,))
            return cursor.fetchone()  # 返回单条结果或None
    finally:
        conn.close()


def check_hot_search_updates():
    """
    检查热搜是否有更新
    
    通过比较最新更新时间来判断热搜是否有更新
    
    Returns:
        tuple: (是否有更新, 更新的热搜列表)
        
    实现逻辑：
    1. 获取最近更新时间
    2. 检查是否在最近5分钟内有更新
    3. 如有更新，返回更新的热搜列表
    """
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 获取最近更新的时间
            sql = """
            SELECT MAX(update_time) as last_update
            FROM hot_top50_final
            WHERE rank_num <= 10
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            last_update = result['last_update'] if result and result['last_update'] else None
            
            if not last_update:
                return False, []
            
            # 检查是否在最近5分钟内有更新
            now = datetime.datetime.now()
            five_minutes_ago = now - datetime.timedelta(minutes=5)
            
            if last_update > five_minutes_ago:
                # 获取最近更新的热搜
                sql = """
                SELECT rank_num, title, hot_value, link, 
                       analysis_content, fetch_time, analysis_time, update_time
                FROM hot_top50_final
                WHERE rank_num <= 10 AND update_time >= %s
                ORDER BY rank_num
                """
                cursor.execute(sql, (five_minutes_ago,))
                updated_hot_searches = cursor.fetchall()
                return True, updated_hot_searches
            
            return False, []
    finally:
        conn.close() 