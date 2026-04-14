import logging
import sys
from utils.config import LOG_LEVEL


def get_logger(name: str):
    """
    配置并返回一个全局统一的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 动态获取配置的日志级别，缺省为 INFO
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    if not logger.handlers:
        logger.setLevel(numeric_level)
        
        # 终端输出 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # 定义日志格式：[时间] [级别] [名称] - 消息内容
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    else:
        # 如果已经有 handler，也要确保级别同步更新
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        
    return logger

# 提供一个默认的全局 logger
logger = get_logger("GeoTrave")
