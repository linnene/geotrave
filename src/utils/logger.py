"""
Logger Module: Centralized logging configuration for GeoTrave.

Provides structured console output with configurable log levels.

Parent Module: src.utils
Dependencies: logging, sys, api.config
"""

import logging
import sys
from utils.config import LOG_LEVEL

def get_logger(name: str) -> logging.Logger:
    """
    Initialize and return a configured logger instance.
    
    Ensures that handlers are only added once to avoid duplicate log entries.
    """
    logger = logging.getLogger(name)
    
    # Sync with global LOG_LEVEL from config
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
    
    if not logger.handlers:
        logger.setLevel(numeric_level)
        
        # Standard Output Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Define log format: [Timestamp] [Level] [Module] - Message
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    else:
        # Sync level for existing handlers
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        
    return logger

# Single default instance for widespread use
logger = get_logger("GeoTrave")
