"""
Module: src.utils.logger
Responsibility: Configures and exports a unified global logger instance for the entire project.
Parent Module: src.utils
Dependencies: logging, sys, src.utils.config

Provides minimalist console logging structured with timestamps, levels, and source names.
Log level is dynamically injected via `config.LOG_LEVEL`.
"""

import logging
import sys

from src.utils.config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    Configure and return a globally unified logger instance.
    
    Args:
        name (str): The name identifier for the logger.
        
    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Dynamically fetch the log level from config, defaulting to INFO
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    if not logger.handlers:
        logger.setLevel(numeric_level)
        
        # Standard console handler outputting to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Consistent formatter: [Timestamp] [Level] [Name] - Message
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    else:
        # Synchronize log level if handlers already exist
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        
    return logger


# Global default logger instance for GeoTrave
logger = get_logger("GeoTrave")
