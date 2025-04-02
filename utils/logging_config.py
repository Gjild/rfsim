# utils/logging_config.py
import logging
from typing import Optional

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Set up logging with a console handler and optionally a file handler.

    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG).
        log_file: Optional path to a file for logging output.
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # Optional file handler
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Retrieve a logger with the given name and level.
    
    Args:
        name: The name of the logger.
        level: Logging level.
        
    Returns:
        A configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
