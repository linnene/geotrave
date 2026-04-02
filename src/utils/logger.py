import logging
import sys

def get_logger(name: str):
    """
    配置并返回一个全局统一的日志记录器
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # 终端输出 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 定义日志格式：[时间] [级别] [名称] - 消息内容
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger

# 提供一个默认的全局 logger
logger = get_logger("GeoTrave")
