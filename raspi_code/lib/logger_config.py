# lib/logger_config.py
import logging
import sys
import os

LOGS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_FOLDER, exist_ok=True)

def setup_logger(name: str, log_file: str = "debug.log", level=logging.INFO):
    """
      Sets up a logger that can be used across modules.
      
      Args:
          name (str): Name of the logger (usually __name__ in modules)
          log_file (str, optional): If provided, logs will also be written to this file
          level (int): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
      Returns:
          logging.Logger: Configured logger
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate logs if logger is called multiple times
    if not logger.hasHandlers():
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

        # File handler (inside logs folder)
        log_path = os.path.join(LOGS_FOLDER, log_file)
        fh = logging.FileHandler(log_path)
        fh.setLevel(level)
        fh_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

    return logger
