import os
import logging
import time
from logging.handlers import RotatingFileHandler

# 创建logs目录（如果不存在）- 用于存储日志文件
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)  # 递归创建目录结构

# 日志文件路径 - 按日期命名日志文件，方便按日期查询和管理
log_file = os.path.join(logs_dir, f'weibo_hot_{time.strftime("%Y%m%d")}.log')

# 创建主日志记录器 - 整个应用的根日志记录器，所有模块的日志记录器都继承自它
logger = logging.getLogger('weibo_hot')
logger.setLevel(logging.DEBUG)  # 设置为最低级别，让处理器决定实际记录级别

# 日志格式 - 包含时间、模块名、日志级别和消息，便于问题定位和分析
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 控制台处理器 - 将日志输出到控制台，用于开发调试和实时监控
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别，减少输出量
console_handler.setFormatter(formatter)

# 文件处理器 (RotatingFileHandler，自动滚动日志) - 将日志写入文件，用于长期存储和问题追踪
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10MB - 单个日志文件最大大小，防止日志文件过大
    backupCount=5,          # 保留5个备份文件，控制磁盘空间占用
    encoding='utf-8'        # 使用UTF-8编码，确保中文正确显示
)
file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别日志，便于问题追踪
file_handler.setFormatter(formatter)

# 添加处理器到主日志记录器 - 配置日志输出目标
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def get_logger():
    """
    获取主日志记录器
    
    返回应用程序的主日志记录器，用于记录通用日志
    
    返回值:
        logging.Logger: 配置好的主日志记录器
    """
    return logger

def setup_module_logger(module_name):
    """
    为特定模块创建日志记录器
    
    创建一个子日志记录器，继承主日志记录器的配置，
    但可以使用模块名作为前缀，便于区分不同模块的日志
    
    参数:
        module_name (str): 模块名称，会作为日志记录器名称的一部分
    
    返回值:
        logging.Logger: 配置好的模块日志记录器
    
    示例:
        logger = setup_module_logger('database')
        logger.info('数据库连接成功')  # 输出: "时间 - weibo_hot.database - INFO - 数据库连接成功"
    """
    # 创建子日志记录器，名称格式为"weibo_hot.模块名"
    module_logger = logging.getLogger(f'weibo_hot.{module_name}')
    module_logger.setLevel(logging.DEBUG)
    # 不需要添加处理器，会继承主日志记录器的处理器
    # 这样可以确保所有模块的日志都遵循相同的格式和输出目标
    return module_logger 